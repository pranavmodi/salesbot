// SalesBot CRM - Main Dashboard JavaScript (Refactored)
// This file now imports and coordinates functionality from separate modules

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    console.log("Dashboard initializing...");
    
    // Initialize all modules
    initializeContacts();
    initializeEmail();
    initializeCampaigns();
    initializeCompanies();
    
    // Setup additional dashboard-specific functionality
    setupMainEventListeners();
    setupInboxPagination();
    
    console.log("Dashboard initialized successfully");
});

// Main dashboard event listeners
function setupMainEventListeners() {
    // Contacts per-page selector
    const perPageSelect = document.getElementById('perPage');
    if (perPageSelect) {
        perPageSelect.addEventListener('change', function() {
            addPaginationLoadingState('contactsContainer');
            changePage(1);
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

    // Test emails functionality
    const sendTestEmailsBtn = document.getElementById('sendTestEmails');
    if (sendTestEmailsBtn) {
        sendTestEmailsBtn.addEventListener('click', sendTestEmails);
    }

    // New company toggle
    const newCompanyToggle = document.getElementById('newCompanyToggle');
    if (newCompanyToggle) {
        newCompanyToggle.addEventListener('change', toggleNewCompanyFields);
    }
}

// Contact form management
function saveNewContact() {
    const form = document.getElementById('addContactForm');
    if (!form) return;

    const formData = new FormData(form);
    const contactData = {};
    
    // Convert FormData to object
    for (let [key, value] of formData.entries()) {
        contactData[key] = value;
    }

    // Validate required fields
    if (!contactData.email || !contactData.first_name) {
        showToast('warningToast', 'Please fill in required fields (Email and First Name)');
        return;
    }

    const saveBtn = document.getElementById('saveContactBtn');
    const originalText = saveBtn.innerHTML;
    
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
    saveBtn.disabled = true;

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
            showToast('successToast', 'Contact added successfully!');
            
            // Reset form
            resetAddContactForm();
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addContactModal'));
            if (modal) {
                modal.hide();
            }
            
            // Refresh contacts
            changePage(1);
            
            // Update contact stats
            updateContactStats();
        } else {
            throw new Error(data.message || 'Failed to add contact');
        }
    })
    .catch(error => {
        console.error('Error adding contact:', error);
        showToast('errorToast', 'Failed to add contact: ' + error.message);
    })
    .finally(() => {
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    });
}

function resetAddContactForm() {
    const form = document.getElementById('addContactForm');
    if (form) {
        form.reset();
    }
    
    // Hide new company fields
    const newCompanyFields = document.getElementById('newCompanyFields');
    if (newCompanyFields) {
        newCompanyFields.style.display = 'none';
    }
    
    // Reset company toggle
    const newCompanyToggle = document.getElementById('newCompanyToggle');
    if (newCompanyToggle) {
        newCompanyToggle.checked = false;
    }
}

function loadCompaniesForDropdown() {
    const companySelect = document.getElementById('companySelect');
    if (!companySelect) return;
    
    fetch('/api/companies/list')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const companies = data.companies || [];
                companySelect.innerHTML = '<option value="">Select existing company...</option>';
                
                companies.forEach(company => {
                    const option = document.createElement('option');
                    option.value = company.id;
                    option.textContent = company.company_name;
                    option.title = company.website_url; // Show website on hover
                    companySelect.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Error loading companies for dropdown:', error);
        });
}

function toggleNewCompanyFields() {
    const createNewCompanyCheckbox = document.getElementById('createNewCompany');
    const newCompanyFields = document.getElementById('newCompanyFields');
    const companySelect = document.getElementById('companySelect');
    
    if (createNewCompanyCheckbox && newCompanyFields && companySelect) {
        if (createNewCompanyCheckbox.checked) {
            newCompanyFields.style.display = 'block';
            companySelect.disabled = true;
            companySelect.value = '';
        } else {
            newCompanyFields.style.display = 'none';
            companySelect.disabled = false;
            
            // Clear new company fields
            const inputs = newCompanyFields.querySelectorAll('input, textarea');
            inputs.forEach(input => input.value = '');
        }
    }
}

