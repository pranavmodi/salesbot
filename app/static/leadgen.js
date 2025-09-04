// Global Variables for Leadgen
let currentPage = 1;
let companiesPerPage = 20;
let currentFilters = {};
let currentCompanyId = null;

// API Configuration
const API_BASE = window.LEADGEN_CONFIG?.apiBaseUrl || '/leadgen/api';

// Initialize the application
function initLeadgen() {
    console.log('Lead Generation Tool initialized');
    loadStats();
    loadCompanies();
    setupEventListeners();
}

// Setup Event Listeners
function setupEventListeners() {
    // Step navigation
    document.querySelectorAll('.step').forEach(step => {
        step.addEventListener('click', () => {
            const stepNumber = step.id.replace('step', '');
            showStep(parseInt(stepNumber));
        });
    });
    
    // Filter events
    document.getElementById('qualifiedOnly')?.addEventListener('change', applyFilters);
    document.getElementById('hasJobs')?.addEventListener('change', applyFilters);
}

// Show specific step
function showStep(stepNumber) {
    // Update navigation
    document.querySelectorAll('.step').forEach(step => step.classList.remove('active'));
    document.getElementById(`step${stepNumber}`).classList.add('active');
    
    // Show/hide sections
    const sections = ['companySection', 'scrapingSection', 'scoringSection', 'exportSection'];
    sections.forEach((section, index) => {
        const element = document.getElementById(section);
        if (element) {
            element.style.display = index === stepNumber - 1 ? 'block' : 'none';
        }
    });
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        if (response.ok) {
            const stats = await response.json();
            document.getElementById('totalCompanies').textContent = stats.total_companies || 0;
            document.getElementById('qualifiedLeads').textContent = stats.qualified_leads || 0;
            document.getElementById('companiesWithJobs').textContent = stats.companies_with_jobs || 0;
            document.getElementById('totalJobs').textContent = stats.total_jobs || 0;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load companies
async function loadCompanies(page = 1) {
    try {
        const params = new URLSearchParams({
            page: page,
            per_page: companiesPerPage,
            ...currentFilters
        });
        
        const response = await fetch(`${API_BASE}/companies?${params}`);
        if (response.ok) {
            const data = await response.json();
            renderCompaniesTable(data.companies);
            renderPagination(data);
            currentPage = page;
        } else {
            console.error('Failed to load companies');
        }
    } catch (error) {
        console.error('Error loading companies:', error);
    }
}

// Render companies table
function renderCompaniesTable(companies) {
    const container = document.getElementById('companiesTable');
    if (!container) return;
    
    if (!companies || companies.length === 0) {
        container.innerHTML = '<div class="no-data">No companies found</div>';
        return;
    }
    
    let html = `
        <table class="companies-table">
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Domain</th>
                    <th>Industry</th>
                    <th>Employees</th>
                    <th>Support Jobs</th>
                    <th>Lead Score</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    companies.forEach(company => {
        const qualifiedBadge = company.is_qualified_lead 
            ? '<span class="badge badge-success">Qualified</span>' 
            : '<span class="badge badge-secondary">Unqualified</span>';
            
        html += `
            <tr onclick="showCompanyDetails(${company.id})">
                <td><strong>${company.name || 'N/A'}</strong></td>
                <td>${company.domain || 'N/A'}</td>
                <td>${company.industry || 'N/A'}</td>
                <td>${company.employee_count || 'N/A'}</td>
                <td>${company.support_roles_count || 0}</td>
                <td>${company.lead_score || 0}</td>
                <td>${qualifiedBadge}</td>
                <td onclick="event.stopPropagation()">
                    <button class="btn btn-sm" onclick="enrichCompany(${company.id})">🔍</button>
                    <button class="btn btn-sm" onclick="scoreCompany(${company.id})">🎯</button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// Render pagination
function renderPagination(data) {
    const container = document.getElementById('companiesPagination');
    if (!container) return;
    
    let html = '<div class="pagination-controls">';
    
    // Previous button
    if (data.page > 1) {
        html += `<button class="btn btn-secondary" onclick="loadCompanies(${data.page - 1})">Previous</button>`;
    }
    
    // Page info
    html += `<span>Page ${data.page} of ${data.pages} (${data.total} total)</span>`;
    
    // Next button
    if (data.page < data.pages) {
        html += `<button class="btn btn-secondary" onclick="loadCompanies(${data.page + 1})">Next</button>`;
    }
    
    html += '</div>';
    container.innerHTML = html;
}

// Apply filters
function applyFilters() {
    currentFilters = {};
    
    if (document.getElementById('qualifiedOnly')?.checked) {
        currentFilters.qualified_only = 'true';
    }
    
    if (document.getElementById('hasJobs')?.checked) {
        currentFilters.has_jobs = 'true';
    }
    
    loadCompanies(1);
}

// Refresh companies
function refreshCompanies() {
    loadStats();
    loadCompanies(currentPage);
}

// Show company details modal
async function showCompanyDetails(companyId) {
    try {
        const response = await fetch(`${API_BASE}/companies/${companyId}`);
        if (response.ok) {
            const company = await response.json();
            renderCompanyModal(company);
            currentCompanyId = companyId;
        }
    } catch (error) {
        console.error('Error loading company details:', error);
    }
}

// Render company modal
function renderCompanyModal(company) {
    const modal = document.getElementById('companyModal');
    const title = document.getElementById('companyModalTitle');
    const body = document.getElementById('companyModalBody');
    
    if (!modal || !title || !body) return;
    
    title.textContent = company.name;
    
    let html = `
        <div class="company-details">
            <div class="detail-row">
                <strong>Domain:</strong> ${company.domain || 'N/A'}
            </div>
            <div class="detail-row">
                <strong>Industry:</strong> ${company.industry || 'N/A'}
            </div>
            <div class="detail-row">
                <strong>Employees:</strong> ${company.employee_count || 'N/A'}
            </div>
            <div class="detail-row">
                <strong>Location:</strong> ${company.location || 'N/A'}
            </div>
            <div class="detail-row">
                <strong>Support Roles:</strong> ${company.support_roles_count || 0}
            </div>
            <div class="detail-row">
                <strong>Sales Roles:</strong> ${company.sales_roles_count || 0}
            </div>
            <div class="detail-row">
                <strong>Lead Score:</strong> ${company.lead_score || 0}
            </div>
            <div class="detail-row">
                <strong>Qualified:</strong> ${company.is_qualified_lead ? 'Yes' : 'No'}
            </div>
        </div>
    `;
    
    if (company.job_postings && company.job_postings.length > 0) {
        html += '<h4>Job Postings</h4>';
        html += '<div class="job-postings">';
        company.job_postings.forEach(job => {
            html += `
                <div class="job-posting">
                    <strong>${job.title}</strong> - ${job.department || 'N/A'}<br>
                    <small>Category: ${job.role_category || 'N/A'} | Source: ${job.ats_source}</small>
                </div>
            `;
        });
        html += '</div>';
    }
    
    body.innerHTML = html;
    modal.style.display = 'block';
}

// Close company modal
function closeCompanyModal() {
    const modal = document.getElementById('companyModal');
    if (modal) {
        modal.style.display = 'none';
    }
    currentCompanyId = null;
}

// Enrich company
async function enrichCompany(companyId) {
    if (!companyId) return;
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/companies/${companyId}/enrich`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                showNotification('Company enriched successfully', 'success');
                refreshCompanies();
            } else {
                showNotification('Failed to enrich company: ' + (result.error || 'Unknown error'), 'error');
            }
        } else {
            showNotification('Failed to enrich company', 'error');
        }
    } catch (error) {
        console.error('Error enriching company:', error);
        showNotification('Error enriching company', 'error');
    } finally {
        hideLoading();
    }
}

// Score company
async function scoreCompany(companyId) {
    if (!companyId) return;
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/companies/${companyId}/score`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                showNotification('Company scored successfully', 'success');
                refreshCompanies();
            } else {
                showNotification('Failed to score company: ' + (result.error || 'Unknown error'), 'error');
            }
        } else {
            showNotification('Failed to score company', 'error');
        }
    } catch (error) {
        console.error('Error scoring company:', error);
        showNotification('Error scoring company', 'error');
    } finally {
        hideLoading();
    }
}

