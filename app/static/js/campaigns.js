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
    const modal = document.getElementById('createCampaignModal');
    if (modal) {
        modal.addEventListener('show.bs.modal', resetCampaignModal);
        setupStepValidation();
        setupSelectionMethodListeners();
        handleSelectionMethodChange();
    }
}

function setupSelectionMethodListeners() {
    // Add event listeners for selection method radio buttons
    const selectionMethodRadios = document.querySelectorAll('input[name="selectionMethod"]');
    selectionMethodRadios.forEach(radio => {
        radio.addEventListener('change', handleSelectionMethodChange);
    });
    
    // Add event listeners for filter fields to update contact count
    const filterFields = ['targetCompany', 'targetLocation', 'targetJobTitle'];
    filterFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('change', updateContactCount);
        }
    });
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
    if (!currentStep) {
        console.error('No current step found');
        return;
    }
    
    const stepNumber = parseInt(currentStep.id.replace('step', ''));
    console.log(`Attempting to move from step ${stepNumber}`);
    
    if (validateCurrentStep(stepNumber)) {
        console.log(`Step ${stepNumber} validation passed`);
        saveCurrentStepData(stepNumber);
        showStep(stepNumber + 1);
    } else {
        console.log(`Step ${stepNumber} validation failed`);
        // Show validation error
        showToast('warningToast', `Please complete all required fields in step ${stepNumber}`);
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
    const nameInput = document.getElementById('campaignName');
    if (!nameInput) {
        console.error('Campaign name input not found');
        return false;
    }
    
    const name = nameInput.value.trim();
    console.log(`Campaign name validation: "${name}", length: ${name.length}`);
    
    if (name.length === 0) {
        // Highlight the field
        nameInput.classList.add('is-invalid');
        return false;
    } else {
        nameInput.classList.remove('is-invalid');
        return true;
    }
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
            const modal = bootstrap.Modal.getInstance(document.getElementById('createCampaignModal'));
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
    console.log('loadCampaigns() called');
    
    // Check if we have the individual campaign containers
    const activeCampaignsContainer = document.getElementById('activeCampaignsContainer');
    const draftCampaignsContainer = document.getElementById('draftCampaignsContainer');
    const completedCampaignsContainer = document.getElementById('completedCampaignsContainer');
    
    if (!activeCampaignsContainer || !draftCampaignsContainer || !completedCampaignsContainer) {
        console.error('Campaign containers not found');
        return;
    }
    
    console.log('Setting loading state...');
    const loadingHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading campaigns...</p>
        </div>
    `;
    
    // Set loading state on all containers
    activeCampaignsContainer.innerHTML = loadingHTML;
    draftCampaignsContainer.innerHTML = loadingHTML;
    completedCampaignsContainer.innerHTML = loadingHTML;
    
    console.log('Fetching campaigns from /api/campaigns...');
    fetch('/api/campaigns')
        .then(response => {
            console.log('Response received:', response.status, response.statusText);
            return response.json();
        })
        .then(data => {
            console.log('Campaign data received:', data);
            if (data.success) {
                console.log('Campaigns loaded successfully:', data.campaigns?.length || 0, 'campaigns');
                displayCampaigns(data.campaigns || []);
                updateCampaignStats(data.campaigns || []);
            } else {
                console.error('API returned success=false:', data.message);
                throw new Error(data.message || 'Failed to load campaigns');
            }
        })
        .catch(error => {
            console.error('Error loading campaigns:', error);
            const errorHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                    <h5 class="text-danger">Failed to Load Campaigns</h5>
                    <p class="text-muted">${error.message}</p>
                    <button class="btn btn-outline-primary" onclick="loadCampaigns()">
                        <i class="fas fa-refresh me-2"></i>Retry
                    </button>
                </div>
            `;
            
            // Set error state on all containers
            activeCampaignsContainer.innerHTML = errorHTML;
            draftCampaignsContainer.innerHTML = errorHTML;
            completedCampaignsContainer.innerHTML = errorHTML;
        });
}