// Test emails functionality
function sendTestEmails(event) {
    event.preventDefault();
    
    const testBtn = event.target;
    const originalText = testBtn.innerHTML;
    
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Sending...';
    testBtn.disabled = true;
    
    const testData = {
        test_type: 'bulk_test',
        recipient_count: 3
    };
    
    fetch('/api/email/send-test', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(testData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', 'Test emails sent successfully!');
            
            // Refresh email history if available
            if (typeof refreshEmailHistory === 'function') {
                refreshEmailHistory();
            }
        } else {
            throw new Error(data.message || 'Failed to send test emails');
        }
    })
    .catch(error => {
        console.error('Error sending test emails:', error);
        showToast('errorToast', 'Failed to send test emails: ' + error.message);
    })
    .finally(() => {
        testBtn.innerHTML = originalText;
        testBtn.disabled = false;
    });
}

// Inbox pagination setup
function setupInboxPagination() {
    // This function sets up pagination for inbox emails
    console.log('Setting up inbox pagination...');
    
    // Add event listeners for inbox pagination
    const inboxPaginationContainer = document.getElementById('inboxPagination');
    if (inboxPaginationContainer) {
        inboxPaginationContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('inbox-page-link')) {
                e.preventDefault();
                const page = parseInt(e.target.getAttribute('data-inbox-page'));
                if (page && !isNaN(page)) {
                    changeInboxPage(page);
                }
            }
        });
    }
}

function changeInboxPage(page) {
    if (!currentGlobalAccount) {
        showToast('warningToast', 'Please select an email account first');
        return;
    }
    
    console.log(`Changing inbox page to: ${page}`);
    
    // Add loading state
    const inboxContainer = document.getElementById('inboxContainer');
    if (inboxContainer) {
        inboxContainer.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading page ${page}...</p>
            </div>
        `;
    }
    
    // Load emails for the specified page
    fetch(`/api/email/inbox/${encodeURIComponent(currentGlobalAccount.email)}?page=${page}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayAccountEmails(data.emails || [], currentGlobalAccount);
                
                // Update pagination if provided
                if (data.pagination) {
                    updateInboxPagination(data.pagination);
                }
            } else {
                throw new Error(data.message || 'Failed to load inbox page');
            }
        })
        .catch(error => {
            console.error('Error loading inbox page:', error);
            if (inboxContainer) {
                inboxContainer.innerHTML = `
                    <div class="text-center py-5">
                        <i class="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                        <h5 class="text-danger">Failed to Load Page</h5>
                        <p class="text-muted">${error.message}</p>
                        <button class="btn btn-outline-primary" onclick="changeInboxPage(${page})">
                            <i class="fas fa-refresh me-2"></i>Retry
                        </button>
                    </div>
                `;
            }
        });
}

function updateInboxPagination(pagination) {
    const paginationContainer = document.getElementById('inboxPagination');
    if (!paginationContainer || pagination.total_pages <= 1) {
        if (paginationContainer) {
            paginationContainer.innerHTML = '';
        }
        return;
    }
    
    let html = `
        <nav aria-label="Inbox pagination" class="mt-4">
            <ul class="pagination justify-content-center">
    `;
    
    // Previous button
    const prevDisabled = pagination.current_page === 1 ? 'disabled' : '';
    html += `
        <li class="page-item ${prevDisabled}">
            <a class="page-link inbox-page-link" href="#" data-inbox-page="${pagination.current_page - 1}" 
               ${prevDisabled ? 'tabindex="-1" aria-disabled="true"' : ''}>
                <i class="fas fa-chevron-left"></i>
            </a>
        </li>
    `;
    
    // Page numbers
    html += generatePageNumbers(pagination.current_page, pagination.total_pages, 'inbox-page-link', 'data-inbox-page');
    
    // Next button
    const nextDisabled = pagination.current_page === pagination.total_pages ? 'disabled' : '';
    html += `
        <li class="page-item ${nextDisabled}">
            <a class="page-link inbox-page-link" href="#" data-inbox-page="${pagination.current_page + 1}"
               ${nextDisabled ? 'tabindex="-1" aria-disabled="true"' : ''}>
                <i class="fas fa-chevron-right"></i>
            </a>
        </li>
    `;
    
    html += `
            </ul>
        </nav>
    `;
    
    paginationContainer.innerHTML = html;
}

