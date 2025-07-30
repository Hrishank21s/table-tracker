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
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
        CORS(self.app)
        
        self.setup_authentication()
        self.setup_routes()
    
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
            return jsonify({
                "success": True,
                "tables": tables,
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
                
                if tables[table_id]['status'] != 'idle':
                    return jsonify({"error": "Cannot change rate while table is running"}), 400
                
                tables[table_id]['rate'] = new_rate
                print(f"{game_type.title()} Table {table_id} rate updated to ₹{new_rate}/min by {current_user.username}")
                
                return jsonify({
                    "success": True,
                    "table": table_id,
                    "new_rate": new_rate,
                    "tables": tables
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
                
                tables[table_id]['sessions'] = []
                print(f"{game_type.title()} Table {table_id} data cleared by {current_user.username}")
                
                return jsonify({
                    "success": True,
                    "table": table_id,
                    "message": f"Table {table_id} data cleared",
                    "tables": tables
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
                
                tables = self.snooker_tables if game_type == 'snooker' else self.pool_tables
                
                if table_id not in tables:
                    return jsonify({"error": "Invalid table ID"}), 400
                
                table = tables[table_id]
                
                if not table['sessions'] or len(table['sessions']) == 0:
                    return jsonify({"error": "No sessions to split"}), 400
                
                last_session = table['sessions'][-1]
                total_amount = last_session['amount']
                
                if players < 1 or players > 50:
                    return jsonify({"error": "Invalid number of players (1-50)"}), 400
                
                per_player = total_amount / players
                
                return jsonify({
                    "success": True,
                    "table": table_id,
                    "total_amount": total_amount,
                    "players": players,
                    "per_player": per_player
                })
                
            except Exception as e:
                print(f"Split Error: {e}")
                return jsonify({"error": str(e)}), 500
    
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
    
    def get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return '127.0.0.1'
    
    def get_login_template(self):
        """Login page template"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Table Tracker - Login</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: white;
            padding: 20px;
        }
        
        .login-container {
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 40px;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.2);
            max-width: 400px;
            width: 100%;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }
        
        .login-header {
            margin-bottom: 30px;
        }
        
        .login-header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .login-header p {
            opacity: 0.9;
            font-size: 1rem;
        }
        
        .form-group {
            margin-bottom: 20px;
            text-align: left;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            font-size: 14px;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px 16px;
            border: none;
            border-radius: 10px;
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 16px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            transition: all 0.3s ease;
        }
        
        .form-group input:focus {
            outline: none;
            background: rgba(255,255,255,0.2);
            border-color: rgba(255,255,255,0.4);
        }
        
        .form-group input::placeholder {
            color: rgba(255,255,255,0.7);
        }
        
        .login-btn {
            width: 100%;
            padding: 15px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 10px;
        }
        
        .login-btn:hover {
            background: #1e7e34;
            transform: translateY(-2px);
        }
        
        .alert {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        
        .alert-danger {
            background: rgba(220,53,69,0.2);
            border: 1px solid rgba(220,53,69,0.3);
            color: #ff6b7d;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>🎯 Table Tracker</h1>
            <p>Please login to continue</p>
        </div>
        
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-danger">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" placeholder="Enter your username" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" placeholder="Enter your password" required>
            </div>
            
            <button type="submit" class="login-btn">Login</button>
        </form>
    </div>
</body>
</html>"""
    
    def get_home_template(self):
        """Home page template"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Table Tracker - Home</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: white;
            padding: 20px;
        }}
        
        .user-info {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.3);
            z-index: 1000;
        }}
        
        .user-info span {{
            margin-right: 15px;
            font-weight: 600;
        }}
        
        .logout-btn {{
            background: #dc3545;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 12px;
            cursor: pointer;
            text-decoration: none;
            transition: background 0.3s ease;
        }}
        
        .logout-btn:hover {{
            background: #c82333;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 50px;
        }}
        
        .header h1 {{
            font-size: 3.5rem;
            font-weight: 700;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header p {{
            font-size: 1.2rem;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        
        .game-selection {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 40px;
            max-width: 800px;
            width: 100%;
        }}
        
        .game-card {{
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 40px 30px;
            text-align: center;
            backdrop-filter: blur(15px);
            border: 2px solid rgba(255,255,255,0.2);
            transition: all 0.3s ease;
            cursor: pointer;
            text-decoration: none;
            color: white;
            position: relative;
            overflow: hidden;
        }}
        
        .game-card:hover {{
            transform: translateY(-10px);
            border-color: rgba(255,255,255,0.4);
            background: rgba(255,255,255,0.15);
        }}
        
        .game-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
            transition: left 0.5s;
        }}
        
        .game-card:hover::before {{
            left: 100%;
        }}
        
        .game-icon {{
            font-size: 4rem;
            margin-bottom: 20px;
            display: block;
        }}
        
        .game-title {{
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 15px;
        }}
        
        .game-description {{
            font-size: 1rem;
            opacity: 0.8;
            margin-bottom: 20px;
            line-height: 1.5;
        }}
        
        .game-status {{
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
            display: inline-block;
        }}
        
        .status-active {{
            background: #28a745;
            color: white;
        }}
        
        .footer {{
            margin-top: 50px;
            text-align: center;
            opacity: 0.7;
            font-size: 0.9rem;
        }}
        
        .mobile-links {{
            margin-top: 30px;
            text-align: center;
        }}
        
        .mobile-link {{
            display: inline-block;
            margin: 0 15px;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 25px;
            text-decoration: none;
            color: white;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }}
        
        .mobile-link:hover {{
            background: rgba(255,255,255,0.3);
            transform: scale(1.05);
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 2.5rem; }}
            .game-card {{ padding: 30px 20px; }}
            .game-icon {{ font-size: 3rem; }}
            .game-title {{ font-size: 1.5rem; }}
        }}
    </style>
</head>
<body>
    <div class="user-info">
        <span>👤 {current_user.username} ({current_user.role.title()})</span>
        <a href="/logout" class="logout-btn">Logout</a>
    </div>

    <div class="header">
        <h1>🎯 Table Tracker</h1>
        <p>Professional Table Management System</p>
        <p>Welcome, {current_user.username}!</p>
    </div>
    
    <div class="game-selection">
        <a href="/snooker" class="game-card">
            <span class="game-icon">🎱</span>
            <div class="game-title">Snooker</div>
            <div class="game-description">
                Full-featured table tracking with timer, billing, and session management. 
                Perfect for snooker halls and gaming centers.
            </div>
            <span class="game-status status-active">✅ Active</span>
        </a>
        
        <a href="/pool" class="game-card">
            <span class="game-icon">🎳</span>
            <div class="game-title">Pool</div>
            <div class="game-description">
                Pool table management system with specialized lower rates. 
                Perfect for pool halls and casual gaming.
            </div>
            <span class="game-status status-active">✅ Active</span>
        </a>
    </div>
    
    <div class="mobile-links">
        <a href="/snooker/mobile" class="mobile-link">📱 Snooker Mobile</a>
        <a href="/pool/mobile" class="mobile-link">📱 Pool Mobile</a>
    </div>
    
    <div class="footer">
        <p>Real-time tracking • Multiple pricing tiers • Split billing • Mobile support</p>
        <p>Built with ❤️ for efficient table management</p>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const cards = document.querySelectorAll('.game-card');
            
            cards.forEach(card => {{
                card.addEventListener('mouseenter', function() {{
                    this.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';
                }});
                
                card.addEventListener('mouseleave', function() {{
                    this.style.boxShadow = 'none';
                }});
            }});
        }});
    </script>
</body>
</html>"""

    def get_game_template(self, game_type):
        """Game interface template"""
        icon = "🎱" if game_type == "snooker" else "🎳"
        title = f"{game_type.title()} Tracker Desktop"
        
        user_management_html = ""
        if current_user.role == 'admin':
            user_management_html = """
            <div class="user-setting">
                <h3>👥 User Management</h3>
                <div style="margin-bottom: 15px; font-size: 12px; opacity: 0.8;">
                    Add new admin or staff users:
                </div>
                <div class="user-form">
                    <input type="text" id="newUsername" placeholder="Username" style="margin: 5px; padding: 8px; border-radius: 5px; border: 1px solid #ccc; background: rgba(255,255,255,0.9); color: #333;">
                    <input type="password" id="newPassword" placeholder="Password" style="margin: 5px; padding: 8px; border-radius: 5px; border: 1px solid #ccc; background: rgba(255,255,255,0.9); color: #333;">
                    <select id="userRole" style="margin: 5px; padding: 8px; border-radius: 5px; border: 1px solid #ccc; background: rgba(255,255,255,0.9); color: #333;">
                        <option value="admin">Admin</option>
                        <option value="staff">Staff</option>
                    </select>
                    <button onclick="tracker.addUser()" style="margin: 5px; padding: 8px 15px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer;">Add User</button>
                </div>
                <div id="usersList" style="margin-top: 15px; max-height: 200px; overflow-y: auto; background: rgba(0,0,0,0.2); border-radius: 8px; padding: 10px;">
                    <!-- Users list will be populated here -->
                </div>
            </div>
            """
        
        sessions_container_style = """
        .sessions-container {
            max-height: 200px;
            overflow-y: auto;
            background: rgba(0,0,0,0.5);
            border-radius: 10px;
            padding: 10px;
            scroll-behavior: auto;
            will-change: scroll-position;
            border: 1px solid rgba(255,255,255,0.3);
        }""" if game_type == 'pool' else """
        .sessions-container {
            max-height: 200px;
            overflow-y: auto;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            padding: 10px;
            scroll-behavior: auto;
            will-change: scroll-position;
        }"""
        
        session_item_style = """
        .session-item {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 10px;
            padding: 8px 10px;
            margin: 5px 0;
            background: rgba(0,0,0,0.4);
            border-radius: 8px;
            font-size: 12px;
            align-items: center;
            min-height: 32px;
            flex-shrink: 0;
            border: 1px solid rgba(255,255,255,0.2);
        }""" if game_type == 'pool' else """
        .session-item {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 10px;
            padding: 8px 10px;
            margin: 5px 0;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            font-size: 12px;
            align-items: center;
            min-height: 32px;
            flex-shrink: 0;
        }"""
        
        session_text_colors = """
        .session-time { color: #87CEEB; font-weight: 600; }
        .session-duration { color: #FFD700; }
        .session-amount { color: #90EE90; font-weight: 600; }
        .session-date { color: #D3D3D3; font-size: 11px; }
        .no-sessions {
            text-align: center;
            color: #D3D3D3;
            font-style: italic;
            padding: 20px;
            min-height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
        }""" if game_type == 'pool' else """
        .session-time { color: #3498db; font-weight: 600; }
        .session-duration { color: #f39c12; }
        .session-amount { color: #2ecc71; font-weight: 600; }
        .session-date { color: #95a5a6; font-size: 11px; }
        .no-sessions {
            text-align: center;
            color: #95a5a6;
            font-style: italic;
            padding: 20px;
            min-height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
        }"""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, {'#667eea 0%, #764ba2 100%' if game_type == 'snooker' else '#11998e 0%, #38ef7d 100%'});
            min-height: 100vh;
            padding: 20px;
            color: white;
        }}
        .header {{ text-align: center; margin-bottom: 30px; position: relative; }}
        .header h1 {{ font-size: 2.5rem; font-weight: 700; margin-bottom: 10px; }}
        
        .user-info {{
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(255,255,255,0.2);
            padding: 8px 16px;
            border-radius: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.3);
            z-index: 1001;
            font-size: 12px;
        }}
        
        .home-btn {{
            position: fixed;
            top: 70px;
            left: 20px;
            background: rgba(255,255,255,0.2);
            border: none;
            border-radius: 25px;
            padding: 8px 16px;
            cursor: pointer;
            font-size: 14px;
            color: white;
            transition: all 0.3s ease;
            z-index: 1000;
            backdrop-filter: blur(10px);
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .home-btn:hover {{ background: rgba(255,255,255,0.3); transform: scale(1.05); }}
        
        .settings-btn {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.2);
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            cursor: pointer;
            font-size: 20px;
            color: white;
            transition: all 0.3s ease;
            z-index: 1000;
            backdrop-filter: blur(10px);
        }}
        .settings-btn:hover {{ background: rgba(255,255,255,0.3); transform: scale(1.1); }}
        
        .settings-panel {{
            position: fixed;
            top: 0;
            right: -400px;
            width: 400px;
            height: 100vh;
            background: rgba(0,0,0,0.9);
            backdrop-filter: blur(20px);
            transition: right 0.3s ease;
            z-index: 999;
            padding: 20px;
            overflow-y: auto;
        }}
        .settings-panel.open {{ right: 0; }}
        .settings-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }}
        .settings-title {{ font-size: 1.5rem; font-weight: 600; }}
        .close-settings {{
            background: none;
            border: none;
            color: white;
            font-size: 24px;
            cursor: pointer;
        }}
        .rate-setting {{
            margin-bottom: 25px;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
        }}
        .rate-setting h3 {{
            margin-bottom: 15px;
            font-size: 1.2rem;
            color: #4caf50;
        }}
        .rate-selector {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }}
        .rate-option {{
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border: 2px solid transparent;
            border-radius: 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 600;
        }}
        .rate-option:hover {{ background: rgba(255,255,255,0.2); }}
        .rate-option.active {{ border-color: #4caf50; background: rgba(76, 175, 80, 0.3); }}
        .rate-option.disabled {{ opacity: 0.5; cursor: not-allowed; }}
        
        .user-setting {{
            margin-bottom: 25px;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
        }}
        .user-setting h3 {{
            margin-bottom: 15px;
            font-size: 1.2rem;
            color: #2196f3;
        }}
        .user-form {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        .user-item {{
            margin: 5px 0;
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid rgba(255,255,255,0.2);
        }}
        
        .user-info-item {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}
        
        .user-name {{
            font-weight: 600;
            font-size: 14px;
        }}
        
        .user-role {{
            font-size: 11px;
            opacity: 0.8;
            text-transform: uppercase;
        }}
        
        .user-role.admin {{
            color: #ffd700;
        }}
        
        .user-role.staff {{
            color: #87ceeb;
        }}
        
        .remove-btn {{
            background: #dc3545;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 10px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .remove-btn:hover {{
            background: #c82333;
            transform: scale(1.05);
        }}
        
        .remove-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .status-bar {{
            background: rgba(255,255,255,0.15);
            padding: 15px 25px;
            border-radius: 15px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }}
        .tables-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .table-card {{
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.3s ease;
        }}
        .table-card:hover {{ transform: translateY(-5px); }}
        .table-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .table-name {{ font-size: 1.4rem; font-weight: 600; }}
        .table-status {{
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .status-idle {{ background: #6c757d; color: white; }}
        .status-running {{ background: #28a745; color: white; }}
        .status-paused {{ background: #fd7e14; color: white; }}
        .table-time {{
            font-size: 3rem;
            font-weight: 700;
            text-align: center;
            margin: 25px 0;
            font-family: 'SF Mono', Monaco, Consolas, monospace;
        }}
        .table-info {{
            display: flex;
            justify-content: space-between;
            margin: 20px 0;
            font-size: 14px;
        }}
        .info-item {{
            text-align: center;
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            flex: 1;
            margin: 0 5px;
        }}
        .controls {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 12px;
            margin: 25px 0;
        }}
        .control-btn {{
            padding: 15px;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .control-btn:hover {{ transform: translateY(-2px); }}
        .control-btn:active {{ transform: translateY(0); }}
        .btn-start {{ background: #28a745; color: white; }}
        .btn-pause {{ background: #fd7e14; color: white; }}
        .btn-end {{ background: #dc3545; color: white; }}
        
        .sessions-section {{
            margin-top: 25px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.3);
        }}
        .sessions-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .sessions-title {{
            font-size: 14px;
            font-weight: 600;
            color: #ecf0f1;
        }}
        .clear-btn {{
            padding: 6px 12px;
            background: #e74c3c;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .clear-btn:hover {{ background: #c0392b; }}
        
        {sessions_container_style}
        
        .sessions-container::-webkit-scrollbar {{
            width: 8px;
        }}
        .sessions-container::-webkit-scrollbar-track {{
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
        }}
        .sessions-container::-webkit-scrollbar-thumb {{
            background: rgba(255,255,255,0.3);
            border-radius: 4px;
        }}
        .sessions-container::-webkit-scrollbar-thumb:hover {{
            background: rgba(255,255,255,0.5);
        }}
        
        {session_item_style}
        
        {session_text_colors}
    </style>
</head>
<body>
    <div class="user-info">👤 {current_user.username} ({current_user.role.title()})</div>
    <a href="/" class="home-btn">🏠 Home</a>
    <button class="settings-btn" onclick="toggleSettings()">⚙️</button>
    
    <div class="settings-panel" id="settings-panel">
        <div class="settings-header">
            <div class="settings-title">⚙️ Settings</div>
            <button class="close-settings" onclick="toggleSettings()">✕</button>
        </div>
        
        {user_management_html}
        
        <div id="rate-settings">
            <!-- Rate settings will be populated here -->
        </div>
    </div>

    <div class="header">
        <h1>{icon} {title}</h1>
    </div>
    
    <div class="status-bar">
        <div>{icon} {game_type.title()} Interface</div>
        <div id="update-status">🔄 Loading...</div>
        <div id="current-time"></div>
    </div>
    
    <div class="tables-container" id="tables-container"></div>

    <script>
        const GAME_TYPE = '{game_type}';
        const USER_ROLE = '{current_user.role}';
        const CURRENT_USER = '{current_user.username}';
        
        class TableTracker {{
            constructor() {{
                this.tables = {{}};
                this.availableRates = [];
                this.scrollPositions = {{}};
                this.lastUpdateTime = 0;
                this.init();
            }}
            
            init() {{
                this.loadTables();
                this.updateClock();
                setInterval(() => this.updateClock(), 1000);
                setInterval(() => this.loadTables(), 1000);
                
                if (USER_ROLE === 'admin') {{
                    this.loadUsers();
                }}
            }}
            
            async loadTables() {{
                try {{
                    const now = Date.now();
                    if (now - this.lastUpdateTime < 950) {{
                        return;
                    }}
                    this.lastUpdateTime = now;
                    
                    this.saveScrollPositions();
                    
                    const response = await fetch(`/api/${{GAME_TYPE}}/tables`);
                    const data = await response.json();
                    
                    if (data.success) {{
                        const newTablesString = JSON.stringify(data.tables);
                        const currentTablesString = JSON.stringify(this.tables);
                        
                        if (newTablesString !== currentTablesString) {{
                            this.tables = data.tables;
                            this.availableRates = data.available_rates;
                            this.renderTables();
                            this.renderSettings();
                            
                            requestAnimationFrame(() => {{
                                setTimeout(() => this.restoreScrollPositions(), 10);
                            }});
                        }}
                        
                        document.getElementById('update-status').textContent = '🟢 Live Updates (1sec)';
                    }}
                }} catch (error) {{
                    console.error('Failed to load tables:', error);
                    document.getElementById('update-status').textContent = '🔴 Connection Error';
                }}
            }}
            
            async loadUsers() {{
                try {{
                    const response = await fetch('/api/users');
                    const data = await response.json();
                    
                    if (data.success) {{
                        this.renderUsers(data.users);
                    }}
                }} catch (error) {{
                    console.error('Failed to load users:', error);
                }}
            }}
            
            renderUsers(users) {{
                const container = document.getElementById('usersList');
                if (!container) return;
                
                if (users.length === 0) {{
                    container.innerHTML = '<div style="text-align: center; opacity: 0.7; padding: 20px;">No users found</div>';
                    return;
                }}
                
                container.innerHTML = users.map(user => `
                    <div class="user-item">
                        <div class="user-info-item">
                            <div class="user-name">${{user.username}}</div>
                            <div class="user-role ${{user.role}}">${{user.role}}</div>
                        </div>
                        <div>
                            ${{user.can_remove ? 
                                `<button class="remove-btn" onclick="tracker.removeUser('${{user.username}}')" title="Remove User">🗑️ Remove</button>` :
                                `<span style="font-size: 10px; opacity: 0.6;">Current User</span>`
                            }}
                        </div>
                    </div>
                `).join('');
            }}
            
            async addUser() {{
                const username = document.getElementById('newUsername').value;
                const password = document.getElementById('newPassword').value;
                const role = document.getElementById('userRole').value;
                
                if (!username || !password) {{
                    alert('Please enter username and password');
                    return;
                }}
                
                if (username.length < 3) {{
                    alert('Username must be at least 3 characters long');
                    return;
                }}
                
                if (password.length < 6) {{
                    alert('Password must be at least 6 characters long');
                    return;
                }}
                
                try {{
                    const response = await fetch('/api/users/add', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            username: username,
                            password: password,
                            role: role
                        }})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        alert(result.message);
                        document.getElementById('newUsername').value = '';
                        document.getElementById('newPassword').value = '';
                        this.loadUsers();
                    }} else {{
                        alert('Error: ' + result.error);
                    }}
                }} catch (error) {{
                    console.error('Add user failed:', error);
                    alert('Failed to add user');
                }}
            }}
            
            async removeUser(username) {{
                if (!confirm(`Are you sure you want to remove user "${{username}}"?\\n\\nThis action cannot be undone.`)) {{
                    return;
                }}
                
                try {{
                    const response = await fetch('/api/users/remove', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            username: username
                        }})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        alert(result.message);
                        this.loadUsers();
                    }} else {{
                        alert('Error: ' + result.error);
                    }}
                }} catch (error) {{
                    console.error('Remove user failed:', error);
                    alert('Failed to remove user');
                }}
            }}
            
            saveScrollPositions() {{
                Object.keys(this.tables).forEach(tableId => {{
                    const container = document.getElementById(`sessions-container-${{tableId}}`);
                    if (container) {{
                        this.scrollPositions[tableId] = container.scrollTop;
                    }}
                }});
            }}
            
            restoreScrollPositions() {{
                Object.keys(this.scrollPositions).forEach(tableId => {{
                    const container = document.getElementById(`sessions-container-${{tableId}}`);
                    if (container && this.scrollPositions[tableId] !== undefined) {{
                        container.scrollTo({{
                            top: this.scrollPositions[tableId],
                            behavior: 'auto'
                        }});
                    }}
                }});
            }}
            
            updateClock() {{
                const now = new Date();
                document.getElementById('current-time').textContent = now.toLocaleTimeString();
            }}
            
            renderSettings() {{
                const container = document.getElementById('rate-settings');
                container.innerHTML = '';
                
                Object.keys(this.tables).forEach(tableId => {{
                    const table = this.tables[tableId];
                    const settingDiv = document.createElement('div');
                    settingDiv.className = 'rate-setting';
                    
                    const rateOptions = this.availableRates.map(rate => {{
                        const isActive = table.rate === rate;
                        const isDisabled = table.status !== 'idle';
                        return `<div class="rate-option ${{isActive ? 'active' : ''}} ${{isDisabled ? 'disabled' : ''}}" 
                                    onclick="${{isDisabled ? '' : `tracker.updateRate(${{tableId}}, ${{rate}})`}}">
                                    ₹${{rate}}/min
                                </div>`;
                    }}).join('');
                    
                    settingDiv.innerHTML = `
                        <h3>Table ${{tableId}} Pricing</h3>
                        <div style="margin-bottom: 10px; font-size: 12px; opacity: 0.8;">
                            ${{table.status !== 'idle' ? '⚠️ Stop table to change rate' : 'Select rate per minute:'}}
                        </div>
                        <div class="rate-selector">
                            ${{rateOptions}}
                        </div>
                    `;
                    
                    container.appendChild(settingDiv);
                }});
            }}
            
            renderTables() {{
                const container = document.getElementById('tables-container');
                
                const currentTableCount = container.children.length;
                const expectedTableCount = Object.keys(this.tables).length;
                
                if (currentTableCount !== expectedTableCount) {{
                    container.innerHTML = '';
                }}
                
                Object.keys(this.tables).forEach(tableId => {{
                    const table = this.tables[tableId];
                    let card = document.getElementById(`table-card-${{tableId}}`);
                    
                    if (!card) {{
                        card = document.createElement('div');
                        card.className = 'table-card';
                        card.id = `table-card-${{tableId}}`;
                        container.appendChild(card);
                    }}
                    
                    let sessionsHTML = '';
                    if (table.sessions && table.sessions.length > 0) {{
                        sessionsHTML = table.sessions.map(session => 
                            `<div class="session-item">
                                <div class="session-time">${{session.start_time}} - ${{session.end_time}}</div>
                                <div class="session-duration">${{session.duration}}min</div>
                                <div class="session-amount">₹${{session.amount}}</div>
                                <div class="session-date">${{session.date}}</div>
                            </div>`
                        ).join('');
                    }} else {{
                        sessionsHTML = '<div class="no-sessions">No sessions recorded yet</div>';
                    }}
                    
                    card.innerHTML = `
                        <div class="table-header">
                            <div class="table-name">Table ${{tableId}}</div>
                            <div class="table-status status-${{table.status}}">${{table.status}}</div>
                        </div>
                        <div class="table-time">${{table.time}}</div>
                        <div class="table-info">
                            <div class="info-item">
                                <div>Rate</div>
                                <strong>₹${{table.rate}}/min</strong>
                            </div>
                            <div class="info-item">
                                <div>Current Amount</div>
                                <strong>₹${{table.amount.toFixed(2)}}</strong>
                            </div>
                        </div>
                        <div class="controls">
                            <button class="control-btn btn-start" onclick="tracker.sendAction(${{tableId}}, 'start')">START</button>
                            <button class="control-btn btn-pause" onclick="tracker.sendAction(${{tableId}}, 'pause')">PAUSE</button>
                            <button class="control-btn btn-end" onclick="tracker.sendAction(${{tableId}}, 'end')">END</button>
                        </div>
                        <div class="sessions-section">
                            <div class="sessions-header">
                                <div class="sessions-title">📊 Session History</div>
                                <div>
                                    <button class="clear-btn" onclick="tracker.splitAmount(${{tableId}})" 
                                            ${{table.sessions && table.sessions.length > 0 ? '' : 'style="opacity: 0.5;" disabled'}}
                                            style="margin-right: 5px; background: #3498db;">
                                        💰 Split
                                    </button>
                                    <button class="clear-btn" onclick="tracker.clearTableData(${{tableId}})" 
                                            ${{table.sessions && table.sessions.length > 0 ? '' : 'style="opacity: 0.5;" disabled'}}>
                                        🗑️ Clear Data
                                    </button>
                                </div>
                            </div>
                            <div class="sessions-container" id="sessions-container-${{tableId}}">
                                ${{sessionsHTML}}
                            </div>
                        </div>
                    `;
                }});
            }}
            
            async sendAction(tableId, action) {{
                try {{
                    const response = await fetch(`/api/${{GAME_TYPE}}/table/${{tableId}}/action`, {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{action: action}})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        console.log(`Action successful: ${{result.result}}`);
                        if (result.tables) {{
                            this.tables = result.tables;
                            this.renderTables();
                            this.renderSettings();
                            setTimeout(() => this.restoreScrollPositions(), 10);
                        }}
                    }} else {{
                        console.error('Action failed:', result.error);
                    }}
                }} catch (error) {{
                    console.error('Action request failed:', error);
                }}
            }}
            
            async updateRate(tableId, newRate) {{
                try {{
                    const response = await fetch(`/api/${{GAME_TYPE}}/table/${{tableId}}/rate`, {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{rate: newRate}})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        console.log(`Rate updated: Table ${{tableId}} - ₹${{newRate}}/min`);
                        if (result.tables) {{
                            this.tables = result.tables;
                            this.renderTables();
                            this.renderSettings();
                        }}
                    }} else {{
                        alert(`Error: ${{result.error}}`);
                    }}
                }} catch (error) {{
                    console.error('Rate update failed:', error);
                }}
            }}
            
            async clearTableData(tableId) {{
                if (!confirm(`Are you sure you want to clear all session data for Table ${{tableId}}?`)) {{
                    return;
                }}
                
                try {{
                    const response = await fetch(`/api/${{GAME_TYPE}}/table/${{tableId}}/clear`, {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}}
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        console.log(`Table ${{tableId}} data cleared`);
                        if (result.tables) {{
                            this.tables = result.tables;
                            this.renderTables();
                        }}
                    }} else {{
                        console.error('Clear failed:', result.error);
                    }}
                }} catch (error) {{
                    console.error('Clear request failed:', error);
                }}
            }}
            
            async splitAmount(tableId) {{
                const players = prompt("Enter number of players:");
                if (!players || players < 1) return;
                
                try {{
                    const response = await fetch(`/api/${{GAME_TYPE}}/table/${{tableId}}/split`, {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{players: parseInt(players)}})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        alert(`Split Result for Table ${{tableId}}:\\n\\nTotal: ₹${{result.total_amount.toFixed(2)}}\\nPlayers: ${{result.players}}\\nPer Player: ₹${{result.per_player.toFixed(2)}}`);
                    }} else {{
                        alert(`Error: ${{result.error}}`);
                    }}
                }} catch (error) {{
                    console.error('Split request failed:', error);
                }}
            }}
        }}
        
        function toggleSettings() {{
            const panel = document.getElementById('settings-panel');
            panel.classList.toggle('open');
        }}
        
        const tracker = new TableTracker();
    </script>
</body>
</html>"""

    def get_mobile_template(self, game_type):
        """Mobile interface template"""
        icon = "🎱" if game_type == "snooker" else "🎳"
        title = f"{game_type.title()} Remote"
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, {'#667eea 0%, #764ba2 100%' if game_type == 'snooker' else '#11998e 0%, #38ef7d 100%'});
            color: white;
            min-height: 100vh;
            padding: 20px;
        }}
        .header {{ 
            text-align: center; 
            margin-bottom: 30px; 
            position: relative;
        }}
        .header h1 {{ font-size: 1.8rem; font-weight: 700; }}
        .user-info {{
            position: absolute;
            top: -10px;
            right: 0;
            background: rgba(255,255,255,0.2);
            padding: 4px 8px;
            border-radius: 15px;
            font-size: 10px;
            backdrop-filter: blur(10px);
        }}
        .home-btn {{
            position: absolute;
            top: 0;
            left: 0;
            background: rgba(255,255,255,0.2);
            border: none;
            border-radius: 20px;
            padding: 6px 12px;
            cursor: pointer;
            font-size: 12px;
            color: white;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            text-decoration: none;
        }}
        .home-btn:hover {{ background: rgba(255,255,255,0.3); }}
        .connection-status {{
            padding: 12px 20px;
            border-radius: 25px;
            font-size: 14px;
            background: rgba(255,255,255,0.15);
            text-align: center;
            margin-bottom: 25px;
            backdrop-filter: blur(10px);
        }}
        .table-card {{
            background: rgba(255,255,255,0.1);
            border-radius: 18px;
            padding: 24px;
            margin-bottom: 20px;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.2);
        }}
        .table-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .table-name {{ font-size: 1.3rem; font-weight: 600; }}
        .table-status {{
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .status-idle {{ background: #6c757d; }}
        .status-running {{ background: #28a745; }}
        .status-paused {{ background: #fd7e14; }}
        .table-time {{
            font-size: 2.5rem;
            font-weight: 700;
            text-align: center;
            margin: 20px 0;
            font-family: 'SF Mono', Monaco, Consolas, monospace;
        }}
        .table-amount {{
            text-align: center;
            font-size: 1.3rem;
            font-weight: 600;
            color: #ffd700;
            margin: 15px 0;
        }}
        .controls {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 12px;
            margin-bottom: 20px;
        }}
        .control-btn {{
            padding: 16px 8px;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .control-btn:active {{ transform: scale(0.95); }}
        .btn-start {{ background: #28a745; color: white; }}
        .btn-pause {{ background: #fd7e14; color: white; }}
        .btn-end {{ background: #dc3545; color: white; }}
        .recent-sessions {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.3);
        }}
        .sessions-title {{
            font-size: 12px;
            color: #bdc3c7;
            margin-bottom: 10px;
        }}
        .session-summary {{
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: #ecf0f1;
            margin: 3px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            font-size: 12px;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="header">
        <a href="/" class="home-btn">🏠 Home</a>
        <div class="user-info">{current_user.username}</div>
        <h1>{icon} {title}</h1>
    </div>
    
    <div class="connection-status" id="connection-status">🔄 Loading...</div>
    <div id="tables-container"></div>
    
    <div class="footer">
        Remote control for {game_type.title()} Tables<br>
        Auto-updates every 1 second
    </div>

    <script>
        const GAME_TYPE = '{game_type}';
        
        class MobileRemote {{
            constructor() {{
                this.tables = {{}};
                this.init();
            }}
            
            init() {{
                this.loadTables();
                setInterval(() => this.loadTables(), 1000);
            }}
            
            async loadTables() {{
                try {{
                    const response = await fetch(`/api/${{GAME_TYPE}}/tables`);
                    const data = await response.json();
                    
                    if (data.success) {{
                        this.tables = data.tables;
                        this.renderTables();
                        document.getElementById('connection-status').innerHTML = '🟢 Connected • Live updates (1sec)';
                    }}
                }} catch (error) {{
                    console.error('Failed to load tables:', error);
                    document.getElementById('connection-status').innerHTML = '🔴 Connection error';
                }}
            }}
            
            renderTables() {{
                const container = document.getElementById('tables-container');
                container.innerHTML = '';
                
                Object.keys(this.tables).forEach(tableId => {{
                    const table = this.tables[tableId];
                    const card = document.createElement('div');
                    card.className = 'table-card';
                    
                    let recentSessionsHTML = '';
                    if (table.sessions && table.sessions.length > 0) {{
                        const recent = table.sessions.slice(-3);
                        recentSessionsHTML = `
                            <div class="recent-sessions">
                                <div class="sessions-title">Recent Sessions (${{table.sessions.length}} total)</div>
                                ${{recent.map(session => 
                                    `<div class="session-summary">
                                        <span>${{session.start_time}}-${{session.end_time}}</span>
                                        <span>${{session.duration}}min - ₹${{session.amount}}</span>
                                    </div>`
                                ).join('')}}
                            </div>
                        `;
                    }}
                    
                    card.innerHTML = `
                        <div class="table-header">
                            <div class="table-name">Table ${{tableId}}</div>
                            <div class="table-status status-${{table.status}}">${{table.status}}</div>
                        </div>
                        <div class="table-time">${{table.time}}</div>
                        <div class="table-amount">₹${{table.amount.toFixed(2)}} (₹${{table.rate}}/min)</div>
                        <div class="controls">
                            <button class="control-btn btn-start" onclick="remote.sendAction(${{tableId}}, 'start')">START</button>
                            <button class="control-btn btn-pause" onclick="remote.sendAction(${{tableId}}, 'pause')">PAUSE</button>
                            <button class="control-btn btn-end" onclick="remote.sendAction(${{tableId}}, 'end')">END</button>
                        </div>
                        ${{recentSessionsHTML}}
                    `;
                    
                    container.appendChild(card);
                }});
            }}
            
            async sendAction(tableId, action) {{
                try {{
                    const response = await fetch(`/api/${{GAME_TYPE}}/table/${{tableId}}/action`, {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{action: action}})
                    }});
                    
                    const result = await response.json();
                    if (result.success) {{
                        if (result.tables) {{
                            this.tables = result.tables;
                            this.renderTables();
                        }}
                    }}
                }} catch (error) {{
                    console.error('Mobile action failed:', error);
                }}
            }}
        }}
        
        const remote = new MobileRemote();
    </script>
</body>
</html>"""
    
    def start(self):
        """Start the application"""
        local_ip = self.get_local_ip()
        
        print("\n" + "="*80)
        print("🚀 PROFESSIONAL TABLE TRACKER SYSTEM - PRODUCTION READY")
        print("="*80)
        print(f"🔐 Login Page: http://{local_ip}:8080")
        print(f"🏠 Home Page: http://{local_ip}:8080 (after login)")
        print(f"🎱 Snooker Desktop: http://{local_ip}:8080/snooker")
        print(f"📱 Snooker Mobile: http://{local_ip}:8080/snooker/mobile")
        print(f"🎳 Pool Desktop: http://{local_ip}:8080/pool")
        print(f"📱 Pool Mobile: http://{local_ip}:8080/pool/mobile")
        print(f"🌐 Network IP: {local_ip}")
        print("="*80)
        print("🔑 DEFAULT CREDENTIALS:")
        print("   👑 Admin: username=admin, password=admin123")
        print("   👤 Staff: username=staff1, password=staff123")
        print("="*80)
        print("✨ COMPLETE FEATURE SET:")
        print("   • 🔐 Secure login system with session management")
        print("   • 👥 User management (add/remove admin/staff)")
        print("   • 🎱 Snooker tables (₹3, ₹4, ₹4.5 per minute)")
        print("   • 🎳 Pool tables (₹2, ₹2, ₹2.5 per minute)")
        print("   • ⚙️ Rate configuration per table")
        print("   • 💰 Bill splitting functionality")
        print("   • 📊 Session history tracking")
        print("   • 📱 Mobile remote control")
        print("   • 🔄 Real-time updates (1-second refresh)")
        print("   • 🛡️ Role-based access control")
        print("="*80)
        print("🎯 SYSTEM READY FOR PRODUCTION USE")
        print("   Press Ctrl+C to stop the server")
        print("="*80)
        
        # Start background timer
        timer_thread = threading.Thread(target=self.update_timers, daemon=True)
        timer_thread.start()
        
        # Auto-open browser
        try:
            webbrowser.open(f'http://{local_ip}:8080')
        except:
            pass
        
        # Start Flask server
        try:
            self.app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
        except KeyboardInterrupt:
            print("\n\n⏹️ Server stopped")
            self.running = False

if __name__ == "__main__":
    print("🚀 Initializing Professional Table Tracker System...")
    try:
        app = TableTracker()
        app.start()
    except KeyboardInterrupt:
        print("\n\n👋 System shutdown complete!")
    except Exception as e:
        print(f"\n❌ System error: {e}")
        import traceback
        traceback.print_exc()

