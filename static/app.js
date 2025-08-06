// Global state
let searchResults = [];
let currentJobId = null;
let searchCount = 0;
let currentSearchAbortController = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    checkConfiguration();
    loadTemplates();
    setupFileUpload();
    loadStats();
});

// Page navigation
function showPage(pageName, buttonElement) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Show selected page
    document.getElementById(`${pageName}-page`).classList.add('active');
    
    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // If called from event, use event.target, otherwise use provided element
    const targetButton = buttonElement || (event && event.target);
    if (targetButton) {
        targetButton.classList.add('active');
    }
    
    // Load page-specific data
    if (pageName === 'results') {
        displayResults();
    } else if (pageName === 'settings') {
        checkConfiguration();
    }
}

// Tab switching
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    event.target.classList.add('active');
}

// Show alert message
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    
    const icon = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    }[type];
    
    alert.innerHTML = `
        <i class="fas ${icon}"></i>
        <span>${message}</span>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// Check configuration status
async function checkConfiguration() {
    try {
        const response = await fetch('/api/config/status');
        const data = await response.json();
        
        const statusDiv = document.getElementById('config-status');
        statusDiv.innerHTML = '';
        
        for (const [service, configured] of Object.entries(data.services)) {
            const statusItem = document.createElement('div');
            statusItem.className = `status-item ${configured ? 'configured' : 'not-configured'}`;
            statusItem.innerHTML = `
                <i class="fas ${configured ? 'fa-check-circle' : 'fa-times-circle'}"></i>
                <span>${service.charAt(0).toUpperCase() + service.slice(1)}: ${configured ? 'Configured' : 'Not configured'}</span>
            `;
            statusDiv.appendChild(statusItem);
        }
        
        if (!data.configured) {
            showAlert('Please configure your Perplexity API key in Settings', 'warning');
        }
        
        return data.configured;
    } catch (error) {
        console.error('Error checking configuration:', error);
        return false;
    }
}

// Load search templates
async function loadTemplates() {
    try {
        const response = await fetch('/api/templates');
        const templates = await response.json();
        
        const select = document.getElementById('template-select');
        select.innerHTML = '<option value="">Select a template...</option>';
        
        for (const [key, template] of Object.entries(templates)) {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = template.name;
            select.appendChild(option);
        }
    } catch (error) {
        console.error('Error loading templates:', error);
    }
}

// Load template fields
async function loadTemplateFields() {
    const templateKey = document.getElementById('template-select').value;
    const fieldsDiv = document.getElementById('template-fields');
    const searchBtn = document.getElementById('template-search-btn');
    
    if (!templateKey) {
        fieldsDiv.innerHTML = '';
        searchBtn.style.display = 'none';
        return;
    }
    
    try {
        const response = await fetch('/api/templates');
        const templates = await response.json();
        const template = templates[templateKey];
        
        fieldsDiv.innerHTML = '';
        
        template.fields.forEach(field => {
            const fieldGroup = document.createElement('div');
            fieldGroup.className = 'form-group';
            
            const label = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            
            fieldGroup.innerHTML = `
                <label>${label}</label>
                <input type="text" id="template-${field}" placeholder="Enter ${label.toLowerCase()}">
            `;
            
            fieldsDiv.appendChild(fieldGroup);
        });
        
        searchBtn.style.display = 'block';
    } catch (error) {
        console.error('Error loading template fields:', error);
    }
}

// Perform search
async function performSearch() {
    const query = document.getElementById('search-query').value.trim();
    
    if (!query) {
        showAlert('Please enter a search query', 'warning');
        return;
    }
    
    const configured = await checkConfiguration();
    if (!configured) {
        showAlert('Please configure your API keys first', 'error');
        showPage('settings');
        return;
    }
    
    const searchMode = document.querySelector('input[name="search-mode"]:checked').value;
    const verifyContacts = document.getElementById('verify-contacts').checked;
    
    // Clear and show activity log
    clearActivityLog();
    showProgress('Initializing search...');
    addLogEntry('Checking API configuration...', 'info');
    
    try {
        // Create abort controller for this search
        currentSearchAbortController = new AbortController();
        
        addLogEntry(`Search mode: ${searchMode === 'enhanced' ? 'Enhanced (deeper search)' : 'Standard (faster)'}`, 'info');
        addLogEntry(`Query: "${query}"`, 'info');
        
        if (verifyContacts) {
            addLogEntry('Email and phone verification enabled', 'info');
        }
        
        addLogEntry('Connecting to Perplexity AI...', 'process');
        updateProgress(20, 'Contacting Perplexity AI...');
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                enhanced: searchMode === 'enhanced',
                verify_emails: verifyContacts,
                verify_phones: verifyContacts
            }),
            signal: currentSearchAbortController.signal
        });
        
        const data = await response.json();
        
        addLogEntry('Response received from server', 'success');
        updateProgress(60, 'Processing results...');
        
        if (data.success) {
            addLogEntry(`Found ${data.count} contacts`, 'success');
            
            if (data.count > 0) {
                addLogEntry('Processing contact information...', 'process');
                data.results.forEach((contact, index) => {
                    addLogEntry(`  ${index + 1}. ${contact.name} - ${contact.company || 'N/A'}`, 'info');
                });
            }
            
            searchResults = searchResults.concat(data.results);
            searchCount++;
            updateStats();
            
            updateProgress(100, 'Search complete!');
            addLogEntry('✨ Search completed successfully!', 'success');
            showAlert(`Found ${data.count} contacts!`, 'success');
            
            if (data.count > 0) {
                setTimeout(() => {
                    showPage('results');
                    displayResults();
                }, 1500);
            }
        } else {
            addLogEntry('Search failed - no results returned', 'error');
            showAlert('Search failed. Please try again.', 'error');
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            addLogEntry('Search cancelled by user', 'warning');
            showAlert('Search cancelled', 'warning');
        } else {
            console.error('Search error:', error);
            addLogEntry(`Error: ${error.message}`, 'error');
            showAlert('An error occurred during search', 'error');
        }
    } finally {
        currentSearchAbortController = null;
        setTimeout(() => {
            hideProgress();
        }, 2000);
    }
}

// Search with template
async function searchWithTemplate() {
    const templateKey = document.getElementById('template-select').value;
    
    if (!templateKey) {
        showAlert('Please select a template', 'warning');
        return;
    }
    
    // Clear and show activity log
    clearActivityLog();
    showProgress('Preparing template search...');
    addLogEntry('Loading template configuration...', 'info');
    
    try {
        const response = await fetch('/api/templates');
        const templates = await response.json();
        const template = templates[templateKey];
        
        const fieldValues = {};
        let allFilled = true;
        
        template.fields.forEach(field => {
            const value = document.getElementById(`template-${field}`).value.trim();
            if (!value) {
                allFilled = false;
            }
            fieldValues[field] = value;
        });
        
        if (!allFilled) {
            showAlert('Please fill in all fields', 'warning');
            return;
        }
        
        addLogEntry(`Template: ${template.name}`, 'info');
        Object.entries(fieldValues).forEach(([field, value]) => {
            addLogEntry(`  ${field}: ${value}`, 'info');
        });
        
        showProgress('Building search query from template...');
        addLogEntry('Generating search query...', 'process');
        updateProgress(30, 'Sending to Perplexity AI...');
        
        // Create abort controller for this search
        currentSearchAbortController = new AbortController();
        
        const searchResponse = await fetch('/api/search/template', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                template_key: templateKey,
                field_values: fieldValues,
                enhanced: false
            }),
            signal: currentSearchAbortController.signal
        });
        
        const data = await searchResponse.json();
        
        addLogEntry('Response received from server', 'success');
        updateProgress(70, 'Processing results...');
        
        if (data.success) {
            addLogEntry(`Found ${data.count} contacts using template`, 'success');
            
            if (data.count > 0) {
                data.results.forEach((contact, index) => {
                    addLogEntry(`  ${index + 1}. ${contact.name} - ${contact.company || 'N/A'}`, 'info');
                });
            }
            
            searchResults = searchResults.concat(data.results);
            searchCount++;
            updateStats();
            
            updateProgress(100, 'Template search complete!');
            addLogEntry('✨ Template search completed successfully!', 'success');
            showAlert(`Found ${data.count} contacts!`, 'success');
            
            if (data.count > 0) {
                setTimeout(() => {
                    showPage('results');
                    displayResults();
                }, 1500);
            }
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            addLogEntry('Search cancelled by user', 'warning');
            showAlert('Search cancelled', 'warning');
        } else {
            console.error('Template search error:', error);
            addLogEntry(`Error: ${error.message}`, 'error');
            showAlert('An error occurred during search', 'error');
        }
    } finally {
        currentSearchAbortController = null;
        setTimeout(() => {
            hideProgress();
        }, 2000);
    }
}

// File upload handling
function setupFileUpload() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const file = e.dataTransfer.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });
}

// Handle file upload
async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayBatchQueries(data.queries);
        } else {
            showAlert('Failed to process file', 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showAlert('Error uploading file', 'error');
    }
}

// Display batch queries
function displayBatchQueries(queries) {
    const previewDiv = document.getElementById('batch-preview');
    const queriesList = document.getElementById('queries-list');
    
    queriesList.innerHTML = `
        <div style="max-height: 200px; overflow-y: auto; background: white; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
            ${queries.slice(0, 10).map((q, i) => `<div>${i + 1}. ${q}</div>`).join('')}
            ${queries.length > 10 ? `<div>... and ${queries.length - 10} more</div>` : ''}
        </div>
    `;
    
    previewDiv.style.display = 'block';
    previewDiv.dataset.queries = JSON.stringify(queries);
}

// Start batch search
async function startBatchSearch() {
    const previewDiv = document.getElementById('batch-preview');
    const queries = JSON.parse(previewDiv.dataset.queries || '[]');
    
    if (queries.length === 0) {
        showAlert('No queries to process', 'warning');
        return;
    }
    
    showProgress(`Processing ${queries.length} queries...`);
    
    try {
        const response = await fetch('/api/search/batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                queries: queries,
                enhanced: false,
                verify: false
            })
        });
        
        const data = await response.json();
        currentJobId = data.job_id;
        
        // Poll for results
        pollBatchStatus();
    } catch (error) {
        console.error('Batch search error:', error);
        showAlert('Error starting batch search', 'error');
        hideProgress();
    }
}

// Poll batch search status
async function pollBatchStatus() {
    if (!currentJobId) return;
    
    try {
        const response = await fetch(`/api/search/status/${currentJobId}`);
        const data = await response.json();
        
        updateProgress(data.progress / data.total * 100, `Processing query ${data.progress} of ${data.total}`);
        
        if (data.status === 'completed') {
            searchResults = searchResults.concat(data.results);
            searchCount += data.total;
            updateStats();
            showAlert(`Batch search complete! Found ${data.results.length} contacts`, 'success');
            hideProgress();
            
            if (data.results.length > 0) {
                showPage('results');
                displayResults();
            }
            
            currentJobId = null;
        } else {
            // Continue polling
            setTimeout(pollBatchStatus, 1000);
        }
    } catch (error) {
        console.error('Status poll error:', error);
        hideProgress();
    }
}

// Global variables for results management
let filteredResults = [];
let selectedContacts = new Set();

// Display results
function displayResults(resultsToShow = null) {
    const tbody = document.getElementById('results-tbody');
    const count = document.getElementById('results-count');
    
    const results = resultsToShow || searchResults;
    count.textContent = results.length;
    
    if (results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="no-data">No results yet. Start a search to see contacts here.</td></tr>';
        return;
    }
    
    tbody.innerHTML = results.map((contact, index) => `
        <tr data-index="${index}">
            <td>
                <input type="checkbox" class="contact-checkbox" value="${index}" onchange="toggleSelection(${index})">
            </td>
            <td>${contact.name || 'N/A'}</td>
            <td>${contact.company || 'N/A'}</td>
            <td>${contact.primary_email || 'N/A'}</td>
            <td>${contact.primary_phone || 'N/A'}</td>
            <td>${contact.confidence_score ? Math.round(contact.confidence_score * 100) + '%' : 'N/A'}</td>
            <td>
                ${contact.verification_status?.email === 'valid' ? '<i class="fas fa-check-circle" style="color: var(--secondary-color);"></i>' : ''}
                ${contact.verification_status?.phone === 'valid' ? '<i class="fas fa-phone-check" style="color: var(--secondary-color);"></i>' : ''}
            </td>
            <td>${contact.sources ? contact.sources.length : 0}</td>
            <td>
                <button class="btn-icon" onclick="editContact(${index})" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn-icon" onclick="deleteContact(${index})" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
                <button class="btn-icon" onclick="viewDetails(${index})" title="View Details">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        </tr>
    `).join('');
    
    updateSelectionUI();
}

// Toggle selection of a contact
function toggleSelection(index) {
    if (selectedContacts.has(index)) {
        selectedContacts.delete(index);
    } else {
        selectedContacts.add(index);
    }
    updateSelectionUI();
}

// Toggle select all
function toggleSelectAll() {
    const selectAll = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('.contact-checkbox');
    
    if (selectAll.checked) {
        checkboxes.forEach(cb => {
            cb.checked = true;
            selectedContacts.add(parseInt(cb.value));
        });
    } else {
        checkboxes.forEach(cb => {
            cb.checked = false;
        });
        selectedContacts.clear();
    }
    
    updateSelectionUI();
}

// Update selection UI
function updateSelectionUI() {
    const selectedCount = document.getElementById('selected-count');
    const selectedNumber = document.getElementById('selected-number');
    const bulkActions = document.getElementById('bulk-actions');
    
    if (selectedContacts.size > 0) {
        selectedCount.style.display = 'inline';
        selectedNumber.textContent = selectedContacts.size;
        bulkActions.style.display = 'flex';
    } else {
        selectedCount.style.display = 'none';
        bulkActions.style.display = 'none';
    }
}

// Filter results
function filterResults() {
    const filterText = document.getElementById('filter-input').value.toLowerCase();
    
    if (!filterText) {
        filteredResults = searchResults;
    } else {
        filteredResults = searchResults.filter(contact => {
            return (
                (contact.name && contact.name.toLowerCase().includes(filterText)) ||
                (contact.company && contact.company.toLowerCase().includes(filterText)) ||
                (contact.primary_email && contact.primary_email.toLowerCase().includes(filterText)) ||
                (contact.primary_phone && contact.primary_phone.toLowerCase().includes(filterText))
            );
        });
    }
    
    displayResults(filteredResults);
}

// Sort results
function sortResults() {
    const sortBy = document.getElementById('sort-select').value;
    
    if (!sortBy) {
        displayResults(filteredResults.length > 0 ? filteredResults : searchResults);
        return;
    }
    
    const resultsToSort = filteredResults.length > 0 ? [...filteredResults] : [...searchResults];
    
    resultsToSort.sort((a, b) => {
        switch(sortBy) {
            case 'name':
                return (a.name || '').localeCompare(b.name || '');
            case 'company':
                return (a.company || '').localeCompare(b.company || '');
            case 'confidence':
                return (b.confidence_score || 0) - (a.confidence_score || 0);
            default:
                return 0;
        }
    });
    
    displayResults(resultsToSort);
}

// Delete selected contacts
function deleteSelected() {
    if (selectedContacts.size === 0) return;
    
    if (confirm(`Delete ${selectedContacts.size} selected contacts?`)) {
        // Convert indices to array and sort in reverse order
        const indicesToDelete = Array.from(selectedContacts).sort((a, b) => b - a);
        
        // Delete from highest index to lowest to maintain correct indices
        indicesToDelete.forEach(index => {
            searchResults.splice(index, 1);
        });
        
        selectedContacts.clear();
        updateStats();
        displayResults();
        showAlert(`Deleted ${indicesToDelete.length} contacts`, 'success');
    }
}

// Verify selected contacts
async function verifySelected() {
    if (selectedContacts.size === 0) return;
    
    showAlert(`Verifying ${selectedContacts.size} contacts...`, 'info');
    
    // TODO: Implement batch verification
    const contactsToVerify = Array.from(selectedContacts).map(i => searchResults[i]);
    
    // For now, just mark as being processed
    showAlert('Batch verification feature coming soon!', 'info');
}

// Delete single contact
function deleteContact(index) {
    if (confirm('Delete this contact?')) {
        searchResults.splice(index, 1);
        selectedContacts.delete(index);
        updateStats();
        displayResults();
        showAlert('Contact deleted', 'success');
    }
}

// Edit contact  
function editContact(index) {
    const contact = searchResults[index];
    // TODO: Implement edit modal
    showAlert('Edit feature coming soon!', 'info');
    console.log('Editing contact:', contact);
}

// View contact details
function viewDetails(index) {
    const contact = searchResults[index];
    // TODO: Implement details modal
    showAlert('Details view coming soon!', 'info');
    console.log('Viewing details:', contact);
}

// Export results
async function exportResults(format) {
    if (searchResults.length === 0) {
        showAlert('No results to export', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                contacts: searchResults,
                format: format
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `contacts.${format === 'apollo' ? 'csv' : format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            showAlert(`Exported ${searchResults.length} contacts to ${format.toUpperCase()}`, 'success');
        } else {
            showAlert('Export failed', 'error');
        }
    } catch (error) {
        console.error('Export error:', error);
        showAlert('Error exporting results', 'error');
    }
}

