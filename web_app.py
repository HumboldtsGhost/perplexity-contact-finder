#!/usr/bin/env python3
"""
Unified Web Application - AI-Powered Contact Finder + Task Tracker
"""
from flask import Flask, render_template_string, request, jsonify, send_file
from flask_cors import CORS
import os
import json
import uuid
import csv
import sqlite3
import asyncio
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Optional
import tempfile
from werkzeug.utils import secure_filename
import threading
import time

# Import our modules
from config import Config
from ai_assistant import AIAssistant
from smart_enrichment import SmartEnrichmentEngine
from perplexity_client import PerplexityClient
from data_exporter import DataExporter

app = Flask(__name__)
CORS(app)

# Configure upload
UPLOAD_FOLDER = 'uploads'
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Global state
current_job = None
job_status = {}
enrichment_engine = None

# Initialize database for task tracker
def init_task_db():
    """Initialize task tracker database"""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
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
        completed_at TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

init_task_db()

# Beautiful modern HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Contact Finder Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .gradient-bg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .card-hover:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        }
        .role-card {
            transition: all 0.3s ease;
        }
        .role-card.selected {
            border-color: #667eea;
            background-color: #f3f4ff;
        }
        .progress-bar {
            transition: width 0.3s ease;
        }
    </style>
</head>
<body class="bg-gray-50">
    <!-- Header -->
    <nav class="gradient-bg text-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <i class="fas fa-search text-2xl mr-3"></i>
                    <span class="text-xl font-bold">Smart Contact Finder Pro</span>
                </div>
                <div class="flex items-center space-x-4">
                    <button onclick="showTab('finder')" class="tab-btn px-4 py-2 rounded hover:bg-white hover:bg-opacity-20">
                        <i class="fas fa-search mr-2"></i>Find Contacts
                    </button>
                    <button onclick="showTab('saved')" class="tab-btn px-4 py-2 rounded hover:bg-white hover:bg-opacity-20">
                        <i class="fas fa-database mr-2"></i>Saved Contacts
                    </button>
                    <button onclick="showTab('tasks')" class="tab-btn px-4 py-2 rounded hover:bg-white hover:bg-opacity-20">
                        <i class="fas fa-tasks mr-2"></i>Task Tracker
                    </button>
                    <button onclick="showSettings()" class="px-4 py-2 rounded hover:bg-white hover:bg-opacity-20">
                        <i class="fas fa-cog mr-2"></i>Settings
                    </button>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        <!-- Finder Tab -->
        <div id="finder-tab" class="tab-content">
            
            <!-- Step 1: Choose Input Method -->
            <div id="step-input-choice" class="bg-white rounded-lg shadow-lg p-6 mb-6">
                <h2 class="text-2xl font-bold mb-4">
                    <span class="text-purple-600">Step 1:</span> How do you want to search?
                </h2>
                
                <div class="grid md:grid-cols-2 gap-6">
                    <!-- Upload Option -->
                    <div onclick="chooseUpload()" class="border-2 border-gray-300 rounded-lg p-8 text-center hover:border-purple-500 hover:bg-purple-50 cursor-pointer transition-all card-hover">
                        <i class="fas fa-file-upload text-5xl text-purple-600 mb-4"></i>
                        <h3 class="text-xl font-bold mb-2">Upload Company List</h3>
                        <p class="text-gray-600 mb-4">I have a CSV/Excel file with companies</p>
                        <ul class="text-sm text-gray-500 text-left">
                            <li>• Bulk process 100s of companies</li>
                            <li>• AI detects company types</li>
                            <li>• Automatic role suggestions</li>
                        </ul>
                    </div>
                    
                    <!-- Manual Entry Option -->
                    <div onclick="chooseManual()" class="border-2 border-gray-300 rounded-lg p-8 text-center hover:border-purple-500 hover:bg-purple-50 cursor-pointer transition-all card-hover">
                        <i class="fas fa-keyboard text-5xl text-purple-600 mb-4"></i>
                        <h3 class="text-xl font-bold mb-2">Manual Search</h3>
                        <p class="text-gray-600 mb-4">I want to describe what I'm looking for</p>
                        <ul class="text-sm text-gray-500 text-left">
                            <li>• Natural language search</li>
                            <li>• No file needed</li>
                            <li>• Quick targeted searches</li>
                        </ul>
                    </div>
                </div>
            </div>

            <!-- Step 1A: Upload -->
            <div id="step-upload" class="bg-white rounded-lg shadow-lg p-6 mb-6 hidden">
                <h2 class="text-2xl font-bold mb-4">
                    <span class="text-purple-600">Step 1A:</span> Upload Your Company List
                </h2>
                
                <div id="drop-zone" class="border-4 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-purple-500 transition-colors">
                    <i class="fas fa-cloud-upload-alt text-6xl text-gray-400 mb-4"></i>
                    <p class="text-xl text-gray-600 mb-2">Drag & drop your CSV file here</p>
                    <p class="text-gray-500 mb-4">or</p>
                    <input type="file" id="file-input" accept=".csv,.xlsx,.txt" class="hidden">
                    <button onclick="document.getElementById('file-input').click()" 
                            class="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700">
                        Choose File
                    </button>
                </div>
                
                <div id="file-info" class="hidden mt-4 p-4 bg-green-50 rounded-lg">
                    <p class="text-green-800"><i class="fas fa-check-circle mr-2"></i>
                        <span id="file-name"></span> uploaded successfully!
                    </p>
                    <p class="text-sm text-gray-600 mt-1">
                        <span id="company-count"></span> companies detected
                    </p>
                </div>
                
                <button onclick="chooseInputMethod()" class="mt-4 text-gray-500 hover:text-gray-700">
                    <i class="fas fa-arrow-left mr-2"></i>Back to options
                </button>
            </div>

            <!-- Step 1B: Manual Entry -->
            <div id="step-manual" class="bg-white rounded-lg shadow-lg p-6 mb-6 hidden">
                <h2 class="text-2xl font-bold mb-4">
                    <span class="text-purple-600">Step 1B:</span> Describe What You're Looking For
                </h2>
                
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            What are you looking for? (Be specific)
                        </label>
                        <textarea id="search-description" rows="3" 
                                  placeholder="Example: Find principals and operations managers at elementary schools in Sacramento California"
                                  class="w-full p-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none">
                        </textarea>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            Specific companies/organizations (optional)
                        </label>
                        <textarea id="company-list" rows="3" 
                                  placeholder="Enter company names separated by commas, or leave blank for general search"
                                  class="w-full p-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none">
                        </textarea>
                    </div>
                    
                    <div class="grid md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">
                                Industry/Type (optional)
                            </label>
                            <select id="industry-type" class="w-full p-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none">
                                <option value="">Auto-detect</option>
                                <option value="schools">K-12 Schools</option>
                                <option value="universities">Higher Education</option>
                                <option value="healthcare">Healthcare</option>
                                <option value="technology">Technology</option>
                                <option value="manufacturing">Manufacturing</option>
                                <option value="retail">Retail</option>
                                <option value="nonprofit">Nonprofit</option>
                                <option value="government">Government</option>
                                <option value="other">Other</option>
                            </select>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">
                                Location (optional)
                            </label>
                            <input type="text" id="location" 
                                   placeholder="e.g., California, New York City, etc."
                                   class="w-full p-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none">
                        </div>
                    </div>
                </div>
                
                <div class="mt-6 flex justify-between">
                    <button onclick="chooseInputMethod()" class="text-gray-500 hover:text-gray-700">
                        <i class="fas fa-arrow-left mr-2"></i>Back to options
                    </button>
                    <button onclick="processManualSearch()" class="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700">
                        Analyze & Continue <i class="fas fa-arrow-right ml-2"></i>
                    </button>
                </div>
            </div>

            <!-- Step 2: AI Role Selection -->
            <div id="step-roles" class="bg-white rounded-lg shadow-lg p-6 mb-6 hidden">
                <h2 class="text-2xl font-bold mb-4">
                    <span class="text-purple-600">Step 2:</span> Select Roles to Find
                </h2>
                
                <div class="bg-blue-50 p-4 rounded-lg mb-6">
                    <p class="text-blue-800">
                        <i class="fas fa-robot mr-2"></i>
                        <strong>AI Analysis:</strong> <span id="industry-type">Analyzing...</span>
                    </p>
                    <p class="text-sm text-gray-600 mt-1" id="ai-insight"></p>
                </div>

                <div class="grid md:grid-cols-2 gap-6">
                    <!-- Primary Roles -->
                    <div>
                        <h3 class="font-bold text-lg mb-3 text-green-600">
                            <i class="fas fa-star mr-2"></i>PRIMARY ROLES (Recommended)
                        </h3>
                        <div id="primary-roles" class="space-y-3">
                            <!-- Roles will be added here dynamically -->
                        </div>
                    </div>
                    
                    <!-- Secondary Roles -->
                    <div>
                        <h3 class="font-bold text-lg mb-3 text-yellow-600">
                            <i class="fas fa-plus-circle mr-2"></i>SECONDARY ROLES (Optional)
                        </h3>
                        <div id="secondary-roles" class="space-y-3">
                            <!-- Roles will be added here dynamically -->
                        </div>
                    </div>
                </div>

                <div class="mt-6">
                    <div class="mb-4 p-4 bg-gray-50 rounded-lg">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Add Custom Roles (comma-separated)</label>
                        <div class="flex gap-2">
                            <input type="text" id="custom-roles-input" 
                                   placeholder="e.g., Principal, Vice Principal, Operations Manager"
                                   class="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500">
                            <button onclick="addCustomRoles()" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
                                <i class="fas fa-plus mr-2"></i>Add
                            </button>
                        </div>
                    </div>
                    
                    <div class="flex justify-between">
                        <button onclick="selectAllPrimary()" class="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700">
                            <i class="fas fa-check-double mr-2"></i>Select All Primary
                        </button>
                        <button onclick="proceedToQueries()" class="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700">
                            Continue <i class="fas fa-arrow-right ml-2"></i>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Step 3: Query Preview -->
            <div id="step-queries" class="bg-white rounded-lg shadow-lg p-6 mb-6 hidden">
                <h2 class="text-2xl font-bold mb-4">
                    <span class="text-purple-600">Step 3:</span> Review & Edit Queries
                </h2>
                
                <div class="bg-gray-50 p-4 rounded-lg mb-4 flex justify-between items-center">
                    <p class="text-gray-700">
                        <i class="fas fa-info-circle mr-2"></i>
                        <span id="query-count"></span> queries will be generated
                    </p>
                    <div class="flex items-center gap-4">
                        <label class="text-sm text-gray-600">Show:</label>
                        <select id="queries-per-page" onchange="updateQueryPagination()" class="border rounded px-3 py-1">
                            <option value="10">10</option>
                            <option value="20">20</option>
                            <option value="50">50</option>
                            <option value="100">100</option>
                            <option value="all">All</option>
                        </select>
                        <div class="text-sm text-gray-600">
                            Page <span id="current-page">1</span> of <span id="total-pages">1</span>
                        </div>
                    </div>
                </div>

                <div class="mb-4 flex gap-4">
                    <button onclick="selectAllQueries()" class="bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300">
                        <i class="fas fa-check-square mr-2"></i>Select All
                    </button>
                    <button onclick="deselectAllQueries()" class="bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300">
                        <i class="fas fa-square mr-2"></i>Deselect All
                    </button>
                    <span class="ml-auto text-gray-600">
                        <span id="selected-queries-count">0</span> of <span id="total-queries-count">0</span> selected
                    </span>
                </div>
                
                <div class="overflow-x-auto">
                    <table class="min-w-full table-auto">
                        <thead class="bg-gray-100">
                            <tr>
                                <th class="px-4 py-2 text-center">
                                    <input type="checkbox" id="select-all-queries-checkbox" onchange="toggleAllQueries()">
                                </th>
                                <th class="px-4 py-2 text-left">#</th>
                                <th class="px-4 py-2 text-left">Company</th>
                                <th class="px-4 py-2 text-left">Role</th>
                                <th class="px-4 py-2 text-left">Query</th>
                                <th class="px-4 py-2 text-left">Action</th>
                            </tr>
                        </thead>
                        <tbody id="query-list" class="divide-y">
                            <!-- Queries will be listed here -->
                        </tbody>
                    </table>
                </div>

                <div class="mt-4 flex justify-center gap-2">
                    <button onclick="previousQueryPage()" id="prev-page-btn" class="bg-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-400 disabled:opacity-50" disabled>
                        <i class="fas fa-chevron-left"></i> Previous
                    </button>
                    <button onclick="nextQueryPage()" id="next-page-btn" class="bg-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-400 disabled:opacity-50">
                        Next <i class="fas fa-chevron-right"></i>
                    </button>
                </div>

                <div class="mt-6 flex justify-between">
                    <button onclick="goBackToRoles()" class="bg-gray-500 text-white px-6 py-2 rounded-lg hover:bg-gray-600">
                        <i class="fas fa-arrow-left mr-2"></i>Back
                    </button>
                    <button onclick="startEnrichment()" class="bg-green-600 text-white px-8 py-3 rounded-lg hover:bg-green-700 text-lg">
                        <i class="fas fa-rocket mr-2"></i>Start Enrichment
                    </button>
                </div>
            </div>

            <!-- Step 4: Progress -->
            <div id="step-progress" class="bg-white rounded-lg shadow-lg p-6 mb-6 hidden">
                <h2 class="text-2xl font-bold mb-4">
                    <span class="text-purple-600">Step 4:</span> Enrichment in Progress
                </h2>
                
                <div class="mb-6">
                    <div class="flex justify-between mb-2">
                        <span class="text-gray-700">Progress</span>
                        <span class="text-gray-700"><span id="progress-current">0</span> / <span id="progress-total">0</span></span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-4">
                        <div id="progress-bar" class="progress-bar bg-purple-600 h-4 rounded-full" style="width: 0%"></div>
                    </div>
                </div>

                <div class="mb-4 flex gap-4">
                    <button id="pause-btn" onclick="togglePause()" class="bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600">
                        <i class="fas fa-pause mr-2"></i>Pause
                    </button>
                    <button onclick="cancelSearch()" class="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600">
                        <i class="fas fa-stop mr-2"></i>Cancel
                    </button>
                    <button onclick="showLiveResults()" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                        <i class="fas fa-eye mr-2"></i>View Results So Far
                    </button>
                </div>

                <div class="bg-gray-50 p-4 rounded-lg">
                    <p class="text-gray-700">
                        <i class="fas fa-spinner fa-spin mr-2" id="spinner-icon"></i>
                        <span id="current-search">Initializing...</span>
                    </p>
                </div>

                <div class="mt-4 grid grid-cols-3 gap-4 text-center">
                    <div class="bg-green-50 p-4 rounded-lg">
                        <p class="text-2xl font-bold text-green-600" id="contacts-found">0</p>
                        <p class="text-sm text-gray-600">Contacts Found</p>
                    </div>
                    <div class="bg-blue-50 p-4 rounded-lg">
                        <p class="text-2xl font-bold text-blue-600" id="emails-found">0</p>
                        <p class="text-sm text-gray-600">Emails Found</p>
                    </div>
                    <div class="bg-yellow-50 p-4 rounded-lg">
                        <p class="text-2xl font-bold text-yellow-600" id="phones-found">0</p>
                        <p class="text-sm text-gray-600">Phones Found</p>
                    </div>
                </div>
                
                <!-- Live Results Preview -->
                <div id="live-results-preview" class="mt-6 hidden">
                    <h3 class="font-bold mb-2">Latest Results:</h3>
                    <div class="max-h-64 overflow-y-auto border rounded p-2">
                        <div id="live-results-list" class="space-y-2">
                            <!-- Live results appear here -->
                        </div>
                    </div>
                </div>
            </div>

            <!-- Step 5: Results -->
            <div id="step-results" class="bg-white rounded-lg shadow-lg p-6 mb-6 hidden">
                <h2 class="text-2xl font-bold mb-4">
                    <span class="text-purple-600">Step 5:</span> Results
                </h2>
                
                <div class="mb-4 flex justify-between">
                    <div>
                        <p class="text-gray-700">
                            <i class="fas fa-check-circle text-green-500 mr-2"></i>
                            Found <span id="total-results">0</span> contacts
                        </p>
                        <p class="text-sm text-gray-600 mt-1">
                            <span id="selected-count">0</span> selected for task tracker
                        </p>
                    </div>
                    <div class="space-x-2">
                        <button onclick="exportResults('csv')" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                            <i class="fas fa-file-csv mr-2"></i>Export CSV
                        </button>
                        <button onclick="exportResults('excel')" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                            <i class="fas fa-file-excel mr-2"></i>Export Excel
                        </button>
                        <button onclick="sendToTaskTracker()" class="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700">
                            <i class="fas fa-tasks mr-2"></i>Send to Tasks
                        </button>
                    </div>
                </div>

                <div class="mb-4 flex gap-4">
                    <button onclick="selectAllResults()" class="bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300">
                        <i class="fas fa-check-square mr-2"></i>Select All
                    </button>
                    <button onclick="deselectAllResults()" class="bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300">
                        <i class="fas fa-square mr-2"></i>Deselect All
                    </button>
                </div>
                
                <div class="overflow-x-auto">
                    <table class="min-w-full table-auto">
                        <thead class="bg-gray-100">
                            <tr>
                                <th class="px-4 py-2 text-center">
                                    <input type="checkbox" id="select-all-checkbox" onchange="toggleAllResults()">
                                </th>
                                <th class="px-4 py-2 text-left">Name</th>
                                <th class="px-4 py-2 text-left">Company</th>
                                <th class="px-4 py-2 text-left">Email</th>
                                <th class="px-4 py-2 text-left">Phone</th>
                                <th class="px-4 py-2 text-left">Confidence</th>
                                <th class="px-4 py-2 text-left">Sources</th>
                            </tr>
                        </thead>
                        <tbody id="results-list" class="divide-y">
                            <!-- Results will be listed here -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Task Tracker Tab -->
        <div id="tasks-tab" class="tab-content hidden">
            <div class="bg-white rounded-lg shadow-lg p-6">
                <h2 class="text-2xl font-bold mb-4">Task Tracker</h2>
                
                <div class="grid grid-cols-4 gap-4 mb-6">
                    <div class="bg-blue-50 p-4 rounded-lg text-center">
                        <p class="text-3xl font-bold text-blue-600" id="pending-tasks">0</p>
                        <p class="text-gray-600">Pending</p>
                    </div>
                    <div class="bg-yellow-50 p-4 rounded-lg text-center">
                        <p class="text-3xl font-bold text-yellow-600" id="in-progress-tasks">0</p>
                        <p class="text-gray-600">In Progress</p>
                    </div>
                    <div class="bg-green-50 p-4 rounded-lg text-center">
                        <p class="text-3xl font-bold text-green-600" id="completed-tasks">0</p>
                        <p class="text-gray-600">Completed</p>
                    </div>
                    <div class="bg-purple-50 p-4 rounded-lg text-center">
                        <p class="text-3xl font-bold text-purple-600" id="total-contacts">0</p>
                        <p class="text-gray-600">Total Contacts</p>
                    </div>
                </div>
                
                <div class="mb-4 flex gap-4">
                    <select id="task-filter" onchange="filterTasks()" class="px-4 py-2 border rounded">
                        <option value="all">All Tasks</option>
                        <option value="pending">Pending</option>
                        <option value="in_progress">In Progress</option>
                        <option value="completed">Completed</option>
                    </select>
                    <select id="task-sort" onchange="sortTasks()" class="px-4 py-2 border rounded">
                        <option value="date">Sort by Date</option>
                        <option value="company">Sort by Company</option>
                        <option value="status">Sort by Status</option>
                    </select>
                </div>

                <div class="overflow-x-auto">
                    <table class="min-w-full table-auto">
                        <thead class="bg-gray-100">
                            <tr>
                                <th class="px-4 py-2 text-left">Company</th>
                                <th class="px-4 py-2 text-left">Name</th>
                                <th class="px-4 py-2 text-left">Email</th>
                                <th class="px-4 py-2 text-left">Phone</th>
                                <th class="px-4 py-2 text-center">Called</th>
                                <th class="px-4 py-2 text-center">Emailed</th>
                                <th class="px-4 py-2 text-left">Status</th>
                                <th class="px-4 py-2 text-left">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="task-list" class="divide-y">
                            <!-- Tasks will be listed here -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Saved Contacts Tab -->
        <div id="saved-tab" class="tab-content hidden">
            <div class="bg-white rounded-lg shadow-lg p-6">
                <h2 class="text-2xl font-bold mb-4">Saved Contacts Database</h2>
                
                <div class="mb-4 flex gap-4">
                    <input type="text" id="saved-search" placeholder="Search by name, company, or email..." 
                           class="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                           onkeyup="searchSavedContacts()">
                    <button onclick="searchSavedContacts()" class="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700">
                        <i class="fas fa-search mr-2"></i>Search
                    </button>
                    <button onclick="exportSavedContacts()" class="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700">
                        <i class="fas fa-download mr-2"></i>Export All
                    </button>
                </div>
                
                <div class="overflow-x-auto">
                    <table class="min-w-full table-auto">
                        <thead class="bg-gray-100">
                            <tr>
                                <th class="px-4 py-2 text-left">Name</th>
                                <th class="px-4 py-2 text-left">Company</th>
                                <th class="px-4 py-2 text-left">Email</th>
                                <th class="px-4 py-2 text-left">Phone</th>
                                <th class="px-4 py-2 text-left">Confidence</th>
                                <th class="px-4 py-2 text-left">Date Found</th>
                                <th class="px-4 py-2 text-left">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="saved-contacts-list" class="divide-y">
                            <!-- Saved contacts will be listed here -->
                        </tbody>
                    </table>
                </div>
                
                <div class="mt-4 text-gray-600">
                    <p><i class="fas fa-info-circle mr-2"></i>All contacts found are automatically saved here to avoid duplicate searches.</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Settings Modal -->
    <div id="settings-modal" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden overflow-y-auto h-full w-full z-50">
        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div class="mt-3">
                <h3 class="text-lg font-bold text-gray-900 mb-4">
                    <i class="fas fa-key mr-2"></i>API Configuration
                </h3>
                
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">
                            Perplexity API Key <span class="text-red-500">*</span>
                        </label>
                        <input type="password" id="perplexity-key" 
                               class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                               placeholder="pplx-...">
                        <p class="text-xs text-gray-500 mt-1">
                            Get your key at <a href="https://www.perplexity.ai/settings/api" target="_blank" class="text-blue-500 hover:underline">perplexity.ai/settings/api</a>
                        </p>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">
                            Anthropic API Key (Optional)
                        </label>
                        <input type="password" id="anthropic-key" 
                               class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                               placeholder="sk-ant-...">
                        <p class="text-xs text-gray-500 mt-1">For AI-powered role suggestions</p>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">
                            Rate Limit Delay (seconds)
                        </label>
                        <input type="number" id="rate-limit" value="2" min="1" max="10"
                               class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500">
                        <p class="text-xs text-gray-500 mt-1">Delay between API calls to prevent rate limiting</p>
                    </div>
                </div>
                
                <div class="mt-6 flex justify-end space-x-3">
                    <button onclick="closeSettings()" 
                            class="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400">
                        Cancel
                    </button>
                    <button onclick="saveSettings()" 
                            class="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700">
                        Save Settings
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let uploadedFile = null;
        let companies = [];
        let selectedRoles = [];
        let queries = [];
        let jobId = null;
        let searchMode = 'upload'; // 'upload' or 'manual'
        
        // Check API configuration on page load
        window.addEventListener('DOMContentLoaded', async () => {
            const response = await fetch('/api/config/status');
            const status = await response.json();
            
            if (!status.configured) {
                showSettings();
                alert('Please configure your API keys to get started');
            }
        });
        
        // Settings management
        function showSettings() {
            document.getElementById('settings-modal').classList.remove('hidden');
            
            // Load current settings if available
            fetch('/api/config/current')
                .then(res => res.json())
                .then(config => {
                    if (config.perplexity_key) {
                        document.getElementById('perplexity-key').value = config.perplexity_key.substring(0, 10) + '...';
                    }
                    if (config.anthropic_key) {
                        document.getElementById('anthropic-key').value = config.anthropic_key.substring(0, 10) + '...';
                    }
                    if (config.rate_limit_delay) {
                        document.getElementById('rate-limit').value = config.rate_limit_delay;
                    }
                })
                .catch(() => {
                    // No existing config, that's ok
                });
        }
        
        function closeSettings() {
            document.getElementById('settings-modal').classList.add('hidden');
        }
        
        async function saveSettings() {
            const perplexityKey = document.getElementById('perplexity-key').value;
            const anthropicKey = document.getElementById('anthropic-key').value;
            const rateLimit = document.getElementById('rate-limit').value;
            
            if (!perplexityKey || perplexityKey.endsWith('...')) {
                alert('Please enter a valid Perplexity API key');
                return;
            }
            
            const response = await fetch('/api/config/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    perplexity_key: perplexityKey,
                    anthropic_key: anthropicKey && !anthropicKey.endsWith('...') ? anthropicKey : '',
                    rate_limit_delay: parseInt(rateLimit)
                })
            });
            
            if (response.ok) {
                alert('Settings saved successfully!');
                closeSettings();
                location.reload(); // Reload to use new settings
            } else {
                alert('Error saving settings');
            }
        }

        // Tab switching
        function showTab(tab) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.getElementById(tab + '-tab').classList.remove('hidden');
            
            if (tab === 'tasks') {
                loadTasks();
            } else if (tab === 'saved') {
                searchSavedContacts();
            }
        }
        
        async function searchSavedContacts() {
            const query = document.getElementById('saved-search').value;
            const response = await fetch(`/api/contacts/search?q=${encodeURIComponent(query)}`);
            const contacts = await response.json();
            
            const list = document.getElementById('saved-contacts-list');
            list.innerHTML = '';
            
            if (contacts.length === 0) {
                list.innerHTML = '<tr><td colspan="7" class="px-4 py-8 text-center text-gray-500">No contacts found</td></tr>';
                return;
            }
            
            contacts.forEach(contact => {
                const date = new Date(contact.date_found).toLocaleDateString();
                list.innerHTML += `
                    <tr class="hover:bg-gray-50">
                        <td class="px-4 py-2">${contact.name || '-'}</td>
                        <td class="px-4 py-2">${contact.company || '-'}</td>
                        <td class="px-4 py-2">
                            ${contact.email || '-'}
                            ${contact.alternate_emails && contact.alternate_emails.length > 0 ? 
                                `<span class="text-xs text-gray-500 block">+${contact.alternate_emails.length} more</span>` : ''}
                        </td>
                        <td class="px-4 py-2">
                            ${contact.phone || '-'}
                            ${contact.alternate_phones && contact.alternate_phones.length > 0 ? 
                                `<span class="text-xs text-gray-500 block">+${contact.alternate_phones.length} more</span>` : ''}
                        </td>
                        <td class="px-4 py-2">
                            <span class="px-2 py-1 rounded text-sm ${
                                contact.confidence > 0.8 ? 'bg-green-100 text-green-800' :
                                contact.confidence > 0.5 ? 'bg-yellow-100 text-yellow-800' :
                                'bg-red-100 text-red-800'
                            }">
                                ${(contact.confidence * 100).toFixed(0)}%
                            </span>
                        </td>
                        <td class="px-4 py-2">${date}</td>
                        <td class="px-4 py-2">
                            <button onclick="addToTaskTracker('${contact.id || ''}')" class="text-purple-600 hover:text-purple-800">
                                <i class="fas fa-plus-circle"></i> Add to Tasks
                            </button>
                        </td>
                    </tr>
                `;
            });
        }
        
        async function exportSavedContacts() {
            // Get all saved contacts and export as CSV
            const response = await fetch('/api/contacts/search');
            const contacts = await response.json();
            
            if (contacts.length === 0) {
                alert('No contacts to export');
                return;
            }
            
            // Create CSV
            let csv = 'Name,Company,Email,Phone,Confidence,Date Found\\n';
            contacts.forEach(c => {
                csv += `"${c.name}","${c.company}","${c.email}","${c.phone}","${c.confidence}","${c.date_found}"\\n`;
            });
            
            // Download
            const blob = new Blob([csv], {type: 'text/csv'});
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `saved_contacts_${new Date().toISOString().split('T')[0]}.csv`;
            a.click();
        }
        
        async function addToTaskTracker(contactId) {
            // Add a saved contact to task tracker
            alert('Adding contact to task tracker...');
            // Implementation would go here
        }

        // Input method selection
        function chooseInputMethod() {
            document.getElementById('step-upload').classList.add('hidden');
            document.getElementById('step-manual').classList.add('hidden');
            document.getElementById('step-input-choice').classList.remove('hidden');
        }

        function chooseUpload() {
            searchMode = 'upload';
            document.getElementById('step-input-choice').classList.add('hidden');
            document.getElementById('step-upload').classList.remove('hidden');
        }

        function chooseManual() {
            searchMode = 'manual';
            document.getElementById('step-input-choice').classList.add('hidden');
            document.getElementById('step-manual').classList.remove('hidden');
        }

        async function processManualSearch() {
            const description = document.getElementById('search-description').value;
            const companyList = document.getElementById('company-list').value;
            const industryType = document.getElementById('industry-type').value;
            const location = document.getElementById('location').value;
            
            if (!description.trim()) {
                alert('Please describe what you are looking for');
                return;
            }
            
            // Parse companies if provided
            if (companyList.trim()) {
                companies = companyList.split(',').map(c => c.trim()).filter(c => c);
            } else {
                companies = []; // Will do general search
            }
            
            // Send to AI for analysis
            try {
                const response = await fetch('/api/analyze-manual-search', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        description: description,
                        companies: companies,
                        industry: industryType,
                        location: location
                    })
                });
                
                const data = await response.json();
                
                // Process AI suggestions (similar to upload flow)
                document.getElementById('industry-type').textContent = data.industry_type || 'General Search';
                document.getElementById('ai-insight').textContent = data.insights || '';
                
                // Display roles
                const primaryContainer = document.getElementById('primary-roles');
                primaryContainer.innerHTML = '';
                if (data.primary_roles) {
                    data.primary_roles.forEach(role => {
                        primaryContainer.innerHTML += createRoleCard(role, 'primary');
                    });
                }
                
                const secondaryContainer = document.getElementById('secondary-roles');
                secondaryContainer.innerHTML = '';
                if (data.secondary_roles) {
                    data.secondary_roles.forEach(role => {
                        secondaryContainer.innerHTML += createRoleCard(role, 'secondary');
                    });
                }
                
                // Show roles step
                document.getElementById('step-manual').classList.add('hidden');
                document.getElementById('step-roles').classList.remove('hidden');
                
            } catch (error) {
                console.error('Error analyzing search:', error);
                alert('Error analyzing your search request');
            }
        }

        // File upload handling
        document.getElementById('file-input').addEventListener('change', handleFileUpload);
        
        // Drag and drop
        const dropZone = document.getElementById('drop-zone');
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('border-purple-500');
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('border-purple-500');
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-purple-500');
            const file = e.dataTransfer.files[0];
            if (file) {
                handleFileUpload({target: {files: [file]}});
            }
        });

        async function handleFileUpload(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            uploadedFile = file;
            
            // Show file info
            document.getElementById('file-name').textContent = file.name;
            document.getElementById('file-info').classList.remove('hidden');
            
            // Upload file
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                companies = data.companies;
                
                document.getElementById('company-count').textContent = companies.length;
                
                // Get AI suggestions
                await getAISuggestions();
                
                // Show roles step
                document.getElementById('step-roles').classList.remove('hidden');
                
            } catch (error) {
                console.error('Upload error:', error);
                alert('Error uploading file');
            }
        }

        async function getAISuggestions() {
            try {
                const response = await fetch('/api/suggest-roles', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({companies: companies.slice(0, 10)})
                });
                
                const data = await response.json();
                
                // Update UI with suggestions
                document.getElementById('industry-type').textContent = data.industry_type;
                document.getElementById('ai-insight').textContent = data.insights;
                
                // Display primary roles
                const primaryContainer = document.getElementById('primary-roles');
                primaryContainer.innerHTML = '';
                data.primary_roles.forEach(role => {
                    primaryContainer.innerHTML += createRoleCard(role, 'primary');
                });
                
                // Display secondary roles
                const secondaryContainer = document.getElementById('secondary-roles');
                secondaryContainer.innerHTML = '';
                data.secondary_roles.forEach(role => {
                    secondaryContainer.innerHTML += createRoleCard(role, 'secondary');
                });
                
            } catch (error) {
                console.error('Error getting suggestions:', error);
            }
        }

        function createRoleCard(roleInfo, type) {
            const bgColor = type === 'primary' ? 'bg-green-50' : 'bg-yellow-50';
            const borderColor = type === 'primary' ? 'border-green-300' : 'border-yellow-300';
            
            return `
                <div class="role-card p-4 rounded-lg border-2 ${borderColor} ${bgColor} cursor-pointer card-hover"
                     onclick="toggleRole(this, '${roleInfo.role}')">
                    <div class="flex items-start">
                        <input type="checkbox" class="mt-1 mr-3" value="${roleInfo.role}">
                        <div class="flex-1">
                            <p class="font-semibold">${roleInfo.role}</p>
                            <p class="text-sm text-gray-600 mt-1">${roleInfo.reason}</p>
                        </div>
                    </div>
                </div>
            `;
        }

        function toggleRole(card, role) {
            const checkbox = card.querySelector('input[type="checkbox"]');
            checkbox.checked = !checkbox.checked;
            card.classList.toggle('selected');
            
            if (checkbox.checked) {
                if (!selectedRoles.includes(role)) {
                    selectedRoles.push(role);
                }
            } else {
                selectedRoles = selectedRoles.filter(r => r !== role);
            }
        }

        function selectAllPrimary() {
            document.querySelectorAll('#primary-roles .role-card').forEach(card => {
                const checkbox = card.querySelector('input[type="checkbox"]');
                checkbox.checked = true;
                card.classList.add('selected');
                const role = checkbox.value;
                if (!selectedRoles.includes(role)) {
                    selectedRoles.push(role);
                }
            });
        }
        
        function addCustomRoles() {
            const input = document.getElementById('custom-roles-input');
            const roles = input.value.split(',').map(r => r.trim()).filter(r => r);
            
            if (roles.length === 0) {
                alert('Please enter at least one role');
                return;
            }
            
            const container = document.getElementById('primary-roles');
            roles.forEach(role => {
                if (!selectedRoles.includes(role)) {
                    selectedRoles.push(role);
                    // Add visual card for the custom role
                    const roleCard = createRoleCard({
                        role: role,
                        reason: 'Custom role added by user'
                    }, 'primary');
                    container.insertAdjacentHTML('beforeend', roleCard);
                    // Auto-select it
                    const newCard = container.lastElementChild;
                    const checkbox = newCard.querySelector('input[type="checkbox"]');
                    checkbox.checked = true;
                    newCard.classList.add('selected');
                }
            });
            
            input.value = '';
            alert(`Added ${roles.length} custom role(s)`);
        }

        let currentQueryPage = 1;
        let queriesPerPage = 10;
        let selectedQueries = new Set();
        let isPaused = false;
        let isCancelled = false;
        
        async function proceedToQueries() {
            if (selectedRoles.length === 0) {
                alert('Please select at least one role');
                return;
            }
            
            // Generate queries
            const response = await fetch('/api/generate-queries', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    companies: companies,
                    roles: selectedRoles
                })
            });
            
            queries = await response.json();
            
            // Display queries
            document.getElementById('query-count').textContent = queries.queries.length;
            
            // Initialize pagination
            currentQueryPage = 1;
            displayQueries();
            
            // Show queries step
            document.getElementById('step-queries').classList.remove('hidden');
        }
        
        function displayQueries() {
            const queryList = document.getElementById('query-list');
            queryList.innerHTML = '';
            
            const perPageValue = document.getElementById('queries-per-page').value;
            queriesPerPage = perPageValue === 'all' ? queries.queries.length : parseInt(perPageValue);
            
            const startIdx = (currentQueryPage - 1) * queriesPerPage;
            const endIdx = Math.min(startIdx + queriesPerPage, queries.queries.length);
            const totalPages = Math.ceil(queries.queries.length / queriesPerPage);
            
            // Update pagination info
            document.getElementById('current-page').textContent = currentQueryPage;
            document.getElementById('total-pages').textContent = totalPages;
            
            // Enable/disable pagination buttons
            document.getElementById('prev-page-btn').disabled = currentQueryPage === 1;
            document.getElementById('next-page-btn').disabled = currentQueryPage === totalPages;
            
            // Display queries for current page
            for (let i = startIdx; i < endIdx; i++) {
                const q = queries.queries[i];
                const isChecked = selectedQueries.has(i) ? 'checked' : '';
                queryList.innerHTML += `
                    <tr class="hover:bg-gray-50">
                        <td class="px-4 py-2 text-center">
                            <input type="checkbox" 
                                   id="query-check-${i}" 
                                   ${isChecked}
                                   onchange="toggleQuerySelection(${i})"
                                   class="query-checkbox">
                        </td>
                        <td class="px-4 py-2">${i + 1}</td>
                        <td class="px-4 py-2">${q.company}</td>
                        <td class="px-4 py-2">${q.role}</td>
                        <td class="px-4 py-2">
                            <input type="text" value="${q.query}" 
                                   class="w-full p-1 border rounded" 
                                   id="query-${i}"
                                   onchange="updateQuery(${i}, this.value)">
                        </td>
                        <td class="px-4 py-2">
                            <button onclick="removeQuery(${i})" class="text-red-500 hover:text-red-700">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `;
            }
            
            // Update counts
            document.getElementById('total-queries-count').textContent = queries.queries.length;
            updateSelectedQueriesCount();
        }
        
        function updateQueryPagination() {
            currentQueryPage = 1;
            displayQueries();
        }
        
        function previousQueryPage() {
            if (currentQueryPage > 1) {
                currentQueryPage--;
                displayQueries();
            }
        }
        
        function nextQueryPage() {
            const totalPages = Math.ceil(queries.queries.length / queriesPerPage);
            if (currentQueryPage < totalPages) {
                currentQueryPage++;
                displayQueries();
            }
        }
        
        function updateQuery(index, value) {
            queries.queries[index].query = value;
        }
        
        function removeQuery(index) {
            queries.queries.splice(index, 1);
            selectedQueries.delete(index);
            displayQueries();
        }
        
        function toggleQuerySelection(index) {
            if (selectedQueries.has(index)) {
                selectedQueries.delete(index);
            } else {
                selectedQueries.add(index);
            }
            updateSelectedQueriesCount();
        }
        
        function selectAllQueries() {
            queries.queries.forEach((_, index) => {
                selectedQueries.add(index);
                const checkbox = document.getElementById(`query-check-${index}`);
                if (checkbox) checkbox.checked = true;
            });
            document.getElementById('select-all-queries-checkbox').checked = true;
            updateSelectedQueriesCount();
        }
        
        function deselectAllQueries() {
            selectedQueries.clear();
            document.querySelectorAll('.query-checkbox').forEach(cb => cb.checked = false);
            document.getElementById('select-all-queries-checkbox').checked = false;
            updateSelectedQueriesCount();
        }
        
        function toggleAllQueries() {
            const selectAll = document.getElementById('select-all-queries-checkbox').checked;
            if (selectAll) {
                selectAllQueries();
            } else {
                deselectAllQueries();
            }
        }
        
        function updateSelectedQueriesCount() {
            document.getElementById('selected-queries-count').textContent = selectedQueries.size;
        }

        async function startEnrichment() {
            if (selectedQueries.size === 0) {
                alert('Please select at least one query to run');
                return;
            }
            
            // Get only selected queries
            const selectedQueriesList = [];
            selectedQueries.forEach(index => {
                if (queries.queries[index]) {
                    selectedQueriesList.push(queries.queries[index]);
                }
            });
            
            // Reset flags
            isPaused = false;
            isCancelled = false;
            // Hide queries, show progress
            document.getElementById('step-queries').classList.add('hidden');
            document.getElementById('step-progress').classList.remove('hidden');
            
            // Start enrichment with selected queries only
            const response = await fetch('/api/start-enrichment', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({queries: selectedQueriesList})
            });
            
            const data = await response.json();
            jobId = data.job_id;
            
            // Update progress UI
            document.getElementById('progress-total').textContent = selectedQueriesList.length;
            
            // Poll for progress
            pollProgress();
        }
        
        function togglePause() {
            isPaused = !isPaused;
            const btn = document.getElementById('pause-btn');
            const spinner = document.getElementById('spinner-icon');
            
            if (isPaused) {
                fetch(`/api/job/${jobId}/pause`, {method: 'POST'});
                btn.innerHTML = '<i class="fas fa-play mr-2"></i>Resume';
                btn.classList.remove('bg-yellow-500', 'hover:bg-yellow-600');
                btn.classList.add('bg-green-500', 'hover:bg-green-600');
                spinner.classList.remove('fa-spin');
            } else {
                fetch(`/api/job/${jobId}/resume`, {method: 'POST'});
                btn.innerHTML = '<i class="fas fa-pause mr-2"></i>Pause';
                btn.classList.remove('bg-green-500', 'hover:bg-green-600');
                btn.classList.add('bg-yellow-500', 'hover:bg-yellow-600');
                spinner.classList.add('fa-spin');
            }
        }
        
        async function cancelSearch() {
            if (confirm('Are you sure you want to cancel the search? You will keep results found so far.')) {
                isCancelled = true;
                await fetch(`/api/job/${jobId}/cancel`, {method: 'POST'});
                
                // Get current results and show them
                const response = await fetch(`/api/job-status/${jobId}`);
                const data = await response.json();
                if (data.results && data.results.length > 0) {
                    showResults(data.results);
                } else {
                    alert('Search cancelled. No results were found yet.');
                    document.getElementById('step-progress').classList.add('hidden');
                    document.getElementById('step-queries').classList.remove('hidden');
                }
            }
        }
        
        function showLiveResults() {
            const preview = document.getElementById('live-results-preview');
            preview.classList.toggle('hidden');
        }

        async function pollProgress() {
            if (isCancelled) return;
            
            const response = await fetch(`/api/job-status/${jobId}`);
            const data = await response.json();
            
            // Update progress bar
            const progress = (data.completed / data.total) * 100;
            document.getElementById('progress-bar').style.width = progress + '%';
            document.getElementById('progress-current').textContent = data.completed;
            
            // Update stats
            document.getElementById('contacts-found').textContent = data.contacts_found;
            document.getElementById('emails-found').textContent = data.emails_found;
            document.getElementById('phones-found').textContent = data.phones_found;
            document.getElementById('current-search').textContent = data.current_search || 'Processing...';
            
            // Update live results preview
            if (data.results && data.results.length > 0) {
                const liveList = document.getElementById('live-results-list');
                liveList.innerHTML = '';
                
                // Show last 5 results
                const recentResults = data.results.slice(-5);
                recentResults.forEach(contact => {
                    liveList.innerHTML += `
                        <div class="bg-gray-50 p-2 rounded">
                            <p class="font-semibold">${contact.name || 'Unknown'} - ${contact.company}</p>
                            <p class="text-sm text-gray-600">
                                ${contact.email ? '✉️ ' + contact.email : ''} 
                                ${contact.phone ? '📞 ' + contact.phone : ''}
                            </p>
                        </div>
                    `;
                });
            }
            
            if (data.status === 'completed' || data.status === 'cancelled') {
                // Show results
                showResults(data.results);
                // Save to database
                saveResultsToDatabase(data.results);
            } else if (data.status === 'paused') {
                // Just wait, don't poll
                setTimeout(pollProgress, 2000);
            } else {
                // Continue polling
                setTimeout(pollProgress, 1000);
            }
        }
        
        async function saveResultsToDatabase(results) {
            // Automatically save all found contacts to database
            await fetch('/api/contacts/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({contacts: results})
            });
        }

        let selectedResults = new Set();
        
        function showResults(results) {
            document.getElementById('step-progress').classList.add('hidden');
            document.getElementById('step-results').classList.remove('hidden');
            
            document.getElementById('total-results').textContent = results.length;
            
            const resultsList = document.getElementById('results-list');
            resultsList.innerHTML = '';
            
            results.forEach((contact, index) => {
                // Format sources
                let sourcesHtml = '';
                if (contact.sources && contact.sources.length > 0) {
                    sourcesHtml = contact.sources.slice(0, 2).map(s => 
                        `<a href="${s.url}" target="_blank" class="text-blue-500 hover:underline text-xs">${s.title || 'Source'}</a>`
                    ).join(', ');
                    if (contact.sources.length > 2) {
                        sourcesHtml += ` <span class="text-xs text-gray-500">+${contact.sources.length - 2} more</span>`;
                    }
                }
                
                resultsList.innerHTML += `
                    <tr class="hover:bg-gray-50">
                        <td class="px-4 py-2 text-center">
                            <input type="checkbox" 
                                   id="result-${index}" 
                                   value="${index}"
                                   onchange="toggleResultSelection(${index})"
                                   class="result-checkbox">
                        </td>
                        <td class="px-4 py-2">${contact.name || '-'}</td>
                        <td class="px-4 py-2">${contact.company || '-'}</td>
                        <td class="px-4 py-2">
                            ${contact.email || '-'}
                            ${contact.alternate_emails && contact.alternate_emails.length > 0 ? 
                                `<span class="text-xs text-gray-500 block">+${contact.alternate_emails.length} more</span>` : ''}
                        </td>
                        <td class="px-4 py-2">
                            ${contact.phone || '-'}
                            ${contact.alternate_phones && contact.alternate_phones.length > 0 ? 
                                `<span class="text-xs text-gray-500 block">+${contact.alternate_phones.length} more</span>` : ''}
                        </td>
                        <td class="px-4 py-2">
                            <span class="px-2 py-1 rounded text-sm ${
                                contact.confidence > 0.8 ? 'bg-green-100 text-green-800' :
                                contact.confidence > 0.5 ? 'bg-yellow-100 text-yellow-800' :
                                'bg-red-100 text-red-800'
                            }">
                                ${(contact.confidence * 100).toFixed(0)}%
                            </span>
                        </td>
                        <td class="px-4 py-2">
                            ${sourcesHtml || '<span class="text-gray-400 text-xs">No sources</span>'}
                        </td>
                    </tr>
                `;
            });
            
            // Store results globally for export/task functions
            window.currentResults = results;
            updateSelectedCount();
        }
        
        function toggleResultSelection(index) {
            if (selectedResults.has(index)) {
                selectedResults.delete(index);
            } else {
                selectedResults.add(index);
            }
            updateSelectedCount();
        }
        
        function selectAllResults() {
            window.currentResults.forEach((_, index) => {
                selectedResults.add(index);
                document.getElementById(`result-${index}`).checked = true;
            });
            document.getElementById('select-all-checkbox').checked = true;
            updateSelectedCount();
        }
        
        function deselectAllResults() {
            selectedResults.clear();
            document.querySelectorAll('.result-checkbox').forEach(cb => cb.checked = false);
            document.getElementById('select-all-checkbox').checked = false;
            updateSelectedCount();
        }
        
        function toggleAllResults() {
            const selectAll = document.getElementById('select-all-checkbox').checked;
            if (selectAll) {
                selectAllResults();
            } else {
                deselectAllResults();
            }
        }
        
        function updateSelectedCount() {
            document.getElementById('selected-count').textContent = selectedResults.size;
        }

        async function exportResults(format) {
            window.location.href = `/api/export/${jobId}?format=${format}`;
        }

        async function sendToTaskTracker() {
            if (selectedResults.size === 0) {
                alert('Please select at least one contact to send to Task Tracker');
                return;
            }
            
            // Get selected contacts
            const selectedContacts = [];
            selectedResults.forEach(index => {
                selectedContacts.push(window.currentResults[index]);
            });
            
            const confirmMsg = `Send ${selectedContacts.length} selected contact${selectedContacts.length > 1 ? 's' : ''} to Task Tracker?`;
            if (!confirm(confirmMsg)) {
                return;
            }
            
            const response = await fetch('/api/import-to-tasks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    job_id: jobId,
                    selected_contacts: selectedContacts
                })
            });
            
            if (response.ok) {
                alert(`${selectedContacts.length} contacts imported to Task Tracker!`);
                showTab('tasks');
            }
        }

        let allTasks = [];
        let currentFilter = 'all';
        let currentSort = 'date';
        
        async function loadTasks() {
            const response = await fetch('/api/tasks/all');
            const data = await response.json();
            allTasks = data.tasks || [];
            
            // Update stats
            const pending = allTasks.filter(t => t.status === 'pending').length;
            const inProgress = allTasks.filter(t => t.status === 'in_progress').length;
            const completed = allTasks.filter(t => t.status === 'completed').length;
            
            document.getElementById('pending-tasks').textContent = pending;
            document.getElementById('in-progress-tasks').textContent = inProgress;
            document.getElementById('completed-tasks').textContent = completed;
            document.getElementById('total-contacts').textContent = allTasks.length;
            
            displayTasks();
        }
        
        function displayTasks() {
            let tasks = [...allTasks];
            
            // Apply filter
            if (currentFilter !== 'all') {
                tasks = tasks.filter(t => t.status === currentFilter);
            }
            
            // Apply sort
            tasks.sort((a, b) => {
                if (currentSort === 'company') return (a.company || '').localeCompare(b.company || '');
                if (currentSort === 'status') return (a.status || '').localeCompare(b.status || '');
                return new Date(b.created_at) - new Date(a.created_at);
            });
            
            const taskList = document.getElementById('task-list');
            taskList.innerHTML = '';
            
            if (tasks.length === 0) {
                taskList.innerHTML = '<tr><td colspan="8" class="px-4 py-8 text-center text-gray-500">No tasks found</td></tr>';
                return;
            }
            
            tasks.forEach(task => {
                const statusColor = task.status === 'completed' ? 'bg-green-100 text-green-800' :
                                  task.status === 'in_progress' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-gray-100 text-gray-800';
                
                taskList.innerHTML += `
                    <tr class="hover:bg-gray-50 ${task.status === 'completed' ? 'opacity-75' : ''}">
                        <td class="px-4 py-2">${task.company || '-'}</td>
                        <td class="px-4 py-2">${task.name || '-'}</td>
                        <td class="px-4 py-2">${task.email || '-'}</td>
                        <td class="px-4 py-2">${task.phone || '-'}</td>
                        <td class="px-4 py-2 text-center">
                            <input type="checkbox" ${task.called ? 'checked' : ''} 
                                   onchange="updateTaskActivity('${task.id}', 'called', this.checked)"
                                   ${task.status === 'completed' ? 'disabled' : ''}>
                        </td>
                        <td class="px-4 py-2 text-center">
                            <input type="checkbox" ${task.emailed ? 'checked' : ''} 
                                   onchange="updateTaskActivity('${task.id}', 'emailed', this.checked)"
                                   ${task.status === 'completed' ? 'disabled' : ''}>
                        </td>
                        <td class="px-4 py-2">
                            <span class="px-2 py-1 rounded text-sm ${statusColor}">
                                ${task.status.replace('_', ' ')}
                            </span>
                        </td>
                        <td class="px-4 py-2">
                            ${task.status !== 'completed' ? `
                                <button onclick="markTaskComplete('${task.id}')" 
                                        class="text-green-600 hover:text-green-800 text-sm">
                                    <i class="fas fa-check-circle"></i> Complete
                                </button>
                            ` : `
                                <button onclick="reopenTask('${task.id}')" 
                                        class="text-blue-600 hover:text-blue-800 text-sm">
                                    <i class="fas fa-undo"></i> Reopen
                                </button>
                            `}
                        </td>
                    </tr>
                `;
            });
        }
        
        function filterTasks() {
            currentFilter = document.getElementById('task-filter').value;
            displayTasks();
        }
        
        function sortTasks() {
            currentSort = document.getElementById('task-sort').value;
            displayTasks();
        }
        
        async function updateTaskActivity(taskId, activity, checked) {
            await fetch(`/api/tasks/${taskId}/activity`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({activity: activity, value: checked})
            });
            
            // Update local data
            const task = allTasks.find(t => t.id === taskId);
            if (task) {
                task[activity] = checked;
                // If both called and emailed, mark as in progress
                if (task.called || task.emailed) {
                    task.status = 'in_progress';
                }
            }
            displayTasks();
        }
        
        async function markTaskComplete(taskId) {
            await fetch(`/api/tasks/${taskId}/complete`, {method: 'POST'});
            const task = allTasks.find(t => t.id === taskId);
            if (task) task.status = 'completed';
            loadTasks();
        }
        
        async function reopenTask(taskId) {
            await fetch(`/api/tasks/${taskId}/reopen`, {method: 'POST'});
            const task = allTasks.find(t => t.id === taskId);
            if (task) task.status = 'pending';
            loadTasks();
        }

    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/config/status')
