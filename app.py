#!/usr/bin/env python3
"""
Professional Table Tracker System - Optimized for Render
Features: Login System, User Management, Snooker & Pool Tracking, Split Bills
"""

import json
import threading
import time
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin):
    """User model for authentication system"""
    def __init__(self, id, username, password_hash, role):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role

class TableTracker:
    """Main Table Tracker Application"""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key-change-in-production')
        CORS(self.app)
        
        # Initialize data
        self.init_data()
        self.setup_authentication()
        self.setup_routes()
        self.running = True
        
        # Start timer thread
        timer_thread = threading.Thread(target=self.update_timers, daemon=True)
        timer_thread.start()
    
    def init_data(self):
        """Initialize table and user data"""
        self.snooker_tables = {
            1: self.create_table(3.0), 2: self.create_table(4.0), 3: self.create_table(4.5)
        }
        self.pool_tables = {
            1: self.create_table(2.0), 2: self.create_table(2.0), 3: self.create_table(2.5)
        }
        self.available_rates = [2.0, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5]
        
        # Default users
        self.users = {
            'admin': User('admin', 'admin', generate_password_hash('admin123'), 'admin'),
            'staff1': User('staff1', 'staff1', generate_password_hash('staff123'), 'staff')
        }
    
    def create_table(self, rate):
        """Create a new table with default values"""
        return {
            "status": "idle", "time": "00:00", "rate": rate, "amount": 0.0,
            "start_time": None, "elapsed_seconds": 0, "sessions": []
        }
    
    def setup_authentication(self):
        """Configure authentication system"""
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = 'login'
        
        @self.login_manager.user_loader
        def load_user(user_id):
            return self.users.get(user_id)
    
    def setup_routes(self):
        """Setup all application routes"""
        
        @self.app.route('/')
        @login_required
        def home():
            return render_template('home.html', current_user=current_user)
        
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                user = self.users.get(username)
                
                if user and check_password_hash(user.password_hash, password):
                    login_user(user)
                    return redirect(request.args.get('next') or url_for('home'))
                flash('Invalid credentials')
            return render_template('login.html')
        
        @self.app.route('/logout')
        @login_required
        def logout():
            logout_user()
            return redirect(url_for('login'))
        
        @self.app.route('/<game_type>')
        @login_required
        def game_page(game_type):
            if game_type not in ['snooker', 'pool']:
                return redirect(url_for('home'))
            return render_template('game.html', game_type=game_type, current_user=current_user)
        
        @self.app.route('/<game_type>/mobile')
        @login_required
        def mobile_page(game_type):
            if game_type not in ['snooker', 'pool']:
                return redirect(url_for('home'))
            return render_template('mobile.html', game_type=game_type, current_user=current_user)
        
        # API Routes
        self.setup_api_routes()
    
    def setup_api_routes(self):
        """Setup API routes"""
        
        @self.app.route('/api/users', methods=['GET'])
        @login_required
        def get_users():
            if current_user.role != 'admin':
                return jsonify({"error": "Admin access required"}), 403
            
            user_list = [{
                'username': user.username,
                'role': user.role,
                'can_remove': user.username != current_user.username
            } for user in self.users.values()]
            return jsonify({"success": True, "users": user_list})
        
        @self.app.route('/api/users/add', methods=['POST'])
        @login_required
        def add_user():
            if current_user.role != 'admin':
                return jsonify({"error": "Admin access required"}), 403
            
            data = request.get_json()
            username, password, role = data.get('username'), data.get('password'), data.get('role')
            
            if not all([username, password]) or role not in ['admin', 'staff']:
                return jsonify({"error": "Invalid user data"}), 400
            
            if username in self.users:
                return jsonify({"error": "Username already exists"}), 400
            
            self.users[username] = User(username, username, generate_password_hash(password), role)
            return jsonify({"success": True, "message": f"{role.title()} user '{username}' created"})
        
        @self.app.route('/api/users/remove', methods=['POST'])
        @login_required
        def remove_user():
            if current_user.role != 'admin':
                return jsonify({"error": "Admin access required"}), 403
            
            username = request.get_json().get('username')
            if not username or username not in self.users:
                return jsonify({"error": "User not found"}), 400
            
            if username == current_user.username:
                return jsonify({"error": "Cannot remove yourself"}), 400
            
            del self.users[username]
            return jsonify({"success": True, "message": f"User '{username}' removed"})
        
        @self.app.route('/api/<game_type>/tables')
        @login_required
        def get_tables(game_type):
            tables = self.snooker_tables if game_type == 'snooker' else self.pool_tables
            return jsonify({
                "success": True, "tables": tables, "available_rates": self.available_rates,
                "timestamp": datetime.now().isoformat()
            })
        
        @self.app.route('/api/<game_type>/table/<int:table_id>/action', methods=['POST'])
        @login_required
        def table_action(game_type, table_id):
            action = request.get_json().get('action')
            tables = self.snooker_tables if game_type == 'snooker' else self.pool_tables
            
            if table_id not in tables or action not in ['start', 'pause', 'end']:
                return jsonify({"error": "Invalid request"}), 400
            
            result = self.handle_table_action(game_type, table_id, action)
            return jsonify({"success": True, "result": result, "tables": tables})
        
        @self.app.route('/api/<game_type>/table/<int:table_id>/rate', methods=['POST'])
        @login_required
        def update_rate(game_type, table_id):
            new_rate = float(request.get_json().get('rate'))
            tables = self.snooker_tables if game_type == 'snooker' else self.pool_tables
            
            if table_id not in tables or new_rate not in self.available_rates:
                return jsonify({"error": "Invalid table or rate"}), 400
            
            if tables[table_id]['status'] != 'idle':
                return jsonify({"error": "Cannot change rate while table is running"}), 400
            
            tables[table_id]['rate'] = new_rate
            return jsonify({"success": True, "tables": tables})
        
        @self.app.route('/api/<game_type>/table/<int:table_id>/clear', methods=['POST'])
        @login_required
        def clear_table(game_type, table_id):
            tables = self.snooker_tables if game_type == 'snooker' else self.pool_tables
            
            if table_id not in tables:
                return jsonify({"error": "Invalid table"}), 400
            
            tables[table_id]['sessions'] = []
            return jsonify({"success": True, "tables": tables})
        
        @self.app.route('/api/<game_type>/table/<int:table_id>/split', methods=['POST'])
        @login_required
        def split_bill(game_type, table_id):
            players = int(request.get_json().get('players', 0))
            tables = self.snooker_tables if game_type == 'snooker' else self.pool_tables
            
            if table_id not in tables:
                return jsonify({"error": "Invalid table"}), 400
            
            table = tables[table_id]
            if not table['sessions']:
                return jsonify({"error": "No sessions to split"}), 400
            
            if not 1 <= players <= 50:
                return jsonify({"error": "Invalid number of players"}), 400
            
            total_amount = table['sessions'][-1]['amount']
            return jsonify({
                "success": True, "total_amount": total_amount,
                "players": players, "per_player": total_amount / players
            })
    
    def handle_table_action(self, game_type, table_id, action):
        """Handle table state changes"""
        tables = self.snooker_tables if game_type == 'snooker' else self.pool_tables
        table = tables[table_id]
        
        if action == 'start':
            if table['status'] == 'idle':
                table.update({
                    'status': 'running', 'start_time': datetime.now(), 
                    'elapsed_seconds': 0, 'session_start_time': datetime.now().strftime("%H:%M:%S")
                })
            return f"Table {table_id} started"
        
        elif action == 'pause':
            if table['status'] == 'running':
                table['status'] = 'paused'
            elif table['status'] == 'paused':
                table.update({'status': 'running', 'start_time': datetime.now()})
            return f"Table {table_id} {'paused' if table['status'] == 'paused' else 'resumed'}"
        
        elif action == 'end':
            if table['status'] in ['running', 'paused']:
                duration_minutes = table['elapsed_seconds'] / 60
                amount = duration_minutes * table['rate']
                
                session = {
                    "start_time": table.get('session_start_time', '00:00:00'),
                    "end_time": datetime.now().strftime("%H:%M:%S"),
                    "duration": round(duration_minutes, 1),
                    "amount": round(amount, 2),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "user": current_user.username
                }
                
                table['sessions'].append(session)
                table.update({
                    'status': 'idle', 'time': '00:00', 'amount': 0,
                    'start_time': None, 'elapsed_seconds': 0, 'session_start_time': None
                })
                return f"Table {table_id} ended - ₹{amount:.2f}"
        
        return "No action taken"
    
    def update_timers(self):
        """Background timer for running tables"""
        while self.running:
            try:
                for tables in [self.snooker_tables, self.pool_tables]:
                    for table in tables.values():
                        if table['status'] == 'running' and table['start_time']:
                            table['elapsed_seconds'] += 1
                            minutes, seconds = divmod(table['elapsed_seconds'], 60)
                            table['time'] = f"{minutes:02d}:{seconds:02d}"
                            table['amount'] = (table['elapsed_seconds'] / 60) * table['rate']
                            table['start_time'] = datetime.now()
                time.sleep(1)
            except Exception as e:
                print(f"Timer error: {e}")
                time.sleep(1)

# Initialize app
app_instance = TableTracker()
app = app_instance.app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
