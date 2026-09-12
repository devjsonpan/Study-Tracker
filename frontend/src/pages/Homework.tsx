// Homework page — add/edit/complete/delete study tasks.
// Each task has a course badge, urgency indicators, and an inline edit form.

import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import { getTasks, createTask, toggleComplete, toggleImportance, deleteTask, editTask } from '../api/homework'
import type { Task } from '../api/homework'
import { getTheme } from '../lib/themes'
import ConfirmModal from '../components/ConfirmModal'

// --- Helpers ---

function formatDue(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit',
  })
}

function getUrgency(iso: string, completed: boolean): 'overdue' | 'soon' | null {
  if (completed) return null
  const diff = new Date(iso).getTime() - Date.now()
  if (diff < 0) return 'overdue'
  if (diff < 24 * 60 * 60 * 1000) return 'soon'
  return null
}

function toDatetimeLocal(iso: string) {
  return iso.slice(0, 16)
}

// Structural input classes without color — border color is applied via inline style per-theme
const inputBase = 'px-3 py-2 rounded-xl border text-sm font-medium text-slate-800 placeholder:text-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-slate-100 transition'
const inputFull = `w-full ${inputBase}`
const inputFlex = `flex-1 min-w-0 ${inputBase}`

// --- Inline edit form ---
// Receives theme via props so it doesn't need its own useLocation call

