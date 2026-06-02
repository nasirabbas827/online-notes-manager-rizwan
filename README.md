# online-notes-manager-rizwan  

A lightweight web application that lets users create, edit, and organize personal notes and reminders. Built with Flask and plain HTML templates, it stores data locally in SQLite for quick prototyping and easy deployment.

---  

## Overview  

The **Online Notes Manager** provides a simple, secure interface for managing notes and reminders. Users can register, log in, and maintain a personal dashboard where they can:

* Create, edit, and delete notes.  
* Set and view time‑based reminders.  
* Update their profile information.  

All data is persisted in an SQLite database (`instance/notes.db`) and rendered through clean, responsive HTML templates.

---  

## Features  

| ✅ | Feature |
|---|----------|
| ✔️ | User authentication (register, login, logout) |
| ✔️ | CRUD operations for notes |
| ✔️ | CRUD operations for reminders with optional due dates |
| ✔️ | Personal profile view & update |
| ✔️ | Dashboard summarising recent notes & upcoming reminders |
| ✔️ | Server‑side validation and flash messages for user feedback |
| ✔️ | SQLite persistence (no external DB required) |
| ✔️ | Fully templated UI using Jinja2 and Bootstrap (optional) |

---  

## Tech Stack  

| Layer | Technology |
|-------|------------|
| Backend | **Python 3**, Flask |
| Database | SQLite (via Flask‑SQLAlchemy) |
| Templating | Jinja2 (HTML) |
| Deployment | Any platform that can run a Flask app (e.g., Heroku, Render, local Docker) |
| Other | `Werkzeug` for password hashing, `Flask‑Login` for session management |

---  

## Installation  

> **Prerequisites**  
> * Python 3.8+  
> * Git  

1. **Clone the repository**  

   ```bash
   git clone https://github.com/your-username/online-notes-manager-rizwan.git
   cd online-notes-manager-rizwan
   ```

2. **Create a virtual environment**  

   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**  

   ```bash
   pip install -r requirements.txt
   ```

   *If a `requirements.txt` file is not present, install the core packages manually:*

   ```bash
   pip install Flask Flask-Login Flask-SQLAlchemy
   ```

4. **Configure environment variables**  

   Create a `.env` file (or export variables in your shell) with at least the following:

   ```env
   FLASK_APP=app.py
   FLASK_ENV=development   # optional, remove for production
   SECRET_KEY=YOUR_OWN_API_KEY
   ```

5. **Initialize the database**  

   ```bash
   flask db upgrade   # if using Flask-Migrate
   # or, for the simple setup provided:
   python -c "from app import db; db.create_all()"
   ```

6. **Run the application**  

   ```bash
   flask run
   ```

   The app will be accessible at `http://127.0.0.1:5000`.

---  

## Usage  

1. **Open the web UI** – navigate to `http://127.0.0.1:5000` in a browser.  
2. **Register a new account** – click *Register* and fill out the form.  
3. **Log in** – use the credentials you just created.  
4. **Dashboard** – view a summary of your notes and upcoming reminders.  
5. **Create a note** – go to *Create Note*, fill in the title and content, then submit.  
6. **Create a reminder** – from the dashboard or the *Add