def get_config_status():
    """Check if API keys are configured"""
    config = Config()
    return jsonify({
        'configured': bool(config.perplexity_api_key),
        'services': {
            'perplexity': bool(config.perplexity_api_key),
            'anthropic': bool(config.anthropic_api_key)
        }
    })

@app.route('/api/config/current')
def get_current_config():
    """Get current config (masked)"""
    config = Config()
    return jsonify({
        'perplexity_key': config.perplexity_api_key[:10] + '...' if config.perplexity_api_key else '',
        'anthropic_key': config.anthropic_api_key[:10] + '...' if config.anthropic_api_key else '',
        'rate_limit_delay': config.rate_limit_delay
    })

@app.route('/api/config/save', methods=['POST'])
def save_config():
    """Save API configuration"""
    global enrichment_engine
    
    data = request.json
    config = Config()
    
    # Save keys
    if data.get('perplexity_key'):
        config.set_api_key('perplexity', data['perplexity_key'])
    
    if data.get('anthropic_key'):
        config.set_api_key('anthropic', data['anthropic_key'])
    
    # Save rate limit delay
    if data.get('rate_limit_delay'):
        config.set_setting('rate_limit_delay', float(data['rate_limit_delay']))
    
    config.save_to_file()
    
    # Reset engine to use new config
    enrichment_engine = None
    
    return jsonify({'success': True})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload and parse companies"""
    global enrichment_engine
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Initialize engine if needed
    if not enrichment_engine:
        config = Config()
        enrichment_engine = SmartEnrichmentEngine(config)
    
    # Parse companies
    try:
        companies, metadata = enrichment_engine.parse_companies_file(filepath)
        return jsonify({
            'companies': companies,
            'metadata': metadata,
            'count': len(companies)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/suggest-roles', methods=['POST'])
def suggest_roles():
    """Get AI role suggestions"""
    data = request.json
    companies = data.get('companies', [])
    
    if not enrichment_engine:
        return jsonify({'error': 'Engine not initialized'}), 500
    
    suggestions = enrichment_engine.ai_assistant.suggest_roles_for_industry(companies)
    return jsonify(suggestions)

@app.route('/api/analyze-manual-search', methods=['POST'])
def analyze_manual_search():
    """Analyze manual search input and suggest roles"""
    global enrichment_engine
    
    data = request.json
    description = data.get('description', '')
    companies = data.get('companies', [])
    industry = data.get('industry', '')
    location = data.get('location', '')
    
    # Initialize engine if needed
    if not enrichment_engine:
        config = Config()
        enrichment_engine = SmartEnrichmentEngine(config)
    
    # Let AI understand the requirements
    requirements = enrichment_engine.ai_assistant.understand_requirements(
        user_input=description,
        companies=companies if companies else None
    )
    
    # If no specific companies, generate based on description
    if not companies:
        # Extract implied search from description
        if 'schools' in description.lower() or 'principal' in description.lower():
            industry = 'schools'
        elif 'hospital' in description.lower() or 'healthcare' in description.lower():
            industry = 'healthcare'
        
        # For general searches, we'll generate queries differently
        companies = ['General Search']
    
    # Get role suggestions based on context
    if companies and companies != ['General Search']:
        suggestions = enrichment_engine.ai_assistant.suggest_roles_for_industry(companies)
    else:
        # Use the requirements to build suggestions
        suggestions = {
            'industry_type': industry or 'General Business',
            'primary_roles': [],
            'secondary_roles': [],
            'insights': f'Based on your search: "{description}"'
        }
        
        # Add roles from requirements
        for role in requirements.get('roles', [])[:3]:
            suggestions['primary_roles'].append({
                'role': role,
                'reason': f'Key role for {industry or "your search"}'
            })
        
        # Add some secondary roles
        if 'manager' not in str(requirements.get('roles', [])).lower():
            suggestions['secondary_roles'].append({
                'role': 'Manager',
                'reason': 'General management contact'
            })
    
    return jsonify(suggestions)

@app.route('/api/generate-queries', methods=['POST'])
def generate_queries():
    """Generate search queries"""
    data = request.json
    companies = data.get('companies', [])
    roles = data.get('roles', [])
    
    queries = []
    for company in companies[:100]:  # Limit for demo
        for role in roles[:2]:  # Max 2 roles per company
            queries.append({
                'company': company,
                'role': role,
                'query': f"Find {role} email and phone for {company}"
            })
    
    return jsonify({'queries': queries})

@app.route('/api/start-enrichment', methods=['POST'])
def start_enrichment():
    """Start enrichment job"""
    global current_job, job_status
    
    data = request.json
    queries = data.get('queries', [])
    
    job_id = str(uuid.uuid4())[:8]
    job_status[job_id] = {
        'status': 'running',
        'total': len(queries),
        'completed': 0,
        'contacts_found': 0,
        'emails_found': 0,
        'phones_found': 0,
        'results': [],
        'current_search': '',
        'errors': []
    }
    
    # Start enrichment in background thread
    thread = threading.Thread(target=run_enrichment, args=(job_id, queries))
    thread.start()
    
    return jsonify({'job_id': job_id})

def run_enrichment(job_id, queries):
    """Run enrichment in background with real Perplexity API"""
    global job_status, enrichment_engine
    
    # Add pause/cancel flags to job
    job_status[job_id]['paused'] = False
    job_status[job_id]['cancelled'] = False
    
    # Initialize Perplexity client if needed
    config = Config()
    if not config.perplexity_api_key:
        job_status[job_id]['status'] = 'error'
        job_status[job_id]['error'] = 'Perplexity API key not configured'
        return
    
    perplexity_client = PerplexityClient(
        api_key=config.perplexity_api_key,
        rate_limit_delay=config.rate_limit_delay
    )
    
    results = []
    batch_size = 5  # Process queries in batches to optimize API calls
    
    # Group queries by company for batch processing
    company_queries = {}
    for q in queries:
        if q['company'] not in company_queries:
            company_queries[q['company']] = []
        company_queries[q['company']].append(q['role'])
    
    total_processed = 0
    
    for company, roles in company_queries.items():
        # Check for pause/cancel
        while job_status[job_id]['paused']:
            job_status[job_id]['status'] = 'paused'
            time.sleep(1)
        
        if job_status[job_id]['cancelled']:
            job_status[job_id]['status'] = 'cancelled'
            return
        
        # Update status
        job_status[job_id]['completed'] = total_processed
        job_status[job_id]['current_search'] = f"Searching for {', '.join(roles[:2])}{'...' if len(roles) > 2 else ''} at {company}"
        
        # Batch roles into single query for efficiency
        if len(roles) > 1:
            batch_query = f"Find contact information for the following positions at {company}: {', '.join(roles)}. Return email and phone for each person."
        else:
            batch_query = f"Find {roles[0]} contact information (email and phone) for {company}"
        
        try:
            # Call real Perplexity API
            contacts = perplexity_client.search_contact(
                query=batch_query,
                additional_context=f"Looking specifically for: {', '.join(roles)} at {company}. Need actual names, emails, and phone numbers."
            )
            
            if contacts:
                for contact in contacts:
                    # Convert ContactInfo to dict for JSON response
                    result = {
                        'name': contact.name or f"{contact.company} Contact",
                        'company': contact.company or company,
                        'email': contact.primary_email or '',
                        'phone': contact.primary_phone or '',
                        'confidence': contact.confidence_score,
                        'sources': contact.sources,
                        'alternate_emails': contact.alternate_emails,
                        'alternate_phones': contact.alternate_phones,
                        'notes': contact.notes
                    }
                    
                    results.append(result)
                    job_status[job_id]['contacts_found'] += 1
                    if contact.primary_email:
                        job_status[job_id]['emails_found'] += 1
                    if contact.primary_phone:
                        job_status[job_id]['phones_found'] += 1
            else:
                # No results found for this company
                job_status[job_id]['errors'].append({
                    'company': company,
                    'message': 'No contacts found'
                })
                
        except Exception as e:
            # Log error but continue processing
            job_status[job_id]['errors'].append({
                'company': company,
                'message': str(e)
            })
        
        total_processed += len(roles)
        job_status[job_id]['results'] = results
        
        # Rate limiting between API calls
        time.sleep(config.rate_limit_delay)
    
    job_status[job_id]['status'] = 'completed'
    job_status[job_id]['completed'] = len(queries)

@app.route('/api/job-status/<job_id>')
def get_job_status(job_id):
    """Get job status"""
    if job_id not in job_status:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(job_status[job_id])

@app.route('/api/job/<job_id>/pause', methods=['POST'])
def pause_job(job_id):
    """Pause a running job"""
    if job_id in job_status:
        job_status[job_id]['paused'] = True
        return jsonify({'success': True})
    return jsonify({'error': 'Job not found'}), 404

@app.route('/api/job/<job_id>/resume', methods=['POST'])
def resume_job(job_id):
    """Resume a paused job"""
    if job_id in job_status:
        job_status[job_id]['paused'] = False
        job_status[job_id]['status'] = 'running'
        return jsonify({'success': True})
    return jsonify({'error': 'Job not found'}), 404

@app.route('/api/job/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a running job"""
    if job_id in job_status:
        job_status[job_id]['cancelled'] = True
        return jsonify({'success': True})
    return jsonify({'error': 'Job not found'}), 404

