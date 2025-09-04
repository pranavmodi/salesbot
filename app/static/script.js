// Global Variables
let websocket = null;
let currentTaskId = null;
let companiesSeeded = false;
let currentPage = 1;
let companiesPerPage = 20;
let currentFilters = {};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Lead Generation Tool initialized');
    
    // Initialize WebSocket connection
    initWebSocket();
    
    // Check database status on load and enable proceed button if companies exist
    checkDatabase().then(count => {
        if (count > 0) {
            document.getElementById('proceedToStep2').disabled = false;
            companiesSeeded = true;
        }
        // Only load companies if no active filters (initial page load)
        console.log('Initial load check - currentFilters:', currentFilters);
        if (Object.keys(currentFilters).length === 0) {
            console.log('No active filters, loading initial companies');
            loadCompanies(1, {});
        } else {
            console.log('Active filters detected, skipping initial load');
        }
        loadFilterOptions();
    });
    
    // Add event listeners
    setupEventListeners();
});

// Setup Event Listeners
function setupEventListeners() {
    // Step navigation
    document.getElementById('step1').addEventListener('click', () => showStep(1));
    document.getElementById('step2').addEventListener('click', () => showStep(2));
    
    // Proceed button
    document.getElementById('proceedToStep2').addEventListener('click', () => showStep(2));
    
    // Filter buttons
    document.getElementById('applyFilters').addEventListener('click', () => applyFilters());
    document.getElementById('clearFilters').addEventListener('click', () => clearFilters());
    document.getElementById('refreshCompanies').addEventListener('click', () => refreshCompanies());
    
    // Search input
    const searchInput = document.getElementById('searchTerm');
    if (searchInput) {
        console.log('Search input found, adding event listener');
        searchInput.addEventListener('input', debounce(() => {
            console.log('Search input changed:', searchInput.value);
            applyFilters();
        }, 500));
    } else {
        console.error('Search input not found!');
    }
    
    // Pagination
    document.getElementById('prevPage').addEventListener('click', () => {
        if (currentPage > 1) {
            loadCompanies(currentPage - 1, currentFilters);
        }
    });
    
    document.getElementById('nextPage').addEventListener('click', () => {
        loadCompanies(currentPage + 1, currentFilters);
    });
    
    // Step 2 specific event listeners
    const backToStep1Btn = document.getElementById('backToStep1');
    if (backToStep1Btn) {
        backToStep1Btn.addEventListener('click', () => goToStep(1));
    }
    
    const maxCompaniesInput = document.getElementById('maxCompanies');
    if (maxCompaniesInput) {
        maxCompaniesInput.addEventListener('input', function() {
            const maxCompanies = parseInt(this.value) || 0;
            const totalCompanies = parseInt(document.getElementById('totalCompanies').textContent) || 0;
            document.getElementById('estimatedLeads').textContent = Math.min(maxCompanies, totalCompanies);
        });
    }
    
    const scrapingForm = document.getElementById('scrapingForm');
    if (scrapingForm) {
        scrapingForm.addEventListener('submit', handleScrapingFormSubmit);
    }
    
    const downloadButton = document.getElementById('downloadButton');
    if (downloadButton) {
        downloadButton.addEventListener('click', handleDownload);
    }
    
    // Score unscored companies
    const scoreUnscoredBtn = document.getElementById('scoreUnscoredBtn');
    if (scoreUnscoredBtn) {
        scoreUnscoredBtn.addEventListener('click', scoreUnscoredCompanies);
    }
    
    // Enhanced button interactions
    setupEnhancedButtonInteractions();
}

// Enhanced Button Interactions
function setupEnhancedButtonInteractions() {
    // Apollo seed button
    const apolloSeedBtn = document.getElementById('apolloSeedButton');
    if (apolloSeedBtn) {
        apolloSeedBtn.addEventListener('click', function() {
            this.classList.add('loading');
            this.disabled = true;
            this.textContent = 'Seeding...';
            
            // Simulate seeding process (replace with actual API call)
            setTimeout(() => {
                this.classList.remove('loading');
                this.disabled = false;
                this.textContent = 'Seed from Apollo';
                // Show success message or close modal
                closeAddCompaniesMenu();
            }, 2000);
        });
    }

    // CSV upload button
    const uploadCsvBtn = document.getElementById('uploadCsvButton');
    if (uploadCsvBtn) {
        uploadCsvBtn.addEventListener('click', function() {
            const fileInput = document.getElementById('csvFileInput');
            if (fileInput.files.length > 0) {
                this.classList.add('loading');
                this.disabled = true;
                this.textContent = 'Processing...';
                
                // Simulate processing (replace with actual API call)
                setTimeout(() => {
                    this.classList.remove('loading');
                    this.disabled = false;
                    this.textContent = 'Upload & Process';
                    // Show success message or close modal
                    closeAddCompaniesMenu();
                }, 2000);
            } else {
                showToast('Please select a CSV file first.', 'error');
            }
        });
    }

    // Manual add button
    const manualAddBtn = document.getElementById('manualAddButton');
    if (manualAddBtn) {
        manualAddBtn.addEventListener('click', function() {
            showManualCompanyForm();
        });
    }

    // Cancel add company button
    const cancelAddBtn = document.getElementById('cancelAddCompanyButton');
    if (cancelAddBtn) {
        cancelAddBtn.addEventListener('click', function() {
            hideManualCompanyForm();
        });
    }

    // Add company form submission
    const addCompanyForm = document.getElementById('addCompanyForm');
    if (addCompanyForm) {
        addCompanyForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleManualCompanySubmission();
        });
    }

    // Start seeding button
    const startSeedingBtn = document.getElementById('startSeedingButton');
    if (startSeedingBtn) {
        startSeedingBtn.addEventListener('click', function() {
            this.classList.add('loading');
            this.disabled = true;
            this.textContent = 'Starting...';
            
            // Simulate seeding start (replace with actual API call)
            setTimeout(() => {
                this.classList.remove('loading');
                this.disabled = false;
                this.textContent = '🌱 Start Seeding';
                // Show success message or close modal
                closeAddCompaniesMenu();
            }, 2000);
        });
    }
}

// Step Navigation
function showStep(stepNumber) {
    // Hide all step content
    document.querySelectorAll('.step-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all steps
    document.querySelectorAll('.step').forEach(step => {
        step.classList.remove('active');
    });
    
    // Show selected step content
    document.getElementById(`step${stepNumber}Content`).classList.add('active');
    
    // Activate selected step
    document.getElementById(`step${stepNumber}`).classList.add('active');
    
    // Update current page
    currentPage = 1;
    
    // Load companies for step 1
    if (stepNumber === 1) {
        loadCompanies(1, currentFilters);
    }
    
    // Load companies for step 2
    if (stepNumber === 2) {
        updateCompanyCounts();
    }
}

// Alternative step navigation function (for compatibility)
function goToStep(stepNumber) {
    showStep(stepNumber);
}

// Check Database Status
async function checkDatabase() {
    try {
        const response = await fetch('/api/company-count');
        const data = await response.json();
        
        if (data.count > 0) {
            document.getElementById('proceedToStep2').disabled = false;
            companiesSeeded = true;
        } else {
            document.getElementById('proceedToStep2').disabled = true;
            companiesSeeded = false;
        }
        
        return data.count;
    } catch (error) {
        console.error('Error checking database:', error);
        return 0;
    }
}

// Update Company Counts for Step 2
function updateCompanyCounts() {
    checkDatabase().then(count => {
        document.getElementById('totalCompanies').textContent = count;
        const maxCompanies = parseInt(document.getElementById('maxCompanies').value);
        document.getElementById('estimatedLeads').textContent = Math.min(count, maxCompanies);
    });
}

// Initialize WebSocket connection
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = function(event) {
        console.log('WebSocket connected');
    };
    
    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    websocket.onclose = function(event) {
        console.log('WebSocket disconnected');
        // Attempt to reconnect after 3 seconds
        setTimeout(initWebSocket, 3000);
    };
    
    websocket.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
}

