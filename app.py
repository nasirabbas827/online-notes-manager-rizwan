from flask import Flask, jsonify, Response, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'notes_db'

mysql = MySQL(app)

# File Upload Configuration
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' in session:
        user_id = session['user_id']
        username = session['username']
        cur = mysql.connection.cursor()
        # Fetch non-draft notes for logged-in user
        cur.execute('SELECT * FROM notes WHERE user_id = %s AND isDraft = FALSE ORDER BY isPinned DESC, updatedAt DESC', (user_id,))
        notes = cur.fetchall()
        cur.close()
        return render_template('index.html', username=username, notes=notes)
    else:
        # Guest mode: render empty notes list (populated by localStorage)
        return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                    (username, email, hashed_password))
        mysql.connection.commit()
        cur.close()

        flash('Registration successful. You can now login.', 'success')
        return redirect(url_for('user_login'))

    return render_template('register.html')

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute('SELECT id, username, password FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return jsonify({'status': 'success', 'redirect': url_for('dashboard')})
        else:
            return jsonify({'status': 'error', 'message': 'Invalid username or password'}), 401

    return render_template('login.html')

@app.route('/notes/sync', methods=['POST'])
def sync_notes():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    user_id = session['user_id']
    data = request.get_json()
    guest_notes = data.get('notes', [])

    cur = mysql.connection.cursor()
    # Fetch existing notes to check for duplicates
    cur.execute('SELECT title, content FROM notes WHERE user_id = %s AND isDraft = FALSE', (user_id,))
    existing_notes = cur.fetchall()
    existing_notes_set = {(note[0], note[1]) for note in existing_notes}  # Set of (title, content) tuples

    new_note_ids = []
    for note in guest_notes:
        title = note.get('title', '')
        content = note.get('content', '')
        category = note.get('category', 'Miscellaneous')
        isPinned = note.get('isPinned', False)

        # Skip duplicates based on title and content
        if (title, content) not in existing_notes_set:
            cur.execute("""
                INSERT INTO notes (user_id, title, content, category, isPinned, isDraft)
                VALUES (%s, %s, %s, %s, %s, FALSE)
            """, (user_id, title, content, category, isPinned))
            new_note_ids.append(cur.lastrowid)
            existing_notes_set.add((title, content))

    mysql.connection.commit()
    cur.close()

    return jsonify({'status': 'success', 'new_note_ids': new_note_ids})

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    username = session['username']

    cur = mysql.connection.cursor()
    # Fetch non-draft notes
    cur.execute('SELECT * FROM notes WHERE user_id = %s AND isDraft = FALSE ORDER BY isPinned DESC, updatedAt DESC', (user_id,))
    notes = cur.fetchall()

    # Fetch draft note (if any)
    cur.execute('SELECT * FROM notes WHERE user_id = %s AND isDraft = TRUE LIMIT 1', (user_id,))
    draft_note = cur.fetchone()

    # Fetch latest 5 upcoming reminders
    cur.execute("""
        SELECT r.id, n.title, r.reminder_date, r.status 
        FROM reminders r 
        JOIN notes n ON r.note_id = n.id 
        WHERE r.user_id = %s AND r.reminder_date >= NOW() 
        ORDER BY r.reminder_date ASC LIMIT 5
    """, (user_id,))
    reminders = cur.fetchall()
    cur.close()

    return render_template('dashboard.html', username=username, notes=notes, draft_note=draft_note, reminders=reminders)


@app.route('/create_note', methods=['GET'])
def create_note_page():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    username = session['username']

    cur = mysql.connection.cursor()
    # Fetch draft note (if any)
    cur.execute('SELECT * FROM notes WHERE user_id = %s AND isDraft = TRUE LIMIT 1', (user_id,))
    draft_note = cur.fetchone()
    cur.close()

    return render_template('create_note.html', username=username, draft_note=draft_note)

@app.route('/notes/create', methods=['POST'])
def create_note():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    user_id = session['user_id']
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    category = data.get('category')
    isPinned = data.get('isPinned')
    isDraft = data.get('isDraft', False)

    cur = mysql.connection.cursor()
    # Check if a draft note exists
    cur.execute('SELECT id FROM notes WHERE user_id = %s AND isDraft = TRUE', (user_id,))
    draft = cur.fetchone()

    if draft and isDraft:
        # Update existing draft
        cur.execute("""
            UPDATE notes SET title=%s, content=%s, category=%s, isPinned=%s, updatedAt=NOW()
            WHERE id=%s AND user_id=%s
        """, (title, content, category, isPinned, draft[0], user_id))
        note_id = draft[0]
    else:
        # Create new note
        cur.execute("""
            INSERT INTO notes (user_id, title, content, category, isPinned, isDraft)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, title, content, category, isPinned, isDraft))
        note_id = cur.lastrowid  # Get last inserted id

    mysql.connection.commit()
    cur.close()

    return jsonify({'status': 'success', 'note_id': note_id})

@app.route('/notes/update/<int:note_id>', methods=['POST'])
def update_note(note_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    category = data.get('category')
    isPinned = data.get('isPinned')
    isDraft = data.get('isDraft', False)

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE notes SET title=%s, content=%s, category=%s, isPinned=%s, isDraft=%s, updatedAt=NOW()
        WHERE id=%s AND user_id=%s
    """, (title, content, category, isPinned, isDraft, note_id, session['user_id']))
    mysql.connection.commit()
    cur.close()

    return jsonify({'status': 'updated'})

@app.route('/notes/delete/<int:note_id>', methods=['POST'])
def delete_note(note_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM notes WHERE id = %s AND user_id = %s", (note_id, session['user_id']))
    mysql.connection.commit()
    cur.close()

    return jsonify({'status': 'deleted'})

@app.route('/notes/search', methods=['GET'])
def search_notes():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    user_id = session['user_id']
    query = request.args.get('query', '')

    cur = mysql.connection.cursor()
    # Search non-draft notes by title or content
    cur.execute("""
        SELECT * FROM notes 
        WHERE user_id = %s AND isDraft = FALSE 
        AND (title LIKE %s OR content LIKE %s) 
        ORDER BY isPinned DESC, updatedAt DESC
    """, (user_id, f'%{query}%', f'%{query}%'))
    notes = cur.fetchall()
    cur.close()

    return jsonify({'status': 'success', 'notes': notes})

@app.route('/notes/export', methods=['GET'])
def export_notes():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute('SELECT title, content, category, isPinned, updatedAt FROM notes WHERE user_id = %s AND isDraft = FALSE', (user_id,))
    notes = cur.fetchall()
    cur.close()

    # Generate text content for export
    export_content = ""
    for note in notes:
        title, content, category, isPinned, updatedAt = note
        export_content += f"Title: {title}\n"
        export_content += f"Category: {category}\n"
        export_content += f"Pinned: {isPinned}\n"
        export_content += f"Updated At: {updatedAt}\n"
        export_content += f"Content:\n{content}\n"
        export_content += "-" * 50 + "\n\n"

    # Return as a downloadable text file
    return Response(
        export_content,
        mimetype='text/plain',
        headers={'Content-Disposition': 'attachment; filename=notes_export.txt'}
    )

@app.route('/notes/edit/<int:note_id>', methods=['GET'])
def edit_note(note_id):
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM notes WHERE id = %s AND user_id = %s", (note_id, session['user_id']))
    note = cur.fetchone()
    cur.close()

    if not note:
        flash('Note not found', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('edit_note.html', note=note)

@app.route('/user/logout')
def user_logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user_id = session['user_id']

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password) if password else None

        profile_picture = None
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                profile_picture = file_path.replace('\\', '/')

        cur = mysql.connection.cursor()
        if hashed_password:
            cur.execute(
                "UPDATE users SET first_name=%s, last_name=%s, email=%s, password=%s, profile_picture=%s WHERE id=%s",
                (first_name, last_name, email, hashed_password, profile_picture, user_id)
            )
        else:
            cur.execute(
                "UPDATE users SET first_name=%s, last_name=%s, email=%s, profile_picture=%s WHERE id=%s",
                (first_name, last_name, email, profile_picture, user_id)
            )
        mysql.connection.commit()
        cur.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('view_profile'))

    # GET: Fetch existing data
    cur = mysql.connection.cursor()
    cur.execute('SELECT first_name, last_name, email, profile_picture FROM users WHERE id = %s', (user_id,))
    user = cur.fetchone()
    cur.close()

    if user:
        user_data = {
            'first_name': user[0],
            'last_name': user[1],
            'email': user[2],
            'profile_picture': user[3].replace('\\', '/') if user[3] else None
        }
        return render_template('update_profile.html', user=user_data)
    else:
        flash('User not found', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/view_profile')
def view_profile():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))
    
    user_id = session['user_id']
    
    cur = mysql.connection.cursor()
    cur.execute('SELECT username, password, first_name, last_name, email, profile_picture FROM users WHERE id = %s', (user_id,))
    user = cur.fetchone()
    cur.close()
    
    if user:
        user_data = {
            'username': user[0],
            'password': user[1],
            'first_name': user[2],
            'last_name': user[3],
            'email': user[4],
            'profile_picture': user[5].replace('\\', '/') if user[5] else None
        }
        return render_template('view_profile.html', user=user_data)
    else:
        flash('User not found', 'danger')
        return redirect(url_for('dashboard'))
    