@app.route('/api/contacts/save', methods=['POST'])
def save_contacts():
    """Save contacts to database"""
    data = request.json
    contacts = data.get('contacts', [])
    
    conn = sqlite3.connect('contacts.db')
    c = conn.cursor()
    
    # Create contacts table if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS saved_contacts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  company TEXT,
                  email TEXT,
                  phone TEXT,
                  alternate_emails TEXT,
                  alternate_phones TEXT,
                  sources TEXT,
                  confidence REAL,
                  notes TEXT,
                  date_found TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    saved_count = 0
    for contact in contacts:
        try:
            c.execute("""INSERT INTO saved_contacts 
                        (name, company, email, phone, alternate_emails, alternate_phones, sources, confidence, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                     (contact.get('name', ''),
                      contact.get('company', ''),
                      contact.get('email', ''),
                      contact.get('phone', ''),
                      json.dumps(contact.get('alternate_emails', [])),
                      json.dumps(contact.get('alternate_phones', [])),
                      json.dumps(contact.get('sources', [])),
                      contact.get('confidence', 0),
                      contact.get('notes', '')))
            saved_count += 1
        except Exception as e:
            print(f"Error saving contact: {e}")
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'saved': saved_count})

@app.route('/api/contacts/search')
def search_saved_contacts():
    """Search saved contacts"""
    query = request.args.get('q', '')
    
    conn = sqlite3.connect('contacts.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if query:
        results = c.execute("""
            SELECT * FROM saved_contacts 
            WHERE name LIKE ? OR company LIKE ? OR email LIKE ?
            ORDER BY date_found DESC
            LIMIT 100
        """, (f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    else:
        results = c.execute("""
            SELECT * FROM saved_contacts 
            ORDER BY date_found DESC 
            LIMIT 100
        """).fetchall()
    
    contacts = []
    for row in results:
        contacts.append({
            'id': row['id'],
            'name': row['name'],
            'company': row['company'],
            'email': row['email'],
            'phone': row['phone'],
            'alternate_emails': json.loads(row['alternate_emails'] or '[]'),
            'alternate_phones': json.loads(row['alternate_phones'] or '[]'),
            'sources': json.loads(row['sources'] or '[]'),
            'confidence': row['confidence'],
            'notes': row['notes'],
            'date_found': row['date_found']
        })
    
    conn.close()
    return jsonify(contacts)

@app.route('/api/export/<job_id>')
def export_results(job_id):
    """Export results"""
    if job_id not in job_status:
        return jsonify({'error': 'Job not found'}), 404
    
    format = request.args.get('format', 'csv')
    results = job_status[job_id]['results']
    
    if format == 'csv':
        # Create CSV
        output = 'Name,Company,Email,Phone,Confidence\n'
        for r in results:
            output += f"{r['name']},{r['company']},{r['email']},{r['phone']},{r['confidence']}\n"
        
        return output, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename=contacts_{job_id}.csv'
        }
    
    return jsonify(results)

@app.route('/api/import-to-tasks', methods=['POST'])
def import_to_tasks():
    """Import selected results to task tracker"""
    data = request.json
    job_id = data.get('job_id')
    selected_contacts = data.get('selected_contacts', None)
    
    # If selected_contacts provided, use those; otherwise use all from job
    if selected_contacts:
        results = selected_contacts
    else:
        if job_id not in job_status:
            return jsonify({'error': 'Job not found'}), 404
        results = job_status[job_id]['results']
    
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    imported_count = 0
    for contact in results:
        # Skip if no useful contact info
        if not (contact.get('email') or contact.get('phone')):
            continue
            
        contact_id = str(uuid.uuid4())
        c.execute("""INSERT INTO contacts (id, name, company, email, phone) 
                    VALUES (?, ?, ?, ?, ?)""",
                 (contact_id, 
                  contact.get('name', 'Unknown'), 
                  contact.get('company', 'Unknown Company'), 
                  contact.get('email', ''), 
                  contact.get('phone', '')))
        
        # Create task
        task_id = str(uuid.uuid4())
        c.execute("""INSERT INTO tasks (id, contact_id, user_id, type, due_date)
                    VALUES (?, ?, ?, ?, ?)""",
                 (task_id, contact_id, 'default', 'initial_contact', date.today().isoformat()))
        
        imported_count += 1
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'imported': imported_count})

@app.route('/api/tasks/all')
def get_all_tasks():
    """Get all tasks with full details"""
    conn = sqlite3.connect('tasks.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Create tasks table with better structure if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id TEXT PRIMARY KEY,
                  contact_id TEXT,
                  user_id TEXT DEFAULT 'default',
                  type TEXT DEFAULT 'initial_contact',
                  status TEXT DEFAULT 'pending',
                  called BOOLEAN DEFAULT 0,
                  emailed BOOLEAN DEFAULT 0,
                  due_date DATE,
                  completed_at TIMESTAMP,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (contact_id) REFERENCES contacts (id))''')
    
    tasks = c.execute("""
        SELECT t.*, c.name, c.company, c.email, c.phone 
        FROM tasks t
        JOIN contacts c ON t.contact_id = c.id
        ORDER BY t.created_at DESC
    """).fetchall()
    
    conn.close()
    return jsonify({'tasks': [dict(task) for task in tasks]})

@app.route('/api/tasks/<task_id>/activity', methods=['POST'])
def update_task_activity(task_id):
    """Update task activity (called/emailed)"""
    data = request.json
    activity = data.get('activity')  # 'called' or 'emailed'
    value = data.get('value', False)
    
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    if activity in ['called', 'emailed']:
        c.execute(f"UPDATE tasks SET {activity} = ? WHERE id = ?", (1 if value else 0, task_id))
        
        # Update status if needed
        if value:
            c.execute("UPDATE tasks SET status = 'in_progress' WHERE id = ? AND status = 'pending'", (task_id,))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/tasks/<task_id>/reopen', methods=['POST'])
def reopen_task(task_id):
    """Reopen a completed task"""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = 'pending', completed_at = NULL WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/tasks/<task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """Mark task complete"""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/activities', methods=['POST'])
def log_activity():
    """Log activity"""
    data = request.json
    # In real app, save to database
    return jsonify({'success': True})

if __name__ == '__main__':
    print("\n🚀 Starting Smart Contact Finder Web App")
    print("📋 Open your browser to: http://localhost:8000")
    print("Press Ctrl+C to stop\n")
    
    # Auto-open browser
    import webbrowser
    webbrowser.open('http://localhost:8000')
    
    app.run(debug=True, port=8000)