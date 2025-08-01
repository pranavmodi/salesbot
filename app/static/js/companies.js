// SalesBot CRM - Company Management Module

// Global company-related variables
let currentCompanyId = null;

// Initialize company functionality
function initializeCompanies() {
    setupCompanyEventListeners();
    setupCompanySearch();
    setupCompaniesPagination();
}

// Company event listeners
function setupCompanyEventListeners() {
    const researchBtn = document.getElementById('researchCompanies');
    const saveCompanyBtn = document.getElementById('saveCompanyBtn');
    const cleanAllResearchBtn = document.getElementById('cleanAllResearchBtn');
    
    if (researchBtn) {
        researchBtn.addEventListener('click', researchCompanies);
    }
    if (saveCompanyBtn) {
        saveCompanyBtn.addEventListener('click', saveCompany);
    }
    if (cleanAllResearchBtn) {
        cleanAllResearchBtn.addEventListener('click', cleanAllResearch);
    }
    
    // Setup company details modal
    setupCompanyDetailsModal();
    
    // Setup delete and reset company buttons
    setupDeleteResetCompanyButtons();
}

// Setup company details modal functionality
function setupCompanyDetailsModal() {
    console.log('Setting up company details modal...');
    
    // Company details modal event listener - triggered when modal is shown
    const companyDetailModal = document.getElementById('companyDetailModal');
    if (companyDetailModal) {
        console.log('Company detail modal found, adding event listener');
        
        companyDetailModal.addEventListener('show.bs.modal', function(event) {
            console.log('Company modal show event triggered');
            
            // Get the button that triggered the modal
            const button = event.relatedTarget;
            const companyId = button ? button.dataset.companyId : null;
            
            console.log(`Modal triggered for company ID: ${companyId}`);
            
            if (companyId) {
                loadCompanyDetails(companyId);
            } else {
                console.error("No company ID found on button");
                const contentDiv = document.getElementById('company-details-content');
                if (contentDiv) {
                    contentDiv.innerHTML = `
                        <div class="alert alert-danger" role="alert">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Error: No company ID provided
                        </div>
                    `;
                }
            }
        });
    } else {
        console.error('Company detail modal not found');
    }
}

// Company search functionality
function setupCompanySearch() {
    const companySearchInput = document.getElementById('companySearch');
    if (companySearchInput) {
        let companySearchTimeout;
        
        companySearchInput.addEventListener('input', function() {
            const searchTerm = this.value.trim();
            
            if (companySearchTimeout) {
                clearTimeout(companySearchTimeout);
            }
            
            companySearchTimeout = setTimeout(() => {
                performCompanySearch(searchTerm);
            }, 300);
        });
    }
}

