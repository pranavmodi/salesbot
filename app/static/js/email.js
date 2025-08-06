// SalesBot CRM - Email Management Module

// Global email-related variables
let emailHistory = window.emailHistoryData || [];
let currentGlobalAccount = null;

// Initialize email functionality
function initializeEmail() {
    setupEmailEventListeners();
    loadGlobalEmailAccounts();
    setupGlobalAccountSelector();
    setupEmailHistoryPagination();
    loadGTMCampaigns();
    setupCampaignValidation();
}

// Email event listeners
function setupEmailEventListeners() {
    const generatePreviewBtn = document.getElementById('generatePreview');
    const composeForm = document.getElementById('composeForm');
    const testEmailBtn = document.getElementById('testEmailConnection');
    
    if (generatePreviewBtn) {
        generatePreviewBtn.addEventListener('click', generateEmailPreview);
    }
    if (composeForm) {
        composeForm.addEventListener('submit', sendComposedEmail);
    }
    if (testEmailBtn) {
        testEmailBtn.addEventListener('click', testEmailConnection);
    }
}

// Global email accounts management
function loadGlobalEmailAccounts() {
    fetch('/api/email/accounts')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const accounts = data.accounts || [];
                console.log('Loaded email accounts:', accounts);
                
                // Update global account selector if it exists
                const globalAccountSelector = document.getElementById('globalAccountSelector');
                if (globalAccountSelector && accounts.length > 0) {
                    globalAccountSelector.innerHTML = '<option value="">Select Email Account</option>';
                    
                    accounts.forEach(account => {
                        const option = document.createElement('option');
                        option.value = account.email;
                        option.textContent = `${account.email} (${account.provider})`;
                        option.setAttribute('data-account', JSON.stringify(account));
                        globalAccountSelector.appendChild(option);
                    });
                    
                    // Set the first account as default if none selected
                    if (!currentGlobalAccount && accounts.length > 0) {
                        globalAccountSelector.value = accounts[0].email;
                        currentGlobalAccount = accounts[0];
                        updateActiveAccountInfo(accounts[0]);
                    }
                }
            } else {
                console.error('Failed to load email accounts:', data.message);
            }
        })
        .catch(error => {
            console.error('Error loading email accounts:', error);
        });
}

function setupGlobalAccountSelector() {
    const globalAccountSelector = document.getElementById('globalAccountSelector');
    if (globalAccountSelector) {
        globalAccountSelector.addEventListener('change', function() {
            const selectedEmail = this.value;
            if (selectedEmail) {
                const option = this.querySelector(`option[value="${selectedEmail}"]`);
                if (option) {
                    const accountData = JSON.parse(option.getAttribute('data-account'));
                    currentGlobalAccount = accountData;
                    updateActiveAccountInfo(accountData);
                    
                    // Load inbox for this account if on inbox tab
                    const inboxTab = document.getElementById('inbox-tab');
                    if (inboxTab && inboxTab.classList.contains('active')) {
                        loadInboxForAccount(accountData);
                    }
                }
            } else {
                currentGlobalAccount = null;
                updateActiveAccountInfo(null);
            }
        });
    }
}

