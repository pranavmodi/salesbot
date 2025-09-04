// SalesBot CRM - Contact Management Module

// Global contact-related variables
let currentContacts = [];
let selectedContacts = [];
let currentContactEmail = null;
let lastComposeContact = null;

// Initialize contact-related functionality
function initializeContacts() {
    setupContactSearch();
    setupContactFilters();
    setupContactEventListeners();
    
    // Load the first page of contacts on initialization
    console.log("Loading initial contacts data...");
    changePage(1);
}

// Contact search functionality
function setupContactSearch() {
    const contactSearchInput = document.getElementById('contactSearch');
    if (contactSearchInput) {
        let searchTimeout;
        
        contactSearchInput.addEventListener('input', function() {
            const searchTerm = this.value.trim();
            
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }
            
            searchTimeout = setTimeout(() => {
                performContactSearch(searchTerm);
            }, 300);
        });
    }
}

function performContactSearch(searchTerm) {
    const contactsContainer = document.getElementById('contacts-table-container');
    const originalContent = contactsContainer.innerHTML;
    
    if (searchTerm === '') {
        window.location.href = window.location.pathname;
        return;
    }
    
    console.log(`Performing server-side contact search: "${searchTerm}"`);
    
    contactsContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Searching contacts...</p>
        </div>
    `;
    
    fetch(`/api/contacts/search?q=${encodeURIComponent(searchTerm)}`)
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
                    <a href="mailto:${contact.email}" class="text-decoration-none">
                        ${contact.email}
                    </a>
                </td>
                <td>
                    <span class="text-muted">${location}</span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary btn-sm" 
                                onclick="viewContactDetails('${contact.email}')" 
                                title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button type="button" class="btn btn-outline-secondary btn-sm" 
                                onclick="exportContact('${contact.email}')" 
                                title="Export">
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
    
    // Update selection counts
    updateSelectionCount();
    
    // Store current contacts for bulk operations
    currentContacts = contacts;
}

function clearContactSearch() {
    const contactSearchInput = document.getElementById('contactSearch');
    if (contactSearchInput) {
        contactSearchInput.value = '';
    }
    window.location.href = window.location.pathname;
}

// Contact filters
function setupContactFilters() {
    const filterButtons = document.querySelectorAll('[data-filter]');
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            const filter = this.getAttribute('data-filter');
            applyContactFilter(filter);
        });
    });
}

function applyContactFilter(filter) {
    console.log(`Applying contact filter: ${filter}`);
    
    // Update active filter button
    const filterButtons = document.querySelectorAll('[data-filter]');
    filterButtons.forEach(btn => btn.classList.remove('active'));
    
    const activeButton = document.querySelector(`[data-filter="${filter}"]`);
    if (activeButton) {
        activeButton.classList.add('active');
    }
    
    if (filter === 'uncontacted') {
        handleUncontactedFilter();
    } else {
        // Handle other filters (all, contacted, etc.)
        changePage(1);
    }
}

function handleUncontactedFilter() {
    const contactsContainer = document.getElementById('contacts-table-container');
    
    contactsContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading uncontacted contacts...</p>
        </div>
    `;
    
    fetch('/api/contacts/uncontacted')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            displayUncontactedContacts(data);
        })
        .catch(error => {
            console.error('Error loading uncontacted contacts:', error);
            showToast('errorToast', 'Failed to load uncontacted contacts: ' + error.message);
        });
}

function displayUncontactedContacts(data) {
    const contactsContainer = document.getElementById('contacts-table-container');
    const contacts = data.contacts || [];
    
    if (contacts.length === 0) {
        contactsContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-check-circle fa-3x text-success mb-3"></i>
                <h5 class="text-success">All contacts have been reached!</h5>
                <p class="text-muted">Every contact in your database has been contacted at least once.</p>
            </div>
        `;
        return;
    }
    
    let tableHtml = `
        <div class="mb-3">
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>${contacts.length}</strong> contacts have not been contacted yet.
            </div>
        </div>
        
        <div class="table-responsive">
            <table class="table table-hover">
                <thead class="table-light">
                    <tr>
                        <th style="width: 40px;">
                            <input type="checkbox" class="form-check-input" id="selectAllUncontacted" onchange="toggleSelectAll()" style="margin: 0;">
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
                        <div class="badge bg-warning text-dark small">Never contacted</div>
                    </div>
                </td>
                <td>
                    <span class="fw-semibold">${company}</span>
                </td>
                <td>
                    <span>${jobTitle}</span>
                </td>
                <td>
                    <a href="mailto:${contact.email}" class="text-decoration-none">
                        ${contact.email}
                    </a>
                </td>
                <td>
                    <span class="text-muted">${location}</span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary btn-sm" 
                                onclick="viewContactDetails('${contact.email}')" 
                                title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button type="button" class="btn btn-outline-secondary btn-sm" 
                                onclick="exportContact('${contact.email}')" 
                                title="Export">
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
    updateSelectionCount();
    currentContacts = contacts;
}

// Contact selection management
function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAllUncontacted') || document.getElementById('selectAllSearchResults');
    const contactCheckboxes = document.querySelectorAll('.contact-checkbox');
    
    contactCheckboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
    
    updateSelectionCount();
}