function displayCampaigns(campaigns) {
    console.log('displayCampaigns() called with:', campaigns);
    
    // Store campaigns globally for use in details modal
    window.lastLoadedCampaigns = campaigns;
    
    const activeCampaignsContainer = document.getElementById('activeCampaignsContainer');
    const draftCampaignsContainer = document.getElementById('draftCampaignsContainer');
    const completedCampaignsContainer = document.getElementById('completedCampaignsContainer');
    
    if (!activeCampaignsContainer || !draftCampaignsContainer || !completedCampaignsContainer) {
        console.error('Campaign containers not found in displayCampaigns');
        return;
    }
    
    if (campaigns.length === 0) {
        console.log('No campaigns to display, showing empty state');
        const emptyStateHTML = `
            <div class="text-center py-5">
                <i class="fas fa-bullhorn fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Campaigns Yet</h5>
                <p class="text-muted">Create your first campaign to start reaching out to contacts.</p>
                <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#createCampaignModal">
                    <i class="fas fa-plus me-2"></i>Create Campaign
                </button>
            </div>
        `;
        activeCampaignsContainer.innerHTML = emptyStateHTML;
        draftCampaignsContainer.innerHTML = '<div class="text-center text-muted py-4"><p>No draft campaigns found.</p></div>';
        completedCampaignsContainer.innerHTML = '<div class="text-center text-muted py-4"><p>No completed campaigns found.</p></div>';
        return;
    }
    
    // Separate campaigns by status
    const activeCampaigns = campaigns.filter(c => c.status === 'active');
    const pausedCampaigns = campaigns.filter(c => c.status === 'paused');
    const completedCampaigns = campaigns.filter(c => c.status === 'completed');
    const draftCampaigns = campaigns.filter(c => c.status === 'draft');
    
    console.log('Campaign counts by status:', {
        active: activeCampaigns.length,
        paused: pausedCampaigns.length,
        completed: completedCampaigns.length,
        draft: draftCampaigns.length
    });
    
    // Display active campaigns (including paused ones in the active tab)
    const allActiveCampaigns = [...activeCampaigns, ...pausedCampaigns];
    if (allActiveCampaigns.length > 0) {
        console.log('Adding active campaigns section');
        activeCampaignsContainer.innerHTML = displayCampaignList(allActiveCampaigns, 'activeCampaigns', 'active');
    } else {
        activeCampaignsContainer.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-bullhorn fa-3x mb-3"></i>
                <p>No active campaigns yet. Create your first GTM campaign to get started!</p>
                <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#createCampaignModal">
                    <i class="fas fa-plus me-1"></i>Create Campaign
                </button>
            </div>
        `;
    }
    
    // Display draft campaigns
    if (draftCampaigns.length > 0) {
        console.log('Adding draft campaigns section');
        draftCampaignsContainer.innerHTML = displayCampaignList(draftCampaigns, 'draftCampaigns', 'draft');
    } else {
        draftCampaignsContainer.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-edit fa-3x mb-3"></i>
                <p>No draft campaigns found.</p>
            </div>
        `;
    }
    
    // Display completed campaigns
    if (completedCampaigns.length > 0) {
        console.log('Adding completed campaigns section');
        completedCampaignsContainer.innerHTML = displayCampaignList(completedCampaigns, 'completedCampaigns', 'completed');
    } else {
        completedCampaignsContainer.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-check fa-3x mb-3"></i>
                <p>No completed campaigns found.</p>
            </div>
        `;
    }
    
    console.log('Campaigns display completed');
}

function displayCampaignList(campaigns, containerId, type) {
    console.log(`displayCampaignList called for ${type} with ${campaigns.length} campaigns`);
    let html = '<div class="row">';
    
    campaigns.forEach(campaign => {
        const statusBadge = getStatusBadge(campaign.status);
        const priorityBadge = getPriorityBadge('medium'); // Default since not in DB
        const createdDate = new Date(campaign.created_at).toLocaleDateString();
        const emailsSent = campaign.emails_sent || 0;
        const targetCount = campaign.target_contacts_count || 0;
        const responseRate = targetCount > 0 ? Math.round((campaign.responses_received || 0) / targetCount * 100) : 0;
        
        html += `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card campaign-card h-100">
                    <div class="card-header d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="card-title mb-1">${campaign.name}</h6>
                            <small class="text-muted">${(campaign.type || 'unknown').replace('_', ' ').toUpperCase()}</small>
                        </div>
                        <div>
                            ${statusBadge}
                            ${priorityBadge}
                        </div>
                    </div>
                    <div class="card-body">
                        <p class="card-text small text-muted">${campaign.description || 'No description provided'}</p>
                        
                        <div class="campaign-metrics">
                            <div class="row text-center">
                                <div class="col-4">
                                    <div class="metric-value">${targetCount}</div>
                                    <div class="metric-label">Targets</div>
                                </div>
                                <div class="col-4">
                                    <div class="metric-value">${emailsSent}</div>
                                    <div class="metric-label">Sent</div>
                                </div>
                                <div class="col-4">
                                    <div class="metric-value">${responseRate}%</div>
                                    <div class="metric-label">Response</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="campaign-details mt-3">
                            <small class="text-muted">
                                <i class="fas fa-calendar me-1"></i>Created: ${createdDate}<br>
                                <i class="fas fa-envelope me-1"></i>Template: ${campaign.email_template || 'Not set'}<br>
                                <i class="fas fa-clock me-1"></i>Follow-up: ${campaign.followup_days || 3} days
                            </small>
                        </div>
                    </div>
                    <div class="card-footer">
                        <div class="btn-group w-100" role="group">
                            <button type="button" class="btn btn-outline-primary btn-sm" onclick="viewCampaignDetails('${campaign.id}')">
                                <i class="fas fa-eye me-1"></i>View
                            </button>
                            <button type="button" class="btn btn-outline-info btn-sm" onclick="viewCampaignAnalytics('${campaign.id}', '${campaign.name.replace(/'/g, '&apos;')}')">
                                <i class="fas fa-chart-line me-1"></i>Analytics
                            </button>
                            ${campaign.status === 'draft' ? 
                                `<button type="button" class="btn btn-outline-success btn-sm" onclick="launchCampaign('${campaign.id}')">
                                    <i class="fas fa-rocket me-1"></i>Launch
                                </button>` : ''
                            }
                            ${campaign.status === 'active' ? 
                                `<button type="button" class="btn btn-outline-warning btn-sm" onclick="pauseCampaign(${campaign.id})">
                                    <i class="fas fa-pause me-1"></i>Pause
                                </button>` : 
                                campaign.status === 'paused' ?
                                `<button type="button" class="btn btn-outline-success btn-sm" onclick="resumeCampaign(${campaign.id})">
                                    <i class="fas fa-play me-1"></i>Resume
                                </button>` : ''
                            }
                        </div>
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
    console.log('Loading campaign details for:', campaignId);
    
    // Show the modal immediately with loading state
    const modal = new bootstrap.Modal(document.getElementById('campaignDetailsModal'));
    modal.show();
    
    // Set loading state
    setDetailsLoadingState(true);
    
    // Set campaign ID for controls
    setCampaignDetailsId(campaignId);
    
    // Load campaign activity data
    loadCampaignActivity(campaignId);
    
    // Fetch campaign data from campaigns list first (immediate display)
    const campaignsData = getCurrentCampaignData(campaignId);
    if (campaignsData) {
        populateCampaignDetails(campaignsData);
    }
    
    // Then fetch detailed status (may have additional info)
    fetch(`/api/campaigns/${campaignId}/status`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Merge status data with campaign data
                const enhancedData = { ...campaignsData, ...data.status };
                populateCampaignDetails(enhancedData);
            } else {
                console.error('Failed to load campaign status:', data.message);
                // Keep displaying basic campaign data
            }
        })
        .catch(error => {
            console.error('Error loading campaign status:', error);
            // Keep displaying basic campaign data
        })
        .finally(() => {
            setDetailsLoadingState(false);
        });
}

