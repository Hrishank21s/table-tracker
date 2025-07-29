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
from datetime import datetime
import os

# ----------------------
# User model
# ----------------------
class User(UserMixin):
    def __init__(self, id, username, password_hash, role):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role  # 'admin' or 'staff'


# ----------------------
# Main Application
# ----------------------
class TableTracker:
    def __init__(self):
        # Initialize tables
        self.snooker_tables = {
            1: {
                "status": "idle",
                "time": "00:00",
                "rate": 3.0,
                "amount": 0.0,
                "start_time": None,
                "elapsed_seconds": 0,
                "sessions": [],
                "session_start_time": None,
            },
            2: {
                "status": "idle",
                "time": "00:00",
                "rate": 4.0,
                "amount": 0.0,
                "start_time": None,
                "elapsed_seconds": 0,
                "sessions": [],
                "session_start_time": None,
            },
            3: {
                "status": "idle",
                "time": "00:00",
                "rate": 4.5,
                "amount": 0.0,
                "start_time": None,
                "elapsed_seconds": 0,
                "sessions": [],
                "session_start_time": None,
            },
        }
        self.pool_tables = {
            1: {
                "status": "idle",
                "time": "00:00",
                "rate": 2.0,
                "amount": 0.0,
                "start_time": None,
                "elapsed_seconds": 0,
                "sessions": [],
                "session_start_time": None,
            },
            2: {
                "status": "idle",
                "time": "00:00",
                "rate": 2.0,
                "amount": 0.0,
                "start_time": None,
                "elapsed_seconds": 0,
                "sessions": [],
                "session_start_time": None,
            },
            3: {
                "status": "idle",
                "time": "00:00",
                "rate": 2.5,
                "amount": 0.0,
                "start_time": None,
                "elapsed_seconds": 0,
                "sessions": [],
                "session_start_time": None,
            },
        }
        # Allowed rates for tables
        self.available_rates = [2.0, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5]

        # User storage: username -> User instance
        self.users = {
            "admin": User("admin", "admin", generate_password_hash("admin123"), "admin"),
            "staff1": User("staff1", "staff1", generate_password_hash("staff123"), "staff"),
        }

        self.running = True
        self.app = Flask(__name__)
        self.app.config["SECRET_KEY"] = "your-secret-key-change-this-in-production"
        CORS(self.app)
        self.setup_authentication()
        self.setup_routes()

        # Start background thread to update timers every second
        threading.Thread(target=self.update_timers, daemon=True).start()

    # ----------------------
    # Authentication Setup
    # ----------------------
    def setup_authentication(self):
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = "login"
        self.login_manager.login_message = "Please log in to access this page."

        @self.login_manager.user_loader
        def load_user(user_id):
            return self.users.get(user_id)

    # ----------------------
    # Route Setup
    # ----------------------
    def setup_routes(self):
        @self.app.route("/")
        @login_required
        def home():
            # Pass current_user.username and role as context, so no f-string needed
            return render_template_string(
                self.get_home_template(),
                username=current_user.username,
                role=current_user.role,
            )

        @self.app.route("/login", methods=["GET", "POST"])
        def login():
            if request.method == "POST":
                username = request.form.get("username")
                password = request.form.get("password")
                user = self.users.get(username)
                if user and check_password_hash(user.password_hash, password):
                    login_user(user)
                    next_page = request.args.get("next")
                    return redirect(next_page) if next_page else redirect(url_for("home"))
                else:
                    flash("Invalid username or password")
            return render_template_string(self.get_login_template())

        @self.app.route("/logout")
        @login_required
        def logout():
            logout_user()
            return redirect(url_for("login"))

        # Snooker Table UI (desktop)
        @self.app.route("/snooker")
        @login_required
        def snooker():
            return render_template_string(self.get_game_template("snooker"))

        # Snooker Table UI (mobile)
        @self.app.route("/snooker/mobile")
        @login_required
        def snooker_mobile():
            return render_template_string(self.get_mobile_template("snooker"))

        # Pool Table UI (desktop)
        @self.app.route("/pool")
        @login_required
        def pool():
            return render_template_string(self.get_game_template("pool"))

        # Pool Table UI (mobile)
        @self.app.route("/pool/mobile")
        @login_required
        def pool_mobile():
            return render_template_string(self.get_mobile_template("pool"))

        # -----------------------------------------
        # User management APIs (admin only)
        # -----------------------------------------
        @self.app.route("/api/users", methods=["GET"])
        @login_required
        def get_users():
            if current_user.role != "admin":
                return jsonify({"error": "Admin access required"}), 403
            user_list = []
            for user in self.users.values():
                user_list.append(
                    {
                        "username": user.username,
                        "role": user.role,
                        "can_remove": user.username != current_user.username,
                    }
                )
            return jsonify({"success": True, "users": user_list})

        @self.app.route("/api/users/add", methods=["POST"])
        @login_required
        def add_user():
            if current_user.role != "admin":
                return jsonify({"error": "Admin access required"}), 403
            try:
                data = request.get_json()
                username = data.get("username")
                password = data.get("password")
                role = data.get("role")
                if not username or not password or role not in ["admin", "staff"]:
                    return jsonify({"error": "Invalid user data"}), 400
                if username in self.users:
                    return jsonify({"error": "Username already exists"}), 400

                password_hash = generate_password_hash(password)
                new_user = User(username, username, password_hash, role)
                self.users[username] = new_user
                print(f"New {role} user created: {username} by {current_user.username}")
                return jsonify(
                    {
                        "success": True,
                        "message": f"{role.title()} user '{username}' created successfully",
                    }
                )
            except Exception as e:
                print(f"Add User Error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/users/remove", methods=["POST"])
        @login_required
        def remove_user():
            if current_user.role != "admin":
                return jsonify({"error": "Admin access required"}), 403
            try:
                data = request.get_json()
                username = data.get("username")
                if not username:
                    return jsonify({"error": "Username is required"}), 400
                if username not in self.users:
                    return jsonify({"error": "User not found"}), 404
                if username == current_user.username:
                    return jsonify({"error": "Cannot remove yourself"}), 400

                removed_user = self.users[username]
                del self.users[username]
                print(f"User removed: {username} ({removed_user.role}) by {current_user.username}")
                return jsonify(
                    {
                        "success": True,
                        "message": f"User '{username}' removed successfully",
                    }
                )
            except Exception as e:
                print(f"Remove User Error: {e}")
                return jsonify({"error": str(e)}), 500

        # -----------------------------------------
        # Table APIs
        # -----------------------------------------
        @self.app.route("/api/<game_type>/tables", methods=["GET"])
        @login_required
        def get_tables(game_type):
            tables = self.snooker_tables if game_type == "snooker" else self.pool_tables
            serializable_tables = {}
            for tid, tdata in tables.items():
                serializable_tables[tid] = {
                    "status": tdata["status"],
                    "time": tdata["time"],
                    "rate": tdata["rate"],
                    "amount": tdata["amount"],
                    "sessions": tdata["sessions"],
                }
            return jsonify(
                {
                    "success": True,
                    "tables": serializable_tables,
                    "available_rates": self.available_rates,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        @self.app.route("/api/<game_type>/table/<int:table_id>/action", methods=["POST"])
        @login_required
        def table_action(game_type, table_id):
            try:
                data = request.get_json()
                action = data.get("action")
                tables = self.snooker_tables if game_type == "snooker" else self.pool_tables
                if table_id not in tables or action not in ["start", "pause", "end"]:
                    return jsonify({"error": "Invalid request"}), 400

                result = self.handle_table_action(game_type, table_id, action)
                print(f"Action: {game_type.title()} Table {table_id} - {action} - User: {current_user.username}")
                return jsonify(
                    {
                        "success": True,
                        "table": table_id,
                        "action": action,
                        "result": result,
                        "tables": tables,
                    }
                )
            except Exception as e:
                print(f"API Error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/<game_type>/table/<int:table_id>/rate", methods=["POST"])
        @login_required
        def update_rate(game_type, table_id):
            try:
                data = request.get_json()
                new_rate = float(data.get("rate"))
                tables = self.snooker_tables if game_type == "snooker" else self.pool_tables
                if table_id not in tables:
                    return jsonify({"error": "Invalid table ID"}), 400
                if new_rate not in self.available_rates:
                    return jsonify({"error": "Invalid rate"}), 400
                if tables[table_id]["status"] != "idle":
                    return jsonify({"error": "Cannot change rate while table is running"}), 400
                tables[table_id]["rate"] = new_rate
                print(f"{game_type.title()} Table {table_id} rate updated to ₹{new_rate}/min by {current_user.username}")
                return jsonify(
                    {
                        "success": True,
                        "table": table_id,
                        "new_rate": new_rate,
                        "tables": tables,
                    }
                )
            except Exception as e:
                print(f"Rate Update Error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/<game_type>/table/<int:table_id>/clear", methods=["POST"])
        @login_required
        def clear_table(game_type, table_id):
            try:
                tables = self.snooker_tables if game_type == "snooker" else self.pool_tables
                if table_id not in tables:
                    return jsonify({"error": "Invalid table ID"}), 400
                tables[table_id]["sessions"].clear()
                print(f"{game_type.title()} Table {table_id} data cleared by {current_user.username}")
                return jsonify(
                    {
                        "success": True,
                        "table": table_id,
                        "message": f"Table {table_id} data cleared",
                        "tables": tables,
                    }
                )
            except Exception as e:
                print(f"Clear Error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/<game_type>/table/<int:table_id>/split", methods=["POST"])
        @login_required
        def split_bill(game_type, table_id):
            try:
                data = request.get_json()
                players = int(data.get("players", 0))
                tables = self.snooker_tables if game_type == "snooker" else self.pool_tables
                if table_id not in tables:
                    return jsonify({"error": "Invalid table ID"}), 400
                table = tables[table_id]
                if not table["sessions"] or len(table["sessions"]) == 0:
                    return jsonify({"error": "No sessions to split"}), 400

                last_session = table["sessions"][-1]
                total_amount = last_session["amount"]
                if players < 1 or players > 50:
                    return jsonify({"error": "Invalid number of players (1-50)"}), 400

                per_player = total_amount / players
                return jsonify(
                    {
                        "success": True,
                        "table": table_id,
                        "total_amount": total_amount,
                        "players": players,
                        "per_player": per_player,
                    }
                )
            except Exception as e:
                print(f"Split Error: {e}")
                return jsonify({"error": str(e)}), 500

    # -----------------------------------------
    # Handle table actions business logic
    # -----------------------------------------
    def handle_table_action(self, game_type, table_id, action):
        tables = self.snooker_tables if game_type == "snooker" else self.pool_tables
        table = tables[table_id]

        if action == "start":
            if table["status"] == "idle":
                table["status"] = "running"
                table["start_time"] = datetime.now()
                table["elapsed_seconds"] = 0
                table["session_start_time"] = datetime.now().strftime("%H:%M:%S")
                return f"{game_type.title()} Table {table_id} started"

        elif action == "pause":
            if table["status"] == "running":
                table["status"] = "paused"
                return f"{game_type.title()} Table {table_id} paused"
            elif table["status"] == "paused":
                table["status"] = "running"
                table["start_time"] = datetime.now()
                return f"{game_type.title()} Table {table_id} resumed"

        elif action == "end":
            if table["status"] in ["running", "paused"]:
                duration_minutes = table["elapsed_seconds"] / 60
                amount = duration_minutes * table["rate"]
                end_time = datetime.now().strftime("%H:%M:%S")
                session = {
                    "start_time": table.get("session_start_time", "00:00:00"),
                    "end_time": end_time,
                    "duration": round(duration_minutes, 1),
                    "amount": round(amount, 2),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "user": current_user.username,
                }
                table["sessions"].append(session)
                table["status"] = "idle"
                table["time"] = "00:00"
                table["amount"] = 0
                table["start_time"] = None
                table["elapsed_seconds"] = 0
                table["session_start_time"] = None
                return f"{game_type.title()} Table {table_id} ended - ₹{amount:.2f} for {duration_minutes:.1f} minutes"

        return "No action taken"

    # -----------------------------------------
    # Timer updater thread
    # -----------------------------------------
    def update_timers(self):
        print("⏰ Timer system started")
        while self.running:
            try:
                updated = False
                for tables in [self.snooker_tables, self.pool_tables]:
                    for table_id, table in tables.items():
                        if table["status"] == "running" and table["start_time"]:
                            table["elapsed_seconds"] += 1
                            minutes = table["elapsed_seconds"] // 60
                            seconds = table["elapsed_seconds"] % 60
                            table["time"] = f"{minutes:02d}:{seconds:02d}"
                            duration_minutes = table["elapsed_seconds"] / 60
                            table["amount"] = duration_minutes * table["rate"]
                            table["start_time"] = datetime.now()
                            updated = True
                if updated:
                    print(f"⏱️ Timers updated: {datetime.now().strftime('%H:%M:%S')}")
                time.sleep(1)
            except Exception as e:
                print(f"Timer error: {e}")
                time.sleep(1)

    # -----------------------------------------
    # HTML Templates
    # -----------------------------------------

    def get_login_template(self):
        return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Table Tracker - Login</title>
  <style>
    body { font-family: Helvetica, Arial, sans-serif; background:#222; color:#eee; text-align:center; }
    form { margin: 50px auto; padding: 20px; width: 300px; background: #333; border-radius: 8px; }
    input[type="text"], input[type="password"] { width: 90%; padding: 10px; margin: 10px 0; border-radius: 5px; border: none; }
    input[type="submit"] { padding: 10px 20px; border:none; background: #3498db; color: white; border-radius: 5px; cursor: pointer; }
    .flash-messages { color: #e74c3c; margin-bottom: 15px; }
    h1 { margin-top: 50px; }
  </style>
</head>
<body>
  <h1>🎯 Table Tracker Login</h1>
  <form action="" method="post">
    <input type="text" name="username" placeholder="Username" autofocus required />
    <input type="password" name="password" placeholder="Password" required />
    <input type="submit" value="Login" />
  </form>
  {% with messages = get_flashed_messages() %}
  {% if messages %}
  <div class="flash-messages">
    {% for message in messages %}
      <p>{{ message }}</p>
    {% endfor %}
  </div>
  {% endif %}
  {% endwith %}
</body>
</html>
        """

    def get_home_template(self):
        # Uses passed context variables {{ username }} and {{ role }} for dynamic content
        return """
<!doctype html>
<html lang="en">
<head>
<title>Table Tracker - Home</title>
<meta charset="UTF-8" />
<style>
  body { font-family: Arial, Helvetica, sans-serif; background: #121212; color: white; margin: 0; padding: 0; }
  header { padding: 20px; background: #222; display:flex; justify-content: space-between; align-items: center; }
  a { color: #1abc9c; text-decoration: none; font-weight: bold; }
  h1 { margin-left: 10px; }
  section { padding: 20px; }
  button { margin: 10px 5px; padding: 10px 15px; background: #1abc9c; border: none; border-radius: 4px; cursor: pointer; color: #121212; font-weight: bold; }
  .overview { display: flex; gap: 40px; justify-content: center; }
  .panel { background: #222; padding: 20px; border-radius: 10px; width: 300px; }
  .panel h2 { margin-top: 0; margin-bottom: 15px; }
  ul { list-style: none; padding: 0; }
  li { margin-bottom: 8px; }
  .links a { display:block; margin: 5px 0; color: #3498db; }
  .user-info { font-size: 14px; margin-left: auto; color: #aaa; }
</style>
</head>
<body>
<header>
  <h1>🎯 Table Tracker</h1>
  <div>
    <span class="user-info">👤 {{ username }} ({{ role.title() }})</span>
    &nbsp; | &nbsp;
    <a href="{{ url_for('logout') }}">Logout</a>
  </div>
</header>
<section>
  <h2>Welcome, {{ username }}!</h2>
  <p>Professional Table Management System with Snooker and Pool Tracking.</p>

  <div class="overview">
    <div class="panel">
      <h2>Snooker Tables</h2>
      <p>Full-featured snooker table tracking with timer, billing, and session management.</p>
      <a href="{{ url_for('snooker') }}"><button>Go to Snooker</button></a>
      <a href="{{ url_for('snooker_mobile') }}"><button>Snooker Mobile UI</button></a>
    </div>
    <div class="panel">
      <h2>Pool Tables</h2>
      <p>Pool table management with lower rates, split billing, and mobile support.</p>
      <a href="{{ url_for('pool') }}"><button>Go to Pool</button></a>
      <a href="{{ url_for('pool_mobile') }}"><button>Pool Mobile UI</button></a>
    </div>
  </div>

  {% if role == 'admin' %}
  <section style="margin-top: 40px;">
    <h2>👥 User Management</h2>
    <div>
      <h3>Add New User</h3>
      <form id="addUserForm" onsubmit="return addUser(event)">
        <input type="text" id="newUsername" placeholder="Username" required />
        <input type="password" id="newPassword" placeholder="Password" required />
        <select id="newRole">
          <option value="staff" selected>Staff</option>
          <option value="admin">Admin</option>
        </select>
        <button type="submit">Add User</button>
      </form>
    </div>
    <br />
    <div>
      <h3>Existing Users</h3>
      <ul id="userList"></ul>
    </div>
  </section>
  {% endif %}
</section>

<script>
  async function fetchUsers() {
    try {
      let res = await fetch('/api/users');
      let data = await res.json();
      if (data.success) {
        const list = document.getElementById('userList');
        list.innerHTML = '';
        data.users.forEach(user => {
          let li = document.createElement('li');
          li.textContent = user.username + " (" + user.role + ")";
          if (user.can_remove) {
            let btn = document.createElement('button');
            btn.textContent = 'Remove';
            btn.style.marginLeft = '10px';
            btn.onclick = () => removeUser(user.username);
            li.appendChild(btn);
          }
          list.appendChild(li);
        });
      } else {
        alert(data.error || "Failed to load users.");
      }
    } catch (err) {
      alert("Error fetching users: " + err);
    }
  }

  async function addUser(event) {
    event.preventDefault();
    try {
      const username = document.getElementById('newUsername').value.trim();
      const password = document.getElementById('newPassword').value.trim();
      const role = document.getElementById('newRole').value;
      const res = await fetch('/api/users/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role })
      });
      const data = await res.json();
      if (data.success) {
        alert(data.message);
        document.getElementById('addUserForm').reset();
        fetchUsers();
      } else {
        alert(data.error);
      }
    } catch (err) {
      alert("Error adding user: " + err);
    }
    return false;
  }

  async function removeUser(username) {
    if (!confirm('Remove user ' + username + '?')) return;
    try {
      const res = await fetch('/api/users/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username })
      });
      const data = await res.json();
      if (data.success) {
        alert(data.message);
        fetchUsers();
      } else {
        alert(data.error);
      }
    } catch (err) {
      alert("Error removing user: " + err);
    }
  }

  {% if role == 'admin' %}
  fetchUsers();
  {% endif %}
</script>

</body>
</html>
        """

    def get_game_template(self, game_type):
        main_color = "#3498db" if game_type == "snooker" else "#2ecc71"
        bg_color = "#111" if game_type == "snooker" else "#222"
        # No f-string necessary here; we inject the game_type into JS via a small variable in script tag.
        return f"""
<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>{game_type.title()} Tables - Table Tracker</title>
<style>
  body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin:0; padding:0;
    background: {bg_color};
    color: white;
  }}
  header {{
    background: {main_color};
    padding: 15px;
    text-align: center;
    font-size: 24px;
    font-weight: bold;
  }}
  #tables {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    margin: 20px;
    gap: 20px;
  }}
  .table-card {{
    background: rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 15px;
    width: 280px;
    box-shadow: 0 0 10px rgba(0,0,0,0.7);
  }}
  .table-card h3 {{
    margin: 0 0 10px 0;
  }}
  .status {{
    font-weight: bold;
    margin-bottom: 10px;
  }}
  .status.idle {{ color: #bbb; }}
  .status.running {{ color: #2ecc71; }}
  .status.paused {{ color: #f39c12; }}
  .stats {{
    display: flex;
    justify-content: space-between;
    margin-bottom: 10px;
  }}
  .stats div {{ font-size: 16px; }}
  button {{
    padding: 8px 12px;
    margin-right: 5px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: bold;
    color: #121212;
  }}
  button.start {{ background: #2ecc71; }}
  button.pause {{ background: #f39c12; }}
  button.end {{ background: #e74c3c; }}
  select.rate-select {{
    width: 100%;
    margin-bottom: 10px;
    border-radius: 6px;
    border: none;
    padding: 8px;
    font-size: 16px;
    font-weight: bold;
    color: #121212;
  }}
  .sessions-container {{
    max-height: 120px;
    overflow-y: auto;
    background: rgba(0,0,0,0.15);
    border-radius: 8px;
    padding: 8px;
    font-size: 13px;
  }}
  .session-item {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1fr;
    padding: 5px 2px;
    border-bottom: 1px solid rgba(255,255,255,0.2);
  }}
  .session-item:last-child {{
    border-bottom: none;
  }}
  .session-time {{ color: {main_color}; font-weight: 600; }}
  .session-duration {{ color: #ffd700; }}
  .session-amount {{ color: #90ee90; font-weight: 600; }}
  .session-date {{ color: #d3d3d3; font-size: 11px; }}
  .split-bill {{
    margin-top: 10px;
    text-align: center;
  }}
  input.split-players {{
    width: 50px;
    padding: 5px;
    font-size: 14px;
    border-radius: 6px;
    border: none;
    font-weight: bold;
    color: #121212;
  }}
  #splitResult {{
    margin-top: 5px;
    font-weight: bold;
  }}
  a.back-link {{
    display: block;
    margin: 10px 20px;
    color: {main_color};
    text-decoration: none;
    font-weight: bold;
  }}
</style>
</head>
<body>
<header>{game_type.title()} Table Tracker</header>
<a href="/" class="back-link">← Back to Home</a>
<div id="tables"></div>

<script>
  const gameType = "{game_type}";
  let tablesData = {{}};
  const availableRates = [];
  let refreshInterval;

  async function fetchTables() {{
    try {{
      let res = await fetch(`/api/${{gameType}}/tables`);
      let data = await res.json();
      if (data.success) {{
        tablesData = data.tables;
        availableRates.length = 0;
        data.available_rates.forEach(rate => availableRates.push(rate));
        renderTables();
      }} else {{
        alert(data.error || "Failed to load tables data.");
      }}
    }} catch (err) {{
      alert("Error fetching table data: " + err);
    }}
  }}

  function renderTables() {{
    const container = document.getElementById('tables');
    container.innerHTML = "";
    Object.keys(tablesData).forEach(key => {{
      const table = tablesData[key];
      const div = document.createElement("div");
      div.className = "table-card";

      let statusClass = table.status;
      if (!["idle","running","paused"].includes(statusClass)) statusClass = "idle";

      div.innerHTML = `
        <h3>Table ${key}</h3>
        <div class="status ${statusClass}">Status: ${table.status.charAt(0).toUpperCase() + table.status.slice(1)}</div>
        <div class="stats">
          <div>Time: ${table.time}</div>
          <div>Amount: ₹${table.amount.toFixed(2)}</div>
        </div>
        <label for="rate-select-${key}">Rate (₹/min):</label>
        <select class="rate-select" id="rate-select-${key}" ${table.status !== "idle" ? "disabled" : ""}>
          ${availableRates.map(rate => `<option value="${rate}" ${rate === table.rate ? "selected" : ""}>₹${rate}</option>`).join('')}
        </select>
        <div>
          ${table.status === "idle" ? `<button class="start" onclick="startTable(${key})">Start</button>` : ""}
          ${table.status === "running" ? `<button class="pause" onclick="pauseTable(${key})">Pause</button>` : ""}
          ${table.status === "paused" ? `<button class="start" onclick="resumeTable(${key})">Resume</button>` : ""}
          ${(table.status === "running" || table.status === "paused") ? `<button class="end" onclick="endTable(${key})">End</button>` : ""}
          <button onclick="clearSessions(${key})">Clear</button>
        </div>
        <div class="sessions-container" id="sessions-${key}">
          ${table.sessions.length > 0 ? table.sessions.map(s => `
            <div class="session-item">
              <div class="session-time">${s.start_time} - ${s.end_time}</div>
              <div class="session-duration">${s.duration} min</div>
              <div class="session-amount">₹${s.amount.toFixed(2)}</div>
              <div class="session-date">${s.date}</div>
            </div>
          `).join('') : '<div class="no-sessions">No sessions yet</div>'}
        </div>
        <div class="split-bill" id="split-bill-${key}">
          <input type="number" class="split-players" min="1" max="50" placeholder="Players" id="players-input-${key}"/>
          <button onclick="splitBill(${key})">Split Bill</button>
          <div id="splitResult-${key}"></div>
        </div>
      `;
      container.appendChild(div);

      // Add event listener for rate change
      const rateSelect = div.querySelector(`#rate-select-${key}`);
      rateSelect.onchange = async function() {{
        await updateRate(key, rateSelect.value);
      }};
    }});
  }}

  async function startTable(tableId) {{
    await sendTableAction(tableId, "start");
  }}
  async function pauseTable(tableId) {{
    await sendTableAction(tableId, "pause");
  }}
  async function resumeTable(tableId) {{
    await sendTableAction(tableId, "pause"); // "pause" toggles pause/resume
  }}
  async function endTable(tableId) {{
    await sendTableAction(tableId, "end");
  }}

  async function sendTableAction(tableId, action) {{
    try {{
      const res = await fetch(`/api/${{gameType}}/table/${{tableId}}/action`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ action }})
      }});
      const data = await res.json();
      if (data.success) {{
        alert(data.result);
        await fetchTables();
      }} else {{
        alert(data.error);
      }}
    }} catch(err) {{
      alert("Error: " + err);
    }}
  }}

  async function updateRate(tableId, rate) {{
    try {{
      const res = await fetch(`/api/${{gameType}}/table/${{tableId}}/rate`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ rate }})
      }});
      const data = await res.json();
      if (data.success) {{
        alert(`Rate updated to ₹${{rate}}/min`);
        await fetchTables();
      }} else {{
        alert(data.error);
      }}
    }} catch(err) {{
      alert("Error updating rate: " + err);
    }}
  }}

  async function clearSessions(tableId) {{
    if (!confirm("Clear all sessions for this table?")) return;
    try {{
      const res = await fetch(`/api/${{gameType}}/table/${{tableId}}/clear`, {{
        method: 'POST',
      }});
      const data = await res.json();
      if (data.success) {{
        alert(data.message);
        await fetchTables();
      }} else {{
        alert(data.error);
      }}
    }} catch(err) {{
      alert("Error clearing sessions: " + err);
    }}
  }}

  async function splitBill(tableId) {{
    const playersInput = document.getElementById(`players-input-${{tableId}}`);
    const players = parseInt(playersInput.value);
    const resultBox = document.getElementById(`splitResult-${{tableId}}`);
    if (!players || players < 1 || players > 50) {{
      alert("Please enter valid number of players between 1 and 50.");
      return;
    }}
    try {{
      const res = await fetch(`/api/${{gameType}}/table/${{tableId}}/split`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ players }})
      }});
      const data = await res.json();
      if (data.success) {{
        resultBox.textContent = `₹${{data.total_amount.toFixed(2)}} total: ₹${{data.per_player.toFixed(2)}} per player`;
      }} else {{
        alert(data.error);
      }}
    }} catch(err) {{
      alert("Error splitting bill: " + err);
    }}
  }}

  // Initial fetch and refresh every second
  fetchTables();
  refreshInterval = setInterval(fetchTables, 1000);
</script>
</body>
</html>
        """

    def get_mobile_template(self, game_type):
        return self.get_game_template(game_type)


# -----------------------------------
# Deployment Entrypoint
# -----------------------------------
tracker = TableTracker()
app = tracker.app  # Expose Flask app for Gunicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