// Handle WebSocket messages
function handleWebSocketMessage(data) {
    if (data.task_id !== currentTaskId) return;
    
    switch(data.type) {
        case 'status':
            addLog(data.message);
            break;
        case 'progress':
            updateProgress(data.progress, data.total, data.current_company);
            break;
        case 'lead_scoring_phase':
            updateLeadScoringPhase(data);
            break;
        case 'log':
            addLog(data.message);
            break;
        case 'error':
            addLog(`❌ ${data.message}`, 'error');
            break;
        case 'lead_found':
            addLog(`✅ ${data.message}`, 'success');
            document.getElementById('leadsFound').textContent = data.leads_found;
            break;
        case 'completed':
            handleCompletion(data);
            break;
    }
}

// Add log message
function addLog(message, type = 'info') {
    const logArea = document.getElementById('logArea');
    const timestamp = new Date().toLocaleTimeString();
    const className = type === 'error' ? 'error' : type === 'success' ? 'success' : '';
    
    logArea.innerHTML += `<div class="${className}">[${timestamp}] ${message}</div>`;
    logArea.scrollTop = logArea.scrollHeight;
}

// Update progress display
function updateProgress(current, total, company) {
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const currentCompany = document.getElementById('currentCompany');
    
    if (progressBar) {
        const percentage = Math.round((current / total) * 100);
        progressBar.style.width = `${percentage}%`;
        progressText.textContent = `${current} / ${total}`;
    }
    
    if (currentCompany) {
        currentCompany.textContent = company || 'Processing...';
    }
}

// Handle completion
async function handleCompletion(data) {
    addLog(`✅ Task completed! ${data.leads_found || 0} leads found.`, 'success');
    
    // Update progress to 100%
    updateProgress(data.total || 1, data.total || 1, 'Completed');
    
    // Enable proceed button
    document.getElementById('proceedToStep2').disabled = false;
    companiesSeeded = true;
    
    // Check database and update company list
    await checkDatabase();
    loadCompanies(1, {});
}

// Load companies with pagination and filters
async function loadCompanies(page = 1, filters = {}) {
    try {
        console.log('loadCompanies called with:', { page, filters });
        showLoadingState();
        
        // Build query parameters
        const params = new URLSearchParams({
            offset: (page - 1) * companiesPerPage,
            limit: companiesPerPage,
            ...filters
        });
        
        const url = `/api/companies?${params}`;
        console.log('Fetching from URL:', url);
        console.log('Page:', page, 'Offset:', (page - 1) * companiesPerPage, 'Limit:', companiesPerPage);
        console.log('Search term being sent:', filters.search_term || 'none');
        
        const response = await fetch(url);
        console.log('Response status:', response.status, response.statusText);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('API response data:', data);
        
        // Debug: Show first few company names to verify filtering
        if (data.companies && data.companies.length > 0) {
            console.log('First 3 companies in results:', data.companies.slice(0, 3).map(c => c.name));
        }
        
        // Update current page
        currentPage = page;
        currentFilters = filters;
        
        // Display companies
        displayCompanies(data.companies);
        
        // Update pagination
        updatePagination(data.total, page);
        
        // Update company statistics
        updateCompanyStats(data.total);
        
        hideLoadingState();
        
    } catch (error) {
        console.error('Error loading companies:', error);
        showToast(`❌ Failed to load companies: ${error.message}`, 'error');
        hideLoadingState();
    }
}

// Display companies in the table
function displayCompanies(companies) {
    console.log('displayCompanies called with:', companies);
    
    const tableBody = document.getElementById('companyTableBody');
    console.log('Table body element:', tableBody);
    
    if (!companies || companies.length === 0) {
        console.log('No companies to display, showing empty state');
        showEmptyState('No companies found with the current filters.');
        return;
    }
    
    console.log(`Displaying ${companies.length} companies`);
    tableBody.innerHTML = '';
    
    companies.forEach(company => {
        const row = document.createElement('div');
        row.className = 'table-row';
        row.innerHTML = `
            <div class="table-cell" style="width: 40px; display:flex; align-items:center;">
                <input type="checkbox" class="company-checkbox" data-company-id="${company.id}" />
            </div>
            <div class="table-cell company-name">
                <div class="company-info">
                    <div class="company-name-text">${company.name || 'Unknown Company'}</div>
                    <div class="company-domain">
                        ${company.domain ? 
                            `<a href="https://${company.domain}" target="_blank" class="domain-link" title="Visit ${company.domain}">${company.domain}</a>` : 
                            '<span class="no-domain">No domain available</span>'
                        }
                    </div>
                </div>
            </div>
            <div class="table-cell industry">
                <span class="industry-tag">${company.industry || 'Unknown Industry'}</span>
            </div>
            <div class="table-cell size">
                <span class="employee-count">${company.employee_count ? `${company.employee_count}+` : 'Unknown'}</span>
            </div>
            <div class="table-cell location">
                <span class="location-tag">${company.location || 'Unknown Location'}</span>
            </div>
            <div class="table-cell lead-score">
                <div class="score-container">
                    <div class="score-bar">
                        <div class="score-fill" style="width: ${Math.min((company.lead_score || 0) * 10, 100)}%"></div>
                    </div>
                    <span class="score-text">${company.lead_score || 0}</span>
                </div>
            </div>
            <div class="table-cell status">
                <span class="status-badge ${company.is_qualified_lead ? 'qualified' : 'not-qualified'}">
                    ${company.is_qualified_lead ? '✅ Qualified' : '❌ Not Qualified'}
                </span>
            </div>
            <div class="table-cell actions">
                <button class="btn btn-secondary btn-sm" onclick="viewCompany(${company.id})" title="View company details">
                    <span class="btn-icon">👁️</span>
                    <span class="btn-text">View</span>
                </button>
                <button class="btn btn-primary btn-sm" id="scoreBtn-${company.id}" onclick="scoreCompanyTwoStep(${company.id})" title="Score (Enrich + Lead Scoring)" style="margin-left: 8px;">
                    <span class="btn-icon">🧮</span>
                    <span class="btn-text">Score</span>
                </button>
                ${company.lead_scored_at ? 
                    `<button class="btn ${company.tenant_id ? 'btn-success' : 'btn-primary'} btn-sm" id="tenantBtn-${company.id}" onclick="createTenantForCompany(${company.id})" title="${company.tenant_id ? 'Tenant Created - Click to recreate' : 'Create Tenant'}" style="margin-left: 8px;">
                        <span class="btn-icon">${company.tenant_id ? '✅' : '🏢'}</span>
                        <span class="btn-text">${company.tenant_id ? 'Tenant Created' : 'Create Tenant'}</span>
                    </button>` : 
                    ''
                }
            </div>
        `;
        tableBody.appendChild(row);
    });

    // Wire up selection behavior
    wireSelectionControls();
}

// Selection controls for batch actions
function wireSelectionControls() {
    const selectAll = document.getElementById('selectAllCompanies');
    const deleteBtn = document.getElementById('deleteSelected');
    const checkboxes = Array.from(document.querySelectorAll('.company-checkbox'));
    if (!selectAll || !deleteBtn || checkboxes.length === 0) return;

    const updateDeleteState = () => {
        const anySelected = checkboxes.some(cb => cb.checked);
        deleteBtn.disabled = !anySelected;
    };

    selectAll.onchange = () => {
        checkboxes.forEach(cb => cb.checked = selectAll.checked);
        updateDeleteState();
    };
    checkboxes.forEach(cb => cb.onchange = updateDeleteState);

    deleteBtn.onclick = async () => {
        const ids = checkboxes.filter(cb => cb.checked).map(cb => parseInt(cb.dataset.companyId));
        if (ids.length === 0) return;
        if (!confirm(`Delete ${ids.length} companies and all associated data? This cannot be undone.`)) return;
        try {
            deleteBtn.disabled = true;
            deleteBtn.textContent = '🗑️ Deleting...';
            const resp = await fetch('/api/companies/delete-batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ company_ids: ids, hard: true })
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || `HTTP ${resp.status}`);
            }
            showToast(`✅ Deleted ${ids.length} companies`, 'success');
            // Reload current page
            loadCompanies(currentPage, currentFilters);
        } catch (e) {
            console.error('delete-batch error:', e);
            showToast(`❌ Failed to delete: ${e.message}`, 'error');
        } finally {
            deleteBtn.disabled = false;
            deleteBtn.textContent = '🗑️ Delete Selected';
        }
    };
}

