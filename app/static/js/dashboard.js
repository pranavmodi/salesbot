// SalesBot CRM - Main Dashboard JavaScript (Refactored)
// This file now imports and coordinates functionality from separate modules

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    console.log("Dashboard initializing...");
    
    // Wait a bit for all scripts to load, then initialize
    setTimeout(function() {
        try {
            // Initialize all modules with error checking
            if (typeof initializeContacts === 'function') {
                initializeContacts();
                console.log("Contacts module initialized");
            } else {
                console.error("initializeContacts function not found");
            }
            
            if (typeof initializeEmail === 'function') {
                initializeEmail();
                console.log("Email module initialized");
            } else {
                console.error("initializeEmail function not found");
            }
            
            if (typeof initializeCampaigns === 'function') {
                initializeCampaigns();
                console.log("Campaigns module initialized");
            } else {
                console.error("initializeCampaigns function not found");
            }
            
            if (typeof initializeCompanies === 'function') {
                initializeCompanies();
                console.log("Companies module initialized");
            } else {
                console.error("initializeCompanies function not found");
            }
            
            // Initialize compose form functionality
            if (typeof setupComposeFormEnhancements === 'function') {
                setupComposeFormEnhancements();
                console.log("Compose form enhancements initialized");
            } else {
                console.error("setupComposeFormEnhancements function not found");
            }
            
            // Setup additional dashboard-specific functionality
            setupMainEventListeners();
            setupInboxPagination();
            
            // Initialize profile functionality
            initializeProfileTab();
            
            console.log("Dashboard initialized successfully");
        } catch (error) {
            console.error("Error during dashboard initialization:", error);
        }
    }, 100); // Small delay to ensure scripts are loaded
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

// Enhanced compose form functionality for contact selection and deep research validation
let composeFormInitialized = false;

