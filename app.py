# Import the necessary modules from the libraries
from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from datetime import datetime
from datetime import timedelta
from flask_session import Session
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)

# Configure SQLAlchemy to use the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///study_tracker.db'

# Configure Flask-Session
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Create an instance of SQLAlchemy to interact with the database
db = SQLAlchemy(app)

bcrypt = Bcrypt(app)
migrate = Migrate(app, db)

# Define the User model for the database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    fullname = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    security_question = db.Column(db.String, nullable=False)
    security_answer = db.Column(db.String, nullable=False)

# Define the StudySession model for the database
class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False) 
    course = db.Column(db.String, nullable=False)
    topic = db.Column(db.String, nullable=True)
    time_in = db.Column(db.Time, nullable=False)
    time_out = db.Column(db.Time, nullable=False)
    date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.String, nullable=True)
    hidden_from_notes = db.Column(db.Boolean, default=False, nullable=False)

# Define the HomeworkTask model for the database
class HomeworkTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False)
    course = db.Column(db.String, nullable=False)
    task_name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    due_date = db.Column(db.DateTime, nullable=False)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False)
    event_name = db.Column(db.String, nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String, nullable=True)
    description = db.Column(db.String, nullable=True)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

# Define the BreakEntry model for the database
class BreakEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False)
    time_in = db.Column(db.Time, nullable=False)
    time_out = db.Column(db.Time, nullable=False)
    date = db.Column(db.Date, nullable=False)

# Route for the login page
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    success = None
    show_reset_form = request.args.get('forgot') == '1'
    
    # Check for flash messages
    flashed_messages = get_flashed_messages(with_categories=True)
    for category, message in flashed_messages:
        if category == 'success':
            success = message
        elif category == 'error':
            error = message
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['username'] = user.username
            return redirect(url_for('home', fullname=user.fullname))
        else:
            error = 'Invalid login credentials. Please try again.'

    return render_template('login.html', error=error, success=success, show_reset_form=show_reset_form)

# Route for password reset
@app.route('/reset_password', methods=['POST'])
def reset_password():
    error = None
    username = request.form.get('username')
    security_answer = request.form.get('security_answer')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    user = User.query.filter_by(username=username).first()
    
    if not user:
        error = 'Username not found.'
        return render_template('login.html', 
                             error=error, 
                             show_reset_form=True, 
                             username=username)
    
    # If security answer not provided yet, show the question
    if not security_answer:
        return render_template('login.html', 
                             show_reset_form=True, 
                             security_question=user.security_question,
                             username=username)
    
    # Verify security answer (case-insensitive)
    if security_answer.lower().strip() != user.security_answer:
        error = 'Incorrect security answer. Please try again.'
        return render_template('login.html', 
                             error=error, 
                             show_reset_form=True, 
                             security_question=user.security_question,
                             username=username)
    
    # Check if passwords match
    if new_password != confirm_password:
        error = 'Passwords do not match.'
        return render_template('login.html', 
                             error=error, 
                             show_reset_form=True, 
                             security_question=user.security_question,
                             username=username)
    
    # Update password
    user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()
    
    # Redirect to login page with success message
    flash('Password reset successful! You can now login with your new password.', 'success')
    return redirect(url_for('login'))

# Route for the registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    
    if request.method == 'POST':
        username = request.form.get('username')
        fullname = request.form.get('fullname')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        security_question = request.form.get('security_question')
        security_answer = request.form.get('security_answer')

        # Check if passwords match
        if password != confirm_password:
            error = 'Passwords do not match. Please try again.'
            return render_template('register.html', error=error)
        
        # Check if security answer is provided
        if not security_answer or len(security_answer.strip()) == 0:
            error = 'Please provide a security answer.'
            return render_template('register.html', error=error)
            
        existing_user = User.query.filter_by(username=username).first()
        
        # Check if new user can be created
        if existing_user:
            error = 'Username is already taken. Please choose a different username.'
        else:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(
                username=username, 
                fullname=fullname, 
                password=hashed_password, 
                security_question=security_question,
                security_answer=security_answer.lower().strip()
            )
            db.session.add(new_user)
            db.session.commit()

            session['username'] = new_user.username
            return redirect(url_for('login'))

    return render_template('register.html', error=error)

