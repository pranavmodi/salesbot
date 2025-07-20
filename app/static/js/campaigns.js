// SalesBot CRM - Campaign Management Module

// Global campaign-related variables
let currentCampaignData = {};
let selectedCampaignContacts = [];

// Initialize campaign functionality
function initializeCampaigns() {
    setupCampaignEventListeners();
    initializeCampaignModal();
    setupCampaignTabListener();
}

function setupCampaignTabListener() {
    const gtmCampaignTab = document.getElementById('gtm-campaign-tab');
    if (gtmCampaignTab) {
        gtmCampaignTab.addEventListener('shown.bs.tab', function (e) {
            console.log('GTM Campaign tab shown, loading campaigns...');
            loadCampaigns();
        });
        
        if (gtmCampaignTab.classList.contains('active')) {
            console.log('GTM Campaign tab is already active, loading campaigns...');
            loadCampaigns();
        }
    }
}

// Campaign event listeners
function setupCampaignEventListeners() {
    const createCampaignBtn = document.getElementById('createCampaignBtn');
    const deleteAllCampaignsBtn = document.getElementById('deleteAllCampaigns');
    
    if (createCampaignBtn) {
        createCampaignBtn.addEventListener('click', createCampaign);
    }
    if (deleteAllCampaignsBtn) {
        deleteAllCampaignsBtn.addEventListener('click', deleteAllCampaigns);
    }
}

// Campaign modal management
function initializeCampaignModal() {
    const modal = document.getElementById('campaignModal');
    if (modal) {
        modal.addEventListener('show.bs.modal', resetCampaignModal);
        setupStepValidation();
        handleSelectionMethodChange();
    }
}

function resetCampaignModal() {
    // Reset all form inputs
    const form = document.getElementById('campaignForm');
    if (form) {
        form.reset();
    }
    
    // Reset step indicators
    showStep(1);
    
    // Clear any existing data
    currentCampaignData = {};
    selectedCampaignContacts = [];
    
    // Reset contact selection
    updateSelectedContactsBadge(0);
    
    // Clear any error messages
    const errorElements = document.querySelectorAll('.text-danger');
    errorElements.forEach(el => el.textContent = '');
    
    console.log('Campaign modal reset');
}

function showStep(stepNumber) {
    // Hide all steps
    const steps = document.querySelectorAll('.campaign-step');
    steps.forEach(step => step.style.display = 'none');
    
    // Show current step
    const currentStep = document.getElementById(`step${stepNumber}`);
    if (currentStep) {
        currentStep.style.display = 'block';
    }
    
    // Update step indicators
    updateStepIndicators(stepNumber);
    
    // Update navigation buttons
    updateNavigationButtons(stepNumber);
    
    // Load data for specific steps
    if (stepNumber === 2) {
        loadCompaniesForCampaign();
    } else if (stepNumber === 3) {
        handleSelectionMethodChange();
    } else if (stepNumber === 4) {
        populateReviewStep();
    }
}

function updateStepIndicators(currentStep = 1) {
    const indicators = document.querySelectorAll('.step-indicator');
    indicators.forEach((indicator, index) => {
        const stepNum = index + 1;
        indicator.classList.remove('active', 'completed');
        
        if (stepNum < currentStep) {
            indicator.classList.add('completed');
        } else if (stepNum === currentStep) {
            indicator.classList.add('active');
        }
    });
}

function updateNavigationButtons(stepNumber) {
    const prevBtn = document.getElementById('prevStepBtn');
    const nextBtn = document.getElementById('nextStepBtn');
    const createBtn = document.getElementById('createCampaignFinalBtn');
    
    // Previous button
    if (prevBtn) {
        prevBtn.style.display = stepNumber === 1 ? 'none' : 'inline-block';
    }
    
    // Next/Create buttons
    if (nextBtn && createBtn) {
        if (stepNumber === 4) {
            nextBtn.style.display = 'none';
            createBtn.style.display = 'inline-block';
        } else {
            nextBtn.style.display = 'inline-block';
            createBtn.style.display = 'none';
        }
    }
}