function setCampaignDetailsId(campaignId) {
    const modalElement = document.getElementById('campaignDetailsModal');
    if (modalElement) {
        modalElement.setAttribute('data-campaign-id', campaignId);
    }
}

function getCurrentCampaignData(campaignId) {
    // Try to get campaign data from currently loaded campaigns
    if (window.lastLoadedCampaigns) {
        return window.lastLoadedCampaigns.find(c => c.id == campaignId);
    }
    return null;
}

function setDetailsLoadingState(isLoading) {
    const loadingText = isLoading ? 'Loading...' : '';
    const fields = [
        'detailsCampaignName', 'detailsCampaignType', 'detailsEmailTemplate',
        'detailsFollowupDays', 'detailsCampaignDescription', 'detailsCreatedAt',
        'detailsUpdatedAt', 'detailsTotalContacts', 'detailsEmailsSent',
        'detailsFailedEmails', 'detailsSuccessRate', 'detailsResponses',
        'detailsActiveContacts', 'detailsFirstEmail', 'detailsLastEmail',
        'detailsUniqueRecipients', 'detailsTotalEmails'
    ];
    
    fields.forEach(fieldId => {
        const element = document.getElementById(fieldId);
        if (element && isLoading) {
            element.textContent = loadingText;
        }
    });
}

