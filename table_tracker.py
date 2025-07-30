#!/usr/bin/env python3
import json
import threading
import time
import os
from datetime import datetime
import socket
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

class User(UserMixin):
    def __init__(self, id, username, password_hash, role):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role  # 'admin' or 'staff'

class TableTracker:
    def __init__(self):
        # Initialize table data
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
        
        # Start timer immediately after setup
        self.start_timer_if_needed()
    
    def start_timer_if_needed(self):
        """Start timer thread only once"""
        if not self.timer_started:
            self.timer_started = True
            timer_thread = threading.Thread(target=self.update_timers, daemon=True)
            timer_thread.start()
            print("⏰ Timer system started")
    
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
            return render_template_string(self.get_game_template("snooker"))
        
        @self.app.route('/snooker/mobile')
        @login_required
        def snooker_mobile():
            return render_template_string(self.get_mobile_template("snooker"))
        
        @self.app.route('/pool')
        @login_required
        def pool():
            return render_template_string(self.get_game_template("pool"))
        
        @self.app.route('/pool/mobile')
        @login_required
        def pool_mobile():
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
        
        @self.app.route('/api/<game_type>/table/<int:table_id>/rate', methods=['POST'])
        @login_required
        def update_rate(game_type, table_id):
            try:
                data = request.get_json()
                new_rate = float(data.get('rate'))
                tables = self.snooker_tables if game_type == 'snooker' else self.pool_tables
                if table_id not in tables:
                    return jsonify({"error": "Invalid table ID"}), 400
                if new_rate not in self.available_rates:
                    return jsonify({"error": "Invalid rate"}), 400
                if tables[table_id]["status"] != "idle":
                    return jsonify({"error": "Cannot change rate while table is running"}), 400
                tables[table_id]["rate"] = new_rate
                print(f"{game_type.title()} Table {table_id} rate updated to ₹{new_rate}/min by {current_user.username}")
                return jsonify({
                    "success": True,
                    "table": table_id,
                    "new_rate": new_rate,
                    "tables": tables,
                })
            except Exception as e:
                print(f"Rate Update Error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/<game_type>/table/<int:table_id>/clear', methods=['POST'])
        @login_required
        def clear_table(game_type, table_id):
            try:
                tables = self.snooker_tables if game_type == 'snooker' else self.pool_tables
                if table_id not in tables:
                    return jsonify({"error": "Invalid table ID"}), 400
                tables[table_id]["sessions"].clear()
                print(f"{game_type.title()} Table {table_id} data cleared by {current_user.username}")
                return jsonify({
                    "success": True,
                    "table": table_id,
                    "message": f"Table {table_id} data cleared",
                    "tables": tables,
                })
            except Exception as e:
                print(f"Clear Error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/<game_type>/table/<int:table_id>/split', methods=['POST'])
        @login_required
        def split_bill(game_type, table_id):
            try:
                data = request.get_json()
                players = int(data.get('players', 0))
                if not players or players < 1:
                    return jsonify({"error": "Invalid number of players"}), 400
                
                tables = self.snooker_tables if game_type == 'snooker' else self.pool_tables
                if table_id not in tables:
                    return jsonify({"error": "Invalid table"}), 400
                
                table = tables[table_id]
                if not table['sessions']:
                    return jsonify({"error": "No sessions to split"}), 400
                
                total_amount = table['sessions'][-1]['amount']
                return jsonify({
                    "success": True,
                    "total_amount": total_amount,
                    "players": players,
                    "per_player": round(total_amount / players, 2)
                })
            except Exception as e:
                print(f"Split bill error: {e}")
                return jsonify({"error": str(e)}), 500

    def update_timers(self):
        """Update all table timers continuously"""
        while self.running:
            try:
                self.update_table_timers(self.snooker_tables)
                self.update_table_timers(self.pool_tables)
                time.sleep(1)
            except Exception as e:
                print(f"Timer Error: {e}")

    def update_table_timers(self, tables):
        """Update timers for a specific set of tables"""
        for table in tables.values():
            if table["status"] == "running":
                if table["start_time"] is None:
                    table["start_time"] = time.time()
                table["elapsed_seconds"] = int(time.time() - table["start_time"])
                table["time"] = self.format_time(table["elapsed_seconds"])
                table["amount"] = round((table["elapsed_seconds"] / 60) * table["rate"], 2)

    def handle_table_action(self, game_type, table_id, action):
        """Handle table start/pause/end actions"""
        tables = self.snooker_tables if game_type == "snooker" else self.pool_tables
        table = tables[table_id]
        
        if action == "start":
            if table["status"] in ["idle", "paused"]:
                if table["status"] == "idle":
                    table["elapsed_seconds"] = 0
                    table["amount"] = 0.0
                table["status"] = "running"
                table["start_time"] = time.time()
                
        elif action == "pause":
            if table["status"] == "running":
                table["status"] = "paused"
                table["start_time"] = None
                
        elif action == "end":
            if table["status"] in ["running", "paused"]:
                session = {
                    "duration": round(table["elapsed_seconds"] / 60, 2),
                    "amount": table["amount"],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                table["sessions"].append(session)
                table["status"] = "idle"
                table["time"] = "00:00"
                table["start_time"] = None
                table["elapsed_seconds"] = 0
                table["amount"] = 0.0
        
        return {"status": table["status"]}

    def format_time(self, seconds):
        """Format seconds into MM:SS"""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def get_login_template(self):
        """Return login page template"""
        return """
        {% extends "base.html" %}
        {% block title %}Login - Table Tracker{% endblock %}
        {% block content %}
        <div class="container">
            <div style="max-width: 400px; margin: 50px auto; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
                <h2 style="text-align: center; margin-bottom: 30px;">Login</h2>
                {% with messages = get_flashed_messages() %}
                    {% if messages %}
                        {% for message in messages %}
                            <div style="background: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
                                {{ message }}
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                <form method="POST">
                    <div style="margin-bottom: 20px;">
                        <label for="username" style="display: block; margin-bottom: 5px;">Username</label>
                        <input type="text" id="username" name="username" required style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>
                    <div style="margin-bottom: 20px;">
                        <label for="password" style="display: block; margin-bottom: 5px;">Password</label>
                        <input type="password" id="password" name="password" required style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>
                    <button type="submit" style="width: 100%; background: #2ecc71; color: white; padding: 10px; border: none; border-radius: 4px; cursor: pointer;">Login</button>
                </form>
            </div>
        </div>
        {% endblock %}
        """

    def get_home_template(self):
        """Return home page template"""
        return """
        {% extends "base.html" %}
        {% block title %}Home - Table Tracker{% endblock %}
        {% block content %}
        <div class="container">
            <div style="text-align: center; margin: 50px 0;">
                <h1>Welcome to Table Tracker</h1>
                <p>Select a game type to manage tables</p>
                
                <div style="display: flex; justify-content: center; gap: 20px; margin-top: 30px;">
                    <div class="game-card" onclick="window.location.href='{{ url_for('snooker') }}'">
                        <i class="fas fa-circle fa-3x" style="color: #3498db;"></i>
                        <h2>Snooker</h2>
                        <p>Manage Snooker Tables</p>
                    </div>
                    
                    <div class="game-card" onclick="window.location.href='{{ url_for('pool') }}'">
                        <i class="fas fa-circle fa-3x" style="color: #2ecc71;"></i>
                        <h2>Pool</h2>
                        <p>Manage Pool Tables</p>
                    </div>
                </div>
                
                {% if current_user.role == 'admin' %}
                <div style="margin-top: 50px;">
                    <h3>User Management</h3>
                    <div id="usersList" style="margin: 20px 0;"></div>
                    
                    <button onclick="showAddUserModal()" class="btn btn-success">
                        <i class="fas fa-user-plus"></i> Add User
                    </button>
                </div>
                
                <!-- Add User Modal -->
                <div id="addUserModal" class="modal">
                    <div class="modal-content">
                        <h3>Add New User</h3>
                        <form id="addUserForm">
                            <div class="form-group">
                                <label>Username:</label>
                                <input type="text" name="username" required>
                            </div>
                            <div class="form-group">
                                <label>Password:</label>
                                <input type="password" name="password" required>
                            </div>
                            <div class="form-group">
                                <label>Role:</label>
                                <select name="role">
                                    <option value="staff">Staff</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                            <div class="form-actions">
                                <button type="submit" class="btn btn-success">Add User</button>
                                <button type="button" onclick="hideAddUserModal()" class="btn btn-secondary">Cancel</button>
                            </div>
                        </form>
                    </div>
                </div>
                {% endif %}
                
                <div style="margin-top: 30px;">
                    <a href="{{ url_for('logout') }}" class="btn btn-danger">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </a>
                </div>
            </div>
        </div>

        {% if current_user.role == 'admin' %}
        <script>
        // User Management
        async function loadUsers() {
            try {
                const response = await fetch('/api/users');
                const data = await response.json();
                
                if (data.success) {
                    const usersList = document.getElementById('usersList');
                    usersList.innerHTML = `
                        <div class="user-grid">
                            ${data.users.map(user => `
                                <div class="user-card">
                                    <div class="user-info">
                                        <i class="fas fa-user"></i>
                                        <span>${user.username}</span>
                                        <span class="user-role">${user.role}</span>
                                    </div>
                                    ${user.can_remove ? `
                                        <button onclick="removeUser('${user.username}')" class="btn btn-danger btn-sm">
                                            <i class="fas fa-user-minus"></i>
                                        </button>
                                    ` : ''}
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Error loading users:', error);
            }
        }

        // Load users on page load
        if (document.getElementById('usersList')) {
            loadUsers();
        }

        async function removeUser(username) {
            if (!confirm(`Are you sure you want to remove user "${username}"?`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/users/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username })
                });
                
                const data = await response.json();
                if (data.success) {
                    loadUsers();
                } else {
                    alert(data.error || 'Failed to remove user');
                }
            } catch (error) {
                console.error('Error removing user:', error);
                alert('Failed to remove user');
            }
        }

        // Modal functions
        function showAddUserModal() {
            document.getElementById('addUserModal').style.display = 'flex';
        }

        function hideAddUserModal() {
            document.getElementById('addUserModal').style.display = 'none';
        }

        // Add user form submission
        document.getElementById('addUserForm').onsubmit = async function(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const userData = {
                username: formData.get('username'),
                password: formData.get('password'),
                role: formData.get('role')
            };
            
            try {
                const response = await fetch('/api/users/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(userData)
                });
                
                const data = await response.json();
                if (data.success) {
                    hideAddUserModal();
                    loadUsers();
                    e.target.reset();
                } else {
                    alert(data.error || 'Failed to add user');
                }
            } catch (error) {
                console.error('Error adding user:', error);
                alert('Failed to add user');
            }
        };

        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('addUserModal');
            if (event.target === modal) {
                hideAddUserModal();
            }
        }
        </script>
        {% endif %}
        {% endblock %}
        """

    def get_game_template(self, game_type):
        """Return game management page template"""
        return """
        {% extends "base.html" %}

        {% block title %}{{ game_type.title() }} - Table Tracker{% endblock %}

        {% block styles %}
        <style>
            .table-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                padding: 20px;
            }
            
            .table-card {
                background: {% if game_type == 'pool' %}rgba(52, 152, 219, 0.1){% else %}rgba(46, 204, 113, 0.1){% endif %};
                border: 2px solid {% if game_type == 'pool' %}#3498db{% else %}#2ecc71{% endif %};
                border-radius: 10px;
                padding: 20px;
                text-align: center;
            }
            
            .table-card.running { border-color: #2ecc71; background: rgba(46, 204, 113, 0.2); }
            .table-card.paused { border-color: #f39c12; background: rgba(243, 156, 18, 0.2); }
            
            .time-display { font-size: 48px; font-weight: bold; margin: 20px 0; }
            .amount-display { font-size: 24px; color: #2ecc71; margin: 10px 0; }
            
            .action-buttons { margin: 15px 0; }
            .action-buttons button { margin: 0 5px; }
            
            .sessions-list {
                margin-top: 20px;
                max-height: 200px;
                overflow-y: auto;
                background: rgba(255, 255, 255, 0.5);
                border-radius: 5px;
                padding: 10px;
            }
            
            .session-item {
                display: flex;
                justify-content: space-between;
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            
            .session-item:last-child { border-bottom: none; }
            
            @media (max-width: 768px) {
                .table-grid { grid-template-columns: 1fr; }
                .time-display { font-size: 36px; }
                .amount-display { font-size: 20px; }
            }

            .split-bill-modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }

            .modal-content {
                background: white;
                padding: 20px;
                border-radius: 10px;
                min-width: 300px;
            }

            .split-result {
                margin-top: 10px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 5px;
            }

            .form-group {
                margin: 15px 0;
            }

            .form-group label {
                display: block;
                margin-bottom: 5px;
            }

            .form-group input,
            .form-group select {
                width: 100%;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }

            .form-actions {
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                margin-top: 20px;
            }

            .rate-selector {
                margin: 10px 0;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .rate-selector select {
                margin-left: 10px;
                padding: 5px;
                border-radius: 4px;
            }
        </style>
        {% endblock %}

        {% block content %}
        <div class="container">
            <div style="text-align: center; margin: 20px 0;">
                <h2><i class="fas fa-table"></i> {{ game_type.title() }} Tables</h2>
                <p>Auto-updates every 1 second</p>
                <div style="margin: 10px 0;">
                    <a href="{{ url_for(game_type + '_mobile') }}" class="btn btn-primary">Mobile View</a>
                    <a href="{{ url_for('home') }}" class="btn btn-success">Home</a>
                </div>
            </div>
            
            <div id="tablesContainer" class="table-grid">
                <div style="text-align: center; padding: 20px;">Loading...</div>
            </div>
        </div>

        <!-- Split Bill Modal -->
        <div id="splitBillModal" class="split-bill-modal">
            <div class="modal-content">
                <h3>Split Bill</h3>
                <div id="splitBillForm">
                    <div class="form-group">
                        <label>Number of Players:</label>
                        <input type="number" id="playerCount" min="1" value="2">
                    </div>
                    <div id="splitResult" class="split-result" style="display: none;"></div>
                    <div class="form-actions">
                        <button onclick="calculateSplit()" class="btn btn-success">Calculate</button>
                        <button onclick="hideSplitModal()" class="btn btn-secondary">Close</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
        let tables = {};
        let splitTableId = null;

        function showSplitModal(tableId) {
            splitTableId = tableId;
            document.getElementById('splitBillModal').style.display = 'flex';
            document.getElementById('splitResult').style.display = 'none';
            document.getElementById('playerCount').value = '2';
        }

        function hideSplitModal() {
            document.getElementById('splitBillModal').style.display = 'none';
            splitTableId = null;
        }

        async function calculateSplit() {
            try {
                const players = parseInt(document.getElementById('playerCount').value);
                if (!players || players < 1) {
                    alert('Please enter a valid number of players');
                    return;
                }
                
                const response = await fetch(`/api/{{ game_type }}/table/${splitTableId}/split`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ players })
                });
                
                const data = await response.json();
                if (data.success) {
                    const resultDiv = document.getElementById('splitResult');
                    resultDiv.innerHTML = `
                        <p><strong>Total Amount:</strong> ₹${data.total_amount}</p>
                        <p><strong>Players:</strong> ${data.players}</p>
                        <p><strong>Per Player:</strong> ₹${data.per_player}</p>
                    `;
                    resultDiv.style.display = 'block';
                } else {
                    alert(data.error || 'Failed to calculate split');
                }
            } catch (error) {
                console.error('Split calculation error:', error);
                alert('Failed to calculate split');
            }
        }

        async function loadTables() {
            try {
                const response = await fetch(`/api/{{ game_type }}/tables`);
                const data = await response.json();
                
                if (data.success) {
                    tables = data.tables;
                    renderTables(data.available_rates);
                }
            } catch (error) {
                console.error('Error loading tables:', error);
            }
        }

        function renderTables(available_rates) {
            const container = document.getElementById('tablesContainer');
            container.innerHTML = Object.entries(tables).map(([id, table]) => `
                <div class="table-card ${table.status}">
                    <h3>Table ${id}</h3>
                    <div class="time-display">${table.time}</div>
                    <div class="amount-display">₹${table.amount.toFixed(2)}</div>
                    <div class="rate-selector">
                        Rate: 
                        <select onchange="updateRate(${id}, this.value)" 
                                ${table.status !== 'idle' ? 'disabled' : ''}>
                            ${available_rates.map(rate => 
                                `<option value="${rate}" ${rate === table.rate ? 'selected' : ''}>
                                    ₹${rate}/min
                                </option>`
                            ).join('')}
                        </select>
                    </div>
                    
                    <div class="action-buttons">
                        ${table.status === 'idle' ? `
                            <button onclick="tableAction(${id}, 'start')" class="btn btn-success">
                                <i class="fas fa-play"></i> START
                            </button>
                        ` : ''}
                        
                        ${table.status === 'running' ? `
                            <button onclick="tableAction(${id}, 'pause')" class="btn btn-warning">
                                <i class="fas fa-pause"></i> PAUSE
                            </button>
                            <button onclick="tableAction(${id}, 'end')" class="btn btn-danger">
                                <i class="fas fa-stop"></i> END
                            </button>
                        ` : ''}
                        
                        ${table.status === 'paused' ? `
                            <button onclick="tableAction(${id}, 'start')" class="btn btn-success">
                                <i class="fas fa-play"></i> RESUME
                            </button>
                            <button onclick="tableAction(${id}, 'end')" class="btn btn-danger">
                                <i class="fas fa-stop"></i> END
                            </button>
                        ` : ''}
                    </div>
                    
                    <div class="sessions-list">
                        ${table.sessions.length === 0 ? 
                            '<p style="color: #666;">No recent sessions</p>' :
                            table.sessions.slice().reverse().map(session => `
                                <div class="session-item">
                                    <span>₹${session.amount.toFixed(2)} (${session.duration} min)</span>
                                    <button onclick="showSplitModal(${id})" 
                                            class="btn btn-sm btn-info">
                                        <i class="fas fa-users"></i> Split
                                    </button>
                                </div>
                            `).join('')
                        }
                    </div>

                    ${table.sessions.length > 0 ? `
                        <button onclick="clearSessions(${id})" class="btn btn-secondary btn-sm" style="margin-top: 10px;">
                            <i class="fas fa-trash"></i> Clear History
                        </button>
                    ` : ''}
                </div>
            `).join('');
        }

        async function tableAction(tableId, action) {
            try {
                const response = await fetch(`/api/{{ game_type }}/table/${tableId}/action`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action })
                });
                
                const data = await response.json();
                if (data.success) {
                    tables = data.tables;
                    renderTables(document.querySelector('.rate-selector select').options);
                    
                    // Haptic feedback on mobile
                    if (navigator.vibrate) {
                        navigator.vibrate(100);
                    }
                }
            } catch (error) {
                console.error('Error with table action:', error);
            }
        }

        async function updateRate(tableId, newRate) {
            try {
                const response = await fetch(`/api/{{ game_type }}/table/${tableId}/rate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ rate: parseFloat(newRate) })
                });
                
                const data = await response.json();
                if (data.success) {
                    tables = data.tables;
                    renderTables(document.querySelector('.rate-selector select').options);
                } else {
                    alert(data.error || 'Failed to update rate');
                }
            } catch (error) {
                console.error('Error updating rate:', error);
            }
        }

        async function clearSessions(tableId) {
            if (!confirm('Are you sure you want to clear the session history for this table?')) {
                return;
            }
            
            try {
                const response = await fetch(`/api/{{ game_type }}/table/${tableId}/clear`, {
                    method: 'POST'
                });
                
                const data = await response.json();
                if (data.success) {
                    tables = data.tables;
                    renderTables(document.querySelector('.rate-selector select').options);
                } else {
                    alert(data.error || 'Failed to clear sessions');
                }
            } catch (error) {
                console.error('Error clearing sessions:', error);
            }
        }

        // Initialize and auto-update
        loadTables();
        setInterval(loadTables, 1000);

        // Close modal when clicking outside
        window.onclick = function(event) {
            if (event.target === document.getElementById('splitBillModal')) {
                hideSplitModal();
            }
        }
        </script>
        {% endblock %}
        """

    def get_mobile_template(self, game_type):
        """Return mobile view template"""
        with open(os.path.join(os.path.dirname(__file__), "templates/mobile.html")) as f:
            return f.read()

def create_app():
    """Create and configure the Flask application"""
    tracker = TableTracker()
    return tracker.app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