function setupComposeFormEnhancements() {
    if (composeFormInitialized) {
        console.log('⏭️ Compose form already initialized, skipping...');
        return;
    }
    
    console.log('🚀 Setting up compose form enhancements...');
    
    const contactSelect = document.getElementById('contactSelect');
    const composerType = document.getElementById('composerType');
    
    if (!contactSelect) {
        console.error('❌ Contact select element not found!');
        return;
    }
    
    if (!composerType) {
        console.error('❌ Composer type element not found!');
        return;
    }
    
    console.log('✅ Form elements found, initializing...');
    composeFormInitialized = true;
    
    let allContacts = [];
    let selectedContact = null;
    
    // Load contacts immediately when form is initialized
    loadContactsForSelection();
    
    // Handle contact selection
    contactSelect.addEventListener('change', function() {
        const selectedValue = this.value;
        selectedContact = null; // Reset previous selection

        if (selectedValue) {
            try {
                // The value is a JSON string, so we need to parse it
                const contactData = JSON.parse(selectedValue);
                // Find the full contact object from the loaded list
                selectedContact = allContacts.find(c => c.id === contactData.id);
            } catch (e) {
                console.error('Error parsing selected contact data:', e);
                selectedContact = null;
            }
        }
        
        if (selectedContact) {
            displaySelectedContactInfo(selectedContact);
            populateContactFields(selectedContact);
            updateDeepResearchValidation();
        } else {
            document.getElementById('selectedContactInfo').style.display = 'none';
            clearContactFields();
            updateDeepResearchValidation();
        }
    });
    
    // Handle composer type changes
    composerType.addEventListener('change', function() {
        updateDeepResearchValidation();
    });
    
    // Add event listeners for content-based fields
    const contentUrl = document.getElementById('contentUrl');
    const contentDescription = document.getElementById('contentDescription');
    
    if (contentUrl) {
        contentUrl.addEventListener('input', function() {
            updateDeepResearchValidation();
        });
    }
    
    if (contentDescription) {
        contentDescription.addEventListener('input', function() {
            updateDeepResearchValidation();
        });
    }
    
    // Add event listeners for campaign management
    const createNewCampaignBtn = document.getElementById('createNewCampaignBtn');
    const gtmCampaignSelect = document.getElementById('gtmCampaignSelect');
    const createQuickCampaignBtn = document.getElementById('createQuickCampaignBtn');
    
    if (createNewCampaignBtn) {
        createNewCampaignBtn.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('quickCampaignModal'));
            modal.show();
        });
    }
    
    if (gtmCampaignSelect) {
        gtmCampaignSelect.addEventListener('change', function() {
            updateDeepResearchValidation();
        });
    }
    
    if (createQuickCampaignBtn) {
        createQuickCampaignBtn.addEventListener('click', createQuickCampaign);
    }
    
    function loadContactsForSelection() {
        console.log('🔄 Loading contacts for selection...');
        contactSelect.innerHTML = '<option value="">Loading contacts...</option>';
        
        fetch('/api/contacts-with-research-status')
            .then(response => {
                console.log('📡 Contact API response status:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('📦 Contact API data:', data);
                if (data.success) {
                    allContacts = data.contacts;
                    window.composeContacts = allContacts; // Store globally for generateEmailPreview
                    console.log(`✅ Loaded ${allContacts.length} contacts total`);
                    populateContactSelect(allContacts);
                } else {
                    console.error('❌ Failed to load contacts:', data.message);
                    contactSelect.innerHTML = '<option value="">Failed to load contacts</option>';
                }
            })
            .catch(error => {
                console.error('❌ Error loading contacts:', error);
                contactSelect.innerHTML = '<option value="">Error loading contacts</option>';
            });
    }
    
    function populateContactSelect(contacts) {
        console.log(`🔍 Filtering ${contacts.length} contacts for completed research...`);
        
        // Filter to only show contacts with completed research
        const contactsWithResearch = contacts.filter(contact => 
            contact.research_status.has_completed_research
        );
        
        console.log(`📋 Found ${contactsWithResearch.length} contacts with completed research`);
        
        contactSelect.innerHTML = '<option value="">Select a contact...</option>';
        
        if (contactsWithResearch.length === 0) {
            console.log('⚠️ No contacts with completed research found');
            const noContactsOption = document.createElement('option');
            noContactsOption.value = '';
            noContactsOption.textContent = 'No contacts with completed research available';
            noContactsOption.disabled = true;
            contactSelect.appendChild(noContactsOption);
            return;
        }
        
        contactsWithResearch.forEach(contact => {
            const option = document.createElement('option');
            option.value = JSON.stringify(contact);
            
            // All contacts in this list have research, so always show the indicator
            option.textContent = `🔬 ${contact.name} (${contact.company_name}) - ${contact.email}`;
            option.setAttribute('data-has-research', 'true');
            
            console.log(`✅ Added contact: ${contact.name} (${contact.company_name})`);
            contactSelect.appendChild(option);
        });
        
        console.log('🎯 Contact dropdown populated successfully');
    }
    
    function displaySelectedContactInfo(contact) {
        const contactDetails = document.getElementById('contactDetails');
        const researchStatus = document.getElementById('researchStatus');
        
        if (contactDetails) {
            contactDetails.innerHTML = `
                <strong>${contact.name}</strong><br>
                <small class="text-muted">${contact.email}</small><br>
                <small class="text-muted">${contact.company_name} ${contact.position ? '- ' + contact.position : ''}</small>
            `;
        }
        
        if (researchStatus) {
            // Since we only show contacts with completed research, always show success status
            const statusHtml = '<i class="fas fa-check-circle text-success me-1"></i>Deep research completed';
            const statusClass = 'text-success';
            
            researchStatus.innerHTML = `<small class="${statusClass}">${statusHtml}</small>`;
        }
        
        const selectedContactInfo = document.getElementById('selectedContactInfo');
        if (selectedContactInfo) {
            selectedContactInfo.style.display = 'block';
        }
    }
    
    function populateContactFields(contact) {
        const recipientEmail = document.getElementById('recipientEmail');
        const recipientName = document.getElementById('recipientName');
        const companyName = document.getElementById('composeCompanyName');
        const position = document.getElementById('position');
        
        if (recipientEmail) recipientEmail.value = contact.email;
        if (recipientName) recipientName.value = contact.name;
        if (companyName) companyName.value = contact.company_name;
        if (position) position.value = contact.position || '';
    }
    
    function clearContactFields() {
        const recipientEmail = document.getElementById('recipientEmail');
        const recipientName = document.getElementById('recipientName');
        const companyName = document.getElementById('composeCompanyName');
        const position = document.getElementById('position');
        
        if (recipientEmail) recipientEmail.value = '';
        if (recipientName) recipientName.value = '';
        if (companyName) companyName.value = '';
        if (position) position.value = '';
    }
    
    function updateDeepResearchValidation() {
        const currentComposerType = composerType.value;
        const deepResearchInfo = document.getElementById('deepResearchInfo');
        const contentBasedInfo = document.getElementById('contentBasedInfo');
        const contentBasedFields = document.getElementById('contentBasedFields');
        const generateBtn = document.getElementById('generatePreview');
        
        // Hide all composer-specific info initially
        if (deepResearchInfo) {
            deepResearchInfo.style.display = 'none';
        }
        if (contentBasedInfo) {
            contentBasedInfo.style.display = 'none';
        }
        if (contentBasedFields) {
            contentBasedFields.style.display = 'none';
        }
        
        // Show appropriate info and fields based on composer type
        if (currentComposerType === 'deep_research' && selectedContact) {
            if (deepResearchInfo) {
                deepResearchInfo.style.display = 'block';
            }
        } else if (currentComposerType === 'content_based') {
            if (contentBasedInfo) {
                contentBasedInfo.style.display = 'block';
            }
            if (contentBasedFields) {
                contentBasedFields.style.display = 'block';
            }
        }
        
        // Enable/disable generate button based on contact selection and composer requirements
        if (generateBtn) {
            let canGenerate = false;
            let buttonText = '<i class="fas fa-user me-2"></i>Select Contact First';
            
            if (selectedContact) {
                if (currentComposerType === 'content_based') {
                    // For content-based, also check if required fields are filled
                    const contentUrl = document.getElementById('contentUrl');
                    const contentDescription = document.getElementById('contentDescription');
                    
                    if (contentUrl && contentDescription && contentUrl.value.trim() && contentDescription.value.trim()) {
                        canGenerate = true;
                        buttonText = '<i class="fas fa-magic me-2"></i>Generate Preview';
                    } else {
                        buttonText = '<i class="fas fa-link me-2"></i>Enter Content Details';
                    }
                } else {
                    canGenerate = true;
                    buttonText = '<i class="fas fa-magic me-2"></i>Generate Preview';
                }
            }
            
            generateBtn.disabled = !canGenerate;
            generateBtn.innerHTML = buttonText;
        }
        
        // Update send button validation to require campaign selection
        const sendBtn = document.getElementById('sendComposedEmail');
        const campaignSelect = document.getElementById('gtmCampaignSelect');
        
        if (sendBtn) {
            const hasContact = selectedContact;
            const hasCampaign = campaignSelect?.value;
            
            // Only require contact and campaign - allow manual email composition
            const canSend = hasContact && hasCampaign;
            
            let sendButtonText = '<i class="fas fa-paper-plane me-1"></i>Send Email';
            if (!hasContact) {
                sendButtonText = '<i class="fas fa-user me-1"></i>Select Contact';
            } else if (!hasCampaign) {
                sendButtonText = '<i class="fas fa-bullhorn me-1"></i>Select Campaign';
            }
            
            sendBtn.disabled = !canSend;
            sendBtn.innerHTML = sendButtonText;
        }
    }
    
    function createQuickCampaign() {
        const name = document.getElementById('quickCampaignName').value.trim();
        const description = document.getElementById('quickCampaignDescription').value.trim();
        const type = document.getElementById('quickCampaignType').value;
        const priority = document.getElementById('quickCampaignPriority').value;
        
        if (!name) {
            showToast('Please enter a campaign name', 'error');
            return;
        }
        
        const createBtn = document.getElementById('createQuickCampaignBtn');
        const originalText = createBtn.innerHTML;
        createBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Creating...';
        createBtn.disabled = true;
        
        fetch('/api/campaigns', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                description: description,
                type: type,
                priority: priority,
                email_template: composerType.value || 'deep_research'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Campaign created successfully!', 'success');
                
                // Add to dropdown and select it
                const gtmSelect = document.getElementById('gtmCampaignSelect');
                const option = document.createElement('option');
                option.value = data.campaign_id;
                option.textContent = name;
                option.selected = true;
                gtmSelect.appendChild(option);
                
                // Close modal and clear form
                bootstrap.Modal.getInstance(document.getElementById('quickCampaignModal')).hide();
                document.getElementById('quickCampaignForm').reset();
                
                // Update validation states
                updateDeepResearchValidation();
            } else {
                showToast('Failed to create campaign: ' + (data.error || 'Unknown error'), 'error');
            }
        })
        .catch(error => {
            console.error('Error creating campaign:', error);
            showToast('Error creating campaign: ' + error.message, 'error');
        })
        .finally(() => {
            createBtn.innerHTML = originalText;
            createBtn.disabled = false;
        });
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
window.setupComposeFormEnhancements = setupComposeFormEnhancements;