function nextStep() {
    const currentStep = document.querySelector('.campaign-step[style*="block"]');
    if (!currentStep) return;
    
    const stepNumber = parseInt(currentStep.id.replace('step', ''));
    
    if (validateCurrentStep(stepNumber)) {
        saveCurrentStepData(stepNumber);
        showStep(stepNumber + 1);
    }
}

function previousStep() {
    const currentStep = document.querySelector('.campaign-step[style*="block"]');
    if (!currentStep) return;
    
    const stepNumber = parseInt(currentStep.id.replace('step', ''));
    if (stepNumber > 1) {
        showStep(stepNumber - 1);
    }
}

function validateCurrentStep(stepNumber) {
    switch(stepNumber) {
        case 1: return validateStep1();
        case 2: return validateStep2();
        case 3: return validateStep3();
        case 4: return validateStep4();
        default: return true;
    }
}

function validateStep1() {
    const name = document.getElementById('campaignName').value.trim();
    return name.length > 0;
}

function validateStep2() {
    // Target criteria validation - at least one filter should be applied
    return true; // For now, allow any configuration
}

function validateStep3() {
    const selectionMethod = document.querySelector('input[name="selectionMethod"]:checked');
    if (!selectionMethod) return false;
    
    if (selectionMethod.value === 'manual') {
        return selectedCampaignContacts.length > 0;
    }
    return true;
}

function validateStep4() {
    return true; // Review step, no additional validation needed
}

function saveCurrentStepData(stepNumber) {
    switch(stepNumber) {
        case 1:
            currentCampaignData.name = document.getElementById('campaignName').value.trim();
            currentCampaignData.description = document.getElementById('campaignDescription').value.trim();
            currentCampaignData.priority = document.getElementById('campaignPriority').value;
            currentCampaignData.email_template = document.getElementById('campaignEmailTemplate').value;
            break;
        case 2:
            currentCampaignData.target_criteria = getFilterCriteria();
            break;
        case 3:
            const selectionMethod = document.querySelector('input[name="selectionMethod"]:checked');
            currentCampaignData.selection_method = selectionMethod ? selectionMethod.value : 'auto';
            if (currentCampaignData.selection_method === 'manual') {
                currentCampaignData.selected_contacts = selectedCampaignContacts;
            }
            break;
    }
    
    console.log('Saved step data:', currentCampaignData);
}

function populateReviewStep() {
    const reviewContent = document.getElementById('reviewContent');
    if (!reviewContent) return;
    
    let html = `
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-muted mb-3">Campaign Details</h6>
                <div class="mb-2">
                    <strong>Name:</strong> ${currentCampaignData.name || 'Not specified'}
                </div>
                <div class="mb-2">
                    <strong>Description:</strong> ${currentCampaignData.description || 'None'}
                </div>
                <div class="mb-2">
                    <strong>Priority:</strong> ${getPriorityBadge(currentCampaignData.priority || 'medium')}
                </div>
                <div class="mb-2">
                    <strong>Email Template:</strong> ${getEmailTemplateDisplayName(currentCampaignData.email_template || 'cold_outreach')}
                </div>
            </div>
            <div class="col-md-6">
                <h6 class="text-muted mb-3">Target & Selection</h6>
                <div class="mb-2">
                    <strong>Selection Method:</strong> 
                    ${currentCampaignData.selection_method === 'manual' ? 'Manual Selection' : 'Automatic Filtering'}
                </div>
    `;
    
    if (currentCampaignData.selection_method === 'manual') {
        html += `
                <div class="mb-2">
                    <strong>Selected Contacts:</strong> ${selectedCampaignContacts.length}
                </div>
        `;
    } else {
        const criteria = currentCampaignData.target_criteria || {};
        html += `
                <div class="mb-2">
                    <strong>Company Filter:</strong> ${criteria.company || 'All companies'}
                </div>
                <div class="mb-2">
                    <strong>Location Filter:</strong> ${criteria.location || 'All locations'}
                </div>
        `;
    }
    
    html += `
            </div>
        </div>
    `;
    
    reviewContent.innerHTML = html;
}

function setupStepValidation() {
    // Add real-time validation for form fields
    const campaignName = document.getElementById('campaignName');
    if (campaignName) {
        campaignName.addEventListener('input', function() {
            const nextBtn = document.getElementById('nextStepBtn');
            if (nextBtn) {
                nextBtn.disabled = this.value.trim().length === 0;
            }
        });
    }
}

