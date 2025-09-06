/**
 * Email Templates Management JavaScript
 * Handles configurable email template creation, editing, and management
 */

let currentTemplates = [];
let editingTemplateId = null;

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    loadEmailTemplates();
});

/**
 * Load all email templates for the current tenant
 */
function loadEmailTemplates() {
    const container = document.getElementById('templatesContainer');
    
    container.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading templates...</span>
            </div>
        </div>
    `;
    
    fetch('/api/email-templates')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentTemplates = data.templates;
                displayTemplates(data.templates);
            } else {
                throw new Error(data.error || 'Failed to load templates');
            }
        })
        .catch(error => {
            console.error('Error loading templates:', error);
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Failed to load email templates: ${error.message}
                </div>
            `;
        });
}

/**
 * Display templates in the UI
 */
function displayTemplates(templates) {
    const container = document.getElementById('templatesContainer');
    
    if (templates.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-envelope-open fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No email templates yet</h5>
                <p class="text-muted">Create your first template to get started with configurable cold outreach.</p>
                <button class="btn btn-primary" onclick="createNewTemplate()">
                    <i class="fas fa-plus me-2"></i>Create First Template
                </button>
            </div>
        `;
        return;
    }
    
    let html = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Template Name</th>
                        <th>Framework</th>
                        <th>Tone</th>
                        <th>Length</th>
                        <th>Usage</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    templates.forEach(template => {
        html += `
            <tr class="${template.is_default ? 'table-primary' : ''}">
                <td>
                    <div>
                        <strong>${template.name}</strong>
                        ${template.is_default ? '<span class="badge bg-primary ms-2">Default</span>' : ''}
                        ${template.description ? `<br><small class="text-muted">${template.description}</small>` : ''}
                    </div>
                </td>
                <td>
                    <span class="badge bg-info">${formatFramework(template.message_framework)}</span>
                </td>
                <td>
                    <span class="badge bg-secondary">${formatTone(template.tone_level)}</span>
                </td>
                <td>
                    <span class="badge bg-success">${formatLength(template.email_length)}</span>
                </td>
                <td>
                    <span class="fw-bold">${template.usage_count || 0}</span> emails
                </td>
                <td>
                    <span class="badge ${template.is_active ? 'bg-success' : 'bg-danger'}">
                        ${template.is_active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-primary" onclick="editTemplate(${template.id})" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-info" onclick="viewAnalytics(${template.id})" title="Analytics">
                            <i class="fas fa-chart-bar"></i>
                        </button>
                        <button class="btn btn-outline-success" onclick="duplicateTemplate(${template.id})" title="Duplicate">
                            <i class="fas fa-copy"></i>
                        </button>
                        ${!template.is_default ? `
                            <button class="btn btn-outline-danger" onclick="deleteTemplate(${template.id})" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : ''}
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
    
    container.innerHTML = html;
}

/**
 * Format framework name for display
 */
function formatFramework(framework) {
    if (!framework) return 'N/A';
    const formats = {
        'AIDA': 'AIDA',
        'PAS': 'PAS', 
        'PROBLEM_SOLUTION': 'Problem-Solution',
        'STORYTELLING': 'Storytelling',
        'DIRECT': 'Direct',
        'CONSULTATIVE': 'Consultative'
    };
    return formats[framework] || framework;
}

/**
 * Format tone level for display
 */
function formatTone(tone) {
    if (!tone) return 'N/A';
    const formats = {
        'FORMAL': 'Formal',
        'SEMI_FORMAL': 'Semi-Formal',
        'CASUAL': 'Casual',
        'CONVERSATIONAL': 'Conversational'
    };
    return formats[tone] || tone;
}

/**
 * Format email length for display
 */
function formatLength(length) {
    if (!length) return 'N/A';
    const formats = {
        'SHORT': 'Short',
        'MEDIUM': 'Medium',
        'LONG': 'Long'
    };
    return formats[length] || length;
}

/**
 * Create a new template
 */
function createNewTemplate() {
    editingTemplateId = null;
    document.getElementById('templateModalTitle').textContent = 'Create New Email Template';
    
    // Clear the form
    clearTemplateForm();
    
    // Set some sensible defaults
    document.getElementById('messageFramework').value = 'DIRECT';
    document.getElementById('toneLevel').value = 'SEMI_FORMAL';
    document.getElementById('emailLength').value = 'MEDIUM';
    document.getElementById('ctaType').value = 'MEETING';
    document.getElementById('isActive').checked = true;
    document.getElementById('usePersonalConnection').checked = true;
    document.getElementById('referenceCompanyResearch').checked = true;
    document.getElementById('includeUnsubscribe').checked = true;
    document.getElementById('duration15').checked = true;
    document.getElementById('duration30').checked = true;
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('templateConfigModal'));
    modal.show();
}

/**
 * Edit an existing template
 */
function editTemplate(templateId) {
    const template = currentTemplates.find(t => t.id === templateId);
    if (!template) {
        showToast('errorToast', 'Template not found');
        return;
    }
    
    editingTemplateId = templateId;
    document.getElementById('templateModalTitle').textContent = `Edit Template: ${template.name}`;
    
    // Populate the form with template data
    populateTemplateForm(template);
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('templateConfigModal'));
    modal.show();
}

/**
 * Clear the template configuration form
 */
function clearTemplateForm() {
    document.getElementById('templateForm').reset();
    document.getElementById('templateId').value = '';
    
    // Clear checkboxes
    document.querySelectorAll('.meeting-duration').forEach(cb => cb.checked = false);
}

/**
 * Populate form with template data
 */
function populateTemplateForm(template) {
    document.getElementById('templateId').value = template.id || '';
    document.getElementById('templateName').value = template.name || '';
    document.getElementById('templateDescription').value = template.description || '';
    document.getElementById('isActive').checked = template.is_active ?? true;
    document.getElementById('isDefault').checked = template.is_default ?? false;
    
    // Message structure
    document.getElementById('messageFramework').value = template.message_framework || 'DIRECT';
    document.getElementById('toneLevel').value = template.tone_level || 'SEMI_FORMAL';
    document.getElementById('emailLength').value = template.email_length || 'MEDIUM';
    
    // Subject lines
    document.getElementById('subjectTemplates').value = (template.subject_templates || []).join('\n');
    document.getElementById('subjectAbTest').checked = template.subject_ab_test ?? false;
    
    // Opening
    document.getElementById('openingStyle').value = template.opening_style || 'personal';
    document.getElementById('usePersonalConnection').checked = template.use_personal_connection ?? true;
    document.getElementById('referenceCompanyResearch').checked = template.reference_company_research ?? true;
    document.getElementById('openingTemplates').value = (template.opening_templates || []).join('\n');
    
    // Product details
    const productDetails = template.product_details || {};
    document.getElementById('productName').value = productDetails.name || '';
    document.getElementById('productDescription').value = productDetails.description || '';
    
    // Value propositions and social proof
    document.getElementById('valuePropositions').value = (template.value_propositions || []).join('\n');
    document.getElementById('socialProofElements').value = (template.social_proof_elements || []).join('\n');
    
    // CTA
    document.getElementById('ctaType').value = template.cta_type || 'MEETING';
    document.getElementById('ctaTemplates').value = (template.cta_templates || []).join('\n');
    document.getElementById('calendarBookingUrl').value = template.calendar_booking_url || '';
    
    // Meeting durations
    const durations = template.meeting_duration_options || [15, 30];
    document.querySelectorAll('.meeting-duration').forEach(cb => {
        cb.checked = durations.includes(parseInt(cb.value));
    });
    
    // Sender info
    document.getElementById('senderName').value = template.sender_name || '';
    document.getElementById('senderTitle').value = template.sender_title || '';
    document.getElementById('senderCompany').value = template.sender_company || '';
    document.getElementById('signatureTemplate').value = template.signature_template || '';
    
    // Compliance
    document.getElementById('includeUnsubscribe').checked = template.include_unsubscribe ?? true;
    document.getElementById('gdprComplianceText').value = template.gdpr_compliance_text || '';
    
    // A/B Testing
    document.getElementById('enableAbTesting').checked = template.enable_ab_testing ?? false;
}

/**
 * Save the template
 */
function saveTemplate() {
    const formData = collectFormData();
    
    // Validate required fields
    if (!formData.name) {
        showToast('warningToast', 'Template name is required');
        return;
    }
    
    const method = editingTemplateId ? 'PUT' : 'POST';
    const url = editingTemplateId ? `/api/email-templates/${editingTemplateId}` : '/api/email-templates';
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', editingTemplateId ? 'Template updated successfully' : 'Template created successfully');
            const modal = bootstrap.Modal.getInstance(document.getElementById('templateConfigModal'));
            modal.hide();
            loadEmailTemplates();
        } else {
            throw new Error(data.error || 'Failed to save template');
        }
    })
    .catch(error => {
        console.error('Error saving template:', error);
        showToast('errorToast', 'Failed to save template: ' + error.message);
    });
}

/**
 * Collect form data into an object
 */
function collectFormData() {
    // Get meeting duration options
    const meetingDurations = [];
    document.querySelectorAll('.meeting-duration:checked').forEach(cb => {
        meetingDurations.push(parseInt(cb.value));
    });
    
    // Split textarea values into arrays
    const subjectTemplates = document.getElementById('subjectTemplates').value.split('\n').filter(line => line.trim());
    const openingTemplates = document.getElementById('openingTemplates').value.split('\n').filter(line => line.trim());
    const valuePropositions = document.getElementById('valuePropositions').value.split('\n').filter(line => line.trim());
    const socialProofElements = document.getElementById('socialProofElements').value.split('\n').filter(line => line.trim());
    const ctaTemplates = document.getElementById('ctaTemplates').value.split('\n').filter(line => line.trim());
    
    return {
        name: document.getElementById('templateName').value,
        description: document.getElementById('templateDescription').value,
        is_active: document.getElementById('isActive').checked,
        is_default: document.getElementById('isDefault').checked,
        
        message_framework: document.getElementById('messageFramework').value,
        tone_level: document.getElementById('toneLevel').value,
        email_length: document.getElementById('emailLength').value,
        
        subject_templates: subjectTemplates,
        subject_ab_test: document.getElementById('subjectAbTest').checked,
        
        opening_style: document.getElementById('openingStyle').value,
        opening_templates: openingTemplates,
        use_personal_connection: document.getElementById('usePersonalConnection').checked,
        reference_company_research: document.getElementById('referenceCompanyResearch').checked,
        
        value_propositions: valuePropositions,
        social_proof_elements: socialProofElements,
        product_details: {
            name: document.getElementById('productName').value,
            description: document.getElementById('productDescription').value
        },
        
        cta_type: document.getElementById('ctaType').value,
        cta_templates: ctaTemplates,
        meeting_duration_options: meetingDurations,
        calendar_booking_url: document.getElementById('calendarBookingUrl').value,
        
        sender_name: document.getElementById('senderName').value,
        sender_title: document.getElementById('senderTitle').value,
        sender_company: document.getElementById('senderCompany').value,
        signature_template: document.getElementById('signatureTemplate').value,
        
        include_unsubscribe: document.getElementById('includeUnsubscribe').checked,
        gdpr_compliance_text: document.getElementById('gdprComplianceText').value,
        
        enable_ab_testing: document.getElementById('enableAbTesting').checked
    };
}

/**
 * Test the template with a sample contact
 */
function testTemplate() {
    const modal = new bootstrap.Modal(document.getElementById('testEmailModal'));
    modal.show();
}

/**
 * Generate a test email using the current template configuration
 */
function generateTestEmail() {
    const contactEmail = document.getElementById('testContactEmail').value;
    const tenantId = document.getElementById('testTenantId').value;
    
    if (!contactEmail) {
        showToast('warningToast', 'Please enter a test contact email');
        return;
    }
    
    const resultDiv = document.getElementById('testEmailResult');
    resultDiv.style.display = 'none';
    
    // Create a temporary template with current form data
    const templateData = collectFormData();
    
    // Make API call to generate test email
    const requestData = {
        contact_email: contactEmail,
        demo_config: tenantId ? { tenant_id: tenantId, campaign: 'test' } : {}
    };
    
    if (editingTemplateId) {
        requestData.template_id = editingTemplateId;
    }
    
    fetch('/api/compose/email/configurable', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('testSubject').textContent = data.subject;
            document.getElementById('testBody').textContent = data.body;
            resultDiv.style.display = 'block';
        } else {
            throw new Error(data.error || 'Failed to generate test email');
        }
    })
    .catch(error => {
        console.error('Error generating test email:', error);
        showToast('errorToast', 'Failed to generate test email: ' + error.message);
    });
}

/**
 * View analytics for a template
 */
function viewAnalytics(templateId) {
    fetch(`/api/email-templates/${templateId}/analytics`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const analytics = data.analytics;
                const modal = document.createElement('div');
                modal.className = 'modal fade';
                modal.innerHTML = `
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Template Analytics: ${analytics.template_name}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row text-center">
                                    <div class="col-6 col-md-3">
                                        <div class="card border-primary">
                                            <div class="card-body">
                                                <h3 class="text-primary">${analytics.total_sent}</h3>
                                                <p class="mb-0">Total Sent</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-6 col-md-3">
                                        <div class="card border-success">
                                            <div class="card-body">
                                                <h3 class="text-success">${analytics.open_rate.toFixed(1)}%</h3>
                                                <p class="mb-0">Open Rate</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-6 col-md-3">
                                        <div class="card border-info">
                                            <div class="card-body">
                                                <h3 class="text-info">${analytics.click_rate.toFixed(1)}%</h3>
                                                <p class="mb-0">Click Rate</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-6 col-md-3">
                                        <div class="card border-warning">
                                            <div class="card-body">
                                                <h3 class="text-warning">${analytics.reply_rate.toFixed(1)}%</h3>
                                                <p class="mb-0">Reply Rate</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);
                const bsModal = new bootstrap.Modal(modal);
                bsModal.show();
                
                // Remove modal from DOM when hidden
                modal.addEventListener('hidden.bs.modal', () => {
                    document.body.removeChild(modal);
                });
            } else {
                throw new Error(data.error || 'Failed to load analytics');
            }
        })
        .catch(error => {
            console.error('Error loading analytics:', error);
            showToast('errorToast', 'Failed to load analytics: ' + error.message);
        });
}

