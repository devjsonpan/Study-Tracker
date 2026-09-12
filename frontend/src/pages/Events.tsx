// Events page — add/edit/complete/delete events with start and end datetimes.
// Validates that end time is after start time before submitting.

import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import { getEvents, createEvent, toggleComplete, toggleImportance, deleteEvent, editEvent } from '../api/events'
import type { Event } from '../api/events'
import { getTheme } from '../lib/themes'
import ConfirmModal from '../components/ConfirmModal'

// --- Helpers ---

function formatDatetime(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit',
  })
}

function getUrgency(endIso: string, completed: boolean): 'overdue' | 'soon' | null {
  if (completed) return null
  const diff = new Date(endIso).getTime() - Date.now()
  if (diff < 0) return 'overdue'
  if (diff < 24 * 60 * 60 * 1000) return 'soon'
  return null
}

function toDatetimeLocal(iso: string) {
  return iso.slice(0, 16)
}

// Structural input classes — border color applied via inline style
const inputBase = 'px-3 py-2 rounded-xl border text-sm font-medium text-slate-800 placeholder:text-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-slate-100 transition'
const inputFull = `w-full ${inputBase}`

// --- Inline edit form ---

function EditForm({
  event, onSave, onCancel, isPending, theme,
}: {
  event: Event
  onSave: (data: Omit<Event, 'id' | 'is_completed' | 'is_important'>) => void
  onCancel: () => void
  isPending: boolean
  theme: ReturnType<typeof getTheme>
}) {
  const [formError, setFormError] = useState<string | null>(null)

  function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const start = fd.get('start_datetime') as string
    const end = fd.get('end_datetime') as string
    if (new Date(end) <= new Date(start)) {
      setFormError('End time must be after start time.')
      return
    }
    setFormError(null)
    onSave({
      event_name: fd.get('event_name') as string,
      start_datetime: start,
      end_datetime: end,
      location: (fd.get('location') as string) || null,
      description: (fd.get('description') as string) || null,
    })
  }

  const labelCls = 'block text-xs font-semibold text-slate-400 mb-1'

  return (
    <form onSubmit={handleSubmit} className="mt-3 space-y-2">
      {formError && (
        <p className="text-xs font-semibold text-rose-500 bg-rose-50 px-3 py-2 rounded-xl">{formError}</p>
      )}
      <input name="event_name" defaultValue={event.event_name} placeholder="Event name" required
        className={inputFull} style={{ borderColor: theme.border }} />
      <div className="flex gap-2">
        <div className="flex-1 min-w-0">
          <label className={labelCls}>Start</label>
          <input name="start_datetime" type="datetime-local" defaultValue={toDatetimeLocal(event.start_datetime)} required
            className={inputFull} style={{ borderColor: theme.border }} />
        </div>
        <div className="flex-1 min-w-0">
          <label className={labelCls}>End</label>
          <input name="end_datetime" type="datetime-local" defaultValue={toDatetimeLocal(event.end_datetime)} required
            className={inputFull} style={{ borderColor: theme.border }} />
        </div>
      </div>
      <input name="location" defaultValue={event.location ?? ''} placeholder="Location (optional)"
        className={inputFull} style={{ borderColor: theme.border }} />
      <input name="description" defaultValue={event.description ?? ''} placeholder="Description (optional)"
        className={inputFull} style={{ borderColor: theme.border }} />
      <div className="flex gap-2">
        <button type="submit" disabled={isPending}
          className="btn-primary px-4 py-1.5 text-white font-bold rounded-xl text-xs cursor-pointer"
          style={{ background: theme.accent }}>
          {isPending ? 'Saving…' : 'Save'}
        </button>
        <button type="button" onClick={onCancel}
          className="btn-secondary px-4 py-1.5 font-bold rounded-xl text-xs cursor-pointer"
          style={{ background: theme.activeBg, color: theme.accent }}>
          Cancel
        </button>
      </div>
    </form>
  )
}

// --- Sort logic ---

type EventSort = 'start_asc' | 'start_desc' | 'starred' | 'az'

const EVENT_SORTS: { key: EventSort; label: string }[] = [
  { key: 'start_asc',    label: 'Start date' },
  { key: 'start_desc',   label: 'Latest first' },
  { key: 'starred',      label: 'Starred' },
  { key: 'az',           label: 'A–Z' },
]

function sortEvents(events: Event[], sort: EventSort): Event[] {
  return [...events].sort((a, b) => {
    if (sort === 'start_asc')    return new Date(a.start_datetime).getTime() - new Date(b.start_datetime).getTime()
    if (sort === 'start_desc')   return new Date(b.start_datetime).getTime() - new Date(a.start_datetime).getTime()
    if (sort === 'starred')      return (+b.is_important - +a.is_important) || new Date(a.start_datetime).getTime() - new Date(b.start_datetime).getTime()
    if (sort === 'az')           return a.event_name.localeCompare(b.event_name)
    return 0
  })
}

