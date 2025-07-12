// SalesBot CRM - Dashboard JavaScript

// Global variables
let currentContacts = [];
let emailHistory = window.emailHistoryData || [];
let currentContactEmail = null; // For modal export functionality
let selectedContacts = []; // For bulk email composition
let currentGlobalAccount = null; // Currently selected global account
let currentCompanyId = null; // For editing company details

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
    
    // Setup GTM campaign tab event listener
    setupCampaignTabListener();
}

function setupCampaignTabListener() {
    const gtmCampaignTab = document.getElementById('gtm-campaign-tab');
    if (gtmCampaignTab) {
        // Load campaigns when GTM campaign tab is shown
        gtmCampaignTab.addEventListener('shown.bs.tab', function (e) {
            console.log('GTM Campaign tab shown, loading campaigns...');
            loadCampaigns();
        });
        
        // If GTM campaign tab is already active on page load, load campaigns immediately
        if (gtmCampaignTab.classList.contains('active')) {
            console.log('GTM Campaign tab is already active, loading campaigns...');
            loadCampaigns();
        }
    }
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
    // Contacts per-page selector
    const perPageSelect = document.getElementById('perPage');
    if (perPageSelect) {
        perPageSelect.addEventListener('change', function() {
            addPaginationLoadingState('contactsContainer');
            changePage(1);
        });
    }

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

    // Add Contact modal reset and setup
    const addContactModal = document.getElementById('addContactModal');
    if (addContactModal) {
        addContactModal.addEventListener('hidden.bs.modal', function() {
            resetAddContactForm();
        });
        addContactModal.addEventListener('show.bs.modal', function() {
            loadCompaniesForDropdown();
        });
    }
    
    // Create new company checkbox handler
    const createNewCompanyCheckbox = document.getElementById('createNewCompany');
    if (createNewCompanyCheckbox) {
        createNewCompanyCheckbox.addEventListener('change', toggleNewCompanyFields);
    }

    const sendTestEmailForm = document.getElementById('sendTestEmailForm');
    if (sendTestEmailForm) {
        sendTestEmailForm.addEventListener('submit', sendTestEmails);
    }
    
    // Setup enhanced pagination for all tabs
    setupEmailHistoryPagination();
    setupInboxPagination();
    setupCompaniesPagination();
    
    // Initialize pagination event delegation
    reinitializePagination();
}

function setupEmailHistoryPagination() {
    // Email history per page selector
    const emailHistoryPerPageSelect = document.getElementById('emailHistoryPerPage');
    if (emailHistoryPerPageSelect) {
        emailHistoryPerPageSelect.addEventListener('change', function() {
            paginateEmailHistory(1); // Reset to first page when changing per page
        });
    }
    
    // Initialize client-side pagination
    paginateEmailHistory(1);
    
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

// Client-side pagination for email history
let currentEmailHistoryPage = 1;
let emailHistoryPerPage = 25;

function paginateEmailHistory(page) {
    const perPageSelect = document.getElementById('emailHistoryPerPage');
    emailHistoryPerPage = perPageSelect ? parseInt(perPageSelect.value) : 25;
    currentEmailHistoryPage = page;
    
    // Get all email history rows
    const allRows = document.querySelectorAll('.email-history-row');
    const totalRows = allRows.length;
    
    if (totalRows === 0) return;
    
    // Calculate pagination
    const totalPages = Math.ceil(totalRows / emailHistoryPerPage);
    const startIndex = (page - 1) * emailHistoryPerPage;
    const endIndex = startIndex + emailHistoryPerPage;
    
    // Hide all rows first
    allRows.forEach((row, index) => {
        if (index >= startIndex && index < endIndex) {
            row.style.display = '';
            row.classList.remove('d-none');
        } else {
            row.style.display = 'none';
            row.classList.add('d-none');
        }
    });
    
    // Update summary
    const summaryElement = document.getElementById('emailHistorySummary');
    if (summaryElement) {
        const showingStart = startIndex + 1;
        const showingEnd = Math.min(endIndex, totalRows);
        summaryElement.innerHTML = `Showing ${showingStart} to ${showingEnd} of <strong>${totalRows}</strong> emails`;
    }
    
    // Generate pagination controls
    generateEmailHistoryPagination(page, totalPages);
}

function generateEmailHistoryPagination(currentPage, totalPages) {
    const paginationNav = document.getElementById('emailHistoryPaginationNav');
    if (!paginationNav || totalPages <= 1) {
        if (paginationNav) paginationNav.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // First Page
    html += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="paginateEmailHistory(1)" title="First page" aria-label="First page">
                <i class="fas fa-angle-double-left"></i>
            </a>
        </li>
    `;
    
    // Previous Page
    html += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="paginateEmailHistory(${currentPage - 1})" title="Previous page" aria-label="Previous page">
                <i class="fas fa-chevron-left"></i>
            </a>
        </li>
    `;
    
    // Page Numbers
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    // Show first page and ellipsis if needed
    if (startPage > 1) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="paginateEmailHistory(1)">1</a>
            </li>
        `;
        if (startPage > 2) {
            html += `
                <li class="page-item disabled">
                    <span class="page-link" aria-disabled="true">…</span>
                </li>
            `;
        }
    }
    
    // Show page numbers around current page
    for (let pageNum = startPage; pageNum <= endPage; pageNum++) {
        if (pageNum === currentPage) {
            html += `
                <li class="page-item active">
                    <span class="page-link" aria-current="page">${pageNum}</span>
                </li>
            `;
        } else {
            html += `
                <li class="page-item">
                    <a class="page-link" href="#" onclick="paginateEmailHistory(${pageNum})">${pageNum}</a>
                </li>
            `;
        }
    }
    
    // Show ellipsis and last page if needed
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            html += `
                <li class="page-item disabled">
                    <span class="page-link" aria-disabled="true">…</span>
                </li>
            `;
        }
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="paginateEmailHistory(${totalPages})">${totalPages}</a>
            </li>
        `;
    }
    
    // Next Page
    html += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="paginateEmailHistory(${currentPage + 1})" title="Next page" aria-label="Next page">
                <i class="fas fa-chevron-right"></i>
            </a>
        </li>
    `;
    
    // Last Page
    html += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="paginateEmailHistory(${totalPages})" title="Last page" aria-label="Last page">
                <i class="fas fa-angle-double-right"></i>
            </a>
        </li>
    `;
    
    paginationNav.innerHTML = html;
}

function changeEmailHistoryPage(page) {
    // Use client-side pagination instead of page reload
    paginateEmailHistory(page);
}

function refreshEmailHistory() {
    const historyContainer = document.getElementById('emailHistoryTableBody');
    if (!historyContainer) return;
    
    // Remember current scroll position
    const currentScrollY = window.scrollY;
    
    // Show loading state
    historyContainer.closest('.table-responsive').classList.add('table-loading');
    
    // Simulate refresh (you can replace this with actual API call)
    setTimeout(() => {
        historyContainer.closest('.table-responsive').classList.remove('table-loading');
        showToast('successToast', 'Email history refreshed!');
        
        // Restore scroll position
        setTimeout(() => {
            window.scrollTo({
                top: currentScrollY,
                behavior: 'smooth'
            });
        }, 100);
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
    
    // Remember current scroll position
    const currentScrollY = window.scrollY;
    
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
    
    // Navigate and restore scroll position
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
    console.log('changePage function called with page:', page);
    const perPageSelect = document.getElementById('perPage');
    const perPage = perPageSelect ? perPageSelect.value : 10;
    console.log('Current per page value:', perPage);
    
    const url = new URL(window.location.href);
    console.log('Current URL:', url.toString());
    
    // Use the correct parameter names that the backend expects
    url.searchParams.set('contacts_page', page);  // Changed from 'page' to 'contacts_page'
    url.searchParams.set('per_page', perPage);
    
    console.log('New URL to navigate to:', url.toString());
    console.log('About to navigate...');
    
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
    
    // Validate company fields if creating new company
    const createNewCompanyCheckbox = document.getElementById('createNewCompany');
    if (createNewCompanyCheckbox && createNewCompanyCheckbox.checked) {
        const newCompanyName = contactData.new_company_name;
        const newCompanyWebsite = contactData.new_company_website;
        
        if (!newCompanyName) {
            showToast('errorToast', 'Company name is required when creating a new company');
            return;
        }
        
        if (!newCompanyWebsite) {
            showToast('errorToast', 'Company website is required when creating a new company');
            return;
        }
        
        // Basic URL validation
        const urlPattern = /^https?:\/\/.+/;
        if (!urlPattern.test(newCompanyWebsite)) {
            showToast('errorToast', 'Please enter a valid website URL (must start with http:// or https://)');
            return;
        }
        
        // Set the flag for new company creation
        contactData.create_new_company = true;
    }
    
    // Show loading state
    const saveBtn = document.getElementById('saveContactBtn');
    const originalText = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
    
    // Determine endpoint and method based on add vs edit
    const endpoint = saveBtn.dataset.editingEmail ? `/api/contact/${encodeURIComponent(saveBtn.dataset.editingEmail)}` : '/api/contacts/add';
    const method = saveBtn.dataset.editingEmail ? 'PUT' : 'POST';
    
    // Send request to backend
    fetch(endpoint, {
        method: method,
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
        // Clear edit state after operation completes
        delete saveBtn.dataset.editingEmail;
        const emailInput = document.getElementById('addEmail');
        if (emailInput) emailInput.readOnly = false;
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
        
        // Reset company selection fields
        const companySelect = document.getElementById('companySelect');
        if (companySelect) companySelect.value = '';
        
        const createNewCompanyCheckbox = document.getElementById('createNewCompany');
        if (createNewCompanyCheckbox) {
            createNewCompanyCheckbox.checked = false;
            toggleNewCompanyFields(); // Hide new company fields
        }
    }
}

function loadCompaniesForDropdown() {
    const companySelect = document.getElementById('companySelect');
    if (!companySelect) return;
    
    fetch('/api/companies/list')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear existing options except the first one
                companySelect.innerHTML = '<option value="">Select existing company...</option>';
                
                // Add companies to dropdown
                data.companies.forEach(company => {
                    const option = document.createElement('option');
                    option.value = company.id;
                    option.textContent = company.company_name;
                    option.title = company.website_url; // Show website on hover
                    companySelect.appendChild(option);
                });
            } else {
                console.error('Failed to load companies:', data.message);
            }
        })
        .catch(error => {
            console.error('Error loading companies:', error);
        });
}

function toggleNewCompanyFields() {
    const createNewCompanyCheckbox = document.getElementById('createNewCompany');
    const newCompanyFields = document.getElementById('newCompanyFields');
    const companySelect = document.getElementById('companySelect');
    
    if (!createNewCompanyCheckbox || !newCompanyFields || !companySelect) return;
    
    if (createNewCompanyCheckbox.checked) {
        // Show new company fields and disable company select
        newCompanyFields.style.display = 'block';
        companySelect.disabled = true;
        companySelect.value = '';
    } else {
        // Hide new company fields and enable company select
        newCompanyFields.style.display = 'none';
        companySelect.disabled = false;
        
        // Clear new company inputs
        const newCompanyName = document.getElementById('newCompanyName');
        const newCompanyWebsite = document.getElementById('newCompanyWebsite');
        if (newCompanyName) newCompanyName.value = '';
        if (newCompanyWebsite) newCompanyWebsite.value = '';
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
    
    // Deep research buttons are handled by delegated event listeners in deep-research.js
    
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
    
    // Remember current scroll position
    const currentScrollY = window.scrollY;
    const companiesTabPane = document.getElementById('companies-tab-pane');
    const companiesContainer = document.getElementById('companies-table-container');
    
    // Show loading state
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
                
                // Restore scroll position after a short delay to allow rendering
                setTimeout(() => {
                    window.scrollTo({
                        top: currentScrollY,
                        behavior: 'smooth'
                    });
                    setupCompaniesPagination();
                }, 100);
            } else {
                throw new Error(data.message || 'Failed to load companies');
            }
        })
        .catch(error => {
            console.error('Error loading companies:', error);
            companiesContainer.innerHTML = originalContent;
            showToast('errorToast', 'Failed to load companies: ' + error.message);
            
            // Restore scroll position even on error
            setTimeout(() => {
                window.scrollTo({
                    top: currentScrollY,
                    behavior: 'smooth'
                });
            }, 100);
        });
}