function toggleSelectAllSearchResults() {
    toggleSelectAll();
}

function updateSelectionCount() {
    const selectedCheckboxes = document.querySelectorAll('.contact-checkbox:checked');
    const selectedContactsDiv = document.getElementById('selectedContactsCount');
    const bulkEmailBtn = document.getElementById('bulkEmailBtn');
    
    selectedContacts = Array.from(selectedCheckboxes).map(checkbox => {
        try {
            return JSON.parse(checkbox.getAttribute('data-contact'));
        } catch (e) {
            console.error('Error parsing contact data:', e);
            return null;
        }
    }).filter(contact => contact !== null);
    
    if (selectedContactsDiv) {
        selectedContactsDiv.textContent = selectedContacts.length;
    }
    
    if (bulkEmailBtn) {
        if (selectedContacts.length > 0) {
            bulkEmailBtn.textContent = `Compose Email (${selectedContacts.length})`;
            bulkEmailBtn.disabled = false;
        } else {
            bulkEmailBtn.textContent = 'Compose Email';
            bulkEmailBtn.disabled = true;
        }
    }
}

// Contact details and modal management
function viewContactDetails(email) {
    console.log(`Loading contact details for: ${email}`);
    currentContactEmail = email;
    
    fetch(`/api/contacts/${encodeURIComponent(email)}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            showContactModal(data.contact);
        })
        .catch(error => {
            console.error('Error loading contact details:', error);
            showToast('errorToast', 'Failed to load contact details: ' + error.message);
        });
}

function showContactModal(contactData) {
    const modal = document.getElementById('contactDetailsModal');
    if (!modal) {
        console.error('Contact details modal not found in DOM');
        showToast('errorToast', 'Contact details modal not available');
        return;
    }
    
    const modalTitle = modal.querySelector('.modal-title');
    const modalBody = modal.querySelector('#contactDetailsContent');
    
    if (!modalTitle || !modalBody) {
        console.error('Modal elements not found - modalTitle:', modalTitle, 'modalBody:', modalBody);
        showToast('errorToast', 'Contact modal elements not found');
        return;
    }
    
    const displayName = contactData.display_name || contactData.full_name || 
                       `${contactData.first_name || ''} ${contactData.last_name || ''}`.trim() || 'Unknown';
    
    modalTitle.textContent = `Contact Details - ${displayName}`;
    
    modalBody.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-muted mb-3">Personal Information</h6>
                <div class="mb-2">
                    <strong>Full Name:</strong> ${displayName}
                </div>
                <div class="mb-2">
                    <strong>Email:</strong> 
                    <a href="mailto:${contactData.email}" class="text-decoration-none">${contactData.email}</a>
                </div>
                <div class="mb-2">
                    <strong>Phone:</strong> ${contactData.phone || 'Not provided'}
                </div>
                <div class="mb-2">
                    <strong>Location:</strong> ${contactData.location || 'Not provided'}
                </div>
            </div>
            <div class="col-md-6">
                <h6 class="text-muted mb-3">Professional Information</h6>
                <div class="mb-2">
                    <strong>Company:</strong> ${contactData.company || contactData.company_name || 'Not provided'}
                </div>
                <div class="mb-2">
                    <strong>Job Title:</strong> ${contactData.job_title || 'Not provided'}
                </div>
                <div class="mb-2">
                    <strong>LinkedIn:</strong> 
                    ${contactData.linkedin_url ? 
                        `<a href="${contactData.linkedin_url}" target="_blank" class="text-decoration-none">
                            <i class="fab fa-linkedin me-1"></i>View Profile
                        </a>` : 'Not provided'}
                </div>
            </div>
        </div>
        
        <hr>
        
        <div class="row">
            <div class="col-12">
                <h6 class="text-muted mb-3">Additional Information</h6>
                <div class="mb-2">
                    <strong>Research Notes:</strong>
                    <div class="mt-1 p-2 bg-light rounded">
                        ${contactData.research_notes || 'No research notes available'}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Load email conversations for this contact
    loadEmailConversations(contactData.email);
    
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

// Contact export functionality
function exportContact(email) {
    console.log(`Exporting contact: ${email}`);
    
    const link = document.createElement('a');
    link.href = `/api/contacts/${encodeURIComponent(email)}/export`;
    link.download = `contact_${email.replace('@', '_at_')}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast('successToast', 'Contact exported successfully!');
}

// Contact stats update
function updateContactStats(count = null) {
    const contactCountElement = document.getElementById('contactCount');
    if (contactCountElement && count !== null) {
        contactCountElement.textContent = count;
    }
}

// Compose email from contact modal
function composeEmailFromModal() {
    if (!currentContactEmail) {
        showToast('errorToast', 'No contact selected');
        return;
    }
    
    // Get current contact data from the API
    fetch(`/api/contacts/${encodeURIComponent(currentContactEmail)}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            const contact = data.contact;
            composeAIGeneratedEmail(contact);
        })
        .catch(error => {
            console.error('Error loading contact for email composition:', error);
            showToast('errorToast', 'Failed to load contact details for email composition');
        });
}

// Compose LinkedIn message from contact modal
function composeLinkedInFromModal() {
    if (!currentContactEmail) {
        showToast('errorToast', 'No contact selected');
        return;
    }
    
    // Get current contact data from the API
    fetch(`/api/contacts/${encodeURIComponent(currentContactEmail)}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            const contact = data.contact;
            composeAIGeneratedLinkedInMessage(contact);
        })
        .catch(error => {
            console.error('Error loading contact for LinkedIn composition:', error);
            showToast('errorToast', 'Failed to load contact details for LinkedIn composition');
        });
}