// Contact selection for campaigns
function handleSelectionMethodChange() {
    const selectionMethod = document.querySelector('input[name="selectionMethod"]:checked');
    const manualSelectionDiv = document.getElementById('manualSelectionDiv');
    const autoSelectionDiv = document.getElementById('autoSelectionDiv');
    
    if (!selectionMethod) return;
    
    if (selectionMethod.value === 'manual') {
        if (manualSelectionDiv) manualSelectionDiv.style.display = 'block';
        if (autoSelectionDiv) autoSelectionDiv.style.display = 'none';
        loadContactsForManualSelection();
    } else {
        if (manualSelectionDiv) manualSelectionDiv.style.display = 'none';
        if (autoSelectionDiv) autoSelectionDiv.style.display = 'block';
        updateContactCount();
    }
}

function loadCompaniesForCampaign() {
    fetch('/api/companies')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateCompanyFilter(data.companies || []);
            }
        })
        .catch(error => {
            console.error('Error loading companies for campaign:', error);
        });
}

function populateCompanyFilter(companies) {
    const companySelect = document.getElementById('targetCompany');
    if (companySelect) {
        companySelect.innerHTML = '<option value="">All Companies</option>';
        companies.forEach(company => {
            const option = document.createElement('option');
            option.value = company.name;
            option.textContent = company.name;
            companySelect.appendChild(option);
        });
    }
}

function updateContactCount() {
    const criteria = getFilterCriteria();
    const countElement = document.getElementById('estimatedContactCount');
    
    if (!countElement) return;
    
    countElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Calculating...';
    
    fetch('/api/contacts/count', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(criteria)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            countElement.innerHTML = `<strong>${data.count}</strong> contacts match your criteria`;
        } else {
            countElement.innerHTML = 'Unable to calculate count';
        }
    })
    .catch(error => {
        console.error('Error getting contact count:', error);
        countElement.innerHTML = 'Unable to calculate count';
    });
}

function getFilterCriteria() {
    return {
        company: document.getElementById('targetCompany')?.value || '',
        location: document.getElementById('targetLocation')?.value || '',
        job_title: document.getElementById('targetJobTitle')?.value || ''
    };
}

function updateSelectedContactsBadge(count = null) {
    const badge = document.getElementById('selectedContactsBadge');
    if (badge) {
        const displayCount = count !== null ? count : selectedCampaignContacts.length;
        badge.textContent = displayCount;
        badge.style.display = displayCount > 0 ? 'inline' : 'none';
    }
}

function loadContactsForManualSelection() {
    const container = document.getElementById('manualContactSelection');
    if (!container) return;
    
    container.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading contacts...</p>
        </div>
    `;
    
    fetch('/api/contacts?limit=100')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayContactsForSelection(data.contacts || []);
            } else {
                throw new Error(data.message || 'Failed to load contacts');
            }
        })
        .catch(error => {
            console.error('Error loading contacts for selection:', error);
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Failed to load contacts: ${error.message}
                </div>
            `;
        });
}