function displayCompaniesTable(companies, pagination) {
    const companiesContainer = document.getElementById('companies-table-container');
    
    let html = '';
    
    // Add Enhanced Pagination Controls at the TOP
    if (pagination.total_pages > 1) {
        html += `
        <div class="pagination-container">
            <div class="row align-items-center g-2">
                <div class="col-xl-3 col-lg-4 col-md-12 mb-2 mb-lg-0">
                    <div class="pagination-controls d-flex align-items-center">
                        <label for="companiesPerPage" class="form-label me-2 mb-0">Show:</label>
                        <select id="companiesPerPage" class="form-select form-select-sm" style="width: auto;">
                            <option value="5" ${pagination.per_page == 5 ? 'selected' : ''}>5</option>
                            <option value="10" ${pagination.per_page == 10 ? 'selected' : ''}>10</option>
                            <option value="25" ${pagination.per_page == 25 ? 'selected' : ''}>25</option>
                            <option value="50" ${pagination.per_page == 50 ? 'selected' : ''}>50</option>
                            <option value="100" ${pagination.per_page == 100 ? 'selected' : ''}>100</option>
                        </select>
                        <span class="text-muted ms-2 small">per page</span>
                    </div>
                </div>
                
                <div class="col-xl-5 col-lg-4 col-md-12 mb-2 mb-lg-0">
                    <div class="pagination-summary">
                        Showing ${((pagination.current_page - 1) * pagination.per_page + 1)} to 
                        ${Math.min(pagination.current_page * pagination.per_page, pagination.total_companies)} 
                        of <strong>${pagination.total_companies}</strong> companies
                    </div>
                </div>
                
                <div class="col-xl-4 col-lg-4 col-md-12">
                    <nav aria-label="Companies pagination" class="d-flex justify-content-lg-end justify-content-center">
                        <ul class="pagination pagination-modern mb-0">
                            <!-- First Page -->
                            <li class="page-item ${pagination.current_page == 1 ? 'disabled' : ''}">
                                <a class="page-link companies-page-link" href="#" data-companies-page="1" title="First page" aria-label="First page">
                                    <i class="fas fa-angle-double-left"></i>
                                </a>
                            </li>
                            
                            <!-- Previous Page -->
                            <li class="page-item ${pagination.current_page == 1 ? 'disabled' : ''}">
                                <a class="page-link companies-page-link" href="#" data-companies-page="${pagination.current_page - 1}" title="Previous page" aria-label="Previous page">
                                    <i class="fas fa-chevron-left"></i>
                                </a>
                            </li>
                            
                            <!-- Page Numbers -->
                            ${generatePageNumbers(pagination.current_page, pagination.total_pages, 'companies-page-link', 'data-companies-page')}
                            
                            <!-- Next Page -->
                            <li class="page-item ${pagination.current_page == pagination.total_pages ? 'disabled' : ''}">
                                <a class="page-link companies-page-link" href="#" data-companies-page="${pagination.current_page + 1}" title="Next page" aria-label="Next page">
                                    <i class="fas fa-chevron-right"></i>
                                </a>
                            </li>
                            
                            <!-- Last Page -->
                            <li class="page-item ${pagination.current_page == pagination.total_pages ? 'disabled' : ''}">
                                <a class="page-link companies-page-link" href="#" data-companies-page="${pagination.total_pages}" title="Last page" aria-label="Last page">
                                    <i class="fas fa-angle-double-right"></i>
                                </a>
                            </li>
                        </ul>
                    </nav>
                </div>
            </div>
        </div>
        `;
    }
    
    // Add the table content
    html += `
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
                            <button class="btn btn-sm btn-outline-info deep-research-btn" data-company-id="${company.id}" data-company-name="${company.company_name}">
                                <i class="fas fa-microscope"></i> Deep Research
                            </button>
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
    `;
    
    companiesContainer.innerHTML = html;
}

