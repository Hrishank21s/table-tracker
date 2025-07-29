#!/usr/bin/env python3
"""
Enhanced Complete Table Tracker System - With Settings Tab and Fixed Scrolling
"""

import json
import threading
import time
from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
from datetime import datetime
import socket
import webbrowser

class SimpleTableTracker:
    def __init__(self):
        self.tables = {
            1: {"status": "idle", "time": "00:00", "rate": 3.0, "amount": 0.0, "start_time": None, "elapsed_seconds": 0, "sessions": []},
            2: {"status": "idle", "time": "00:00", "rate": 4.0, "amount": 0.0, "start_time": None, "elapsed_seconds": 0, "sessions": []},
            3: {"status": "idle", "time": "00:00", "rate": 4.5, "amount": 0.0, "start_time": None, "elapsed_seconds": 0, "sessions": []}
        }
        
        # Available pricing options
        self.available_rates = [2.0, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5]
        
        self.running = True
        self.app = Flask(__name__)
        CORS(self.app)
        self.setup_routes()
        
    def setup_routes(self):
        @self.app.route('/')
        def desktop_interface():
            return render_template_string(self.get_desktop_html())
            
        @self.app.route('/mobile')
        def mobile_interface():
            return render_template_string(self.get_mobile_html())
            
        @self.app.route('/api/tables', methods=['GET'])
        def get_tables():
            return jsonify({
                "success": True,
                "tables": self.tables,
                "available_rates": self.available_rates,
                "timestamp": datetime.now().isoformat()
            })
            
        @self.app.route('/api/table/<int:table_id>/action', methods=['POST'])
        def table_action(table_id):
            try:
                data = request.get_json()
                action = data.get('action')
                
                if table_id not in self.tables or action not in ['start', 'pause', 'end']:
                    return jsonify({"error": "Invalid request"}), 400
                
                result = self.handle_table_action(table_id, action)
                print(f"Action: Table {table_id} - {action} - {result}")
                
                return jsonify({
                    "success": True,
                    "table": table_id,
                    "action": action,
                    "result": result,
                    "tables": self.tables
                })
                
            except Exception as e:
                print(f"API Error: {e}")
                return jsonify({"error": str(e)}), 500
        
        # NEW ROUTE: Update table rate
        @self.app.route('/api/table/<int:table_id>/rate', methods=['POST'])
        def update_table_rate(table_id):
            try:
                data = request.get_json()
                new_rate = float(data.get('rate'))
                
                if table_id not in self.tables:
                    return jsonify({"error": "Invalid table ID"}), 400
                
                if new_rate not in self.available_rates:
                    return jsonify({"error": "Invalid rate"}), 400
                
                # Update rate only if table is idle
                if self.tables[table_id]['status'] != 'idle':
                    return jsonify({"error": "Cannot change rate while table is running"}), 400
                
                self.tables[table_id]['rate'] = new_rate
                print(f"Table {table_id} rate updated to ₹{new_rate}/min")
                
                return jsonify({
                    "success": True,
                    "table": table_id,
                    "new_rate": new_rate,
                    "tables": self.tables
                })
                
            except Exception as e:
                print(f"Rate Update Error: {e}")
                return jsonify({"error": str(e)}), 500
        
        # Clear table data route
        @self.app.route('/api/table/<int:table_id>/clear', methods=['POST'])
        def clear_table_data(table_id):
            try:
                if table_id not in self.tables:
                    return jsonify({"error": "Invalid table ID"}), 400
                
                self.tables[table_id]['sessions'] = []
                print(f"Table {table_id} session data cleared")
                
                return jsonify({
                    "success": True,
                    "table": table_id,
                    "message": f"Table {table_id} data cleared",
                    "tables": self.tables
                })
                
            except Exception as e:
                print(f"Clear Error: {e}")
                return jsonify({"error": str(e)}), 500
    
    def handle_table_action(self, table_id, action):
        table = self.tables[table_id]
        
        if action == 'start':
            if table['status'] == 'idle':
                table['status'] = 'running'
                table['start_time'] = datetime.now()
                table['elapsed_seconds'] = 0
                table['session_start_time'] = datetime.now().strftime("%H:%M:%S")
                return f"Table {table_id} started"
                
        elif action == 'pause':
            if table['status'] == 'running':
                table['status'] = 'paused'
                return f"Table {table_id} paused"
            elif table['status'] == 'paused':
                table['status'] = 'running'
                table['start_time'] = datetime.now()
                return f"Table {table_id} resumed"
                
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
                    "date": datetime.now().strftime("%Y-%m-%d")
                }
                table['sessions'].append(session)
                
                table['status'] = 'idle'
                table['time'] = '00:00'
                table['amount'] = 0
                table['start_time'] = None
                table['elapsed_seconds'] = 0
                table['session_start_time'] = None
                
                return f"Table {table_id} ended - ₹{amount:.2f} for {duration_minutes:.1f} minutes"
        
        return "No action taken"
    
    def update_timers(self):
        """Background timer updates"""
        print("⏰ Timer thread started")
        while self.running:
            try:
                updated = False
                for table_id, table in self.tables.items():
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
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return '127.0.0.1'
    
    def get_desktop_html(self):
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Table Tracker - Desktop</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: white;
        }
        .header { text-align: center; margin-bottom: 30px; position: relative; }
        .header h1 { font-size: 2.5rem; font-weight: 700; margin-bottom: 10px; }
        
        /* Settings Button */
        .settings-btn {
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
        }
        .settings-btn:hover { background: rgba(255,255,255,0.3); transform: scale(1.1); }
        
        /* Settings Panel */
        .settings-panel {
            position: fixed;
            top: 0;
            right: -350px;
            width: 350px;
            height: 100vh;
            background: rgba(0,0,0,0.9);
            backdrop-filter: blur(20px);
            transition: right 0.3s ease;
            z-index: 999;
            padding: 20px;
            overflow-y: auto;
        }
        .settings-panel.open { right: 0; }
        .settings-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }
        .settings-title { font-size: 1.5rem; font-weight: 600; }
        .close-settings {
            background: none;
            border: none;
            color: white;
            font-size: 24px;
            cursor: pointer;
        }
        .rate-setting {
            margin-bottom: 25px;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
        }
        .rate-setting h3 {
            margin-bottom: 15px;
            font-size: 1.2rem;
            color: #4caf50;
        }
        .rate-selector {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }
        .rate-option {
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border: 2px solid transparent;
            border-radius: 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 600;
        }
        .rate-option:hover { background: rgba(255,255,255,0.2); }
        .rate-option.active { border-color: #4caf50; background: rgba(76, 175, 80, 0.3); }
        .rate-option.disabled { opacity: 0.5; cursor: not-allowed; }
        
        .status-bar {
            background: rgba(255,255,255,0.15);
            padding: 15px 25px;
            border-radius: 15px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        .tables-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px;
            max-width: 1400px;
            margin: 0 auto;
        }
        .table-card {
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.3s ease;
        }
        .table-card:hover { transform: translateY(-5px); }
        .table-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .table-name { font-size: 1.4rem; font-weight: 600; }
        .table-status {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-idle { background: #6c757d; color: white; }
        .status-running { background: #28a745; color: white; }
        .status-paused { background: #fd7e14; color: white; }
        .table-time {
            font-size: 3rem;
            font-weight: 700;
            text-align: center;
            margin: 25px 0;
            font-family: 'SF Mono', Monaco, Consolas, monospace;
        }
        .table-info {
            display: flex;
            justify-content: space-between;
            margin: 20px 0;
            font-size: 14px;
        }
        .info-item {
            text-align: center;
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            flex: 1;
            margin: 0 5px;
        }
        .controls {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 12px;
            margin: 25px 0;
        }
        .control-btn {
            padding: 15px;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .control-btn:hover { transform: translateY(-2px); }
        .control-btn:active { transform: translateY(0); }
        .btn-start { background: #28a745; color: white; }
        .btn-pause { background: #fd7e14; color: white; }
        .btn-end { background: #dc3545; color: white; }
        
        .sessions-section {
            margin-top: 25px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.3);
        }
        .sessions-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .sessions-title {
            font-size: 14px;
            font-weight: 600;
            color: #ecf0f1;
        }
        .clear-btn {
            padding: 6px 12px;
            background: #e74c3c;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .clear-btn:hover { background: #c0392b; }
        .sessions-container {
            max-height: 200px;
            overflow-y: auto;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            padding: 10px;
            /* Fix scrolling issue - maintain scroll position */
            scroll-behavior: smooth;
        }
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
        }
        .session-time { color: #3498db; font-weight: 600; }
        .session-duration { color: #f39c12; }
        .session-amount { color: #2ecc71; font-weight: 600; }
        .session-date { color: #95a5a6; font-size: 11px; }
        .no-sessions {
            text-align: center;
            color: #95a5a6;
            font-style: italic;
            padding: 20px;
        }
    </style>
</head>
<body>
    <button class="settings-btn" onclick="toggleSettings()">⚙️</button>
    
    <div class="settings-panel" id="settings-panel">
        <div class="settings-header">
            <div class="settings-title">⚙️ Settings</div>
            <button class="close-settings" onclick="toggleSettings()">✕</button>
        </div>
        <div id="rate-settings">
            <!-- Rate settings will be populated here -->
        </div>
    </div>

    <div class="header">
        <h1>🎯 Table Tracker Desktop</h1>
    </div>
    
    <div class="status-bar">
        <div>💻 Desktop Interface</div>
        <div id="update-status">🔄 Loading...</div>
        <div id="current-time"></div>
    </div>
    
    <div class="tables-container" id="tables-container"></div>

    <script>
        class TableTracker {
            constructor() {
                this.tables = {};
                this.availableRates = [];
                this.scrollPositions = {}; // Track scroll positions
                this.init();
            }
            
            init() {
                this.loadTables();
                this.updateClock();
                setInterval(() => this.updateClock(), 1000);
                setInterval(() => this.loadTables(), 2000);
            }
            
            async loadTables() {
                try {
                    // Save scroll positions before update
                    this.saveScrollPositions();
                    
                    const response = await fetch('/api/tables');
                    const data = await response.json();
                    
                    if (data.success) {
                        this.tables = data.tables;
                        this.availableRates = data.available_rates;
                        this.renderTables();
                        this.renderSettings();
                        
                        // Restore scroll positions after render
                        setTimeout(() => this.restoreScrollPositions(), 50);
                        
                        document.getElementById('update-status').textContent = '🟢 Live Updates';
                    }
                } catch (error) {
                    console.error('Failed to load tables:', error);
                    document.getElementById('update-status').textContent = '🔴 Connection Error';
                }
            }
            
            saveScrollPositions() {
                Object.keys(this.tables).forEach(tableId => {
                    const container = document.getElementById(`sessions-container-${tableId}`);
                    if (container) {
                        this.scrollPositions[tableId] = container.scrollTop;
                    }
                });
            }
            
            restoreScrollPositions() {
                Object.keys(this.scrollPositions).forEach(tableId => {
                    const container = document.getElementById(`sessions-container-${tableId}`);
                    if (container && this.scrollPositions[tableId]) {
                        container.scrollTop = this.scrollPositions[tableId];
                    }
                });
            }
            
            updateClock() {
                const now = new Date();
                document.getElementById('current-time').textContent = now.toLocaleTimeString();
            }
            
            renderSettings() {
                const container = document.getElementById('rate-settings');
                container.innerHTML = '';
                
                Object.keys(this.tables).forEach(tableId => {
                    const table = this.tables[tableId];
                    const settingDiv = document.createElement('div');
                    settingDiv.className = 'rate-setting';
                    
                    const rateOptions = this.availableRates.map(rate => {
                        const isActive = table.rate === rate;
                        const isDisabled = table.status !== 'idle';
                        return `<div class="rate-option ${isActive ? 'active' : ''} ${isDisabled ? 'disabled' : ''}" 
                                    onclick="${isDisabled ? '' : `tracker.updateRate(${tableId}, ${rate})`}">
                                    ₹${rate}/min
                                </div>`;
                    }).join('');
                    
                    settingDiv.innerHTML = `
                        <h3>Table ${tableId} Pricing</h3>
                        <div style="margin-bottom: 10px; font-size: 12px; opacity: 0.8;">
                            ${table.status !== 'idle' ? '⚠️ Stop table to change rate' : 'Select rate per minute:'}
                        </div>
                        <div class="rate-selector">
                            ${rateOptions}
                        </div>
                    `;
                    
                    container.appendChild(settingDiv);
                });
            }
            
            renderTables() {
                const container = document.getElementById('tables-container');
                container.innerHTML = '';
                
                Object.keys(this.tables).forEach(tableId => {
                    const table = this.tables[tableId];
                    const card = document.createElement('div');
                    card.className = 'table-card';
                    
                    let sessionsHTML = '';
                    if (table.sessions && table.sessions.length > 0) {
                        sessionsHTML = table.sessions.map(session => 
                            `<div class="session-item">
                                <div class="session-time">${session.start_time} - ${session.end_time}</div>
                                <div class="session-duration">${session.duration}min</div>
                                <div class="session-amount">₹${session.amount}</div>
                                <div class="session-date">${session.date}</div>
                            </div>`
                        ).join('');
                    } else {
                        sessionsHTML = '<div class="no-sessions">No sessions recorded yet</div>';
                    }
                    
                    card.innerHTML = `
                        <div class="table-header">
                            <div class="table-name">Table ${tableId}</div>
                            <div class="table-status status-${table.status}">${table.status}</div>
                        </div>
                        <div class="table-time">${table.time}</div>
                        <div class="table-info">
                            <div class="info-item">
                                <div>Rate</div>
                                <strong>₹${table.rate}/min</strong>
                            </div>
                            <div class="info-item">
                                <div>Current Amount</div>
                                <strong>₹${table.amount.toFixed(2)}</strong>
                            </div>
                        </div>
                        <div class="controls">
                            <button class="control-btn btn-start" onclick="tracker.sendAction(${tableId}, 'start')">START</button>
                            <button class="control-btn btn-pause" onclick="tracker.sendAction(${tableId}, 'pause')">PAUSE</button>
                            <button class="control-btn btn-end" onclick="tracker.sendAction(${tableId}, 'end')">END</button>
                        </div>
                        <div class="sessions-section">
                            <div class="sessions-header">
                                <div class="sessions-title">📊 Session History</div>
                                <button class="clear-btn" onclick="tracker.clearTableData(${tableId})" 
                                        ${table.sessions && table.sessions.length > 0 ? '' : 'style="opacity: 0.5;" disabled'}>
                                    🗑️ Clear Data
                                </button>
                            </div>
                            <div class="sessions-container" id="sessions-container-${tableId}">
                                ${sessionsHTML}
                            </div>
                        </div>
                    `;
                    
                    container.appendChild(card);
                });
            }
            
            async sendAction(tableId, action) {
                try {
                    const response = await fetch(`/api/table/${tableId}/action`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({action: action})
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        console.log(`Action successful: ${result.result}`);
                        if (result.tables) {
                            this.tables = result.tables;
                            this.renderTables();
                            this.renderSettings();
                            setTimeout(() => this.restoreScrollPositions(), 50);
                        }
                    } else {
                        console.error('Action failed:', result.error);
                    }
                } catch (error) {
                    console.error('Action request failed:', error);
                }
            }
            
            async updateRate(tableId, newRate) {
                try {
                    const response = await fetch(`/api/table/${tableId}/rate`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({rate: newRate})
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        console.log(`Rate updated: Table ${tableId} - ₹${newRate}/min`);
                        if (result.tables) {
                            this.tables = result.tables;
                            this.renderTables();
                            this.renderSettings();
                        }
                    } else {
                        alert(`Error: ${result.error}`);
                    }
                } catch (error) {
                    console.error('Rate update failed:', error);
                }
            }
            
            async clearTableData(tableId) {
                if (!confirm(`Are you sure you want to clear all session data for Table ${tableId}?`)) {
                    return;
                }
                
                try {
                    const response = await fetch(`/api/table/${tableId}/clear`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'}
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        console.log(`Table ${tableId} data cleared`);
                        if (result.tables) {
                            this.tables = result.tables;
                            this.renderTables();
                        }
                    } else {
                        console.error('Clear failed:', result.error);
                    }
                } catch (error) {
                    console.error('Clear request failed:', error);
                }
            }
        }
        
        function toggleSettings() {
            const panel = document.getElementById('settings-panel');
            panel.classList.toggle('open');
        }
        
        const tracker = new TableTracker();
    </script>
</body>
</html>"""

    def get_mobile_html(self):
        # Keep the same mobile HTML as before
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Table Remote Control</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 1.8rem; font-weight: 700; }
        .connection-status {
            padding: 12px 20px;
            border-radius: 25px;
            font-size: 14px;
            background: rgba(255,255,255,0.15);
            text-align: center;
            margin-bottom: 25px;
            backdrop-filter: blur(10px);
        }
        .table-card {
            background: rgba(255,255,255,0.1);
            border-radius: 18px;
            padding: 24px;
            margin-bottom: 20px;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        .table-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .table-name { font-size: 1.3rem; font-weight: 600; }
        .table-status {
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-idle { background: #6c757d; }
        .status-running { background: #28a745; }
        .status-paused { background: #fd7e14; }
        .table-time {
            font-size: 2.5rem;
            font-weight: 700;
            text-align: center;
            margin: 20px 0;
            font-family: 'SF Mono', Monaco, Consolas, monospace;
        }
        .table-amount {
            text-align: center;
            font-size: 1.3rem;
            font-weight: 600;
            color: #ffd700;
            margin: 15px 0;
        }
        .controls {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 12px;
            margin-bottom: 20px;
        }
        .control-btn {
            padding: 16px 8px;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .control-btn:active { transform: scale(0.95); }
        .btn-start { background: #28a745; color: white; }
        .btn-pause { background: #fd7e14; color: white; }
        .btn-end { background: #dc3545; color: white; }
        .recent-sessions {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.3);
        }
        .sessions-title {
            font-size: 12px;
            color: #bdc3c7;
            margin-bottom: 10px;
        }
        .session-summary {
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: #ecf0f1;
            margin: 3px 0;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            font-size: 12px;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📱 Remote Control</h1>
    </div>
    
    <div class="connection-status" id="connection-status">🔄 Loading...</div>
    <div id="tables-container"></div>
    
    <div class="footer">
        Remote control for Table Tracker<br>
        Auto-updates every 2 seconds
    </div>

    <script>
        class MobileRemote {
            constructor() {
                this.tables = {};
                this.init();
            }
            
            init() {
                this.loadTables();
                setInterval(() => this.loadTables(), 2000);
            }
            
            async loadTables() {
                try {
                    const response = await fetch('/api/tables');
                    const data = await response.json();
                    
                    if (data.success) {
                        this.tables = data.tables;
                        this.renderTables();
                        document.getElementById('connection-status').innerHTML = '🟢 Connected • Live updates';
                    }
                } catch (error) {
                    console.error('Failed to load tables:', error);
                    document.getElementById('connection-status').innerHTML = '🔴 Connection error';
                }
            }
            
            renderTables() {
                const container = document.getElementById('tables-container');
                container.innerHTML = '';
                
                Object.keys(this.tables).forEach(tableId => {
                    const table = this.tables[tableId];
                    const card = document.createElement('div');
                    card.className = 'table-card';
                    
                    let recentSessionsHTML = '';
                    if (table.sessions && table.sessions.length > 0) {
                        const recent = table.sessions.slice(-3);
                        recentSessionsHTML = `
                            <div class="recent-sessions">
                                <div class="sessions-title">Recent Sessions (${table.sessions.length} total)</div>
                                ${recent.map(session => 
                                    `<div class="session-summary">
                                        <span>${session.start_time}-${session.end_time}</span>
                                        <span>${session.duration}min - ₹${session.amount}</span>
                                    </div>`
                                ).join('')}
                            </div>
                        `;
                    }
                    
                    card.innerHTML = `
                        <div class="table-header">
                            <div class="table-name">Table ${tableId}</div>
                            <div class="table-status status-${table.status}">${table.status}</div>
                        </div>
                        <div class="table-time">${table.time}</div>
                        <div class="table-amount">₹${table.amount.toFixed(2)} (₹${table.rate}/min)</div>
                        <div class="controls">
                            <button class="control-btn btn-start" onclick="remote.sendAction(${tableId}, 'start')">START</button>
                            <button class="control-btn btn-pause" onclick="remote.sendAction(${tableId}, 'pause')">PAUSE</button>
                            <button class="control-btn btn-end" onclick="remote.sendAction(${tableId}, 'end')">END</button>
                        </div>
                        ${recentSessionsHTML}
                    `;
                    
                    container.appendChild(card);
                });
            }
            
            async sendAction(tableId, action) {
                try {
                    const response = await fetch(`/api/table/${tableId}/action`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({action: action})
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        if (result.tables) {
                            this.tables = result.tables;
                            this.renderTables();
                        }
                    }
                } catch (error) {
                    console.error('Mobile action failed:', error);
                }
            }
        }
        
        const remote = new MobileRemote();
    </script>
</body>
</html>"""
    
    def start(self):
        local_ip = self.get_local_ip()
        
        print("\n" + "="*60)
        print("🚀 ENHANCED TABLE TRACKER WITH SETTINGS & FIXED SCROLLING")
        print("="*60)
        print(f"🖥️  Desktop Interface: http://{local_ip}:8080")
        print(f"📱 Mobile Interface: http://{local_ip}:8080/mobile")
        print(f"🌐 Local IP: {local_ip}")
        print("="*60)
        print("✨ New Features:")
        print("   • Settings tab in top-right corner (⚙️)")
        print("   • Rate pricing: 2, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5")
        print("   • Fixed scrolling bug - maintains scroll position")
        print("   • Cannot change rate while table is running")
        print("   • Persistent session data with clear buttons")
        print("="*60)
        print("📝 Instructions:")
        print("   1. Click ⚙️ button to open settings")
        print("   2. Change rates only when table is idle")
        print("   3. Session scroll stays in position during updates")
        print("   4. Press Ctrl+C to stop")
        print("="*60)
        
        # Start timer thread
        timer_thread = threading.Thread(target=self.update_timers)
        timer_thread.daemon = True
        timer_thread.start()
        
        # Auto-open desktop
        try:
            webbrowser.open(f'http://{local_ip}:8080')
        except:
            pass
        
        # Start Flask server (blocking)
        try:
            self.app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
        except KeyboardInterrupt:
            print("\n\n⏹️ Server stopped by user")
            self.running = False

if __name__ == "__main__":
    print("🚀 Starting Enhanced Table Tracker System...")
    try:
        tracker = SimpleTableTracker()
        tracker.start()
    except KeyboardInterrupt:
        print("\n\n👋 System shutdown complete!")
    except Exception as e:
        print(f"\n❌ System error: {e}")
        import traceback
        traceback.print_exc()