function EditForm({
  task, onSave, onCancel, isPending, theme,
}: {
  task: Task
  onSave: (data: Omit<Task, 'id' | 'is_completed' | 'is_important'>) => void
  onCancel: () => void
  isPending: boolean
  theme: ReturnType<typeof getTheme>
}) {
  function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    onSave({
      course: fd.get('course') as string,
      task_name: fd.get('task_name') as string,
      description: (fd.get('description') as string) || null,
      due_date: fd.get('due_date') as string,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 space-y-2">
      <div className="flex gap-2">
        <input name="course" defaultValue={task.course} placeholder="Course" required
          className={`w-28 ${inputBase}`} style={{ borderColor: theme.border }} />
        <input name="task_name" defaultValue={task.task_name} placeholder="Task name" required
          className={inputFlex} style={{ borderColor: theme.border }} />
      </div>
      <input name="description" defaultValue={task.description ?? ''} placeholder="Description (optional)"
        className={inputFull} style={{ borderColor: theme.border }} />
      <input name="due_date" type="datetime-local" defaultValue={toDatetimeLocal(task.due_date)} required
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

type HomeworkSort = 'deadline_asc' | 'deadline_desc' | 'starred' | 'az'

const HOMEWORK_SORTS: { key: HomeworkSort; label: string }[] = [
  { key: 'deadline_asc',  label: 'Due date' },
  { key: 'deadline_desc', label: 'Latest first' },
  { key: 'starred',       label: 'Starred' },
  { key: 'az',            label: 'A–Z' },
]

function sortTasks(tasks: Task[], sort: HomeworkSort): Task[] {
  return [...tasks].sort((a, b) => {
    if (sort === 'deadline_asc')  return new Date(a.due_date).getTime() - new Date(b.due_date).getTime()
    if (sort === 'deadline_desc') return new Date(b.due_date).getTime() - new Date(a.due_date).getTime()
    if (sort === 'starred')       return (+b.is_important - +a.is_important) || new Date(a.due_date).getTime() - new Date(b.due_date).getTime()
    if (sort === 'az')            return a.task_name.localeCompare(b.task_name)
    return 0
  })
}

// --- Component ---

export default function Homework() {
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [sort, setSort] = useState<HomeworkSort>('deadline_asc')
  const [search, setSearch] = useState('')
  // Hide-completed toggle — persisted so the preference survives reloads.
  // Completed items stay in the DB (and on the calendar); this only filters the list view.
  const [hideCompleted, setHideCompleted] = useState(() => {
    try { return localStorage.getItem('homework.hideCompleted') === '1' } catch { return false }
  })
  function toggleHideCompleted() {
    const next = !hideCompleted
    setHideCompleted(next)
    try { localStorage.setItem('homework.hideCompleted', next ? '1' : '0') } catch { /* storage blocked — in-memory only */ }
  }

  const { pathname } = useLocation()
  const theme = getTheme(pathname)

  const { data, isLoading, error } = useQuery({ queryKey: ['tasks'], queryFn: getTasks })

  const createMutation = useMutation({
    mutationFn: createTask,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  })
  const completeMutation = useMutation({
    mutationFn: toggleComplete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  })
  const importanceMutation = useMutation({
    mutationFn: toggleImportance,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  })
  const deleteMutation = useMutation({
    mutationFn: deleteTask,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  })
  const editMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Omit<Task, 'id' | 'is_completed' | 'is_important'> }) =>
      editTask(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      setEditingId(null)
    },
  })

  function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const form = e.currentTarget
    createMutation.mutate(
      {
        course: fd.get('course') as string,
        task_name: fd.get('task_name') as string,
        description: (fd.get('description') as string) || null,
        due_date: fd.get('due_date') as string,
      },
      { onSuccess: () => form.reset() },
    )
  }

  const cardStyle: React.CSSProperties = {
    background: '#FFFFFF',
    border: `1px solid ${theme.border}`,
    borderRadius: '16px',
  }

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <p className="font-semibold animate-pulse" style={{ color: theme.accent }}>Loading tasks…</p>
    </div>
  )
  if (error) return (
    <div className="flex items-center justify-center h-64">
      <p className="text-rose-400 font-semibold">Something went wrong. Try refreshing.</p>
    </div>
  )

  const tasks = data!
  const completedCount = tasks.filter(t => t.is_completed).length
  const visible = hideCompleted ? tasks.filter(t => !t.is_completed) : tasks
  const q = search.trim().toLowerCase()
  const filtered = q
    ? visible.filter(t =>
        t.task_name.toLowerCase().includes(q) ||
        t.course.toLowerCase().includes(q) ||
        (t.description ?? '').toLowerCase().includes(q)
      )
    : visible
  const sorted = sortTasks(filtered, sort)

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">

      <div className="mb-6">
        <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight">Homework</h1>
        <p className="text-sm text-slate-400 mt-1 font-medium">
          {tasks.length} task{tasks.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Search */}
      <input
        value={search} onChange={e => setSearch(e.target.value)}
        placeholder="Search tasks, courses…"
        className={`${inputFull} mb-3`} style={{ borderColor: theme.border }}
      />

      {/* Sort controls */}
      <div className="flex flex-wrap gap-1.5 mb-6">
        {HOMEWORK_SORTS.map(({ key, label }) => (
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

      {/* Add task form */}
      <div className="shadow-sm p-6 mb-6" style={cardStyle}>
        <h2 className="text-xs font-bold uppercase tracking-wider mb-4" style={{ color: theme.accent }}>
          Add a task
        </h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Course and task name side by side */}
          <div className="flex gap-3">
            <input name="course" placeholder="Course" required
              className={`w-28 ${inputBase}`} style={{ borderColor: theme.border }} />
            <input name="task_name" placeholder="Task name" required
              className={inputFlex} style={{ borderColor: theme.border }} />
          </div>
          <input name="description" placeholder="Description (optional)"
            className={inputFull} style={{ borderColor: theme.border }} />
          <div className="flex gap-3 items-center">
            <input name="due_date" type="datetime-local" required
              className={inputFlex} style={{ borderColor: theme.border }} />
            <button type="submit" disabled={createMutation.isPending}
              className="btn-primary px-5 py-2 text-white font-bold rounded-xl text-sm cursor-pointer shadow-sm shrink-0"
              style={{ background: theme.accent }}>
              {createMutation.isPending ? 'Adding…' : '+ Add'}
            </button>
          </div>
        </form>
      </div>

      {tasks.length === 0 && (
        <div className="text-center py-20">
          <p className="font-bold text-slate-400">No tasks yet.</p>
        </div>
      )}
      {tasks.length > 0 && sorted.length === 0 && (
        <div className="text-center py-20">
          <p className="font-bold text-slate-400">
            {q ? `No tasks match "${search}".` : 'All tasks completed — nice.'}
          </p>
        </div>
      )}

      <ConfirmModal
        isOpen={deletingId !== null}
        title="Delete task?"
        message="This can't be undone."
        onConfirm={() => { deleteMutation.mutate(deletingId!); setDeletingId(null) }}
        onCancel={() => setDeletingId(null)}
        theme={theme}
      />

      <ul className="space-y-3">
        {sorted.map(task => {
          const urgency = getUrgency(task.due_date, task.is_completed)
          return (
            <li key={task.id}
              className={`shadow-sm px-5 py-4 transition-opacity ${task.is_completed ? 'opacity-50' : ''}`}
              style={cardStyle}
            >
              <div className="flex items-start gap-4">
                {/* Complete toggle — filled with accent color when done */}
                <button onClick={() => completeMutation.mutate(task.id)}
                  className="mt-1 w-5 h-5 rounded-full border-2 shrink-0 transition-colors cursor-pointer"
                  style={task.is_completed
                    ? { background: theme.accent, borderColor: theme.accent }
                    : { borderColor: theme.border }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    {/* Course badge in page theme color */}
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full"
                      style={{ background: theme.activeBg, color: theme.accent }}>
                      {task.course}
                    </span>
                    {urgency === 'overdue' && (
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-500">Overdue</span>
                    )}
                    {urgency === 'soon' && (
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-orange-100 text-orange-500">Due soon</span>
                    )}
                  </div>
                  <p className={`font-bold text-slate-800 leading-snug ${task.is_completed ? 'line-through' : ''}`}>
                    {task.task_name}
                  </p>
                  {task.description && editingId !== task.id && (
                    <p className="text-sm text-slate-500 mt-0.5 break-words">{task.description}</p>
                  )}
                  <p className="text-xs text-slate-400 mt-1 font-medium">Due {formatDue(task.due_date)}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0 mt-0.5">
                  {/* Star — theme border color when active, neutral when not */}
                  <button onClick={() => importanceMutation.mutate(task.id)}
                    className="text-xl leading-none cursor-pointer transition-all hover:scale-110"
                    style={{ color: task.is_important ? theme.border : '#D1D5DB' }}>
                    ★
                  </button>
                  <button onClick={() => setEditingId(editingId === task.id ? null : task.id)}
                    className="text-xs font-bold cursor-pointer transition-colors"
                    style={{ color: theme.accent, opacity: 0.7 }}>
                    {editingId === task.id ? 'Close' : 'Edit'}
                  </button>
                  <button onClick={() => setDeletingId(task.id)}
                    className="text-rose-300 hover:text-rose-400 cursor-pointer transition-colors font-bold">
                    ✕
                  </button>
                </div>
              </div>

              {editingId === task.id && (
                <EditForm
                  task={task}
                  isPending={editMutation.isPending}
                  onCancel={() => setEditingId(null)}
                  onSave={data => editMutation.mutate({ id: task.id, data })}
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
