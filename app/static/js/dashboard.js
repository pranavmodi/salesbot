// SalesBot CRM - Dashboard JavaScript

// Global variables
let currentContacts = [];
let emailHistory = window.emailHistoryData || [];
let currentContactEmail = null; // For modal export functionality
let selectedContacts = []; // For bulk email composition
let currentGlobalAccount = null; // Currently selected global account

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    setupSearch();
    setupFilters();
    // Update dashboard stats if needed
    // updateDashboardStats();
    initializePage();
});

function initializePage() {
    // All other initializations can go here
    // For example, setting up filters or other dynamic elements
    console.log("Dashboard initialized");
    
    // Load global email accounts and setup global selector
    loadGlobalEmailAccounts();
    setupGlobalAccountSelector();
}

// Pagination utility functions
function addPaginationLoadingState(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.style.opacity = '0.6';
        container.style.pointerEvents = 'none';
    }
}

function removePaginationLoadingState(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.style.opacity = '1';
        container.style.pointerEvents = 'auto';
    }
}

function setupEventListeners() {
    // Pagination
    const perPageSelect = document.getElementById('perPage');
    if (perPageSelect) {
        perPageSelect.addEventListener('change', function() {
            addPaginationLoadingState('contactsContainer');
            changePage(1);
        });
    }

    document.querySelectorAll('.pagination .page-link[data-page]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = parseInt(this.getAttribute('data-page'));
            if (page && !this.parentElement.classList.contains('disabled')) {
                addPaginationLoadingState('contactsContainer');
                changePage(page);
            }
        });
    });

    // Compose form (for compose tab only)
    const generatePreviewBtn = document.getElementById('generatePreview');
    const composeForm = document.getElementById('composeForm');
    
    if (generatePreviewBtn) {
        generatePreviewBtn.addEventListener('click', generateEmailPreview);
    }
    if (composeForm) {
        composeForm.addEventListener('submit', sendComposedEmail);
    }

    // Export from modal button
    const exportFromModalBtn = document.getElementById('exportFromModal');
    if (exportFromModalBtn) {
        exportFromModalBtn.addEventListener('click', function() {
            if (currentContactEmail) {
                exportContact(currentContactEmail);
            }
        });
    }

    // Add Contact form
    const saveContactBtn = document.getElementById('saveContactBtn');
    if (saveContactBtn) {
        saveContactBtn.addEventListener('click', saveNewContact);
    }

    // Add Contact modal reset
    const addContactModal = document.getElementById('addContactModal');
    if (addContactModal) {
        addContactModal.addEventListener('hidden.bs.modal', function() {
            resetAddContactForm();
        });
    }

    const sendTestEmailForm = document.getElementById('sendTestEmailForm');
    if (sendTestEmailForm) {
        sendTestEmailForm.addEventListener('submit', sendTestEmails);
    }
    
    // Setup enhanced pagination
    setupEmailHistoryPagination();
    setupInboxPagination();
}

function setupEmailHistoryPagination() {
    // Email history per page selector
    const emailHistoryPerPageSelect = document.getElementById('emailHistoryPerPage');
    if (emailHistoryPerPageSelect) {
        emailHistoryPerPageSelect.addEventListener('change', function() {
            changeEmailHistoryPage(1); // Reset to first page when changing per page
        });
    }
    
    // Email history pagination links
    document.querySelectorAll('[data-email-page]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = parseInt(this.getAttribute('data-email-page'));
            if (page && !this.parentElement.classList.contains('disabled')) {
                changeEmailHistoryPage(page);
            }
        });
    });
    
    // Email history filter functionality
    const filterItems = document.querySelectorAll('#history-tab-pane [data-filter]');
    filterItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const filter = this.getAttribute('data-filter');
            applyEmailHistoryFilter(filter);
        });
    });
}

function changeEmailHistoryPage(page) {
    // Get current per page value
    const perPageSelect = document.getElementById('emailHistoryPerPage');
    const perPage = perPageSelect ? perPageSelect.value : 25;
    
    // Show loading state
    const emailHistoryContainer = document.getElementById('emailHistoryTableBody');
    if (emailHistoryContainer) {
        addPaginationLoadingState('emailHistoryTableBody');
    }
    
    // For now, just reload the page with email history pagination parameters
    // In a real implementation, you'd fetch paginated email history data via AJAX
    const url = new URL(window.location.href);
    url.searchParams.set('email_history_page', page);
    url.searchParams.set('email_history_per_page', perPage);
    window.location.href = url.toString();
}

function refreshEmailHistory() {
    const historyContainer = document.getElementById('emailHistoryTableBody');
    if (!historyContainer) return;
    
    // Show loading state
    historyContainer.closest('.table-responsive').classList.add('table-loading');
    
    // Simulate refresh (you can replace this with actual API call)
    setTimeout(() => {
        historyContainer.closest('.table-responsive').classList.remove('table-loading');
        showToast('successToast', 'Email history refreshed!');
    }, 1000);
}

function applyEmailHistoryFilter(filter) {
    const emailRows = document.querySelectorAll('#emailHistoryTableBody tr');
    
    emailRows.forEach(row => {
        let showRow = true;
        const status = row.getAttribute('data-email-status');
        const date = row.getAttribute('data-email-date');
        
        switch(filter) {
            case 'success':
                showRow = status === 'success';
                break;
            case 'failed':
                showRow = status !== 'success';
                break;
            case 'today':
                const today = new Date().toISOString().split('T')[0];
                showRow = date === today;
                break;
            case 'week':
                const weekAgo = new Date();
                weekAgo.setDate(weekAgo.getDate() - 7);
                const emailDate = new Date(date);
                showRow = emailDate >= weekAgo;
                break;
            case 'all':
            default:
                showRow = true;
                break;
        }
        
        if (showRow) {
            row.style.display = '';
            row.classList.remove('d-none');
        } else {
            row.style.display = 'none';
            row.classList.add('d-none');
        }
    });
}

function setupInboxPagination() {
    // Inbox per page selector
    const inboxPerPageSelect = document.getElementById('inboxPerPage');
    if (inboxPerPageSelect) {
        inboxPerPageSelect.addEventListener('change', function() {
            changeInboxPage(1); // Reset to first page when changing per page
        });
    }
    
    // Inbox pagination links
    document.querySelectorAll('[data-inbox-page]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = parseInt(this.getAttribute('data-inbox-page'));
            if (page && !this.parentElement.classList.contains('disabled')) {
                changeInboxPage(page);
            }
        });
    });
}

function changeInboxPage(page) {
    // Get current per page value
    const perPageSelect = document.getElementById('inboxPerPage');
    const perPage = perPageSelect ? perPageSelect.value : 10;
    
    // Show loading state
    const inboxContainer = document.getElementById('threadsAccordion');
    if (inboxContainer) {
        addPaginationLoadingState('threadsAccordion');
    }
    
    // For now, just reload the page with inbox pagination parameters
    // In a real implementation, you'd fetch paginated inbox data via AJAX
    const url = new URL(window.location.href);
    url.searchParams.set('inbox_page', page);
    url.searchParams.set('inbox_per_page', perPage);
    window.location.href = url.toString();
}

function setupSearch() {
    // Contact search functionality with server-side search
    const contactSearchInput = document.getElementById('contactSearch');
    if (contactSearchInput) {
        let searchTimeout;
        
        contactSearchInput.addEventListener('input', function() {
            const searchTerm = this.value.trim();
            
            // Clear previous timeout
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }
            
            // Debounce search to avoid too many API calls
            searchTimeout = setTimeout(() => {
                performContactSearch(searchTerm);
            }, 300);
        });
    }
    
    // Company search functionality with server-side search
    const companySearchInput = document.getElementById('companySearch');
    if (companySearchInput) {
        let companySearchTimeout;
        
        companySearchInput.addEventListener('input', function() {
            const searchTerm = this.value.trim();
            
            // Clear previous timeout
            if (companySearchTimeout) {
                clearTimeout(companySearchTimeout);
            }
            
            // Debounce search to avoid too many API calls
            companySearchTimeout = setTimeout(() => {
                performCompanySearch(searchTerm);
            }, 300);
        });
    }
}

function performContactSearch(searchTerm) {
    const contactsContainer = document.getElementById('contacts-table-container');
    const originalContent = contactsContainer.innerHTML;
    
    if (searchTerm === '') {
        // If search is empty, reload the original paginated view
        window.location.href = window.location.pathname;
        return;
    }
    
    console.log(`Performing server-side contact search: "${searchTerm}"`);
    
    // Show loading state
    contactsContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Searching contacts...</p>
        </div>
    `;
    
    // Perform server-side search
    fetch(`/api/search_contacts?q=${encodeURIComponent(searchTerm)}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            displayContactSearchResults(data.contacts, searchTerm);
            updateContactStats(data.count);
        })
        .catch(error => {
            console.error('Error searching contacts:', error);
            contactsContainer.innerHTML = originalContent;
            showToast('errorToast', 'Failed to search contacts: ' + error.message);
        });
}