function updateActiveAccountInfo(account) {
    const activeAccountInfo = document.getElementById('activeAccountInfo');
    if (activeAccountInfo) {
        if (account) {
            activeAccountInfo.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="fas fa-envelope text-primary me-2"></i>
                    <div>
                        <strong>${account.email}</strong>
                        <small class="text-muted d-block">${account.provider}</small>
                    </div>
                    <button class="btn btn-outline-primary btn-sm ms-3" onclick="testGlobalAccountConnection()">
                        <i class="fas fa-plug me-1"></i>Test
                    </button>
                </div>
            `;
        } else {
            activeAccountInfo.innerHTML = `
                <div class="text-muted">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    No email account selected
                </div>
            `;
        }
    }
}

function testGlobalAccountConnection() {
    if (!currentGlobalAccount) {
        showToast('warningToast', 'Please select an email account first');
        return;
    }
    
    const testBtn = document.querySelector('[onclick="testGlobalAccountConnection()"]');
    const originalText = testBtn.innerHTML;
    
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Testing...';
    testBtn.disabled = true;
    
    fetch('/api/email/test-connection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            email: currentGlobalAccount.email
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', 'Email connection successful!');
        } else {
            showToast('errorToast', 'Email connection failed: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error testing email connection:', error);
        showToast('errorToast', 'Failed to test email connection');
    })
    .finally(() => {
        testBtn.innerHTML = originalText;
        testBtn.disabled = false;
    });
}

// Email composition and sending
function generateEmailPreview() {
    const contactSelect = document.getElementById('contactSelect');
    const composerType = document.getElementById('composerType');
    const recipientEmail = document.getElementById('recipientEmail').value;
    const recipientName = document.getElementById('recipientName').value;
    const companyName = document.getElementById('companyName').value;
    const position = document.getElementById('position').value;
    
    if (!contactSelect.value) {
        showToast('warningToast', 'Please select a contact first');
        return;
    }
    
    if (!recipientEmail) {
        showToast('warningToast', 'Recipient email is missing');
        return;
    }
    
    // For the new compose form, we don't need currentGlobalAccount validation
    // since this will be handled by the backend
    
    const generateBtn = document.getElementById('generatePreview');
    const originalText = generateBtn.innerHTML;
    
    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Generating...';
    generateBtn.disabled = true;
    
    // Use the currently selected contact that was parsed from JSON
    let selectedContact = currentSelectedContact;
    
    // Prepare contact data for the API
    const contactData = {
        email: recipientEmail,
        name: recipientName,
        company: companyName,
        position: position
    };
    
    // Get tracking preference
    const enableTracking = document.getElementById('enableTracking');
    const includeTracking = enableTracking ? enableTracking.checked : true; // Default to true if element not found
    
    const requestData = {
        contact_data: contactData,
        composer_type: composerType.value || 'deep_research',
        include_tracking: includeTracking
    };
    
    console.log('🎯 Generating email preview with data:', requestData);
    
    fetch('/api/preview_email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.subject && data.body) {
            document.getElementById('emailSubject').value = data.subject || '';
            
            // Check if the body contains HTML and render it properly
            const emailBodyElement = document.getElementById('emailBody');
            if (data.body.includes('<html>') || data.body.includes('<body>')) {
                // If it's HTML, create a preview iframe or render it as HTML
                emailBodyElement.style.display = 'none';
                
                // Create or update HTML preview container
                let htmlPreviewContainer = document.getElementById('htmlPreviewContainer');
                if (!htmlPreviewContainer) {
                    htmlPreviewContainer = document.createElement('div');
                    htmlPreviewContainer.id = 'htmlPreviewContainer';
                    htmlPreviewContainer.className = 'border rounded p-3 bg-light';
                    htmlPreviewContainer.style.minHeight = '300px';
                    emailBodyElement.parentNode.insertBefore(htmlPreviewContainer, emailBodyElement.nextSibling);
                    
                    // Add a label
                    const label = document.createElement('label');
                    label.className = 'form-label';
                    label.textContent = 'Email Preview (Rendered)';
                    htmlPreviewContainer.parentNode.insertBefore(label, htmlPreviewContainer);
                }
                
                // Create iframe to render HTML safely
                htmlPreviewContainer.innerHTML = `
                    <iframe 
                        srcdoc="${data.body.replace(/"/g, '&quot;')}" 
                        style="width: 100%; height: 400px; border: 1px solid #ddd; border-radius: 4px;"
                        frameborder="0">
                    </iframe>
                    <div class="mt-2">
                        <small class="text-muted">
                            <i class="fas fa-info-circle me-1"></i>
                            This is how the email will appear to recipients. 
                            <button type="button" class="btn btn-outline-secondary btn-sm ms-2" onclick="toggleRawHtml()">
                                <i class="fas fa-code me-1"></i>View Raw HTML
                            </button>
                        </small>
                    </div>
                `;
                
                // Store the raw HTML in the textarea for form submission
                emailBodyElement.value = data.body;
            } else {
                // Plain text email
                emailBodyElement.value = data.body;
                emailBodyElement.style.display = 'block';
                
                // Remove HTML preview container if it exists
                const htmlPreviewContainer = document.getElementById('htmlPreviewContainer');
                if (htmlPreviewContainer) {
                    htmlPreviewContainer.remove();
                }
            }
            
            showToast('successToast', 'Email preview generated successfully!');
        } else {
            throw new Error(data.error || 'Failed to generate email preview');
        }
    })
    .catch(error => {
        console.error('Error generating email preview:', error);
        showToast('errorToast', 'Failed to generate email preview: ' + error.message);
    })
    .finally(() => {
        generateBtn.innerHTML = originalText;
        generateBtn.disabled = false;
    });
}

// Toggle between HTML preview and raw HTML view
function toggleRawHtml() {
    const emailBodyElement = document.getElementById('emailBody');
    const htmlPreviewContainer = document.getElementById('htmlPreviewContainer');
    
    if (!emailBodyElement || !htmlPreviewContainer) {
        console.warn('Could not find email body or preview container to toggle');
        return;
    }
    
    if (emailBodyElement.style.display === 'none') {
        // Show raw HTML
        emailBodyElement.style.display = 'block';
        htmlPreviewContainer.style.display = 'none';
    } else {
        // Show rendered preview
        emailBodyElement.style.display = 'none';
        htmlPreviewContainer.style.display = 'block';
    }
}

function sendComposedEmail(e) {
    e.preventDefault();
    
    const recipientEmail = document.getElementById('recipientEmail').value;
    const subject = document.getElementById('emailSubject').value;
    const body = document.getElementById('emailBody').value;
    
    if (!recipientEmail || !subject || !body) {
        showToast('warningToast', 'Please fill in all required fields');
        return;
    }
    
    if (!currentGlobalAccount) {
        showToast('warningToast', 'Please select a sender email account');
        return;
    }
    
    const sendBtn = document.querySelector('#composeForm button[type="submit"]');
    const originalText = sendBtn.innerHTML;
    
    sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Sending...';
    sendBtn.disabled = true;
    
    // Get tracking preference for sending
    const enableTracking = document.getElementById('enableTracking');
    const includeTracking = enableTracking ? enableTracking.checked : true;
    
    fetch('/api/send_email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            recipient_email: recipientEmail,
            sender_email: currentGlobalAccount.email,
            subject: subject,
            body: body,
            include_tracking: includeTracking
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', 'Email sent successfully!');
            
            // Reset form
            document.getElementById('composeForm').reset();
            const emailPreviewSection = document.getElementById('emailPreviewSection');
            if (emailPreviewSection) {
                emailPreviewSection.style.display = 'none';
            }
            
            // Refresh email history
            refreshEmailHistory();
        } else {
            showToast('errorToast', 'Failed to send email: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error sending email:', error);
        showToast('errorToast', 'Failed to send email');
    })
    .finally(() => {
        sendBtn.innerHTML = originalText;
        sendBtn.disabled = false;
    });
}

// Email history management
function setupEmailHistoryPagination() {
    const emailHistoryContainer = document.getElementById('emailHistoryContainer');
    if (emailHistoryContainer && emailHistory.length > 0) {
        paginateEmailHistory(1);
    }
}

function paginateEmailHistory(page = 1) {
    const itemsPerPage = 10;
    const startIndex = (page - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const paginatedEmails = emailHistory.slice(startIndex, endIndex);
    
    const emailHistoryContainer = document.getElementById('emailHistoryContainer');
    if (!emailHistoryContainer) return;
    
    if (paginatedEmails.length === 0) {
        emailHistoryContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Email History</h5>
                <p class="text-muted">No emails have been sent yet.</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="list-group">';
    
    paginatedEmails.forEach(email => {
        const statusIcon = getEmailStatusIcon(email.status);
        const statusClass = getEmailStatusClass(email.status);
        
        html += `
            <div class="list-group-item">
                <div class="d-flex w-100 justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">${email.subject || 'No Subject'}</h6>
                        <p class="mb-1 text-muted">
                            <strong>To:</strong> ${email.recipient} 
                            <strong class="ms-3">From:</strong> ${email.sender}
                        </p>
                        <small class="text-muted">
                            <i class="${statusIcon} me-1"></i>
                            <span class="${statusClass}">${email.status}</span>
                            <span class="ms-3">${new Date(email.timestamp).toLocaleString()}</span>
                        </small>
                    </div>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary" 
                                onclick="showEmailDetails(this)" 
                                data-email='${JSON.stringify(email)}'>
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    // Add pagination
    const totalPages = Math.ceil(emailHistory.length / itemsPerPage);
    if (totalPages > 1) {
        html += generateEmailHistoryPagination(page, totalPages);
    }
    
    emailHistoryContainer.innerHTML = html;
}