/**
 * Duplicate a template
 */
function duplicateTemplate(templateId) {
    const template = currentTemplates.find(t => t.id === templateId);
    if (!template) {
        showToast('errorToast', 'Template not found');
        return;
    }
    
    editingTemplateId = null;
    document.getElementById('templateModalTitle').textContent = `Duplicate Template: ${template.name}`;
    
    populateTemplateForm(template);
    
    // Modify name and unset default
    document.getElementById('templateName').value = template.name + ' (Copy)';
    document.getElementById('isDefault').checked = false;
    
    const modal = new bootstrap.Modal(document.getElementById('templateConfigModal'));
    modal.show();
}

/**
 * Delete a template
 */
function deleteTemplate(templateId) {
    const template = currentTemplates.find(t => t.id === templateId);
    if (!template) {
        showToast('errorToast', 'Template not found');
        return;
    }
    
    if (template.is_default) {
        showToast('warningToast', 'Cannot delete the default template');
        return;
    }
    
    if (confirm(`Are you sure you want to delete the template "${template.name}"? This action cannot be undone.`)) {
        fetch(`/api/email-templates/${templateId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('successToast', 'Template deleted successfully');
                loadEmailTemplates();
            } else {
                throw new Error(data.error || 'Failed to delete template');
            }
        })
        .catch(error => {
            console.error('Error deleting template:', error);
            showToast('errorToast', 'Failed to delete template: ' + error.message);
        });
    }
}

/**
 * Show toast notification
 */
function showToast(type, message) {
    // Create toast element dynamically if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    const toastId = `toast-${Date.now()}`;
    const toastClass = type === 'successToast' ? 'text-bg-success' : 
                      type === 'warningToast' ? 'text-bg-warning' : 'text-bg-danger';
    
    const toast = document.createElement('div');
    toast.className = `toast ${toastClass}`;
    toast.id = toastId;
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast from DOM after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toastContainer.removeChild(toast);
    });
}