from flask import Flask, jsonify, Response, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# SQLite3 Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Enable foreign keys for SQLite3
def enable_foreign_keys():
    if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
        from sqlalchemy import event
        @event.listens_for(db.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

# File Upload Configuration
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    profile_picture = db.Column(db.String(255))

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    category = db.Column(db.String(50))
    isPinned = db.Column(db.Boolean, default=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)
    updatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    isLocal = db.Column(db.Boolean, default=False)
    isDraft = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref='notes')

class Reminder(db.Model):
    __tablename__ = 'reminders'
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('notes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reminder_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Enum('pending', 'completed', 'snoozed', 'canceled'), default='pending')
    snoozed_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    note = db.relationship('Note', backref='reminders')
    user = db.relationship('User', backref='reminders')

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' in session:
        user_id = session['user_id']
        username = session['username']
        notes = Note.query.filter_by(user_id=user_id, isDraft=False).order_by(Note.isPinned.desc(), Note.updatedAt.desc()).all()
        return render_template('index.html', username=username, notes=notes)
    else:
        return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful. You can now login.', 'success')
        return redirect(url_for('user_login'))

    return render_template('register.html')

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
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

    existing_notes = Note.query.filter_by(user_id=user_id, isDraft=False).all()
    existing_notes_set = {(note.title, note.content) for note in existing_notes}

    new_note_ids = []
    for note in guest_notes:
        title = note.get('title', '')
        content = note.get('content', '')
        category = note.get('category', 'Miscellaneous')
        isPinned = note.get('isPinned', False)

        if (title, content) not in existing_notes_set:
            new_note = Note(user_id=user_id, title=title, content=content, category=category, isPinned=isPinned, isDraft=False)
            db.session.add(new_note)
            db.session.flush()
            new_note_ids.append(new_note.id)
            existing_notes_set.add((title, content))

    db.session.commit()
    return jsonify({'status': 'success', 'new_note_ids': new_note_ids})

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    username = session['username']

    notes = Note.query.filter_by(user_id=user_id, isDraft=False).order_by(Note.isPinned.desc(), Note.updatedAt.desc()).all()
    draft_note = Note.query.filter_by(user_id=user_id, isDraft=True).first()
    reminders = db.session.query(Reminder, Note).join(Note).filter(Reminder.user_id == user_id, Reminder.reminder_date >= datetime.utcnow()).order_by(Reminder.reminder_date.asc()).limit(5).all()

    return render_template('dashboard.html', username=username, notes=notes, draft_note=draft_note, reminders=reminders)

@app.route('/create_note', methods=['GET'])
def create_note_page():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    username = session['username']
    draft_note = Note.query.filter_by(user_id=user_id, isDraft=True).first()
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

    draft = Note.query.filter_by(user_id=user_id, isDraft=True).first()
    if draft and isDraft:
        draft.title = title
        draft.content = content
        draft.category = category
        draft.isPinned = isPinned
        draft.updatedAt = datetime.utcnow()
        note_id = draft.id
    else:
        new_note = Note(user_id=user_id, title=title, content=content, category=category, isPinned=isPinned, isDraft=isDraft)
        db.session.add(new_note)
        db.session.flush()
        note_id = new_note.id

    db.session.commit()
    return jsonify({'status': 'success', 'note_id': note_id})

@app.route('/notes/update/<int:note_id>', methods=['POST'])
def update_note(note_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    data = request.get_json()
    note = Note.query.filter_by(id=note_id, user_id=session['user_id']).first()
    if not note:
        return jsonify({'status': 'error', 'message': 'Note not found'}), 404

    note.title = data.get('title')
    note.content = data.get('content')
    note.category = data.get('category')
    note.isPinned = data.get('isPinned')
    note.isDraft = data.get('isDraft', False)
    note.updatedAt = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'updated'})