function searchContactsForCampaign() {
    const searchInput = document.getElementById('campaignContactSearch');
    if (!searchInput) return;
    
    const searchTerm = searchInput.value.trim();
    if (searchTerm.length < 2) {
        loadContactsForManualSelection();
        return;
    }
    
    fetch(`/api/contacts/search?q=${encodeURIComponent(searchTerm)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayContactsForSelection(data.contacts || []);
            }
        })
        .catch(error => {
            console.error('Error searching contacts for campaign:', error);
        });
}

function displayContactsForSelection(contacts) {
    const container = document.getElementById('manualContactSelection');
    if (!container) return;
    
    if (contacts.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-users fa-2x text-muted mb-3"></i>
                <p class="text-muted">No contacts found</p>
            </div>
        `;
        return;
    }
    
    let html = `
        <div class="mb-3">
            <input type="text" class="form-control" id="campaignContactSearch" 
                   placeholder="Search contacts..." onkeyup="searchContactsForCampaign()">
        </div>
        <div class="contact-selection-list" style="max-height: 300px; overflow-y: auto;">
    `;
    
    contacts.forEach(contact => {
        const displayName = contact.display_name || contact.full_name || 
                           `${contact.first_name || ''} ${contact.last_name || ''}`.trim() || 'Unknown';
        const isSelected = selectedCampaignContacts.some(c => c.email === contact.email);
        
        html += `
            <div class="form-check contact-selection-item p-2 border-bottom">
                <input class="form-check-input" type="checkbox" 
                       value="${contact.email}" 
                       id="contact_${contact.email.replace('@', '_')}"
                       ${isSelected ? 'checked' : ''}
                       onchange="toggleContactSelection('${contact.email}', this.checked)"
                       data-contact='${JSON.stringify(contact)}'>
                <label class="form-check-label w-100" for="contact_${contact.email.replace('@', '_')}">
                    <div class="d-flex align-items-center">
                        <div class="contact-avatar me-2" style="width: 32px; height: 32px; font-size: 0.75rem;">
                            ${contact.first_name ? contact.first_name[0].toUpperCase() : '?'}
                        </div>
                        <div class="flex-grow-1">
                            <div class="fw-semibold">${displayName}</div>
                            <small class="text-muted">
                                ${contact.company || 'No company'} • ${contact.email}
                            </small>
                        </div>
                    </div>
                </label>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function toggleContactSelection(email, isSelected) {
    const checkbox = document.querySelector(`input[value="${email}"]`);
    if (!checkbox) return;
    
    const contactData = JSON.parse(checkbox.getAttribute('data-contact'));
    
    if (isSelected) {
        // Add to selected contacts if not already present
        if (!selectedCampaignContacts.some(c => c.email === email)) {
            selectedCampaignContacts.push(contactData);
        }
    } else {
        // Remove from selected contacts
        selectedCampaignContacts = selectedCampaignContacts.filter(c => c.email !== email);
    }
    
    updateSelectedContactsBadge();
    updateSelectedContactsPreview();
    
    console.log(`Contact ${email} ${isSelected ? 'selected' : 'deselected'}. Total: ${selectedCampaignContacts.length}`);
}

function updateSelectedContactsPreview() {
    const preview = document.getElementById('selectedContactsPreview');
    if (!preview) return;
    
    if (selectedCampaignContacts.length === 0) {
        preview.innerHTML = '<p class="text-muted">No contacts selected yet</p>';
        return;
    }
    
    let html = '<div class="selected-contacts-list">';
    selectedCampaignContacts.slice(0, 5).forEach(contact => {
        const displayName = contact.display_name || contact.full_name || 
                           `${contact.first_name || ''} ${contact.last_name || ''}`.trim() || 'Unknown';
        html += `
            <div class="d-flex align-items-center justify-content-between mb-2 p-2 bg-light rounded">
                <div class="d-flex align-items-center">
                    <div class="contact-avatar me-2" style="width: 24px; height: 24px; font-size: 0.65rem;">
                        ${contact.first_name ? contact.first_name[0].toUpperCase() : '?'}
                    </div>
                    <div>
                        <small class="fw-semibold">${displayName}</small>
                        <br>
                        <small class="text-muted">${contact.email}</small>
                    </div>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger" 
                        onclick="toggleContactSelection('${contact.email}', false)">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
    });
    
    if (selectedCampaignContacts.length > 5) {
        html += `<small class="text-muted">... and ${selectedCampaignContacts.length - 5} more contacts</small>`;
    }
    
    html += '</div>';
    preview.innerHTML = html;
}

function clearCampaignSearch() {
    const searchInput = document.getElementById('campaignContactSearch');
    if (searchInput) {
        searchInput.value = '';
        loadContactsForManualSelection();
    }
}

// Campaign CRUD operations
function createCampaign() {
    if (!validateAllSteps()) {
        showToast('warningToast', 'Please complete all required fields');
        return;
    }
    
    // Save current step data
    saveCurrentStepData(4);
    
    const createBtn = document.getElementById('createCampaignFinalBtn');
    const originalText = createBtn.innerHTML;
    
    createBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Creating...';
    createBtn.disabled = true;
    
    fetch('/api/campaigns', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(currentCampaignData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', 'Campaign created successfully!');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('campaignModal'));
            if (modal) {
                modal.hide();
            }
            
            // Reload campaigns
            loadCampaigns();
        } else {
            throw new Error(data.message || 'Failed to create campaign');
        }
    })
    .catch(error => {
        console.error('Error creating campaign:', error);
        showToast('errorToast', 'Failed to create campaign: ' + error.message);
    })
    .finally(() => {
        createBtn.innerHTML = originalText;
        createBtn.disabled = false;
    });
}