// Helper function to generate page numbers for pagination
function generatePageNumbers(currentPage, totalPages, linkClass, dataAttribute) {
    let html = '';
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    // Show first page and ellipsis if needed
    if (startPage > 1) {
        html += `
            <li class="page-item">
                <a class="page-link ${linkClass}" href="#" ${dataAttribute}="1">1</a>
            </li>
        `;
        if (startPage > 2) {
            html += `
                <li class="page-item disabled">
                    <span class="page-link" aria-disabled="true">…</span>
                </li>
            `;
        }
    }
    
    // Show page numbers around current page
    for (let pageNum = startPage; pageNum <= endPage; pageNum++) {
        if (pageNum === currentPage) {
            html += `
                <li class="page-item active">
                    <span class="page-link" aria-current="page">${pageNum}</span>
                </li>
            `;
        } else {
            html += `
                <li class="page-item">
                    <a class="page-link ${linkClass}" href="#" ${dataAttribute}="${pageNum}">${pageNum}</a>
                </li>
            `;
        }
    }
    
    // Show ellipsis and last page if needed
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            html += `
                <li class="page-item disabled">
                    <span class="page-link" aria-disabled="true">…</span>
                </li>
            `;
        }
        html += `
            <li class="page-item">
                <a class="page-link ${linkClass}" href="#" ${dataAttribute}="${totalPages}">${totalPages}</a>
            </li>
        `;
    }
    
    return html;
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
    
    currentCompanyId = companyId; // store for editing
    
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
    
    // Create the company details HTML with editable fields
    modalContent.innerHTML = `
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="card-title mb-0">
                            <i class="fas fa-building me-2"></i>Company Information
                        </h6>
                        <button type="button" class="btn btn-sm btn-outline-primary" id="toggleEditMode" onclick="toggleCompanyEditMode()">
                            <i class="fas fa-edit me-1"></i>Edit
                        </button>
                    </div>
                    <div class="card-body">
                        <div id="companyViewMode">
                            <dl class="row">
                                <dt class="col-4">Name:</dt>
                                <dd class="col-8" id="displayCompanyName">${company.company_name || 'N/A'}</dd>
                                
                                <dt class="col-4">Website:</dt>
                                <dd class="col-8" id="displayWebsiteUrl">
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
                        </div>
                        
                        <div id="companyEditMode" style="display: none;">
                            <div class="mb-3">
                                <label class="form-label">Company Name:</label>
                                <input type="text" class="form-control" id="editCompanyName" value="${company.company_name || ''}">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Website URL:</label>
                                <input type="url" class="form-control" id="editWebsiteUrl" value="${company.website_url || ''}">
                            </div>
                            <div class="d-flex gap-2">
                                <button type="button" class="btn btn-success btn-sm" onclick="saveCompanyInModal()">
                                    <i class="fas fa-save me-1"></i>Save
                                </button>
                                <button type="button" class="btn btn-secondary btn-sm" onclick="cancelCompanyEdit()">
                                    <i class="fas fa-times me-1"></i>Cancel
                                </button>
                            </div>
                        </div>
                        
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
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="card-title mb-0">
                            <i class="fas fa-chart-line me-2"></i>Company Research & Insights
                        </h6>
                        <button type="button" class="btn btn-sm btn-outline-primary" id="toggleResearchEdit" onclick="toggleResearchEditMode()">
                            <i class="fas fa-edit me-1"></i>Edit Research
                        </button>
                    </div>
                    <div class="card-body">
                        <div id="researchViewMode" style="max-height: 400px; overflow-y: auto;">
                            ${researchContent}
                        </div>
                        <div id="researchEditMode" style="display: none;">
                            <textarea class="form-control" id="editCompanyResearch" rows="15" style="max-height: 400px;">${company.company_research || ''}</textarea>
                            <div class="d-flex gap-2 mt-2">
                                <button type="button" class="btn btn-success btn-sm" onclick="saveResearchInModal()">
                                    <i class="fas fa-save me-1"></i>Save Research
                                </button>
                                <button type="button" class="btn btn-secondary btn-sm" onclick="cancelResearchEdit()">
                                    <i class="fas fa-times me-1"></i>Cancel
                                </button>
                            </div>
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

// Function to reinitialize pagination after dynamic content loads
function reinitializePagination() {
    console.log('Reinitializing pagination event listeners...');
    
    // Use event delegation for better reliability
    // Remove existing delegated listeners first
    document.removeEventListener('click', handlePaginationClick);
    
    // Add new delegated event listener
    document.addEventListener('click', handlePaginationClick);
}

// Centralized pagination click handler
function handlePaginationClick(e) {
    const target = e.target.closest('.page-link');
    if (!target) return;
    
    // Check if it's a pagination link and not disabled
    if (target.parentElement && target.parentElement.classList.contains('disabled')) {
        e.preventDefault();
        console.log('Pagination click blocked - disabled item');
        return;
    }
    
    // Handle contacts pagination
    if (target.hasAttribute('data-page')) {
        e.preventDefault();
        e.stopPropagation();
        const page = parseInt(target.getAttribute('data-page'));
        console.log('Contacts pagination clicked - data-page:', target.getAttribute('data-page'), 'parsed page:', page);
        console.log('Parent element classes:', target.parentElement.classList.toString());
        
        if (page && !target.parentElement.classList.contains('disabled')) {
            console.log('Navigating to contacts page:', page);
            addPaginationLoadingState('contactsContainer');
            changePage(page);
        } else {
            console.log('Contacts page navigation blocked - invalid page or disabled');
        }
        return;
    }
    
    // Handle companies pagination
    if (target.hasAttribute('data-companies-page')) {
        e.preventDefault();
        e.stopPropagation();
        const page = parseInt(target.getAttribute('data-companies-page'));
        console.log('Companies pagination clicked:', page);
        if (page && !target.parentElement.classList.contains('disabled')) {
            console.log('Navigating to companies page:', page);
            changeCompaniesPage(page);
        }
        return;
    }
    
    // Handle email history pagination
    if (target.hasAttribute('data-email-page')) {
        e.preventDefault();
        e.stopPropagation();
        const page = parseInt(target.getAttribute('data-email-page'));
        console.log('Email history pagination clicked:', page);
        if (page && !target.parentElement.classList.contains('disabled')) {
            console.log('Navigating to email history page:', page);
            changeEmailHistoryPage(page);
        }
        return;
    }
    
    // Handle inbox pagination
    if (target.hasAttribute('data-inbox-page')) {
        e.preventDefault();
        e.stopPropagation();
        const page = parseInt(target.getAttribute('data-inbox-page'));
        console.log('Inbox pagination clicked:', page);
        if (page && !target.parentElement.classList.contains('disabled')) {
            console.log('Navigating to inbox page:', page);
            changeInboxPage(page);
        }
        return;
    }
}

// GTM Campaign Functions

// Campaign contact selection variables
let campaignContactsSelected = [];
let availableContacts = [];
let campaignCompanies = [];
let currentSearchResults = [];

// Multi-step workflow variables
let currentCampaignStep = 1;
let campaignData = {};

// Campaign execution logging
function addCampaignLog(message, type = 'info') {
    const logContainer = document.getElementById('campaignExecutionLogs');
    if (logContainer) {
        const timestamp = new Date().toLocaleTimeString();
        const iconMap = {
            'info': 'fas fa-info-circle text-info',
            'success': 'fas fa-check-circle text-success', 
            'warning': 'fas fa-exclamation-triangle text-warning',
            'error': 'fas fa-times-circle text-danger',
            'research': 'fas fa-microscope text-primary',
            'email': 'fas fa-envelope text-primary',
            'publish': 'fas fa-cloud-upload-alt text-info'
        };
        
        const icon = iconMap[type] || iconMap['info'];
        const logEntry = `
            <div class="log-entry mb-2">
                <small class="text-muted">[${timestamp}]</small>
                <i class="${icon} me-2"></i>
                <span>${message}</span>
            </div>
        `;
        
        logContainer.innerHTML += logEntry;
        logContainer.scrollTop = logContainer.scrollHeight;
        
        // Also show in console for debugging
        console.log(`[Campaign] ${message}`);
    }
}

// Global function for external access
window.addCampaignLog = addCampaignLog;

// Initialize campaign modal when opened
document.addEventListener('DOMContentLoaded', function() {
    const createCampaignModal = document.getElementById('createCampaignModal');
    if (createCampaignModal) {
        createCampaignModal.addEventListener('shown.bs.modal', function() {
            initializeCampaignModal();
        });
        
        createCampaignModal.addEventListener('hidden.bs.modal', function() {
            resetCampaignModal();
        });
        
        // Setup selection method radio buttons
        const selectionMethodRadios = document.querySelectorAll('input[name="selectionMethod"]');
        selectionMethodRadios.forEach(radio => {
            radio.addEventListener('change', handleSelectionMethodChange);
        });
    }
});

function initializeCampaignModal() {
    // Reset to step 1
    currentCampaignStep = 1;
    showStep(1);
    updateStepIndicators();
    
    // Reset campaign data
    campaignData = {};
    campaignContactsSelected = [];
    updateSelectedContactsBadge();
    
    // Load companies for filter dropdown
    loadCompaniesForCampaign();
    
    // Initialize with quick filter
    setTimeout(() => {
        handleSelectionMethodChange();
        updateContactCount();
    }, 100);
    
    // Setup form field listeners for real-time validation
    setupStepValidation();
}

function resetCampaignModal() {
    currentCampaignStep = 1;
    campaignData = {};
    campaignContactsSelected = [];
    currentSearchResults = [];
    
    // Reset form
    const form = document.getElementById('createCampaignForm');
    if (form) {
        form.reset();
    }
    
    // Clear search input
    const searchInput = document.getElementById('contactSearchCampaign');
    if (searchInput) {
        searchInput.value = '';
    }
    
    // Reset step indicators
    updateStepIndicators();
    showStep(1);
}

function showStep(stepNumber) {
    // Hide all steps
    document.querySelectorAll('.step-content').forEach(step => {
        step.classList.add('d-none');
    });
    
    // Show current step
    const currentStepEl = document.getElementById(`step${stepNumber}`);
    if (currentStepEl) {
        currentStepEl.classList.remove('d-none');
    }
    
    // Update navigation buttons
    updateNavigationButtons(stepNumber);
}

function updateStepIndicators() {
    const stepItems = document.querySelectorAll('.step-item');
    const stepConnectors = document.querySelectorAll('.step-connector');
    
    stepItems.forEach((item, index) => {
        const stepNum = index + 1;
        item.classList.remove('active', 'completed');
        
        if (stepNum < currentCampaignStep) {
            item.classList.add('completed');
        } else if (stepNum === currentCampaignStep) {
            item.classList.add('active');
        }
    });
    
    stepConnectors.forEach((connector, index) => {
        connector.classList.remove('completed');
        if (index + 1 < currentCampaignStep) {
            connector.classList.add('completed');
        }
    });
}

function updateNavigationButtons(stepNumber) {
    const prevBtn = document.getElementById('prevStepBtn');
    const nextBtn = document.getElementById('nextStepBtn');
    const launchBtn = document.getElementById('launchCampaignBtn');
    
    // Previous button
    if (prevBtn) {
        prevBtn.disabled = stepNumber <= 1;
    }
    
    // Next/Launch buttons
    if (stepNumber < 4) {
        if (nextBtn) {
            nextBtn.style.display = '';
            nextBtn.disabled = !validateCurrentStep();
        }
        if (launchBtn) {
            launchBtn.style.display = 'none';
        }
    } else {
        if (nextBtn) {
            nextBtn.style.display = 'none';
        }
        if (launchBtn) {
            launchBtn.style.display = '';
            launchBtn.disabled = !validateCurrentStep();
        }
    }
}

function nextStep() {
    if (!validateCurrentStep()) {
        return;
    }
    
    // Save current step data
    saveCurrentStepData();
    
    if (currentCampaignStep < 4) {
        currentCampaignStep++;
        showStep(currentCampaignStep);
        updateStepIndicators();
        
        // Load step-specific data
        if (currentCampaignStep === 4) {
            populateReviewStep();
        }
    }
}

function previousStep() {
    if (currentCampaignStep > 1) {
        currentCampaignStep--;
        showStep(currentCampaignStep);
        updateStepIndicators();
    }
}

function validateCurrentStep() {
    switch (currentCampaignStep) {
        case 1:
            return validateStep1();
        case 2:
            return validateStep2();
        case 3:
            return validateStep3();
        case 4:
            return validateStep4();
        default:
            return false;
    }
}

function validateStep1() {
    const name = document.getElementById('campaignName')?.value.trim();
    const type = document.getElementById('campaignType')?.value;
    
    return name && type;
}

function validateStep2() {
    const selectedMethod = document.querySelector('input[name="selectionMethod"]:checked')?.value;
    
    if (selectedMethod === 'manual') {
        return campaignContactsSelected.length > 0;
    }
    
    // For quick and advanced filters, check if contact count > 0
    const countText = document.getElementById('selectedContactsCount')?.textContent || '0';
    const count = parseInt(countText.match(/\d+/)?.[0] || '0');
    return count > 0;
}

function validateStep3() {
    const template = document.getElementById('emailTemplate')?.value;
    return template;
}

function validateStep4() {
    return true; // Review step is always valid if we got here
}

function saveCurrentStepData() {
    switch (currentCampaignStep) {
        case 1:
            campaignData.name = document.getElementById('campaignName')?.value;
            campaignData.type = document.getElementById('campaignType')?.value;
            campaignData.description = document.getElementById('campaignDescription')?.value;
            campaignData.goal = document.getElementById('campaignGoal')?.value;
            campaignData.priority = document.getElementById('campaignPriority')?.value;
            break;
        case 2:
            campaignData.selection_criteria = getFilterCriteria();
            campaignData.selectedContacts = [...campaignContactsSelected];
            break;
        case 3:
            campaignData.email_template = document.getElementById('emailTemplate')?.value;
            campaignData.subject_line = document.getElementById('emailSubjectLine')?.value;
            campaignData.schedule_date = document.getElementById('scheduleDate')?.value;
            campaignData.followup_days = document.getElementById('followupDays')?.value || 3;
            campaignData.enable_tracking = document.getElementById('enableTracking')?.checked;
            campaignData.enable_personalization = document.getElementById('enablePersonalization')?.checked;
            
            // Email sending settings
            const emailFrequencyValue = document.getElementById('emailFrequencyValue')?.value || 30;
            const emailFrequencyUnit = document.getElementById('emailFrequencyUnit')?.value || 'minutes';
            campaignData.email_frequency = {
                value: parseInt(emailFrequencyValue),
                unit: emailFrequencyUnit
            };
            campaignData.timezone = document.getElementById('campaignTimezone')?.value || 'America/Los_Angeles';
            campaignData.daily_email_limit = parseInt(document.getElementById('dailyEmailLimit')?.value || 50);
            
            // Business hours settings
            campaignData.respect_business_hours = document.getElementById('respectBusinessHours')?.checked;
            if (campaignData.respect_business_hours) {
                campaignData.business_hours = {
                    start_time: document.getElementById('businessStartTime')?.value || '09:00',
                    end_time: document.getElementById('businessEndTime')?.value || '17:00',
                    days: {
                        monday: document.getElementById('businessMon')?.checked || false,
                        tuesday: document.getElementById('businessTue')?.checked || false,
                        wednesday: document.getElementById('businessWed')?.checked || false,
                        thursday: document.getElementById('businessThu')?.checked || false,
                        friday: document.getElementById('businessFri')?.checked || false,
                        saturday: document.getElementById('businessSat')?.checked || false,
                        sunday: document.getElementById('businessSun')?.checked || false
                    }
                };
            }
            
            // Additional sending preferences
            campaignData.enable_spam_check = document.getElementById('enableSpamCheck')?.checked;
            campaignData.enable_unsubscribe_link = document.getElementById('enableUnsubscribeLink')?.checked;
            break;
    }
}

function populateReviewStep() {
    // Campaign name and type
    document.getElementById('reviewCampaignName').textContent = campaignData.name || 'Untitled Campaign';
    document.getElementById('reviewCampaignType').textContent = campaignData.type || 'Unknown Type';
    
    // Contact count
    const selectedMethod = document.querySelector('input[name="selectionMethod"]:checked')?.value;
    let contactCount = 0;
    if (selectedMethod === 'manual') {
        contactCount = campaignContactsSelected.length;
    } else {
        const countText = document.getElementById('selectedContactsCount')?.textContent || '0';
        contactCount = parseInt(countText.match(/\d+/)?.[0] || '0');
    }
    document.getElementById('reviewContactCount').textContent = contactCount;
    document.getElementById('estimatedReach').textContent = `${contactCount} contacts`;
    
    // Email template
    const templateSelect = document.getElementById('emailTemplate');
    const templateText = templateSelect?.selectedOptions[0]?.textContent || 'Not selected';
    document.getElementById('reviewEmailTemplate').textContent = templateText;
    
    // Priority
    const prioritySelect = document.getElementById('campaignPriority');
    const priorityText = prioritySelect?.selectedOptions[0]?.textContent || 'Medium';
    document.getElementById('reviewPriority').textContent = priorityText;
    
    // Follow-up
    const followupDays = document.getElementById('followupDays')?.value || '3';
    document.getElementById('reviewFollowup').textContent = `${followupDays} days`;
    
    // Description
    const description = campaignData.description || 'No description provided';
    document.getElementById('reviewDescriptionText').textContent = description;
    
    // Expected responses (15% response rate)
    const expectedResponses = Math.round(contactCount * 0.15);
    document.getElementById('expectedResponses').textContent = `~${expectedResponses} replies`;
    
    // Launch time
    const scheduleDate = campaignData.schedule_date;
    if (scheduleDate) {
        const date = new Date(scheduleDate);
        document.getElementById('launchTime').textContent = date.toLocaleString();
    } else {
        document.getElementById('launchTime').textContent = 'Immediately';
    }
    
    // Email sending settings review
    if (campaignData.email_frequency) {
        const frequency = `${campaignData.email_frequency.value} ${campaignData.email_frequency.unit}`;
        document.getElementById('reviewEmailFrequency').textContent = frequency;
    }
    
    if (campaignData.daily_email_limit) {
        document.getElementById('reviewDailyLimit').textContent = `${campaignData.daily_email_limit} emails`;
    }
    
    if (campaignData.timezone) {
        const timezoneMap = {
            'America/New_York': 'Eastern Time',
            'America/Chicago': 'Central Time', 
            'America/Denver': 'Mountain Time',
            'America/Los_Angeles': 'Pacific Time',
            'UTC': 'UTC',
            'Europe/London': 'London Time',
            'Europe/Paris': 'Paris Time',
            'Asia/Tokyo': 'Tokyo Time',
            'Asia/Shanghai': 'Shanghai Time',
            'Australia/Sydney': 'Sydney Time'
        };
        document.getElementById('reviewTimezone').textContent = timezoneMap[campaignData.timezone] || campaignData.timezone;
    }
    
    if (campaignData.respect_business_hours !== undefined) {
        if (campaignData.respect_business_hours && campaignData.business_hours) {
            const businessDays = Object.values(campaignData.business_hours.days).filter(day => day).length;
            const timeRange = `${campaignData.business_hours.start_time}-${campaignData.business_hours.end_time}`;
            document.getElementById('reviewBusinessHours').textContent = `${timeRange} (${businessDays} days)`;
        } else {
            document.getElementById('reviewBusinessHours').textContent = 'Disabled';
        }
    }
}

function setupStepValidation() {
    // Add real-time validation listeners
    const step1Fields = ['campaignName', 'campaignType'];
    const step3Fields = ['emailTemplate'];
    
    step1Fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('input', () => {
                if (currentCampaignStep === 1) {
                    updateNavigationButtons(1);
                }
            });
            field.addEventListener('change', () => {
                if (currentCampaignStep === 1) {
                    updateNavigationButtons(1);
                }
            });
        }
    });
    
    step3Fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('change', () => {
                if (currentCampaignStep === 3) {
                    updateNavigationButtons(3);
                }
            });
        }
    });
    
    // Add listener for business hours toggle
    const respectBusinessHours = document.getElementById('respectBusinessHours');
    if (respectBusinessHours) {
        respectBusinessHours.addEventListener('change', function() {
            const businessHoursSettings = document.getElementById('businessHoursSettings');
            if (businessHoursSettings) {
                if (this.checked) {
                    businessHoursSettings.style.display = 'flex';
                    businessHoursSettings.classList.remove('d-none');
                } else {
                    businessHoursSettings.style.display = 'none';
                    businessHoursSettings.classList.add('d-none');
                }
            }
        });
        
        // Initialize the state
        const businessHoursSettings = document.getElementById('businessHoursSettings');
        if (businessHoursSettings) {
            if (respectBusinessHours.checked) {
                businessHoursSettings.style.display = 'flex';
                businessHoursSettings.classList.remove('d-none');
            } else {
                businessHoursSettings.style.display = 'none';
                businessHoursSettings.classList.add('d-none');
            }
        }
    }
}

function handleSelectionMethodChange() {
    const selectedMethod = document.querySelector('input[name="selectionMethod"]:checked')?.value;
    if (!selectedMethod) return;
    
    // Hide all content divs
    document.querySelectorAll('.selection-method-content').forEach(div => {
        div.classList.add('d-none');
    });
    
    // Show selected method content
    if (selectedMethod === 'quick') {
        document.getElementById('quickFilterOptions')?.classList.remove('d-none');
    } else if (selectedMethod === 'manual') {
        document.getElementById('manualSelectionOptions')?.classList.remove('d-none');
        // Load contacts if manual selection
        if (currentSearchResults.length === 0 && availableContacts.length === 0) {
            loadContactsForManualSelection();
        } else if (availableContacts.length > 0) {
            displayContactsForSelection(availableContacts.slice(0, 20)); // Show first 20 contacts
        }
    } else if (selectedMethod === 'advanced') {
        document.getElementById('advancedFilterOptions')?.classList.remove('d-none');
    }
    
    updateContactCount();
}

function loadCompaniesForCampaign() {
    fetch('/api/companies?per_page=1000')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                campaignCompanies = data.companies;
                populateCompanyFilter();
            }
        })
        .catch(error => {
            console.error('Error loading companies:', error);
        });
}

function populateCompanyFilter() {
    const companyFilter = document.getElementById('companyFilter');
    if (!companyFilter) return;
    
    // Clear existing options (except "All Companies")
    companyFilter.innerHTML = '<option value="">All Companies</option>';
    
    // Add company options
    campaignCompanies.forEach(company => {
        const option = document.createElement('option');
        option.value = company.company_name;
        option.textContent = `${company.company_name}`;
        companyFilter.appendChild(option);
    });
}

function updateContactCount() {
    const selectedMethod = document.querySelector('input[name="selectionMethod"]:checked')?.value;
    
    if (selectedMethod === 'manual') {
        // For manual selection, count is based on selected checkboxes
        updateSelectedContactsBadge();
        if (currentCampaignStep === 2) {
            updateNavigationButtons(2);
        }
        return;
    }
    
    // For quick and advanced filters, get actual contact count from API
    const filterCriteria = getFilterCriteria();
    
    fetch('/api/contacts/count-filtered', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(filterCriteria)
    })
    .then(response => response.json())
    .then(data => {
        const count = data.count || 0;
        updateSelectedContactsBadge(count);
        if (currentCampaignStep === 2) {
            updateNavigationButtons(2);
        }
    })
    .catch(error => {
        console.error('Error getting contact count:', error);
        // Fallback to placeholder counts
        let estimatedCount = 0;
        if (filterCriteria.type === 'quick') {
            switch(filterCriteria.filter_type) {
                case 'all': estimatedCount = 100; break;
                case 'uncontacted': estimatedCount = 50; break;
                case 'has_phone': estimatedCount = 75; break;
                case 'has_linkedin': estimatedCount = 60; break;
                case 'recent': estimatedCount = 25; break;
                default: estimatedCount = 0;
            }
        } else if (filterCriteria.type === 'advanced') {
            estimatedCount = 30;
        }
        updateSelectedContactsBadge(estimatedCount);
        if (currentCampaignStep === 2) {
            updateNavigationButtons(2);
        }
    });
}

function getFilterCriteria() {
    const selectedMethod = document.querySelector('input[name="selectionMethod"]:checked')?.value;
    
    if (selectedMethod === 'quick') {
        return {
            type: 'quick',
            filter_type: document.getElementById('quickFilterType')?.value || 'all',
            company: document.getElementById('companyFilter')?.value || ''
        };
    } else if (selectedMethod === 'advanced') {
        return {
            type: 'advanced',
            company: document.getElementById('advancedCompany')?.value || '',
            job_title: document.getElementById('advancedTitle')?.value || '',
            location: document.getElementById('advancedLocation')?.value || '',
            exclude_contacted: document.getElementById('excludeContacted')?.checked || false,
            require_phone: document.getElementById('requirePhone')?.checked || false,
            require_linkedin: document.getElementById('requireLinkedIn')?.checked || false,
            exclude_active_campaigns: document.getElementById('excludeInactiveCampaigns')?.checked || false
        };
    }
    
    return { type: 'manual', contacts: campaignContactsSelected };
}

function updateSelectedContactsBadge(count = null) {
    const badge = document.getElementById('selectedContactsCount');
    if (!badge) return;
    
    const selectedMethod = document.querySelector('input[name="selectionMethod"]:checked')?.value;
    
    if (selectedMethod === 'manual') {
        count = campaignContactsSelected.length;
    }
    
    if (count !== null) {
        badge.textContent = `${count} contacts selected`;
        badge.className = count > 0 ? 'badge bg-success' : 'badge bg-secondary';
    }
}

function loadContactsForManualSelection() {
    fetch('/api/contacts?per_page=100')
        .then(response => response.json())
        .then(data => {
            if (data.contacts) {
                availableContacts = data.contacts;
                displayContactsForSelection(availableContacts);
            }
        })
        .catch(error => {
            console.error('Error loading contacts:', error);
        });
}

function searchContactsForCampaign() {
    const searchTerm = document.getElementById('contactSearchCampaign')?.value.trim();
    
    if (!searchTerm) {
        displayContactsForSelection(availableContacts);
        return;
    }
    
    fetch(`/api/search_contacts?q=${encodeURIComponent(searchTerm)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Store the search results for contact selection
                currentSearchResults = data.contacts || [];
                displayContactsForSelection(currentSearchResults);
            }
        })
        .catch(error => {
            console.error('Error searching contacts:', error);
        });
}

