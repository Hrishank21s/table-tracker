#!/usr/bin/env python3
"""
Professional Table Tracker System - Complete Business Management Solution
Features: Login System, User Management, Snooker & Pool Tracking, Split Bills
"""

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
import webbrowser
import os

class User(UserMixin):
    """User model for authentication system"""
    def __init__(self, id, username, password_hash, role):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role  # 'admin' or 'staff'

class TableTracker:
    """Main Table Tracker Application"""
    
    def __init__(self):
        # Initialize table data
        self.snooker_tables = {
            1: {"status": "idle", "time": "00:00", "rate": 3.0, "amount": 0.0,
                "start_time": None, "elapsed_seconds": 0, "sessions": []},
            2: {"status": "idle", "time": "00:00", "rate": 4.0, "amount": 0.0,
                "start_time": None, "elapsed_seconds": 0, "sessions": []},
            3: {"status": "idle", "time": "00:00", "rate": 4.5, "amount": 0.0,
                "start_time": None, "elapsed_seconds": 0, "sessions": []}
        }
        
        self.pool_tables = {
            1: {"status": "idle", "time": "00:00", "rate": 2.0, "amount": 0.0,
                "start_time": None, "elapsed_seconds": 0, "sessions": []},
            2: {"status": "idle", "time": "00:00", "rate": 2.0, "amount": 0.0,
                "start_time": None, "elapsed_seconds": 0, "sessions": []},
            3: {"status": "idle", "time": "00:00", "rate": 2.5, "amount": 0.0,
                "start_time": None, "elapsed_seconds": 0, "sessions": []}
        }
        
        self.available_rates = [2.0, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5]
        
        # User management
        self.users = {
            'admin': User('admin', 'admin', generate_password_hash('admin123'), 'admin'),
            'staff1': User('staff1', 'staff1', generate_password_hash('staff123'), 'staff')
        }
        
        self.running = True
        self.timer_started = False  # Flag to prevent multiple timer threads
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
        CORS(self.app)
        
        self.setup_authentication()
        self.setup_routes()
    
    def start_timer_if_needed(self):
        """Start timer thread only once, when first request comes in"""
        if not self.timer_started:
            self.timer_started = True
            timer_thread = threading.Thread(target=self.update_timers, daemon=True)
            timer_thread.start()
            print("⏰ Timer system started on first request")
    
    def setup_authentication(self):
        """Configure authentication system"""
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = 'login'
        self.login_manager.login_message = 'Please log in to access this page.'
        
        @self.login_manager.user_loader
        def load_user(user_id):
            return self.users.get(user_id)
    
    def setup_routes(self):
        """Setup all application routes"""
        
        @self.app.before_first_request
        def initialize_timer():
            """Start timer on first request"""
            self.start_timer_if_needed()
        
        @self.app.route('/')
        @login_required
        def home():
            self.start_timer_if_needed()  # Backup timer start
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
        
        @self.app.route('/snooker')
        @login_required
        def snooker():
            self.start_timer_if_needed()  # Ensure timer is running
            return render_template_string(self.get_game_template("snooker"))
        
        @self.app.route('/snooker/mobile')
        @login_required
        def snooker_mobile():
            self.start_timer_if_needed()  # Ensure timer is running
            return render_template_string(self.get_mobile_template("snooker"))
        
        @self.app.route('/pool')
        @login_required
        def pool():
            self.start_timer_if_needed()  # Ensure timer is running
            return render_template_string(self.get_game_template("pool"))
        
        @self.app.route('/pool/mobile')
        @login_required
        def pool_mobile():
            self.start_timer_if_needed()  # Ensure timer is running
            return render_template_string(self.get_mobile_template("pool"))
        
        # User management APIs
        @self.app.route('/api/users', methods=['GET'])
        @login_required
        def get_users():
            if current_user.role != 'admin':
                return jsonify({"error": "Admin access required"}), 403
            
            user_list = []
            for user in self.users.values():
                user_list.append({
                    'username': user.username,
                    'role': user.role,
                    'can_remove': user.username != current_user.username
                })
            
            return jsonify({"success": True, "users": user_list})
        
        @self.app.route('/api/users/add', methods=['POST'])
        @login_required
        def add_user():
            if current_user.role != 'admin':
                return jsonify({"error": "Admin access required"}), 403
            
            try:
                data = request.get_json()
                username = data.get('username')
                password = data.get('password')
                role = data.get('role')
                
                if not username or not password or role not in ['admin', 'staff']:
                    return jsonify({"error": "Invalid user data"}), 400
                
                if username in self.users:
                    return jsonify({"error": "Username already exists"}), 400
                
                password_hash = generate_password_hash(password)
                new_user = User(username, username, password_hash, role)
                self.users[username] = new_user
                
                print(f"New {role} user created: {username} by {current_user.username}")
                
                return jsonify({
                    "success": True,
                    "message": f"{role.title()} user '{username}' created successfully"
                })
                
            except Exception as e:
                print(f"Add User Error: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/users/remove', methods=['POST'])
        @login_required
        def remove_user():
            if current_user.role != 'admin':
                return jsonify({"error": "Admin access required"}), 403
            
            try:
                data = request.get_json()
                username = data.get('username')
                
                if not username:
                    return jsonify({"error": "Username is required"}), 400
                
                if username not in self.users:
                    return jsonify({"error": "User not found"}), 404
                
                if username == current_user.username:
                    return jsonify({"error": "Cannot remove yourself"}), 400
                
                removed_user = self.users[username]
                del self.users[username]
                
                print(f"User removed: {username} ({removed_user.role}) by {current_user.username}")
                
                return jsonify({
                    "success": True,
                    "message": f"User '{username}' removed successfully"
                })
                
            except Exception as e:
                print(f"Remove User Error: {e}")
                return jsonify({"error": str(e)}), 500
        
        # Table management APIs
        @self.app.route('/api/<game_type>/tables', methods=['GET'])
        @login_required
        def get_tables(game_type):
            self.start_timer_if_needed()  # Ensure timer is running for API calls
            tables = self.snooker_tables if game_type == 'snooker' else self.pool_tables
            # Create serializable copy without datetime objects
            serializable_tables = {}
            for tid, tdata in tables.items():
                serializable_tables[tid] = {
                    "status": tdata["status"],
                    "time": tdata["time"],
                    "rate": tdata["rate"],
                    "amount": tdata["amount"],
                    "sessions": tdata["sessions"],
                }
            return jsonify({
                "success": True,
                "tables": serializable_tables,
                "available_rates": self.available_rates,
                "timestamp": datetime.now().isoformat()
            })
        
        @self.app.route('/api/<game_type>/table/<int:table_id>/action', methods=['POST'])
        @login_required
        def table_action(game_type, table_id):
            try:
                data = request.get_json()
                action = data.get('action')
                
                tables = self.snooker_tables if game_type == 'snooker' else self.pool_tables
                
                if table_id not in tables or action not in ['start', 'pause', 'end']:
                    return jsonify({"error": "Invalid request"}), 400
                
                result = self.handle_table_action(game_type, table_id, action)
                print(f"Action: {game_type.title()} Table {table_id} - {action} - User: {current_user.username}")
                
                return jsonify({
                    "success": True,
                    "table": table_id,
                    "action": action,
                    "result": result,
                    "tables": tables
                })
                
            except Exception as e:
                print(f"API Error: {e}")
                return jsonify({"error": str(e)}), 500
        
        # (Keep all your other API routes the same - rate update, clear, split, etc.)
        # ... rest of your API routes unchanged ...
    
    def handle_table_action(self, game_type, table_id, action):
        """Handle table actions"""
        tables = self.snooker_tables if game_type == 'snooker' else self.pool_tables
        table = tables[table_id]
        
        if action == 'start':
            if table['status'] == 'idle':
                table['status'] = 'running'
                table['start_time'] = datetime.now()
                table['elapsed_seconds'] = 0
                table['session_start_time'] = datetime.now().strftime("%H:%M:%S")
                return f"{game_type.title()} Table {table_id} started"
        
        elif action == 'pause':
            if table['status'] == 'running':
                table['status'] = 'paused'
                return f"{game_type.title()} Table {table_id} paused"
            elif table['status'] == 'paused':
                table['status'] = 'running'
                table['start_time'] = datetime.now()
                return f"{game_type.title()} Table {table_id} resumed"
        
        elif action == 'end':
            if table['status'] in ['running', 'paused']:
                duration_minutes = table['elapsed_seconds'] / 60
                amount = duration_minutes * table['rate']
                end_time = datetime.now().strftime("%H:%M:%S")
                
                session = {
                    "start_time": table.get('session_start_time', '00:00:00'),
                    "end_time": end_time,
                    "duration": round(duration_minutes, 1),
                    "amount": round(amount, 2),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "user": current_user.username
                }
                table['sessions'].append(session)
                
                table['status'] = 'idle'
                table['time'] = '00:00'
                table['amount'] = 0
                table['start_time'] = None
                table['elapsed_seconds'] = 0
                table['session_start_time'] = None
                
                return f"{game_type.title()} Table {table_id} ended - ₹{amount:.2f} for {duration_minutes:.1f} minutes"
        
        return "No action taken"
    
    def update_timers(self):
        """Background timer thread"""
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
    
    # (Include all your template methods here - get_login_template, get_home_template, etc.)
    # They remain exactly the same as in your original code...

# Create tracker instance and expose app for Gunicorn
tracker = TableTracker()
app = tracker.app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