// Update pagination controls
function updatePagination(total, currentPage) {
    const totalPages = Math.ceil(total / companiesPerPage);
    const paginationInfo = document.getElementById('paginationInfo');
    const prevButton = document.getElementById('prevPage');
    const nextButton = document.getElementById('nextPage');
    const pageNumbers = document.getElementById('pageNumbers');
    
    // Update info
    const start = (currentPage - 1) * companiesPerPage + 1;
    const end = Math.min(currentPage * companiesPerPage, total);
    paginationInfo.textContent = `Showing ${start}-${end} of ${total} companies`;
    
    // Update buttons
    prevButton.disabled = currentPage <= 1;
    nextButton.disabled = currentPage >= totalPages;
    
    // Generate page numbers
    pageNumbers.innerHTML = '';
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageButton = document.createElement('button');
        pageButton.textContent = i;
        pageButton.className = i === currentPage ? 'active' : '';
        pageButton.onclick = () => loadCompanies(i, currentFilters);
        pageNumbers.appendChild(pageButton);
    }
}

// Update company statistics
function updateCompanyStats(total) {
    document.getElementById('totalCompaniesCount').textContent = total;
    
    // Get qualified leads count
    fetch('/api/companies?is_qualified_lead=true&limit=1')
        .then(response => response.json())
        .then(data => {
            document.getElementById('qualifiedLeadsCount').textContent = data.total || 0;
        })
        .catch(error => {
            console.error('Error getting qualified leads count:', error);
            document.getElementById('qualifiedLeadsCount').textContent = '0';
        });
}

// Show/hide loading state
function showLoadingState() {
    document.getElementById('loadingState').style.display = 'flex';
    document.getElementById('emptyState').style.display = 'none';
}

function hideLoadingState() {
    document.getElementById('loadingState').style.display = 'none';
}

// Show empty state
function showEmptyState(message) {
    const emptyState = document.getElementById('emptyState');
    const loadingState = document.getElementById('loadingState');
    const tableBody = document.getElementById('companyTableBody');
    
    loadingState.style.display = 'none';
    tableBody.innerHTML = '';
    
    emptyState.querySelector('p').textContent = message;
    emptyState.style.display = 'block';
}

// Apply filters
function applyFilters() {
    console.log('applyFilters called');
    
    const searchTerm = document.getElementById('searchTerm');
    const industryFilter = document.getElementById('industryFilter');
    const sourceFilter = document.getElementById('sourceFilter');
    const minEmployees = document.getElementById('minEmployees');
    const maxEmployees = document.getElementById('maxEmployees');
    const leadStatusFilter = document.getElementById('leadStatusFilter');
    const atsStatusFilter = document.getElementById('atsStatusFilter');
    
    console.log('Filter elements found:', {
        searchTerm: !!searchTerm,
        industryFilter: !!industryFilter,
        sourceFilter: !!sourceFilter,
        minEmployees: !!minEmployees,
        maxEmployees: !!maxEmployees,
        leadStatusFilter: !!leadStatusFilter,
        atsStatusFilter: !!atsStatusFilter
    });
    
    const filters = {
        search_term: searchTerm ? searchTerm.value : '',
        industry: industryFilter ? industryFilter.value : '',
        source: sourceFilter ? sourceFilter.value : '',
        min_employees: minEmployees ? minEmployees.value : '',
        max_employees: maxEmployees ? maxEmployees.value : '',
        is_qualified_lead: leadStatusFilter ? leadStatusFilter.value : '',
        has_ats_data: atsStatusFilter ? atsStatusFilter.value : ''
    };
    
    console.log('Filters object:', filters);
    
    // Remove empty filters
    Object.keys(filters).forEach(key => {
        if (!filters[key]) delete filters[key];
    });
    
    console.log('Final filters:', filters);
    
    // Update current filters before loading
    currentFilters = filters;
    
    // Reset to first page and load companies
    currentPage = 1;
    loadCompanies(1, filters);
}

// Clear filters
function clearFilters() {
    // Clear all filter inputs
    document.getElementById('searchTerm').value = '';
    document.getElementById('industryFilter').value = '';
    document.getElementById('sourceFilter').value = '';
    document.getElementById('minEmployees').value = '';
    document.getElementById('maxEmployees').value = '';
    document.getElementById('leadStatusFilter').value = '';
    document.getElementById('atsStatusFilter').value = '';
    
    // Reset filters and reload
    currentFilters = {};
    currentPage = 1;
    loadCompanies(1, {});
}

// Refresh companies
function refreshCompanies() {
    loadCompanies(currentPage, currentFilters);
}