function validateAllSteps() {
    return validateStep1() && validateStep2() && validateStep3() && validateStep4();
}

function saveCampaignDraft() {
    // Save current step data
    const currentStep = document.querySelector('.campaign-step[style*="block"]');
    if (currentStep) {
        const stepNumber = parseInt(currentStep.id.replace('step', ''));
        saveCurrentStepData(stepNumber);
    }
    
    const draftData = {
        ...currentCampaignData,
        status: 'draft'
    };
    
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
            showToast('successToast', 'Campaign draft saved!');
        } else {
            throw new Error(data.message || 'Failed to save draft');
        }
    })
    .catch(error => {
        console.error('Error saving campaign draft:', error);
        showToast('errorToast', 'Failed to save draft: ' + error.message);
    });
}

// Campaign loading and display
function loadCampaigns() {
    const campaignsContainer = document.getElementById('campaignsContainer');
    if (!campaignsContainer) return;
    
    campaignsContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading campaigns...</p>
        </div>
    `;
    
    fetch('/api/campaigns')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayCampaigns(data.campaigns || []);
                updateCampaignStats(data.campaigns || []);
            } else {
                throw new Error(data.message || 'Failed to load campaigns');
            }
        })
        .catch(error => {
            console.error('Error loading campaigns:', error);
            campaignsContainer.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                    <h5 class="text-danger">Failed to Load Campaigns</h5>
                    <p class="text-muted">${error.message}</p>
                    <button class="btn btn-outline-primary" onclick="loadCampaigns()">
                        <i class="fas fa-refresh me-2"></i>Retry
                    </button>
                </div>
            `;
        });
}

