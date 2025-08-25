"""
Lightweight Task Tracker - Simple BDR task management
Deliberately minimal to avoid feature creep
"""
import sqlite3
import json
import uuid
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import csv

from flask import Flask, request, jsonify, render_template_string, send_file
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Database setup
DB_PATH = "tasks.db"

def init_db():
    """Initialize the database with minimal schema"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Just 4 tables - no more!
    c.execute('''CREATE TABLE IF NOT EXISTS contacts (
        id TEXT PRIMARY KEY,
        name TEXT,
        company TEXT,
        email TEXT,
        phone TEXT,
        status TEXT DEFAULT 'new',
        assigned_to TEXT,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        contact_id TEXT,
        user_id TEXT,
        type TEXT,
        status TEXT DEFAULT 'pending',
        due_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY (contact_id) REFERENCES contacts (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS activities (
        id TEXT PRIMARY KEY,
        contact_id TEXT,
        user_id TEXT,
        type TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (contact_id) REFERENCES contacts (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create default user
    c.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", 
             (str(uuid.uuid4()), "Default BDR"))
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Simple HTML interface (no external dependencies)
SIMPLE_UI = '''
<!DOCTYPE html>
<html>
<head>
    <title>Task Tracker</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #4CAF50;
        }
        .task-list {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .task-item {
            display: flex;
            align-items: center;
            padding: 12px;
            border-bottom: 1px solid #eee;
            transition: background 0.2s;
        }
        .task-item:hover {
            background: #f9f9f9;
        }
        .task-checkbox {
            margin-right: 15px;
        }
        .task-info {
            flex: 1;
        }
        .task-company {
            font-weight: bold;
            color: #333;
        }
        .task-name {
            color: #666;
            font-size: 0.9em;
        }
        .task-actions {
            display: flex;
            gap: 10px;
        }
        button {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        button:hover {
            background: #45a049;
        }
        button.secondary {
            background: #757575;
        }
        .upload-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        input[type="file"] {
            margin: 10px 0;
        }
        .success {
            color: #4CAF50;
            margin: 10px 0;
        }
        .error {
            color: #f44336;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <h1>📋 Task Tracker</h1>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-number" id="todayCount">0</div>
            <div>Tasks Today</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="completedCount">0</div>
            <div>Completed</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="contactsCount">0</div>
            <div>Total Contacts</div>
        </div>
    </div>
    
    <div class="upload-section">
        <h2>Import Contacts</h2>
        <input type="file" id="fileInput" accept=".csv">
        <button onclick="uploadFile()">Import CSV</button>
        <button class="secondary" onclick="assignTasks()">Auto-Assign Tasks</button>
        <div id="uploadMessage"></div>
    </div>
    
    <div class="task-list">
        <h2>Today's Tasks</h2>
        <div id="taskList">Loading...</div>
    </div>
    
    <script>
        // Load tasks on page load
        window.onload = function() {
            loadTasks();
            loadStats();
        };
        
        function loadTasks() {
            fetch('/api/tasks/today')
                .then(response => response.json())
                .then(tasks => {
                    const taskList = document.getElementById('taskList');
                    if (tasks.length === 0) {
                        taskList.innerHTML = '<p>No tasks for today. Import contacts to get started!</p>';
                        return;
                    }
                    
                    taskList.innerHTML = tasks.map(task => `
                        <div class="task-item">
                            <input type="checkbox" class="task-checkbox" 
                                   onchange="completeTask('${task.id}')">
                            <div class="task-info">
                                <div class="task-company">${task.company || 'Unknown Company'}</div>
                                <div class="task-name">${task.name || 'Unknown'} - ${task.email || 'No email'}</div>
                            </div>
                            <div class="task-actions">
                                <button onclick="logActivity('${task.contact_id}', 'called')">Called</button>
                                <button onclick="logActivity('${task.contact_id}', 'emailed')">Emailed</button>
                                <button class="secondary" onclick="logActivity('${task.contact_id}', 'no_answer')">No Answer</button>
                            </div>
                        </div>
                    `).join('');
                });
        }
        
        function loadStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(stats => {
                    document.getElementById('todayCount').textContent = stats.today_tasks;
                    document.getElementById('completedCount').textContent = stats.completed_today;
                    document.getElementById('contactsCount').textContent = stats.total_contacts;
                });
        }
        
        function completeTask(taskId) {
            fetch(`/api/tasks/${taskId}/complete`, { method: 'POST' })
                .then(response => response.json())
                .then(result => {
                    loadTasks();
                    loadStats();
                });
        }
        
        function logActivity(contactId, type) {
            fetch('/api/activities', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contact_id: contactId,
                    type: type,
                    notes: `${type} at ${new Date().toLocaleTimeString()}`
                })
            })
            .then(response => response.json())
            .then(result => {
                loadTasks();
                // Auto-create follow-up task if needed
                if (type === 'no_answer' || type === 'called') {
                    createFollowUpTask(contactId);
                }
            });
        }
        
        function createFollowUpTask(contactId) {
            fetch('/api/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contact_id: contactId,
                    type: 'follow_up',
                    due_date: new Date(Date.now() + 86400000).toISOString() // Tomorrow
                })
            });
        }
        
        function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('Please select a file');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            fetch('/api/import', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(result => {
                document.getElementById('uploadMessage').innerHTML = 
                    `<div class="success">✓ Imported ${result.count} contacts</div>`;
                loadTasks();
                loadStats();
            })
            .catch(error => {
                document.getElementById('uploadMessage').innerHTML = 
                    `<div class="error">Error: ${error.message}</div>`;
            });
        }
        
        function assignTasks() {
            fetch('/api/tasks/auto-assign', { method: 'POST' })
                .then(response => response.json())
                .then(result => {
                    alert(`Created ${result.count} tasks`);
                    loadTasks();
                    loadStats();
                });
        }
    </script>
</body>
</html>
'''

# API Routes (minimal - just what's needed)

@app.route('/')
def index():
    """Serve the simple UI"""
    return SIMPLE_UI

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    """Get all contacts"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    contacts = c.execute("SELECT * FROM contacts ORDER BY imported_at DESC").fetchall()
    conn.close()
    
    return jsonify([dict(contact) for contact in contacts])

