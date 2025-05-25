// SalesBot CRM - Dashboard JavaScript

// Global variables
let currentContacts = [];
let emailHistory = window.emailHistoryData || [];
let currentContactEmail = null; // For modal export functionality

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