function displayContactsForSelection(contacts) {
    const container = document.getElementById('campaignContactsList');
    if (!container) return;
    
    if (!contacts || contacts.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="fas fa-users fa-2x mb-2"></i>
                <p>No contacts found</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="list-group">';
    
    contacts.forEach(contact => {
        const isSelected = campaignContactsSelected.some(c => c.email === contact.email);
        const displayName = contact.display_name || contact.full_name || `${contact.first_name || ''} ${contact.last_name || ''}`.trim() || 'Unknown';
        const company = contact.company || contact.company_name || 'Not specified';
        
        const sanitizedEmail = contact.email.replace(/[^a-zA-Z0-9@._-]/g, '_');
        html += `
            <div class="list-group-item ${isSelected ? 'list-group-item-success' : ''}" id="contact-item-${sanitizedEmail}">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" 
                           id="contact_${sanitizedEmail}" 
                           ${isSelected ? 'checked' : ''}
                           onchange="toggleContactSelection('${contact.email.replace(/'/g, "\\'")}', this.checked)">
                    <label class="form-check-label w-100" for="contact_${sanitizedEmail}">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <div class="fw-semibold">${displayName}</div>
                                <div class="text-muted small">${contact.email}</div>
                                <div class="text-muted small">${company} • ${contact.job_title || 'No title'}</div>
                            </div>
                            ${isSelected ? '<div class="text-success"><i class="fas fa-check-circle"></i></div>' : ''}
                        </div>
                    </label>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function toggleContactSelection(email, isSelected) {
    if (isSelected) {
        // Add to selection if not already there
        // Look for contact in available contacts or current search results
        let contact = availableContacts.find(c => c.email === email);
        if (!contact) {
            contact = currentSearchResults.find(c => c.email === email);
        }
        
        if (contact && !campaignContactsSelected.some(c => c.email === email)) {
            campaignContactsSelected.push(contact);
            console.log(`Added contact: ${contact.display_name || contact.email} to campaign selection`);
        } else {
            console.log(`Contact not found or already selected: ${email}`);
        }
    } else {
        // Remove from selection
        const removedContact = campaignContactsSelected.find(c => c.email === email);
        campaignContactsSelected = campaignContactsSelected.filter(c => c.email !== email);
        if (removedContact) {
            console.log(`Removed contact: ${removedContact.display_name || removedContact.email} from campaign selection`);
        }
    }
    
    // Update visual state of the contact item
    const contactItemId = `contact-item-${email.replace(/[^a-zA-Z0-9@._-]/g, '_')}`;
    const contactItem = document.getElementById(contactItemId);
    if (contactItem) {
        if (isSelected) {
            contactItem.classList.add('list-group-item-success');
            // Add checkmark icon if not already there
            const checkmark = contactItem.querySelector('.text-success');
            if (!checkmark) {
                const labelDiv = contactItem.querySelector('.d-flex');
                if (labelDiv) {
                    labelDiv.innerHTML += '<div class="text-success"><i class="fas fa-check-circle"></i></div>';
                }
            }
        } else {
            contactItem.classList.remove('list-group-item-success');
            // Remove checkmark icon
            const checkmark = contactItem.querySelector('.text-success');
            if (checkmark) {
                checkmark.remove();
            }
        }
    }
    
    updateSelectedContactsBadge();
    updateSelectedContactsPreview();
    
    console.log(`Campaign contacts selected count: ${campaignContactsSelected.length}`);
    
    // Update navigation buttons if on step 2
    if (currentCampaignStep === 2) {
        updateNavigationButtons(2);
    }
}

function updateSelectedContactsPreview() {
    const previewDiv = document.getElementById('selectedContactsPreview');
    if (!previewDiv) return;
    
    if (campaignContactsSelected.length === 0) {
        previewDiv.classList.add('d-none');
        return;
    }
    
    previewDiv.classList.remove('d-none');
    const listContainer = previewDiv.querySelector('.selected-contacts-list');
    
    let html = '<div class="list-group list-group-flush">';
    campaignContactsSelected.slice(0, 5).forEach(contact => {
        const displayName = contact.display_name || 'Unknown';
        html += `
            <div class="list-group-item py-1 px-2 small">
                <strong>${displayName}</strong> - ${contact.company || 'No company'}
            </div>
        `;
    });
    
    if (campaignContactsSelected.length > 5) {
        html += `
            <div class="list-group-item py-1 px-2 small text-muted">
                ... and ${campaignContactsSelected.length - 5} more
            </div>
        `;
    }
    
    html += '</div>';
    listContainer.innerHTML = html;
}

function clearCampaignSearch() {
    const searchInput = document.getElementById('campaignSearch');
    if (searchInput) {
        searchInput.value = '';
        // Trigger search to show all campaigns
        searchCampaigns('');
    }
}

function searchCampaigns(searchTerm) {
    // TODO: Implement campaign search functionality
    console.log('Searching campaigns for:', searchTerm);
}

function createCampaign() {
    // Save current step data before final validation
    saveCurrentStepData();
    
    // Final validation
    if (!validateAllSteps()) {
        showToast('errorToast', 'Please complete all required fields');
        return;
    }
    
    // Merge all campaign data
    const finalCampaignData = {
        ...campaignData,
        selection_criteria: getFilterCriteria(),
        selected_contacts: [...campaignContactsSelected]
    };
    
    // Show loading state
    const launchBtn = document.getElementById('launchCampaignBtn');
    const originalText = launchBtn?.innerHTML;
    if (launchBtn) {
        launchBtn.disabled = true;
        launchBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Creating Campaign...';
    }
    
    // Get contact count for success message
    const selectedMethod = document.querySelector('input[name="selectionMethod"]:checked')?.value;
    const contactCount = selectedMethod === 'manual' ? campaignContactsSelected.length : 
                        parseInt(document.getElementById('selectedContactsCount')?.textContent.match(/\d+/)?.[0] || '0');
    
    // Create campaign
    fetch('/api/campaigns', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(finalCampaignData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `Campaign "${finalCampaignData.name}" created successfully! Targeting ${contactCount} contacts.`);
            bootstrap.Modal.getInstance(document.getElementById('createCampaignModal')).hide();
            loadCampaigns(); // Refresh campaigns list
        } else {
            showToast('errorToast', data.message || 'Failed to create campaign');
        }
    })
    .catch(error => {
        console.error('Error creating campaign:', error);
        showToast('errorToast', 'An error occurred while creating the campaign');
    })
    .finally(() => {
        // Restore button state
        if (launchBtn && originalText) {
            launchBtn.disabled = false;
            launchBtn.innerHTML = originalText;
        }
    });
}

function validateAllSteps() {
    // Check Step 1
    if (!campaignData.name || !campaignData.type) {
        return false;
    }
    
    // Check Step 2
    const selectedMethod = document.querySelector('input[name="selectionMethod"]:checked')?.value;
    let hasContacts = false;
    
    if (selectedMethod === 'manual') {
        hasContacts = campaignContactsSelected.length > 0;
    } else {
        const countText = document.getElementById('selectedContactsCount')?.textContent || '0';
        const count = parseInt(countText.match(/\d+/)?.[0] || '0');
        hasContacts = count > 0;
    }
    
    if (!hasContacts) {
        return false;
    }
    
    // Check Step 3
    if (!campaignData.email_template) {
        return false;
    }
    
    return true;
}

function saveCampaignDraft() {
    // Save current step data first
    saveCurrentStepData();
    
    // Merge all available campaign data for draft
    const draftData = {
        ...campaignData,
        selection_criteria: getFilterCriteria(),
        selected_contacts: [...campaignContactsSelected],
        status: 'draft'
    };
    
    if (!draftData.name) {
        showToast('errorToast', 'Campaign name is required to save draft');
        return;
    }
    
    // Show loading state
    const saveBtn = document.getElementById('saveDraftBtn');
    const originalText = saveBtn?.innerHTML;
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
    }
    
    fetch('/api/campaigns/draft', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(draftData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `Campaign "${draftData.name}" saved as draft!`);
            bootstrap.Modal.getInstance(document.getElementById('createCampaignModal')).hide();
            loadCampaigns();
        } else {
            showToast('errorToast', data.message || 'Failed to save campaign draft');
        }
    })
    .catch(error => {
        console.error('Error saving campaign draft:', error);
        showToast('errorToast', 'Error saving campaign draft');
    })
    .finally(() => {
        // Restore button state
        if (saveBtn && originalText) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalText;
        }
    });
}

function loadCampaigns() {
    console.log('Loading campaigns...');
    
    fetch('/api/campaigns')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayCampaigns(data.campaigns);
                updateCampaignStats(data.campaigns);
            } else {
                console.error('Failed to load campaigns:', data.message);
                showToast('errorToast', 'Failed to load campaigns');
            }
        })
        .catch(error => {
            console.error('Error loading campaigns:', error);
            showToast('errorToast', 'Error loading campaigns');
        });
}

function displayCampaigns(campaigns) {
    // Store campaigns globally for campaign details modal access
    window.lastLoadedCampaigns = campaigns;
    
    // Separate campaigns by status
    const activeCampaigns = campaigns.filter(c => c.status === 'active' || c.status === 'ready' || c.status === 'scheduled');
    const draftCampaigns = campaigns.filter(c => c.status === 'draft');
    const completedCampaigns = campaigns.filter(c => c.status === 'completed' || c.status === 'failed' || c.status === 'paused');
    
    // Display active campaigns
    displayCampaignList(activeCampaigns, 'activeCampaignsContainer', 'active');
    
    // Display draft campaigns
    displayCampaignList(draftCampaigns, 'draftCampaignsContainer', 'draft');
    
    // Display completed campaigns
    displayCampaignList(completedCampaigns, 'completedCampaignsContainer', 'completed');
}

function displayCampaignList(campaigns, containerId, type) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (campaigns.length === 0) {
        const emptyMessages = {
            'active': 'No active campaigns yet. Create your first GTM campaign to get started!',
            'draft': 'No draft campaigns found.',
            'completed': 'No completed campaigns found.'
        };
        
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-${type === 'active' ? 'bullhorn' : type === 'draft' ? 'edit' : 'check'} fa-3x mb-3"></i>
                <p>${emptyMessages[type]}</p>
                ${type === 'active' ? '<button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#createCampaignModal"><i class="fas fa-plus me-1"></i>Create Campaign</button>' : ''}
            </div>
        `;
        return;
    }
    
    let html = '<div class="row">';
    
    campaigns.forEach(campaign => {
        const statusBadge = getStatusBadge(campaign.status);
        const priorityBadge = getPriorityBadge(campaign.priority);
        const createdDate = new Date(campaign.created_at).toLocaleDateString();
        const emailsSent = campaign.emails_sent || 0;
        const targetCount = campaign.target_contacts_count || 0;
        const responseRate = targetCount > 0 ? Math.round((campaign.responses_received || 0) / targetCount * 100) : 0;
        
        html += `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card campaign-card h-100">
                    <div class="card-header d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="card-title mb-1">${campaign.name}</h6>
                            <small class="text-muted">${campaign.type.replace('_', ' ').toUpperCase()}</small>
                        </div>
                        <div>
                            ${statusBadge}
                            ${priorityBadge}
                        </div>
                    </div>
                    <div class="card-body">
                        <p class="card-text small text-muted">${campaign.description || 'No description provided'}</p>
                        
                        <div class="campaign-metrics">
                            <div class="row text-center">
                                <div class="col-4">
                                    <div class="metric-value">${targetCount}</div>
                                    <div class="metric-label">Targets</div>
                                </div>
                                <div class="col-4">
                                    <div class="metric-value">${emailsSent}</div>
                                    <div class="metric-label">Sent</div>
                                </div>
                                <div class="col-4">
                                    <div class="metric-value">${responseRate}%</div>
                                    <div class="metric-label">Response</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="campaign-details mt-3">
                            <small class="text-muted">
                                <i class="fas fa-calendar me-1"></i>Created: ${createdDate}<br>
                                <i class="fas fa-envelope me-1"></i>Template: ${campaign.email_template}<br>
                                <i class="fas fa-clock me-1"></i>Follow-up: ${campaign.followup_days} days
                            </small>
                        </div>
                    </div>
                    <div class="card-footer">
                        <div class="btn-group w-100" role="group">
                            <button type="button" class="btn btn-outline-primary btn-sm" onclick="viewCampaignDetails('${campaign.id}')">
                                <i class="fas fa-eye me-1"></i>View
                            </button>
                            ${campaign.status === 'draft' ? 
                                `<button type="button" class="btn btn-outline-success btn-sm" onclick="launchCampaign('${campaign.id}')">
                                    <i class="fas fa-rocket me-1"></i>Launch
                                </button>` : ''
                            }
                            ${campaign.status === 'active' ? 
                                `<button type="button" class="btn btn-outline-warning btn-sm" onclick="pauseCampaign(${campaign.id})">
                                    <i class="fas fa-pause me-1"></i>Pause
                                </button>` : 
                                campaign.status === 'paused' ?
                                `<button type="button" class="btn btn-outline-success btn-sm" onclick="resumeCampaign(${campaign.id})">
                                    <i class="fas fa-play me-1"></i>Resume
                                </button>` : ''
                            }
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function getStatusBadge(status) {
    const badges = {
        'active': '<span class="badge bg-success">Active</span>',
        'ready': '<span class="badge bg-primary">Ready</span>',
        'draft': '<span class="badge bg-secondary">Draft</span>',
        'completed': '<span class="badge bg-info">Completed</span>',
        'failed': '<span class="badge bg-danger">Failed</span>',
        'paused': '<span class="badge bg-warning">Paused</span>'
    };
    return badges[status] || '<span class="badge bg-light">Unknown</span>';
}

function getPriorityBadge(priority) {
    const badges = {
        'high': '<span class="badge bg-danger ms-1">High</span>',
        'medium': '<span class="badge bg-warning ms-1">Medium</span>',
        'low': '<span class="badge bg-info ms-1">Low</span>'
    };
    return badges[priority] || '';
}

function viewCampaignDetails(campaignId) {
    console.log('Loading campaign details for:', campaignId);
    
    // Show the modal immediately with loading state
    const modal = new bootstrap.Modal(document.getElementById('campaignDetailsModal'));
    modal.show();
    
    // Set loading state
    setDetailsLoadingState(true);
    
    // Set campaign ID for controls
    setCampaignDetailsId(campaignId);
    
    // Load campaign activity data
    loadCampaignActivity(campaignId);
    
    // Fetch campaign data from campaigns list first (immediate display)
    const campaignsData = getCurrentCampaignData(campaignId);
    if (campaignsData) {
        populateCampaignDetails(campaignsData);
    }
    
    // Then fetch detailed status (may have additional info)
    fetch(`/api/campaigns/${campaignId}/status`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Merge status data with campaign data
                const enhancedData = { ...campaignsData, ...data.status };
                populateCampaignDetails(enhancedData);
            } else {
                console.error('Failed to load campaign status:', data.message);
                // Keep displaying basic campaign data
            }
        })
        .catch(error => {
            console.error('Error loading campaign status:', error);
            // Keep displaying basic campaign data
        })
        .finally(() => {
            setDetailsLoadingState(false);
        });
}

let currentCampaignDetailsId = null;

function setCampaignDetailsId(campaignId) {
    currentCampaignDetailsId = campaignId;
    
    // Set up control button event handlers
    const pauseBtn = document.getElementById('pauseCampaignBtn');
    const resumeBtn = document.getElementById('resumeCampaignBtn');
    const executeNowBtn = document.getElementById('executeNowBtn');
    const resetBtn = document.getElementById('resetCampaignBtn');
    const updateToDeepResearchBtn = document.getElementById('updateToDeepResearchBtn');
    const refreshBtn = document.getElementById('refreshCampaignBtn');
    
    if (pauseBtn) {
        pauseBtn.onclick = () => pauseCampaign(campaignId);
    }
    if (resumeBtn) {
        resumeBtn.onclick = () => resumeCampaign(campaignId);
    }
    if (executeNowBtn) {
        executeNowBtn.onclick = () => executeCampaignNow(campaignId);
    }
    if (resetBtn) {
        resetBtn.onclick = () => resetCampaignForTesting(campaignId);
    }
    if (updateToDeepResearchBtn) {
        updateToDeepResearchBtn.onclick = () => updateCampaignToDeepResearch(campaignId);
    }
    if (refreshBtn) {
        refreshBtn.onclick = () => viewCampaignDetails(campaignId);
    }
}

function getCurrentCampaignData(campaignId) {
    // Try to get campaign data from currently loaded campaigns
    const containers = ['activeCampaignsContainer', 'draftCampaignsContainer', 'completedCampaignsContainer'];
    for (const containerId of containers) {
        const container = document.getElementById(containerId);
        if (container) {
            // Look for campaign data in the global campaigns array if available
            if (window.lastLoadedCampaigns) {
                return window.lastLoadedCampaigns.find(c => c.id == campaignId);
            }
        }
    }
    return null;
}

function setDetailsLoadingState(isLoading) {
    const loadingText = isLoading ? 'Loading...' : '';
    const fields = [
        'detailsCampaignName', 'detailsCampaignType', 'detailsEmailTemplate',
        'detailsFollowupDays', 'detailsCampaignDescription', 'detailsCreatedAt',
        'detailsUpdatedAt', 'detailsTotalContacts', 'detailsEmailsSent',
        'detailsFailedEmails', 'detailsSuccessRate', 'detailsResponses',
        'detailsActiveContacts', 'detailsFirstEmail', 'detailsLastEmail',
        'detailsUniqueRecipients', 'detailsTotalEmails'
    ];
    
    fields.forEach(fieldId => {
        const element = document.getElementById(fieldId);
        if (element && isLoading) {
            element.textContent = loadingText;
        }
    });
}

function populateCampaignDetails(campaign) {
    if (!campaign) return;
    
    // Update modal title
    document.getElementById('campaignDetailsTitle').textContent = `${campaign.name} - Details`;
    
    // Basic Information
    document.getElementById('detailsCampaignName').textContent = campaign.name || 'N/A';
    document.getElementById('detailsCampaignType').textContent = (campaign.type || 'cold_outreach').replace('_', ' ').toUpperCase();
    document.getElementById('detailsEmailTemplate').textContent = getEmailTemplateDisplayName(campaign.email_template || 'deep_research');
    document.getElementById('detailsFollowupDays').textContent = `${campaign.followup_days || 3} days`;
    document.getElementById('detailsCampaignDescription').textContent = campaign.description || 'No description provided';
    
    // Dates
    if (campaign.created_at) {
        document.getElementById('detailsCreatedAt').textContent = new Date(campaign.created_at).toLocaleString();
    }
    if (campaign.updated_at) {
        document.getElementById('detailsUpdatedAt').textContent = new Date(campaign.updated_at).toLocaleString();
    }
    
    // Status badges
    const statusElement = document.getElementById('detailsCampaignStatus');
    statusElement.className = `badge ${getStatusBadgeClass(campaign.status)}`;
    statusElement.textContent = (campaign.status || 'unknown').toUpperCase();
    
    const priorityElement = document.getElementById('detailsCampaignPriority');
    priorityElement.className = `badge ${getPriorityBadgeClass(campaign.priority)}`;
    priorityElement.textContent = (campaign.priority || 'medium').toUpperCase();
    
    // Metrics
    document.getElementById('detailsTotalContacts').textContent = campaign.total_contacts || campaign.target_contacts_count || 0;
    document.getElementById('detailsEmailsSent').textContent = campaign.sent_emails || campaign.emails_sent || 0;
    document.getElementById('detailsFailedEmails').textContent = campaign.failed_emails || 0;
    document.getElementById('detailsSuccessRate').textContent = `${campaign.success_rate || 0}%`;
    document.getElementById('detailsResponses').textContent = campaign.responses_received || 0;
    document.getElementById('detailsActiveContacts').textContent = campaign.active_contacts || 0;
    
    // Timeline
    document.getElementById('detailsFirstEmail').textContent = campaign.first_email_date ? 
        new Date(campaign.first_email_date).toLocaleString() : 'No emails sent yet';
    document.getElementById('detailsLastEmail').textContent = campaign.last_email_date ? 
        new Date(campaign.last_email_date).toLocaleString() : 'No emails sent yet';
    document.getElementById('detailsUniqueRecipients').textContent = campaign.unique_recipients || 0;
    document.getElementById('detailsTotalEmails').textContent = campaign.total_emails || 0;
    
    // Progress bars
    const totalContacts = campaign.total_contacts || campaign.target_contacts_count || 1;
    const activeContacts = campaign.active_contacts || 0;
    const completedContacts = campaign.completed_contacts || 0;
    const pausedContacts = campaign.paused_contacts || 0;
    const failedContacts = campaign.failed_emails || 0;
    
    updateProgressBar('detailsActiveProgress', 'detailsActiveCount', activeContacts, totalContacts);
    updateProgressBar('detailsCompletedProgress', 'detailsCompletedCount', completedContacts, totalContacts);
    updateProgressBar('detailsPausedProgress', 'detailsPausedCount', pausedContacts, totalContacts);
    updateProgressBar('detailsFailedProgress', 'detailsFailedCount', failedContacts, totalContacts);
    
    // Show/hide control buttons based on status
    updateCampaignControlButtons(campaign.status);
}

function updateProgressBar(progressId, countId, value, total) {
    const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
    document.getElementById(progressId).style.width = `${percentage}%`;
    document.getElementById(countId).textContent = value;
}

function getEmailTemplateDisplayName(template) {
    const templateNames = {
        'deep_research': '🔬 Deep Research',
        'warm': '🤝 Warm Outreach',
        'alt_subject': '📧 Alternative Subject',
        'custom': '✏️ Custom Template'
    };
    return templateNames[template] || template;
}

function getStatusBadgeClass(status) {
    const classes = {
        'active': 'bg-success',
        'ready': 'bg-primary',
        'draft': 'bg-secondary',
        'completed': 'bg-info',
        'failed': 'bg-danger',
        'paused': 'bg-warning',
        'scheduled': 'bg-primary'
    };
    return classes[status] || 'bg-light';
}

function getPriorityBadgeClass(priority) {
    const classes = {
        'high': 'bg-danger',
        'medium': 'bg-warning',
        'low': 'bg-info'
    };
    return classes[priority] || 'bg-warning';
}

function updateCampaignControlButtons(status) {
    const pauseBtn = document.getElementById('pauseCampaignBtn');
    const resumeBtn = document.getElementById('resumeCampaignBtn');
    const editBtn = document.getElementById('editCampaignBtn');
    const executeNowBtn = document.getElementById('executeNowBtn');
    const resetBtn = document.getElementById('resetCampaignBtn');
    const updateToDeepResearchBtn = document.getElementById('updateToDeepResearchBtn');
    
    // Hide all first
    [pauseBtn, resumeBtn, editBtn, executeNowBtn, resetBtn, updateToDeepResearchBtn].forEach(btn => {
        if (btn) btn.style.display = 'none';
    });
    
    // Show appropriate buttons based on status
    if (status === 'active' || status === 'ready') {
        if (pauseBtn) pauseBtn.style.display = 'inline-block';
    } else if (status === 'paused') {
        if (resumeBtn) resumeBtn.style.display = 'inline-block';
    }
    
    // Edit button for draft campaigns
    if (status === 'draft' && editBtn) {
        editBtn.style.display = 'inline-block';
    }
    
    // Execute Now button for all campaigns (testing) - always show for testing purposes
    if (executeNowBtn) {
        executeNowBtn.style.display = 'inline-block';
    }
    
    // Reset button for testing - always show for testing purposes
    if (resetBtn) {
        resetBtn.style.display = 'inline-block';
    }
    
    // Update to Deep Research button - show if not already using deep research
    if (updateToDeepResearchBtn) {
        updateToDeepResearchBtn.style.display = 'inline-block';
    }
}

function executeCampaignNow(campaignId) {
    if (!confirm('⚠️ TEST MODE: This will execute the campaign IMMEDIATELY bypassing all time delays and business hour restrictions.\n\nAre you sure you want to proceed?')) {
        return;
    }
    
    console.log('🚀 TEST MODE: Executing campaign immediately:', campaignId);
    
    // Show loading state
    const executeBtn = document.getElementById('executeNowBtn');
    const originalText = executeBtn?.innerHTML;
    if (executeBtn) {
        executeBtn.disabled = true;
        executeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Executing...';
    }
    
    fetch(`/api/campaigns/${campaignId}/execute-now`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `🚀 ${data.message}`);
            
            // Show additional info toast
            setTimeout(() => {
                showToast('successToast', '📧 Check the logs and email history for execution progress!');
            }, 2000);
            
            // Refresh campaign data after a short delay to see the results
            setTimeout(() => {
                loadCampaigns();
                if (currentCampaignDetailsId == campaignId) {
                    viewCampaignDetails(campaignId);
                }
            }, 3000);
            
        } else {
            showToast('errorToast', data.message || 'Failed to execute campaign immediately');
        }
    })
    .catch(error => {
        console.error('Error executing campaign immediately:', error);
        showToast('errorToast', 'An error occurred while executing the campaign');
    })
    .finally(() => {
        // Restore button state
        if (executeBtn && originalText) {
            executeBtn.disabled = false;
            executeBtn.innerHTML = originalText;
        }
    });
}

function resetCampaignForTesting(campaignId) {
    if (!confirm('🔄 TEST MODE: This will reset all contacts in this campaign back to "active" status so you can re-test the execution.\n\nAre you sure you want to proceed?')) {
        return;
    }
    
    console.log('🔄 TEST MODE: Resetting campaign for testing:', campaignId);
    
    // Show loading state
    const resetBtn = document.getElementById('resetCampaignBtn');
    const originalText = resetBtn?.innerHTML;
    if (resetBtn) {
        resetBtn.disabled = true;
        resetBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Resetting...';
    }
    
    fetch(`/api/campaigns/${campaignId}/reset-for-testing`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `🔄 ${data.message}`);
            
            // Show additional info toast
            setTimeout(() => {
                showToast('successToast', `📋 ${data.reset_count} out of ${data.total_contacts} contacts reactivated for testing!`);
            }, 1500);
            
            // Refresh campaign data after a short delay to see the results
            setTimeout(() => {
                loadCampaigns();
                if (currentCampaignDetailsId == campaignId) {
                    viewCampaignDetails(campaignId);
                }
            }, 2500);
            
        } else {
            showToast('errorToast', data.message || 'Failed to reset campaign for testing');
        }
    })
    .catch(error => {
        console.error('Error resetting campaign for testing:', error);
        showToast('errorToast', 'An error occurred while resetting the campaign');
    })
    .finally(() => {
        // Restore button state
        if (resetBtn && originalText) {
            resetBtn.disabled = false;
            resetBtn.innerHTML = originalText;
        }
    });
}

function updateCampaignToDeepResearch(campaignId) {
    if (!confirm('🔬 This will update the campaign to use the Deep Research email template.\n\nFuture emails will automatically:\n• Trigger company research\n• Generate strategic reports\n• Include tracking-enabled report links\n\nAre you sure you want to proceed?')) {
        return;
    }
    
    console.log('🔬 Updating campaign to Deep Research template:', campaignId);
    
    // Show loading state
    const updateBtn = document.getElementById('updateToDeepResearchBtn');
    const originalText = updateBtn?.innerHTML;
    if (updateBtn) {
        updateBtn.disabled = true;
        updateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Updating...';
    }
    
    fetch(`/api/campaigns/${campaignId}/update-template`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            email_template: 'deep_research'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `🔬 ${data.message}`);
            
            // Show additional info toast
            setTimeout(() => {
                showToast('successToast', '📊 Future emails will now include company research and report links!');
            }, 1500);
            
            // Refresh campaign data after a short delay to see the results
            setTimeout(() => {
                loadCampaigns();
                if (currentCampaignDetailsId == campaignId) {
                    viewCampaignDetails(campaignId);
                }
            }, 2500);
            
        } else {
            showToast('errorToast', data.message || 'Failed to update campaign template');
        }
    })
    .catch(error => {
        console.error('Error updating campaign template:', error);
        showToast('errorToast', 'An error occurred while updating the campaign');
    })
    .finally(() => {
        // Restore button state
        if (updateBtn && originalText) {
            updateBtn.disabled = false;
            updateBtn.innerHTML = originalText;
        }
    });
}

function launchCampaign(campaignId) {
    // TODO: Implement campaign launch functionality
    console.log('Launching campaign:', campaignId);
    showToast('successToast', 'Campaign launch feature coming soon!');
}

function pauseCampaign(campaignId) {
    if (!confirm('Are you sure you want to pause this campaign?')) {
        return;
    }
    
    fetch(`/api/campaigns/${campaignId}/pause`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', data.message);
            loadCampaigns(); // Refresh campaigns list
            
            // If campaign details modal is open for this campaign, refresh it
            if (currentCampaignDetailsId == campaignId) {
                setTimeout(() => viewCampaignDetails(campaignId), 500);
            }
        } else {
            showToast('errorToast', data.message || 'Failed to pause campaign');
        }
    })
    .catch(error => {
        console.error('Error pausing campaign:', error);
        showToast('errorToast', 'An error occurred while pausing the campaign');
    });
}

function resumeCampaign(campaignId) {
    if (!confirm('Are you sure you want to resume this campaign?')) {
        return;
    }
    
    fetch(`/api/campaigns/${campaignId}/resume`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', data.message);
            loadCampaigns(); // Refresh campaigns list
            
            // If campaign details modal is open for this campaign, refresh it
            if (currentCampaignDetailsId == campaignId) {
                setTimeout(() => viewCampaignDetails(campaignId), 500);
            }
        } else {
            showToast('errorToast', data.message || 'Failed to resume campaign');
        }
    })
    .catch(error => {
        console.error('Error resuming campaign:', error);
        showToast('errorToast', 'An error occurred while resuming the campaign');
    });
}

function updateCampaignStats(campaigns) {
    if (!campaigns || !Array.isArray(campaigns)) {
        campaigns = [];
    }
    
    // Calculate stats from campaigns array
    const activeCampaigns = campaigns.filter(c => c.status === 'active' || c.status === 'ready').length;
    const totalEmailsSent = campaigns.reduce((sum, c) => sum + (c.emails_sent || 0), 0);
    const totalTargets = campaigns.reduce((sum, c) => sum + (c.target_contacts_count || 0), 0);
    const totalResponses = campaigns.reduce((sum, c) => sum + (c.responses_received || 0), 0);
    
    const responseRate = totalTargets > 0 ? Math.round((totalResponses / totalTargets) * 100) : 0;
    const conversionRate = totalEmailsSent > 0 ? Math.round((totalResponses / totalEmailsSent) * 100) : 0;
    
    // Update DOM elements
    const totalCampaignsEl = document.getElementById('totalCampaigns');
    const emailsSentEl = document.getElementById('campaignEmailsSent');
    const responseRateEl = document.getElementById('campaignResponseRate');
    const conversionRateEl = document.getElementById('campaignConversionRate');
    
    if (totalCampaignsEl) totalCampaignsEl.textContent = activeCampaigns;
    if (emailsSentEl) emailsSentEl.textContent = totalEmailsSent;
    if (responseRateEl) responseRateEl.textContent = responseRate + '%';
    if (conversionRateEl) conversionRateEl.textContent = conversionRate + '%';
}

// -------------------------------------------------------------
// Editing existing contact
// -------------------------------------------------------------
// currentContactEmail is declared at the top of this file; no need to redeclare here.

function editContact(email) {
    // Fetch contact details and pre-fill the Add Contact form for editing
    fetch(`/api/contact/${encodeURIComponent(email)}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showToast('errorToast', data.error);
                return;
            }

            // Open the add contact modal in edit mode
            const modalEl = document.getElementById('addContactModal');
            const form = document.getElementById('addContactForm');
            if (!modalEl || !form) {
                showToast('errorToast', 'Add Contact modal not found');
                return;
            }

            // Populate form fields
            form.first_name.value = data.first_name || '';
            form.last_name.value = data.last_name || '';
            form.email.value = data.email || '';
            form.job_title.value = data.job_title || '';
            form.linkedin_profile.value = data.linkedin_profile || '';
            form.location.value = data.location || '';
            form.phone.value = data.phone || '';
            
            // Handle company selection for editing
            const companySelect = document.getElementById('companySelect');
            if (companySelect && data.company_id) {
                // If contact has a company_id, select it in the dropdown
                companySelect.value = data.company_id;
            } else if (companySelect) {
                // If no company_id but has company name, leave dropdown unselected 
                companySelect.value = '';
            }

            // Make email read-only during edit
            form.email.readOnly = true;

            // Mark save button with editing email
            const saveBtn = document.getElementById('saveContactBtn');
            saveBtn.dataset.editingEmail = email;

            // Show modal
            const bsModal = new bootstrap.Modal(modalEl);
            bsModal.show();
        })
        .catch(error => {
            console.error('Error loading contact:', error);
            showToast('errorToast', 'Failed to load contact data');
        });
}

// -------------------------------------------------------------
// Company editing functions
// -------------------------------------------------------------

// Attach click handler for saveCompanyBtn
document.addEventListener('DOMContentLoaded', function() {
    const saveCompanyBtn = document.getElementById('saveCompanyBtn');
    if (saveCompanyBtn) {
        saveCompanyBtn.addEventListener('click', saveCompany);
    }
});

// Toggle between view and edit mode for company information
function toggleCompanyEditMode() {
    const viewMode = document.getElementById('companyViewMode');
    const editMode = document.getElementById('companyEditMode');
    const toggleBtn = document.getElementById('toggleEditMode');
    
    if (editMode.style.display === 'none') {
        viewMode.style.display = 'none';
        editMode.style.display = 'block';
        toggleBtn.innerHTML = '<i class="fas fa-eye me-1"></i>View';
    } else {
        viewMode.style.display = 'block';
        editMode.style.display = 'none';
        toggleBtn.innerHTML = '<i class="fas fa-edit me-1"></i>Edit';
    }
}

// Toggle between view and edit mode for research
function toggleResearchEditMode() {
    const viewMode = document.getElementById('researchViewMode');
    const editMode = document.getElementById('researchEditMode');
    const toggleBtn = document.getElementById('toggleResearchEdit');
    
    if (editMode.style.display === 'none') {
        viewMode.style.display = 'none';
        editMode.style.display = 'block';
        toggleBtn.innerHTML = '<i class="fas fa-eye me-1"></i>View';
    } else {
        viewMode.style.display = 'block';
        editMode.style.display = 'none';
        toggleBtn.innerHTML = '<i class="fas fa-edit me-1"></i>Edit Research';
    }
}

// Save company information in the modal
function saveCompanyInModal() {
    const companyName = document.getElementById('editCompanyName').value.trim();
    const websiteUrl = document.getElementById('editWebsiteUrl').value.trim();
    
    if (!companyName) {
        showToast('errorToast', 'Company name is required');
        return;
    }
    
    const companyData = {
        company_name: companyName,
        website_url: websiteUrl,
        company_research: document.getElementById('editCompanyResearch')?.value || ''
    };
    
    // Show loading state
    const saveBtn = document.querySelector('#companyEditMode .btn-success');
    const originalHTML = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
    
    fetch(`/api/companies/${currentCompanyId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(companyData)
    })
    .then(resp => resp.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', data.message);
            // Update the display without reloading
            document.getElementById('displayCompanyName').textContent = companyName;
            document.getElementById('displayWebsiteUrl').innerHTML = websiteUrl ? 
                `<a href="${websiteUrl}" target="_blank" class="text-decoration-none">
                    ${websiteUrl} <i class="fas fa-external-link-alt ms-1"></i>
                </a>` : 'N/A';
            
            // Switch back to view mode
            toggleCompanyEditMode();
        } else {
            showToast('errorToast', data.message || 'Failed to save company');
        }
    })
    .catch(err => {
        console.error('Error saving company:', err);
        showToast('errorToast', 'Error saving company');
    })
    .finally(() => {
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalHTML;
    });
}

// Save research in the modal
function saveResearchInModal() {
    const research = document.getElementById('editCompanyResearch').value.trim();
    
    const companyData = {
        company_name: document.getElementById('editCompanyName')?.value || document.getElementById('displayCompanyName').textContent,
        website_url: document.getElementById('editWebsiteUrl')?.value || '',
        company_research: research
    };
    
    // Show loading state
    const saveBtn = document.querySelector('#researchEditMode .btn-success');
    const originalHTML = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
    
    fetch(`/api/companies/${currentCompanyId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(companyData)
    })
    .then(resp => resp.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', data.message);
            // Update the display
            document.getElementById('researchViewMode').innerHTML = research ? 
                research.replace(/\n/g, '<br>') : 
                '<em class="text-muted">No research available yet. Click the Research button to generate AI-powered insights.</em>';
            
            // Switch back to view mode
            toggleResearchEditMode();
        } else {
            showToast('errorToast', data.message || 'Failed to save research');
        }
    })
    .catch(err => {
        console.error('Error saving research:', err);
        showToast('errorToast', 'Error saving research');
    })
    .finally(() => {
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalHTML;
    });
}

