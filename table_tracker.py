import sqlite3
import time
import threading
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# --- User Model ---
class User(UserMixin):
    def __init__(self, id, username, password_hash, role):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role  # 'admin' or 'staff'

# --- Flask App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
CORS(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# --- Users Setup ---
users = {
    'admin': User('admin', 'admin', generate_password_hash('admin123'), 'admin'),
    'staff1': User('staff1', 'staff1', generate_password_hash('staff123'), 'staff'),
}

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

# --- SQLite Database Setup ---
DATABASE = 'tables.db'

def get_db():
    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row
    return con

def init_db(num_tables=5):
    with get_db() as con:
        con.execute('''
            CREATE TABLE IF NOT EXISTS snooker_tables (
                id INTEGER PRIMARY KEY,
                status TEXT DEFAULT 'idle',    -- idle, running, paused
                start_time REAL DEFAULT NULL,  -- UNIX timestamp when started
                elapsed REAL DEFAULT 0         -- elapsed time in seconds
            )
        ''')
        # Insert tables if not already present
        for tid in range(1, num_tables+1):
            cur = con.execute("SELECT 1 FROM snooker_tables WHERE id=?", (tid,))
            if not cur.fetchone():
                con.execute("INSERT INTO snooker_tables (id) VALUES (?)", (tid,))

# Initialize DB with 5 snooker tables
init_db(5)

# --- Routes ---

@app.route('/')
@login_required
def home():
    return redirect(url_for('snooker'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    return render_template_string('''
        <h2>Login</h2>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for m in messages %}
              <p style="color:red;">{{m}}</p>
            {% endfor %}
          {% endif %}
        {% endwith %}
        <form method="POST">
          Username: <input name="username"><br>
          Password: <input name="password" type="password"><br>
          <button type="submit">Login</button>
        </form>
    ''')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/snooker')
@login_required
def snooker():
    # Simple page that shows tables and buttons
    return render_template_string('''
    <h1>Snooker Table Tracker</h1>
    <p>User: {{current_user.username}} ({{current_user.role}}) <a href="{{ url_for('logout') }}">Logout</a></p>
    <div id="tables"></div>
    <script>
      async function fetchTables(){
        const res = await fetch('/api/snooker/tables');
        const data = await res.json();
        const div = document.getElementById('tables');
        div.innerHTML = '';
        for(const t of data.tables){
          const btnStart = document.createElement('button');
          btnStart.textContent = 'Start';
          btnStart.disabled = (t.status === 'running');
          btnStart.onclick = () => sendAction(t.id, 'start');
          const btnEnd = document.createElement('button');
          btnEnd.textContent = 'End';
          btnEnd.disabled = (t.status !== 'running');
          btnEnd.onclick = () => sendAction(t.id, 'end');
          div.innerHTML += `<div>Table ${t.id}: Status: ${t.status} | Time: ${t.time} </div>`;
          div.appendChild(btnStart);
          div.appendChild(btnEnd);
          div.appendChild(document.createElement('br'));
        }
      }
      async function sendAction(id, action){
        const res = await fetch('/api/snooker/table/' + id + '/action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: action })
        });
        if(res.ok){
          fetchTables();
        } else {
          alert('Action failed');
        }
      }
      setInterval(fetchTables, 1000);
      fetchTables();
    </script>
    ''')

# --- API Endpoints ---

@app.route('/api/snooker/tables')
@login_required
def api_get_tables():
    con = get_db()
    cur = con.execute("SELECT * FROM snooker_tables ORDER BY id")
    rows = cur.fetchall()
    now = time.time()
    tables = []
    for row in rows:
        table_id = row['id']
        status = row['status']
        start_time = row['start_time']
        elapsed = row['elapsed']
        if status == 'running' and start_time is not None:
            # compute updated elapsed time
            running_time = elapsed + (now - start_time)
        else:
            running_time = elapsed
        # format time as HH:MM:SS or 'notime' if zero
        if running_time > 0:
            time_str = format_seconds(int(running_time))
        else:
            time_str = "notime"
        tables.append({
            'id': table_id,
            'status': status,
            'time': time_str
        })
    con.close()
    return jsonify({'tables': tables})

@app.route('/api/snooker/table/<int:table_id>/action', methods=['POST'])
@login_required
def api_table_action(table_id):
    data = request.get_json()
    action = data.get('action')
    if action not in ['start', 'end']:
        return jsonify({'error': 'Invalid action'}), 400
    con = get_db()
    cur = con.execute("SELECT status, start_time, elapsed FROM snooker_tables WHERE id=?", (table_id,))
    row = cur.fetchone()
    if not row:
        con.close()
        return jsonify({'error': 'Table not found'}), 404

    status = row['status']
    start_time = row['start_time']
    elapsed = row['elapsed']
    now = time.time()

    if action == 'start':
        if status == 'idle' or status == 'paused':
            con.execute(
                "UPDATE snooker_tables SET status='running', start_time=?, elapsed=0 WHERE id=?",
                (now, table_id)
            )
        else:
            con.close()
            return jsonify({'error': 'Table already running'}), 400

    elif action == 'end':
        if status == 'running':
            total_elapsed = elapsed + (now - start_time)
            con.execute(
                "UPDATE snooker_tables SET status='idle', start_time=NULL, elapsed=? WHERE id=?",
                (total_elapsed, table_id)
            )
        else:
            con.close()
            return jsonify({'error': 'Table not running'}), 400

    con.commit()
    con.close()
    return jsonify({'success': True})

# --- Helper function ---

def format_seconds(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# --- Background timer updater (Optional) ---
# Since we compute elapsed on demand, no timer thread needed.

# --- Run app ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
