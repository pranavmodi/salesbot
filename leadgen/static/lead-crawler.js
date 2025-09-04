// Lead Crawler JavaScript
let crawlerSocket = null;
let crawlerTaskId = null;
let crawlerStartTime = null;
let crawlerTimer = null;

// DOM Elements
const crawlerForm = document.getElementById('crawlerForm');
const startCrawlerBtn = document.getElementById('startCrawlerBtn');
const stopCrawlerBtn = document.getElementById('stopCrawlerBtn');
const crawlerProgress = document.getElementById('crawlerProgress');
const crawlerResults = document.getElementById('crawlerResults');
const crawlerStatus = document.getElementById('crawlerStatus');
const crawlerStage = document.getElementById('crawlerStage');
const crawlerTimer = document.getElementById('crawlerTimer');
const crawlerProgressFill = document.getElementById('crawlerProgressFill');
const crawlerProgressText = document.getElementById('crawlerProgressText');
const crawlerLiveUpdates = document.getElementById('crawlerLiveUpdates');
const crawlerResultsSummary = document.getElementById('crawlerResultsSummary');
const crawlerResultsPreview = document.getElementById('crawlerResultsPreview');
const downloadCrawlerResults = document.getElementById('downloadCrawlerResults');
const viewCrawlerResults = document.getElementById('viewCrawlerResults');

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    console.log('Lead Crawler page loaded');
    setupEventListeners();
});

function setupEventListeners() {
    // Form submission
    crawlerForm.addEventListener('submit', startCrawling);
    
    // Stop button
    stopCrawlerBtn.addEventListener('click', stopCrawling);
    
    // Results actions
    downloadCrawlerResults.addEventListener('click', downloadResults);
    viewCrawlerResults.addEventListener('click', () => window.open('/', '_blank'));
}

async function startCrawling(e) {
    e.preventDefault();
    
    // Get form data
    const formData = new FormData(crawlerForm);
    const config = {
        seed_companies: formData.get('seedCompanies').split('\n').filter(line => line.trim()),
        industry: formData.get('industry'),
        company_size: formData.get('companySize'),
        max_companies: parseInt(formData.get('maxCompanies')) || 50,
        crawl_depth: parseInt(formData.get('crawlDepth')) || 2,
        enable_enrichment: formData.get('enableEnrichment') === 'on',
        enable_scoring: formData.get('enableScoring') === 'on',
        skip_existing: formData.get('skipExisting') === 'on'
    };
    
    console.log('Starting crawler with config:', config);
    
    try {
        // Start crawling task
        const response = await fetch('/api/start-crawling', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(config)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        crawlerTaskId = result.task_id;
        
        // Update UI
        updateCrawlerStatus('running', 'Crawling Started');
        showCrawlerProgress();
        startCrawlerBtn.style.display = 'none';
        stopCrawlerBtn.style.display = 'inline-block';
        
        // Start WebSocket connection
        connectCrawlerWebSocket();
        
        // Start timer
        startCrawlerTimer();
        
        showSuccessMessage('Company crawling started successfully!');
        
    } catch (error) {
        console.error('Error starting crawler:', error);
        showErrorMessage(`Failed to start crawler: ${error.message}`);
    }
}

function connectCrawlerWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    crawlerSocket = new WebSocket(wsUrl);
    
    crawlerSocket.onopen = function() {
        console.log('Crawler WebSocket connected');
    };
    
    crawlerSocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('Crawler WebSocket message:', data);
        
        // Filter for our task ID
        if (data.task_id && data.task_id !== crawlerTaskId) return;
        
        updateCrawlerProgress(data);
    };
    
    crawlerSocket.onclose = function() {
        console.log('Crawler WebSocket disconnected');
        crawlerSocket = null;
    };
    
    crawlerSocket.onerror = function(error) {
        console.error('Crawler WebSocket error:', error);
    };
}

function updateCrawlerProgress(data) {
    // Update stage
    if (data.stage) {
        crawlerStage.textContent = data.stage;
    }
    
    // Update progress
    if (data.progress !== undefined) {
        const progress = Math.round(data.progress);
        crawlerProgressFill.style.width = `${progress}%`;
        crawlerProgressText.textContent = `${progress}% Complete`;
    }
    
    // Add live update
    if (data.message) {
        addCrawlerLiveUpdate(data.message);
    }
    
    // Handle completion
    if (data.status === 'completed') {
        handleCrawlerCompletion(data);
    } else if (data.status === 'failed') {
        handleCrawlerError(data.error || 'Crawling failed');
    }
}

function addCrawlerLiveUpdate(message) {
    const updateItem = document.createElement('div');
    updateItem.className = 'update-item';
    updateItem.innerHTML = `
        <span class="timestamp">${formatTime(getCrawlerElapsedTime())}</span>
        <span class="message">${escapeHtml(message)}</span>
    `;
    
    crawlerLiveUpdates.appendChild(updateItem);
    
    // Scroll to bottom
    crawlerLiveUpdates.scrollTop = crawlerLiveUpdates.scrollHeight;
    
    // Limit to last 50 updates
    const updates = crawlerLiveUpdates.children;
    if (updates.length > 50) {
        crawlerLiveUpdates.removeChild(updates[0]);
    }
}