// Cancel company edit
function cancelCompanyEdit() {
    // Reset form values to original
    const originalName = document.getElementById('displayCompanyName').textContent;
    const originalUrl = document.getElementById('displayWebsiteUrl').querySelector('a')?.href || '';
    
    document.getElementById('editCompanyName').value = originalName === 'N/A' ? '' : originalName;
    document.getElementById('editWebsiteUrl').value = originalUrl;
    
    toggleCompanyEditMode();
}

// Cancel research edit
function cancelResearchEdit() {
    toggleResearchEditMode();
}

// Legacy function for compatibility (now unused)
function editCompany(companyId) {
    // This function is now replaced by the in-modal editing
    console.log('editCompany called - now using in-modal editing');
}

function saveCompany() {
    const form = document.getElementById('addCompanyForm');
    const saveBtn = document.getElementById('saveCompanyBtn');

    const companyData = {
        company_name: document.getElementById('companyName').value.trim(),
        website_url: document.getElementById('websiteUrl').value.trim(),
        company_research: document.getElementById('companyResearch').value.trim()
    };

    if (!companyData.company_name) {
        showToast('errorToast', 'Company name is required');
        return;
    }

    // Show loading state
    const originalHTML = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';

    const editingId = saveBtn.dataset.editingCompanyId;
    const endpoint = editingId ? `/api/companies/${editingId}` : '/api/companies/add';
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
                showToast('successToast', data.message);
                const modal = bootstrap.Modal.getInstance(document.getElementById('addCompanyModal'));
                if (modal) modal.hide();

                // Reset form and state
                form.reset();
                delete saveBtn.dataset.editingCompanyId;
                document.getElementById('addCompanyModalLabel').textContent = 'Add New Company';

                setTimeout(() => window.location.reload(), 1500);
            } else {
                showToast('errorToast', data.message || 'Failed to save company');
            }
        })
        .catch(err => {
            console.error('Error saving company:', err);
            showToast('errorToast', 'Error saving company');
        })
        .finally(() => {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalHTML;
        });
}