// Email conversations functionality
function loadEmailConversations(contactEmail) {
    const conversationsContainer = document.getElementById('emailConversations');
    if (!conversationsContainer) return;
    
    conversationsContainer.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border spinner-border-sm text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <small class="d-block mt-2 text-muted">Loading email history...</small>
        </div>
    `;
    
    fetch(`/api/email/conversations/${encodeURIComponent(contactEmail)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.summary) {
                    displayConversationSummary(data.summary, contactEmail);
                } else {
                    conversationsContainer.innerHTML = `
                        <div class="text-center py-3">
                            <i class="fas fa-inbox text-muted mb-2"></i>
                            <p class="text-muted mb-0">No email conversations found</p>
                        </div>
                    `;
                }
            } else {
                throw new Error(data.message || 'Failed to load conversations');
            }
        })
        .catch(error => {
            console.error('Error loading email conversations:', error);
            conversationsContainer.innerHTML = `
                <div class="text-center py-3">
                    <i class="fas fa-exclamation-triangle text-warning mb-2"></i>
                    <p class="text-muted mb-0">Failed to load email history</p>
                </div>
            `;
        });
}

function displayConversationSummary(summary, contactEmail) {
    const conversationsContainer = document.getElementById('emailConversations');
    if (!conversationsContainer) return;
    
    let html = `
        <div class="conversation-summary">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="mb-0">Email History Summary</h6>
                <button class="btn btn-outline-primary btn-sm" onclick="loadDetailedConversations('${contactEmail}')">
                    <i class="fas fa-list me-1"></i>View Details
                </button>
            </div>
            
            <div class="row text-center mb-3">
                <div class="col-3">
                    <div class="text-primary h5 mb-0">${summary.total_emails || 0}</div>
                    <small class="text-muted">Total Emails</small>
                </div>
                <div class="col-3">
                    <div class="text-success h5 mb-0">${summary.sent_emails || 0}</div>
                    <small class="text-muted">Sent</small>
                </div>
                <div class="col-3">
                    <div class="text-info h5 mb-0">${summary.received_emails || 0}</div>
                    <small class="text-muted">Received</small>
                </div>
                <div class="col-3">
                    <div class="text-warning h5 mb-0">${summary.response_rate || 0}%</div>
                    <small class="text-muted">Response Rate</small>
                </div>
            </div>
    `;
    
    if (summary.last_contact) {
        html += `
            <div class="alert alert-light">
                <small class="text-muted">
                    <i class="fas fa-clock me-1"></i>
                    Last contact: ${new Date(summary.last_contact).toLocaleDateString()}
                </small>
            </div>
        `;
    }
    
    html += '</div>';
    conversationsContainer.innerHTML = html;
}