@app.route('/notes/delete/<int:note_id>', methods=['POST'])
def delete_note(note_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    note = Note.query.filter_by(id=note_id, user_id=session['user_id']).first()
    if not note:
        return jsonify({'status': 'error', 'message': 'Note not found'}), 404

    db.session.delete(note)
    db.session.commit()
    return jsonify({'status': 'deleted'})

@app.route('/notes/search', methods=['GET'])
def search_notes():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    user_id = session['user_id']
    query = request.args.get('query', '')
    notes = Note.query.filter(Note.user_id == user_id, Note.isDraft == False, 
                             (Note.title.ilike(f'%{query}%') | Note.content.ilike(f'%{query}%')))\
                     .order_by(Note.isPinned.desc(), Note.updatedAt.desc()).all()
    
    notes_data = [{'id': note.id, 'title': note.title, 'content': note.content, 'category': note.category, 
                   'isPinned': note.isPinned, 'createdAt': note.createdAt.isoformat(), 
                   'updatedAt': note.updatedAt.isoformat()} 
                  for note in notes]
    return jsonify({'status': 'success', 'notes': notes_data})

@app.route('/notes/export', methods=['GET'])
def export_notes():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    user_id = session['user_id']
    notes = Note.query.filter_by(user_id=user_id, isDraft=False).all()
    export_content = ""
    for note in notes:
        export_content += f"Title: {note.title}\n"
        export_content += f"Category: {note.category}\n"
        export_content += f"Pinned: {note.isPinned}\n"
        export_content += f"Updated At: {note.updatedAt}\n"
        export_content += f"Content:\n{note.content}\n"
        export_content += "-" * 50 + "\n\n"

    return Response(
        export_content,
        mimetype='text/plain',
        headers={'Content-Disposition': 'attachment; filename=notes_export.txt'}
    )

@app.route('/notes/edit/<int:note_id>', methods=['GET'])
def edit_note(note_id):
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    note = Note.query.filter_by(id=note_id, user_id=session['user_id']).first()
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
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        user.first_name = request.form['first_name']
        user.last_name = request.form['last_name']
        user.email = request.form['email']
        password = request.form['password']

        if password:
            user.password = generate_password_hash(password)

        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                user.profile_picture = file_path.replace('\\', '/')

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('view_profile'))

    user_data = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'profile_picture': user.profile_picture.replace('\\', '/') if user.profile_picture else None
    }
    return render_template('update_profile.html', user=user_data)

@app.route('/view_profile')
def view_profile():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('dashboard'))

    user_data = {
        'username': user.username,
        'password': user.password,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'profile_picture': user.profile_picture.replace('\\', '/') if user.profile_picture else None
    }
    return render_template('view_profile.html', user=user_data)

@app.route('/reminders/add', methods=['GET', 'POST'])
def add_reminder():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    if request.method == 'POST':
        note_id = request.form['note_id']
        reminder_date_str = request.form['reminder_date']
        status = request.form['status']
        # Convert reminder_date string to datetime object
        try:
            reminder_date = datetime.strptime(reminder_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid reminder date format', 'danger')
            return redirect(url_for('add_reminder'))

        reminder = Reminder(note_id=note_id, user_id=user_id, reminder_date=reminder_date, status=status)
        db.session.add(reminder)
        db.session.commit()
        flash('Reminder added successfully!', 'success')
        return redirect(url_for('view_reminders'))

    notes = Note.query.filter_by(user_id=user_id, isDraft=False).all()
    return render_template('add_reminder.html', notes=notes)

@app.route('/reminders/view', methods=['GET'])
def view_reminders():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    reminders = db.session.query(Reminder, Note).join(Note).filter(Reminder.user_id == user_id).order_by(Reminder.reminder_date.desc()).all()
    return render_template('view_reminders.html', reminders=reminders)

@app.route('/reminders/delete/<int:reminder_id>', methods=['POST'])
def delete_reminder(reminder_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    reminder = Reminder.query.filter_by(id=reminder_id, user_id=session['user_id']).first()
    if not reminder:
        return jsonify({'status': 'error', 'message': 'Reminder not found'}), 404

    db.session.delete(reminder)
    db.session.commit()
    return jsonify({'status': 'deleted'})

@app.route('/reminders/edit/<int:reminder_id>', methods=['GET', 'POST'])
def edit_reminder(reminder_id):
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    reminder = Reminder.query.filter_by(id=reminder_id, user_id=session['user_id']).first()
    if not reminder:
        flash('Reminder not found', 'danger')
        return redirect(url_for('view_reminders'))

    if request.method == 'POST':
        reminder.note_id = request.form['note_id']
        reminder_date_str = request.form['reminder_date']
        status = request.form['status']
        snoozed_until_str = request.form['snoozed_until']
        # Convert reminder_date string to datetime object
        try:
            reminder.reminder_date = datetime.strptime(reminder_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid reminder date format', 'danger')
            return redirect(url_for('edit_reminder', reminder_id=reminder_id))
        # Convert snoozed_until string to datetime object if provided
        reminder.snoozed_until = datetime.strptime(snoozed_until_str, '%Y-%m-%dT%H:%M') if snoozed_until_str else None
        reminder.status = status
        reminder.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Reminder updated successfully!', 'success')
        return redirect(url_for('view_reminders'))

    notes = Note.query.filter_by(user_id=session['user_id'], isDraft=False).all()
    return render_template('edit_reminder.html', reminder=reminder, notes=notes)

if __name__ == '__main__':
    with app.app_context():
        enable_foreign_keys()
        db.create_all()  # Create tables if they don't exist
    app.run(debug=True)