function performCompanySearch(searchTerm) {
    const companiesContainer = document.getElementById('companies-table-container');
    const originalContent = companiesContainer.innerHTML;
    
    if (searchTerm === '') {
        changeCompaniesPage(1);
        return;
    }
    
    console.log(`Performing server-side company search: "${searchTerm}"`);
    
    companiesContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Searching companies...</p>
        </div>
    `;
    
    fetch(`/api/companies/search?q=${encodeURIComponent(searchTerm)}`)
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                throw new Error(data.message || 'Failed to search companies');
            }
            
            displayCompanySearchResults(data.companies, searchTerm);
            updateCompanyStats(data.count);
        })
        .catch(error => {
            console.error('Error searching companies:', error);
            companiesContainer.innerHTML = originalContent;
            showToast('errorToast', 'Failed to search companies: ' + error.message);
        });
}

function displayCompanySearchResults(companies, searchTerm) {
    const companiesContainer = document.getElementById('companies-table-container');
    
    if (companies.length === 0) {
        companiesContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-search fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No companies found</h5>
                <p class="text-muted">No companies found matching "${searchTerm}"</p>
                <button class="btn btn-outline-primary mt-3" onclick="clearCompanySearch()">
                    <i class="fas fa-arrow-left me-2"></i>Back to All Companies
                </button>
            </div>
        `;
        return;
    }
    
    let tableHtml = `
        <div class="mb-3">
            <div class="alert alert-info">
                <i class="fas fa-search me-2"></i>
                Found <strong>${companies.length}</strong> companies matching "${searchTerm}"
                <button class="btn btn-outline-primary btn-sm ms-3" onclick="clearCompanySearch()">
                    <i class="fas fa-times me-1"></i>Clear Search
                </button>
            </div>
        </div>
        
        <div class="table-responsive">
            <table class="table table-hover">
                <thead class="table-light">
                    <tr>
                        <th>Company Name</th>
                        <th>Website</th>
                        <th>Research Status</th>
                        <th>Created</th>
                        <th>Updated</th>
                        <th style="width: 120px;">Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    companies.forEach(company => {
        tableHtml += `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="company-avatar me-2">
                            ${company.company_name ? company.company_name[0].toUpperCase() : '?'}
                        </div>
                        <div>
                            <strong>${company.company_name || 'Unknown Company'}</strong>
                            ${company.website_url ? `<br><small class="text-muted">
                                <a href="${company.website_url}" target="_blank" class="text-decoration-none">
                                    <i class="fas fa-external-link-alt me-1"></i>${company.website_url}
                                </a>
                            </small>` : ''}
                        </div>
                    </div>
                </td>
                <td>
                    <span>${company.website_url ? `<a href="${company.website_url}" target="_blank">${company.website_url}</a>` : 'Not specified'}</span>
                </td>
                <td>
                    <span class="badge ${company.company_research ? 'bg-success' : 'bg-warning'}">${company.company_research ? 'Researched' : 'Pending'}</span>
                </td>
                <td>
                    <span class="text-muted">${company.created_at ? new Date(company.created_at).toLocaleDateString() : 'Unknown'}</span>
                </td>
                <td>
                    <span class="text-muted">${company.updated_at ? new Date(company.updated_at).toLocaleDateString() : 'Unknown'}</span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary btn-sm" 
                                onclick="loadCompanyDetails(${company.id})" 
                                title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button type="button" class="btn btn-outline-success btn-sm" 
                                onclick="researchSingleCompany(${company.id}, '${company.company_name}', this)" 
                                title="Research Company">
                            <i class="fas fa-search"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tableHtml += `
                </tbody>
            </table>
        </div>
    `;
    
    companiesContainer.innerHTML = tableHtml;
}

function clearCompanySearch() {
    const companySearchInput = document.getElementById('companySearch');
    if (companySearchInput) {
        companySearchInput.value = '';
    }
    changeCompaniesPage(1);
}

// Company pagination
function setupCompaniesPagination() {
    // Pagination is handled by the changeCompaniesPage function
    console.log('Company pagination setup complete');
}

function changeCompaniesPage(page) {
    addPaginationLoadingState('companies-table-container');
    
    const perPage = 20; // Fixed per page for companies
    const url = `/api/companies?page=${page}&per_page=${perPage}`;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                throw new Error(data.message || 'Failed to load companies');
            }
            
            displayCompaniesTable(data.companies || [], data.pagination || {});
            updateCompanyStats(data.total);
            removePaginationLoadingState('companies-table-container');
        })
        .catch(error => {
            console.error('Error loading companies:', error);
            showToast('errorToast', 'Failed to load companies: ' + error.message);
            removePaginationLoadingState('companies-table-container');
        });
}

