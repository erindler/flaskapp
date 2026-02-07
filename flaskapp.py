from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'mydatabase.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'txt'}

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# SQLite setup
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              password TEXT NOT NULL,
              firstname TEXT NOT NULL,
              lastname TEXT NOT NULL,
              email TEXT NOT NULL,
              address TEXT)''')
conn.commit()
conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def count_words_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        words = content.split()
        return len(words)

@app.route('/')
def index():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    firstname = request.form.get('firstname')
    lastname = request.form.get('lastname')
    email = request.form.get('email')
    address = request.form.get('address')
    
    # Handle file upload
    file_uploaded = False
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(username + '_' + file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            file_uploaded = True

    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""INSERT INTO users (username, password, firstname, lastname, email, address) 
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (username, password, firstname, lastname, email, address))
        conn.commit()
        conn.close()
        return redirect(url_for('profile', username=username))
    except sqlite3.IntegrityError:
        return "Username already exists! Please choose another.", 400

@app.route('/profile/<username>')
def profile(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()

    if user is None:
        return "User not found", 404

    # Check if user has uploaded a file
    user_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                  if f.startswith(username + '_')]
    
    word_count = 0
    file_name = None
    if user_files:
        file_name = user_files[0]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        word_count = count_words_in_file(filepath)

    return render_template('profile.html', user=user, word_count=word_count, file_name=file_name)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            return redirect(url_for('profile', username=username))
        else:
            return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')

@app.route('/download/<filename>')
def download_file(filename):
    # Security check: ensure filename starts with username
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    
    if not os.path.exists(filepath):
        return "File not found", 404
    
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