// AI-powered email composition
function composeAIGeneratedEmail(contact) {
    showComposeModal('email', contact);
}

// AI-powered LinkedIn message composition
function composeAIGeneratedLinkedInMessage(contact) {
    showComposeModal('linkedin', contact);
}

// Show compose modal with AI generation
function showComposeModal(type, contact) {
    const modalId = type === 'email' ? 'composeEmailModal' : 'composeLinkedInModal';
    let modal = document.getElementById(modalId);
    
    // Remember the last contact used for composition to support legacy helpers
    lastComposeContact = contact;
    
    if (!modal) {
        modal = createComposeModal(type, contact);
        document.body.appendChild(modal);
    } else {
        // Modal already exists, just regenerate content
        const composeContent = modal.querySelector('#composeContent');
        composeContent.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Generating...</span>
                </div>
                <p class="mt-2">Generating personalized ${type} message...</p>
            </div>
        `;
        generateComposedContent(type, contact, modal);
    }
    
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

// Create compose modal
function createComposeModal(type, contact) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = type === 'email' ? 'composeEmailModal' : 'composeLinkedInModal';
    
    const title = type === 'email' ? 'Compose Email' : 'Compose LinkedIn Message';
    const icon = type === 'email' ? 'fas fa-envelope' : 'fab fa-linkedin';
    
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="${icon} me-2"></i>${title}
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3 border-bottom pb-3">
                        <div class="row">
                            <div class="col-md-6">
                                <label class="form-label"><strong>Demo Tenant ID:</strong></label>
                                <input type="text" class="form-control form-control-sm" id="demoTenantId" placeholder="e.g., 4fe5fee7-2733-489d-8847-a92c28e43f68">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label"><strong>Campaign:</strong></label>
                                <input type="text" class="form-control form-control-sm" id="demoCampaign" placeholder="e.g., cold-outreach-q4">
                            </div>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mt-2">
                            <small class="text-muted">Demo URL: https://getpossibleminds.com/tenants/{tenant-id}/control-panel?utm_source=email&utm_medium=email&utm_campaign={campaign}</small>
                            <button type="button" class="btn btn-primary btn-sm" id="generateContentBtn" onclick="generateContentWithConfig('${type}', '${contact.email}')">
                                <i class="fas fa-magic me-1"></i>Generate Message
                            </button>
                        </div>
                    </div>
                    <div id="composeContent">
                        <div class="text-center py-4 text-muted">
                            <i class="fas fa-arrow-up fa-2x mb-2"></i>
                            <p>Enter tenant ID and campaign above, then click "Generate Message"</p>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-outline-primary" id="regenerateBtn" onclick="regenerateContent('${type}', '${contact.email}')" style="display: none;">
                        <i class="fas fa-redo me-1"></i>Regenerate
                    </button>
                    <button type="button" class="btn btn-primary" id="copyToClipboardBtn" onclick="copyComposedContent()" style="display: none;">
                        <i class="fas fa-copy me-1"></i>Copy to Clipboard
                    </button>
                </div>
            </div>
        </div>
    `;
    
    return modal;
}

// Generate content with config from modal fields
function generateContentWithConfig(type, email) {
    const modal = document.getElementById(type === 'email' ? 'composeEmailModal' : 'composeLinkedInModal');
    if (!modal) return;
    
    const tenantIdField = modal.querySelector('#demoTenantId');
    const campaignField = modal.querySelector('#demoCampaign');
    
    if (!tenantIdField.value.trim()) {
        alert('Please enter a Demo Tenant ID');
        tenantIdField.focus();
        return;
    }
    
    // Get contact data
    fetch(`/api/contacts/${encodeURIComponent(email)}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Show loading state
            const composeContent = modal.querySelector('#composeContent');
            composeContent.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Generating...</span>
                    </div>
                    <p class="mt-2">Generating personalized ${type} message...</p>
                </div>
            `;
            
            generateComposedContent(type, data.contact, modal);
        })
        .catch(error => {
            console.error('Error loading contact for composition:', error);
            const composeContent = modal.querySelector('#composeContent');
            composeContent.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Failed to load contact details: ${error.message}
                </div>
            `;
        });
}

// Generate AI content for email or LinkedIn
function generateComposedContent(type, contact, modal) {
    const endpoint = type === 'email' ? '/api/compose/email' : '/api/compose/linkedin';
    
    // Get demo configuration from modal fields
    const tenantIdField = modal.querySelector('#demoTenantId');
    const campaignField = modal.querySelector('#demoCampaign');
    const tenantId = tenantIdField ? tenantIdField.value.trim() : '';
    const campaign = campaignField ? campaignField.value.trim() : '';
    
    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            contact: {
                email: contact.email,
                name: contact.display_name || contact.full_name || `${contact.first_name || ''} ${contact.last_name || ''}`.trim(),
                company: contact.company || contact.company_name,
                job_title: contact.job_title,
                linkedin_url: contact.linkedin_url
            },
            demo_config: {
                tenant_id: tenantId,
                campaign: campaign
            }
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayComposedContent(modal, type, data, contact);
        } else {
            throw new Error(data.message || 'Failed to generate content');
        }
    })
    .catch(error => {
        console.error(`Error generating ${type} content:`, error);
        const composeContent = modal.querySelector('#composeContent');
        composeContent.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to generate ${type} content: ${error.message}
            </div>
        `;
    });
}