function loadDetailedConversations(contactEmail) {
    const conversationsContainer = document.getElementById('emailConversations');
    if (!conversationsContainer) return;
    
    conversationsContainer.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border spinner-border-sm text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <small class="d-block mt-2 text-muted">Loading detailed conversations...</small>
        </div>
    `;
    
    fetch(`/api/email/conversations/${encodeURIComponent(contactEmail)}/detailed`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayDetailedConversations(data, contactEmail);
            } else {
                throw new Error(data.message || 'Failed to load detailed conversations');
            }
        })
        .catch(error => {
            console.error('Error loading detailed conversations:', error);
            conversationsContainer.innerHTML = `
                <div class="text-center py-3">
                    <i class="fas fa-exclamation-triangle text-warning mb-2"></i>
                    <p class="text-muted mb-0">Failed to load detailed conversations</p>
                    <button class="btn btn-outline-primary btn-sm mt-2" onclick="loadEmailConversations('${contactEmail}')">
                        <i class="fas fa-arrow-left me-1"></i>Back to Summary
                    </button>
                </div>
            `;
        });
}

function displayDetailedConversations(data, contactEmail) {
    const conversationsContainer = document.getElementById('emailConversations');
    if (!conversationsContainer) return;
    
    const conversations = data.conversations || [];
    
    let html = `
        <div class="detailed-conversations">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="mb-0">Detailed Email History</h6>
                <button class="btn btn-outline-secondary btn-sm" onclick="loadEmailConversations('${contactEmail}')">
                    <i class="fas fa-arrow-left me-1"></i>Back to Summary
                </button>
            </div>
    `;
    
    if (conversations.length === 0) {
        html += `
            <div class="text-center py-3">
                <i class="fas fa-inbox text-muted mb-2"></i>
                <p class="text-muted mb-0">No detailed conversations available</p>
            </div>
        `;
    } else {
        html += '<div class="conversation-list">';
        
        conversations.forEach(conversation => {
            const statusIcon = getEmailStatusIcon(conversation.status);
            const statusClass = getEmailStatusClass(conversation.status);
            const isInbound = conversation.direction === 'inbound';
            
            html += `
                <div class="conversation-item border-bottom pb-3 mb-3">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${conversation.subject || 'No Subject'}</h6>
                            <small class="text-muted">
                                <i class="${isInbound ? 'fas fa-arrow-down text-success' : 'fas fa-arrow-up text-primary'} me-1"></i>
                                ${isInbound ? 'Received from' : 'Sent to'} ${conversation.contact}
                            </small>
                        </div>
                        <div class="text-end">
                            <small class="text-muted d-block">${new Date(conversation.timestamp).toLocaleDateString()}</small>
                            <small class="${statusClass}">
                                <i class="${statusIcon} me-1"></i>${conversation.status}
                            </small>
                        </div>
                    </div>
                    
                    ${conversation.preview ? `
                        <div class="conversation-preview p-2 bg-light rounded">
                            <small>${conversation.preview}</small>
                        </div>
                    ` : ''}
                </div>
            `;
        });
        
        html += '</div>';
    }
    
    html += '</div>';
    conversationsContainer.innerHTML = html;
}

// Campaign activity functions (referenced by campaigns.js)
function loadCampaignActivity(campaignId) {
    console.log(`Loading campaign activity for ID: ${campaignId}`);
    
    const tabsContainer = document.getElementById('campaignActivityTabs');
    const contentContainer = document.getElementById('campaignActivityContent');
    
    if (tabsContainer && contentContainer) {
        // Show loading state
        contentContainer.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading campaign activity...</p>
            </div>
        `;
        
        fetch(`/api/campaigns/${campaignId}/activity`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    populateEmailHistory(data.email_history || []);
                    populateExecutionLogs(data.execution_logs || []);
                    populateNextActions(data.next_actions || []);
                } else {
                    throw new Error(data.message || 'Failed to load campaign activity');
                }
            })
            .catch(error => {
                console.error('Error loading campaign activity:', error);
                showActivityError(error.message);
            });
    }
}

// Stub functions for campaign activity (to be implemented or moved to campaigns.js)
function populateEmailHistory(emails) {
    console.log('Populating email history:', emails);
}

function populateExecutionLogs(logs) {
    console.log('Populating execution logs:', logs);
}

function populateNextActions(actions) {
    console.log('Populating next actions:', actions);
}

function showActivityError(message) {
    const contentContainer = document.getElementById('campaignActivityContent');
    if (contentContainer) {
        contentContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                <h5 class="text-danger">Failed to Load Activity</h5>
                <p class="text-muted">${message}</p>
            </div>
        `;
    }
}

// Global functions that may be called from HTML onclick handlers
window.saveNewContact = saveNewContact;
window.resetAddContactForm = resetAddContactForm;
window.loadCompaniesForDropdown = loadCompaniesForDropdown;
window.toggleNewCompanyFields = toggleNewCompanyFields;
window.sendTestEmails = sendTestEmails;
window.changeInboxPage = changeInboxPage;
window.loadEmailConversations = loadEmailConversations;
window.loadDetailedConversations = loadDetailedConversations;
window.loadCampaignActivity = loadCampaignActivity;