// Load campaign activity data (emails, logs, next actions)
function loadCampaignActivity(campaignId) {
    console.log('Loading campaign activity for:', campaignId);
    
    fetch(`/api/campaigns/${campaignId}/activity`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateEmailHistory(data.data.emails);
                populateExecutionLogs(data.data.logs);
                populateNextActions(data.data.next_actions);
            } else {
                console.error('Failed to load campaign activity:', data.message);
                showActivityError(data.message);
            }
        })
        .catch(error => {
            console.error('Error loading campaign activity:', error);
            showActivityError('Failed to load campaign activity');
        });
}

function populateEmailHistory(emails) {
    const container = document.getElementById('campaignEmailHistory');
    
    if (!emails || emails.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-envelope-open-text fa-2x mb-2"></i>
                <p class="mb-0">No emails sent yet</p>
                <small>Use "Execute Now (Test)" to send emails immediately</small>
            </div>
        `;
        return;
    }
    
    let html = '<div class="list-group list-group-flush">';
    
    emails.forEach(email => {
        const statusIcon = getEmailStatusIcon(email.status);
        const statusClass = getEmailStatusClass(email.status);
        const sentDate = email.sent_at ? new Date(email.sent_at).toLocaleString() : 'Not sent';
        
        html += `
            <div class="list-group-item border-0">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center mb-1">
                            <span class="badge ${statusClass} me-2">${statusIcon} ${email.status}</span>
                            <strong>${email.recipient_email}</strong>
                        </div>
                        <p class="mb-1 text-muted">${email.subject || 'No subject'}</p>
                        <small class="text-muted">
                            <i class="fas fa-clock me-1"></i>${sentDate}
                        </small>
                        ${email.error_message ? `<div class="mt-1"><small class="text-danger"><i class="fas fa-exclamation-triangle me-1"></i>${email.error_message}</small></div>` : ''}
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function populateExecutionLogs(logs) {
    const container = document.getElementById('campaignExecutionLogs');
    
    if (!logs || logs.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-file-alt fa-2x mb-2"></i>
                <p class="mb-0">No execution logs yet</p>
                <small>Logs will appear as the campaign runs</small>
            </div>
        `;
        return;
    }
    
    let html = '<div class="list-group list-group-flush">';
    
    logs.forEach(log => {
        const levelIcon = getLogLevelIcon(log.level);
        const levelClass = getLogLevelClass(log.level);
        const logTime = new Date(log.timestamp).toLocaleString();
        
        html += `
            <div class="list-group-item border-0">
                <div class="d-flex align-items-start">
                    <span class="badge ${levelClass} me-2">${levelIcon}</span>
                    <div class="flex-grow-1">
                        <div class="d-flex justify-content-between align-items-start">
                            <strong class="mb-1">${log.message}</strong>
                            <small class="text-muted">${logTime}</small>
                        </div>
                        ${log.details ? `<p class="mb-0 text-muted small">${log.details}</p>` : ''}
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function populateNextActions(actions) {
    const container = document.getElementById('campaignNextActions');
    
    if (!actions || actions.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-check-circle fa-2x mb-2"></i>
                <p class="mb-0">No pending actions</p>
                <small>Campaign is up to date</small>
            </div>
        `;
        return;
    }
    
    let html = '<div class="list-group list-group-flush">';
    
    actions.forEach(action => {
        const typeIcon = getActionTypeIcon(action.type);
        const typeClass = getActionTypeClass(action.type);
        
        html += `
            <div class="list-group-item border-0">
                <div class="d-flex align-items-start">
                    <span class="badge ${typeClass} me-2">${typeIcon}</span>
                    <div class="flex-grow-1">
                        <div class="d-flex justify-content-between align-items-start">
                            <strong class="mb-1">${action.action}</strong>
                            <small class="text-muted">${action.scheduled_time}</small>
                        </div>
                        <p class="mb-0 text-muted small">${action.description}</p>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function showActivityError(message) {
    const containers = ['campaignEmailHistory', 'campaignExecutionLogs', 'campaignNextActions'];
    containers.forEach(containerId => {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="text-center text-danger py-4">
                    <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                    <p class="mb-0">Failed to load data</p>
                    <small>${message}</small>
                </div>
            `;
        }
    });
}

// Helper functions for status/level styling
function getEmailStatusIcon(status) {
    const icons = {
        'Success': '<i class="fas fa-check"></i>',
        'Failed': '<i class="fas fa-times"></i>',
        'Pending': '<i class="fas fa-clock"></i>',
        'Sent': '<i class="fas fa-paper-plane"></i>'
    };
    return icons[status] || '<i class="fas fa-question"></i>';
}

function getEmailStatusClass(status) {
    const classes = {
        'Success': 'bg-success',
        'Failed': 'bg-danger',
        'Pending': 'bg-warning',
        'Sent': 'bg-primary'
    };
    return classes[status] || 'bg-secondary';
}

function getLogLevelIcon(level) {
    const icons = {
        'INFO': '<i class="fas fa-info"></i>',
        'SUCCESS': '<i class="fas fa-check"></i>',
        'WARNING': '<i class="fas fa-exclamation-triangle"></i>',
        'ERROR': '<i class="fas fa-times"></i>'
    };
    return icons[level] || '<i class="fas fa-circle"></i>';
}

function getLogLevelClass(level) {
    const classes = {
        'INFO': 'bg-info',
        'SUCCESS': 'bg-success',
        'WARNING': 'bg-warning',
        'ERROR': 'bg-danger'
    };
    return classes[level] || 'bg-secondary';
}

function getActionTypeIcon(type) {
    const icons = {
        'scheduled': '<i class="fas fa-calendar-alt"></i>',
        'recurring': '<i class="fas fa-sync-alt"></i>',
        'manual': '<i class="fas fa-hand-paper"></i>',
        'completed': '<i class="fas fa-check-circle"></i>'
    };
    return icons[type] || '<i class="fas fa-cog"></i>';
}

function getActionTypeClass(type) {
    const classes = {
        'scheduled': 'bg-primary',
        'recurring': 'bg-info',
        'manual': 'bg-warning',
        'completed': 'bg-success'
    };
    return classes[type] || 'bg-secondary';
}

function deleteAllCampaigns() {
    // Show detailed confirmation dialog
    const confirmationMessage = `🗑️ DELETE ALL CAMPAIGNS
    
⚠️ WARNING: This action cannot be undone!

This will permanently delete:
• ALL campaigns from the database
• ALL campaign-contact relationships
• ALL email history records associated with campaigns
• The campaigns.json file

Contacts and Companies will NOT be deleted.

Are you absolutely sure you want to proceed?`;

    if (!confirm(confirmationMessage)) {
        return;
    }
    
    // Second confirmation with text input
    const confirmText = prompt('🚨 FINAL WARNING: This will delete ALL campaigns and associated data permanently.\n\nType "DELETE" (in all caps) to confirm:');
    if (confirmText !== 'DELETE') {
        showToast('errorToast', 'Deletion cancelled. You must type "DELETE" exactly to confirm.');
        return;
    }
    
    console.log('🗑️ Starting deletion of all campaigns...');
    
    // Show loading state on the button
    const deleteBtn = document.querySelector('button[onclick="deleteAllCampaigns()"]');
    const originalText = deleteBtn?.innerHTML;
    if (deleteBtn) {
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Deleting...';
    }
    
    // Show progress toast
    showToast('successToast', '🗑️ Deleting all campaigns and associated data...');
    
    fetch('/api/campaigns/delete-all', {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `✅ ${data.message}`);
            
            // Show detailed results if available
            if (data.deleted_counts) {
                const counts = data.deleted_counts;
                setTimeout(() => {
                    showToast('successToast', 
                        `📊 Deletion Summary: ${counts.campaigns} campaigns, ${counts.campaign_contacts} contact links, ${counts.email_history} email records`
                    );
                }, 2000);
            }
            
            // Refresh the campaign view to show empty state
            setTimeout(() => {
                loadCampaigns();
                updateCampaignStats([]); // Reset stats to zero
            }, 3000);
            
        } else {
            showToast('errorToast', data.message || 'Failed to delete campaigns');
        }
    })
    .catch(error => {
        console.error('Error deleting all campaigns:', error);
        showToast('errorToast', 'An error occurred while deleting campaigns');
    })
    .finally(() => {
        // Reset button state
        if (deleteBtn && originalText) {
            deleteBtn.disabled = false;
            deleteBtn.innerHTML = originalText;
        }
    });
}