# Route for the home page
@app.route('/home')
def home():
    if session.get('username') == None:
        return redirect(url_for('login'))

    username = session.get('username')
    fullname = User.query.filter_by(username=username).first().fullname

    return render_template('home.html', username=username, fullname=fullname)

# Route for the study session page
@app.route('/session')
def study_session():
    if session.get('username') == None:
        return redirect(url_for('login'))

    return render_template('study_session.html')

# Route for saving the study session data
@app.route('/save_study_session', methods=['POST'])
def save_study_session():
    if request.method == 'POST':
        course = request.form.get('course')
        topic = request.form.get('topic')
        time_in_str = request.form.get('time_in')
        time_out_str = request.form.get('time_out')
        notes = request.form.get('notes')

        username = session['username']

        try:
            time_in = datetime.strptime(time_in_str, '%H:%M:%S').time()
        except ValueError:
            time_in = datetime.strptime(time_in_str, '%H:%M').time()

        try:
            time_out = datetime.strptime(time_out_str, '%H:%M:%S').time()
        except ValueError:
            time_out = datetime.strptime(time_out_str, '%H:%M').time()

        current_date = datetime.now().date()

        new_entry = StudySession(
            username=username, 
            course=course, 
            topic=topic,
            time_in=time_in, 
            time_out=time_out,
            date=current_date,
            notes=notes
        )

        db.session.add(new_entry)
        db.session.commit()

        return redirect(url_for('study_session'))

    return render_template('study_session.html')

# Route for the homework page
@app.route('/homework')
def homework():
    if session.get('username') == None:
        return redirect(url_for('login'))

    username = session['username']
    # Get all tasks ordered by due date, regardless of completion status
    tasks = HomeworkTask.query.filter_by(username=username).order_by(HomeworkTask.due_date).all()
    
    return render_template('homework.html', tasks=tasks, now=datetime.now())