// Profile Tab Functionality
function initializeProfileTab() {
    console.log("Initializing profile tab...");
    
    const profileForm = document.getElementById('tenantProfileForm');
    if (profileForm) {
        // Load existing profile data
        loadTenantProfile();
        
        // Setup form submission
        profileForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveTenantProfile();
        });
        
        // Setup real-time preview
        setupProfilePreview();
        
        console.log("Profile tab initialized successfully");
    } else {
        console.error("Profile form not found");
    }
}

function loadTenantProfile() {
    fetch('/api/tenant/profile')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.profile) {
                populateProfileForm(data.profile);
                updateProfilePreview(data.profile);
            }
        })
        .catch(error => {
            console.error('Error loading profile:', error);
        });
}

function populateProfileForm(profile) {
    const fields = [
        'firstName', 'lastName', 'jobTitle', 'phoneNumber', 'personalEmail',
        'linkedinProfile', 'companyName', 'companyWebsite', 'companySize',
        'industry', 'companyDescription', 'emailSignature', 'brandVoice',
        'preferredCTA', 'calendarUrl', 'valueProposition'
    ];
    
    fields.forEach(field => {
        const element = document.getElementById(field);
        if (element && profile[field]) {
            element.value = profile[field];
        }
    });
}

function saveTenantProfile() {
    const form = document.getElementById('tenantProfileForm');
    const formData = new FormData(form);
    const profileData = {};
    
    // Convert FormData to object
    for (let [key, value] of formData.entries()) {
        profileData[key] = value;
    }
    
    const saveBtn = document.getElementById('saveProfileBtn');
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
    saveBtn.disabled = true;
    
    fetch('/api/tenant/profile', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(profileData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Profile saved successfully!', 'success');
            updateProfilePreview(profileData);
        } else {
            showToast('Failed to save profile: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Error saving profile:', error);
        showToast('Error saving profile: ' + error.message, 'error');
    })
    .finally(() => {
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    });
}