// Display the generated content in the modal
function displayComposedContent(modal, type, data, contact) {
    const composeContent = modal.querySelector('#composeContent');
    const regenerateBtn = modal.querySelector('#regenerateBtn');
    const copyBtn = modal.querySelector('#copyToClipboardBtn');
    
    const displayName = contact.display_name || contact.full_name || `${contact.first_name || ''} ${contact.last_name || ''}`.trim();
    
    if (type === 'email') {
        composeContent.innerHTML = `
            <div class="mb-3">
                <h6><i class="fas fa-user me-2"></i>To: ${displayName} (${contact.email})</h6>
                <small class="text-muted">${contact.company || contact.company_name || 'Unknown Company'}</small>
            </div>
            
            <div class="mb-3">
                <label class="form-label"><strong>Subject:</strong></label>
                <div class="form-control" id="generatedSubject" style="background-color: #f8f9fa;">${data.subject}</div>
            </div>
            
            <div class="mb-3">
                <label class="form-label"><strong>Message:</strong></label>
                <div class="form-control" id="generatedBody" style="background-color: #f8f9fa; min-height: 300px; white-space: pre-wrap;">${data.body}</div>
            </div>
        `;
    } else {
        composeContent.innerHTML = `
            <div class="mb-3">
                <h6><i class="fab fa-linkedin me-2"></i>LinkedIn Message to: ${displayName}</h6>
                <small class="text-muted">${contact.company || contact.company_name || 'Unknown Company'}</small>
                ${contact.linkedin_url ? `<a href="${contact.linkedin_url}" target="_blank" class="btn btn-sm btn-outline-primary ms-2">
                    <i class="fas fa-external-link-alt me-1"></i>View Profile
                </a>` : ''}
            </div>
            
            <div class="mb-3">
                <label class="form-label"><strong>Message:</strong></label>
                <div class="form-control" id="generatedMessage" style="background-color: #f8f9fa; min-height: 200px; white-space: pre-wrap;">${data.message}</div>
            </div>
        `;
    }
    
    // Show action buttons
    regenerateBtn.style.display = 'inline-block';
    copyBtn.style.display = 'inline-block';
}