// --- Component ---

export default function Events() {
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [sort, setSort] = useState<EventSort>('start_asc')
  const [search, setSearch] = useState('')
  // Hide-completed toggle — persisted so the preference survives reloads.
  // Completed items stay in the DB (and on the calendar); this only filters the list view.
  const [hideCompleted, setHideCompleted] = useState(() => {
    try { return localStorage.getItem('events.hideCompleted') === '1' } catch { return false }
  })
  function toggleHideCompleted() {
    const next = !hideCompleted
    setHideCompleted(next)
    try { localStorage.setItem('events.hideCompleted', next ? '1' : '0') } catch { /* storage blocked — in-memory only */ }
  }

  const { pathname } = useLocation()
  const theme = getTheme(pathname)

  const { data, isLoading, error } = useQuery({ queryKey: ['events'], queryFn: getEvents })

  const createMutation = useMutation({
    mutationFn: createEvent,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['events'] }),
  })
  const completeMutation = useMutation({
    mutationFn: toggleComplete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['events'] }),
  })
  const importanceMutation = useMutation({
    mutationFn: toggleImportance,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['events'] }),
  })
  const deleteMutation = useMutation({
    mutationFn: deleteEvent,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['events'] }),
  })
  const editMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Omit<Event, 'id' | 'is_completed' | 'is_important'> }) =>
      editEvent(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['events'] })
      setEditingId(null)
    },
  })

  function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const start = fd.get('start_datetime') as string
    const end = fd.get('end_datetime') as string
    if (new Date(end) <= new Date(start)) {
      setFormError('End time must be after start time.')
      return
    }
    setFormError(null)
    const form = e.currentTarget
    createMutation.mutate(
      {
        event_name: fd.get('event_name') as string,
        start_datetime: start,
        end_datetime: end,
        location: (fd.get('location') as string) || null,
        description: (fd.get('description') as string) || null,
      },
      { onSuccess: () => form.reset() },
    )
  }

  const cardStyle: React.CSSProperties = {
    background: '#FFFFFF',
    border: `1px solid ${theme.border}`,
    borderRadius: '16px',
  }

  const labelCls = 'block text-xs font-semibold text-slate-400 mb-1'

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <p className="font-semibold animate-pulse" style={{ color: theme.accent }}>Loading events…</p>
    </div>
  )
  if (error) return (
    <div className="flex items-center justify-center h-64">
      <p className="text-rose-400 font-semibold">Something went wrong. Try refreshing.</p>
    </div>
  )

  const events = data!
  const completedCount = events.filter(e => e.is_completed).length
  const visible = hideCompleted ? events.filter(e => !e.is_completed) : events
  const q = search.trim().toLowerCase()
  const filtered = q
    ? visible.filter(e =>
        e.event_name.toLowerCase().includes(q) ||
        (e.location ?? '').toLowerCase().includes(q) ||
        (e.description ?? '').toLowerCase().includes(q)
      )
    : visible
  const sorted = sortEvents(filtered, sort)

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">

      <div className="mb-6">
        <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight">Events</h1>
        <p className="text-sm text-slate-400 mt-1 font-medium">
          {events.length} event{events.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Search */}
      <input
        value={search} onChange={e => setSearch(e.target.value)}
        placeholder="Search events, locations…"
        className={`${inputFull} mb-3`} style={{ borderColor: theme.border }}
      />

      {/* Sort controls */}
      <div className="flex flex-wrap gap-1.5 mb-6">
        {EVENT_SORTS.map(({ key, label }) => (
          <button key={key} onClick={() => setSort(key)}
            className="px-3 py-1 rounded-full text-xs font-bold transition-all cursor-pointer"
            style={sort === key
              ? { background: theme.accent, color: '#FFFFFF' }
              : { background: theme.activeBg, color: theme.accent }
            }>
            {label}
          </button>
        ))}
        {/* Hide-completed toggle — sits right of the sort pills */}
        <button onClick={toggleHideCompleted}
          className="ml-auto px-3 py-1 rounded-full text-xs font-bold transition-all cursor-pointer"
          style={hideCompleted
            ? { background: theme.accent, color: '#FFFFFF' }
            : { background: theme.activeBg, color: theme.accent }
          }>
          {hideCompleted ? `Show completed (${completedCount})` : 'Hide completed'}
        </button>
      </div>

      {/* Add event form */}
      <div className="shadow-sm p-6 mb-6" style={cardStyle}>
        <h2 className="text-xs font-bold uppercase tracking-wider mb-4" style={{ color: theme.accent }}>
          Add an event
        </h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input name="event_name" placeholder="Event name" required
            className={inputFull} style={{ borderColor: theme.border }} />
          <div className="flex gap-3">
            <div className="flex-1 min-w-0">
              <label className={labelCls}>Start</label>
              <input name="start_datetime" type="datetime-local" required
                className={inputFull} style={{ borderColor: theme.border }} />
            </div>
            <div className="flex-1 min-w-0">
              <label className={labelCls}>End</label>
              <input name="end_datetime" type="datetime-local" required
                className={inputFull} style={{ borderColor: theme.border }} />
            </div>
          </div>
          {formError && (
            <p className="text-xs font-semibold text-rose-500 bg-rose-50 px-3 py-2 rounded-xl">{formError}</p>
          )}
          <input name="location" placeholder="Location (optional)"
            className={inputFull} style={{ borderColor: theme.border }} />
          <input name="description" placeholder="Description (optional)"
            className={inputFull} style={{ borderColor: theme.border }} />
          <button type="submit" disabled={createMutation.isPending}
            className="btn-primary w-full px-5 py-2 text-white font-bold rounded-xl text-sm cursor-pointer shadow-sm"
            style={{ background: theme.accent }}>
            {createMutation.isPending ? 'Adding…' : '+ Add Event'}
          </button>
        </form>
      </div>

      {events.length === 0 && (
        <div className="text-center py-20">
          <p className="font-bold text-slate-400">No events yet.</p>
        </div>
      )}
      {events.length > 0 && sorted.length === 0 && (
        <div className="text-center py-20">
          <p className="font-bold text-slate-400">No events match "{search}".</p>
        </div>
      )}

      <ConfirmModal
        isOpen={deletingId !== null}
        title="Delete event?"
        message="This can't be undone."
        onConfirm={() => { deleteMutation.mutate(deletingId!); setDeletingId(null) }}
        onCancel={() => setDeletingId(null)}
        theme={theme}
      />

      <ul className="space-y-3">
        {sorted.map(event => {
          const urgency = getUrgency(event.end_datetime, event.is_completed)
          return (
            <li key={event.id}
              className={`shadow-sm px-5 py-4 transition-opacity ${event.is_completed ? 'opacity-50' : ''}`}
              style={cardStyle}
            >
              <div className="flex items-start gap-4">
                <button onClick={() => completeMutation.mutate(event.id)}
                  className="mt-1 w-5 h-5 rounded-full border-2 shrink-0 transition-colors cursor-pointer"
                  style={event.is_completed
                    ? { background: theme.accent, borderColor: theme.accent }
                    : { borderColor: theme.border }}
                />
                <div className="flex-1 min-w-0">
                  {(urgency === 'overdue' || urgency === 'soon') && (
                    <div className="flex items-center gap-2 mb-1">
                      {urgency === 'overdue' && (
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-500">Overdue</span>
                      )}
                      {urgency === 'soon' && (
                        <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-orange-100 text-orange-500">Starting soon</span>
                      )}
                    </div>
                  )}
                  <p className={`font-bold text-slate-800 leading-snug ${event.is_completed ? 'line-through' : ''}`}>
                    {event.event_name}
                  </p>
                  <p className="text-xs text-slate-400 mt-1 font-medium">
                    {formatDatetime(event.start_datetime)} → {formatDatetime(event.end_datetime)}
                  </p>
                  {event.location && editingId !== event.id && (
                    <p className="text-xs text-slate-400 mt-0.5">{event.location}</p>
                  )}
                  {/* break-all handles long unbroken strings like URLs */}
                  {event.description && editingId !== event.id && (
                    <p className="text-sm text-slate-500 mt-0.5 break-all">{event.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-3 shrink-0 mt-0.5">
                  <button onClick={() => importanceMutation.mutate(event.id)}
                    className="text-xl leading-none cursor-pointer transition-all hover:scale-110"
                    style={{ color: event.is_important ? theme.border : '#D1D5DB' }}>
                    ★
                  </button>
                  <button onClick={() => setEditingId(editingId === event.id ? null : event.id)}
                    className="text-xs font-bold cursor-pointer transition-colors"
                    style={{ color: theme.accent, opacity: 0.7 }}>
                    {editingId === event.id ? 'Close' : 'Edit'}
                  </button>
                  <button onClick={() => setDeletingId(event.id)}
                    className="text-rose-300 hover:text-rose-400 cursor-pointer transition-colors font-bold">
                    ✕
                  </button>
                </div>
              </div>

              {editingId === event.id && (
                <EditForm
                  event={event}
                  isPending={editMutation.isPending}
                  onCancel={() => setEditingId(null)}
                  onSave={data => editMutation.mutate({ id: event.id, data })}
                  theme={theme}
                />
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