function generateEmailHistoryPagination(currentPage, totalPages) {
    let paginationHTML = `
        <nav aria-label="Email history pagination" class="mt-4">
            <ul class="pagination justify-content-center">
    `;
    
    // Previous button
    const prevDisabled = currentPage === 1 ? 'disabled' : '';
    paginationHTML += `
        <li class="page-item ${prevDisabled}">
            <a class="page-link" href="#" onclick="changeEmailHistoryPage(${currentPage - 1})" 
               ${prevDisabled ? 'tabindex="-1" aria-disabled="true"' : ''}>
                <i class="fas fa-chevron-left"></i>
            </a>
        </li>
    `;
    
    // Page numbers
    paginationHTML += generatePageNumbers(currentPage, totalPages, 'email-history-page', 'data-page');
    
    // Next button
    const nextDisabled = currentPage === totalPages ? 'disabled' : '';
    paginationHTML += `
        <li class="page-item ${nextDisabled}">
            <a class="page-link" href="#" onclick="changeEmailHistoryPage(${currentPage + 1})"
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

function changeEmailHistoryPage(page) {
    paginateEmailHistory(page);
}

function refreshEmailHistory() {
    fetch('/api/email/all')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                emailHistory = data.emails || [];
                paginateEmailHistory(1);
            } else {
                console.error('Failed to refresh email history:', data.message);
                throw new Error(data.message || 'API returned success:false');
            }
        })
        .catch(error => {
            console.error('Error refreshing email history:', error);
            const emailHistoryContainer = document.getElementById('emailHistoryContainer');
            if(emailHistoryContainer) {
                emailHistoryContainer.innerHTML = `<div class="alert alert-danger">Error loading email history.</div>`;
            }
        });
}

function applyEmailHistoryFilter(filter) {
    let filteredEmails;
    
    switch(filter) {
        case 'sent':
            filteredEmails = emailHistory.filter(email => email.status === 'sent');
            break;
        case 'delivered':
            filteredEmails = emailHistory.filter(email => email.status === 'delivered');
            break;
        case 'opened':
            filteredEmails = emailHistory.filter(email => email.status === 'opened');
            break;
        case 'failed':
            filteredEmails = emailHistory.filter(email => email.status === 'failed' || email.status === 'bounced');
            break;
        default:
            filteredEmails = emailHistory;
    }
    
    // Temporarily replace emailHistory for pagination
    const originalHistory = emailHistory;
    emailHistory = filteredEmails;
    paginateEmailHistory(1);
    emailHistory = originalHistory;
}

// Inbox management
function loadInboxForAccount(account) {
    const inboxContainer = document.getElementById('inboxContainer');
    if (!inboxContainer) return;
    
    inboxContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading inbox for ${account.email}...</p>
        </div>
    `;
    
    fetch(`/api/email/inbox/${encodeURIComponent(account.email)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayAccountEmails(data.emails || [], account);
            } else {
                throw new Error(data.message || 'Failed to load inbox');
            }
        })
        .catch(error => {
            console.error('Error loading inbox:', error);
            inboxContainer.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                    <h5 class="text-danger">Failed to Load Inbox</h5>
                    <p class="text-muted">${error.message}</p>
                    <button class="btn btn-outline-primary" onclick="loadInboxForAccount(currentGlobalAccount)">
                        <i class="fas fa-refresh me-2"></i>Retry
                    </button>
                </div>
            `;
        });
}

