# Online-Notes-Manager-Rizwan

A lightweight web application that lets users create, edit, and organize personal notes and reminders. Built with Flask (Python) and plain HTML templates, it provides a clean, responsive UI for managing daily tasks.

---

## Overview
The **Online-Notes-Manager-Rizwan** project offers a simple yet functional notes‑taking platform. Users can register, log in, create notes, set reminders, and view/edit their profile—all backed by a SQLite database.

---

## Features
- **User Authentication** – Register, login, and logout securely.  
- **Notes Management** – Create, edit, delete, and view notes.  
- **Reminders** – Add, edit, and list time‑based reminders.  
- **Profile Management** – Update and view user profile information.  
- **Responsive UI** – Clean HTML templates using a shared `base.html`.  
- **SQLite Persistence** – All data stored in `instance/notes.db`.

---

## Tech Stack
| Layer | Technology |
|-------|------------|
| Backend | Python 3, Flask |
| Database | SQLite (`instance/notes.db`) |
| Front‑end | HTML5, CSS (embedded in templates) |
| Deployment | Any WSGI‑compatible server (e.g., Gunicorn) |

---

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Online-Notes-Manager-Rizwan.git
   cd Online-Notes-Manager-Rizwan
   ```

2. **Create a virtual environment** (optional but recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *If `requirements.txt` is missing, install Flask manually:*
   ```bash
   pip install Flask
   ```

4. **Set up environment variables** (replace placeholders as needed)
   ```bash
   export FLASK_APP=app.py
   export FLASK_ENV=development   # optional, for debug mode
   export SECRET_KEY=YOUR_OWN_API_KEY
   ```

5. **Initialize the database** (only required on first run)
   ```bash
   flask init-db
   ```
   *The command creates `instance/notes.db` if it does not exist.*

---

## Usage

```bash
flask run
```

- The app will be available at `http://127.0.0.1:5000/`.
- Navigate to `/register` to create a new account, then log in.
- Use the dashboard to manage notes and reminders.

---

## License

This project is licensed under the **MIT License** – see the `LICENSE` file for details.