function displayCompaniesTable(companies, pagination) {
    const companiesContainer = document.getElementById('companies-table-container');
    
    if (companies.length === 0) {
        companiesContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-building fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Companies Found</h5>
                <p class="text-muted">No companies have been added to the system yet.</p>
            </div>
        `;
        return;
    }
    
    let html = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead class="table-light">
                    <tr>
                        <th>Company Name</th>
                        <th>Website</th>
                        <th>Research Status</th>
                        <th>Created</th>
                        <th>Updated</th>
                        <th style="width: 120px;">Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    companies.forEach(company => {
        html += `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="company-avatar me-2" style="width: 36px; height: 36px; font-size: 0.875rem;">
                            ${company.company_name ? company.company_name[0].toUpperCase() : '?'}
                        </div>
                        <div>
                            <strong>${company.company_name || 'Unknown Company'}</strong>
                            ${company.website_url ? `<br><small class="text-muted">
                                <a href="${company.website_url}" target="_blank" class="text-decoration-none">
                                    <i class="fas fa-external-link-alt me-1"></i>${company.website_url}
                                </a>
                            </small>` : ''}
                        </div>
                    </div>
                </td>
                <td>
                    <span>${company.website_url ? `<a href="${company.website_url}" target="_blank">${company.website_url}</a>` : 'Not specified'}</span>
                </td>
                <td>
                    <span class="badge ${company.company_research ? 'bg-success' : 'bg-warning'}">${company.company_research ? 'Researched' : 'Pending'}</span>
                </td>
                <td>
                    <span class="text-muted">${company.created_at ? new Date(company.created_at).toLocaleDateString() : 'Unknown'}</span>
                </td>
                <td>
                    <span class="text-muted">${company.updated_at ? new Date(company.updated_at).toLocaleDateString() : 'Unknown'}</span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary btn-sm" 
                                onclick="loadCompanyDetails(${company.id})" 
                                title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button type="button" class="btn btn-outline-success btn-sm" 
                                onclick="researchSingleCompany(${company.id}, '${company.company_name}', this)" 
                                title="Research Company">
                            <i class="fas fa-search"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    // Add pagination if needed
    if (pagination.total_pages > 1) {
        html += generateCompaniesPagination(pagination.current_page, pagination.total_pages);
    }
    
    companiesContainer.innerHTML = html;
}

function generateCompaniesPagination(currentPage, totalPages) {
    let paginationHTML = `
        <nav aria-label="Companies pagination" class="mt-4">
            <ul class="pagination justify-content-center">
    `;
    
    // Previous button
    const prevDisabled = currentPage === 1 ? 'disabled' : '';
    paginationHTML += `
        <li class="page-item ${prevDisabled}">
            <a class="page-link" href="#" onclick="changeCompaniesPage(${currentPage - 1})" 
               ${prevDisabled ? 'tabindex="-1" aria-disabled="true"' : ''}>
                <i class="fas fa-chevron-left"></i>
            </a>
        </li>
    `;
    
    // Page numbers
    paginationHTML += generatePageNumbers(currentPage, totalPages, 'companies-page', 'data-page');
    
    // Next button
    const nextDisabled = currentPage === totalPages ? 'disabled' : '';
    paginationHTML += `
        <li class="page-item ${nextDisabled}">
            <a class="page-link" href="#" onclick="changeCompaniesPage(${currentPage + 1})"
               ${nextDisabled ? 'tabindex="-1" aria-disabled="true"' : ''}>
                <i class="fas fa-chevron-right"></i>
            </a>
        </li>
    `;
    
    paginationHTML += `
            </ul>
        </nav>
    `;
    
    return paginationHTML;
}

// Clean all research functionality
function cleanAllResearch() {
    if (!confirm('Are you sure you want to clean ALL research data from ALL companies? This action cannot be undone.')) {
        return;
    }
    
    const cleanBtn = document.getElementById('cleanAllResearchBtn');
    const originalText = cleanBtn.innerHTML;
    
    cleanBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Cleaning...';
    cleanBtn.disabled = true;
    
    fetch('/api/companies/clean-all-research', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', 'All research data has been cleaned successfully!');
            
            // Reload companies to show updated data
            setTimeout(() => {
                changeCompaniesPage(1);
            }, 1000);
        } else {
            throw new Error(data.message || 'Failed to clean research data');
        }
    })
    .catch(error => {
        console.error('Error cleaning research data:', error);
        showToast('errorToast', 'Failed to clean research data: ' + error.message);
    })
    .finally(() => {
        cleanBtn.innerHTML = originalText;
        cleanBtn.disabled = false;
    });
}