// Save settings
async function saveSettings() {
    const perplexityKey = document.getElementById('perplexity-key').value.trim();
    
    if (!perplexityKey) {
        showAlert('Perplexity API key is required', 'error');
        return;
    }
    
    const settings = {
        perplexity: perplexityKey,
        hunter: document.getElementById('hunter-key').value.trim(),
        zerobounce: document.getElementById('zerobounce-key').value.trim(),
        numverify: document.getElementById('numverify-key').value.trim(),
        twilio_account_sid: document.getElementById('twilio-sid').value.trim(),
        twilio_auth_token: document.getElementById('twilio-token').value.trim()
    };
    
    try {
        const response = await fetch('/api/config/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Configuration saved successfully!', 'success');
            checkConfiguration();
        } else {
            showAlert('Failed to save configuration', 'error');
        }
    } catch (error) {
        console.error('Save settings error:', error);
        showAlert('Error saving settings', 'error');
    }
}

// Activity log functions
function addLogEntry(message, type = '') {
    const log = document.getElementById('activity-log');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    
    const timestamp = new Date().toLocaleTimeString();
    entry.innerHTML = `<span class="log-timestamp">[${timestamp}]</span> ${message}`;
    
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
}

function clearActivityLog() {
    const log = document.getElementById('activity-log');
    log.innerHTML = '';
}