// Load filter options
async function loadFilterOptions() {
    try {
        // Load industries
        const industriesResponse = await fetch('/api/companies?limit=1000');
        const industriesData = await industriesResponse.json();
        const industries = [...new Set(industriesData.companies.map(c => c.industry).filter(Boolean))];
        
        const industryFilter = document.getElementById('industryFilter');
        industries.forEach(industry => {
            const option = document.createElement('option');
            option.value = industry;
            option.textContent = industry;
            industryFilter.appendChild(option);
        });
        
        // Load sources
        const sources = [...new Set(industriesData.companies.map(c => c.source).filter(Boolean))];
        const sourceFilter = document.getElementById('sourceFilter');
        sources.forEach(source => {
            const option = document.createElement('option');
            option.value = source;
            option.textContent = source;
            sourceFilter.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading filter options:', error);
    }
}

// Toggle Add Companies Menu
function toggleAddCompaniesMenu() {
    const addMenu = document.getElementById('addCompaniesMenu');
    if (addMenu.style.display === 'none' || addMenu.style.display === '') {
        addMenu.style.display = 'flex';
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    } else {
        addMenu.style.display = 'none';
        document.body.style.overflow = 'auto'; // Restore scrolling
    }
}

// Close Add Companies Menu
function closeAddCompaniesMenu() {
    const addMenu = document.getElementById('addCompaniesMenu');
    addMenu.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// View company details
async function viewCompany(companyId) {
    try {
        // Show loading state
        showToast('Loading company details...', 'info');
        
        // Fetch company details
        const response = await fetch(`/api/companies/${companyId}`);
        if (!response.ok) {
            throw new Error(`Failed to load company: ${response.status} ${response.statusText}`);
        }
        
        const company = await response.json();
        
        // Debug: Log company data to console
        console.log('Company data:', company);
        console.log('Available fields:', Object.keys(company));
        
        // Show company details modal
        showCompanyDetailsModal(company);
        
    } catch (error) {
        console.error('Error loading company details:', error);
        showToast(`❌ Failed to load company details: ${error.message}`, 'error');
    }
}

// Show company details modal
function showCompanyDetailsModal(company) {
    // Remove existing modal if any
    const existingModal = document.getElementById('companyDetailsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Create modal
    const modal = document.createElement('div');
    modal.id = 'companyDetailsModal';
    modal.className = 'company-details-modal';
    modal.innerHTML = `
        <div class="modal-overlay" onclick="closeCompanyDetailsModal()"></div>
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">
                    <h2>${company.name || 'Unknown Company'}</h2>
                    <div class="company-subtitle">
                        ${company.domain ? 
                            `<a href="https://${company.domain}" target="_blank" class="domain-link">${company.domain}</a>` : 
                            '<span class="no-domain">No domain available</span>'
                        }
                    </div>
                </div>
                <button class="modal-close-btn" onclick="closeCompanyDetailsModal()">×</button>
            </div>
            
            <div class="modal-body">
                <!-- Overview Row -->
                <div class="info-section">
                    <h3 class="section-title">📊 Company Overview</h3>
                    <div class="info-grid">
                        <div class="info-item">
                            <label>Industry</label>
                            <span class="industry-tag">${company.industry || 'Unknown Industry'}</span>
                        </div>
                        <div class="info-item">
                            <label>Location</label>
                            <span class="location-tag">${company.location || 'Unknown Location'}</span>
                        </div>
                        <div class="info-item">
                            <label>Employees</label>
                            <span class="employee-count">${company.employee_count ? company.employee_count + '+' : 'Unknown'}</span>
                        </div>
                        <div class="info-item">
                            <label>Data Source</label>
                            <span class="source-tag">${company.source || 'Unknown'}</span>
                        </div>
                    </div>
                </div>

                <!-- Lead Score Summary -->
                <div class="info-section">
                    <h3 class="section-title">🧮 Lead Score</h3>
                    <div class="info-grid">
                        <div class="info-item" style="grid-column: span 2;">
                            <div class="score-display">
                                <div class="score-bar-large">
                                    <div class="score-fill" style="width: ${Math.min(Math.round(((company.lead_score || 0) / 400) * 100), 100)}%"></div>
                                </div>
                                <span class="score-text-large">${company.lead_score || 0}/400</span>
                            </div>
                        </div>
                        <div class="info-item">
                            <label>Status</label>
                            <span class="status-badge ${company.is_qualified_lead ? 'qualified' : 'not-qualified'}">
                                ${company.is_qualified_lead ? '✅ Qualified Lead' : '❌ Not Qualified'}
                            </span>
                        </div>
                        <div class="info-item">
                            <label>Last Scored</label>
                            <span>${company.lead_scored_at ? new Date(company.lead_scored_at).toLocaleString() : 'Not yet scored'}</span>
                        </div>
                        ${company.tenant_id ? 
                            `<div class="info-item">
                                <label>Tenant ID</label>
                                <span style="font-family: monospace; background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px;">${company.tenant_id}</span>
                            </div>
                            <div class="info-item">
                                <label>Tenant Created</label>
                                <span>${company.tenant_created_at ? new Date(company.tenant_created_at).toLocaleString() : 'Unknown'}</span>
                            </div>` : 
                            ''
                        }
                    </div>
                    <div class="info-grid" style="margin-top: 8px;">
                        <div class="info-item">
                            <label>Support Intensity</label>
                            <span>${company.support_intensity_score ?? 0}</span>
                        </div>
                        <div class="info-item">
                            <label>Growth Signals</label>
                            <span>${company.growth_signals_score ?? 0}</span>
                        </div>
                        <div class="info-item">
                            <label>Implementation Feasibility</label>
                            <span>${company.implementation_feasibility_score ?? 0}</span>
                        </div>
                        <div class="info-item">
                            <label>Digital Presence</label>
                            <span>${company.digital_presence_score ?? 0}</span>
                        </div>
                    </div>
                </div>
                
                <!-- Lead Scoring Analysis -->
                <div class="info-section">
                    <h3 class="section-title">📝 Lead Scoring Analysis</h3>
                    <div id="leadScoringAnalysis-${company.id}" class="lead-scoring-analysis">
                        ${generateLeadScoringAnalysisHTML(company.lead_scoring_data)}
                    </div>
                </div>
                
                <!-- Enriched Data -->
                <div class="info-section">
                    <h3 class="section-title">🔍 Enriched Data</h3>
                    <div class="enriched-data">
                        ${generateEnrichedDataHTML(company)}
                    </div>
                </div>
                
                <!-- Lead Scoring Status (live) will be injected below -->
                
                <!-- Job Postings -->
                <div class="info-section">
                    <h3 class="section-title">💼 Job Postings</h3>
                    <div class="job-postings" id="jobPostings-${company.id}">
                        <div class="loading-jobs">Loading job postings...</div>
                    </div>
                </div>
                
                <!-- Company Logs -->
                <div class="info-section">
                    <h3 class="section-title">📝 Activity Logs</h3>
                    <div class="activity-logs" id="activityLogs-${company.id}">
                        <div class="loading-logs">Loading activity logs...</div>
                    </div>
                </div>
            </div>
            
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeCompanyDetailsModal()">Close</button>
                <button class="btn btn-primary" id="scoreLeadBtn-${company.id}" onclick="scoreCompanyTwoStep(${company.id})">
                    🧮 Score (Enrich + Lead)
                </button>
                ${company.domain ? 
                    `<button class="btn btn-success" onclick="window.open('https://${company.domain}', '_blank')">
                        🌐 Visit Website
                    </button>` : ''
                }
                ${company.lead_scored_at ? 
                    `<button class="btn ${company.tenant_id ? 'btn-success' : 'btn-primary'}" id="createTenantBtn-${company.id}" onclick="createTenantForCompany(${company.id})">
                        ${company.tenant_id ? '✅ Tenant Created' : '🏢 Create Tenant'}
                    </button>` : 
                    ''
                }
            </div>
        </div>
    `;
    
    // Add to page
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    
    // Show modal with animation
    setTimeout(() => modal.classList.add('show'), 100);
    
    // Load additional data
    loadJobPostings(company.id);
    loadActivityLogs(company.id);

    // Prepare lead scoring status area
    ensureLeadScoringStatusArea(company.id);
}

// Generate enriched data HTML
function generateEnrichedDataHTML(company) {
    // Define all possible enriched fields with their labels
    const enrichedFieldMap = {
        'description': 'Description',
        'company_description': 'Description',
        'founded_year': 'Founded Year',
        'founded': 'Founded Year',
        'revenue': 'Revenue',
        'annual_revenue': 'Annual Revenue',
        'funding': 'Funding',
        'total_funding': 'Total Funding',
        'ceo': 'CEO',
        'ceo_name': 'CEO',
        'headquarters': 'Headquarters',
        'hq_location': 'Headquarters',
        'tech_stack': 'Technology Stack',
        'technology_stack': 'Technology Stack',
        'technologies': 'Technologies',
        'social_media': 'Social Media',
        'linkedin_url': 'LinkedIn',
        'twitter_url': 'Twitter',
        'facebook_url': 'Facebook',
        'website': 'Website',
        'phone': 'Phone',
        'email': 'Email',
        'contact_email': 'Contact Email',
        'company_type': 'Company Type',
        'business_model': 'Business Model',
        'key_people': 'Key People',
        'specialties': 'Specialties',
        'tags': 'Tags',
        'keywords': 'Keywords'
    };
    
    // Find enriched data by checking all possible field names
    const enrichedData = [];
    
    // Check all company properties for enriched data
    for (const [key, value] of Object.entries(company)) {
        // Skip basic and system fields already shown elsewhere in the modal
        const basicFields = [
            'id', 'name', 'domain', 'industry', 'location', 'employee_count', 'lead_score', 'is_qualified_lead', 'source', 'created_at', 'updated_at',
            // System/state fields
            'is_active', 'last_scrape_status', 'ats_scraped', 'ats_scraped_at',
            // Lead scoring fields (shown in summary section)
            'support_intensity_score', 'digital_presence_score', 'growth_signals_score', 'implementation_feasibility_score', 'lead_scoring_data', 'lead_scored_at',
            // Counting fields not needed here
            'support_roles_count', 'sales_roles_count', 'ai_roles_count'
        ];
        
        if (basicFields.includes(key) || !value || value === 'null' || value === null || value === '') {
            continue;
        }
        
        // Get label from map or format the key
        const label = enrichedFieldMap[key] || formatFieldLabel(key);
        
        // Format the value
        const formattedValue = formatFieldValue(value);
        
        if (formattedValue && formattedValue.length > 0) {
            enrichedData.push({
                label: label,
                value: formattedValue
            });
        }
    }
    
    // If no enriched data found, show the empty state
    if (enrichedData.length === 0) {
        return `
            <div class="no-enriched-data">
                <div class="no-data-icon">🔍</div>
                <p>No enriched data available yet.</p>
                <p class="no-data-subtitle">Click "Enrich Data" to gather additional company information.</p>
            </div>
        `;
    }
    
    // Generate HTML for enriched data
    return enrichedData.map(field => `
        <div class="enriched-item">
            <label>${field.label}</label>
            <div class="enriched-value">${field.value}</div>
        </div>
    `).join('');
}

// Generate readable lead scoring analysis from stored data
function generateLeadScoringAnalysisHTML(data) {
    try {
        if (!data) return `<div class="no-data">No detailed scoring analysis available yet.</div>`;
        // If backend stored JSON, ensure it's an object
        const obj = typeof data === 'string' ? JSON.parse(data) : data;
        const sections = [
            { key: 'support_infrastructure', label: 'Support Infrastructure' },
            { key: 'kb_depth', label: 'Knowledge Base Depth' },
            { key: 'post_purchase', label: 'Post-purchase Signals' },
            { key: 'support_tooling', label: 'Support Tooling' },
            { key: 'review_complaints', label: 'Review Complaints' },
            { key: 'sitemap_density', label: 'Sitemap Density' },
            { key: 'faq_richness', label: 'FAQ Richness' },
            { key: 'traffic_scale', label: 'Traffic Scale' },
            { key: 'catalog_size', label: 'Catalog Size' },
            { key: 'hiring_velocity', label: 'Hiring Velocity' },
            { key: 'headcount_growth', label: 'Headcount Growth' },
            { key: 'recent_funding', label: 'Recent Funding' },
            { key: 'tech_team_size', label: 'Tech Team Size' },
            { key: 'ai_roles', label: 'AI Roles' },
            { key: 'existing_bots', label: 'Existing Bots' },
            { key: 'chat_readiness', label: 'Chat Readiness' }
        ];

        const cards = sections.map(({ key, label }) => {
            const item = obj[key];
            if (!item) return '';
            const score = item.score ?? '-';
            const reasoning = item.reasoning || 'No reasoning provided.';
            const extras = Object.entries(item)
                .filter(([k]) => !['score', 'reasoning'].includes(k))
                .map(([k, v]) => {
                    const pretty = typeof v === 'object' ? `<pre class="json-inline">${escapeHtml(JSON.stringify(v, null, 2))}</pre>` : String(v);
                    return `<div class="kv"><span class="k">${formatFieldLabel(k)}:</span><span class="v">${pretty}</span></div>`;
                }).join('');
            return `
                <div class="analysis-card">
                    <div class="analysis-header">
                        <div class="analysis-title">${label}</div>
                        <div class="analysis-score">Score: <strong>${score}</strong></div>
                    </div>
                    <div class="analysis-reasoning">${escapeHtml(reasoning)}</div>
                    ${extras ? `<div class="analysis-extras">${extras}</div>` : ''}
                </div>
            `;
        }).join('');

        return cards || `<div class="no-data">No detailed scoring analysis available yet.</div>`;
    } catch (e) {
        console.error('Error rendering lead scoring analysis:', e);
        return `<div class="error-state">Failed to render analysis</div>`;
    }
}

// Ensure lead scoring status area exists in modal
function ensureLeadScoringStatusArea(companyId) {
    const modal = document.getElementById('companyDetailsModal');
    if (!modal) return;
    let status = modal.querySelector(`#leadScoringStatus-${companyId}`);
    if (!status) {
        const container = document.createElement('div');
        container.className = 'info-section';
        container.innerHTML = `
            <h3 class="section-title">🧮 Lead Scoring Status</h3>
            <div id="leadScoringStatus-${companyId}" class="lead-scoring-status">
                <div class="phase-line"><span class="phase-badge">Idle</span></div>
            </div>
        `;
        const body = modal.querySelector('.modal-body');
        body.appendChild(container);
    }
}

// Start lead scoring for a company
async function startLeadScoring(companyId) {
    try {
        const btn = document.getElementById(`scoreLeadBtn-${companyId}`);
        if (btn) {
            btn.disabled = true;
            btn.textContent = '🧮 Scoring...';
        }
        const resp = await fetch(`/api/companies/${companyId}/score`, { method: 'POST' });
        if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
        const data = await resp.json();
        currentTaskId = data.task_id;
        showToast(`🧮 Lead scoring started for company ${companyId}`, 'success');
    } catch (e) {
        console.error('startLeadScoring error:', e);
        showToast(`❌ Failed to start lead scoring: ${e.message}`, 'error');
        const btn = document.getElementById(`scoreLeadBtn-${companyId}`);
        if (btn) {
            btn.disabled = false;
            btn.textContent = '🧮 Score Lead';
        }
    }
}

// Update UI with lead scoring phase
function updateLeadScoringPhase({ company_id, phase, index, total }) {
    const status = document.getElementById(`leadScoringStatus-${company_id}`);
    if (!status) return;
    const phasesMap = {
        support_infrastructure: 'Support Infrastructure',
        kb_depth: 'Knowledge Base Depth',
        post_purchase: 'Post-purchase Signals',
        support_tooling: 'Support Tooling',
        review_complaints: 'Review Complaints',
        sitemap_density: 'Sitemap Density',
        faq_richness: 'FAQ Richness',
        traffic_scale: 'Traffic Scale',
        catalog_size: 'Catalog Size',
        hiring_velocity: 'Hiring Velocity',
        headcount_growth: 'Headcount Growth',
        recent_funding: 'Recent Funding',
        tech_team_size: 'Tech Team Size',
        ai_roles: 'AI Roles',
        existing_bots: 'Existing Bots',
        chat_readiness: 'Chat Readiness'
    };
    const human = phasesMap[phase] || phase;
    status.innerHTML = `
        <div class="phase-line">
            <span class="phase-badge">${index + 1} / ${total}</span>
            <span class="phase-text">${human}</span>
        </div>
    `;
}

// Helper function to format field labels
function formatFieldLabel(key) {
    return key
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase())
        .replace(/Url$/, 'URL')
        .replace(/Api$/, 'API')
        .replace(/Ceo$/, 'CEO')
        .replace(/Hq$/, 'HQ');
}

// Helper function to format field values
function formatFieldValue(value) {
    if (!value || value === 'null' || value === null) {
        return '';
    }
    
    // Convert to string
    // Objects and arrays should be shown as pretty JSON
    if (typeof value === 'object') {
        try {
            return `<pre class="json-block">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
        } catch (e) {
            // Fall through to string handling
        }
    }
    let strValue = String(value).trim();
    
    // Handle URLs
    if (strValue.startsWith('http://') || strValue.startsWith('https://')) {
        const domain = strValue.replace(/^https?:\/\//, '').replace(/\/$/, '');
        return `<a href="${strValue}" target="_blank" class="enriched-link">${domain}</a>`;
    }
    
    // Handle email addresses
    if (strValue.includes('@') && strValue.includes('.')) {
        return `<a href="mailto:${strValue}" class="enriched-link">${strValue}</a>`;
    }
    
    // Handle phone numbers
    if (/^\+?[\d\s\-\(\)]{10,}$/.test(strValue)) {
        return `<a href="tel:${strValue.replace(/\D/g, '')}" class="enriched-link">${strValue}</a>`;
    }
    
    // Handle arrays or JSON strings
    if (strValue.startsWith('[') || strValue.startsWith('{')) {
        try {
            const parsed = JSON.parse(strValue);
            if (Array.isArray(parsed)) {
                return `<pre class="json-block">${escapeHtml(JSON.stringify(parsed, null, 2))}</pre>`;
            } else if (typeof parsed === 'object') {
                return `<pre class="json-block">${escapeHtml(JSON.stringify(parsed, null, 2))}</pre>`;
            }
        } catch (e) {
            // If parsing fails, return as is
        }
    }
    
    // Limit very long text
    if (strValue.length > 500) {
        return strValue.substring(0, 500) + '...';
    }
    
    return strValue;
}

// Simple HTML escape for safe <pre> rendering
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Close company details modal
function closeCompanyDetailsModal() {
    const modal = document.getElementById('companyDetailsModal');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = 'auto';
        setTimeout(() => modal.remove(), 300);
    }
}

// Load job postings for company
async function loadJobPostings(companyId) {
    try {
        const response = await fetch(`/api/companies/${companyId}/jobs`);
        if (!response.ok) {
            throw new Error(`Failed to load job postings: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Job postings response:', data);
        
        const container = document.getElementById(`jobPostings-${companyId}`);
        if (!container) return;
        
        // Handle different response formats
        let jobs = [];
        if (data && typeof data === 'object') {
            if (Array.isArray(data)) {
                jobs = data;
            } else if (data.jobs && Array.isArray(data.jobs)) {
                jobs = data.jobs;
            } else if (data.data && Array.isArray(data.data)) {
                jobs = data.data;
            } else if (data.results && Array.isArray(data.results)) {
                jobs = data.results;
            } else {
                console.warn('Unexpected job postings response format:', data);
                jobs = [];
            }
        }
        
        if (jobs && jobs.length > 0) {
            container.innerHTML = jobs.map(job => `
                <div class="job-item">
                    <div class="job-header">
                        <h4 class="job-title">${job.title || 'Untitled Position'}</h4>
                        <span class="job-date">${job.posted_date || job.created_at || 'Unknown Date'}</span>
                    </div>
                    <div class="job-details">
                        <span class="job-location">📍 ${job.location || 'Location not specified'}</span>
                        <span class="job-type">💼 ${job.job_type || 'Full-time'}</span>
                    </div>
                    <p class="job-description">${job.description || 'No description available'}</p>
                    ${job.apply_url ? `<a href="${job.apply_url}" target="_blank" class="job-link">Apply Now</a>` : ''}
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div class="no-data">
                    <div class="no-data-icon">💼</div>
                    <p>No job postings found for this company.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading job postings:', error);
        const container = document.getElementById(`jobPostings-${companyId}`);
        if (container) {
            container.innerHTML = `
                <div class="error-state">
                    <div class="error-icon">❌</div>
                    <p>Failed to load job postings</p>
                    <small>${error.message}</small>
                </div>
            `;
        }
    }
}

// Load activity logs for company
async function loadActivityLogs(companyId) {
    try {
        const response = await fetch(`/api/companies/${companyId}/logs`);
        if (!response.ok) {
            throw new Error(`Failed to load activity logs: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Activity logs response:', data);
        
        const container = document.getElementById(`activityLogs-${companyId}`);
        if (!container) return;
        
        // Handle different response formats
        let logs = [];
        if (data && typeof data === 'object') {
            if (Array.isArray(data)) {
                logs = data;
            } else if (data.logs && Array.isArray(data.logs)) {
                logs = data.logs;
            } else if (data.data && Array.isArray(data.data)) {
                logs = data.data;
            } else if (data.results && Array.isArray(data.results)) {
                logs = data.results;
            } else {
                console.warn('Unexpected activity logs response format:', data);
                logs = [];
            }
        }
        
        if (logs && logs.length > 0) {
            container.innerHTML = logs.map(log => `
                <div class="log-item">
                    <div class="log-header">
                        <span class="log-type ${log.log_type || 'info'}">${log.log_type || 'info'}</span>
                        <span class="log-date">${log.timestamp ? new Date(log.timestamp).toLocaleString() : 'Unknown Date'}</span>
                    </div>
                    <div class="log-message">${log.message || 'No message available'}</div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div class="no-data">
                    <div class="no-data-icon">📝</div>
                    <p>No activity logs found for this company.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading activity logs:', error);
        const container = document.getElementById(`activityLogs-${companyId}`);
        if (container) {
            container.innerHTML = `
                <div class="error-state">
                    <div class="error-icon">❌</div>
                    <p>Failed to load activity logs</p>
                    <small>${error.message}</small>
                </div>
            `;
        }
    }
}

// Enrich company data using OpenAI
async function enrichCompany(companyId) {
    try {
        const button = event.target;
        const originalText = button.textContent;
        
        // Disable button and show loading state
        button.disabled = true;
        button.textContent = '🔍 Enriching...';
        button.style.opacity = '0.6';
        
        // Start enrichment
        const response = await fetch(`/api/companies/${companyId}/enrich`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Enrichment started:', data);
        
        // Show success message
        showToast(`✅ Enrichment started for company ${companyId}`, 'success');
        
        // Set up task monitoring
        if (data.task_id) {
            monitorEnrichmentTask(data.task_id, button, originalText);
        } else {
            // Re-enable button after 5 seconds if no task ID
            setTimeout(() => {
                button.disabled = false;
                button.textContent = originalText;
                button.style.opacity = '1';
            }, 5000);
        }
        
    } catch (error) {
        console.error('Enrichment error:', error);
        showToast(`❌ Failed to start enrichment: ${error.message}`, 'error');
        
        // Re-enable button
        const button = event.target;
        button.disabled = false;
        button.textContent = '🔍 Enrich';
        button.style.opacity = '1';
    }
}

// Two-step scoring: 1) Enrich, 2) Lead scoring
async function scoreCompanyTwoStep(companyId) {
    const btn = document.getElementById(`scoreBtn-${companyId}`) || document.getElementById(`scoreLeadBtn-${companyId}`);
    const originalText = btn ? btn.textContent : '';
    try {
        if (btn) {
            btn.disabled = true;
            btn.textContent = '🔍 Enriching...';
        }
        // Step 1: Enrich
        const enrichResp = await fetch(`/api/companies/${companyId}/enrich`, { method: 'POST' });
        if (!enrichResp.ok) throw new Error(`Enrich failed: ${enrichResp.status}`);
        const enrichData = await enrichResp.json();
        if (enrichData.task_id) {
            currentTaskId = enrichData.task_id;
        }
        // Poll enrichment status until completion (up to ~2 min)
        if (enrichData.task_id) {
            const taskId = enrichData.task_id;
            let checks = 0;
            const maxChecks = 60; // 60 * 2s = 120s
            while (checks < maxChecks) {
                checks++;
                try {
                    const st = await fetch(`/api/status/${taskId}`);
                    if (st.ok) {
                        const js = await st.json();
                        if (js.status === 'completed') break;
                        if (js.status === 'failed') throw new Error('Enrichment failed');
                    }
                } catch (e) {
                    // ignore transient errors and continue
                }
                await new Promise(r => setTimeout(r, 2000));
            }
        } else {
            // Fallback small wait if no task id is returned
            await new Promise(resolve => setTimeout(resolve, 3000));
        }
        if (btn) btn.textContent = '🧮 Scoring...';
        // Re-fetch company to confirm domain populated
        try {
            const cmpResp = await fetch(`/api/companies/${companyId}`);
            if (cmpResp.ok) {
                const cmp = await cmpResp.json();
                if (!cmp.domain) {
                    throw new Error('Domain still missing after enrichment');
                }
            }
        } catch (e) {
            showToast('❌ Cannot start lead scoring: company domain is missing. Try enriching again.', 'error');
            return;
        }
        // Step 2: Lead scoring (backend also enforces domain requirement)
        // Extra assertion to log and guard if domain missing
        if (!window.__debug) window.__debug = {};
        window.__debug.lastDomainCheck = { companyId, time: new Date().toISOString() };
        const scoreResp = await fetch(`/api/companies/${companyId}/score`, { method: 'POST' });
        if (!scoreResp.ok) throw new Error(`Score failed: ${scoreResp.status}`);
        const scoreData = await scoreResp.json();
        if (scoreData.task_id) {
            currentTaskId = scoreData.task_id;
        }
        showToast('🧮 Lead scoring started', 'success');
        // Optionally reload companies after a short delay to reflect domain updates
        setTimeout(() => loadCompanies(currentPage, currentFilters), 4000);
    } catch (e) {
        console.error('scoreCompanyTwoStep error:', e);
        showToast(`❌ Scoring failed: ${e.message}`, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText || '🧮 Score';
        }
    }
}

// Score all companies that are not yet scored
async function scoreUnscoredCompanies() {
    const btn = document.getElementById('scoreUnscoredBtn');
    const originalText = btn ? btn.textContent : '';
    try {
        if (!confirm('This will score companies that have not been scored yet. Continue?')) return;
        if (btn) {
            btn.disabled = true;
            btn.textContent = '🧮 Starting...';
        }
        const resp = await fetch('/api/companies/score-unscored', { method: 'POST' });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        if (data.task_id) {
            currentTaskId = data.task_id;
        }
        showToast(`🧮 Scoring started for ${data.companies ? data.companies.length : data.count || ''} companies`, 'success');
    } catch (e) {
        console.error('scoreUnscoredCompanies error:', e);
        showToast(`❌ Failed to start scoring: ${e.message}`, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText || '🧮 Score Unscored';
        }
    }
}

// Monitor enrichment task progress
function monitorEnrichmentTask(taskId, button, originalText) {
    let checkCount = 0;
    const maxChecks = 30; // 30 checks * 2 seconds = 60 seconds timeout
    
    const checkStatus = async () => {
        try {
            checkCount++;
            console.log(`Checking status for task ${taskId}, attempt ${checkCount}/${maxChecks}`);
            
            const response = await fetch(`/api/status/${taskId}`);
            
            if (!response.ok) {
                throw new Error(`Status check failed: ${response.status} ${response.statusText}`);
            }
            
            const task = await response.json();
            console.log(`Task ${taskId} status:`, task);
            
            if (task.status === 'completed') {
                console.log(`Task ${taskId} completed successfully`);
                showToast(`✅ Enrichment completed successfully!`, 'success');
                button.disabled = false;
                button.textContent = originalText;
                button.style.opacity = '1';
                
                // Refresh company list to show updated data
                loadCompanies(1, {});
                
            } else if (task.status === 'failed') {
                console.log(`Task ${taskId} failed`);
                showToast(`❌ Enrichment failed`, 'error');
                button.disabled = false;
                button.textContent = originalText;
                button.style.opacity = '1';
                
            } else if (checkCount >= maxChecks) {
                // Timeout
                console.log(`Task ${taskId} timed out after ${maxChecks} checks`);
                showToast(`⏰ Enrichment timed out - please check logs`, 'error');
                button.disabled = false;
                button.textContent = originalText;
                button.style.opacity = '1';
                
            } else {
                // Still running, check again in 2 seconds
                console.log(`Task ${taskId} still running, checking again in 2 seconds...`);
                setTimeout(checkStatus, 2000);
            }
            
        } catch (error) {
            console.error(`Status check error for task ${taskId}:`, error);
            showToast(`❌ Failed to check enrichment status: ${error.message}`, 'error');
            button.disabled = false;
            button.textContent = originalText;
            button.style.opacity = '1';
        }
    };
    
    // Start monitoring after 1 second
    setTimeout(checkStatus, 1000);
}

// Enrich companies that are missing domains
async function enrichMissingDomains() {
    try {
        if (!confirm('This will enrich up to 10 companies that don\'t have domains. This may take several minutes. Continue?')) {
            return;
        }
        
        const button = document.getElementById('enrichMissingBtn');
        const originalText = button.textContent;
        
        // Disable button and show loading state
        button.disabled = true;
        button.textContent = '🔍 Enriching...';
        button.style.opacity = '0.6';
        
        // Start bulk enrichment
        const response = await fetch('/api/companies/enrich-missing-domains?limit=10', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Bulk enrichment started:', data);
        
        if (data.count === 0) {
            showToast('ℹ️ No companies found without domains', 'info');
            button.disabled = false;
            button.textContent = originalText;
            button.style.opacity = '1';
            return;
        }
        
        // Show success message
        showToast(`✅ Bulk enrichment started for ${data.companies.length} companies`, 'success');
        
        // Set up task monitoring
        if (data.task_id) {
            monitorBulkEnrichmentTask(data.task_id, button, originalText);
        }
        
    } catch (error) {
        console.error('Bulk enrichment error:', error);
        showToast(`❌ Failed to start bulk enrichment: ${error.message}`, 'error');
        
        // Re-enable button
        const button = document.getElementById('enrichMissingBtn');
        button.disabled = false;
        button.textContent = '🔍 Enrich Missing Domains';
        button.style.opacity = '1';
    }
}

// Monitor bulk enrichment task progress
function monitorBulkEnrichmentTask(taskId, button, originalText) {
    const checkStatus = async () => {
        try {
            const response = await fetch(`/api/status/${taskId}`);
            const task = await response.json();
            
            // Update button text with progress
            if (task.status === 'running') {
                button.textContent = `🔍 Enriching... (${task.progress}/${task.total})`;
            }
            
            if (task.status === 'completed') {
                showToast(`✅ Bulk enrichment completed! ${task.leads_found} companies enriched successfully.`, 'success');
                button.disabled = false;
                button.textContent = originalText;
                button.style.opacity = '1';
                
                // Refresh company list to show updated data
                loadCompanies(1, {});
                
            } else if (task.status === 'failed') {
                showToast(`❌ Bulk enrichment failed`, 'error');
                button.disabled = false;
                button.textContent = originalText;
                button.style.opacity = '1';
                
            } else {
                // Still running, check again in 3 seconds
                setTimeout(checkStatus, 3000);
            }
            
        } catch (error) {
            console.error('Bulk status check error:', error);
            button.disabled = false;
            button.textContent = originalText;
            button.style.opacity = '1';
        }
    };
    
    // Start monitoring after 2 seconds
    setTimeout(checkStatus, 2000);
}

// Toast notification system
function showToast(message, type = 'info') {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.toast');
    existingToasts.forEach(toast => toast.remove());
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    // Add to page
    document.body.appendChild(toast);
    
    // Show toast
    setTimeout(() => toast.classList.add('show'), 100);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Handle scraping form submission
async function handleScrapingFormSubmit(e) {
    e.preventDefault();
    
    try {
        const formData = new FormData(e.target);
        const config = {
            max_companies: parseInt(document.getElementById('maxCompanies').value) || 50,
            min_support_roles: parseInt(document.getElementById('minSupportRoles')?.value) || 1,
            max_ai_roles: parseInt(document.getElementById('maxAiRoles')?.value) || 0,
            include_greenhouse: document.getElementById('includeGreenhouse')?.checked || false,
            include_lever: document.getElementById('includeLever')?.checked || false,
            use_seeded_companies: true
        };
        
        // Show progress section
        document.getElementById('progressSection').style.display = 'block';
        document.getElementById('downloadSection').style.display = 'none';
        
        // Start scraping
        const response = await fetch('/api/start-scraping', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        currentTaskId = data.task_id;
        
        // Show success message
        showToast('🚀 Lead generation started successfully!', 'success');
        
    } catch (error) {
        console.error('Error starting scraping:', error);
        showToast(`❌ Failed to start lead generation: ${error.message}`, 'error');
    }
}

// Handle download button click
function handleDownload() {
    if (currentTaskId) {
        window.open(`/api/download/${currentTaskId}`, '_blank');
    } else {
        showToast('❌ No completed task available for download', 'error');
    }
}

// Manual Company Functions
function showManualCompanyForm() {
    // Hide seeding options
    const seedingOptions = document.querySelector('.seeding-options');
    const seedingConfig = document.getElementById('seedingConfig');
    if (seedingOptions) seedingOptions.style.display = 'none';
    if (seedingConfig) seedingConfig.style.display = 'none';
    
    // Show manual company form
    const manualForm = document.getElementById('manualCompanyForm');
    if (manualForm) {
        manualForm.style.display = 'block';
        // Focus on first input
        const firstInput = document.getElementById('companyName');
        if (firstInput) firstInput.focus();
    }
}

function hideManualCompanyForm() {
    // Show seeding options again
    const seedingOptions = document.querySelector('.seeding-options');
    if (seedingOptions) seedingOptions.style.display = 'block';
    
    // Hide manual form
    const manualForm = document.getElementById('manualCompanyForm');
    if (manualForm) {
        manualForm.style.display = 'none';
        // Reset form
        document.getElementById('addCompanyForm').reset();
    }
}

async function handleManualCompanySubmission() {
    const submitBtn = document.getElementById('submitCompanyButton');
    
    try {
        // Get form data
        const companyData = {
            name: document.getElementById('companyName').value.trim(),
            domain: document.getElementById('companyDomain').value.trim(),
            industry: document.getElementById('companyIndustry').value.trim() || null,
            employee_count: parseInt(document.getElementById('companyEmployees').value) || null,
            location: document.getElementById('companyLocation').value.trim() || null,
            founded_year: parseInt(document.getElementById('companyFounded').value) || null,
            linkedin_url: document.getElementById('companyLinkedIn').value.trim() || null,
            source: "manual"
        };

        // Validate required fields
        if (!companyData.name || !companyData.domain) {
            showToast('❌ Please fill in required fields (Company Name and Domain)', 'error');
            return;
        }

        // Clean domain (remove protocol and www)
        companyData.domain = companyData.domain
            .replace(/^https?:\/\//, '')
            .replace(/^www\./, '')
            .toLowerCase();

        // Show loading state
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳ Adding...';

        // Send request to API
        const response = await fetch('/api/companies', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(companyData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to add company');
        }

        const result = await response.json();
        
        // Show success message
        showToast(`✅ Successfully added ${companyData.name}!`, 'success');
        
        // Reset form and close
        document.getElementById('addCompanyForm').reset();
        closeAddCompaniesMenu();
        
        // Refresh the companies list to show the new company
        await loadCompanies(1, currentFilters);
        
        // Update database status
        await checkDatabase();

    } catch (error) {
        console.error('Error adding company:', error);
        showToast(`❌ Failed to add company: ${error.message}`, 'error');
    } finally {
        // Reset button state
        submitBtn.disabled = false;
        submitBtn.textContent = '✅ Add Company';
    }
}

// Tenant Creation Functions

async function createTenantForCompany(companyId) {
    const btn = document.getElementById(`createTenantBtn-${companyId}`) || document.getElementById(`tenantBtn-${companyId}`);
    let originalText = null;
    
    if (btn) {
        btn.disabled = true;
        originalText = btn.textContent || btn.innerHTML;
        btn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">Creating...</span>';
    }
    
    try {
        console.log(`Starting tenant creation for company ${companyId}...`);
        
        const response = await fetch(`/api/companies/${companyId}/create-tenant`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            console.log(`✅ Tenant created successfully! Tenant ID: ${result.tenant_id}`);
            
            // Show success notification
            showNotification(`Tenant created successfully for company! Tenant ID: ${result.tenant_id}`, 'success');
            
            // If control panel URL is available, offer to open it
            if (result.control_panel_url) {
                const openPanel = confirm(`Tenant created successfully!\n\nWould you like to open the control panel?\n\nTenant ID: ${result.tenant_id}`);
                if (openPanel) {
                    window.open(result.control_panel_url, '_blank');
                }
            }
            
            // Refresh the companies list to show updated status
            await loadCompanies();
            
            // If in modal view, close and refresh
            const modal = document.getElementById('companyDetailsModal');
            if (modal && modal.style.display === 'block') {
                closeCompanyDetailsModal();
            }
            
        } else {
            const errorMsg = result.detail || result.message || 'Unknown error occurred';
            console.error(`❌ Failed to create tenant: ${errorMsg}`);
            showNotification(`Failed to create tenant: ${errorMsg}`, 'error');
        }
        
    } catch (error) {
        console.error(`❌ Error creating tenant: ${error.message}`);
        showNotification(`Error creating tenant: ${error.message}`, 'error');
        console.error('Error creating tenant:', error);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText || '<span class="btn-icon">🏢</span><span class="btn-text">Create Tenant</span>';
        }
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">×</button>
    `;
    
    // Add styles if not already present
    if (!document.querySelector('#notification-styles')) {
        const styles = document.createElement('style');
        styles.id = 'notification-styles';
        styles.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 5px;
                color: white;
                font-weight: bold;
                z-index: 10000;
                max-width: 400px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                display: flex;
                align-items: center;
                justify-content: space-between;
                animation: slideIn 0.3s ease-out;
            }
            .notification-success { background-color: #28a745; }
            .notification-error { background-color: #dc3545; }
            .notification-info { background-color: #17a2b8; }
            .notification button {
                background: none;
                border: none;
                color: white;
                font-size: 18px;
                cursor: pointer;
                margin-left: 10px;
            }
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(styles);
    }
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Configuration Functions

function toggleConfigMenu() {
    console.log('Config button clicked');
    const modal = document.getElementById('configModal');
    console.log('Config modal element:', modal);
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('show');
        loadCurrentConfig();
    } else {
        console.error('Config modal not found');
    }
}

function closeConfigModal() {
    const modal = document.getElementById('configModal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300); // Wait for animation
    }
}

async function loadCurrentConfig() {
    try {
        // Load current configuration from backend
        const response = await fetch('/api/config');
        const config = await response.json();
        
        const tenantApiUrlInput = document.getElementById('tenantApiUrl');
        if (tenantApiUrlInput && config.tenant_api_url) {
            tenantApiUrlInput.value = config.tenant_api_url;
        }
        
        // Clear status
        const status = document.getElementById('configStatus');
        if (status) {
            status.textContent = '';
            status.className = '';
        }
    } catch (error) {
        console.error('Error loading config:', error);
        // Fallback to localStorage
        const savedApiUrl = localStorage.getItem('tenantCreationApiUrl') || 'http://localhost:9000/api/v1/external/create-tenant';
        const tenantApiUrlInput = document.getElementById('tenantApiUrl');
        if (tenantApiUrlInput) {
            tenantApiUrlInput.value = savedApiUrl;
        }
    }
}

async function saveConfig() {
    const tenantApiUrlInput = document.getElementById('tenantApiUrl');
    const status = document.getElementById('configStatus');
    
    if (!tenantApiUrlInput || !status) return;
    
    const apiUrl = tenantApiUrlInput.value.trim();
    
    if (!apiUrl) {
        status.textContent = 'API URL is required';
        status.className = 'config-status error';
        return;
    }
    
    // Validate URL format
    try {
        new URL(apiUrl);
    } catch (e) {
        status.textContent = 'Invalid URL format';
        status.className = 'config-status error';
        return;
    }
    
    status.textContent = 'Saving configuration...';
    status.className = 'config-status info';
    
    try {
        // Save to backend
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tenant_api_url: apiUrl
            })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            // Also save to localStorage as backup
            localStorage.setItem('tenantCreationApiUrl', apiUrl);
            
            status.textContent = '✅ Configuration saved successfully!';
            status.className = 'config-status success';
            
            showNotification('Configuration saved successfully!', 'success');
            
            // Close modal after a short delay
            setTimeout(() => {
                closeConfigModal();
            }, 1500);
        } else {
            status.textContent = `❌ Failed to save: ${result.message || 'Unknown error'}`;
            status.className = 'config-status error';
        }
    } catch (error) {
        status.textContent = `❌ Error saving: ${error.message}`;
        status.className = 'config-status error';
    }
}

async function testTenantApi() {
    const tenantApiUrlInput = document.getElementById('tenantApiUrl');
    const status = document.getElementById('configStatus');
    
    if (!tenantApiUrlInput || !status) return;
    
    const apiUrl = tenantApiUrlInput.value.trim();
    
    if (!apiUrl) {
        status.textContent = 'Please enter an API URL to test';
        status.className = 'config-status error';
        return;
    }
    
    status.textContent = 'Testing API connection...';
    status.className = 'config-status info';
    
    try {
        // Test with a dummy request to see if the endpoint exists
        const response = await fetch(apiUrl.replace('/create-tenant', '/health'), {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            status.textContent = '✅ API connection successful!';
            status.className = 'config-status success';
        } else {
            status.textContent = `⚠️ API responded with status ${response.status}`;
            status.className = 'config-status warning';
        }
    } catch (error) {
        status.textContent = `❌ API connection failed: ${error.message}`;
        status.className = 'config-status error';
    }
}

// Update tenant creation function to use configured URL
function getConfiguredTenantApiUrl() {
    return localStorage.getItem('tenantCreationApiUrl') || 'http://localhost:9000/api/v1/external/create-tenant';
}

// Make configuration functions globally available
window.toggleConfigMenu = toggleConfigMenu;
window.closeConfigModal = closeConfigModal;
window.saveConfig = saveConfig;
window.testTenantApi = testTenantApi;

// Utility Functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Open lead crawler in new page
function openLeadCrawler() {
    window.open('/static/lead-crawler.html', '_blank');
}

// Add keyboard event listener for escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('companyDetailsModal');
        if (modal) {
            closeCompanyDetailsModal();
        }
        closeAddCompaniesMenu();
    }
});