// Legacy compatibility shim: some older code paths may call this helper.
// Normalize various possible signatures and delegate to displayComposedContent.
function updateComposeModalContent() {
    // Supported patterns:
    // 1) (type, data)
    // 2) (modal, type, data, contact)
    // 3) (data)
    let modal, type, data, contact;
    const args = Array.from(arguments);
    
    if (args.length >= 2 && typeof args[0] === 'string') {
        // (type, data[, contact])
        type = args[0];
        data = args[1] || {};
        contact = args[2] || lastComposeContact;
        modal = document.getElementById(type === 'email' ? 'composeEmailModal' : 'composeLinkedInModal');
    } else if (args.length >= 3 && args[0] && args[0].querySelector) {
        // (modal, type, data[, contact])
        modal = args[0];
        type = args[1];
        data = args[2] || {};
        contact = args[3] || lastComposeContact;
    } else if (args.length === 1 && typeof args[0] === 'object') {
        // (data)
        data = args[0] || {};
        // Infer type from fields
        type = 'message' in data && !('subject' in data) ? 'linkedin' : 'email';
        modal = document.getElementById(type === 'email' ? 'composeEmailModal' : 'composeLinkedInModal');
        contact = lastComposeContact;
    }
    
    if (!modal) {
        return;
    }
    
    // Ensure minimal shape expected by displayComposedContent
    if (type === 'email') {
        data = {
            subject: data.subject || '',
            body: data.body || ''
        };
    } else {
        data = {
            message: data.message || ''
        };
    }
    
    displayComposedContent(modal, type, data, contact || { email: '' });
}

// Regenerate content
function regenerateContent(type, email) {
    fetch(`/api/contacts/${encodeURIComponent(email)}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            const modal = document.getElementById(type === 'email' ? 'composeEmailModal' : 'composeLinkedInModal');
            const composeContent = modal.querySelector('#composeContent');
            
            composeContent.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Regenerating...</span>
                    </div>
                    <p class="mt-2">Regenerating ${type} content...</p>
                </div>
            `;
            
            generateComposedContent(type, data.contact, modal);
        })
        .catch(error => {
            console.error('Error regenerating content:', error);
            showToast('errorToast', 'Failed to regenerate content');
        });
}

// Copy composed content to clipboard
function copyComposedContent() {
    let textToCopy = '';
    
    const subject = document.getElementById('generatedSubject');
    const body = document.getElementById('generatedBody');
    const message = document.getElementById('generatedMessage');
    
    if (subject && body) {
        // Email content
        textToCopy = `Subject: ${subject.textContent}\n\n${body.textContent}`;
    } else if (message) {
        // LinkedIn message content
        textToCopy = message.textContent;
    }
    
    if (textToCopy) {
        navigator.clipboard.writeText(textToCopy).then(() => {
            showToast('successToast', 'Content copied to clipboard!');
        }).catch(error => {
            console.error('Failed to copy to clipboard:', error);
            showToast('errorToast', 'Failed to copy to clipboard');
        });
    }
}

