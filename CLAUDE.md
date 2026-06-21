# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (Flask not in PATH — use python -m)
python -m flask run

# Database migrations
python -m flask db upgrade                   # apply pending migrations
python -m flask db migrate -m "description"  # generate migration after model changes
python -m flask db upgrade                   # then apply it
```

> No automated tests in this project.

---

## Architecture

| Layer | Details |
|---|---|
| **App** | Single-file Flask app — all routes, models, and logic in `app.py`. No blueprints. |
| **Database** | SQLite locally (`instance/study_tracker.db`), PostgreSQL on Railway (`DATABASE_URL`). ORM: Flask-SQLAlchemy. Migrations: Flask-Migrate (Alembic). |
| **Models** | `User`, `StudyGroup`, `StudySession`, `BreakEntry`, `HomeworkTask`, `Event` |
| **Auth** | Two paths: (1) local username/password via Flask-Bcrypt; (2) Google OAuth via Supabase JS SDK (implicit flow) → `/auth/callback` → POST to `/auth/verify` → Flask session |
| **Session** | Flask-Session (filesystem). Datetimes stored as naive UTC. `User.timezone` (pytz) applied at display time via `get_current_datetime()` / `get_current_date()`. Never rely on server time. |
| **Frontend** | Jinja2 templates + per-page CSS/JS in `static/`. Shared styles: `shared.css`, `dark_mode.css`, `dropdown.css`. No bundler. Charts: Chart.js (CDN). Calendar: FullCalendar (CDN). |
| **Study Groups** | One group per user via `User.group_id` FK. Auto-deleted when last member leaves. Join codes: 6-char alphanumeric via `secrets`. |

**Most complex route:** `/summary` — computes weekly leaderboard, per-day study/break breakdowns, per-course pie chart, and GitHub-style heatmap entirely in Python, passed as JSON to the template.

---

## Environment Variables

Loaded from `app.env` locally, or from Railway environment in production.

| Variable | Purpose | Required |
|---|---|---|
| `SECRET_KEY` | Flask session signing | Yes |
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Supabase anon/public key | Yes |
| `DATABASE_URL` | PostgreSQL URL | No (falls back to SQLite) |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | Gmail SMTP for password-reset emails | No (mocks to stdout if unset) |

---

## Key Conventions

- **Auth guard** — every protected route: `if session.get('username') == None: return redirect(url_for('login'))`
- **Ownership check** — before any mutation: verify `record.username == session['username']`
- **Sort preferences** — stored in Flask session (`session['sort_homework']`, `session['sort_notes']`, `session['sort_events']`) so they persist across page loads
- **Soft-delete notes** — sets `hidden_from_notes=True` and clears `notes` on `StudySession` (preserves study time data)
- **Duration helper** — `calculate_duration_mins(start, end, target_date)` slices multi-day sessions to a single day's contribution
- **Migrations** — always name unique constraints explicitly (e.g., `'uq_user_email'`) — SQLite batch mode fails on `None` constraint names

---

## Communication Style

- Always address me as **Jason** at the start of a conversation.
- Keep responses **short and direct**. No padding.
- For non-trivial changes, include a **brief explanation** of what's happening and why — just enough for me to learn the concept, not a full breakdown. Use judgment on what's worth explaining.
- For trivial fixes (typos, missing imports), just state the fix and why in one sentence.

---

## Code Commenting Policy

- Add comments in **every file** so a new developer can understand what each section does without prior context.
- Comment **sections and non-obvious logic** — not individual obvious lines.
- Focus on the *why* behind decisions, not restating what the code does.
- Flag edge cases, trade-offs, and anything that would surprise a new reader.
