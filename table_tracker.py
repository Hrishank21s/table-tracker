#!/usr/bin/env python3
import json
import threading
import time
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
                players = int(data.get('players',

