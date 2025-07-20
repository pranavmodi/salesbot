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
    
    if (researchBtn) {
        researchBtn.addEventListener('click', researchCompanies);
    }
    if (saveCompanyBtn) {
        saveCompanyBtn.addEventListener('click', saveCompany);
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
                        <th>Industry</th>
                        <th>Location</th>
                        <th>Employee Count</th>
                        <th>Contact Count</th>
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
                            ${company.name ? company.name[0].toUpperCase() : '?'}
                        </div>
                        <div>
                            <strong>${company.name || 'Unknown Company'}</strong>
                            ${company.website ? `<br><small class="text-muted">
                                <a href="${company.website}" target="_blank" class="text-decoration-none">
                                    <i class="fas fa-external-link-alt me-1"></i>${company.website}
                                </a>
                            </small>` : ''}
                        </div>
                    </div>
                </td>
                <td>
                    <span>${company.industry || 'Not specified'}</span>
                </td>
                <td>
                    <span class="text-muted">${company.location || 'Not specified'}</span>
                </td>
                <td>
                    <span>${company.employee_count || 'Unknown'}</span>
                </td>
                <td>
                    <span class="badge bg-primary">${company.contact_count || 0}</span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary btn-sm" 
                                onclick="loadCompanyDetails(${company.id})" 
                                title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button type="button" class="btn btn-outline-success btn-sm" 
                                onclick="researchSingleCompany(${company.id}, '${company.name}', this)" 
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
                        <th>Industry</th>
                        <th>Location</th>
                        <th>Employee Count</th>
                        <th>Contact Count</th>
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
                            ${company.name ? company.name[0].toUpperCase() : '?'}
                        </div>
                        <div>
                            <strong>${company.name || 'Unknown Company'}</strong>
                            ${company.website ? `<br><small class="text-muted">
                                <a href="${company.website}" target="_blank" class="text-decoration-none">
                                    <i class="fas fa-external-link-alt me-1"></i>${company.website}
                                </a>
                            </small>` : ''}
                        </div>
                    </div>
                </td>
                <td>
                    <span>${company.industry || 'Not specified'}</span>
                </td>
                <td>
                    <span class="text-muted">${company.location || 'Not specified'}</span>
                </td>
                <td>
                    <span>${company.employee_count || 'Unknown'}</span>
                </td>
                <td>
                    <span class="badge bg-primary">${company.contact_count || 0}</span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary btn-sm" 
                                onclick="loadCompanyDetails(${company.id})" 
                                title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button type="button" class="btn btn-outline-success btn-sm" 
                                onclick="researchSingleCompany(${company.id}, '${company.name}', this)" 
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
            showToast('errorToast', 'Failed to load company details: ' + error.message);
        });
}

function displayCompanyDetails(company) {
    const modal = document.getElementById('companyModal');
    const modalTitle = modal.querySelector('.modal-title');
    const modalBody = modal.querySelector('#companyDetails');
    
    modalTitle.textContent = `Company Details - ${company.name || 'Unknown Company'}`;
    
    modalBody.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-muted mb-3">Basic Information</h6>
                <div class="mb-2">
                    <strong>Company Name:</strong> 
                    <span id="companyNameDisplay">${company.name || 'Not provided'}</span>
                    <input type="text" class="form-control d-none" id="companyNameEdit" value="${company.name || ''}">
                </div>
                <div class="mb-2">
                    <strong>Industry:</strong> 
                    <span id="industryDisplay">${company.industry || 'Not provided'}</span>
                    <input type="text" class="form-control d-none" id="industryEdit" value="${company.industry || ''}">
                </div>
                <div class="mb-2">
                    <strong>Website:</strong> 
                    <span id="websiteDisplay">
                        ${company.website ? 
                            `<a href="${company.website}" target="_blank" class="text-decoration-none">
                                <i class="fas fa-external-link-alt me-1"></i>${company.website}
                            </a>` : 'Not provided'}
                    </span>
                    <input type="url" class="form-control d-none" id="websiteEdit" value="${company.website || ''}">
                </div>
                <div class="mb-2">
                    <strong>Location:</strong> 
                    <span id="locationDisplay">${company.location || 'Not provided'}</span>
                    <input type="text" class="form-control d-none" id="locationEdit" value="${company.location || ''}">
                </div>
                <div class="mb-2">
                    <strong>Employee Count:</strong> 
                    <span id="employeeCountDisplay">${company.employee_count || 'Unknown'}</span>
                    <input type="number" class="form-control d-none" id="employeeCountEdit" value="${company.employee_count || ''}">
                </div>
            </div>
            <div class="col-md-6">
                <h6 class="text-muted mb-3">Contact Information</h6>
                <div class="mb-2">
                    <strong>Contact Count:</strong> 
                    <span class="badge bg-primary">${company.contact_count || 0}</span>
                </div>
                <div class="mb-2">
                    <strong>Primary Contact:</strong> 
                    ${company.primary_contact_email ? 
                        `<a href="mailto:${company.primary_contact_email}" class="text-decoration-none">
                            ${company.primary_contact_email}
                        </a>` : 'Not specified'}
                </div>
                <div class="mb-2">
                    <strong>Phone:</strong> 
                    <span id="phoneDisplay">${company.phone || 'Not provided'}</span>
                    <input type="tel" class="form-control d-none" id="phoneEdit" value="${company.phone || ''}">
                </div>
            </div>
        </div>
        
        <hr>
        
        <div class="row">
            <div class="col-12">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="text-muted mb-0">Research Notes</h6>
                    <div class="btn-group btn-group-sm">
                        <button type="button" class="btn btn-outline-primary" 
                                id="editCompanyBtn" onclick="toggleCompanyEditMode()">
                            <i class="fas fa-edit me-1"></i>Edit
                        </button>
                        <button type="button" class="btn btn-outline-success" 
                                onclick="researchSingleCompany(${company.id}, '${company.name}', this)">
                            <i class="fas fa-search me-1"></i>Research
                        </button>
                    </div>
                </div>
                
                <div id="researchNotesDisplay" class="p-3 bg-light rounded">
                    ${company.research_notes || 'No research notes available'}
                </div>
                <textarea class="form-control d-none" id="researchNotesEdit" rows="6">${company.research_notes || ''}</textarea>
                
                <div class="d-none mt-3" id="editControls">
                    <button type="button" class="btn btn-success me-2" onclick="saveCompanyInModal()">
                        <i class="fas fa-save me-1"></i>Save Changes
                    </button>
                    <button type="button" class="btn btn-secondary" onclick="cancelCompanyEdit()">
                        <i class="fas fa-times me-1"></i>Cancel
                    </button>
                </div>
            </div>
        </div>
    `;
    
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
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
    // This function can be used for saving new companies
    console.log('Save company functionality to be implemented');
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