function handleCrawlerCompletion(data) {
    console.log('Crawler completed:', data);
    
    updateCrawlerStatus('completed', 'Crawling Completed');
    stopCrawlerTimer();
    
    // Hide stop button, show start button
    startCrawlerBtn.style.display = 'inline-block';
    stopCrawlerBtn.style.display = 'none';
    
    // Show results
    showCrawlerResults(data);
    
    showSuccessMessage('Company crawling completed successfully!');
}

function handleCrawlerError(error) {
    console.error('Crawler error:', error);
    
    updateCrawlerStatus('error', 'Crawling Failed');
    stopCrawlerTimer();
    
    startCrawlerBtn.style.display = 'inline-block';
    stopCrawlerBtn.style.display = 'none';
    
    showErrorMessage(`Crawling failed: ${error}`);
}

function showCrawlerResults(data) {
    // Update summary
    const stats = data.stats || {};
    crawlerResultsSummary.innerHTML = `
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-number">${stats.companies_discovered || 0}</div>
                <div class="stat-label">Companies Discovered</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${stats.companies_added || 0}</div>
                <div class="stat-label">New Companies Added</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${stats.companies_enriched || 0}</div>
                <div class="stat-label">Companies Enriched</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">${stats.companies_scored || 0}</div>
                <div class="stat-label">Companies Scored</div>
            </div>
        </div>
    `;
    
    // Show preview of discovered companies
    if (data.preview && data.preview.length > 0) {
        const previewTable = `
            <h4>🔍 Preview of Discovered Companies</h4>
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Company</th>
                        <th>Domain</th>
                        <th>Industry</th>
                        <th>Size</th>
                        <th>Score</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.preview.map(company => `
                        <tr>
                            <td><strong>${escapeHtml(company.name)}</strong></td>
                            <td>${company.domain || '-'}</td>
                            <td>${company.industry || '-'}</td>
                            <td>${company.employee_count || '-'}</td>
                            <td>${company.lead_score || 0}</td>
                            <td>
                                <span class="status-badge ${company.is_qualified_lead ? 'status-qualified' : 'status-pending'}">
                                    ${company.is_qualified_lead ? 'Qualified' : 'Pending'}
                                </span>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        crawlerResultsPreview.innerHTML = previewTable;
    }
    
    // Show results section
    crawlerResults.style.display = 'block';
    crawlerResults.scrollIntoView({ behavior: 'smooth' });
}

async function stopCrawling() {
    if (!crawlerTaskId) return;
    
    try {
        const response = await fetch(`/api/stop-crawling/${crawlerTaskId}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            updateCrawlerStatus('stopped', 'Crawling Stopped');
            stopCrawlerTimer();
            startCrawlerBtn.style.display = 'inline-block';
            stopCrawlerBtn.style.display = 'none';
            showSuccessMessage('Crawling stopped successfully');
        }
    } catch (error) {
        console.error('Error stopping crawler:', error);
        showErrorMessage('Failed to stop crawler');
    }
}

async function downloadResults() {
    if (!crawlerTaskId) return;
    
    try {
        const response = await fetch(`/api/download-crawling/${crawlerTaskId}`);
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `crawler_results_${crawlerTaskId}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }
    } catch (error) {
        console.error('Error downloading results:', error);
        showErrorMessage('Failed to download results');
    }
}

// UI Helper Functions
function updateCrawlerStatus(status, text) {
    const statusBadge = crawlerStatus.querySelector('.status-badge');
    statusBadge.className = `status-badge status-${status}`;
    statusBadge.textContent = text;
}

function showCrawlerProgress() {
    crawlerProgress.style.display = 'block';
    crawlerProgress.scrollIntoView({ behavior: 'smooth' });
}

function startCrawlerTimer() {
    crawlerStartTime = Date.now();
    crawlerTimer = setInterval(() => {
        const elapsed = getCrawlerElapsedTime();
        document.getElementById('crawlerTimer').textContent = formatTime(elapsed);
    }, 1000);
}

function stopCrawlerTimer() {
    if (crawlerTimer) {
        clearInterval(crawlerTimer);
        crawlerTimer = null;
    }
}

function getCrawlerElapsedTime() {
    return crawlerStartTime ? Math.floor((Date.now() - crawlerStartTime) / 1000) : 0;
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showSuccessMessage(message) {
    const successDiv = document.getElementById('successMessage');
    successDiv.textContent = message;
    successDiv.style.display = 'block';
    setTimeout(() => {
        successDiv.style.display = 'none';
    }, 5000);
}

function showErrorMessage(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (crawlerSocket) {
        crawlerSocket.close();
    }
    if (crawlerTimer) {
        clearInterval(crawlerTimer);
    }
});