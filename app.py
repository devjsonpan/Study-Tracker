# Study Time Tracker — Flask application entry point.
# All routes, models, and business logic live in this single file (no blueprints).
# See CLAUDE.md for architecture overview, conventions, and environment variable docs.

# =============================================================================
# Imports
# =============================================================================

# Flask core: app factory, request parser, server-side session, JSON response helper
from flask import Flask, request, session, jsonify

from flask_sqlalchemy import SQLAlchemy    # ORM — talk to DB using Python classes instead of raw SQL
from flask_migrate import Migrate          # manages DB schema changes via Alembic migration files
from flask_bcrypt import Bcrypt            # hashes passwords so plain text is never stored
from flask_session import Session          # stores session data on the server filesystem instead of in the cookie
from flask_socketio import SocketIO, join_room, emit  # real-time bidirectional messaging (chat feature)

from apscheduler.schedulers.background import BackgroundScheduler  # runs functions on a schedule in a background thread (email reminders)

from collections import defaultdict        # dict that auto-initializes missing keys (used for aggregating study/break totals)
from datetime import datetime, timedelta, date   # date math throughout the app
import os, re, secrets, string, time, pytz, threading  # pytz for timezones; secrets for cryptographically secure join codes

from dotenv import load_dotenv             # loads app.env into os.environ at startup
import requests as http_requests           # outbound HTTP — Brevo email API, Supabase token verification

from google import genai                   # Gemini AI client (used only in /api/parse)
from google.genai import types as genai_types  # typed config objects for controlling Gemini generation

# =============================================================================
# App & Database Config
# =============================================================================

# app.env is a non-standard filename, so pass it explicitly; load_dotenv() is a fallback
# for Railway's injected env vars or a plain .env file in the project root
load_dotenv('app.env')
load_dotenv()

# Serve the compiled React app from frontend/dist (built by Vite before deploy).
# static_folder must point at the Vite output directory so Flask can find index.html
# and the hashed asset files (main-abc123.js, etc.) that Vite generates.
app = Flask(__name__, static_folder='frontend/dist', static_url_path='')