function toggleActivityLog() {
    const log = document.getElementById('activity-log');
    const icon = document.getElementById('log-toggle-icon');
    
    if (log.classList.contains('expanded')) {
        log.classList.remove('expanded');
        icon.className = 'fas fa-chevron-right';
    } else {
        log.classList.add('expanded');
        icon.className = 'fas fa-chevron-down';
    }
}

// Progress bar functions
function showProgress(text) {
    const container = document.getElementById('progress-container');
    const progressText = document.getElementById('progress-text');
    
    container.style.display = 'block';
    progressText.textContent = text;
    updateProgress(0);
}

function updateProgress(percent, text) {
    const fill = document.getElementById('progress-fill');
    fill.style.width = `${percent}%`;
    
    if (text) {
        document.getElementById('progress-text').textContent = text;
    }
}

function hideProgress() {
    document.getElementById('progress-container').style.display = 'none';
}

// Update stats
function updateStats() {
    document.getElementById('contacts-found').textContent = searchResults.length;
    document.getElementById('searches-performed').textContent = searchCount;
    
    // Save to localStorage
    localStorage.setItem('searchResults', JSON.stringify(searchResults));
    localStorage.setItem('searchCount', searchCount);
}

// Load stats from localStorage
function loadStats() {
    const savedResults = localStorage.getItem('searchResults');
    const savedCount = localStorage.getItem('searchCount');
    
    if (savedResults) {
        searchResults = JSON.parse(savedResults);
    }
    
    if (savedCount) {
        searchCount = parseInt(savedCount);
    }
    
    updateStats();
}

// Cancel current search
function cancelSearch() {
    if (currentSearchAbortController) {
        currentSearchAbortController.abort();
        currentSearchAbortController = null;
        addLogEntry('Cancelling search...', 'warning');
    }
    
    if (currentJobId) {
        // TODO: Cancel batch job on server
        currentJobId = null;
        addLogEntry('Cancelling batch search...', 'warning');
    }
    
    setTimeout(() => {
        hideProgress();
    }, 1000);
}