function setupProfilePreview() {
    const fields = [
        'firstName', 'lastName', 'jobTitle', 'companyName', 'emailSignature'
    ];
    
    fields.forEach(field => {
        const element = document.getElementById(field);
        if (element) {
            element.addEventListener('input', updateProfilePreview);
        }
    });
}

function updateProfilePreview(profileData = null) {
    const previewElement = document.getElementById('profilePreview');
    if (!previewElement) return;
    
    if (!profileData) {
        // Get current form data
        const form = document.getElementById('tenantProfileForm');
        const formData = new FormData(form);
        profileData = {};
        for (let [key, value] of formData.entries()) {
            profileData[key] = value;
        }
    }
    
    const firstName = profileData.firstName || '';
    const lastName = profileData.lastName || '';
    const jobTitle = profileData.jobTitle || '';
    const companyName = profileData.companyName || '';
    const emailSignature = profileData.emailSignature || '';
    
    if (firstName && lastName) {
        let preview = `
            <div class="mb-2">
                <strong>${firstName} ${lastName}</strong><br>
                ${jobTitle ? jobTitle + '<br>' : ''}
                ${companyName ? companyName + '<br>' : ''}
            </div>
        `;
        
        if (emailSignature) {
            preview += `<div class="text-muted small">${emailSignature}</div>`;
        }
        
        previewElement.innerHTML = preview;
    } else {
        previewElement.innerHTML = '<small class="text-muted">Fill out the form to see a preview of how your information will appear in emails</small>';
    }
}

// Global profile functions
window.initializeProfileTab = initializeProfileTab;
window.loadTenantProfile = loadTenantProfile;
window.saveTenantProfile = saveTenantProfile;