@app.route('/api/import', methods=['POST'])
def import_contacts():
    """Import contacts from CSV"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save temporarily and read
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    count = 0
    try:
        with open(tmp_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                contact_id = str(uuid.uuid4())
                
                # Map common column names
                name = row.get('name') or row.get('Name') or ''
                company = row.get('company') or row.get('Company') or ''
                email = row.get('email') or row.get('Email') or row.get('primary_email') or ''
                phone = row.get('phone') or row.get('Phone') or row.get('primary_phone') or ''
                
                c.execute("""INSERT INTO contacts (id, name, company, email, phone) 
                           VALUES (?, ?, ?, ?, ?)""",
                         (contact_id, name, company, email, phone))
                count += 1
        
        conn.commit()
    finally:
        conn.close()
        os.unlink(tmp_path)
    
    return jsonify({'success': True, 'count': count})

@app.route('/api/tasks/today', methods=['GET'])
def get_today_tasks():
    """Get today's tasks"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    tasks = c.execute("""
        SELECT t.*, c.name, c.company, c.email, c.phone 
        FROM tasks t
        JOIN contacts c ON t.contact_id = c.id
        WHERE t.status = 'pending' 
        AND date(t.due_date) <= date('now')
        ORDER BY t.created_at
    """).fetchall()
    
    conn.close()
    
    return jsonify([dict(task) for task in tasks])

@app.route('/api/tasks/<task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """Mark task as complete"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""UPDATE tasks 
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP 
                WHERE id = ?""", (task_id,))
    
    # Update contact status
    c.execute("""UPDATE contacts 
                SET status = 'contacted' 
                WHERE id = (SELECT contact_id FROM tasks WHERE id = ?)""", (task_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/activities', methods=['POST'])
def log_activity():
    """Log an activity"""
    data = request.json
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    activity_id = str(uuid.uuid4())
    c.execute("""INSERT INTO activities (id, contact_id, user_id, type, notes)
                VALUES (?, ?, ?, ?, ?)""",
             (activity_id, data['contact_id'], 'default', data['type'], data.get('notes', '')))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'id': activity_id})

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    data = request.json
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    task_id = str(uuid.uuid4())
    c.execute("""INSERT INTO tasks (id, contact_id, user_id, type, due_date)
                VALUES (?, ?, ?, ?, ?)""",
             (task_id, data['contact_id'], 'default', data.get('type', 'call'), 
              data.get('due_date', date.today().isoformat())))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'id': task_id})

@app.route('/api/tasks/auto-assign', methods=['POST'])
def auto_assign_tasks():
    """Auto-create tasks for all new contacts"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get contacts without tasks
    new_contacts = c.execute("""
        SELECT id FROM contacts 
        WHERE status = 'new' 
        AND id NOT IN (SELECT contact_id FROM tasks WHERE status = 'pending')
    """).fetchall()
    
    count = 0
    for contact in new_contacts:
        task_id = str(uuid.uuid4())
        c.execute("""INSERT INTO tasks (id, contact_id, user_id, type, due_date)
                    VALUES (?, ?, ?, ?, ?)""",
                 (task_id, contact[0], 'default', 'initial_contact', date.today().isoformat()))
        count += 1
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'count': count})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get basic stats"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    stats = {
        'today_tasks': c.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'pending' AND date(due_date) <= date('now')"
        ).fetchone()[0],
        'completed_today': c.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'completed' AND date(completed_at) = date('now')"
        ).fetchone()[0],
        'total_contacts': c.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    }
    
    conn.close()
    
    return jsonify(stats)

@app.route('/api/export', methods=['GET'])
def export_data():
    """Export all data to CSV"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    contacts = c.execute("""
        SELECT c.*, 
               COUNT(DISTINCT a.id) as activity_count,
               COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.id END) as completed_tasks
        FROM contacts c
        LEFT JOIN activities a ON c.id = a.contact_id
        LEFT JOIN tasks t ON c.id = t.contact_id
        GROUP BY c.id
    """).fetchall()
    
    conn.close()
    
    # Create CSV
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Name', 'Company', 'Email', 'Phone', 'Status', 'Activities', 'Completed Tasks'])
    
    # Data
    for contact in contacts:
        writer.writerow([
            contact['name'],
            contact['company'],
            contact['email'],
            contact['phone'],
            contact['status'],
            contact['activity_count'],
            contact['completed_tasks']
        ])
    
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'contacts_export_{datetime.now().strftime("%Y%m%d")}.csv'
    )

if __name__ == '__main__':
    print("🚀 Task Tracker running at http://localhost:5000")
    print("📋 This is a minimal task tracker - no features will be added!")
    print("⏰ Remember: This is temporary. Plan to replace with a real CRM in 6 months.")
    app.run(debug=True, port=5000)