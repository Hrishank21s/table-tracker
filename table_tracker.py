import json
import threading
import time
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import socket
import os

class User(UserMixin):
    def __init__(self, id, username, password_hash, role):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role  # 'admin' or 'staff'

class TableTracker:
    def __init__(self):
        self.snooker_tables = {
            1: {"status": "idle", "time": "00:00", "rate": 3.0, "amount": 0.0, "start_time": None, "elapsed_seconds": 0, "sessions": []},
            2: {"status": "idle", "time": "00:00", "rate": 4.0, "amount": 0.0, "start_time": None, "elapsed_seconds": 0, "sessions": []},
            3: {"status": "idle", "time": "00:00", "rate": 4.5, "amount": 0.0, "start_time": None, "elapsed_seconds": 0, "sessions": []}
        }
        self.pool_tables = {
            1: {"status": "idle", "time": "00:00", "rate": 2.0, "amount": 0.0, "start_time": None, "elapsed_seconds": 0, "sessions": []},
            2: {"status": "idle", "time": "00:00", "rate": 2.0, "amount": 0.0, "start_time": None, "elapsed_seconds": 0, "sessions": []},
            3: {"status": "idle", "time": "00:00", "rate": 2.5, "amount": 0.0, "start_time": None, "elapsed_seconds": 0, "sessions": []}
        }
        self.available_rates = [2.0, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5]
        self.users = {
            'admin': User('admin', 'admin', generate_password_hash('admin123'), 'admin'),
            'staff1': User('staff1', 'staff1', generate_password_hash('staff123'), 'staff')
        }
        self.running = True
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
        CORS(self.app)
        self.setup_authentication()
        self.setup_routes()
        threading.Thread(target=self.update_timers, daemon=True).start()

    def setup_authentication(self):
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = 'login'
        self.login_manager.login_message = 'Please log in to access this page.'

        @self.login_manager.user_loader
        def load_user(user_id):
            return self.users.get(user_id)

    def setup_routes(self):
        @self.app.route('/')
        @login_required
        def home():
            return render_template_string(self.get_home_template())

        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                user = self.users.get(username)
                if user and check_password_hash(user.password_hash, password):
                    login_user(user)
                    next_page = request.args.get('next')
                    return redirect(next_page) if next_page else redirect(url_for('home'))
                else:
                    flash('Invalid username or password')
            return render_template_string(self.get_login_template())

        @self.app.route('/logout')
        @login_required
        def logout():
            logout_user()
            return redirect(url_for('login'))

        # Add the rest of your routes here! For brevity, only some included above.

    # ...SNIP: include your other methods here, as in your long original file...

    def update_timers(self):
        print("⏰ Timer system started")
        while self.running:
            try:
                updated = False
                for tables in [self.snooker_tables, self.pool_tables]:
                    for table_id, table in tables.items():
                        if table['status'] == 'running' and table['start_time']:
                            table['elapsed_seconds'] += 1
                            minutes = table['elapsed_seconds'] // 60
                            seconds = table['elapsed_seconds'] % 60
                            table['time'] = f"{minutes:02d}:{seconds:02d}"
                            duration_minutes = table['elapsed_seconds'] / 60
                            table['amount'] = duration_minutes * table['rate']
                            table['start_time'] = datetime.now()
                            updated = True
                if updated:
                    print(f"⏱️ Timers updated: {datetime.now().strftime('%H:%M:%S')}")
                time.sleep(1)
            except Exception as e:
                print(f"Timer error: {e}")
                time.sleep(1)

    def get_login_template(self):
        return """
        <!doctype html>
        <title>Table Tracker - Login</title>
        <h1>🎯 Table Tracker</h1>
        <form action="" method="post">
            <p><input type=text name=username placeholder="Username">
            <p><input type=password name=password placeholder="Password">
            <p><input type=submit value=Login>
        </form>
        {% with messages = get_flashed_messages() %}
        {% if messages %}
            <ul>
            {% for message in messages %}
                <li>{{ message }}</li>
            {% endfor %}
            </ul>
        {% endif %}
        {% endwith %}
        """

    def get_home_template(self):
        return f"""
        <!doctype html>
        <title>Table Tracker - Home</title>
        <h2>👤 {current_user.username} ({current_user.role.title()})</h2>
        <a href="{{{{ url_for('logout') }}}}">Logout</a>
        <h1>🎯 Table Tracker</h1>
        <p>Professional Table Management System</p>
        <p>Welcome, {current_user.username}!</p>
        <!-- Add your UI here -->
        """
        
# Deployment-supporting entry point
tracker = TableTracker()
app = tracker.app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