# Railway injects DATABASE_URL as postgres://, but SQLAlchemy requires postgresql://
database_url = os.getenv('DATABASE_URL', 'sqlite:///study_tracker.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# SESSION_TYPE = 'filesystem' stores session data in files on the server, not in the cookie.
# This keeps the cookie small and prevents users from reading/tampering with session contents.
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

db      = SQLAlchemy(app)
bcrypt  = Bcrypt(app)
migrate = Migrate(app, db)

# async_mode='threading' works on any Python version with no extra deps.
# simple-websocket (in requirements.txt) provides WebSocket support in this mode.
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# =============================================================================
# Models
# =============================================================================
# Each class maps to a DB table. SQLAlchemy generates the SQL; Flask-Migrate tracks schema changes.
# Convention: username is a plain string FK (not Integer FK) to avoid JOIN overhead on every query.

class StudyGroup(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String, nullable=False)
    join_code = db.Column(db.String, unique=True, nullable=False)

class User(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String, unique=True, nullable=False)
    fullname   = db.Column(db.String, nullable=False)
    password   = db.Column(db.String, nullable=True)       # null for Google-only accounts
    timezone   = db.Column(db.String, nullable=False)
    google_id  = db.Column(db.String, unique=True, nullable=True)  # set for Google OAuth users
    email      = db.Column(db.String, unique=True, nullable=True)  # used for password reset + OAuth account linking
    group_id   = db.Column(db.Integer, db.ForeignKey('study_group.id'), nullable=True)
    group      = db.relationship('StudyGroup', backref='members')

    # AI import rate limiting — tracks daily usage in the user's local timezone
    parse_date  = db.Column(db.Date, nullable=True)
    parse_count = db.Column(db.Integer, default=0, nullable=False, server_default='0')

    # Email reminders — opt-in toggle; requires email to be set before enabling
    # server_default is required for nullable=False columns added via migration (existing rows need a default)
    email_reminders = db.Column(db.Boolean, default=False, nullable=False, server_default='0')
    # reminder_timing column exists in the DB but is unused by the UI (simplified to 1-hour only toggle)
    reminder_timing = db.Column(db.String(10), default='1day', nullable=False, server_default='1day')

class StudySession(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    username         = db.Column(db.String, nullable=False)
    course           = db.Column(db.String, nullable=False)
    topic            = db.Column(db.String, nullable=True)
    start_datetime   = db.Column(db.DateTime, nullable=False)
    end_datetime     = db.Column(db.DateTime, nullable=False)
    notes            = db.Column(db.String, nullable=True)
    # Soft-delete flag: True means the note was "deleted" but the row stays to preserve study time stats
    hidden_from_notes = db.Column(db.Boolean, default=False, nullable=False)
    is_important     = db.Column(db.Boolean, default=False, nullable=False)

class HomeworkTask(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String, nullable=False)
    course       = db.Column(db.String, nullable=False)
    task_name    = db.Column(db.String, nullable=False)
    description  = db.Column(db.String, nullable=True)
    due_date     = db.Column(db.DateTime, nullable=False)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    is_important = db.Column(db.Boolean, default=False, nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.now)

class Event(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    username       = db.Column(db.String, nullable=False)
    event_name     = db.Column(db.String, nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime   = db.Column(db.DateTime, nullable=False)
    location       = db.Column(db.String, nullable=True)
    description    = db.Column(db.String, nullable=True)
    is_completed   = db.Column(db.Boolean, default=False, nullable=False)
    is_important   = db.Column(db.Boolean, default=False, nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.now)

class BreakEntry(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    username       = db.Column(db.String, nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime   = db.Column(db.DateTime, nullable=False)

class Message(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, nullable=False)
    sender          = db.Column(db.String(80), nullable=False)
    content         = db.Column(db.Text, nullable=True)
    file_url        = db.Column(db.Text, nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.now)

class Conversation(db.Model):
    # type is either 'dm' (direct message between two users) or 'group' (linked to a StudyGroup)
    id         = db.Column(db.Integer, primary_key=True)
    type       = db.Column(db.String(10), nullable=False)
    group_id   = db.Column(db.Integer, nullable=True)  # only set when type == 'group'
    created_at = db.Column(db.DateTime, default=datetime.now)

class Friendship(db.Model):
    # status is 'pending' (request sent) or 'accepted' (both users are friends)
    id         = db.Column(db.Integer, primary_key=True)
    sender     = db.Column(db.String(80), nullable=False)
    receiver   = db.Column(db.String(80), nullable=False)
    status     = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class ConversationMember(db.Model):
    # Junction table: one row per (conversation, user) pair.
    # Used to check membership before allowing message reads/sends.
    id              = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, nullable=False)
    username        = db.Column(db.String(80), nullable=False)

# =============================================================================
# Helper Functions
# =============================================================================

def generate_join_code(length=6):
    """Returns a random 6-character alphanumeric code for study group invites."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

# pytz.common_timezones is the list shown in the timezone dropdown (~400 entries)
TIMEZONES = pytz.common_timezones

def get_current_datetime(user_timezone=None):
    """Returns the current time as a naive datetime in the user's local timezone.
    Naive means no tzinfo attached — all DB datetimes are stored this way.
    Timezone is only applied here at read time, never stored."""
    try:
        tz = pytz.timezone(user_timezone) if user_timezone else pytz.UTC
    except pytz.UnknownTimeZoneError:
        tz = pytz.UTC
    return datetime.now(tz).replace(tzinfo=None)

def get_current_date(user_timezone=None):
    """Returns today's date in the user's local timezone (no time component)."""
    try:
        tz = pytz.timezone(user_timezone) if user_timezone else pytz.UTC
    except pytz.UnknownTimeZoneError:
        tz = pytz.UTC
    return datetime.now(tz).date()

def get_user_timezone(username=None):
    """Looks up the user's timezone string from the DB.
    Falls back to 'UTC' if the user is not found or has no timezone set."""
    if username is None:
        username = session.get('username')
    if username:
        user = User.query.filter_by(username=username).first()
        if user and user.timezone:
            return user.timezone
    return 'UTC'

def calculate_duration_mins(start_datetime, end_datetime, target_date=None):
    """Calculates how many minutes a session/break falls on a specific date.
    Without target_date, returns the full duration.
    With target_date, clips the session to only the portion within that calendar day.
    This handles sessions that span midnight correctly."""
    if target_date is None:
        return (end_datetime - start_datetime).total_seconds() / 60.0

    start_of_target = datetime.combine(target_date, datetime.min.time())
    end_of_target   = start_of_target + timedelta(days=1)

    # Clamp the session to the target day's boundaries
    chunk_start = max(start_datetime, start_of_target)
    chunk_end   = min(end_datetime, end_of_target)

    if chunk_start < chunk_end:
        return (chunk_end - chunk_start).total_seconds() / 60.0
    return 0.0

# =============================================================================
# Email Helpers
# =============================================================================
# Both functions call the Brevo transactional email API.
# If BREVO_API_KEY is not set (local dev), they print to stdout instead of sending.

def send_reset_email(to_email, reset_code):
    """Sends a 6-digit password reset code to the given email address."""
    api_key = os.getenv('BREVO_API_KEY')

    if not api_key:
        print(f"MOCK EMAIL to {to_email}: Your reset code is {reset_code}")
        return True

    try:
        response = http_requests.post(
            'https://api.brevo.com/v3/smtp/email',
            headers={
                'api-key': api_key,
                'Content-Type': 'application/json',
            },
            json={
                'sender': {'name': 'LockNIn', 'email': 'studytracker.noreply@gmail.com'},
                'to': [{'email': to_email}],
                'subject': 'Password Reset Code - LockNIn',
                'textContent': f'Your password reset code is: {reset_code}\n\nIf you did not request this, please ignore this email.',
            },
            timeout=10,
        )
        if response.status_code in (200, 201):
            return True
        print(f"Brevo error: {response.status_code} {response.text}")
        return False
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_reminder_email(to_email, fullname, items):
    """Sends a homework deadline reminder.
    items is a list of dicts: {'name': str, 'due': str}"""
    api_key = os.getenv('BREVO_API_KEY')

    lines = [f"  - {i['name']} — due {i['due']}" for i in items]
    body = (
        f"Hi {fullname},\n\nYou have an upcoming homework deadline:\n\n"
        + "\n".join(lines)
        + "\n\nLock in and get it done!"
        + "\n\nTo turn off reminders, go to Profile > Email Reminders."
    )

    if not api_key:
        print(f"MOCK REMINDER EMAIL to {to_email}:\n{body}")
        return True

    try:
        response = http_requests.post(
            'https://api.brevo.com/v3/smtp/email',
            headers={'api-key': api_key, 'Content-Type': 'application/json'},
            json={
                'sender': {'name': 'LockNIn', 'email': 'studytracker.noreply@gmail.com'},
                'to': [{'email': to_email}],
                'subject': 'Upcoming homework deadline — LockNIn',
                'textContent': body,
            },
            timeout=10,
        )
        return response.status_code in (200, 201)
    except Exception as e:
        print(f"Failed to send reminder email: {e}")
        return False

# =============================================================================
# Auth Routes
# =============================================================================
# Two auth paths:
#   1. Google OAuth via Supabase JS SDK — frontend gets the access token, sends it here for verification
#   2. Local username/password — traditional login/register with bcrypt-hashed passwords

@app.route('/auth/verify', methods=['POST'])
def auth_verify():
    """Verifies a Supabase Google OAuth access token and creates/finds the user in our DB.
    The frontend calls this after the Supabase JS SDK completes the OAuth flow."""
    access_token = request.json.get('access_token')
    if not access_token:
        return jsonify({'error': 'No token provided'}), 400

    supabase_url      = os.getenv('SUPABASE_URL')
    supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')

    # Ask Supabase to validate the token and return user metadata
    resp = http_requests.get(
        f"{supabase_url}/auth/v1/user",
        headers={
            "Authorization": f"Bearer {access_token}",
            "apikey": supabase_anon_key
        }
    )

    if resp.status_code != 200:
        return jsonify({'error': 'Invalid token'}), 401

    user_data = resp.json()
    google_id = user_data.get('id')
    email     = user_data.get('email', '')
    metadata  = user_data.get('user_metadata', {})
    full_name = metadata.get('full_name') or metadata.get('name') or email.split('@')[0]

    # Look up by google_id first; fall back to email so that a user who previously
    # registered with a password can link their Google account on their first OAuth login
    user = User.query.filter_by(google_id=google_id).first()
    if not user and email:
        user = User.query.filter_by(email=email).first()

    if not user:
        # New user — generate a unique username from the email prefix
        base_username = re.sub(r'[^a-zA-Z0-9_]', '', email.split('@')[0]) or 'user'
        username = base_username
        counter  = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1

        user = User(
            username=username, fullname=full_name, email=email,
            password=None, timezone='UTC', google_id=google_id
        )
        db.session.add(user)
        db.session.commit()
    else:
        # Existing user — attach google_id and email if they weren't set yet
        changed = False
        if not user.google_id:
            user.google_id = google_id
            changed = True
        if not user.email:
            user.email = email
            changed = True
        if changed:
            db.session.commit()

    session['username'] = user.username
    return jsonify({'success': True})

@app.route('/api/auth/supabase-config', methods=['GET'])
def api_supabase_config():
    """Returns public Supabase keys for the React frontend to initialize the Supabase JS SDK.
    These are the anon (public) keys — safe to expose to the browser."""
    return jsonify({
        'supabase_url':      os.getenv('SUPABASE_URL', ''),
        'supabase_anon_key': os.getenv('SUPABASE_ANON_KEY', ''),
    })

@app.route('/api/auth/me', methods=['GET'])
def api_auth_me():
    """Returns the logged-in user's basic info, or 401 if no session exists.
    The React app calls this on mount to check if the user is already logged in."""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'username':   user.username,
        'fullname':   user.fullname,
        'email':      user.email,
        'timezone':   user.timezone,
        'has_google': user.google_id is not None,
    })

@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    """Username/password login — sets the Flask session cookie on success."""
    data     = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    user = User.query.filter_by(username=username).first()
    if not user or not user.password or not bcrypt.check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid username or password'}), 401

    session['username'] = user.username
    return jsonify({'username': user.username, 'fullname': user.fullname})

@app.route('/api/auth/register', methods=['POST'])
def api_auth_register():
    """Creates a new user account and logs them in immediately."""
    data             = request.get_json()
    username         = data.get('username', '').strip()
    fullname         = data.get('fullname', '').strip()
    email            = data.get('email', '').strip()
    password         = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    timezone         = data.get('timezone', 'UTC')

    if not username or not fullname or not password or not email:
        return jsonify({'error': 'All fields are required'}), 400
    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400
    if timezone not in TIMEZONES:
        return jsonify({'error': 'Invalid timezone'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400

    hashed   = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, fullname=fullname, email=email, password=hashed, timezone=timezone)
    db.session.add(new_user)
    db.session.commit()
    session['username'] = new_user.username
    return jsonify({'username': new_user.username, 'fullname': new_user.fullname}), 201

@app.route('/api/auth/forgot-password', methods=['POST'])
def api_forgot_password():
    """Generates a 6-digit reset code, stores it in the session, and emails it to the user."""
    data  = request.get_json()
    email = (data.get('email') or '').strip()
    if not email:
        return jsonify({'error': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        # Don't reveal whether the email exists — prevents account enumeration
        return jsonify({'message': 'If that email is registered, a code has been sent.'}), 200

    # 60-second cooldown prevents email spam abuse
    last_sent = session.get('reset_code_sent_at')
    if last_sent and (time.time() - last_sent) < 60:
        remaining = int(60 - (time.time() - last_sent))
        return jsonify({'error': f'Please wait {remaining}s before requesting another code.'}), 429

    import random
    code = f"{random.randint(100000, 999999)}"
    session['reset_code']       = code
    session['reset_email']      = email
    session['reset_code_sent_at'] = time.time()
    session['reset_code_expiry']  = time.time() + 600  # code valid for 10 minutes
    send_reset_email(email, code)
    return jsonify({'message': 'If that email is registered, a code has been sent.'}), 200

@app.route('/api/auth/reset-password', methods=['POST'])
def api_reset_password():
    """Validates the reset code and updates the user's password."""
    data         = request.get_json()
    email        = (data.get('email') or '').strip()
    code         = (data.get('code') or '').strip()
    new_password = data.get('new_password', '')

    if not all([email, code, new_password]):
        return jsonify({'error': 'Email, code, and new password are required'}), 400
    if time.time() > session.get('reset_code_expiry', 0):
        return jsonify({'error': 'Code has expired. Please request a new one.'}), 400
    if code != session.get('reset_code') or email != session.get('reset_email'):
        return jsonify({'error': 'Invalid code. Please try again.'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Something went wrong. Please try again.'}), 400

    user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()
    # Clear the reset session keys so the code can't be reused
    for key in ('reset_code', 'reset_email', 'reset_code_sent_at', 'reset_code_expiry'):
        session.pop(key, None)
    return jsonify({'message': 'Password updated successfully.'})

@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    """Clears the Flask session, logging the user out."""
    session.pop('username', None)
    return jsonify({'success': True})

@app.route('/api/auth/delete-account', methods=['DELETE'])
def api_delete_account():
    """Permanently deletes the logged-in user's account and all their data.
    Deletes every row across all tables that references the username, then removes the User row."""
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401

    username = session['username']
    user     = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Cancel all pending reminder jobs before wiping DB rows
    for task in HomeworkTask.query.filter_by(username=username, is_completed=False).all():
        cancel_reminder(task.id, 'homework')

    # Delete all user data across every table
    StudySession.query.filter_by(username=username).delete()
    BreakEntry.query.filter_by(username=username).delete()
    HomeworkTask.query.filter_by(username=username).delete()
    Event.query.filter_by(username=username).delete()
    Message.query.filter_by(sender=username).delete()
    ConversationMember.query.filter_by(username=username).delete()
    Friendship.query.filter_by(sender=username).delete()
    Friendship.query.filter_by(receiver=username).delete()

    # If user was last member of a group, clean up the group + its conversation
    if user.group_id:
        remaining = User.query.filter_by(group_id=user.group_id).filter(User.username != username).count()
        if remaining == 0:
            group_conv = Conversation.query.filter_by(type='group', group_id=user.group_id).first()
            if group_conv:
                ConversationMember.query.filter_by(conversation_id=group_conv.id).delete()
                Message.query.filter_by(conversation_id=group_conv.id).delete()
                db.session.delete(group_conv)
            db.session.delete(StudyGroup.query.get(user.group_id))

    db.session.delete(user)
    db.session.commit()
    session.pop('username', None)
    return jsonify({'success': True})

@app.route('/api/auth/change-username', methods=['PUT'])
def api_change_username():
    """Changes the logged-in user's username.
    Because username is denormalized across many tables (plain string FK, no real FK constraint),
    this route bulk-updates every table in a single transaction before committing."""
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401

    data         = request.get_json()
    new_username = (data.get('username') or '').strip()
    old_username = session['username']

    if not new_username:
        return jsonify({'error': 'Username is required'}), 400
    if len(new_username) > 30:
        return jsonify({'error': 'Username must be 30 characters or fewer'}), 400
    if not re.match(r'^[a-zA-Z0-9_]+$', new_username):
        return jsonify({'error': 'Username can only contain letters, numbers, and underscores'}), 400
    if new_username == old_username:
        return jsonify({'error': 'That is already your username'}), 400
    if User.query.filter_by(username=new_username).first():
        return jsonify({'error': 'Username already taken'}), 400

    # Cascade the update across every table that stores username as a plain string
    User.query.filter_by(username=old_username).update({'username': new_username})
    StudySession.query.filter_by(username=old_username).update({'username': new_username})
    HomeworkTask.query.filter_by(username=old_username).update({'username': new_username})
    Event.query.filter_by(username=old_username).update({'username': new_username})
    BreakEntry.query.filter_by(username=old_username).update({'username': new_username})
    ConversationMember.query.filter_by(username=old_username).update({'username': new_username})
    Message.query.filter_by(sender=old_username).update({'sender': new_username})
    Friendship.query.filter_by(sender=old_username).update({'sender': new_username})
    Friendship.query.filter_by(receiver=old_username).update({'receiver': new_username})

    db.session.commit()
    session['username'] = new_username
    return jsonify({'username': new_username})

@app.route('/api/auth/set-password', methods=['PUT'])
def api_set_password():
    """Lets a Google-only user add a password to their account.
    Blocked if the account already has a password — use forgot-password to change an existing one."""
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401

    user = User.query.filter_by(username=session['username']).first()
    if user.password:
        return jsonify({'error': 'Account already has a password. Use forgot-password to change it.'}), 400

    data     = request.get_json()
    password = data.get('password', '')
    confirm  = data.get('confirm_password', '')

    if not password:
        return jsonify({'error': 'Password is required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if password != confirm:
        return jsonify({'error': 'Passwords do not match'}), 400

    user.password = bcrypt.generate_password_hash(password).decode('utf-8')
    db.session.commit()
    return jsonify({'has_password': True})

@app.route('/api/timezones', methods=['GET'])
def api_timezones():
    """Returns all pytz timezone strings — populates the timezone selector in Profile and Register."""
    return jsonify(TIMEZONES)

# =============================================================================
# Homework API Routes
# =============================================================================
# CRUD for HomeworkTask. All routes return JSON for the React frontend.
# Pattern for every protected route: auth check → ownership check → DB op → jsonify response.

@app.route('/api/homework', methods=['GET'])
def api_get_homework():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401

    tasks = HomeworkTask.query.filter_by(username=session['username']).order_by(HomeworkTask.due_date.asc()).all()

    # Convert SQLAlchemy model objects to plain dicts — jsonify() cannot serialize ORM objects directly
    return jsonify([{
        'id':           t.id,
        'course':       t.course,
        'task_name':    t.task_name,
        'description':  t.description,
        'due_date':     t.due_date.isoformat(),  # ISO string e.g. "2026-08-15T23:59:00" — easy to parse in JS
        'is_completed': t.is_completed,
        'is_important': t.is_important,
    } for t in tasks])

@app.route('/api/homework', methods=['POST'])
def api_create_homework():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    try:
        due_date = datetime.fromisoformat(data['due_date'])
    except (KeyError, ValueError):
        return jsonify({'error': 'Invalid due_date'}), 400

    task = HomeworkTask(
        username    = session['username'],
        course      = data.get('course', ''),
        task_name   = data.get('task_name', ''),
        description = data.get('description') or None,
        due_date    = due_date,
    )
    db.session.add(task)
    db.session.commit()
    
    # add a call to schedule_reminder if the user has reminders enabled
    user = User.query.filter_by(username=session['username']).first()
    if user.email_reminders:
        schedule_reminder(task.id, 'homework', task.due_date, user, name=f"{task.course}: {task.task_name}")

    # Return the created task so React can optimistically add it without re-fetching
    return jsonify({
        'id': task.id, 'course': task.course, 'task_name': task.task_name,
        'description': task.description, 'due_date': task.due_date.isoformat(),
        'is_completed': task.is_completed, 'is_important': task.is_important,
    }), 201

@app.route('/api/homework/<int:task_id>/complete', methods=['POST'])
def api_complete_task(task_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    task = HomeworkTask.query.get_or_404(task_id)
    if task.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403
    task.is_completed = not task.is_completed  # toggle
    db.session.commit()
    
    # cancel the reminder when a task is marked complete
    if task.is_completed:
        cancel_reminder(task.id, 'homework')
    else:
        # reschedule the reminder when task is toggled back to incomplete
        user = User.query.filter_by(username=session['username']).first()
        if user.email_reminders:
            schedule_reminder(task.id, 'homework', task.due_date, user, name=f"{task.course}: {task.task_name}")

    return jsonify({'id': task.id, 'is_completed': task.is_completed})

@app.route('/api/homework/<int:task_id>/importance', methods=['POST'])
def api_toggle_task_importance(task_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    task = HomeworkTask.query.get_or_404(task_id)
    if task.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403
    task.is_important = not task.is_important  # toggle
    db.session.commit()
    return jsonify({'id': task.id, 'is_important': task.is_important})

@app.route('/api/homework/<int:task_id>', methods=['DELETE'])
def api_delete_task(task_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    task = HomeworkTask.query.get_or_404(task_id)
    if task.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403
    db.session.delete(task)
    db.session.commit()
    
    # cancel the reminder
    cancel_reminder(task.id, 'homework')
    
    return jsonify({'success': True})

@app.route('/api/homework/<int:task_id>', methods=['PUT'])
def api_edit_task(task_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    task = HomeworkTask.query.get_or_404(task_id)
    if task.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json()
    task.course      = data.get('course', task.course)
    task.task_name   = data.get('task_name', task.task_name)
    task.description = data.get('description') or None
    try:
        task.due_date = datetime.fromisoformat(data['due_date'])
    except (KeyError, ValueError):
        return jsonify({'error': 'Invalid due_date'}), 400

    db.session.commit()
    
    # cancel old job and reschedule with the new due date (if changed)
    cancel_reminder(task.id, 'homework')
    user = User.query.filter_by(username=session['username']).first()
    if user.email_reminders:
        schedule_reminder(task.id, 'homework', task.due_date, user, name=f"{task.course}: {task.task_name}")

    return jsonify({
        'id': task.id, 'course': task.course, 'task_name': task.task_name,
        'description': task.description, 'due_date': task.due_date.isoformat(),
        'is_completed': task.is_completed, 'is_important': task.is_important,
    })

# =============================================================================
# Events API Routes
# =============================================================================

@app.route('/api/events', methods=['GET'])
def api_get_events():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    events = Event.query.filter_by(username=session['username']).order_by(Event.start_datetime.asc()).all()
    return jsonify([{
        'id':             e.id,
        'event_name':     e.event_name,
        'start_datetime': e.start_datetime.isoformat(),
        'end_datetime':   e.end_datetime.isoformat(),
        'location':       e.location,
        'description':    e.description,
        'is_completed':   e.is_completed,
        'is_important':   e.is_important,
    } for e in events])

@app.route('/api/events', methods=['POST'])
def api_create_event():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json()
    try:
        start = datetime.fromisoformat(data['start_datetime'])
        end   = datetime.fromisoformat(data['end_datetime'])
    except (KeyError, ValueError):
        return jsonify({'error': 'Invalid datetimes'}), 400
    if start >= end:
        return jsonify({'error': 'Start must be before end'}), 400

    event = Event(
        username       = session['username'],
        event_name     = data.get('event_name', ''),
        start_datetime = start, end_datetime = end,
        location       = data.get('location') or None,
        description    = data.get('description') or None,
    )
    db.session.add(event)
    db.session.commit()

    return jsonify({
        'id': event.id, 'event_name': event.event_name,
        'start_datetime': event.start_datetime.isoformat(),
        'end_datetime':   event.end_datetime.isoformat(),
        'location': event.location, 'description': event.description,
        'is_completed': event.is_completed, 'is_important': event.is_important,
    }), 201

@app.route('/api/events/<int:event_id>/complete', methods=['POST'])
def api_complete_event(event_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    event = Event.query.get_or_404(event_id)
    if event.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403
    event.is_completed = not event.is_completed
    db.session.commit()

    return jsonify({'id': event.id, 'is_completed': event.is_completed})

@app.route('/api/events/<int:event_id>/importance', methods=['POST'])
def api_toggle_event_importance(event_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    event = Event.query.get_or_404(event_id)
    if event.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403
    event.is_important = not event.is_important
    db.session.commit()
    return jsonify({'id': event.id, 'is_important': event.is_important})

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
def api_delete_event(event_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    event = Event.query.get_or_404(event_id)
    if event.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403
    db.session.delete(event)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/events/<int:event_id>', methods=['PUT'])
def api_edit_event(event_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    event = Event.query.get_or_404(event_id)
    if event.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json()
    event.event_name  = data.get('event_name', event.event_name)
    event.location    = data.get('location') or None
    event.description = data.get('description') or None
    try:
        event.start_datetime = datetime.fromisoformat(data['start_datetime'])
        event.end_datetime   = datetime.fromisoformat(data['end_datetime'])
    except (KeyError, ValueError):
        return jsonify({'error': 'Invalid datetime'}), 400
    db.session.commit()
    return jsonify({
        'id': event.id, 'event_name': event.event_name,
        'start_datetime': event.start_datetime.isoformat(),
        'end_datetime':   event.end_datetime.isoformat(),
        'location': event.location, 'description': event.description,
        'is_completed': event.is_completed, 'is_important': event.is_important,
    })

# =============================================================================
# Breaks API Routes
# =============================================================================

@app.route('/api/breaks', methods=['GET'])
def api_get_breaks():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    breaks = BreakEntry.query.filter_by(username=session['username']).order_by(BreakEntry.start_datetime.desc()).all()
    return jsonify([{
        'id':             b.id,
        # 'Z' suffix tells JS Date that this is UTC, so it converts to the user's local time automatically
        'start_datetime': b.start_datetime.isoformat() + 'Z',
        'end_datetime':   b.end_datetime.isoformat() + 'Z',
    } for b in breaks])

@app.route('/api/breaks', methods=['POST'])
def api_create_break():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json()
    try:
        start = datetime.fromisoformat(data['start_datetime'])
        end   = datetime.fromisoformat(data['end_datetime'])
    except (KeyError, ValueError):
        return jsonify({'error': 'Invalid datetimes'}), 400
    entry = BreakEntry(username=session['username'], start_datetime=start, end_datetime=end)
    db.session.add(entry)
    db.session.commit()
    return jsonify({
        'id':             entry.id,
        'start_datetime': entry.start_datetime.isoformat() + 'Z',
        'end_datetime':   entry.end_datetime.isoformat() + 'Z',
    }), 201

@app.route('/api/breaks/<int:break_id>', methods=['DELETE'])
def api_delete_break(break_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    entry = BreakEntry.query.get_or_404(break_id)
    if entry.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'success': True})

# =============================================================================
# Study Sessions API Routes
# =============================================================================

@app.route('/api/sessions', methods=['GET'])
def api_get_sessions():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    sessions_list = StudySession.query.filter_by(username=session['username']).order_by(StudySession.start_datetime.desc()).all()
    return jsonify([{
        'id':             s.id,
        'course':         s.course,
        'topic':          s.topic,
        'start_datetime': s.start_datetime.isoformat() + 'Z',
        'end_datetime':   s.end_datetime.isoformat() + 'Z',
        'notes':          s.notes,
        'is_important':   s.is_important,
    } for s in sessions_list])

@app.route('/api/sessions', methods=['POST'])
def api_create_session():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json()
    try:
        start = datetime.fromisoformat(data['start_datetime'])
        end   = datetime.fromisoformat(data['end_datetime'])
    except (KeyError, ValueError):
        return jsonify({'error': 'Invalid datetimes'}), 400
    s = StudySession(
        username       = session['username'],
        course         = data.get('course', ''),
        topic          = data.get('topic') or None,
        start_datetime = start, end_datetime = end,
        notes          = data.get('notes') or None,
    )
    db.session.add(s)
    db.session.commit()
    return jsonify({
        'id': s.id, 'course': s.course, 'topic': s.topic,
        'start_datetime': s.start_datetime.isoformat() + 'Z',
        'end_datetime':   s.end_datetime.isoformat() + 'Z',
        'notes': s.notes, 'is_important': s.is_important,
    }), 201

@app.route('/api/sessions/<int:session_id>', methods=['DELETE'])
def api_delete_session(session_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    s = StudySession.query.get_or_404(session_id)
    if s.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403
    db.session.delete(s)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/sessions/<int:session_id>/importance', methods=['POST'])
def api_toggle_session_importance(session_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    s = StudySession.query.get_or_404(session_id)
    if s.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403
    s.is_important = not s.is_important
    db.session.commit()
    return jsonify({'id': s.id, 'is_important': s.is_important})

# =============================================================================
# Notes API Routes
# =============================================================================
# Notes are study sessions that have notes text.
# "Deleting" a note is a soft delete — hidden_from_notes=True hides it from the Notes page
# but preserves the row so the study time still appears in Summary stats.

@app.route('/api/notes', methods=['GET'])
def api_get_notes():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    # Only return sessions where the note hasn't been soft-deleted
    notes_list = StudySession.query.filter_by(
        username=session['username'], hidden_from_notes=False
    ).order_by(StudySession.start_datetime.desc()).all()
    return jsonify([{
        'id': n.id, 'course': n.course, 'topic': n.topic,
        'start_datetime': n.start_datetime.isoformat() + 'Z',
        'end_datetime':   n.end_datetime.isoformat() + 'Z',
        'notes': n.notes, 'is_important': n.is_important,
    } for n in notes_list])

@app.route('/api/notes/<int:session_id>/importance', methods=['POST'])
def api_toggle_note_importance(session_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    s = StudySession.query.get_or_404(session_id)
    if s.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403
    s.is_important = not s.is_important
    db.session.commit()
    return jsonify({'id': s.id, 'is_important': s.is_important})

@app.route('/api/notes/<int:session_id>', methods=['PUT'])
def api_edit_note(session_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    s = StudySession.query.get_or_404(session_id)
    if s.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json()
    if 'course' in data:
        s.course = data['course']
    if 'topic' in data:
        s.topic = data['topic'] or None
    if 'notes' in data:
        s.notes = data['notes'] or None
    db.session.commit()
    return jsonify({
        'id': s.id, 'course': s.course, 'topic': s.topic,
        'notes': s.notes, 'is_important': s.is_important,
    })

@app.route('/api/notes/<int:session_id>', methods=['DELETE'])
def api_delete_note(session_id):
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    s = StudySession.query.get_or_404(session_id)
    if s.username != session['username']:
        return jsonify({'error': 'Forbidden'}), 403
    # Soft delete: hide from notes view but keep row intact to preserve study time data
    s.hidden_from_notes = True
    s.notes = None
    db.session.commit()
    return jsonify({'success': True})

# =============================================================================
# Profile API Routes
# =============================================================================

@app.route('/api/profile', methods=['GET'])
def api_get_profile():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    user = User.query.filter_by(username=session['username']).first()
    return jsonify({
        'username':        user.username,
        'fullname':        user.fullname,
        'email':           user.email,
        'timezone':        user.timezone,
        'has_google':      user.google_id is not None,
        'has_password':    user.password is not None,
        'email_reminders': user.email_reminders,
    })

@app.route('/api/profile', methods=['PUT'])
def api_update_profile():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    user = User.query.filter_by(username=session['username']).first()
    data = request.get_json()

    if data.get('fullname'):
        user.fullname = data['fullname'].strip()

    if data.get('timezone'):
        if data['timezone'] not in TIMEZONES:
            return jsonify({'error': 'Invalid timezone'}), 400
        user.timezone = data['timezone']

    # Email can only be added — once set it's locked to prevent accidental account unlinking
    if data.get('email') and not user.email:
        existing = User.query.filter_by(email=data['email']).first()
        if existing:
            return jsonify({'error': 'Email already linked to another account'}), 400
        user.email = data['email'].strip()

    # Reminder toggle — block enabling without a valid email address
    if 'email_reminders' in data:
        if data['email_reminders'] and not user.email:
            return jsonify({'error': 'Set an email address before enabling reminders'}), 400
        user.email_reminders = bool(data['email_reminders'])

    db.session.commit()

    # When toggling reminders, sync scheduled jobs for all existing incomplete tasks
    if 'email_reminders' in data:
        upcoming_tasks = HomeworkTask.query.filter_by(username=user.username, is_completed=False).all()
        for task in upcoming_tasks:
            if user.email_reminders:
                schedule_reminder(task.id, 'homework', task.due_date, user, name=f"{task.course}: {task.task_name}")
            else:
                cancel_reminder(task.id, 'homework')
    return jsonify({
        'username': user.username, 'fullname': user.fullname,
        'email': user.email, 'timezone': user.timezone,
        'has_google': user.google_id is not None,
        'has_password': user.password is not None,
        'email_reminders': user.email_reminders,
    })

@app.route('/api/user/<username>', methods=['GET'])
def api_public_profile(username):
    """Public profile — no auth required. Returns stats + heatmap for any user by username."""
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    sessions      = StudySession.query.filter_by(username=username).order_by(StudySession.start_datetime).all()
    total_minutes = sum(
        int((s.end_datetime - s.start_datetime).total_seconds() / 60)
        for s in sessions
    )

    # This week's study — convert the user's local Monday midnight to UTC so sessions
    # stored as naive UTC are correctly included regardless of the user's timezone.
    profile_tz = user.timezone or 'UTC'
    try:
        _profile_tz_obj = pytz.timezone(profile_tz)
    except pytz.UnknownTimeZoneError:
        _profile_tz_obj = pytz.UTC
    today = datetime.now(pytz.utc).astimezone(_profile_tz_obj).date()
    week_start_local = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    week_start_utc   = _profile_tz_obj.localize(week_start_local).astimezone(pytz.utc).replace(tzinfo=None)
    week_mins  = sum(
        int((s.end_datetime - s.start_datetime).total_seconds() / 60)
        for s in sessions
        if s.start_datetime >= week_start_utc
    )

    # GitHub-style heatmap: daily aggregated hours for the last 365 days.
    # Use calculate_duration_mins to correctly distribute sessions that span midnight.
    heatmap_start = today - timedelta(days=364)
    daily_study: dict = {}
    for s in sessions:
        day = s.start_datetime.date()
        last_day = min(s.end_datetime.date(), today)
        while day <= last_day:
            if day >= heatmap_start:
                mins = calculate_duration_mins(s.start_datetime, s.end_datetime, day)
                daily_study[day] = daily_study.get(day, 0) + mins
            day += timedelta(days=1)
    heatmap = [
        {
            'date':  (heatmap_start + timedelta(days=i)).strftime('%Y-%m-%d'),
            # Cap at 24h/day — anything above indicates corrupted session data
            'hours': min(round(daily_study.get(heatmap_start + timedelta(days=i), 0) / 60, 2), 24.0),
        }
        for i in range(365)
    ]

    group_name = None
    if user.group_id:
        group = StudyGroup.query.get(user.group_id)
        group_name = group.name if group else None

    # Streak: current = consecutive days ending today; longest = all-time max run
    current_streak = 0
    longest_streak = 0
    if daily_study:
        check = today
        while daily_study.get(check, 0) > 0:
            current_streak += 1
            check -= timedelta(days=1)
        run  = 0
        scan = min(daily_study.keys())
        while scan <= today:
            if daily_study.get(scan, 0) > 0:
                run += 1
                if run > longest_streak:
                    longest_streak = run
            else:
                run = 0
            scan += timedelta(days=1)

    return jsonify({
        'username':        user.username,
        'fullname':        user.fullname,
        'total_sessions':  len(sessions),
        'total_hours':     round(total_minutes / 60, 1),
        'this_week_hours': round(week_mins / 60, 1),
        'current_streak':  current_streak,
        'longest_streak':  longest_streak,
        'group_name':      group_name,
        'heatmap':         heatmap,
    })

# =============================================================================
# Study Groups API Routes
# =============================================================================
# One group per user (enforced by User.group_id FK).
# When a group is created or joined, a linked Conversation is created atomically
# so group members can chat immediately without extra setup.
# Groups created before the chat feature are handled by lazy-creating their Conversation
# on first access (see api_group_me and api_join_group).

@app.route('/api/groups/me', methods=['GET'])
def api_group_me():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    user = User.query.filter_by(username=session['username']).first()
    if not user.group_id:
        return jsonify({'group': None})

    group   = StudyGroup.query.get(user.group_id)
    members = [u.username for u in User.query.filter_by(group_id=group.id).all()]

    # Lazy-create the conversation if this group predates the chat feature
    conv = Conversation.query.filter_by(type='group', group_id=group.id).first()
    if not conv:
        conv = Conversation(type='group', group_id=group.id)
        db.session.add(conv)
        db.session.flush()  # get conv.id before committing so we can add members
        for m in User.query.filter_by(group_id=group.id).all():
            db.session.add(ConversationMember(conversation_id=conv.id, username=m.username))
        db.session.commit()

    return jsonify({'group': {
        'id': group.id, 'name': group.name,
        'join_code': group.join_code,
        'members': members, 'conv_id': conv.id,
    }})

@app.route('/api/groups/create', methods=['POST'])
def api_create_group():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    data       = request.get_json()
    group_name = (data.get('group_name') or '').strip()
    if not group_name:
        return jsonify({'error': 'Group name is required'}), 400

    # Retry until we get a join code not already in use
    while True:
        code = generate_join_code()
        if not StudyGroup.query.filter_by(join_code=code).first():
            break

    user      = User.query.filter_by(username=session['username']).first()
    new_group = StudyGroup(name=group_name, join_code=code)
    db.session.add(new_group)
    db.session.flush()  # assigns new_group.id without committing
    user.group_id = new_group.id

    # Create the group conversation and add creator as first member — all in one transaction
    conv = Conversation(type='group', group_id=new_group.id)
    db.session.add(conv)
    db.session.flush()
    db.session.add(ConversationMember(conversation_id=conv.id, username=user.username))
    db.session.commit()
    return jsonify({'name': new_group.name, 'join_code': new_group.join_code}), 201

@app.route('/api/groups/join', methods=['POST'])
def api_join_group():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401
    data      = request.get_json()
    join_code = (data.get('join_code') or '').upper().strip()
    if not join_code:
        return jsonify({'error': 'Join code is required'}), 400

    group = StudyGroup.query.filter_by(join_code=join_code).first()
    if not group:
        return jsonify({'error': 'Invalid join code'}), 404

    user          = User.query.filter_by(username=session['username']).first()
    user.group_id = group.id
    db.session.commit()

    # Add user to the group chat conversation.
    # If no conversation exists yet (legacy group), create it and add all current members.
    conv = Conversation.query.filter_by(type='group', group_id=group.id).first()
    if not conv:
        conv = Conversation(type='group', group_id=group.id)
        db.session.add(conv)
        db.session.flush()
        for m in User.query.filter_by(group_id=group.id).all():
            db.session.add(ConversationMember(conversation_id=conv.id, username=m.username))
    else:
        # Conversation exists — just add this user if they aren't already a member
        already_member = ConversationMember.query.filter_by(
            conversation_id=conv.id, username=user.username).first()
        if not already_member:
            db.session.add(ConversationMember(conversation_id=conv.id, username=user.username))
    db.session.commit()
    return jsonify({'name': group.name, 'join_code': group.join_code})

@app.route('/api/groups/leave', methods=['POST'])
def api_leave_group():
    """Removes the user from their group. Auto-deletes the group and conversation
    when the last member leaves."""
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401

    user     = User.query.filter_by(username=session['username']).first()
    group_id = user.group_id
    username = user.username
    user.group_id = None
    db.session.commit()

    if group_id:
        conv = Conversation.query.filter_by(type='group', group_id=group_id).first()
        if conv:
            # Remove this user from the group conversation
            member_row = ConversationMember.query.filter_by(
                conversation_id=conv.id, username=username).first()
            if member_row:
                db.session.delete(member_row)

        remaining = User.query.filter_by(group_id=group_id).count()
        if remaining == 0:
            # Last member left — clean up the group and all associated chat data
            group = StudyGroup.query.get(group_id)
            if group:
                db.session.delete(group)
            if conv:
                ConversationMember.query.filter_by(conversation_id=conv.id).delete()
                db.session.delete(conv)
        db.session.commit()
    return jsonify({'success': True})

# =============================================================================
# Calendar API Route
# =============================================================================

@app.route('/api/calendar', methods=['GET'])
def api_calendar_data():
    """Returns homework tasks and events formatted for FullCalendar's EventInput schema.
    Colors encode status: green = completed, red = overdue, amber = upcoming (tasks),
    purple = upcoming (events)."""
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401

    username = session['username']
    now      = get_current_datetime(get_user_timezone(username))
    tasks    = HomeworkTask.query.filter_by(username=username).all()
    events   = Event.query.filter_by(username=username).all()

    calendar_events = []

    for task in tasks:
        color = '#48bb78' if task.is_completed else ('#e53e3e' if task.due_date < now else '#f59e0b')
        calendar_events.append({
            'id':              f'task-{task.id}',
            'title':           f"{task.course}: {task.task_name}",
            'start':           task.due_date.isoformat(),
            'backgroundColor': color,
            'borderColor':     color,
            'textColor':       '#fff',
            'display':         'list-item',
            'extendedProps': {
                'type': 'task', 'completed': task.is_completed,
                'description': task.description or '',
                'deadline': task.due_date.strftime('%B %d, %Y at %I:%M %p'),
            }
        })

    for event in events:
        end_dt = event.end_datetime
        # FullCalendar treats midnight as the end of the previous day —
        # nudge by 1 minute to keep events that end exactly at midnight visible on the right day
        if end_dt.hour == 0 and end_dt.minute == 0:
            end_dt = end_dt + timedelta(minutes=1)
        calendar_events.append({
            'id':              f'event-{event.id}',
            'title':           event.event_name,
            'start':           event.start_datetime.isoformat(),
            'end':             end_dt.isoformat(),
            'backgroundColor': '#48bb78' if event.is_completed else '#667eea',
            'borderColor':     '#38a169' if event.is_completed else '#5568d3',
            'textColor':       '#fff',
            'display':         'block',
            'extendedProps': {
                'type': 'event', 'completed': event.is_completed,
                'location': event.location or '', 'description': event.description or '',
            }
        })

    calendar_events.sort(key=lambda e: e['start'])
    return jsonify(calendar_events)

# =============================================================================
# Summary API Route
# =============================================================================
# Most complex route in the app. Computes:
#   - Leaderboard: weekly study/break hours for the user + all group members
#   - Daily bar chart: per-day study/break hours (handles midnight-spanning sessions)
#   - Course pie chart: total study time broken down by course
#   - Heatmap: study hours per day from Jan 1 of the earliest year with data to today
#   - Streaks: current and longest consecutive study days

@app.route('/api/summary', methods=['GET'])
def api_summary_data():
    current_username = session.get('username')
    if not current_username:
        return jsonify({'error': 'Not logged in'}), 401

    current_user = User.query.filter_by(username=current_username).first()
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    user_tz       = get_user_timezone(current_username)
    today         = get_current_date(user_tz)
    today_start_dt = datetime.combine(today, datetime.min.time())
    today_end_dt   = today_start_dt + timedelta(days=1)
    week_start    = today - timedelta(days=today.weekday())  # Monday of the current week

    # Sessions are stored as naive UTC. Convert today's local midnight boundaries to UTC
    # so "today" filters correctly for users in non-UTC timezones (e.g. EDT sessions done
    # after 8pm local appear as next-day UTC and were being excluded from "Studied today").
    try:
        _tz_obj = pytz.timezone(user_tz)
    except pytz.UnknownTimeZoneError:
        _tz_obj = pytz.UTC
    today_start_utc = _tz_obj.localize(today_start_dt).astimezone(pytz.utc).replace(tzinfo=None)
    today_end_utc   = _tz_obj.localize(today_end_dt).astimezone(pytz.utc).replace(tzinfo=None)
    week_start_utc  = _tz_obj.localize(
        datetime.combine(week_start, datetime.min.time())
    ).astimezone(pytz.utc).replace(tzinfo=None)

    has_group  = current_user.group_id is not None
    group_info = None

    if has_group:
        group      = StudyGroup.query.get(current_user.group_id)
        group_info = {'name': group.name, 'join_code': group.join_code}
        all_users  = User.query.filter_by(group_id=current_user.group_id).all()
    else:
        all_users = [current_user]

    # Ensure current user is always first in the leaderboard
    if current_user in all_users:
        all_users.remove(current_user)
    all_users.insert(0, current_user)

    friend_names, friend_usernames, friend_study_hours, friend_break_hours = [], [], [], []
    friend_today_study, friend_today_break = [], []

    for user in all_users:
        user_sessions = StudySession.query.filter_by(username=user.username).filter(
            StudySession.start_datetime >= week_start_utc
        ).all()
        user_breaks = BreakEntry.query.filter_by(username=user.username).filter(
            BreakEntry.start_datetime >= week_start_utc
        ).all()
        total_study_mins = sum((s.end_datetime - s.start_datetime).total_seconds() / 60.0 for s in user_sessions)
        total_break_mins = sum((b.end_datetime - b.start_datetime).total_seconds() / 60.0 for b in user_breaks)

        # For "today" stats, use UTC boundaries so sessions stored as naive UTC are
        # correctly matched to the user's local calendar day.
        user_today_sessions = StudySession.query.filter_by(username=user.username).filter(
            StudySession.start_datetime < today_end_utc, StudySession.end_datetime >= today_start_utc
        ).all()
        user_today_breaks = BreakEntry.query.filter_by(username=user.username).filter(
            BreakEntry.start_datetime < today_end_utc, BreakEntry.end_datetime >= today_start_utc
        ).all()
        # Clip each session to the UTC window for today so overnight sessions don't double-count
        today_study = sum(
            (min(s.end_datetime, today_end_utc) - max(s.start_datetime, today_start_utc)).total_seconds() / 60.0
            for s in user_today_sessions
        )
        today_break = sum(
            (min(b.end_datetime, today_end_utc) - max(b.start_datetime, today_start_utc)).total_seconds() / 60.0
            for b in user_today_breaks
        )

        friend_names.append(user.fullname)
        friend_usernames.append(user.username)
        friend_study_hours.append(round(total_study_mins / 60, 2))
        friend_break_hours.append(round(total_break_mins / 60, 2))
        friend_today_study.append(round(today_study / 60, 2))
        friend_today_break.append(round(today_break / 60, 2))

    # Sort leaderboard by weekly study hours (descending) — zip keeps the lists aligned
    sorted_data = sorted(
        zip(friend_study_hours, friend_break_hours, friend_names, friend_usernames, friend_today_study, friend_today_break),
        reverse=True
    )
    if sorted_data:
        friend_study_hours, friend_break_hours, friend_names, friend_usernames, friend_today_study, friend_today_break = map(list, zip(*sorted_data))

    my_sessions = StudySession.query.filter_by(username=current_username).order_by(StudySession.start_datetime).all()
    my_breaks   = BreakEntry.query.filter_by(username=current_username).order_by(BreakEntry.start_datetime).all()

    daily_study = defaultdict(float)
    daily_break = defaultdict(float)

    # Walk each session day-by-day to correctly split sessions that span midnight
    for s in my_sessions:
        current = s.start_datetime
        while current < s.end_datetime:
            next_day    = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_chunk = min(s.end_datetime, next_day)
            daily_study[current.date()] += (end_of_chunk - current).total_seconds() / 3600.0
            current = end_of_chunk

    for b in my_breaks:
        current = b.start_datetime
        while current < b.end_datetime:
            next_day    = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_chunk = min(b.end_datetime, next_day)
            daily_break[current.date()] += (end_of_chunk - current).total_seconds() / 3600.0
            current = end_of_chunk

    first_date = None
    if daily_study or daily_break:
        first_date = min(list(daily_study.keys()) + list(daily_break.keys()))
        last_date  = max(list(daily_study.keys()) + list(daily_break.keys()))
        total_days = (last_date - first_date).days + 1
        daily_labels       = [(first_date + timedelta(days=i)).strftime('%b %d') for i in range(total_days)]
        daily_study_values = [round(daily_study.get(first_date + timedelta(days=i), 0), 2) for i in range(total_days)]
        daily_break_values = [round(daily_break.get(first_date + timedelta(days=i), 0), 2) for i in range(total_days)]
    else:
        daily_labels, daily_study_values, daily_break_values = [], [], []

    # Streak: count consecutive days with study time ending at today, then scan all history for longest run
    current_streak = 0
    longest_streak = 0
    if daily_study:
        check = today
        while daily_study.get(check, 0) > 0:
            current_streak += 1
            check -= timedelta(days=1)

        run  = 0
        scan = min(daily_study.keys())
        while scan <= today:
            if daily_study.get(scan, 0) > 0:
                run += 1
                if run > longest_streak:
                    longest_streak = run
            else:
                run = 0
            scan += timedelta(days=1)

    # Heatmap starts from Jan 1 of the first year with data so the frontend can
    # filter by full calendar year rather than just rolling 365 days
    heatmap_start     = first_date.replace(month=1, day=1) if first_date else today.replace(month=1, day=1)
    total_heatmap_days = (today - heatmap_start).days + 1
    heatmap_data = [
        {
            'date':  (heatmap_start + timedelta(days=i)).strftime('%Y-%m-%d'),
            'hours': round(daily_study.get(heatmap_start + timedelta(days=i), 0), 2),
        }
        for i in range(total_heatmap_days)
    ]

    # All-time course breakdown for the pie chart
    course_totals = defaultdict(float)
    for s in my_sessions:
        course_totals[s.course] += (s.end_datetime - s.start_datetime).total_seconds() / 60.0

    # Today's stats for the summary cards — use UTC boundaries (see comment above)
    today_sessions_q = StudySession.query.filter_by(username=current_username).filter(
        StudySession.start_datetime < today_end_utc, StudySession.end_datetime >= today_start_utc
    ).all()
    today_breaks_q = BreakEntry.query.filter_by(username=current_username).filter(
        BreakEntry.start_datetime < today_end_utc, BreakEntry.end_datetime >= today_start_utc
    ).all()
    today_course_totals = defaultdict(float)
    for s in today_sessions_q:
        today_course_totals[s.course] += (
            min(s.end_datetime, today_end_utc) - max(s.start_datetime, today_start_utc)
        ).total_seconds() / 60.0
    today_study_mins = sum(
        (min(s.end_datetime, today_end_utc) - max(s.start_datetime, today_start_utc)).total_seconds() / 60.0
        for s in today_sessions_q
    )
    today_break_mins = sum(
        (min(b.end_datetime, today_end_utc) - max(b.start_datetime, today_start_utc)).total_seconds() / 60.0
        for b in today_breaks_q
    )

    return jsonify({
        'current_username': current_username,
        'current_fullname': current_user.fullname,
        'has_group':         has_group,
        'group_info':        group_info,
        'friend_names':      friend_names,
        'friend_usernames':  friend_usernames,
        'friend_study_hours': friend_study_hours,
        'friend_break_hours': friend_break_hours,
        'friend_today_study': friend_today_study,
        'friend_today_break': friend_today_break,
        'course_labels':      list(course_totals.keys()),
        'course_hours':       [round(m / 60, 2) for m in course_totals.values()],
        'daily_labels':       daily_labels,
        'daily_study_values': daily_study_values,
        'daily_break_values': daily_break_values,
        'today_course_labels': list(today_course_totals.keys()),
        'today_course_hours':  [round(m / 60, 2) for m in today_course_totals.values()],
        'today_study_hours':   round(today_study_mins / 60, 2),
        'today_break_hours':   round(today_break_mins / 60, 2),
        'heatmap_data':        heatmap_data,
        'current_streak':      current_streak,
        'longest_streak':      longest_streak,
    })

# =============================================================================
# AI Parse Route
# =============================================================================
# Sends raw syllabus/schedule text to Gemini and returns structured tasks/events.
# The frontend shows these as editable preview cards before the user confirms creation.
# Rate-limited to 1 parse per user per day (in their local timezone) to stay within
# Gemini's free API quota.

@app.route('/api/parse', methods=['POST'])
def api_parse():
    if session.get('username') is None:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    if len(text) > 20000:
        return jsonify({'error': 'Input too long — maximum 20000 characters.'}), 400

    username   = session['username']
    user       = User.query.filter_by(username=username).first()
    today_date = get_current_date(get_user_timezone(username))

    # Reset the daily counter when the user's local date changes
    if user.parse_date != today_date:
        user.parse_count = 0
        user.parse_date  = today_date

    if user.parse_count >= 1:
        return jsonify({'error': 'Daily limit reached — you can use Import once per day.'}), 429

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return jsonify({'error': 'GEMINI_API_KEY not set in app.env'}), 500

    today     = get_current_datetime(get_user_timezone(username))
    today_str = today.strftime('%A, %B %d, %Y')

    prompt = f"""Today is {today_str}.

Extract all homework tasks and calendar events from the text below.
Return a JSON object with an "items" array.

Each item must have:
  "type": "task" or "event"

For a task (assignment, quiz, exam due date, homework):
  "type": "task"
  "course": string (course code or name, e.g. "COMP 101") — use null if unknown
  "task_name": string
  "description": string or null
  "due_date": ISO 8601 datetime string or null (e.g. "2026-09-15T23:59:00") — if no time given, use 23:59:00

For an event (lecture, lab, meeting, exam at a specific time):
  "type": "event"
  "event_name": string
  "start_datetime": ISO 8601 datetime string or null — FIRST occurrence only
  "end_datetime": ISO 8601 datetime string or null (if duration not given, assume 1 hour after start) — FIRST occurrence only
  "location": string or null
  "description": string or null
  "recurrence": object or null — include ONLY for recurring events:
    "days": array of day abbreviations the event repeats on, e.g. ["Tue", "Thu"] (use Mon/Tue/Wed/Thu/Fri/Sat/Sun)
    "until": ISO date string YYYY-MM-DD — last date of the recurrence range

Rules:
- If year is not specified, assume {today.year} or {today.year + 1} based on context (e.g. a date that has already passed this year → next year).
- Recurring events: set start_datetime/end_datetime to the FIRST occurrence only, and populate "recurrence". Do NOT generate multiple items for recurring events.
- Non-recurring events: omit "recurrence" entirely (or set to null).
- If something could be either type, make your best guess.
- Keep description fields SHORT (under 100 characters). Omit redundant or low-value details.
- Omit null fields entirely rather than including them as null.

Text:
{text}"""

    try:
        client   = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type='application/json',
                max_output_tokens=8192,
            ),
        )
        import json
        raw = response.text.strip()

        # Strip markdown fences in case Gemini wraps the JSON in ```json ... ``` despite the mime type
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw[3:]
        if raw.endswith('```'):
            raw = raw.rsplit('```', 1)[0]

        try:
            parsed = json.loads(raw.strip())
        except json.JSONDecodeError as je:
            preview = raw[:300].replace('\n', ' ')
            return jsonify({'error': f'Gemini returned invalid JSON: {je}. Response preview: {preview}'}), 500

        items = parsed.get('items', [])
        # Only accept items with a recognized type — discard anything malformed
        valid = [item for item in items if item.get('type') in ('task', 'event')]

        # Count against the limit only on a successful parse (not on Gemini errors)
        user.parse_count += 1
        db.session.commit()

        return jsonify({'items': valid})

    except Exception as e:
        return jsonify({'error': f'Parse failed: {str(e)}'}), 500

# =============================================================================
# Friends API Routes
# =============================================================================
# Friendship has two states: 'pending' (request sent, not yet accepted) and 'accepted'.
# The sender is the user who sent the request; the receiver is who they sent it to.

@app.route('/api/friends', methods=['GET'])
def api_get_friends():
    """Returns the user's accepted friends and their pending incoming requests."""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401

    # filter() with OR conditions — needed because sender/receiver can be in either column
    accepted = Friendship.query.filter(
        ((Friendship.sender == username) | (Friendship.receiver == username)),
        Friendship.status == 'accepted'
    ).all()

    # Only incoming pending requests (receiver == me) are shown — outgoing ones aren't actionable here
    pending = Friendship.query.filter(
        Friendship.receiver == username,
        Friendship.status == 'pending'
    ).all()

    def friend_name(f):
        # Returns the other person's username regardless of who sent the request
        return f.receiver if f.sender == username else f.sender

    return jsonify({
        'friends': [{'id': f.id, 'username': friend_name(f)} for f in accepted],
        'pending': [{'id': f.id, 'from': f.sender} for f in pending],
    })

@app.route('/api/friends/request', methods=['POST'])
def api_send_friend_request():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401

    data   = request.get_json()
    target = data.get('username', '').strip()
    if not target or target == username:
        return jsonify({'error': 'Invalid target'}), 400

    if not User.query.filter_by(username=target).first():
        return jsonify({'error': 'User not found'}), 404

    # Check both directions — a request either way already exists
    existing = Friendship.query.filter(
        ((Friendship.sender == username) & (Friendship.receiver == target)) |
        ((Friendship.sender == target) & (Friendship.receiver == username))
    ).first()
    if existing:
        return jsonify({'error': 'Request already exists'}), 409

    f = Friendship(sender=username, receiver=target, status='pending')
    db.session.add(f)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/friends/<int:friendship_id>/accept', methods=['POST'])
def api_accept_friend(friendship_id):
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    f = Friendship.query.get_or_404(friendship_id)
    if f.receiver != username:
        return jsonify({'error': 'Forbidden'}), 403  # only the receiver can accept
    f.status = 'accepted'
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/friends/<int:friendship_id>/decline', methods=['POST'])
def api_decline_friend(friendship_id):
    """Declines or cancels a friend request — both sender and receiver can do this."""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    f = Friendship.query.get_or_404(friendship_id)
    if f.sender != username and f.receiver != username:
        return jsonify({'error': 'Forbidden'}), 403
    db.session.delete(f)
    db.session.commit()
    return jsonify({'ok': True})

# =============================================================================
# Conversations (DM + Group Chat) API Routes
# =============================================================================
# A Conversation is either 'dm' (two users) or 'group' (linked to a StudyGroup).
# ConversationMember is a junction table that grants read/send access.

@app.route('/api/conversations', methods=['GET'])
def api_get_conversations():
    """Returns all conversations the user is a member of, with display names."""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401

    memberships = ConversationMember.query.filter_by(username=username).all()
    conv_ids    = [m.conversation_id for m in memberships]
    # .in_() is SQLAlchemy's WHERE id IN (...) — filter_by() can't do this
    conversations = Conversation.query.filter(Conversation.id.in_(conv_ids)).all()

    result = []
    for conv in conversations:
        members    = ConversationMember.query.filter_by(conversation_id=conv.id).all()
        other_names = [m.username for m in members if m.username != username]
        if conv.type == 'dm':
            name = other_names[0] if other_names else f'DM {conv.id}'
        elif conv.type == 'group' and conv.group_id:
            group_obj = StudyGroup.query.get(conv.group_id)
            name = group_obj.name if group_obj else f'Group {conv.id}'
        else:
            name = f'Group {conv.id}'
        result.append({'id': conv.id, 'type': conv.type, 'name': name})

    return jsonify({'conversations': result})

@app.route('/api/conversations/dm', methods=['POST'])
def api_open_dm():
    """Opens a DM conversation with another user, creating it if it doesn't exist yet."""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401

    data   = request.get_json()
    target = data.get('username', '').strip()
    if not target or target == username:
        return jsonify({'error': 'Invalid target'}), 400

    # Find a conversation that both users are already members of (the existing DM)
    my_convs    = {m.conversation_id for m in ConversationMember.query.filter_by(username=username).all()}
    their_convs = {m.conversation_id for m in ConversationMember.query.filter_by(username=target).all()}
    shared      = my_convs & their_convs
    for conv_id in shared:
        conv = Conversation.query.get(conv_id)
        if conv and conv.type == 'dm':
            return jsonify({'id': conv.id})

    # No existing DM — create one and add both users atomically
    conv = Conversation(type='dm')
    db.session.add(conv)
    # flush() sends SQL so conv.id is assigned, but doesn't commit — lets us add members
    # in the same transaction so either both the conv and both members are saved or neither is
    db.session.flush()
    db.session.add(ConversationMember(conversation_id=conv.id, username=username))
    db.session.add(ConversationMember(conversation_id=conv.id, username=target))
    db.session.commit()
    return jsonify({'id': conv.id}), 201

@app.route('/api/conversations/<int:conv_id>/messages', methods=['GET'])
def api_get_messages(conv_id):
    """Returns all messages in a conversation, oldest first. Blocks non-members."""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401

    # .first() returns one row or None — using it for existence checks avoids loading a full list
    member = ConversationMember.query.filter_by(conversation_id=conv_id, username=username).first()
    if not member:
        return jsonify({'error': 'Forbidden'}), 403

    msgs = Message.query.filter_by(conversation_id=conv_id).order_by(Message.created_at.asc()).all()
    return jsonify({'messages': [
        {
            'id':         m.id,
            'sender':     m.sender,
            'content':    m.content,
            # 'Z' suffix signals UTC to the browser so it renders in the user's local time
            'created_at': m.created_at.isoformat() + 'Z',
        }
        for m in msgs
    ]})

# =============================================================================
# SocketIO Events
# =============================================================================
# 'join': subscribes the user's socket connection to a conversation room so they
#         receive messages emitted to that room.
# 'send_message': saves the message to the DB and broadcasts it to all room members.

@socketio.on('join')
def on_join(data):
    username = session.get('username')
    if not username:
        return
    conv_id = data.get('conv_id')
    member  = ConversationMember.query.filter_by(conversation_id=conv_id, username=username).first()
    if not member:
        return
    # join_room() subscribes this socket connection to a named room —
    # any emit() targeting this room will reach this user
    join_room(str(conv_id))

@socketio.on('send_message')
def on_send_message(data):
    username = session.get('username')
    if not username:
        return
    conv_id = data.get('conv_id')
    content = (data.get('content') or '').strip()
    if not content or len(content) > 2000:
        return
    member = ConversationMember.query.filter_by(conversation_id=conv_id, username=username).first()
    if not member:
        return

    msg = Message(conversation_id=conv_id, sender=username, content=content)
    db.session.add(msg)
    db.session.commit()

    # emit() broadcasts the event to every socket subscribed to this room —
    # both users see the message appear in real time without polling
    emit('new_message', {
        'id':         msg.id,
        'conv_id':    conv_id,
        'sender':     msg.sender,
        'content':    msg.content,
        'created_at': msg.created_at.isoformat() + 'Z',
    }, room=str(conv_id))

# =============================================================================
# Email Reminder Logic
# =============================================================================
# Per-task exact scheduling: when a task/event is created, edited, completed, or deleted,
# a dedicated APScheduler job fires exactly 1 hour before the deadline.
# No polling — each item has its own job keyed by f'reminder_{type}_{id}'.

# Lock + sent-key set prevent duplicate emails when two tasks share the same deadline.
# Both jobs can fire simultaneously in different threads — the lock ensures only the
# first one actually sends; the second sees the key and returns immediately.
_reminder_lock      = threading.Lock()
_sent_reminder_keys: set = set()

def _send_reminder_job(username, to_email, fullname, due_str):
    # APScheduler runs this in a background thread — app.app_context() required for DB access.
    with app.app_context():
        target = datetime.fromisoformat(due_str)
        # Dedup key: one email per user per due-minute, even if multiple jobs fire at once
        key = (username, target.replace(second=0, microsecond=0))
        with _reminder_lock:
            if key in _sent_reminder_keys:
                return
            _sent_reminder_keys.add(key)

        window_start = target - timedelta(minutes=1)
        window_end   = target + timedelta(minutes=1)

        tasks = HomeworkTask.query.filter(
            HomeworkTask.username == username,
            HomeworkTask.is_completed == False,
            HomeworkTask.due_date >= window_start,
            HomeworkTask.due_date <= window_end,
        ).all()

        if not tasks:
            return

        items = [{'name': f"{t.course}: {t.task_name}", 'due': t.due_date.strftime('%b %d at %I:%M %p')} for t in tasks]
        send_reminder_email(to_email, fullname, items)

def schedule_reminder(item_id, item_type, due_datetime, user, name=''):
    # schedules a job to fire 1 hour before due_datetime
    # job id: f'reminder_{item_type}_{item_id}'
    # name param kept for call-site compatibility but unused — job queries the DB itself at fire time
    run_date = due_datetime - timedelta(hours=1)
    if run_date > get_current_datetime(user.timezone):
        job_id = f'reminder_{item_type}_{item_id}'
        _scheduler.add_job(
            _send_reminder_job,
            trigger='date',
            run_date=run_date,
            id=job_id,
            replace_existing=True,
            args=[user.username, user.email, user.fullname, due_datetime.isoformat()])

def cancel_reminder(item_id, item_type):
    # cancels the job if it exists
    job_id = f'reminder_{item_type}_{item_id}'
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)

# =============================================================================
# React catch-all — serve index.html for any route React Router handles.
# =============================================================================
# Every non-API route (e.g. /home, /study, /user/:username, /auth/callback) is a
# client-side React Router route. Without this, a hard refresh or direct URL
# navigation — including OAuth redirects — returns Flask's 404 instead of the app.
#
# WHY two handlers instead of only serve_react:
# Flask registers a built-in static handler for static_url_path='' which matches
# /<path:filename>. That static handler takes priority over serve_react for paths
# that don't correspond to real files and returns 404 before serve_react runs.
# The 404 error handler below catches those cases and completes the SPA fallback.

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    from flask import send_from_directory
    import os as _os
    dist = _os.path.join(app.root_path, 'frontend', 'dist')
    # Serve real static assets (JS, CSS, images) directly; fall back to index.html.
    file_path = _os.path.join(dist, path)
    if path and _os.path.exists(file_path):
        return send_from_directory(dist, path)
    return send_from_directory(dist, 'index.html')

@app.errorhandler(404)
def not_found(e):
    from flask import send_from_directory
    # API and auth-verify routes should return JSON 404, not the SPA shell.
    if request.path.startswith('/api/') or request.path == '/auth/verify':
        return jsonify({'error': 'Not found'}), 404
    # For all other paths (SPA routes like /auth/callback, /home, /user/:username)
    # serve index.html so React Router can handle the route client-side.
    import os as _os
    dist = _os.path.join(app.root_path, 'frontend', 'dist')
    return send_from_directory(dist, 'index.html')

# =============================================================================
# Scheduler + App Entry Point
# =============================================================================
# The WERKZEUG_RUN_MAIN guard prevents the scheduler from starting twice in dev mode.
# Flask's reloader forks the process — the parent process watches for file changes
# and the child (WERKZEUG_RUN_MAIN=true) is the one that actually serves requests.
# Starting the scheduler only in the child avoids duplicate emails during development.

if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not os.environ.get('FLASK_DEBUG'):
    _scheduler = BackgroundScheduler()
    _scheduler.start()

if __name__ == '__main__':
    socketio.run(app, debug=True)
