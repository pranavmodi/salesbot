// SalesBot CRM - Contact Management Module

// Global contact-related variables
let currentContacts = [];
let selectedContacts = [];
let currentContactEmail = null;

// Initialize contact-related functionality
function initializeContacts() {
    setupContactSearch();
    setupContactFilters();
    setupContactEventListeners();
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