// Mark contact as contacted or not contacted
function markAsContacted(email, contacted) {
    fetch(`/api/contacts/${encodeURIComponent(email)}/contacted`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            contacted: contacted
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the row visually
            const contactRow = document.querySelector(`tr[data-contact-email="${email}"]`);
            if (contactRow) {
                if (contacted) {
                    contactRow.classList.add('table-success');
                    contactRow.setAttribute('data-contacted', 'true');
                    showToast('successToast', 'Contact marked as contacted');
                } else {
                    contactRow.classList.remove('table-success');
                    contactRow.setAttribute('data-contacted', 'false');
                    showToast('successToast', 'Contact marked as not contacted');
                }
                
                // Update the button
                const actionCell = contactRow.querySelector('td:last-child');
                const buttonGroup = actionCell.querySelector('.btn-group');
                const contactedBtn = buttonGroup.querySelector('[onclick*="markAsContacted"]');
                
                if (contacted) {
                    contactedBtn.className = 'btn btn-success btn-sm';
                    contactedBtn.setAttribute('onclick', `markAsContacted('${email}', false)`);
                    contactedBtn.setAttribute('title', 'Mark as Not Contacted');
                    contactedBtn.innerHTML = '<i class="fas fa-check"></i>';
                } else {
                    contactedBtn.className = 'btn btn-outline-warning btn-sm';
                    contactedBtn.setAttribute('onclick', `markAsContacted('${email}', true)`);
                    contactedBtn.setAttribute('title', 'Mark as Contacted');
                    contactedBtn.innerHTML = '<i class="fas fa-handshake"></i>';
                }
            }
        } else {
            throw new Error(data.message || 'Failed to update contact status');
        }
    })
    .catch(error => {
        console.error('Error updating contact status:', error);
        showToast('errorToast', 'Failed to update contact status: ' + error.message);
    });
}

// Contact event listeners setup
function setupContactEventListeners() {
    // Export from modal button
    const exportFromModalBtn = document.getElementById('exportFromModal');
    if (exportFromModalBtn) {
        exportFromModalBtn.addEventListener('click', function() {
            if (currentContactEmail) {
                exportContact(currentContactEmail);
            }
        });
    }
    
    // Bulk email button
    const bulkEmailBtn = document.getElementById('bulkEmailBtn');
    if (bulkEmailBtn) {
        bulkEmailBtn.addEventListener('click', startBulkEmailComposition);
    }
    
    // Pagination click handlers
    setupPaginationEventListeners();
}

function setupPaginationEventListeners() {
    // Set up event delegation for pagination links
    document.addEventListener('click', function(e) {
        const target = e.target.closest('a[data-page]');
        if (target && target.getAttribute('data-page')) {
            e.preventDefault();
            const page = parseInt(target.getAttribute('data-page'));
            if (!isNaN(page)) {
                changePage(page);
            }
        }
    });
}

function startBulkEmailComposition() {
    if (selectedContacts.length === 0) {
        showToast('warningToast', 'Please select contacts first');
        return;
    }
    
    console.log(`Starting bulk email composition for ${selectedContacts.length} contacts`);
    showBulkEmailComposer(selectedContacts);
}

// Pagination for contacts
function changePage(page) {
    addPaginationLoadingState('contactsContainer');
    
    const perPage = document.getElementById('perPage')?.value || 50;
    const url = `/api/contacts?page=${page}&per_page=${perPage}`;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Update contacts display
            const contactsContainer = document.getElementById('contacts-table-container');
            if (contactsContainer && data.html) {
                contactsContainer.innerHTML = data.html;
            }
            
            updateContactStats(data.total);
            removePaginationLoadingState('contactsContainer');
        })
        .catch(error => {
            console.error('Error loading contacts:', error);
            showToast('errorToast', 'Failed to load contacts: ' + error.message);
            removePaginationLoadingState('contactsContainer');
        });
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeContacts,
        performContactSearch,
        clearContactSearch,
        viewContactDetails,
        exportContact,
        updateSelectionCount,
        toggleSelectAll,
        changePage,
        currentContacts,
        selectedContacts,
        currentContactEmail
    };
}

// Global function assignments for HTML onclick handlers
window.clearContactSearch = clearContactSearch;
window.viewContactDetails = viewContactDetails;
window.exportContact = exportContact;
window.updateSelectionCount = updateSelectionCount;
window.toggleSelectAll = toggleSelectAll;
window.toggleSelectAllSearchResults = toggleSelectAllSearchResults;
window.startBulkEmailComposition = startBulkEmailComposition;
window.changePage = changePage;
window.composeEmailFromModal = composeEmailFromModal;
window.composeLinkedInFromModal = composeLinkedInFromModal;
window.regenerateContent = regenerateContent;
window.copyComposedContent = copyComposedContent;
window.markAsContacted = markAsContacted;
window.generateContentWithConfig = generateContentWithConfig;