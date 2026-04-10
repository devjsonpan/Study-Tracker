# Real-Time Study & Productivity Tracker ⚡

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)

A comprehensive study time tracking web application designed to help students manage their study sessions, homework tasks, events, and track progress alongside friends in study groups.

🌟 **Live Demo:** [Try the App Here!](https://study-tracker-production-2086.up.railway.app/)

## 🎮 Features

### Study Management
| Feature | Description | Key Details |
|---------|-------------|-------------|
| **Study Sessions** | Track active study time | Log course, topic, notes, and time in/out |
| **Break Times** | Log rest periods | Track break durations separately from study time |
| **Notes System** | Centralized study notes | View, edit, hide, and manage notes from all sessions |

### Task & Schedule Management
- **Homework Tracker** - Manage assignments with due dates, descriptions, and completion status.
- **Event Planner** - Schedule events with start/end times, locations, and specific descriptions.
- **Calendar View** - Comprehensive visual timeline of all tasks and events. Color-coded based on status (Completed, Pending, Overdue).

### Social & Security Features
- **Study Groups** - Create or join study groups using unique 6-character codes.
- **Analytics & Leaderboard** - Compare daily and weekly study hours vs. break hours among group members.
- **User Authentication** - Secure login system with `Flask-Bcrypt` password hashing and security question recovery.

## 🎯 How to Use

1. **Create an Account** - Register with a username, password, and security question.
2. **Track Your Time**
   - Go to **Study Session** to log a new study session.
   - Go to **Break Time** to track a rest period.
3. **Manage Schedule**
   - Add upcoming assignments in **Homework Tasks**.
   - Schedule activities in **Events**.
   - Review your schedule timeline in the **Calendar**.
4. **Study Groups**
   - Navigate to the **Study Summary** dashboard to review analytics.
   - Create a group or join an existing one using a code to see how your friends are doing!

## 📸 Screenshots

<table>
  <tr>
    <td align="center">
      <img alt="Study Session" src="https://github.com/user-attachments/assets/ae2f55bf-1886-4c3a-8dfc-05e24ecf03bd">
      <br><em>Study Session</em>
    </td>
    <td align="center">
      <img alt="Notes" src="https://github.com/user-attachments/assets/7fad43b9-0e9a-4db1-8d2e-27db424b5036">
      <br><em>Study Notes</em>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img alt="Tasks" src="https://github.com/user-attachments/assets/f141028c-64e1-437f-84a8-d9d287629e6f">
      <br><em>Homework Tasks</em>
    </td>
    <td align="center">
      <img alt="Calendar View" src="https://github.com/user-attachments/assets/ac081b3f-278a-4e20-8d7c-11ea9e81aa95">
      <br><em>Calendar View</em>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img alt="Dashboard" src="https://github.com/user-attachments/assets/6589e1a3-bfc5-4427-b3ed-4b93b9c869f2">
      <br><em>Group Dashboard</em>
    </td>
    <td align="center">
      <img alt="Dashboard" src="https://github.com/user-attachments/assets/b84048d0-a815-4beb-a9a3-d5f6f774867a">
      <br><em>Individual Dashboard</em>
    </td>
  </tr>
</table>

## 🛠️ Built With

- **Flask** - Core Python web framework for application routing
- **SQLAlchemy & SQLite** - Relational database management with ORM mapping
- **Flask-Session & Flask-Bcrypt** - State management and security
- **Jinja2, HTML/CSS/JavaScript** - Responsive frontend rendering and styling

## 📁 Project Structure

```
Study-Tracker/
├── app.py                  # Main Flask application and routes
├── requirements.txt        # Python library dependencies
├── migrations/             # Database migration versions
├── static/                 # CSS and JS files
├── templates/              # HTML templates
└── README.md               # This file
```

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/devjsonpan/Study-Tracker.git
   cd "Study-Tracker"
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv venv
   
   # For Windows:
   venv\Scripts\activate
   # For macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
4. **Set up database**
   ```bash
   flask db upgrade
   ```

5. **Run the app**
   ```bash
   flask run
   ```
