// SalesBot CRM - Dashboard JavaScript

// Global variables
let currentContacts = [];
let emailHistory = window.emailHistoryData || [];
let currentContactEmail = null; // For modal export functionality
let selectedContacts = []; // For bulk email composition

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    setupSearch();
    setupFilters();
});

function setupEventListeners() {
    // Pagination
    const perPageSelect = document.getElementById('perPage');
    if (perPageSelect) {
        perPageSelect.addEventListener('change', function() {
            changePage(1);
        });
    }

    document.querySelectorAll('.pagination .page-link').forEach(link => {
        if (link.hasAttribute('data-page')) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                changePage(parseInt(this.getAttribute('data-page')));
            });
        }
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
}

function setupSearch() {
    const searchInput = document.getElementById('contactSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const contactRows = document.querySelectorAll('.contact-row');
            
            contactRows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    row.style.display = '';
                    row.classList.remove('d-none');
                } else {
                    row.style.display = 'none';
                    row.classList.add('d-none');
                }
            });
            
            updateContactStats();
        });
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
    const contactRows = document.querySelectorAll('.contact-row');
    
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
    // Show loading state
    const contactsContainer = document.getElementById('contactsContainer');
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
    const contactsContainer = document.getElementById('contactsContainer');
    
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
    const visibleRows = document.querySelectorAll('.contact-row:not(.d-none)');
    const statsNumbers = document.querySelectorAll('.stats-number');
    
    if (statsNumbers[0]) {
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

// Email composition functions (for compose tab)
function generateEmailPreview() {
    const form = document.getElementById('composeForm');
    const leadInfo = {
        name: form.recipientName.value,
        email: form.recipientEmail.value,
        company: form.companyName.value,
        position: form.position.value
    };
    
    fetch('/preview_email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(leadInfo)
    })
    .then(response => response.json())
    .then(data => {
        form.emailSubject.value = data.subject;
        form.emailBody.value = data.body;
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('errorToast', 'Failed to generate email preview');
    });
}

function sendComposedEmail(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    
    fetch('/send_email', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', 'Email sent successfully!');
            form.reset();
        } else {
            showToast('errorToast', data.message || 'Failed to send email');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('errorToast', 'An error occurred while sending the email');
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
    // Prepare contact data for AI composer
    const contactData = {
        name: contact.first_name || contact.display_name || 'There',
        email: contact.email,
        company: contact.company || '',
        position: contact.job_title || ''
    };
    
    // Call the existing AI email preview API
    return fetch('/api/preview_email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(contactData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.subject && data.body) {
            return {
                contact: contact,
                subject: data.subject,
                body: data.body,
                success: true,
                index: index
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
    
    // Prepare recipients data for bulk sending
    const recipients = window.generatedEmails.map(email => ({
        recipient_email: email.contact.email,
        recipient_name: email.contact.display_name || email.contact.first_name || 'There',
        subject: email.subject,
        body: email.body
    }));
    
    // Send bulk emails
    fetch('/api/send_bulk_emails', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ recipients: recipients })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `Successfully sent ${data.results.success} emails!`);
            
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
            showToast('errorToast', data.message || 'Failed to send emails');
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
    
    // Prepare recipients data for bulk sending
    const recipients = window.previewedEmails.map(email => ({
        recipient_email: email.contact.email,
        recipient_name: email.contact.display_name || email.contact.first_name || 'There',
        subject: email.subject,
        body: email.body
    }));
    
    // Send bulk emails
    fetch('/api/send_bulk_emails', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ recipients: recipients })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `Successfully sent ${data.results.success} emails!`);
            
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
            showToast('errorToast', data.message || 'Failed to send emails');
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