// Company research functionality
function researchCompanies() {
    const researchBtn = document.getElementById('researchCompanies');
    const originalText = researchBtn.innerHTML;
    
    researchBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Researching...';
    researchBtn.disabled = true;
    
    fetch('/api/companies/research-all', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', 'Company research started! This may take a few minutes.');
            
            // Optionally reload companies to show updated data
            setTimeout(() => {
                changeCompaniesPage(1);
            }, 2000);
        } else {
            throw new Error(data.message || 'Failed to start company research');
        }
    })
    .catch(error => {
        console.error('Error starting company research:', error);
        showToast('errorToast', 'Failed to start research: ' + error.message);
    })
    .finally(() => {
        researchBtn.innerHTML = originalText;
        researchBtn.disabled = false;
    });
}

function researchSingleCompany(companyId, companyName, buttonElement) {
    const originalText = buttonElement.innerHTML;
    
    buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    buttonElement.disabled = true;
    
    fetch(`/api/companies/${companyId}/research`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `Research completed for ${companyName}!`);
            
            // Reload company details if modal is open
            const modal = document.getElementById('companyModal');
            if (modal && modal.classList.contains('show')) {
                loadCompanyDetails(companyId);
            }
        } else {
            throw new Error(data.message || 'Failed to research company');
        }
    })
    .catch(error => {
        console.error('Error researching company:', error);
        showToast('errorToast', `Failed to research ${companyName}: ` + error.message);
    })
    .finally(() => {
        buttonElement.innerHTML = originalText;
        buttonElement.disabled = false;
    });
}