function displayAccountEmails(emails, account) {
    const inboxContainer = document.getElementById('inboxContainer');
    
    if (emails.length === 0) {
        inboxContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">Inbox Empty</h5>
                <p class="text-muted">No emails found in ${account.email}</p>
            </div>
        `;
        return;
    }
    
    let html = `
        <div class="mb-3">
            <h6>Inbox for ${account.email}</h6>
            <small class="text-muted">${emails.length} emails</small>
        </div>
        <div class="list-group">
    `;
    
    emails.forEach((email, index) => {
        const isUnread = !email.read;
        const dateStr = new Date(email.date).toLocaleString();
        
        html += `
            <div class="list-group-item ${isUnread ? 'border-primary' : ''}">
                <div class="d-flex w-100 justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center mb-1">
                            ${isUnread ? '<i class="fas fa-circle text-primary me-2" style="font-size: 0.5rem;"></i>' : ''}
                            <h6 class="mb-0 ${isUnread ? 'fw-bold' : ''}">${email.subject || 'No Subject'}</h6>
                        </div>
                        <p class="mb-1 text-muted">
                            <strong>From:</strong> ${email.from}
                        </p>
                        <small class="text-muted">${dateStr}</small>
                    </div>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary" 
                                onclick="viewEmailDetails(${index}, '${account.email}')" 
                                title="View Email">
                            <i class="fas fa-eye"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    inboxContainer.innerHTML = html;
}

function viewEmailDetails(emailIndex, accountName) {
    console.log(`Viewing email details: ${emailIndex} from ${accountName}`);
    // Implementation for viewing email details would go here
    showToast('infoToast', 'Email details view coming soon!');
}

function showEmailDetails(button) {
    const emailData = JSON.parse(button.getAttribute('data-email'));
    
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Email Details</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="row">
                        <div class="col-12">
                            <h6 class="text-muted mb-3">Email Information</h6>
                            <div class="mb-2">
                                <strong>Subject:</strong> ${emailData.subject || 'No Subject'}
                            </div>
                            <div class="mb-2">
                                <strong>To:</strong> ${emailData.recipient}
                            </div>
                            <div class="mb-2">
                                <strong>From:</strong> ${emailData.sender}
                            </div>
                            <div class="mb-2">
                                <strong>Status:</strong> 
                                <span class="${getEmailStatusClass(emailData.status)}">
                                    <i class="${getEmailStatusIcon(emailData.status)} me-1"></i>
                                    ${emailData.status}
                                </span>
                            </div>
                            <div class="mb-3">
                                <strong>Sent:</strong> ${new Date(emailData.timestamp).toLocaleString()}
                            </div>
                            
                            <h6 class="text-muted mb-3">Email Content</h6>
                            <div class="border rounded p-3 bg-light">
                                <pre style="white-space: pre-wrap; font-family: inherit;">${emailData.body || 'No content available'}</pre>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
    
    modal.addEventListener('hidden.bs.modal', function() {
        document.body.removeChild(modal);
    });
}

// Email connection testing
function testEmailConnection() {
    const modal = document.getElementById('emailConfigModal');
    if (modal) {
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }
}

function showEmailConfigModal(message, helpUrl) {
    const modal = document.getElementById('emailConfigModal');
    if (modal) {
        const modalBody = modal.querySelector('.modal-body');
        modalBody.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                ${message}
            </div>
            <p>Please configure your email settings to send emails.</p>
            ${helpUrl ? `<a href="${helpUrl}" target="_blank" class="btn btn-primary">
                <i class="fas fa-external-link-alt me-2"></i>View Setup Guide
            </a>` : ''}
        `;
        
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeEmail,
        loadGlobalEmailAccounts,
        generateEmailPreview,
        sendComposedEmail,
        refreshEmailHistory,
        testEmailConnection,
        currentGlobalAccount,
        emailHistory
    };
}

// Global function assignments for HTML onclick handlers
// GTM Campaign Integration for Manual Execution
let availableGTMCampaigns = [];
let currentSelectedContact = null;

// Load GTM campaigns for manual execution
function loadGTMCampaigns() {
    fetch('/api/campaigns?execution_mode=manual')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                availableGTMCampaigns = data.campaigns || [];
                updateGTMCampaignDropdown();
                console.log(`Loaded ${availableGTMCampaigns.length} manual GTM campaigns`);
            } else {
                console.warn('Failed to load GTM campaigns:', data.message);
            }
        })
        .catch(error => {
            console.error('Error loading GTM campaigns:', error);
        });
}

// Update the GTM campaign dropdown
function updateGTMCampaignDropdown() {
    const campaignSelect = document.getElementById('gtmCampaignSelect');
    if (!campaignSelect) return;

    campaignSelect.innerHTML = '<option value="">Select GTM Campaign (or send without campaign)</option>';
    
    availableGTMCampaigns.forEach(campaign => {
        const option = document.createElement('option');
        option.value = campaign.id;
        option.textContent = `${campaign.name} (${campaign.type}) - ${campaign.execution_mode}`;
        option.setAttribute('data-campaign', JSON.stringify(campaign));
        campaignSelect.appendChild(option);
    });
}

// Setup campaign validation event listeners
function setupCampaignValidation() {
    const campaignSelect = document.getElementById('gtmCampaignSelect');
    const contactSelect = document.getElementById('contactSelect');
    
    if (campaignSelect) {
        campaignSelect.addEventListener('change', validateCampaignSelection);
    }
    
    if (contactSelect) {
        contactSelect.addEventListener('change', function() {
            const selectedValue = this.value;
            if (selectedValue) {
                try {
                    currentSelectedContact = JSON.parse(selectedValue);
                    validateCampaignSelection();
                } catch (e) {
                    console.error('Error parsing contact data:', e);
                    currentSelectedContact = null;
                    validateCampaignSelection();
                }
            } else {
                currentSelectedContact = null;
                validateCampaignSelection();
            }
        });
    }
    
    // Initial validation
    validateCampaignSelection();
}

// Validate campaign and contact selection
function validateCampaignSelection() {
    const campaignSelect = document.getElementById('gtmCampaignSelect');
    const sendButton = document.getElementById('sendComposedEmail');
    const statusText = document.getElementById('sendButtonStatusText');
    const campaignStatusInfo = document.getElementById('campaignStatusInfo');
    const campaignWarning = document.getElementById('campaignWarning');
    const campaignSuccess = document.getElementById('campaignSuccess');
    const campaignWarningText = document.getElementById('campaignWarningText');
    const campaignSuccessText = document.getElementById('campaignSuccessText');
    
    if (!sendButton || !statusText) return;

    // Reset campaign status display
    if (campaignStatusInfo) campaignStatusInfo.style.display = 'none';
    if (campaignWarning) campaignWarning.style.display = 'none';
    if (campaignSuccess) campaignSuccess.style.display = 'none';
    
    // Check if contact is selected
    if (!currentSelectedContact) {
        sendButton.disabled = true;
        statusText.textContent = 'Select a contact to enable sending';
        return;
    }
    
    const selectedCampaignId = campaignSelect ? campaignSelect.value : '';
    
    // If no campaign selected, allow sending without campaign
    if (!selectedCampaignId) {
        sendButton.disabled = false;
        statusText.textContent = 'Ready to send (without campaign tracking)';
        return;
    }
    
    // Validate campaign selection
    const selectedCampaign = availableGTMCampaigns.find(c => c.id == selectedCampaignId);
    if (!selectedCampaign) {
        sendButton.disabled = true;
        statusText.textContent = 'Invalid campaign selected';
        showCampaignWarning('Selected campaign not found');
        return;
    }
    
    // Check if contact is part of the campaign and email hasn't been sent
    checkContactCampaignStatus(selectedCampaignId, currentSelectedContact.lead_id || currentSelectedContact.id);
}

// Check if contact is in campaign and email status
function checkContactCampaignStatus(campaignId, contactId) {
    const sendButton = document.getElementById('sendComposedEmail');
    const statusText = document.getElementById('sendButtonStatusText');
    
    fetch(`/api/campaigns/${campaignId}/contact/${contactId}/status`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const isInCampaign = data.in_campaign;
                const emailSent = data.email_sent;
                const lastEmailDate = data.last_email_date;
                
                if (!isInCampaign) {
                    sendButton.disabled = true;
                    statusText.textContent = 'Contact is not part of this campaign';
                    showCampaignWarning('This contact is not included in the selected campaign');
                } else if (emailSent) {
                    sendButton.disabled = true;
                    statusText.textContent = `Email already sent on ${lastEmailDate || 'unknown date'}`;
                    showCampaignWarning(`An email has already been sent to this contact for this campaign on ${lastEmailDate || 'unknown date'}`);
                } else {
                    sendButton.disabled = false;
                    statusText.textContent = 'Ready to send via GTM campaign';
                    showCampaignSuccess('Contact is part of this campaign and ready to receive email');
                }
            } else {
                sendButton.disabled = true;
                statusText.textContent = 'Error validating campaign status';
                showCampaignWarning('Unable to verify campaign status');
            }
        })
        .catch(error => {
            console.error('Error checking campaign status:', error);
            sendButton.disabled = true;
            statusText.textContent = 'Error validating campaign status';
            showCampaignWarning('Unable to verify campaign status');
        });
}

// Show campaign warning message
function showCampaignWarning(message) {
    const campaignStatusInfo = document.getElementById('campaignStatusInfo');
    const campaignWarning = document.getElementById('campaignWarning');
    const campaignWarningText = document.getElementById('campaignWarningText');
    
    if (campaignStatusInfo && campaignWarning && campaignWarningText) {
        campaignWarningText.textContent = message;
        campaignStatusInfo.style.display = 'block';
        campaignWarning.style.display = 'block';
    }
}

// Show campaign success message
function showCampaignSuccess(message) {
    const campaignStatusInfo = document.getElementById('campaignStatusInfo');
    const campaignSuccess = document.getElementById('campaignSuccess');
    const campaignSuccessText = document.getElementById('campaignSuccessText');
    
    if (campaignStatusInfo && campaignSuccess && campaignSuccessText) {
        campaignSuccessText.textContent = message;
        campaignStatusInfo.style.display = 'block';
        campaignSuccess.style.display = 'block';
    }
}

window.generateEmailPreview = generateEmailPreview;
window.sendComposedEmail = sendComposedEmail;
window.testGlobalAccountConnection = testGlobalAccountConnection;
window.refreshEmailHistory = refreshEmailHistory;
window.changeEmailHistoryPage = changeEmailHistoryPage;
window.applyEmailHistoryFilter = applyEmailHistoryFilter;
window.viewEmailDetails = viewEmailDetails;
window.showEmailDetails = showEmailDetails;
window.testEmailConnection = testEmailConnection;
window.toggleRawHtml = toggleRawHtml;