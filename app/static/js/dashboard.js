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
    
    // Create detailed contact view
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
            </div>
        </div>
    `;
    
    modalContent.innerHTML = detailsHtml;
    
    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
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