// Company details and modal management
function loadCompanyDetails(companyId) {
    console.log(`Loading company details for ID: ${companyId}`);
    currentCompanyId = companyId;
    
    // Reset modal content to loading state
    const modalContent = document.getElementById('company-details-content');
    const modalTitle = document.getElementById('companyDetailModalLabel');
    
    if (modalContent) {
        modalContent.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading company details...</p>
            </div>
        `;
    }
    
    if (modalTitle) {
        modalTitle.textContent = 'Loading Company Details...';
    }
    
    fetch(`/api/companies/${companyId}`)
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                throw new Error(data.message || 'Failed to load company details');
            }
            displayCompanyDetails(data.company);
        })
        .catch(error => {
            console.error('Error loading company details:', error);
            if (modalContent) {
                modalContent.innerHTML = `
                    <div class="alert alert-danger" role="alert">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Failed to load company details: ${error.message}
                    </div>
                `;
            }
        });
}

function displayCompanyDetails(company) {
    const modalContent = document.getElementById('company-details-content');
    const modalTitle = document.getElementById('companyDetailModalLabel');
    
    if (!modalContent) {
        console.error('Modal content div not found');
        return;
    }
    
    // Update modal title
    if (modalTitle) {
        modalTitle.textContent = company.company_name || 'Company Details';
    }
    
    // Format the research content
    const researchContent = company.company_research ? 
        company.company_research.replace(/\n/g, '<br>') : 
        '<em class="text-muted">No research available yet. Click the Research button to generate AI-powered insights.</em>';
    
    // Create the company details HTML
    modalContent.innerHTML = `
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h6 class="card-title mb-0">
                            <i class="fas fa-building me-2"></i>Company Information
                        </h6>
                    </div>
                    <div class="card-body">
                        <dl class="row">
                            <dt class="col-4">Name:</dt>
                            <dd class="col-8">${company.company_name || 'N/A'}</dd>
                            
                            <dt class="col-4">Website:</dt>
                            <dd class="col-8">
                                ${company.website_url ? 
                                    `<a href="${company.website_url}" target="_blank" class="text-decoration-none">
                                        ${company.website_url} <i class="fas fa-external-link-alt ms-1"></i>
                                    </a>` : 
                                    'N/A'
                                }
                            </dd>
                            
                            <dt class="col-4">Created:</dt>
                            <dd class="col-8">${company.created_at ? new Date(company.created_at).toLocaleDateString() : 'N/A'}</dd>
                            
                            <dt class="col-4">Updated:</dt>
                            <dd class="col-8">${company.updated_at ? new Date(company.updated_at).toLocaleDateString() : 'N/A'}</dd>
                        </dl>
                        
                        ${company.needs_research ? 
                            `<div class="alert alert-warning mt-3">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                <strong>Research Needed:</strong> This company hasn't been researched yet.
                            </div>` : 
                            `<div class="alert alert-success mt-3">
                                <i class="fas fa-check-circle me-2"></i>
                                <strong>Research Complete:</strong> AI insights available.
                            </div>`
                        }
                    </div>
                </div>
            </div>
            
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h6 class="card-title mb-0">
                            <i class="fas fa-chart-line me-2"></i>Company Research & Insights
                        </h6>
                    </div>
                    <div class="card-body">
                        <div style="max-height: 400px; overflow-y: auto;">
                            ${researchContent}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Show research action buttons
    const researchActions = document.getElementById('companyResearchActions');
    if (researchActions) {
        researchActions.style.display = 'block';
        
        // Set up action buttons
        const deepResearchBtn = document.getElementById('deepResearchModalBtn');
        const triggerResearchBtn = document.getElementById('triggerResearchBtn');
        const forceRefreshBtn = document.getElementById('forceRefreshBtn');
        const viewReportBtn = document.getElementById('viewReportBtn');
        
        if (deepResearchBtn) {
            deepResearchBtn.onclick = () => triggerDeepResearch(company.id, company.company_name);
        }
        
        if (triggerResearchBtn) {
            triggerResearchBtn.onclick = () => triggerQuickResearch(company.id);
        }
        
        if (forceRefreshBtn) {
            forceRefreshBtn.onclick = () => loadCompanyDetails(company.id);
        }
        
        // Show view report button if research is available
        if (viewReportBtn && company.company_research) {
            viewReportBtn.style.display = 'block';
            viewReportBtn.onclick = () => viewCompanyReport(company.id);
        }
    }
}

// Company editing functionality
function toggleCompanyEditMode() {
    const isEditing = document.getElementById('companyNameEdit').classList.contains('d-none');
    
    if (isEditing) {
        // Switch to edit mode
        document.getElementById('companyNameDisplay').classList.add('d-none');
        document.getElementById('companyNameEdit').classList.remove('d-none');
        
        document.getElementById('industryDisplay').classList.add('d-none');
        document.getElementById('industryEdit').classList.remove('d-none');
        
        document.getElementById('websiteDisplay').classList.add('d-none');
        document.getElementById('websiteEdit').classList.remove('d-none');
        
        document.getElementById('locationDisplay').classList.add('d-none');
        document.getElementById('locationEdit').classList.remove('d-none');
        
        document.getElementById('employeeCountDisplay').classList.add('d-none');
        document.getElementById('employeeCountEdit').classList.remove('d-none');
        
        document.getElementById('phoneDisplay').classList.add('d-none');
        document.getElementById('phoneEdit').classList.remove('d-none');
        
        document.getElementById('researchNotesDisplay').classList.add('d-none');
        document.getElementById('researchNotesEdit').classList.remove('d-none');
        
        document.getElementById('editControls').classList.remove('d-none');
        
        document.getElementById('editCompanyBtn').innerHTML = '<i class="fas fa-times me-1"></i>Cancel';
        document.getElementById('editCompanyBtn').onclick = cancelCompanyEdit;
    } else {
        cancelCompanyEdit();
    }
}

function saveCompanyInModal() {
    if (!currentCompanyId) {
        showToast('errorToast', 'No company selected for editing');
        return;
    }
    
    const companyData = {
        name: document.getElementById('companyNameEdit').value.trim(),
        industry: document.getElementById('industryEdit').value.trim(),
        website: document.getElementById('websiteEdit').value.trim(),
        location: document.getElementById('locationEdit').value.trim(),
        employee_count: parseInt(document.getElementById('employeeCountEdit').value) || null,
        phone: document.getElementById('phoneEdit').value.trim(),
        research_notes: document.getElementById('researchNotesEdit').value.trim()
    };
    
    const saveBtn = document.querySelector('[onclick="saveCompanyInModal()"]');
    const originalText = saveBtn.innerHTML;
    
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
    saveBtn.disabled = true;
    
    fetch(`/api/companies/${currentCompanyId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(companyData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', 'Company updated successfully!');
            
            // Reload company details
            loadCompanyDetails(currentCompanyId);
            
            // Reload companies table
            changeCompaniesPage(1);
        } else {
            throw new Error(data.message || 'Failed to update company');
        }
    })
    .catch(error => {
        console.error('Error updating company:', error);
        showToast('errorToast', 'Failed to update company: ' + error.message);
    })
    .finally(() => {
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    });
}

function cancelCompanyEdit() {
    // Switch back to display mode
    document.getElementById('companyNameDisplay').classList.remove('d-none');
    document.getElementById('companyNameEdit').classList.add('d-none');
    
    document.getElementById('industryDisplay').classList.remove('d-none');
    document.getElementById('industryEdit').classList.add('d-none');
    
    document.getElementById('websiteDisplay').classList.remove('d-none');
    document.getElementById('websiteEdit').classList.add('d-none');
    
    document.getElementById('locationDisplay').classList.remove('d-none');
    document.getElementById('locationEdit').classList.add('d-none');
    
    document.getElementById('employeeCountDisplay').classList.remove('d-none');
    document.getElementById('employeeCountEdit').classList.add('d-none');
    
    document.getElementById('phoneDisplay').classList.remove('d-none');
    document.getElementById('phoneEdit').classList.add('d-none');
    
    document.getElementById('researchNotesDisplay').classList.remove('d-none');
    document.getElementById('researchNotesEdit').classList.add('d-none');
    
    document.getElementById('editControls').classList.add('d-none');
    
    document.getElementById('editCompanyBtn').innerHTML = '<i class="fas fa-edit me-1"></i>Edit';
    document.getElementById('editCompanyBtn').onclick = toggleCompanyEditMode;
}

function saveCompany() {
    const form = document.getElementById('addCompanyForm');
    const saveBtn = document.getElementById('saveCompanyBtn');
    
    // Get form data
    const companyData = {
        company_name: document.getElementById('companyName').value.trim(),
        website_url: document.getElementById('websiteUrl').value.trim()
    };
    
    // Validate required fields
    if (!companyData.company_name) {
        showToast('errorToast', 'Company name is required');
        return;
    }
    
    // Show loading state
    const originalHTML = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
    
    // Check if we're editing or creating
    const editingId = saveBtn.dataset.editingCompanyId;
    const endpoint = editingId ? `/api/companies/${editingId}` : '/api/companies';
    const method = editingId ? 'PUT' : 'POST';
    
    fetch(endpoint, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(companyData)
    })
    .then(resp => resp.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', data.message || 'Company saved successfully');
            
            // Close modal if it exists
            const modal = bootstrap.Modal.getInstance(document.getElementById('addCompanyModal'));
            if (modal) modal.hide();
            
            // Reset form and state
            if (form) form.reset();
            delete saveBtn.dataset.editingCompanyId;
            
            // Update modal title if it exists
            const modalLabel = document.getElementById('addCompanyModalLabel');
            if (modalLabel) modalLabel.textContent = 'Add New Company';
            
            // Reload companies list
            setTimeout(() => {
                if (typeof loadCompanies === 'function') {
                    loadCompanies();
                } else {
                    window.location.reload();
                }
            }, 1500);
        } else {
            showToast('errorToast', data.message || 'Failed to save company');
        }
    })
    .catch(err => {
        console.error('Error saving company:', err);
        showToast('errorToast', 'Error saving company');
    })
    .finally(() => {
        // Restore button state
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalHTML;
    });
}

// Company stats update
function updateCompanyStats(count = null) {
    const companyCountElement = document.getElementById('companyCount');
    if (companyCountElement && count !== null) {
        companyCountElement.textContent = count;
    }
}

// Export companies from contacts
function extractCompaniesFromContacts() {
    const extractBtn = document.getElementById('extractCompanies');
    if (!extractBtn) return;
    
    const originalText = extractBtn.innerHTML;
    extractBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Extracting...';
    extractBtn.disabled = true;
    
    fetch('/api/companies/extract-from-contacts', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `Extracted ${data.count || 0} companies from contacts!`);
            changeCompaniesPage(1);
        } else {
            throw new Error(data.message || 'Failed to extract companies');
        }
    })
    .catch(error => {
        console.error('Error extracting companies:', error);
        showToast('errorToast', 'Failed to extract companies: ' + error.message);
    })
    .finally(() => {
        extractBtn.innerHTML = originalText;
        extractBtn.disabled = false;
    });
}

// Setup delete and reset company buttons
function setupDeleteResetCompanyButtons() {
    console.log('Setting up delete and reset company buttons...');
    
    // Use event delegation since buttons are dynamically generated
    document.addEventListener('click', function(event) {
        if (event.target.closest('.delete-reset-company-btn')) {
            const button = event.target.closest('.delete-reset-company-btn');
            const companyId = button.dataset.companyId;
            const companyName = button.dataset.companyName;
            
            console.log(`Delete and reset clicked for company: ${companyName} (ID: ${companyId})`);
            deleteAndResetCompany(companyId, companyName);
        }
    });
}

// Delete and reset company function
function deleteAndResetCompany(companyId, companyName) {
    console.log(`Deleting and resetting company: ${companyName} (ID: ${companyId})`);
    
    // Show loading state
    const button = document.querySelector(`[data-company-id="${companyId}"].delete-reset-company-btn`);
    if (button) {
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Resetting...';
        button.disabled = true;
        
        // Send delete request
        fetch(`/api/companies/${companyId}/delete-reset`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('successToast', `Research data for "${companyName}" reset successfully!`);
                // Refresh the current page
                changeCompaniesPage(getCurrentCompaniesPage());
            } else {
                throw new Error(data.message || 'Failed to reset research');
            }
        })
        .catch(error => {
            console.error('Error resetting research:', error);
            showToast('errorToast', 'Failed to reset research: ' + error.message);
        })
        .finally(() => {
            // Restore button state
            if (button) {
                button.innerHTML = originalText;
                button.disabled = false;
            }
        });
    }
}

// Helper function to get current companies page
function getCurrentCompaniesPage() {
    const urlParams = new URLSearchParams(window.location.search);
    return parseInt(urlParams.get('companies_page')) || 1;
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeCompanies,
        performCompanySearch,
        clearCompanySearch,
        changeCompaniesPage,
        loadCompanyDetails,
        researchCompanies,
        researchSingleCompany,
        extractCompaniesFromContacts,
        currentCompanyId
    };
}

// Global function assignments for HTML onclick handlers
window.clearCompanySearch = clearCompanySearch;
window.changeCompaniesPage = changeCompaniesPage;
window.loadCompanyDetails = loadCompanyDetails;
window.researchCompanies = researchCompanies;
window.researchSingleCompany = researchSingleCompany;
window.extractCompaniesFromContacts = extractCompaniesFromContacts;
window.toggleCompanyEditMode = toggleCompanyEditMode;
window.saveCompanyInModal = saveCompanyInModal;
window.cancelCompanyEdit = cancelCompanyEdit;
window.saveCompany = saveCompany;