function performCompanySearch(searchTerm) {
    const companiesContainer = document.getElementById('companies-table-container');
    const originalContent = companiesContainer.innerHTML;
    
    if (searchTerm === '') {
        // If search is empty, reload the original paginated view
        changeCompaniesPage(1);
        return;
    }
    
    console.log(`Performing server-side company search: "${searchTerm}"`);
    
    // Show loading state
    companiesContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Searching companies...</p>
        </div>
    `;
    
    // Perform server-side search
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

function displayContactSearchResults(contacts, searchTerm) {
    const contactsContainer = document.getElementById('contacts-table-container');
    
    if (contacts.length === 0) {
        contactsContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-search fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No contacts found</h5>
                <p class="text-muted">No contacts found matching "${searchTerm}"</p>
                <button class="btn btn-outline-primary mt-3" onclick="clearContactSearch()">
                    <i class="fas fa-arrow-left me-2"></i>Back to All Contacts
                </button>
            </div>
        `;
        return;
    }
    
    let tableHtml = `
        <div class="mb-3">
            <div class="alert alert-info">
                <i class="fas fa-search me-2"></i>
                Found <strong>${contacts.length}</strong> contacts matching "${searchTerm}"
                <button class="btn btn-outline-primary btn-sm ms-3" onclick="clearContactSearch()">
                    <i class="fas fa-times me-1"></i>Clear Search
                </button>
            </div>
        </div>
        
        <div class="table-responsive">
            <table class="table table-hover">
                <thead class="table-light">
                    <tr>
                        <th style="width: 40px;">
                            <input type="checkbox" class="form-check-input" id="selectAllSearchResults" onchange="toggleSelectAllSearchResults()" style="margin: 0;">
                        </th>
                        <th style="width: 50px;"></th>
                        <th>Name</th>
                        <th>Company</th>
                        <th>Position</th>
                        <th>Email</th>
                        <th>Location</th>
                        <th style="width: 120px;">Actions</th>
                    </tr>
                </thead>
                <tbody id="contactsContainer">
    `;
    
    contacts.forEach((contact, index) => {
        const initials = contact.first_name ? contact.first_name[0].toUpperCase() : '?';
        const displayName = contact.display_name || contact.full_name || `${contact.first_name || ''} ${contact.last_name || ''}`.trim() || 'Unknown';
        const company = contact.company || contact.company_name || 'Not specified';
        const jobTitle = contact.job_title || 'Not specified';
        const location = contact.location || 'Not specified';
        
        tableHtml += `
            <tr class="contact-row" data-contact-email="${contact.email}">
                <td>
                    <input type="checkbox" class="form-check-input contact-checkbox" 
                           value="${contact.email}" 
                           data-contact='${JSON.stringify(contact).replace(/'/g, "&apos;")}'
                           onchange="updateSelectionCount()">
                </td>
                <td>
                    <div class="contact-avatar" style="width: 36px; height: 36px; font-size: 0.875rem;">
                        ${initials}
                    </div>
                </td>
                <td>
                    <div class="contact-name">
                        <strong>${displayName}</strong>
                    </div>
                </td>
                <td>
                    <span class="fw-semibold">${company}</span>
                </td>
                <td>
                    <span>${jobTitle}</span>
                </td>
                <td>
                    <a href="mailto:${contact.email}" class="text-decoration-none">${contact.email}</a>
                </td>
                <td>
                    <span>${location}</span>
                </td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-outline-primary btn-sm" onclick="viewContactDetails('${contact.email}')" title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${contact.linkedin_profile ? `
                        <a href="${contact.linkedin_profile}" target="_blank" class="btn btn-outline-info btn-sm" title="LinkedIn Profile">
                            <i class="fab fa-linkedin"></i>
                        </a>
                        ` : ''}
                        <button class="btn btn-outline-secondary btn-sm" onclick="exportContact('${contact.email}')" title="Export Contact">
                            <i class="fas fa-download"></i>
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
    
    contactsContainer.innerHTML = tableHtml;
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
    
    let html = `
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
                        <th>Research Summary</th>
                        <th>Created At</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    companies.forEach(company => {
        const createdAt = company.created_at ? new Date(company.created_at).toLocaleDateString() : 'N/A';
        const researchSummary = company.company_research ? 
            (company.company_research.length > 100 ? 
                company.company_research.substring(0, 100) + '...' : 
                company.company_research) : '';
        
        html += `
            <tr>
                <td><strong>${company.company_name || ''}</strong></td>
                <td><a href="${company.website_url || '#'}" target="_blank">${company.website_url || ''}</a></td>
                <td>${researchSummary}</td>
                <td>${createdAt}</td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-primary company-view-btn" data-bs-toggle="modal" data-bs-target="#companyDetailModal" data-company-id="${company.id}">
                            <i class="fas fa-eye"></i> View
                        </button>
                        ${company.needs_research ? 
                            `<button class="btn btn-sm btn-outline-warning research-company-btn" data-company-id="${company.id}" data-company-name="${company.company_name}" title="Research this company">
                                <i class="fas fa-search"></i> Research
                            </button>` :
                            `<button class="btn btn-sm btn-outline-success research-company-btn" data-company-id="${company.id}" data-company-name="${company.company_name}" title="Re-research this company">
                                <i class="fas fa-redo"></i> Re-research
                            </button>`
                        }
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
    
    companiesContainer.innerHTML = html;
    
    // Re-setup event listeners for the new elements
    setTimeout(setupCompaniesPagination, 100);
}

function updateCompanyStats(visibleCount) {
    // Update any company statistics display
    const statsNumbers = document.querySelectorAll('#companies-tab-pane .stats-number');
    if (statsNumbers.length > 0 && typeof visibleCount !== 'undefined') {
        statsNumbers[0].textContent = visibleCount;
    }
}

function clearContactSearch() {
    const contactSearchInput = document.getElementById('contactSearch');
    if (contactSearchInput) {
        contactSearchInput.value = '';
        
        // Reload the original paginated view instead of showing local rows
        window.location.href = window.location.pathname;
    }
}

function clearCompanySearch() {
    const companySearchInput = document.getElementById('companySearch');
    if (companySearchInput) {
        companySearchInput.value = '';
        
        // Reload the original paginated view instead of showing local rows
        changeCompaniesPage(1);
    }
}

function setupFilters() {
    const filterItems = document.querySelectorAll('[data-filter]');
    filterItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const filter = this.getAttribute('data-filter');
            applyFilter(filter);
        });
    });
}

function applyFilter(filter) {
    // Clear search when applying filters
    const contactSearchInput = document.getElementById('contactSearch');
    if (contactSearchInput) {
        contactSearchInput.value = '';
    }
    
    const contactRows = document.querySelectorAll('#contactsContainer .contact-row');
    
    if (filter === 'uncontacted') {
        // Handle uncontacted filter with API call
        handleUncontactedFilter();
        return;
    }
    
    contactRows.forEach(row => {
        let showRow = true;
        const text = row.textContent;
        
        switch(filter) {
            case 'has-phone':
                showRow = text.includes('tel:') && !text.includes('Not available');
                break;
            case 'has-linkedin':
                showRow = row.querySelector('a[href*="linkedin"]') !== null;
                break;
            case 'recent':
                // Show contacts added in the last 30 days (simplified)
                showRow = text.includes('Added:');
                break;
            case 'all':
            default:
                showRow = true;
                break;
        }
        
        if (showRow) {
            row.style.display = '';
            row.classList.remove('d-none');
        } else {
            row.style.display = 'none';
            row.classList.add('d-none');
        }
    });
    
    updateContactStats();
}

function handleUncontactedFilter() {
    // Show loading state - use the table container now
    const contactsContainer = document.getElementById('contacts-table-container');
    const originalContent = contactsContainer.innerHTML;
    
    contactsContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading uncontacted contacts...</p>
        </div>
    `;
    
    // Fetch uncontacted contacts
    fetch('/api/contacts/uncontacted')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            displayUncontactedContacts(data);
        })
        .catch(error => {
            console.error('Error fetching uncontacted contacts:', error);
            contactsContainer.innerHTML = originalContent;
            showToast('errorToast', 'Failed to load uncontacted contacts: ' + error.message);
        });
}

function displayUncontactedContacts(data) {
    const contactsContainer = document.getElementById('contacts-table-container');
    
    if (data.contacts.length === 0) {
        contactsContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-check-circle fa-3x text-success mb-3"></i>
                <h5 class="text-success">All contacts have been contacted!</h5>
                <p class="text-muted">Every contact in your database has received at least one email.</p>
                <div class="mt-3">
                    <small class="text-muted">
                        Total contacts: ${data.total_contacts} | 
                        Contacted: ${data.contacted_count}
                    </small>
                </div>
            </div>
        `;
        return;
    }
    
    let tableHtml = `
        <div class="mb-3">
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                Found <strong>${data.count}</strong> uncontacted contacts out of ${data.total_contacts} total contacts.
            </div>
        </div>
        
        <!-- Selection Controls -->
        <div class="card mb-3">
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="selectAllContacts" onchange="toggleSelectAll()">
                            <label class="form-check-label" for="selectAllContacts">
                                <strong>Select All</strong>
                            </label>
                            <span class="ms-2 text-muted" id="selectedCount">0 selected</span>
                        </div>
                    </div>
                    <div class="col-md-6 text-end">
                        <button class="btn btn-primary" id="composeForSelectedBtn" onclick="startBulkEmailComposition()" disabled>
                            <i class="fas fa-edit me-2"></i>Compose for Selected
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <table class="table table-hover">
            <thead>
                <tr>
                    <th style="width: 40px;">
                        <input type="checkbox" class="form-check-input" id="selectAllHeader" onchange="toggleSelectAll()" style="margin: 0;">
                    </th>
                    <th style="width: 50px;"></th>
                    <th>Name</th>
                    <th>Company</th>
                    <th>Position</th>
                    <th>Email</th>
                    <th>Location</th>
                    <th style="width: 120px;">Actions</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    data.contacts.forEach((contact, index) => {
        const initials = contact.first_name ? contact.first_name[0].toUpperCase() : '?';
        const displayName = contact.display_name || 'Unknown';
        const company = contact.company || 'Not specified';
        const jobTitle = contact.job_title || 'Not specified';
        const location = contact.location || 'Not specified';
        
        tableHtml += `
            <tr class="contact-row" data-contact-email="${contact.email}">
                <td>
                    <input type="checkbox" class="form-check-input contact-checkbox" 
                           value="${contact.email}" 
                           data-contact='${JSON.stringify(contact).replace(/'/g, "&apos;")}'
                           onchange="updateSelectionCount()">
                </td>
                <td>
                    <div class="contact-avatar" style="width: 36px; height: 36px; font-size: 0.875rem;">
                        ${initials}
                    </div>
                </td>
                <td>
                    <div class="contact-name">
                        <strong>${displayName}</strong>
                        <br><small class="text-warning"><i class="fas fa-envelope-open me-1"></i>Not contacted</small>
                    </div>
                </td>
                <td>
                    <span class="fw-semibold">${company}</span>
                </td>
                <td>
                    <span>${jobTitle}</span>
                </td>
                <td>
                    <a href="mailto:${contact.email}" class="text-decoration-none">${contact.email}</a>
                </td>
                <td>
                    <span>${location}</span>
                </td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-outline-primary btn-sm" onclick="viewContactDetails('${contact.email}')" title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${contact.linkedin_profile ? `
                        <a href="${contact.linkedin_profile}" target="_blank" class="btn btn-outline-info btn-sm" title="LinkedIn Profile">
                            <i class="fab fa-linkedin"></i>
                        </a>
                        ` : ''}
                        <button class="btn btn-outline-secondary btn-sm" onclick="exportContact('${contact.email}')" title="Export Contact">
                            <i class="fas fa-download"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tableHtml += `
            </tbody>
        </table>
        <div class="mt-3">
            <button class="btn btn-outline-secondary" onclick="window.location.reload()">
                <i class="fas fa-arrow-left me-2"></i>Back to All Contacts
            </button>
        </div>
    `;
    
    contactsContainer.innerHTML = tableHtml;
    
    // Update stats
    updateContactStats();
}

function updateContactStats() {
    const visibleRows = document.querySelectorAll('#contactsContainer .contact-row:not(.d-none):not([style*="display: none"])');
    const statsNumbers = document.querySelectorAll('#contacts-tab-pane .stats-number');
    
    if (statsNumbers.length > 0) {
        statsNumbers[0].textContent = visibleRows.length;
    }
}

function changePage(page) {
    const perPageSelect = document.getElementById('perPage');
    const perPage = perPageSelect ? perPageSelect.value : 10;
    const url = new URL(window.location.href);
    url.searchParams.set('page', page);
    url.searchParams.set('per_page', perPage);
    window.location.href = url.toString();
}

// Contact management functions
function viewContactDetails(email) {
    currentContactEmail = email; // Store for modal export
    
    // Find the contact row
    const contactRow = document.querySelector(`tr[data-contact-email="${email}"]`);
    if (!contactRow) {
        showToast('errorToast', 'Contact not found');
        return;
    }
    
    // Extract contact data from the row
    const cells = contactRow.querySelectorAll('td');
    const contactData = {
        email: email,
        avatar: cells[0].querySelector('.contact-avatar').textContent.trim(),
        name: cells[1].querySelector('strong').textContent.trim(),
        company: cells[2].textContent.trim(),
        position: cells[3].textContent.trim(),
        location: cells[5].textContent.trim(),
        phone: cells[6].textContent.trim(),
        linkedinBtn: contactRow.querySelector('a[href*="linkedin"]'),
        companyLink: cells[2].querySelector('a'),
        addedDate: cells[1].querySelector('small') ? cells[1].querySelector('small').textContent.trim() : ''
    };
    
    showContactModal(contactData);
}

function showContactModal(contactData) {
    const modal = document.getElementById('contactDetailsModal');
    const modalContent = document.getElementById('contactDetailsContent');
    
    if (!modal || !modalContent) {
        showToast('errorToast', 'Modal not found');
        return;
    }
    
    // Create detailed contact view with email conversation section
    const detailsHtml = `
        <div class="row">
            <div class="col-md-3 text-center mb-4">
                <div class="contact-avatar mx-auto mb-3" style="width: 80px; height: 80px; font-size: 2rem;">
                    ${contactData.avatar}
                </div>
                <h5 class="text-primary">${contactData.name}</h5>
                ${contactData.addedDate ? `<small class="text-muted">${contactData.addedDate}</small>` : ''}
            </div>
            <div class="col-md-9">
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <h6 class="text-muted mb-2">
                            <i class="fas fa-briefcase me-2"></i>Professional Information
                        </h6>
                        <div class="ms-3">
                            <div class="mb-2">
                                <strong>Position:</strong><br>
                                <span>${contactData.position}</span>
                            </div>
                            <div class="mb-2">
                                <strong>Company:</strong><br>
                                <span>${contactData.company}</span>
                                ${contactData.companyLink ? `<br><a href="${contactData.companyLink.href}" target="_blank" class="text-decoration-none"><i class="fas fa-external-link-alt me-1"></i>Visit Website</a>` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <h6 class="text-muted mb-2">
                            <i class="fas fa-address-book me-2"></i>Contact Information
                        </h6>
                        <div class="ms-3">
                            <div class="mb-2">
                                <strong>Email:</strong><br>
                                <a href="mailto:${contactData.email}" class="text-decoration-none">${contactData.email}</a>
                            </div>
                            <div class="mb-2">
                                <strong>Phone:</strong><br>
                                <span>${contactData.phone}</span>
                            </div>
                            <div class="mb-2">
                                <strong>Location:</strong><br>
                                <span>${contactData.location}</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-12">
                        <h6 class="text-muted mb-2">
                            <i class="fas fa-share-alt me-2"></i>Social & Links
                        </h6>
                        <div class="ms-3">
                            ${contactData.linkedinBtn ? 
                                `<a href="${contactData.linkedinBtn.href}" target="_blank" class="btn btn-outline-primary btn-sm me-2">
                                    <i class="fab fa-linkedin me-1"></i>LinkedIn Profile
                                </a>` : 
                                '<span class="text-muted">No LinkedIn profile available</span>'
                            }
                        </div>
                    </div>
                </div>
                
                <!-- Email Conversations Section -->
                <div class="row mt-4">
                    <div class="col-12">
                        <h6 class="text-muted mb-2">
                            <i class="fas fa-envelope me-2"></i>Email Conversations
                            <button class="btn btn-outline-primary btn-sm ms-2" onclick="loadEmailConversations('${contactData.email}')">
                                <i class="fas fa-sync me-1"></i>Load Conversations
                            </button>
                        </h6>
                        <div id="emailConversationsContainer" class="ms-3">
                            <div class="text-muted">
                                <i class="fas fa-info-circle me-2"></i>
                                Click "Load Conversations" to view email history with this contact
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    modalContent.innerHTML = detailsHtml;
    
    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

// Email conversation functions
function loadEmailConversations(contactEmail) {
    const container = document.getElementById('emailConversationsContainer');
    
    // Show loading state
    container.innerHTML = `
        <div class="text-center py-3">
            <div class="loading-spinner me-2"></div>
            Loading email conversations...
        </div>
    `;
    
    // Fetch conversations
    fetch(`/api/email/conversations/${contactEmail}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayConversationSummary(data.conversation_summary, contactEmail);
            } else {
                let errorMessage = data.message || 'Failed to load conversations';
                let helpText = '';
                
                if (data.feature_disabled) {
                    // Feature is disabled - show a clean message
                    container.innerHTML = `
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            <strong>Email Conversations</strong><br>
                            This feature requires IMAP access and is currently disabled. 
                            <br><small class="text-muted">You can enable this later when IMAP access is available.</small>
                        </div>
                    `;
                    return;
                } else if (data.error && data.error.includes('not configured')) {
                    helpText = `
                        <div class="mt-3">
                            <h6>To enable email reading:</h6>
                            <ol class="small">
                                <li>Login to <a href="https://www.zoho.com/mail" target="_blank">Zoho Mail</a></li>
                                <li>Go to Settings > Mail Accounts</li>
                                <li>Click on your email address</li>
                                <li>Enable "IMAP Access" checkbox</li>
                                <li>Click Save</li>
                            </ol>
                            <button class="btn btn-primary btn-sm" onclick="testEmailConnection()">
                                <i class="fas fa-plug me-1"></i>Test Email Connection
                            </button>
                        </div>
                    `;
                }
                
                container.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        ${errorMessage}
                        ${helpText}
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading conversations:', error);
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-times me-2"></i>
                    Error loading conversations. Check email configuration.
                    <div class="mt-2">
                        <button class="btn btn-primary btn-sm" onclick="testEmailConnection()">
                            <i class="fas fa-plug me-1"></i>Test Email Connection
                        </button>
                    </div>
                </div>
            `;
        });
}

function displayConversationSummary(summary, contactEmail) {
    const container = document.getElementById('emailConversationsContainer');
    
    if (summary.total_emails === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                No email conversations found with this contact.
            </div>
        `;
        return;
    }
    
    const summaryHtml = `
        <div class="conversation-summary">
            <div class="row mb-3">
                <div class="col-md-3">
                    <div class="stats-card text-center">
                        <div class="stats-number">${summary.total_emails}</div>
                        <div class="stats-label">Total Emails</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stats-card text-center">
                        <div class="stats-number">${summary.sent_count}</div>
                        <div class="stats-label">Sent</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stats-card text-center">
                        <div class="stats-number">${summary.received_count}</div>
                        <div class="stats-label">Received</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stats-card text-center">
                        <div class="stats-number">${Object.keys(summary.threads).length}</div>
                        <div class="stats-label">Threads</div>
                    </div>
                </div>
            </div>
            
            ${summary.last_email_date ? `
                <div class="alert alert-info">
                    <strong>Last Email:</strong> 
                    ${new Date(summary.last_email_date).toLocaleDateString()} 
                    (${summary.last_email_direction === 'sent' ? 'Sent by you' : 'Received from contact'})
                </div>
            ` : ''}
            
            <div class="mb-3">
                <h6>Recent Emails:</h6>
                <div class="list-group">
                    ${summary.recent_emails.slice(0, 5).map(email => `
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <h6 class="mb-1">${email.subject || 'No Subject'}</h6>
                                    <p class="mb-1 text-truncate" style="max-width: 400px;">
                                        ${email.body ? email.body.substring(0, 100) + '...' : 'No content'}
                                    </p>
                                    <small class="text-muted">
                                        ${new Date(email.date).toLocaleDateString()} - 
                                        ${email.direction === 'sent' ? 'Sent' : 'Received'}
                                    </small>
                                </div>
                                <span class="badge ${email.direction === 'sent' ? 'bg-primary' : 'bg-success'}">
                                    ${email.direction === 'sent' ? 'Sent' : 'Received'}
                                </span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <div class="text-center">
                <button class="btn btn-outline-primary" onclick="loadDetailedConversations('${contactEmail}')">
                    <i class="fas fa-comments me-2"></i>View All Conversations
                </button>
            </div>
        </div>
    `;
    
    container.innerHTML = summaryHtml;
}

function loadDetailedConversations(contactEmail) {
    const container = document.getElementById('emailConversationsContainer');
    
    // Show loading state
    container.innerHTML = `
        <div class="text-center py-3">
            <div class="loading-spinner me-2"></div>
            Loading detailed conversations...
        </div>
    `;
    
    // Fetch detailed conversations
    fetch(`/api/email/conversations/${contactEmail}/detailed`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayDetailedConversations(data, contactEmail);
            } else {
                container.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Failed to load detailed conversations
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading detailed conversations:', error);
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-times me-2"></i>
                    Error loading detailed conversations
                </div>
            `;
        });
}

function displayDetailedConversations(data, contactEmail) {
    const container = document.getElementById('emailConversationsContainer');
    
    let threadsHtml = '';
    for (const threadId in data.threads) {
        const thread = data.threads[threadId];
        threadsHtml += `
            <div class="card mb-3">
                <div class="card-header">
                    <h6 class="mb-0">
                        <i class="fas fa-comments me-2"></i>
                        ${thread.emails[0].subject || 'No Subject'}
                        <span class="badge bg-primary ms-2">${thread.email_count} emails</span>
                    </h6>
                </div>
                <div class="card-body">
                    ${thread.emails.map(email => `
                        <div class="email-item border-start border-3 ${email.direction === 'sent' ? 'border-primary' : 'border-success'} ps-3 mb-3">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <div>
                                    <strong>${email.direction === 'sent' ? 'You' : email.from}</strong>
                                    <small class="text-muted ms-2">${new Date(email.date).toLocaleString()}</small>
                                </div>
                                <span class="badge ${email.direction === 'sent' ? 'bg-primary' : 'bg-success'}">
                                    ${email.direction === 'sent' ? 'Sent' : 'Received'}
                                </span>
                            </div>
                            <p class="mb-0">${email.body}</p>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    const detailedHtml = `
        <div class="detailed-conversations">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6>All Conversations with ${contactEmail}</h6>
                <button class="btn btn-outline-secondary btn-sm" onclick="loadEmailConversations('${contactEmail}')">
                    <i class="fas fa-arrow-left me-1"></i>Back to Summary
                </button>
            </div>
            
            <div class="alert alert-info">
                <strong>Total:</strong> ${data.total_emails} emails in ${data.thread_count} conversation threads
            </div>
            
            ${threadsHtml || '<div class="text-muted">No conversation threads found</div>'}
        </div>
    `;
    
    container.innerHTML = detailedHtml;
}

function exportContact(email) {
    if (!email) {
        showToast('errorToast', 'No contact email provided');
        return;
    }
    
    // Find the contact row
    const contactRow = document.querySelector(`tr[data-contact-email="${email}"]`);
    if (!contactRow) {
        showToast('errorToast', 'Contact not found');
        return;
    }
    
    // Extract all contact information
    const cells = contactRow.querySelectorAll('td');
    const contactText = `
Contact Information Export
==========================

Name: ${cells[1].querySelector('strong').textContent.trim()}
Company: ${cells[2].textContent.trim()}
Position: ${cells[3].textContent.trim()}
Email: ${email}
Location: ${cells[5].textContent.trim()}
Phone: ${cells[6].textContent.trim()}
${cells[1].querySelector('small') ? cells[1].querySelector('small').textContent.trim() : ''}

LinkedIn: ${contactRow.querySelector('a[href*="linkedin"]') ? contactRow.querySelector('a[href*="linkedin"]').href : 'Not available'}
Company Website: ${cells[2].querySelector('a') ? cells[2].querySelector('a').href : 'Not available'}

Exported on: ${new Date().toLocaleString()}
    `.trim();
    
    // Create and download file
    const blob = new Blob([contactText], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `contact-${email.replace('@', '_at_')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    showToast('successToast', 'Contact exported successfully!');
    
    // Close modal if export was triggered from modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('contactDetailsModal'));
    if (modal) {
        modal.hide();
    }
}

// Load available email accounts for global selector
function loadGlobalEmailAccounts() {
    const globalAccountSelect = document.getElementById('globalAccountSelector');
    if (!globalAccountSelect) return;
    
    fetch('/api/email/accounts')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.accounts) {
                globalAccountSelect.innerHTML = '';
                
                // Add account options
                data.accounts.forEach(account => {
                    const option = document.createElement('option');
                    option.value = account.name;
                    option.textContent = account.email;
                    option.dataset.isDefault = account.is_default;
                    option.dataset.email = account.email;
                    
                    // Select the default account
                    if (account.is_default) {
                        option.selected = true;
                        currentGlobalAccount = account;
                        updateActiveAccountInfo(account);
                    }
                    globalAccountSelect.appendChild(option);
                });
                
                // If no default found but accounts exist, select the first
                if (!currentGlobalAccount && data.accounts.length > 0) {
                    const firstAccount = data.accounts[0];
                    currentGlobalAccount = firstAccount;
                    globalAccountSelect.value = firstAccount.name;
                    updateActiveAccountInfo(firstAccount);
                }
                
                // Load inbox for the selected account
                loadInboxForAccount(currentGlobalAccount);
                
            } else {
                globalAccountSelect.innerHTML = '<option value="">No accounts available</option>';
                updateActiveAccountInfo(null);
            }
        })
        .catch(error => {
            console.error('Error loading email accounts:', error);
            globalAccountSelect.innerHTML = '<option value="">Error loading accounts</option>';
            updateActiveAccountInfo(null);
        });
}

// Setup global account selector event listeners
function setupGlobalAccountSelector() {
    const globalAccountSelect = document.getElementById('globalAccountSelector');
    const testAccountBtn = document.getElementById('testGlobalAccount');
    
    if (globalAccountSelect) {
        globalAccountSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption && selectedOption.value) {
                currentGlobalAccount = {
                    name: selectedOption.value,
                    email: selectedOption.dataset.email,
                    is_default: selectedOption.dataset.isDefault === 'true'
                };
                updateActiveAccountInfo(currentGlobalAccount);
                
                // Reload inbox for new account
                loadInboxForAccount(currentGlobalAccount);
                
                console.log('Global account changed to:', currentGlobalAccount);
            }
        });
    }
    
    if (testAccountBtn) {
        testAccountBtn.addEventListener('click', function() {
            if (currentGlobalAccount) {
                testGlobalAccountConnection();
            }
        });
    }
}

// Update the active account info display
function updateActiveAccountInfo(account) {
    const activeAccountInfo = document.getElementById('activeAccountInfo');
    if (activeAccountInfo) {
        if (account) {
            activeAccountInfo.innerHTML = `<strong>${account.email}</strong>${account.is_default ? ' <span class="badge bg-primary">Default</span>' : ''}`;
        } else {
            activeAccountInfo.textContent = 'No account selected';
        }
    }
}

// Test the global account connection
function testGlobalAccountConnection() {
    if (!currentGlobalAccount) {
        showToast('errorToast', 'No account selected');
        return;
    }
    
    const testBtn = document.getElementById('testGlobalAccount');
    const originalHTML = testBtn.innerHTML;
    testBtn.disabled = true;
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    fetch(`/api/email/accounts/${currentGlobalAccount.name}/test`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `✓ ${currentGlobalAccount.email} connection successful`);
        } else {
            showToast('errorToast', `✗ ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error testing account:', error);
        showToast('errorToast', 'Failed to test account connection');
    })
    .finally(() => {
        testBtn.disabled = false;
        testBtn.innerHTML = originalHTML;
    });
}

// Email composition functions (for compose tab)
function generateEmailPreview() {
    const form = document.getElementById('composeForm');
    const composerType = document.getElementById('composerType').value || 'alt_subject';
    
    const leadInfo = {
        name: form.recipientName.value,
        email: form.recipientEmail.value,
        company: form.companyName.value,
        position: form.position.value
    };
    
    fetch('/api/preview_email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            contact_data: leadInfo,
            composer_type: composerType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.subject && data.body) {
            form.emailSubject.value = data.subject;
            form.emailBody.value = data.body;
        } else {
            showToast('errorToast', data.error || 'Failed to generate email preview');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('errorToast', 'Failed to generate email preview');
    });
}

// Load inbox emails for the selected account
function loadInboxForAccount(account) {
    if (!account) {
        console.log('No account selected for inbox');
        return;
    }
    
    console.log('Loading inbox for account:', account.email);
    
    // Update inbox tab to show loading state
    const inboxContainer = document.querySelector('#inbox-tab-pane .card-body');
    if (inboxContainer) {
        inboxContainer.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading emails for ${account.email}...</p>
            </div>
        `;
    }
    
    // Load emails for the specific account
    fetch(`/api/email/accounts/${account.name}/emails`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayAccountEmails(data.emails, account);
            } else {
                if (inboxContainer) {
                    inboxContainer.innerHTML = `
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            <strong>Unable to load emails for ${account.email}</strong>
                            <br><small>${data.message}</small>
                        </div>
                        <div class="text-center py-4">
                            <p class="text-muted">Check your email account configuration and try again.</p>
                            <button class="btn btn-primary" onclick="loadInboxForAccount(currentGlobalAccount)">
                                <i class="fas fa-refresh me-2"></i>Retry
                            </button>
                        </div>
                    `;
                }
            }
        })
        .catch(error => {
            console.error('Error loading emails:', error);
            if (inboxContainer) {
                inboxContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        <strong>Error loading emails</strong>
                        <br><small>Please check your connection and try again.</small>
                    </div>
                    <div class="text-center py-4">
                        <button class="btn btn-primary" onclick="loadInboxForAccount(currentGlobalAccount)">
                            <i class="fas fa-refresh me-2"></i>Retry
                        </button>
                    </div>
                `;
            }
        });
}

// Display emails for the account
function displayAccountEmails(emails, account) {
    const inboxContainer = document.querySelector('#inbox-tab-pane .card-body');
    if (!inboxContainer) return;
    
    let emailsHtml = `
        <div class="alert alert-success mb-4">
            <i class="fas fa-check-circle me-2"></i>
            <strong>Loaded ${emails.length} emails from ${account.email}</strong>
            <button class="btn btn-sm btn-outline-success ms-3" onclick="loadInboxForAccount(currentGlobalAccount)">
                <i class="fas fa-refresh me-1"></i>Refresh
            </button>
        </div>
    `;
    
    if (emails.length === 0) {
        emailsHtml += `
            <div class="text-center py-5">
                <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No emails found</h5>
                <p class="text-muted">No emails found in ${account.email}</p>
            </div>
        `;
    } else {
        emailsHtml += `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>From/To</th>
                            <th>Subject</th>
                            <th>Folder</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        emails.forEach((email, index) => {
            const date = email.date ? new Date(email.date).toLocaleDateString() : 'Unknown';
            const fromTo = email.folder === 'Sent' ? `To: ${email.to || 'Unknown'}` : `From: ${email.from || 'Unknown'}`;
            const subject = email.subject || '(No subject)';
            const folder = email.folder || 'Unknown';
            
            emailsHtml += `
                <tr>
                    <td>${date}</td>
                    <td class="text-truncate" style="max-width: 200px;">${fromTo}</td>
                    <td class="text-truncate" style="max-width: 300px;">${subject}</td>
                    <td><span class="badge ${folder === 'Sent' ? 'bg-success' : 'bg-primary'}">${folder}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewEmailDetails(${index}, '${account.name}')">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        emailsHtml += `
                    </tbody>
                </table>
            </div>
        `;
    }
    
    inboxContainer.innerHTML = emailsHtml;
    
    // Store emails globally for viewing details
    window.currentAccountEmails = emails;
}

// View email details
function viewEmailDetails(emailIndex, accountName) {
    if (!window.currentAccountEmails || !window.currentAccountEmails[emailIndex]) {
        showToast('errorToast', 'Email not found');
        return;
    }
    
    const email = window.currentAccountEmails[emailIndex];
    
    // Create modal content
    const modalContent = `
        <div class="row mb-3">
            <div class="col-sm-3"><strong>From:</strong></div>
            <div class="col-sm-9">${email.from || 'Unknown'}</div>
        </div>
        <div class="row mb-3">
            <div class="col-sm-3"><strong>To:</strong></div>
            <div class="col-sm-9">${email.to || 'Unknown'}</div>
        </div>
        <div class="row mb-3">
            <div class="col-sm-3"><strong>Subject:</strong></div>
            <div class="col-sm-9">${email.subject || '(No subject)'}</div>
        </div>
        <div class="row mb-3">
            <div class="col-sm-3"><strong>Date:</strong></div>
            <div class="col-sm-9">${email.date ? new Date(email.date).toLocaleString() : 'Unknown'}</div>
        </div>
        <div class="row mb-3">
            <div class="col-sm-3"><strong>Folder:</strong></div>
            <div class="col-sm-9"><span class="badge ${email.folder === 'Sent' ? 'bg-success' : 'bg-primary'}">${email.folder || 'Unknown'}</span></div>
        </div>
        <hr>
        <div>
            <strong>Content:</strong>
            <div class="mt-2 p-3 bg-light rounded">
                <pre style="white-space: pre-wrap; word-wrap: break-word;">${email.body || 'No content available'}</pre>
            </div>
        </div>
    `;
    
    // Show in existing email details modal
    const emailDetailsContent = document.getElementById('emailDetailsContent');
    if (emailDetailsContent) {
        emailDetailsContent.innerHTML = modalContent;
        
        const modal = new bootstrap.Modal(document.getElementById('emailDetailsModal'));
        modal.show();
    }
}

function sendComposedEmail(e) {
    e.preventDefault();
    const form = e.target;
    
    // Create a FormData object from the form
    const formData = new FormData();
    formData.append('recipient_email', document.getElementById('recipientEmail').value);
    formData.append('recipient_name', document.getElementById('recipientName').value);
    formData.append('preview_subject', document.getElementById('emailSubject').value);
    formData.append('preview_body', document.getElementById('emailBody').value);
    
    // Use the globally selected account
    if (currentGlobalAccount) {
        formData.append('account_name', currentGlobalAccount.name);
    }

    fetch('/api/send_email', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            // If response is not ok, read as text to avoid JSON parsing errors
            return response.text().then(text => {
                throw new Error(text || 'Server error with no message');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showToast('successToast', data.message || `Email sent successfully from ${currentGlobalAccount ? currentGlobalAccount.email : 'default account'}!`);
            form.reset();
        } else {
            showToast('errorToast', data.message || 'Failed to send email');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('errorToast', 'An error occurred while sending the email. Check console for details.');
    });
}

// Email history functions (for emails tab)
function showEmailDetails(button) {
    const emailIndex = button.dataset.emailIndex;
    const email = emailHistory[emailIndex];
    
    if (email) {
        const modalHtml = `
            <div class="modal fade" id="emailDetailsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Email Details</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p><strong>To:</strong> ${email.to}</p>
                            <p><strong>Subject:</strong> ${email.subject}</p>
                            <p><strong>Date:</strong> ${email.date}</p>
                            <p><strong>Status:</strong> ${email.status}</p>
                            <div class="mt-3">
                                <strong>Message:</strong>
                                <div class="email-preview mt-2">${email.body}</div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        let modal = document.getElementById('emailDetailsModal');
        if (modal) {
            modal.remove();
        }
        
        const div = document.createElement('div');
        div.innerHTML = modalHtml;
        modal = div.firstElementChild;
        document.body.appendChild(modal);
        
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

// Utility functions
function showToast(toastId, message) {
    let toast = document.getElementById(toastId);
    if (!toast) {
        // Create toast if it doesn't exist
        toast = createToast(toastId, message);
        document.body.appendChild(toast);
    } else {
        toast.querySelector('.toast-body').textContent = message;
    }
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

function createToast(id, message) {
    const isSuccess = id.includes('success');
    const toastHtml = `
        <div class="toast align-items-center text-bg-${isSuccess ? 'success' : 'danger'} border-0" 
             id="${id}" role="alert" aria-live="assertive" aria-atomic="true"
             style="position: fixed; top: 20px; right: 20px; z-index: 1055;">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    const div = document.createElement('div');
    div.innerHTML = toastHtml;
    return div.firstElementChild;
}

// Email connection testing function
function testEmailConnection() {
    // Show loading state
    const testButton = event.target;
    const originalText = testButton.innerHTML;
    testButton.innerHTML = '<div class="loading-spinner me-1"></div>Testing...';
    testButton.disabled = true;
    
    fetch('/api/email/test-connection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `Email connection successful! Connected to ${data.email}`);
        } else if (data.feature_disabled) {
            showToast('errorToast', 'Email reading feature is currently disabled');
        } else {
            // Create a modal to show detailed error message
            showEmailConfigModal(data.message, data.help_url);
        }
    })
    .catch(error => {
        console.error('Error testing email connection:', error);
        showToast('errorToast', 'Failed to test email connection');
    })
    .finally(() => {
        // Restore button
        testButton.innerHTML = originalText;
        testButton.disabled = false;
    });
}

function showEmailConfigModal(message, helpUrl) {
    const modalHtml = `
        <div class="modal fade" id="emailConfigModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-cog me-2"></i>Email Configuration Required
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            ${message.replace(/\n/g, '<br>')}
                        </div>
                        ${helpUrl ? `
                            <div class="text-center mt-3">
                                <a href="${helpUrl}" target="_blank" class="btn btn-primary">
                                    <i class="fas fa-external-link-alt me-2"></i>
                                    View Zoho IMAP Setup Guide
                                </a>
                            </div>
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" onclick="testEmailConnection()">
                            <i class="fas fa-sync me-1"></i>Test Again
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    let modal = document.getElementById('emailConfigModal');
    if (modal) {
        modal.remove();
    }
    
    const div = document.createElement('div');
    div.innerHTML = modalHtml;
    modal = div.firstElementChild;
    document.body.appendChild(modal);
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAllContacts') || document.getElementById('selectAllHeader');
    const contactCheckboxes = document.querySelectorAll('.contact-checkbox');
    const isChecked = selectAllCheckbox.checked;
    
    contactCheckboxes.forEach(checkbox => {
        checkbox.checked = isChecked;
    });
    
    // Sync both select all checkboxes
    const selectAllMain = document.getElementById('selectAllContacts');
    const selectAllHeader = document.getElementById('selectAllHeader');
    if (selectAllMain) selectAllMain.checked = isChecked;
    if (selectAllHeader) selectAllHeader.checked = isChecked;
    
    updateSelectionCount();
}

function updateSelectionCount() {
    const contactCheckboxes = document.querySelectorAll('.contact-checkbox:checked');
    const count = contactCheckboxes.length;
    const totalCheckboxes = document.querySelectorAll('.contact-checkbox').length;
    
    // Update selected contacts array
    selectedContacts = Array.from(contactCheckboxes).map(checkbox => {
        return JSON.parse(checkbox.getAttribute('data-contact').replace(/&apos;/g, "'"));
    });
    
    // Update UI
    const selectedCountElement = document.getElementById('selectedCount');
    const composeButton = document.getElementById('composeForSelectedBtn');
    const selectAllMain = document.getElementById('selectAllContacts');
    const selectAllHeader = document.getElementById('selectAllHeader');
    
    if (selectedCountElement) {
        selectedCountElement.textContent = `${count} selected`;
    }
    
    if (composeButton) {
        composeButton.disabled = count === 0;
    }
    
    // Update select all checkbox state
    if (selectAllMain && selectAllHeader) {
        const allSelected = count === totalCheckboxes && totalCheckboxes > 0;
        const someSelected = count > 0 && count < totalCheckboxes;
        
        selectAllMain.checked = allSelected;
        selectAllHeader.checked = allSelected;
        selectAllMain.indeterminate = someSelected;
        selectAllHeader.indeterminate = someSelected;
    }
}

function startBulkEmailComposition() {
    if (selectedContacts.length === 0) {
        showToast('errorToast', 'Please select at least one contact');
        return;
    }
    
    // Create and show the bulk email composition modal
    showBulkEmailComposer(selectedContacts);
}

function showBulkEmailComposer(contacts) {
    const modalHtml = `
        <div class="modal fade" id="bulkEmailModal" tabindex="-1" data-bs-backdrop="static">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-users me-2"></i>
                            Bulk Email Composition - ${contacts.length} Recipients
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div id="bulkEmailContent">
                            <!-- Content will be loaded here -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    let existingModal = document.getElementById('bulkEmailModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to page
    const div = document.createElement('div');
    div.innerHTML = modalHtml;
    const modal = div.firstElementChild;
    document.body.appendChild(modal);
    
    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    // Load the bulk email composer interface
    loadBulkEmailComposer(contacts);
}

function loadBulkEmailComposer(contacts) {
    const contentContainer = document.getElementById('bulkEmailContent');
    
    contentContainer.innerHTML = `
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">
                            <i class="fas fa-users me-2"></i>Selected Recipients (${contacts.length})
                        </h6>
                    </div>
                    <div class="card-body" style="max-height: 400px; overflow-y: auto;">
                        <div class="mb-3">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="selectAllForPreview" onchange="toggleSelectAllForPreview()">
                                <label class="form-check-label" for="selectAllForPreview">
                                    <strong>Select all for preview</strong>
                                </label>
                            </div>
                        </div>
                        ${contacts.map((contact, index) => `
                            <div class="d-flex align-items-center mb-2 p-2 border rounded">
                                <input type="checkbox" class="form-check-input me-2 preview-contact-checkbox" 
                                       value="${contact.email}" 
                                       data-index="${index}"
                                       onchange="updatePreviewSelection()">
                                <div class="contact-avatar me-2" style="width: 24px; height: 24px; font-size: 0.75rem;">
                                    ${contact.first_name ? contact.first_name[0].toUpperCase() : '?'}
                                </div>
                                <div class="flex-grow-1">
                                    <div class="fw-semibold">${contact.display_name || 'Unknown'}</div>
                                    <small class="text-muted">${contact.company || 'No company'}</small>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
            
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">
                            <i class="fas fa-edit me-2"></i>Email Composition
                        </h6>
                    </div>
                    <div class="card-body">
                        <div class="mb-3">
                            <label for="composerTypeSelect" class="form-label">
                                <i class="fas fa-palette me-1"></i>Email Style
                            </label>
                            <select class="form-select" id="composerTypeSelect">
                                <option value="alt_subject">AI Pilled Subject Line (Default)</option>
                                <option value="warm">Warm & Personal</option>
                            </select>
                            <small class="form-text text-muted">
                                Choose the email style and subject line approach
                            </small>
                        </div>
                        
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            <strong>Sending from:</strong> ${currentGlobalAccount ? currentGlobalAccount.email : 'Default account'}
                            <br><small class="text-muted">All bulk emails will be sent from the currently selected global account</small>
                        </div>
                        
                        <div class="mb-3">
                            <button class="btn btn-primary" id="generatePreviewBtn" onclick="generatePreviewEmails()" disabled>
                                <i class="fas fa-eye me-2"></i>Generate Preview for Selected
                            </button>
                            <small class="d-block text-muted mt-1">
                                <span id="previewSelectionCount">Select contacts to preview AI-generated emails</span>
                            </small>
                        </div>
                        
                        <div id="bulkEmailProgress" style="display: none;">
                            <div class="progress mb-3">
                                <div class="progress-bar" role="progressbar" style="width: 0%"></div>
                            </div>
                            <div class="text-center">
                                <span id="progressText">Generating emails...</span>
                            </div>
                        </div>
                        
                        <div id="emailPreviewContainer" style="display: none;">
                            <!-- Email previews will be shown here -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function generateBulkEmails() {
    const generateBtn = document.getElementById('generateBulkEmailsBtn');
    const progressContainer = document.getElementById('bulkEmailProgress');
    const progressBar = progressContainer.querySelector('.progress-bar');
    const progressText = document.getElementById('progressText');
    
    // Show progress and disable button
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';
    progressContainer.style.display = 'block';
    
    // Generate emails for each contact
    const emailPromises = selectedContacts.map((contact, index) => {
        return generateEmailForContact(contact, index);
    });
    
    let completedCount = 0;
    const totalCount = selectedContacts.length;
    let generatedEmails = [];
    
    // Process emails one by one to show progress
    processEmailsSequentially(emailPromises, 0, generatedEmails, completedCount, totalCount, progressBar, progressText)
        .then(emails => {
            // All emails generated successfully
            displayEmailPreviews(emails);
            progressContainer.style.display = 'none';
            generateBtn.style.display = 'none'; // Hide the generate button once done
        })
        .catch(error => {
            console.error('Error generating bulk emails:', error);
            showToast('errorToast', 'Failed to generate some emails. Please try again.');
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Generate AI Emails for All';
            progressContainer.style.display = 'none';
        });
}

function processEmailsSequentially(promises, index, results, completedCount, totalCount, progressBar, progressText) {
    if (index >= promises.length) {
        return Promise.resolve(results);
    }
    
    return promises[index]
        .then(email => {
            results.push(email);
            completedCount++;
            
            // Update progress
            const percentage = (completedCount / totalCount) * 100;
            progressBar.style.width = `${percentage}%`;
            progressText.textContent = `Generated ${completedCount} of ${totalCount} emails...`;
            
            // Process next email
            return processEmailsSequentially(promises, index + 1, results, completedCount, totalCount, progressBar, progressText);
        })
        .catch(error => {
            console.error(`Error generating email for contact ${index}:`, error);
            // Add a failed email entry and continue
            results.push({
                contact: selectedContacts[index],
                error: error.message || 'Failed to generate email',
                success: false
            });
            completedCount++;
            
            // Update progress
            const percentage = (completedCount / totalCount) * 100;
            progressBar.style.width = `${percentage}%`;
            progressText.textContent = `Generated ${completedCount} of ${totalCount} emails...`;
            
            // Continue with next email
            return processEmailsSequentially(promises, index + 1, results, completedCount, totalCount, progressBar, progressText);
        });
}

function generateEmailForContact(contact, index) {
    // Get the selected composer type
    const composerTypeSelect = document.getElementById('composerTypeSelect');
    const composerType = composerTypeSelect ? composerTypeSelect.value : 'alt_subject';
    
    // Call the existing AI email preview API with composer type
    // Use email as contact_id since Contact model doesn't have id field
    return fetch('/api/preview_email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            contact_id: contact.email,
            composer_type: composerType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.subject && data.body) {
            return {
                contact: contact,
                subject: data.subject,
                body: data.body,
                success: true,
                index: index,
                composer_type: composerType
            };
        } else {
            throw new Error(data.error || 'Failed to generate email content');
        }
    });
}

function displayEmailPreviews(emails, isPreviewMode = false) {
    const previewContainer = document.getElementById('emailPreviewContainer');
    const successfulEmails = emails.filter(email => email.success);
    const failedEmails = emails.filter(email => !email.success);
    
    let actionButtonsHtml = '';
    if (isPreviewMode) {
        const totalContacts = selectedContacts.length;
        const previewedCount = emails.length;
        const remainingCount = totalContacts - previewedCount;
        
        actionButtonsHtml = `
            <div>
                <button class="btn btn-outline-primary me-2" onclick="toggleAllPreviews()">
                    <i class="fas fa-eye me-1"></i>Toggle All
                </button>
                ${remainingCount > 0 ? `
                <button class="btn btn-success me-2" onclick="generateForAllContacts()">
                    <i class="fas fa-magic me-1"></i>Generate for All (${totalContacts})
                </button>
                ` : ''}
                <button class="btn btn-primary" onclick="sendPreviewedEmails()" ${successfulEmails.length === 0 ? 'disabled' : ''}>
                    <i class="fas fa-paper-plane me-2"></i>Send Previewed (${successfulEmails.length})
                </button>
            </div>
        `;
    } else {
        actionButtonsHtml = `
            <div>
                <button class="btn btn-outline-primary me-2" onclick="toggleAllPreviews()">
                    <i class="fas fa-eye me-1"></i>Toggle All
                </button>
                <button class="btn btn-success" onclick="sendAllEmails()" ${successfulEmails.length === 0 ? 'disabled' : ''}>
                    <i class="fas fa-paper-plane me-2"></i>Send All (${successfulEmails.length})
                </button>
            </div>
        `;
    }
    
    let previewHtml = `
        <div class="mb-3">
            <div class="alert alert-success">
                <i class="fas fa-check-circle me-2"></i>
                Generated <strong>${successfulEmails.length}</strong> emails successfully
                ${failedEmails.length > 0 ? `, ${failedEmails.length} failed` : ''}
                ${isPreviewMode ? ' (Preview Mode)' : ''}
            </div>
        </div>
        
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h6 class="mb-0">Email Previews</h6>
            ${actionButtonsHtml}
        </div>
    `;
    
    // Add previews for successful emails
    successfulEmails.forEach((email, index) => {
        previewHtml += `
            <div class="card mb-3 email-preview-card">
                <div class="card-header">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <div class="d-flex align-items-center">
                                <div class="contact-avatar me-2" style="width: 24px; height: 24px; font-size: 0.75rem;">
                                    ${email.contact.first_name ? email.contact.first_name[0].toUpperCase() : '?'}
                                </div>
                                <div>
                                    <strong>${email.contact.display_name || 'Unknown'}</strong>
                                    <br><small class="text-muted">${email.contact.email}</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4 text-end">
                            <button class="btn btn-outline-secondary btn-sm" onclick="toggleEmailPreview(${index})">
                                <i class="fas fa-eye me-1"></i>Preview
                            </button>
                        </div>
                    </div>
                </div>
                <div class="card-body email-preview-body" id="preview-${index}" style="display: none;">
                    <div class="mb-3">
                        <strong>Subject:</strong> ${email.subject}
                    </div>
                    <div class="mb-3">
                        <strong>Message:</strong>
                        <div class="mt-2 p-3 bg-light rounded">
                            ${email.body.replace(/\n/g, '<br>')}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    // Add failed emails section if any
    if (failedEmails.length > 0) {
        previewHtml += `
            <div class="mt-4">
                <h6 class="text-danger">Failed to Generate (${failedEmails.length})</h6>
                ${failedEmails.map(email => `
                    <div class="alert alert-danger">
                        <strong>${email.contact.display_name || 'Unknown'}</strong> (${email.contact.email}): 
                        ${email.error}
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    previewContainer.innerHTML = previewHtml;
    previewContainer.style.display = 'block';
    
    // Store successful emails globally for sending
    if (isPreviewMode) {
        window.previewedEmails = successfulEmails;
    } else {
        window.generatedEmails = successfulEmails;
    }
}

function toggleEmailPreview(index) {
    const previewBody = document.getElementById(`preview-${index}`);
    const isVisible = previewBody.style.display !== 'none';
    
    previewBody.style.display = isVisible ? 'none' : 'block';
}

function toggleAllPreviews() {
    const previewBodies = document.querySelectorAll('.email-preview-body');
    const anyVisible = Array.from(previewBodies).some(body => body.style.display !== 'none');
    
    previewBodies.forEach(body => {
        body.style.display = anyVisible ? 'none' : 'block';
    });
}

function sendAllEmails() {
    if (!window.generatedEmails || window.generatedEmails.length === 0) {
        showToast('errorToast', 'No emails to send');
        return;
    }
    
    // Show confirmation dialog
    if (!confirm(`Are you sure you want to send ${window.generatedEmails.length} emails?`)) {
        return;
    }
    
    const sendButton = document.querySelector('button[onclick="sendAllEmails()"]');
    sendButton.disabled = true;
    sendButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Sending...';
    
    // Get the selected composer type
    const composerTypeSelect = document.getElementById('composerTypeSelect');
    const composerType = composerTypeSelect ? composerTypeSelect.value : 'alt_subject';
    
    // Use the globally selected account
    const account_name = currentGlobalAccount ? currentGlobalAccount.name : '';
    
    // Prepare recipients data for bulk sending
    const recipients_data = window.generatedEmails.map(email => ({
        contact_id: email.contact.email
    }));
    
    // Send bulk emails
    fetch('/api/send_bulk_emails', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            recipients_data: recipients_data,
            composer_type: composerType,
            account_name: account_name
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.sent && data.sent.length > 0) {
            showToast('successToast', `Successfully sent ${data.sent.length} emails!`);
            
            // Close the bulk email modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('bulkEmailModal'));
            if (modal) {
                modal.hide();
            }
            
            // Refresh the page to update contact status
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            const failedCount = data.failed ? data.failed.length : 0;
            showToast('errorToast', `Failed to send emails. ${failedCount} failures.`);
        }
    })
    .catch(error => {
        console.error('Error sending bulk emails:', error);
        showToast('errorToast', 'Error sending emails: ' + error.message);
    })
    .finally(() => {
        sendButton.disabled = false;
        sendButton.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Send All';
    });
}

function toggleSelectAllForPreview() {
    const selectAllCheckbox = document.getElementById('selectAllForPreview');
    const contactCheckboxes = document.querySelectorAll('.preview-contact-checkbox');
    const isChecked = selectAllCheckbox.checked;
    
    contactCheckboxes.forEach(checkbox => {
        checkbox.checked = isChecked;
    });
    
    updatePreviewSelection();
}

function updatePreviewSelection() {
    const contactCheckboxes = document.querySelectorAll('.preview-contact-checkbox:checked');
    const count = contactCheckboxes.length;
    const totalCheckboxes = document.querySelectorAll('.preview-contact-checkbox').length;
    
    // Update selected contacts array for preview
    const selectedForPreview = Array.from(contactCheckboxes).map(checkbox => {
        const index = parseInt(checkbox.getAttribute('data-index'));
        return selectedContacts[index];
    });
    
    // Update UI
    const previewSelectionCountElement = document.getElementById('previewSelectionCount');
    const generateButton = document.getElementById('generatePreviewBtn');
    const selectAllCheckbox = document.getElementById('selectAllForPreview');
    
    if (previewSelectionCountElement) {
        if (count === 0) {
            previewSelectionCountElement.textContent = 'Select contacts to preview AI-generated emails';
        } else {
            previewSelectionCountElement.textContent = `${count} contact${count > 1 ? 's' : ''} selected for preview`;
        }
    }
    
    if (generateButton) {
        generateButton.disabled = count === 0;
    }
    
    // Update select all checkbox state
    if (selectAllCheckbox) {
        const allSelected = count === totalCheckboxes && totalCheckboxes > 0;
        const someSelected = count > 0 && count < totalCheckboxes;
        
        selectAllCheckbox.checked = allSelected;
        selectAllCheckbox.indeterminate = someSelected;
    }
    
    // Store selected contacts for preview globally
    window.selectedForPreview = selectedForPreview;
}

function generatePreviewEmails() {
    if (!window.selectedForPreview || window.selectedForPreview.length === 0) {
        showToast('errorToast', 'Please select at least one contact for preview');
        return;
    }
    
    const generateBtn = document.getElementById('generatePreviewBtn');
    const progressContainer = document.getElementById('bulkEmailProgress');
    const progressBar = progressContainer.querySelector('.progress-bar');
    const progressText = document.getElementById('progressText');
    
    // Show progress and disable button
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';
    progressContainer.style.display = 'block';
    
    // Generate emails for selected contacts only
    const emailPromises = window.selectedForPreview.map((contact, index) => {
        return generateEmailForContact(contact, index);
    });
    
    let completedCount = 0;
    const totalCount = window.selectedForPreview.length;
    let generatedEmails = [];
    
    // Process emails one by one to show progress
    processEmailsSequentially(emailPromises, 0, generatedEmails, completedCount, totalCount, progressBar, progressText)
        .then(emails => {
            // All emails generated successfully
            displayEmailPreviews(emails, true); // Pass true to indicate this is a preview mode
            progressContainer.style.display = 'none';
            generateBtn.style.display = 'none'; // Hide the generate button once done
        })
        .catch(error => {
            console.error('Error generating preview emails:', error);
            showToast('errorToast', 'Failed to generate some preview emails. Please try again.');
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fas fa-eye me-2"></i>Generate Preview for Selected';
            progressContainer.style.display = 'none';
        });
}

function generateForAllContacts() {
    if (selectedContacts.length === 0) {
        showToast('errorToast', 'No contacts available');
        return;
    }
    
    // Show confirmation
    if (!confirm(`Generate emails for all ${selectedContacts.length} contacts? This will replace the current previews.`)) {
        return;
    }
    
    // Reset the preview container and show progress
    const previewContainer = document.getElementById('emailPreviewContainer');
    const progressContainer = document.getElementById('bulkEmailProgress');
    const progressBar = progressContainer.querySelector('.progress-bar');
    const progressText = document.getElementById('progressText');
    
    previewContainer.style.display = 'none';
    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';
    progressText.textContent = 'Generating emails for all contacts...';
    
    // Generate emails for all contacts
    const emailPromises = selectedContacts.map((contact, index) => {
        return generateEmailForContact(contact, index);
    });
    
    let completedCount = 0;
    const totalCount = selectedContacts.length;
    let generatedEmails = [];
    
    // Process emails one by one to show progress
    processEmailsSequentially(emailPromises, 0, generatedEmails, completedCount, totalCount, progressBar, progressText)
        .then(emails => {
            // All emails generated successfully
            displayEmailPreviews(emails, false); // Pass false for full generation mode
            progressContainer.style.display = 'none';
        })
        .catch(error => {
            console.error('Error generating all emails:', error);
            showToast('errorToast', 'Failed to generate some emails. Please try again.');
            progressContainer.style.display = 'none';
        });
}

function sendPreviewedEmails() {
    if (!window.previewedEmails || window.previewedEmails.length === 0) {
        showToast('errorToast', 'No emails to send');
        return;
    }
    
    // Show confirmation dialog
    if (!confirm(`Are you sure you want to send ${window.previewedEmails.length} emails?`)) {
        return;
    }
    
    const sendButton = document.querySelector('button[onclick="sendPreviewedEmails()"]');
    sendButton.disabled = true;
    sendButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Sending...';
    
    // Get the selected composer type
    const composerTypeSelect = document.getElementById('composerTypeSelect');
    const composerType = composerTypeSelect ? composerTypeSelect.value : 'alt_subject';
    
    // Use the globally selected account
    const account_name = currentGlobalAccount ? currentGlobalAccount.name : '';
    
    // Prepare recipients data for bulk sending
    const recipients_data = window.previewedEmails.map(email => ({
        contact_id: email.contact.email
    }));
    
    // Send bulk emails
    fetch('/api/send_bulk_emails', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            recipients_data: recipients_data,
            composer_type: composerType,
            account_name: account_name
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.sent && data.sent.length > 0) {
            showToast('successToast', `Successfully sent ${data.sent.length} emails!`);
            
            // Close the bulk email modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('bulkEmailModal'));
            if (modal) {
                modal.hide();
            }
            
            // Refresh the page to update contact status
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            const failedCount = data.failed ? data.failed.length : 0;
            showToast('errorToast', `Failed to send emails. ${failedCount} failures.`);
        }
    })
    .catch(error => {
        console.error('Error sending bulk emails:', error);
        showToast('errorToast', 'Error sending emails: ' + error.message);
    })
    .finally(() => {
        sendButton.disabled = false;
        sendButton.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Send Previewed';
    });
}

// Add Contact Form Functions
function saveNewContact() {
    const form = document.getElementById('addContactForm');
    const formData = new FormData(form);
    
    // Convert FormData to JSON
    const contactData = {};
    for (let [key, value] of formData.entries()) {
        contactData[key] = value.trim();
    }
    
    // Validate required fields
    if (!contactData.email) {
        showToast('errorToast', 'Email address is required');
        return;
    }
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(contactData.email)) {
        showToast('errorToast', 'Please enter a valid email address');
        return;
    }
    
    // Show loading state
    const saveBtn = document.getElementById('saveContactBtn');
    const originalText = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
    
    // Send request to backend
    fetch('/api/contacts/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(contactData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', data.message);
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addContactModal'));
            if (modal) {
                modal.hide();
            }
            
            // Reset form
            resetAddContactForm();
            
            // Refresh the page to show the new contact
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showToast('errorToast', data.message || 'Failed to add contact');
        }
    })
    .catch(error => {
        console.error('Error adding contact:', error);
        showToast('errorToast', 'An error occurred while adding the contact');
    })
    .finally(() => {
        // Restore button state
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalText;
    });
}

function resetAddContactForm() {
    const form = document.getElementById('addContactForm');
    if (form) {
        form.reset();
        
        // Clear any validation states
        const inputs = form.querySelectorAll('.form-control');
        inputs.forEach(input => {
            input.classList.remove('is-valid', 'is-invalid');
        });
    }
}

// Auto-format URL fields
document.addEventListener('DOMContentLoaded', function() {
    const urlFields = ['addCompanyDomain', 'addLinkedInProfile'];
    
    urlFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('blur', function() {
                let value = this.value.trim();
                if (value && !value.startsWith('http://') && !value.startsWith('https://')) {
                    this.value = 'https://' + value;
                }
            });
        }
    });
    
    // Auto-generate full name
    const firstNameField = document.getElementById('addFirstName');
    const lastNameField = document.getElementById('addLastName');
    
    if (firstNameField && lastNameField) {
        function updateFullName() {
            const firstName = firstNameField.value.trim();
            const lastName = lastNameField.value.trim();
            // This is just for display purposes - the backend will handle full_name generation
        }
        
        firstNameField.addEventListener('input', updateFullName);
        lastNameField.addEventListener('input', updateFullName);
    }
});

// Function to handle sending test emails
function sendTestEmails(event) {
    event.preventDefault(); // Prevent default form submission

    const emailAddresses = document.getElementById('testEmailAddresses').value.trim();
    const subject = document.getElementById('testEmailSubject').value.trim();
    const body = document.getElementById('testEmailBody').value.trim();
    const statusDiv = document.getElementById('testEmailStatus');

    if (!emailAddresses || !body) {
        statusDiv.innerHTML = `<div class="alert alert-danger">Email addresses and body are required.</div>`;
        return;
    }

    const recipient_emails = emailAddresses.split(',').map(email => email.trim()).filter(email => email);

    if (recipient_emails.length === 0) {
        statusDiv.innerHTML = `<div class="alert alert-danger">Please enter at least one valid email address.</div>`;
        return;
    }

    statusDiv.innerHTML = `<div class="alert alert-info">Sending test emails...</div>`;

    fetch('/api/send_test_email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            recipient_emails: recipient_emails,
            subject: subject || 'Test Email', // Use default if subject is empty
            body: body 
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            let resultMessage = `<div class="alert alert-success">Test email process completed.`;
            if (data.results) {
                if (data.results.sent && data.results.sent.length > 0) {
                    resultMessage += `<br>Successfully sent to: ${data.results.sent.join(', ')}.`;
                }
                if (data.results.failed && data.results.failed.length > 0) {
                    resultMessage += `<br>Failed to send to: ${data.results.failed.join(', ')}.`;
                }
            }
            resultMessage += `</div>`;
            statusDiv.innerHTML = resultMessage;
            document.getElementById('sendTestEmailForm').reset(); // Reset the form
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger">Error: ${data.message || 'Failed to send test emails.'}</div>`;
        }
    })
    .catch(error => {
        console.error('Error sending test emails:', error);
        statusDiv.innerHTML = `<div class="alert alert-danger">An unexpected error occurred. Check console for details.</div>`;
    });
}

// Company Management Functions
document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners for company buttons
    const extractCompaniesBtn = document.getElementById('extractCompaniesBtn');
    const researchCompaniesBtn = document.getElementById('researchCompaniesBtn');
    
    if (extractCompaniesBtn) {
        extractCompaniesBtn.addEventListener('click', extractCompaniesFromContacts);
    }
    
    if (researchCompaniesBtn) {
        researchCompaniesBtn.addEventListener('click', researchCompanies);
    }
    
    // Add event listeners for companies pagination
    setupCompaniesPagination();
});

function setupCompaniesPagination() {
    // Companies per page selector
    const companiesPerPageSelect = document.getElementById('companiesPerPage');
    if (companiesPerPageSelect) {
        companiesPerPageSelect.addEventListener('change', function() {
            changeCompaniesPage(1); // Reset to first page when changing per page
        });
    }
    
    // Companies pagination links
    document.querySelectorAll('.companies-page-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = parseInt(this.getAttribute('data-companies-page'));
            if (page && !this.parentElement.classList.contains('disabled')) {
                changeCompaniesPage(page);
            }
        });
    });
    
    // Individual company research buttons
    document.querySelectorAll('.research-company-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const companyId = this.getAttribute('data-company-id');
            const companyName = this.getAttribute('data-company-name');
            researchSingleCompany(companyId, companyName, this);
        });
    });
    
    // Company view buttons
    document.querySelectorAll('.company-view-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            const companyId = this.getAttribute('data-company-id');
            if (companyId) {
                loadCompanyDetails(companyId);
            }
        });
    });
}

function changeCompaniesPage(page) {
    // Get current per page value
    const perPageSelect = document.getElementById('companiesPerPage');
    const perPage = perPageSelect ? perPageSelect.value : 10;
    
    // Show loading state
    const companiesContainer = document.getElementById('companies-table-container');
    const originalContent = companiesContainer.innerHTML;
    
    companiesContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading companies...</p>
        </div>
    `;
    
    // Fetch companies for the requested page
    fetch(`/api/companies?page=${page}&per_page=${perPage}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayCompaniesTable(data.companies, data.pagination);
                // Re-setup pagination after content is loaded
                setTimeout(setupCompaniesPagination, 100);
            } else {
                throw new Error(data.message || 'Failed to load companies');
            }
        })
        .catch(error => {
            console.error('Error loading companies:', error);
            companiesContainer.innerHTML = originalContent;
            showToast('errorToast', 'Failed to load companies: ' + error.message);
        });
}