function displayCampaigns(campaigns) {
    const campaignsContainer = document.getElementById('campaignsContainer');
    
    if (campaigns.length === 0) {
        campaignsContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-bullhorn fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Campaigns Yet</h5>
                <p class="text-muted">Create your first campaign to start reaching out to contacts.</p>
                <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#campaignModal">
                    <i class="fas fa-plus me-2"></i>Create Campaign
                </button>
            </div>
        `;
        return;
    }
    
    // Separate campaigns by status
    const activeCampaigns = campaigns.filter(c => c.status === 'active');
    const pausedCampaigns = campaigns.filter(c => c.status === 'paused');
    const completedCampaigns = campaigns.filter(c => c.status === 'completed');
    const draftCampaigns = campaigns.filter(c => c.status === 'draft');
    
    let html = '';
    
    if (activeCampaigns.length > 0) {
        html += '<h6 class="text-success mb-3"><i class="fas fa-play-circle me-2"></i>Active Campaigns</h6>';
        html += displayCampaignList(activeCampaigns, 'activeCampaigns', 'active');
    }
    
    if (pausedCampaigns.length > 0) {
        html += '<h6 class="text-warning mb-3 mt-4"><i class="fas fa-pause-circle me-2"></i>Paused Campaigns</h6>';
        html += displayCampaignList(pausedCampaigns, 'pausedCampaigns', 'paused');
    }
    
    if (draftCampaigns.length > 0) {
        html += '<h6 class="text-secondary mb-3 mt-4"><i class="fas fa-edit me-2"></i>Draft Campaigns</h6>';
        html += displayCampaignList(draftCampaigns, 'draftCampaigns', 'draft');
    }
    
    if (completedCampaigns.length > 0) {
        html += '<h6 class="text-primary mb-3 mt-4"><i class="fas fa-check-circle me-2"></i>Completed Campaigns</h6>';
        html += displayCampaignList(completedCampaigns, 'completedCampaigns', 'completed');
    }
    
    campaignsContainer.innerHTML = html;
}

function displayCampaignList(campaigns, containerId, type) {
    let html = `<div id="${containerId}" class="row">`;
    
    campaigns.forEach(campaign => {
        const statusBadge = getStatusBadge(campaign.status);
        const priorityBadge = getPriorityBadge(campaign.priority);
        
        html += `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h6 class="card-title mb-0">${campaign.name}</h6>
                            <div class="btn-group btn-group-sm" role="group">
                                <button type="button" class="btn btn-outline-primary" 
                                        onclick="viewCampaignDetails(${campaign.id})" 
                                        title="View Details">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </div>
                        </div>
                        
                        <div class="mb-2">
                            ${statusBadge}
                            ${priorityBadge}
                        </div>
                        
                        <p class="card-text text-muted small mb-3">
                            ${campaign.description || 'No description provided'}
                        </p>
                        
                        <div class="mb-2">
                            <small class="text-muted">
                                <i class="fas fa-users me-1"></i>
                                ${campaign.target_count || 0} contacts
                            </small>
                        </div>
                        
                        <div class="mb-2">
                            <small class="text-muted">
                                <i class="fas fa-envelope me-1"></i>
                                ${campaign.emails_sent || 0} emails sent
                            </small>
                        </div>
                        
                        <div class="progress mb-2" style="height: 5px;">
                            <div class="progress-bar" 
                                 style="width: ${campaign.progress || 0}%"
                                 aria-valuenow="${campaign.progress || 0}" 
                                 aria-valuemin="0" 
                                 aria-valuemax="100">
                            </div>
                        </div>
                        
                        <small class="text-muted">
                            <i class="fas fa-calendar me-1"></i>
                            Created ${new Date(campaign.created_at).toLocaleDateString()}
                        </small>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    return html;
}

function updateCampaignStats(campaigns) {
    const totalCampaigns = campaigns.length;
    const activeCampaigns = campaigns.filter(c => c.status === 'active').length;
    const totalEmails = campaigns.reduce((sum, c) => sum + (c.emails_sent || 0), 0);
    
    // Update stats in UI
    const totalCampaignsElement = document.getElementById('totalCampaigns');
    const activeCampaignsElement = document.getElementById('activeCampaigns');
    const totalEmailsElement = document.getElementById('totalEmails');
    
    if (totalCampaignsElement) totalCampaignsElement.textContent = totalCampaigns;
    if (activeCampaignsElement) activeCampaignsElement.textContent = activeCampaigns;
    if (totalEmailsElement) totalEmailsElement.textContent = totalEmails;
}

// Campaign management operations
function viewCampaignDetails(campaignId) {
    console.log(`Viewing campaign details for ID: ${campaignId}`);
    
    // Set campaign ID for details modal
    setCampaignDetailsId(campaignId);
    
    // Show the details modal
    const detailsModal = document.getElementById('campaignDetailsModal');
    if (detailsModal) {
        const modal = new bootstrap.Modal(detailsModal);
        modal.show();
        
        // Load campaign data
        loadCampaignActivity(campaignId);
    }
}

function setCampaignDetailsId(campaignId) {
    const modalElement = document.getElementById('campaignDetailsModal');
    if (modalElement) {
        modalElement.setAttribute('data-campaign-id', campaignId);
    }
}

function deleteAllCampaigns() {
    if (!confirm('Are you sure you want to delete ALL campaigns? This action cannot be undone.')) {
        return;
    }
    
    const deleteBtn = document.getElementById('deleteAllCampaigns');
    const originalText = deleteBtn.innerHTML;
    
    deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Deleting...';
    deleteBtn.disabled = true;
    
    fetch('/api/campaigns/delete-all', {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', 'All campaigns deleted successfully!');
            loadCampaigns();
        } else {
            throw new Error(data.message || 'Failed to delete campaigns');
        }
    })
    .catch(error => {
        console.error('Error deleting campaigns:', error);
        showToast('errorToast', 'Failed to delete campaigns: ' + error.message);
    })
    .finally(() => {
        deleteBtn.innerHTML = originalText;
        deleteBtn.disabled = false;
    });
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeCampaigns,
        loadCampaigns,
        createCampaign,
        viewCampaignDetails,
        deleteAllCampaigns,
        currentCampaignData,
        selectedCampaignContacts
    };
}