function populateCampaignDetails(campaign) {
    if (!campaign) return;
    
    // Update modal title
    const titleElement = document.getElementById('campaignDetailsTitle');
    if (titleElement) {
        titleElement.textContent = `${campaign.name} - Details`;
    }
    
    // Basic Information
    const setElementText = (id, value) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    };
    
    setElementText('detailsCampaignName', campaign.name || 'N/A');
    setElementText('detailsCampaignType', (campaign.type || 'cold_outreach').replace('_', ' ').toUpperCase());
    setElementText('detailsEmailTemplate', getEmailTemplateDisplayName(campaign.email_template || 'deep_research'));
    setElementText('detailsFollowupDays', `${campaign.followup_days || 3} days`);
    setElementText('detailsCampaignDescription', campaign.description || 'No description provided');
    
    // Dates
    if (campaign.created_at) {
        setElementText('detailsCreatedAt', new Date(campaign.created_at).toLocaleString());
    }
    if (campaign.updated_at) {
        setElementText('detailsUpdatedAt', new Date(campaign.updated_at).toLocaleString());
    }
    
    // Status badges
    const statusElement = document.getElementById('detailsCampaignStatus');
    if (statusElement) {
        statusElement.className = `badge ${getStatusBadgeClass(campaign.status)}`;
        statusElement.textContent = (campaign.status || 'unknown').toUpperCase();
    }
    
    const priorityElement = document.getElementById('detailsCampaignPriority');
    if (priorityElement) {
        priorityElement.className = `badge ${getPriorityBadgeClass(campaign.priority)}`;
        priorityElement.textContent = (campaign.priority || 'medium').toUpperCase();
    }
    
    // Metrics
    setElementText('detailsTotalContacts', campaign.total_contacts || campaign.target_contacts_count || 0);
    setElementText('detailsEmailsSent', campaign.sent_emails || campaign.emails_sent || 0);
    setElementText('detailsFailedEmails', campaign.failed_emails || 0);
    setElementText('detailsSuccessRate', `${campaign.success_rate || 0}%`);
    setElementText('detailsResponses', campaign.responses_received || 0);
    setElementText('detailsActiveContacts', campaign.active_contacts || 0);
    
    // Timeline
    setElementText('detailsFirstEmail', campaign.first_email_date ? 
        new Date(campaign.first_email_date).toLocaleString() : 'No emails sent yet');
    setElementText('detailsLastEmail', campaign.last_email_date ? 
        new Date(campaign.last_email_date).toLocaleString() : 'No emails sent yet');
    setElementText('detailsUniqueRecipients', campaign.unique_recipients || 0);
    setElementText('detailsTotalEmails', campaign.total_emails || 0);
}

function getEmailTemplateDisplayName(template) {
    const templates = {
        'deep_research': 'Deep Research',
        'quick_intro': 'Quick Introduction',
        'follow_up': 'Follow Up',
        'cold_outreach': 'Cold Outreach'
    };
    return templates[template] || template.replace('_', ' ').toUpperCase();
}