# Route for saving new homework task
@app.route('/save_homework', methods=['POST'])
def save_homework():
    if request.method == 'POST':
        course = request.form.get('course')
        task_name = request.form.get('task_name')
        description = request.form.get('description') or None
        due_date_str = request.form.get('due_date')
        
        username = session['username']
        
        # Convert string to date
        due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        
        new_task = HomeworkTask(
            username=username,
            course=course,
            task_name=task_name,
            description=description,
            due_date=due_date
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        return redirect(url_for('homework'))
    
    return redirect(url_for('homework'))

# Route for marking task as completed
@app.route('/complete_task/<int:task_id>')
def complete_task(task_id):
    if session.get('username') == None:
        return redirect(url_for('login'))
    
    task = HomeworkTask.query.get_or_404(task_id)
    
    # Only allow user to complete their own tasks
    if task.username == session['username']:
        task.is_completed = not task.is_completed  # Toggle completion status
        db.session.commit()
    
    return redirect(url_for('homework'))

# Route for deleting task
@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    if session.get('username') == None:
        return redirect(url_for('login'))
    
    task = HomeworkTask.query.get_or_404(task_id)
    
    # Only allow user to delete their own tasks
    if task.username == session['username']:
        db.session.delete(task)
        db.session.commit()
    
    return redirect(url_for('homework'))

# Route for editing a homework task
@app.route('/edit_task/<int:task_id>', methods=['POST'])
def edit_task(task_id):
    if session.get('username') == None:
        return redirect(url_for('login'))
    
    task = HomeworkTask.query.get_or_404(task_id)
    
    if task.username == session['username']:
        task.course = request.form.get('course')
        task.task_name = request.form.get('task_name')
        task.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%dT%H:%M')
        task.description = request.form.get('description')
        db.session.commit()
        flash('Task updated successfully!', 'success')
    
    return redirect(url_for('homework'))
 
# Route for the events page
@app.route('/events')
def events():
    if session.get('username') == None:
        return redirect(url_for('login'))
    
    username = session['username']
    
    all_events = Event.query.filter_by(username=username).order_by(Event.start_datetime).all()
    
    return render_template('events.html', events=all_events, now=datetime.now())

# Route for saving new event
@app.route('/save_event', methods=['POST'])
def save_event():
    if request.method == 'POST':
        event_name = request.form.get('event_name')
        start_datetime_str = request.form.get('start_datetime')
        end_datetime_str = request.form.get('end_datetime')
        location = request.form.get('location')
        description = request.form.get('description')
        
        username = session['username']
        
        # Convert string to datetime
        start_datetime = datetime.strptime(start_datetime_str, '%Y-%m-%dT%H:%M')
        end_datetime = datetime.strptime(end_datetime_str, '%Y-%m-%dT%H:%M')
        
        if start_datetime >= end_datetime:
            flash('The start time must be before the end time.', 'error')
            return redirect(url_for('events'))
        
        new_event = Event(
            username=username,
            event_name=event_name,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            location=location,
            description=description
        )
        
        db.session.add(new_event)
        db.session.commit()
        
        return redirect(url_for('events'))
    
    return redirect(url_for('events'))

# Route for marking event as completed
@app.route('/complete_event/<int:event_id>')
def complete_event(event_id):
    if session.get('username') == None:
        return redirect(url_for('login'))
    
    event = Event.query.get_or_404(event_id)
    
    # Only allow user to complete their own events
    if event.username == session['username']:
        event.is_completed = not event.is_completed  # Toggle completion status
        db.session.commit()
    
    return redirect(url_for('events'))

# Route for deleting event
@app.route('/delete_event/<int:event_id>')
def delete_event(event_id):
    if session.get('username') == None:
        return redirect(url_for('login'))
    
    event = Event.query.get_or_404(event_id)
    
    # Only allow user to delete their own events
    if event.username == session['username']:
        db.session.delete(event)
        db.session.commit()
    
    return redirect(url_for('events'))

# Route for editing an event
@app.route('/edit_event/<int:event_id>', methods=['POST'])
def edit_event(event_id):
    if session.get('username') == None:
        return redirect(url_for('login'))
    
    event = Event.query.get_or_404(event_id)
    
    if event.username == session['username']:
        start_datetime = datetime.strptime(request.form.get('start_datetime'), '%Y-%m-%dT%H:%M')
        end_datetime = datetime.strptime(request.form.get('end_datetime'), '%Y-%m-%dT%H:%M')
        
        if start_datetime >= end_datetime:
            flash('The start time must be before the end time.', 'error')
            return redirect(url_for('events'))
        
        event.event_name = request.form.get('event_name')
        event.start_datetime = start_datetime
        event.end_datetime = end_datetime
        event.location = request.form.get('location')
        event.description = request.form.get('description')
        db.session.commit()
        flash('Event updated successfully!', 'success')
    
    return redirect(url_for('events'))

# Route for the calendar page
@app.route('/calendar')
def calendar_view():
    if session.get('username') == None:
        return redirect(url_for('login'))
        
    username = session['username']
    
    tasks = HomeworkTask.query.filter_by(username=username).all()
    events = Event.query.filter_by(username=username).all()
    
    calendar_events = []
    
    for task in tasks:
        if task.is_completed:
            bg_color = '#48bb78'
        elif task.due_date < datetime.now():
            bg_color = '#e53e3e'
        else:
            bg_color = '#ff9900'

        calendar_events.append({
            'title': f"{task.course}: {task.task_name}",
            'start': task.due_date.isoformat(),
            'backgroundColor': bg_color,
            'borderColor': bg_color,
            'textColor': '#fff',
            'display': 'list-item',
            'extendedProps': {
                'type': 'task',
                'completed': task.is_completed,
                'description': task.description or 'N/A',
                'deadline': task.due_date.strftime('%B %d, %Y at %I:%M %p')
            }
        })

    for event in events:
        end_dt = event.end_datetime
        if end_dt.hour == 0 and end_dt.minute == 0:
            end_dt = end_dt + timedelta(minutes=1)

        calendar_events.append({
            'title': f"{event.event_name}",
            'start': event.start_datetime.isoformat(),
            'end': end_dt.isoformat(),
            'backgroundColor': '#48bb78' if event.is_completed else '#667eea',
            'borderColor': '#38a169' if event.is_completed else '#5568d3',
            'textColor': '#fff',
            'display': 'block',
            'extendedProps': {
                'type': 'event',
                'completed': event.is_completed,
                'real_start': event.start_datetime.strftime('%B %d, %Y at %I:%M %p'),
                'real_end': event.end_datetime.strftime('%B %d, %Y at %I:%M %p'),
                'location': event.location or 'N/A',
                'description': event.description or 'N/A'
            }
        })

    return render_template('calendar.html', calendar_events=calendar_events)

# Route for the break page
@app.route('/break')
def break_time():
    if session.get('username') == None:
        return redirect(url_for('login'))
    
    return render_template('break_time.html')

# Route for saving the break data
@app.route('/save_break', methods=['POST'])
def save_break():
    if request.method == 'POST':
        time_in_str = request.form.get('time_in')
        time_out_str = request.form.get('time_out')

        username = session['username']

        # The frontend JS timer will send HH:MM:SS, but fallback to HH:MM if manual input
        try:
            time_in = datetime.strptime(time_in_str, '%H:%M:%S').time()
        except ValueError:
            time_in = datetime.strptime(time_in_str, '%H:%M').time()
            
        try:
            time_out = datetime.strptime(time_out_str, '%H:%M:%S').time()
        except ValueError:
            time_out = datetime.strptime(time_out_str, '%H:%M').time()
            
        current_date = datetime.now().date()

        new_entry = BreakEntry(username=username, time_in=time_in, time_out=time_out, date=current_date)

        db.session.add(new_entry)
        db.session.commit()

        return redirect(url_for('break_time'))

    return render_template('break_time.html')

# Route for the notes page
@app.route('/notes')
def notes():
    if session.get('username') == None:
        return redirect(url_for('login'))
    
    username = session['username']
    sessions_with_notes = StudySession.query.filter_by(
        username=username,
        hidden_from_notes=False
    ).order_by(StudySession.date.desc()).all()
    
    return render_template('notes.html', sessions=sessions_with_notes)

# Route for deleting a note
@app.route('/delete_note/<int:session_id>')
def delete_note(session_id):
    if session.get('username') == None:
        return redirect(url_for('login'))
    
    username = session['username']
    # Find the study session
    study_session = StudySession.query.get_or_404(session_id)
    
    # Make sure user can only delete their own notes
    if study_session.username == username:
        study_session.hidden_from_notes = True
        study_session.notes = None
        db.session.commit()
        flash('Note deleted successfully!', 'success')
    else:
        flash('You do not have permission to delete this note.', 'error')
    
    return redirect(url_for('notes'))

# Route for editing a note
@app.route('/edit_note/<int:session_id>', methods=['POST'])
def edit_note(session_id):
    if session.get('username') == None:
        return redirect(url_for('login'))
    
    username = session['username']
    # Find the study session
    study_session = StudySession.query.get_or_404(session_id)
    
    # Make sure user can only edit their own notes
    if study_session.username == username:
        # Update the fields
        study_session.course = request.form.get('course')
        study_session.topic = request.form.get('topic')
        study_session.notes = request.form.get('notes')
        db.session.commit()
        flash('Note updated successfully!', 'success')
    else:
        flash('You do not have permission to edit this note.', 'error')
    
    return redirect(url_for('notes'))

def calculate_duration_mins(time_in, time_out):
    in_sec = time_in.hour * 3600 + time_in.minute * 60 + time_in.second
    out_sec = time_out.hour * 3600 + time_out.minute * 60 + time_out.second
    diff = out_sec - in_sec
    if diff < 0:
        diff += 86400
    return diff / 60.0

@app.route('/summary')
def study_summary():
    current_date = datetime.now()
    current_username = session.get('username')
    
    if current_username is None:
        return redirect(url_for('login'))

    all_users = User.query.all()

    current_user = next((u for u in all_users if u.username == current_username), None)
    if current_user:
        all_users.remove(current_user)
        all_users.insert(0, current_user)

    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())

    # Friends comparison data
    friend_names = []
    friend_study_hours = []
    friend_break_hours = []
    friend_today_study = []
    friend_today_break = []

    for user in all_users:
        # Weekly sessions for leaderboard
        user_sessions = StudySession.query.filter_by(username=user.username).filter(
            StudySession.date >= week_start
        ).all()
        user_breaks = BreakEntry.query.filter_by(username=user.username).filter(
            BreakEntry.date >= week_start
        ).all()

        total_study_mins = sum(
            calculate_duration_mins(s.time_in, s.time_out)
            for s in user_sessions
        )
        total_break_mins = sum(
            calculate_duration_mins(b.time_in, b.time_out)
            for b in user_breaks
        )

        # Today's sessions for today graphs
        user_today_sessions = StudySession.query.filter_by(username=user.username).filter(
            StudySession.date == today
        ).all()
        user_today_breaks = BreakEntry.query.filter_by(username=user.username).filter(
            BreakEntry.date == today
        ).all()

        today_study_mins = sum(
            calculate_duration_mins(s.time_in, s.time_out)
            for s in user_today_sessions
        )
        today_break_mins = sum(
            calculate_duration_mins(b.time_in, b.time_out)
            for b in user_today_breaks
        )

        friend_names.append(user.fullname)
        friend_study_hours.append(round(total_study_mins / 60, 2))
        friend_break_hours.append(round(total_break_mins / 60, 2))
        friend_today_study.append(round(today_study_mins / 60, 2))
        friend_today_break.append(round(today_break_mins / 60, 2))

    # Sort all lists together by weekly study hours
    sorted_friends = sorted(
        zip(friend_study_hours, friend_break_hours, friend_names, friend_today_study, friend_today_break),
        reverse=True
    )
    if sorted_friends:
        friend_study_hours, friend_break_hours, friend_names, friend_today_study, friend_today_break = map(list, zip(*sorted_friends))
    else:
        friend_study_hours, friend_break_hours, friend_names, friend_today_study, friend_today_break = [], [], [], [], []

    # Self analytics data
    my_sessions = StudySession.query.filter_by(username=current_username).order_by(StudySession.date).all()
    my_breaks = BreakEntry.query.filter_by(username=current_username).order_by(BreakEntry.date).all()

    # Course breakdown (minutes per course)
    course_totals = {}
    for s in my_sessions:
        mins = calculate_duration_mins(s.time_in, s.time_out)
        course_totals[s.course] = course_totals.get(s.course, 0) + mins

    course_labels = list(course_totals.keys())
    course_hours = [round(m / 60, 2) for m in course_totals.values()]

    # Study hours per day (last 14 days)
    from collections import defaultdict
    daily_study = defaultdict(float)
    daily_break = defaultdict(float)

    for s in my_sessions:
        mins = calculate_duration_mins(s.time_in, s.time_out)
        daily_study[s.date.strftime('%b %d')] += round(mins / 60, 2)

    for b in my_breaks:
        mins = calculate_duration_mins(b.time_in, b.time_out)
        daily_break[b.date.strftime('%b %d')] += round(mins / 60, 2)

    all_dates = sorted(set(list(daily_study.keys()) + list(daily_break.keys())))
    daily_labels = all_dates[-14:]
    daily_study_values = [daily_study.get(d, 0) for d in daily_labels]
    daily_break_values = [daily_break.get(d, 0) for d in daily_labels]

    # Today's data for My Stats tab
    today_sessions = StudySession.query.filter_by(username=current_username).filter(
        StudySession.date == today
    ).all()
    today_breaks = BreakEntry.query.filter_by(username=current_username).filter(
        BreakEntry.date == today
    ).all()

    today_course_totals = {}
    for s in today_sessions:
        mins = calculate_duration_mins(s.time_in, s.time_out)
        today_course_totals[s.course] = today_course_totals.get(s.course, 0) + mins

    today_course_labels = list(today_course_totals.keys())
    today_course_hours = [round(m / 60, 2) for m in today_course_totals.values()]

    today_study_mins = sum(
        calculate_duration_mins(s.time_in, s.time_out)
        for s in today_sessions
    )
    today_break_mins = sum(
        calculate_duration_mins(b.time_in, b.time_out)
        for b in today_breaks
    )
    today_study_hours = round(today_study_mins / 60, 2)
    today_break_hours = round(today_break_mins / 60, 2)

    return render_template('study_summary.html',
        current_date=current_date,
        current_username=current_username,
        current_fullname=current_user.fullname if current_user else '',
        week_start=week_start,
        # Friends chart
        friend_names=friend_names,
        friend_study_hours=friend_study_hours,
        friend_break_hours=friend_break_hours,
        friend_today_study=friend_today_study,
        friend_today_break=friend_today_break,
        # Self chart
        course_labels=course_labels,
        course_hours=course_hours,
        daily_labels=daily_labels,
        daily_study_values=daily_study_values,
        daily_break_values=daily_break_values,
        # Today's chart
        today_course_labels=today_course_labels,
        today_course_hours=today_course_hours,
        today_study_hours=today_study_hours,
        today_break_hours=today_break_hours,
    )

# Main block to run the application
if __name__ == '__main__':
    app.run(debug=True)