// Enrich current company in modal
function enrichCurrentCompany() {
    if (currentCompanyId) {
        enrichCompany(currentCompanyId);
    }
}

// Score current company in modal
function scoreCurrentCompany() {
    if (currentCompanyId) {
        scoreCompany(currentCompanyId);
    }
}

// Start scraping
async function startScraping() {
    const companyList = document.getElementById('companyList');
    if (!companyList) return;
    
    const companies = companyList.value.split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);
    
    if (companies.length === 0) {
        showNotification('Please enter at least one company name', 'error');
        return;
    }
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/start-scraping`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                companies: companies,
                include_greenhouse: document.getElementById('includeGreenhouse')?.checked || true,
                include_lever: document.getElementById('includeLever')?.checked || true
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification('Scraping started successfully', 'success');
            // TODO: Show progress tracking
            refreshCompanies();
        } else {
            showNotification('Failed to start scraping', 'error');
        }
    } catch (error) {
        console.error('Error starting scraping:', error);
        showNotification('Error starting scraping', 'error');
    } finally {
        hideLoading();
    }
}

// Utility functions
function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

function showNotification(message, type = 'info') {
    // Simple notification implementation
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        z-index: 10000;
        color: white;
        font-weight: 500;
        background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#007bff'};
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Export functions to global scope
window.loadStats = loadStats;
window.loadCompanies = loadCompanies;
window.refreshCompanies = refreshCompanies;
window.applyFilters = applyFilters;
window.showCompanyDetails = showCompanyDetails;
window.closeCompanyModal = closeCompanyModal;
window.enrichCompany = enrichCompany;
window.scoreCompany = scoreCompany;
window.enrichCurrentCompany = enrichCurrentCompany;
window.scoreCurrentCompany = scoreCurrentCompany;
window.startScraping = startScraping;
window.showStep = showStep;

// Auto-initialize if DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLeadgen);
} else {
    initLeadgen();
}