function getPriorityBadgeClass(priority) {
    const priorityClasses = {
        'high': 'bg-danger',
        'medium': 'bg-warning',
        'low': 'bg-success'
    };
    return priorityClasses[priority] || 'bg-secondary';
}

function deleteAllCampaigns() {
    if (!confirm('Are you sure you want to delete ALL campaigns? This action cannot be undone.')) {
        return;
    }
    
    const deleteBtn = document.getElementById('deleteAllCampaigns');
    if (!deleteBtn) {
        console.error('Delete all campaigns button not found');
        showToast('errorToast', 'Delete button not found');
        return;
    }
    
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

// Campaign action functions
function viewCampaignAnalytics(campaignId, campaignName) {
    console.log('Loading campaign analytics for:', campaignId, campaignName);
    
    // Show the analytics modal immediately with loading state
    const modal = new bootstrap.Modal(document.getElementById('campaignAnalyticsModal'));
    modal.show();
    
    // Set modal title
    const titleElement = document.getElementById('campaignAnalyticsTitle');
    if (titleElement) {
        titleElement.textContent = `${campaignName} - Analytics`;
    }
    
    // Set loading state for analytics content
    const analyticsContent = document.getElementById('campaignAnalyticsContent');
    if (analyticsContent) {
        analyticsContent.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading analytics...</p>
            </div>
        `;
    }
    
    // Fetch analytics data
    fetch(`/api/campaigns/${campaignId}/analytics`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayCampaignAnalytics(data.analytics, campaignName);
            } else {
                throw new Error(data.error || 'Failed to load analytics');
            }
        })
        .catch(error => {
            console.error('Error loading campaign analytics:', error);
            if (analyticsContent) {
                analyticsContent.innerHTML = `
                    <div class="text-center py-4">
                        <i class="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                        <h5 class="text-danger">Failed to Load Analytics</h5>
                        <p class="text-muted">${error.message}</p>
                        <button class="btn btn-outline-primary" onclick="viewCampaignAnalytics(${campaignId}, '${campaignName}')">
                            <i class="fas fa-refresh me-2"></i>Retry
                        </button>
                    </div>
                `;
            }
        });
}

function displayCampaignAnalytics(analytics, campaignName) {
    const analyticsContent = document.getElementById('campaignAnalyticsContent');
    if (!analyticsContent) return;
    
    const html = `
        <div class="row">
            <!-- Overview Cards -->
            <div class="col-12 mb-4">
                <div class="row g-3">
                    <div class="col-md-3">
                        <div class="card bg-primary text-white">
                            <div class="card-body">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <h6 class="card-subtitle mb-2">Total Sent</h6>
                                        <h4 class="mb-0">${analytics.total_sent || 0}</h4>
                                    </div>
                                    <i class="fas fa-paper-plane fa-2x opacity-75"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-success text-white">
                            <div class="card-body">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <h6 class="card-subtitle mb-2">Opened</h6>
                                        <h4 class="mb-0">${analytics.total_opened || 0}</h4>
                                        <small class="opacity-75">${analytics.open_rate || 0}% rate</small>
                                    </div>
                                    <i class="fas fa-envelope-open fa-2x opacity-75"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-info text-white">
                            <div class="card-body">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <h6 class="card-subtitle mb-2">Replied</h6>
                                        <h4 class="mb-0">${analytics.total_replied || 0}</h4>
                                        <small class="opacity-75">${analytics.reply_rate || 0}% rate</small>
                                    </div>
                                    <i class="fas fa-reply fa-2x opacity-75"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-warning text-dark">
                            <div class="card-body">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <h6 class="card-subtitle mb-2">Bounced</h6>
                                        <h4 class="mb-0">${analytics.total_bounced || 0}</h4>
                                        <small class="opacity-75">${analytics.bounce_rate || 0}% rate</small>
                                    </div>
                                    <i class="fas fa-exclamation-triangle fa-2x opacity-75"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Click Analytics -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="card-title mb-0"><i class="fas fa-mouse-pointer me-2"></i>Click Analytics</h5>
                    </div>
                    <div class="card-body">
                        <div class="row text-center">
                            <div class="col-6">
                                <h4 class="text-primary">${analytics.total_clicks || 0}</h4>
                                <small class="text-muted">Total Clicks</small>
                            </div>
                            <div class="col-6">
                                <h4 class="text-success">${analytics.unique_clicks || 0}</h4>
                                <small class="text-muted">Unique Clicks</small>
                            </div>
                        </div>
                        <div class="mt-3">
                            <div class="d-flex justify-content-between">
                                <span>Click Rate</span>
                                <span class="fw-bold">${analytics.click_rate || 0}%</span>
                            </div>
                            <div class="progress mt-1">
                                <div class="progress-bar bg-info" style="width: ${analytics.click_rate || 0}%"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Performance Summary -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="card-title mb-0"><i class="fas fa-chart-bar me-2"></i>Performance Summary</h5>
                    </div>
                    <div class="card-body">
                        <div class="mb-3">
                            <div class="d-flex justify-content-between">
                                <span>Open Rate</span>
                                <span class="fw-bold text-success">${analytics.open_rate || 0}%</span>
                            </div>
                            <div class="progress mt-1">
                                <div class="progress-bar bg-success" style="width: ${analytics.open_rate || 0}%"></div>
                            </div>
                        </div>
                        <div class="mb-3">
                            <div class="d-flex justify-content-between">
                                <span>Reply Rate</span>
                                <span class="fw-bold text-info">${analytics.reply_rate || 0}%</span>
                            </div>
                            <div class="progress mt-1">
                                <div class="progress-bar bg-info" style="width: ${analytics.reply_rate || 0}%"></div>
                            </div>
                        </div>
                        <div class="mb-0">
                            <div class="d-flex justify-content-between">
                                <span>Bounce Rate</span>
                                <span class="fw-bold text-warning">${analytics.bounce_rate || 0}%</span>
                            </div>
                            <div class="progress mt-1">
                                <div class="progress-bar bg-warning" style="width: ${analytics.bounce_rate || 0}%"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        ${analytics.total_sent === 0 ? `
            <div class="text-center py-4">
                <i class="fas fa-chart-line fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Analytics Data Yet</h5>
                <p class="text-muted">This campaign hasn't sent any emails yet. Analytics will appear once emails are sent.</p>
            </div>
        ` : ''}
    `;
    
    analyticsContent.innerHTML = html;
}

function launchCampaign(campaignId) {
    console.log(`Launching campaign: ${campaignId}`);
    if (confirm('Are you sure you want to launch this campaign? This will start sending emails to the selected contacts.')) {
        // Implementation would go here
        showToast('infoToast', 'Campaign launch feature coming soon!');
    }
}

function pauseCampaign(campaignId) {
    console.log(`Pausing campaign: ${campaignId}`);
    if (confirm('Are you sure you want to pause this campaign?')) {
        // Implementation would go here
        showToast('infoToast', 'Campaign pause feature coming soon!');
    }
}

function resumeCampaign(campaignId) {
    console.log(`Resuming campaign: ${campaignId}`);
    if (confirm('Are you sure you want to resume this campaign?')) {
        // Implementation would go here
        showToast('infoToast', 'Campaign resume feature coming soon!');
    }
}

// Global function assignments for HTML onclick handlers
window.nextStep = nextStep;
window.previousStep = previousStep;
window.handleSelectionMethodChange = handleSelectionMethodChange;
window.toggleContactSelection = toggleContactSelection;
window.searchContactsForCampaign = searchContactsForCampaign;
window.clearCampaignSearch = clearCampaignSearch;
window.saveCampaignDraft = saveCampaignDraft;
window.updateContactCount = updateContactCount;
window.viewCampaignDetails = viewCampaignDetails;
window.viewCampaignAnalytics = viewCampaignAnalytics;
window.launchCampaign = launchCampaign;
window.pauseCampaign = pauseCampaign;
window.resumeCampaign = resumeCampaign;
window.deleteAllCampaigns = deleteAllCampaigns;