@app.route('/reminders/add', methods=['GET', 'POST'])
def add_reminder():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        note_id = request.form['note_id']
        reminder_date = request.form['reminder_date']
        status = request.form['status']

        cur.execute("""
            INSERT INTO reminders (note_id, user_id, reminder_date, status)
            VALUES (%s, %s, %s, %s)
        """, (note_id, user_id, reminder_date, status))
        mysql.connection.commit()
        cur.close()
        flash('Reminder added successfully!', 'success')
        return redirect(url_for('view_reminders'))

    # Fetch user's non-draft notes for dropdown
    cur.execute('SELECT id, title FROM notes WHERE user_id = %s AND isDraft = FALSE', (user_id,))
    notes = cur.fetchall()
    cur.close()
    return render_template('add_reminder.html', notes=notes)


@app.route('/reminders/view', methods=['GET'])
def view_reminders():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT r.id, n.title, r.reminder_date, r.status, r.snoozed_until 
        FROM reminders r 
        JOIN notes n ON r.note_id = n.id 
        WHERE r.user_id = %s 
        ORDER BY r.reminder_date DESC
    """, (user_id,))
    reminders = cur.fetchall()
    cur.close()
    return render_template('view_reminders.html', reminders=reminders)

@app.route('/reminders/delete/<int:reminder_id>', methods=['POST'])
def delete_reminder(reminder_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM reminders WHERE id = %s AND user_id = %s", (reminder_id, session['user_id']))
    mysql.connection.commit()
    cur.close()
    return jsonify({'status': 'deleted'})


@app.route('/reminders/edit/<int:reminder_id>', methods=['GET', 'POST'])
def edit_reminder(reminder_id):
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        note_id = request.form['note_id']
        reminder_date = request.form['reminder_date']
        status = request.form['status']
        snoozed_until = request.form['snoozed_until'] if request.form['snoozed_until'] else None

        cur.execute("""
            UPDATE reminders 
            SET note_id=%s, reminder_date=%s, status=%s, snoozed_until=%s 
            WHERE id=%s AND user_id=%s
        """, (note_id, reminder_date, status, snoozed_until, reminder_id, user_id))
        mysql.connection.commit()
        cur.close()
        flash('Reminder updated successfully!', 'success')
        return redirect(url_for('view_reminders'))

    # Fetch reminder and user's non-draft notes
    cur.execute("SELECT id, note_id, reminder_date, status, snoozed_until FROM reminders WHERE id = %s AND user_id = %s", (reminder_id, user_id))
    reminder = cur.fetchone()
    cur.execute('SELECT id, title FROM notes WHERE user_id = %s AND isDraft = FALSE', (user_id,))
    notes = cur.fetchall()
    cur.close()

    if not reminder:
        flash('Reminder not found', 'danger')
        return redirect(url_for('view_reminders'))

    return render_template('edit_reminder.html', reminder=reminder, notes=notes)


if __name__ == '__main__':
    app.run(debug=True)