function displayCompaniesTable(companies, pagination) {
    const companiesContainer = document.getElementById('companies-table-container');
    
    let html = `
    <div class="table-responsive">
        <table class="table table-hover">
            <thead class="table-light">
                <tr>
                    <th>Company Name</th>
                    <th>Website</th>
                    <th>Research Summary</th>
                    <th>Created At</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    if (companies && companies.length > 0) {
        companies.forEach(company => {
            const createdAt = company.created_at ? new Date(company.created_at).toLocaleDateString() : 'N/A';
            const researchSummary = company.company_research ? 
                (company.company_research.length > 100 ? 
                    company.company_research.substring(0, 100) + '...' : 
                    company.company_research) : '';
            
            html += `
                <tr>
                    <td><strong>${company.company_name || ''}</strong></td>
                    <td><a href="${company.website_url || '#'}" target="_blank">${company.website_url || ''}</a></td>
                    <td>${researchSummary}</td>
                    <td>${createdAt}</td>
                    <td>
                        <div class="btn-group" role="group">
                            <button class="btn btn-sm btn-outline-primary company-view-btn" data-bs-toggle="modal" data-bs-target="#companyDetailModal" data-company-id="${company.id}">
                                <i class="fas fa-eye"></i> View
                            </button>
                            ${company.needs_research ? 
                                `<button class="btn btn-sm btn-outline-warning research-company-btn" data-company-id="${company.id}" data-company-name="${company.company_name}" title="Research this company">
                                    <i class="fas fa-search"></i> Research
                                </button>` :
                                `<button class="btn btn-sm btn-outline-success research-company-btn" data-company-id="${company.id}" data-company-name="${company.company_name}" title="Re-research this company">
                                    <i class="fas fa-redo"></i> Re-research
                                </button>`
                            }
                        </div>
                    </td>
                </tr>
            `;
        });
    } else {
        html += `
            <tr>
                <td colspan="5" class="text-center">No companies found.</td>
            </tr>
        `;
    }
    
    html += `
            </tbody>
        </table>
    </div>
    
    <!-- Pagination Controls -->
    <div class="row mb-3">
        <div class="col-md-6">
            <div class="d-flex align-items-center">
                <label for="companiesPerPage" class="me-2">Show:</label>
                <select id="companiesPerPage" class="form-select" style="width: auto;">
                    <option value="5" ${pagination.per_page == 5 ? 'selected' : ''}>5 per page</option>
                    <option value="10" ${pagination.per_page == 10 ? 'selected' : ''}>10 per page</option>
                    <option value="25" ${pagination.per_page == 25 ? 'selected' : ''}>25 per page</option>
                    <option value="50" ${pagination.per_page == 50 ? 'selected' : ''}>50 per page</option>
                </select>
            </div>
        </div>
        <div class="col-md-6">
            <nav aria-label="Page navigation">
                <ul class="pagination justify-content-end mb-0">
                    <li class="page-item ${pagination.current_page == 1 ? 'disabled' : ''}">
                        <a class="page-link companies-page-link" href="#" data-companies-page="${pagination.current_page - 1}">
                            <i class="fas fa-chevron-left"></i>
                        </a>
                    </li>
                    <li class="page-item active">
                        <span class="page-link">${pagination.current_page} of ${pagination.total_pages}</span>
                    </li>
                    <li class="page-item ${pagination.current_page == pagination.total_pages ? 'disabled' : ''}">
                        <a class="page-link companies-page-link" href="#" data-companies-page="${pagination.current_page + 1}">
                            <i class="fas fa-chevron-right"></i>
                        </a>
                    </li>
                </ul>
            </nav>
        </div>
    </div>
    `;
    
    companiesContainer.innerHTML = html;
}

function extractCompaniesFromContacts() {
    const extractBtn = document.getElementById('extractCompaniesBtn');
    const originalText = extractBtn.innerHTML;
    
    // Show loading state
    extractBtn.disabled = true;
    extractBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Extracting...';
    
    fetch('/api/companies/extract', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', data.message);
            
            // Refresh the companies table
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            showToast('errorToast', data.message || 'Failed to extract companies');
        }
    })
    .catch(error => {
        console.error('Error extracting companies:', error);
        showToast('errorToast', 'An error occurred while extracting companies');
    })
    .finally(() => {
        // Restore button state
        extractBtn.disabled = false;
        extractBtn.innerHTML = originalText;
    });
}

function researchCompanies() {
    const researchBtn = document.getElementById('researchCompaniesBtn');
    const originalText = researchBtn.innerHTML;
    
    // Ask user for number of companies to research
    const maxCompanies = prompt('How many companies would you like to research? (Default: 10)', '10');
    
    if (maxCompanies === null) {
        return; // User cancelled
    }
    
    const maxCompaniesNum = parseInt(maxCompanies) || 10;
    
    // Show loading state
    researchBtn.disabled = true;
    researchBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Starting Research...';
    
    fetch('/api/companies/research', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            max_companies: maxCompaniesNum
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', data.message);
            
            // Update button to show research is in progress
            researchBtn.innerHTML = '<i class="fas fa-cog fa-spin me-1"></i>Research Running...';
            
            // Keep the button disabled for a few minutes to prevent multiple starts
            setTimeout(() => {
                researchBtn.disabled = false;
                researchBtn.innerHTML = originalText;
            }, 120000); // Re-enable after 2 minutes
            
        } else {
            showToast('errorToast', data.message || 'Failed to start company research');
            researchBtn.disabled = false;
            researchBtn.innerHTML = originalText;
        }
    })
    .catch(error => {
        console.error('Error starting company research:', error);
        showToast('errorToast', 'An error occurred while starting company research');
        researchBtn.disabled = false;
        researchBtn.innerHTML = originalText;
    });
}

function researchSingleCompany(companyId, companyName, buttonElement) {
    const originalText = buttonElement.innerHTML;
    
    // Confirm with user
    if (!confirm(`Start AI research for "${companyName}"? This will run in the background and may take a few minutes.`)) {
        return;
    }
    
    // Show loading state
    buttonElement.disabled = true;
    buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Researching...';
    
    fetch(`/api/companies/${companyId}/research`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', data.message);
            
            // Update button to show research is in progress
            buttonElement.innerHTML = '<i class="fas fa-cog fa-spin me-1"></i>Researching...';
            buttonElement.classList.remove('btn-outline-warning', 'btn-outline-success');
            buttonElement.classList.add('btn-outline-info');
            
            // Keep the button disabled for a few minutes to prevent multiple starts
            setTimeout(() => {
                buttonElement.disabled = false;
                buttonElement.innerHTML = '<i class="fas fa-redo"></i> Re-research';
                buttonElement.classList.remove('btn-outline-info');
                buttonElement.classList.add('btn-outline-success');
                buttonElement.title = 'Re-research this company';
            }, 180000); // Re-enable after 3 minutes
            
        } else {
            showToast('errorToast', data.message || 'Failed to start company research');
            buttonElement.disabled = false;
            buttonElement.innerHTML = originalText;
        }
    })
    .catch(error => {
        console.error('Error starting company research:', error);
        showToast('errorToast', 'An error occurred while starting company research');
        buttonElement.disabled = false;
        buttonElement.innerHTML = originalText;
    });
}

function loadCompanyDetails(companyId) {
    // Reset modal content to loading state
    const modalContent = document.getElementById('company-details-content');
    const modalTitle = document.getElementById('companyDetailModalLabel');
    
    modalContent.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading company details...</p>
        </div>
    `;
    modalTitle.textContent = 'Company Details';
    
    // Fetch company details
    fetch(`/api/companies/${companyId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayCompanyDetails(data.company);
            } else {
                throw new Error(data.message || 'Failed to load company details');
            }
        })
        .catch(error => {
            console.error('Error loading company details:', error);
            modalContent.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Failed to load company details: ${error.message}
                </div>
            `;
        });
}

function displayCompanyDetails(company) {
    const modalContent = document.getElementById('company-details-content');
    const modalTitle = document.getElementById('companyDetailModalLabel');
    
    // Update modal title
    modalTitle.textContent = company.company_name || 'Company Details';
    
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
}

function toggleSelectAllSearchResults() {
    const selectAllCheckbox = document.getElementById('selectAllSearchResults');
    const contactCheckboxes = document.querySelectorAll('.contact-checkbox');
    const isChecked = selectAllCheckbox.checked;
    
    contactCheckboxes.forEach(checkbox => {
        checkbox.checked = isChecked;
    });
    
    updateSelectionCount();
}