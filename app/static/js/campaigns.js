// SalesBot CRM - Campaign Management Module

// Global campaign-related variables
let currentCampaignData = {};
let selectedCampaignContacts = [];
let currentCampaignDetailsId = null;

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
    
    // Clear any stale campaign IDs
    currentCampaignDetailsId = null;
    
    // Reset contact selection
    updateSelectedContactsBadge(0);
    
    // Clear any error messages
    const errorElements = document.querySelectorAll('.text-danger');
    errorElements.forEach(el => el.textContent = '');
    
    // Reset selection method to ensure clean state
    const selectionMethodRadios = document.querySelectorAll('input[name="selectionMethod"]');
    selectionMethodRadios.forEach(radio => {
        if (radio.value === 'manual') {
            radio.checked = true;
        }
    });
    
    // Trigger selection method change to show correct UI
    handleSelectionMethodChange();
    
    console.log('Campaign modal reset with clean state');
}

function showStep(stepNumber) {
    console.log(`Showing step ${stepNumber}`);
    
    // Hide all steps by adding d-none class
    const steps = document.querySelectorAll('.step-content');
    steps.forEach(step => {
        step.classList.add('d-none');
    });
    
    // Show current step by removing d-none class
    const currentStep = document.getElementById(`step${stepNumber}`);
    if (currentStep) {
        currentStep.classList.remove('d-none');
        console.log(`Step ${stepNumber} is now visible`);
    } else {
        console.error(`Step element step${stepNumber} not found`);
    }
    
    // Update step indicators
    updateStepIndicators(stepNumber);
    
    // Update button visibility
    updateStepButtons(stepNumber);
    
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

function updateStepButtons(stepNumber) {
    // This function can be used for step-specific button updates if needed
    // Currently handled by updateNavigationButtons
}

function updateNavigationButtons(stepNumber) {
    const prevBtn = document.getElementById('prevStepBtn');
    const nextBtn = document.getElementById('nextStepBtn');
    const saveBtn = document.getElementById('saveCampaignBtn');
    
    // Previous button
    if (prevBtn) {
        prevBtn.disabled = stepNumber <= 1;
    }
    
    // Next/Save buttons
    if (nextBtn && saveBtn) {
        if (stepNumber === 4) {
            nextBtn.style.display = 'none';
            saveBtn.style.display = 'inline-block';
        } else {
            nextBtn.style.display = 'inline-block';
            saveBtn.style.display = 'none';
        }
    }
}

function nextStep() {
    // Find the currently visible step (one without d-none class)
    let currentStep = document.querySelector('.step-content:not(.d-none)');
    
    // If still not found, check if any step elements exist at all
    if (!currentStep) {
        const allSteps = document.querySelectorAll('.step-content');
        console.log(`Found ${allSteps.length} step-content elements:`, Array.from(allSteps).map(s => s.id));
        
        if (allSteps.length === 0) {
            console.error('No step-content elements found in DOM');
            return;
        }
        
        console.warn('No visible step found, defaulting to step 1');
        showStep(1);
        
        // Try again to find the visible step
        currentStep = document.querySelector('.step-content:not(.d-none)');
        if (!currentStep) {
            console.error('Still no visible step found after showStep(1)');
            return;
        }
    }
    
    continueNextStep(currentStep);
}

function continueNextStep(currentStep) {
    const stepNumber = parseInt(currentStep.id.replace('step', ''));
    console.log(`Attempting to move from step ${stepNumber}`);
    
    if (validateCurrentStep(stepNumber)) {
        console.log(`Step ${stepNumber} validation passed`);
        saveCurrentStepData(stepNumber);
        
        // Only move to next step if we're not on the last step (step 4)
        if (stepNumber < 4) {
            showStep(stepNumber + 1);
            
            // Load step-specific data
            if (stepNumber + 1 === 4) {
                populateReviewStep();
            }
        } else {
            // We're on step 4, this should be handled by a "Launch Campaign" button
            console.log('Reached final step - campaign should be submitted via Launch button');
            showToast('infoToast', 'Click "Launch Campaign" to create your campaign');
        }
    } else {
        console.log(`Step ${stepNumber} validation failed`);
        // Show validation error
        showToast('warningToast', `Please complete all required fields in step ${stepNumber}`);
    }
}

function previousStep() {
    const currentStep = document.querySelector('.step-content:not(.d-none)');
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
            currentCampaignData.type = document.getElementById('campaignType').value;
            break;
        case 2:
            // Save selection method
            const selectionMethod = document.querySelector('input[name="selectionMethod"]:checked');
            currentCampaignData.selection_method = selectionMethod ? selectionMethod.value : 'quick';
            
            // Save filter criteria
            currentCampaignData.target_criteria = getFilterCriteria();
            
            // If manual selection, save selected contacts
            if (currentCampaignData.selection_method === 'manual') {
                currentCampaignData.selected_contacts = selectedCampaignContacts;
            }
            break;
        case 3:
            currentCampaignData.email_template = document.getElementById('emailTemplate').value;
            currentCampaignData.schedule_date = document.getElementById('scheduleDate').value;
            currentCampaignData.followup_days = parseInt(document.getElementById('followupDays').value) || 3;
            
            // Email sending settings
            currentCampaignData.email_frequency = {
                value: parseInt(document.getElementById('emailFrequencyValue').value) || 30,
                unit: document.getElementById('emailFrequencyUnit').value || 'minutes'
            };
            currentCampaignData.timezone = document.getElementById('campaignTimezone').value;
            currentCampaignData.daily_email_limit = parseInt(document.getElementById('dailyEmailLimit').value) || 50;
            
            // Random delay settings
            currentCampaignData.random_delay = {
                min_minutes: parseInt(document.getElementById('randomDelayMin').value) || 1,
                max_minutes: parseInt(document.getElementById('randomDelayMax').value) || 5
            };
            
            // Business hours settings
            currentCampaignData.respect_business_hours = document.getElementById('respectBusinessHours').checked;
            if (currentCampaignData.respect_business_hours) {
                currentCampaignData.business_hours = {
                    start_time: document.getElementById('businessStartTime').value || '09:00',
                    end_time: document.getElementById('businessEndTime').value || '17:00',
                    days: {
                        monday: document.getElementById('businessMon').checked,
                        tuesday: document.getElementById('businessTue').checked,
                        wednesday: document.getElementById('businessWed').checked,
                        thursday: document.getElementById('businessThu').checked,
                        friday: document.getElementById('businessFri').checked,
                        saturday: document.getElementById('businessSat').checked,
                        sunday: document.getElementById('businessSun').checked
                    }
                };
            }
            break;
    }
    
    console.log('Saved step data:', currentCampaignData);
}

function populateReviewStep() {
    // Save all current step data first to ensure we have complete data
    saveCurrentStepData(3);
    
    // Update contact count from the current selection before populating review
    const selectionMethod = document.querySelector('input[name="selectionMethod"]:checked');
    if (selectionMethod && selectionMethod.value !== 'manual') {
        // Trigger an update of contact count for filtered selections
        updateContactCount();
        // Give a brief moment for the count to update
        setTimeout(() => {
            updateReviewContactCount();
        }, 500);
    } else {
        // For manual selection, update immediately
        updateReviewContactCount();
    }
    
    // Update the review modal elements
    const reviewCampaignName = document.getElementById('reviewCampaignName');
    const reviewCampaignType = document.getElementById('reviewCampaignType');
    const reviewEmailTemplate = document.getElementById('reviewEmailTemplate');
    const reviewFollowup = document.getElementById('reviewFollowup');
    
    // Campaign name and type
    if (reviewCampaignName) {
        reviewCampaignName.textContent = currentCampaignData.name || 'Untitled Campaign';
    }
    if (reviewCampaignType) {
        reviewCampaignType.textContent = currentCampaignData.type || 'GTM Campaign';
    }
    
    // Email template
    if (reviewEmailTemplate) {
        const templateText = getEmailTemplateDisplayName(currentCampaignData.email_template || 'cold_outreach');
        reviewEmailTemplate.textContent = templateText;
    }
    
    // Follow-up days
    if (reviewFollowup) {
        const followupDays = currentCampaignData.followup_days || 3;
        reviewFollowup.textContent = `${followupDays} days`;
    }
    
    // Contact count will be updated separately
    updateReviewContactCount();
    
    // Update email settings
    const reviewEmailFrequency = document.getElementById('reviewEmailFrequency');
    const reviewDailyLimit = document.getElementById('reviewDailyLimit');
    const reviewTimezone = document.getElementById('reviewTimezone');
    const reviewBusinessHours = document.getElementById('reviewBusinessHours');
    
    if (reviewEmailFrequency) {
        const frequency = currentCampaignData.email_frequency || { value: 30, unit: 'minutes' };
        reviewEmailFrequency.textContent = `${frequency.value} ${frequency.unit}`;
    }
    
    if (reviewDailyLimit) {
        const dailyLimit = currentCampaignData.daily_email_limit || 50;
        reviewDailyLimit.textContent = `${dailyLimit} emails`;
    }
    
    if (reviewTimezone) {
        const timezone = currentCampaignData.timezone || 'America/Los_Angeles';
        const timezoneMap = {
            'America/New_York': 'Eastern Time',
            'America/Chicago': 'Central Time',
            'America/Denver': 'Mountain Time',
            'America/Los_Angeles': 'Pacific Time',
            'Europe/London': 'GMT',
            'Europe/Paris': 'Central European Time',
            'Asia/Tokyo': 'Japan Time',
            'Australia/Sydney': 'Sydney Time'
        };
        reviewTimezone.textContent = timezoneMap[timezone] || timezone;
    }
    
    if (reviewBusinessHours) {
        const respectBusinessHours = currentCampaignData.respect_business_hours !== false;
        if (respectBusinessHours && currentCampaignData.business_hours) {
            const businessHours = currentCampaignData.business_hours;
            const businessDays = Object.values(businessHours.days || {}).filter(day => day).length;
            const timeRange = `${businessHours.start_time || '09:00'}-${businessHours.end_time || '17:00'}`;
            reviewBusinessHours.textContent = `${timeRange} (${businessDays} days)`;
        } else {
            reviewBusinessHours.textContent = 'Disabled';
        }
    }
    
    // Also update the reviewContent div if it exists for backward compatibility
    const reviewContent = document.getElementById('reviewContent');
    if (reviewContent) {
        let html = `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-muted mb-3">Campaign Details</h6>
                    <div class="mb-2">
                        <strong>Name:</strong> ${currentCampaignData.name || 'Not specified'}
                    </div>
                    <div class="mb-2">
                        <strong>Email Template:</strong> ${getEmailTemplateDisplayName(currentCampaignData.email_template || 'cold_outreach')}
                    </div>
                </div>
                <div class="col-md-6">
                    <h6 class="text-muted mb-3">Target & Selection</h6>
                    <div class="mb-2">
                        <strong>Selected Contacts:</strong> ${contactCount}
                    </div>
                </div>
            </div>
        `;
        
        reviewContent.innerHTML = html;
    }
}

function updateReviewContactCount() {
    // Contact count
    let contactCount = 0;
    const selectionMethod = document.querySelector('input[name="selectionMethod"]:checked');
    
    if (selectionMethod) {
        if (selectionMethod.value === 'manual') {
            contactCount = selectedCampaignContacts.length;
        } else {
            // For quick/advanced filters, try to get count from the estimated count element
            const estimatedCountElement = document.getElementById('estimatedContactCount');
            if (estimatedCountElement) {
                const countText = estimatedCountElement.textContent;
                // Extract number from text like "25 contacts match your criteria"
                const match = countText.match(/\d+/);
                contactCount = match ? parseInt(match[0]) : 0;
            }
            
            // Also try the selected contacts count badge
            if (contactCount === 0) {
                const selectedContactsBadge = document.getElementById('selectedContactsCount');
                if (selectedContactsBadge) {
                    const badgeText = selectedContactsBadge.textContent;
                    const match = badgeText.match(/(\d+)\s+contacts/);
                    contactCount = match ? parseInt(match[1]) : 0;
                }
            }
        }
    }
    
    // Update contact-related elements
    const reviewContactCount = document.getElementById('reviewContactCount');
    if (reviewContactCount) {
        reviewContactCount.textContent = contactCount.toString();
    }
    
    // Update any other elements that might show target contacts
    const targetContactsElements = document.querySelectorAll('[id*="reviewTarget"], [id*="estimatedReach"]');
    targetContactsElements.forEach(element => {
        if (element.id.includes('Contact') || element.id.includes('Reach')) {
            element.textContent = `${contactCount}`;
        }
    });
    
    // Update expected responses
    const expectedResponses = document.getElementById('expectedResponses');
    if (expectedResponses) {
        const expectedReplies = Math.round(contactCount * 0.15);
        expectedResponses.textContent = `~${expectedReplies} replies`;
    }
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
    
    // Get all selection method content divs
    const quickFilterOptions = document.getElementById('quickFilterOptions');
    const manualSelectionOptions = document.getElementById('manualSelectionOptions');
    const advancedFilterOptions = document.getElementById('advancedFilterOptions');
    
    if (!selectionMethod) return;
    
    // Hide all options first
    if (quickFilterOptions) quickFilterOptions.classList.add('d-none');
    if (manualSelectionOptions) manualSelectionOptions.classList.add('d-none');
    if (advancedFilterOptions) advancedFilterOptions.classList.add('d-none');
    
    // Show the selected option
    switch (selectionMethod.value) {
        case 'quick':
            if (quickFilterOptions) quickFilterOptions.classList.remove('d-none');
            updateContactCount();
            break;
        case 'manual':
            if (manualSelectionOptions) manualSelectionOptions.classList.remove('d-none');
            loadContactsForManualSelection();
            break;
        case 'advanced':
            if (advancedFilterOptions) advancedFilterOptions.classList.remove('d-none');
            updateContactCount();
            break;
    }
    
    console.log(`Selection method changed to: ${selectionMethod.value}`);
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
    const badge = document.getElementById('selectedContactsCount');
    if (!badge) {
        console.error('Selected contacts count badge not found');
        return;
    }
    
    const displayCount = count !== null ? count : selectedCampaignContacts.length;
    badge.textContent = `${displayCount} contact${displayCount !== 1 ? 's' : ''} selected`;
    badge.style.display = displayCount > 0 ? 'inline' : 'inline'; // Always show the badge
    
    console.log(`Updated contacts badge: ${displayCount} contacts selected`);
}

function loadContactsForManualSelection() {
    const container = document.getElementById('campaignContactsList');
    if (!container) {
        console.error('Campaign contacts list container not found');
        return;
    }
    
    container.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading contacts...</p>
        </div>
    `;
    
    fetch('/api/contacts/for-campaign?limit=100')
        .then(response => response.json())
        .then(data => {
            // Handle the API response format: {success: true, contacts: [...], ...}
            let contacts = [];
            if (data.success && data.contacts && Array.isArray(data.contacts)) {
                contacts = data.contacts;
            } else if (data.error) {
                throw new Error(data.error);
            } else {
                throw new Error('Failed to load contacts');
            }
            
            displayContactsForSelection(contacts);
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
    const searchInput = document.getElementById('contactSearchCampaign');
    if (!searchInput) {
        console.error('Contact search input not found');
        return;
    }
    
    const searchTerm = searchInput.value.trim();
    if (searchTerm.length < 2) {
        loadContactsForManualSelection();
        return;
    }
    
    fetch(`/api/search_contacts?q=${encodeURIComponent(searchTerm)}`)
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
    const container = document.getElementById('campaignContactsList');
    if (!container) {
        console.error('Campaign contacts list container not found');
        return;
    }
    
    if (contacts.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-users fa-2x text-muted mb-3"></i>
                <p class="text-muted">No contacts found</p>
                <p class="text-muted small">Try adjusting your search terms</p>
            </div>
        `;
        return;
    }
    
    // Don't create a new search input - use the existing one in the template
    let html = `<div class="contact-selection-list">`;
    
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
    
    const createBtn = document.getElementById('saveCampaignBtn');
    if (!createBtn) {
        console.error('Save campaign button not found');
        return;
    }
    
    const originalText = createBtn.innerHTML;
    
    createBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
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
            showToast('successToast', 'Campaign saved successfully! You can launch it from the campaign list.');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('createCampaignModal'));
            if (modal) {
                modal.hide();
            }
            
            // Reload campaigns
            loadCampaigns();
        } else {
            throw new Error(data.message || 'Failed to save campaign');
        }
    })
    .catch(error => {
        console.error('Error creating campaign:', error);
        showToast('errorToast', 'Failed to save campaign: ' + error.message);
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
    const currentStep = document.querySelector('.step-content:not(.d-none)');
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
    
    // Check if we have the single campaign container
    const allCampaignsContainer = document.getElementById('allCampaignsContainer');
    
    if (!allCampaignsContainer) {
        console.error('Campaign container not found');
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
    
    // Set loading state on the container
    allCampaignsContainer.innerHTML = loadingHTML;
    
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
            
            // Set error state on the container
            allCampaignsContainer.innerHTML = errorHTML;
        });
}

function displayCampaigns(campaigns) {
    console.log('displayCampaigns() called with:', campaigns);
    
    // Store campaigns globally for use in details modal
    window.lastLoadedCampaigns = campaigns;
    
    const allCampaignsContainer = document.getElementById('allCampaignsContainer');
    
    if (!allCampaignsContainer) {
        console.error('Campaign container not found in displayCampaigns');
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
        allCampaignsContainer.innerHTML = emptyStateHTML;
        return;
    }
    
    console.log('Displaying all campaigns in a single list');
    // Display all campaigns regardless of status in a single list
    allCampaignsContainer.innerHTML = displayCampaignList(campaigns, 'allCampaigns', 'all');
    
    console.log('Campaigns display completed');
}

function displayCampaignList(campaigns, containerId, type) {
    console.log(`displayCampaignList called for ${type} with ${campaigns.length} campaigns`);
    
    let html = `
        <div class="campaign-list-container">
            <div class="table-responsive shadow-sm rounded">
                <table class="table table-hover table-striped mb-0 campaign-table">
                    <thead class="table-dark">
                        <tr>
                            <th scope="col" class="border-0 ps-4">
                                <i class="fas fa-bullhorn me-2"></i>Campaign
                            </th>
                            <th scope="col" class="border-0 text-center">
                                <i class="fas fa-signal me-2"></i>Status
                            </th>
                            <th scope="col" class="border-0 text-center">
                                <i class="fas fa-tag me-2"></i>Type
                            </th>
                            <th scope="col" class="border-0 text-center">
                                <i class="fas fa-users me-2"></i>Targets
                            </th>
                            <th scope="col" class="border-0 text-center">
                                <i class="fas fa-paper-plane me-2"></i>Sent
                            </th>
                            <th scope="col" class="border-0 text-center">
                                <i class="fas fa-chart-line me-2"></i>Response
                            </th>
                            <th scope="col" class="border-0 text-center">
                                <i class="fas fa-calendar me-2"></i>Created
                            </th>
                            <th scope="col" class="border-0 text-center pe-4">
                                <i class="fas fa-cogs me-2"></i>Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody>
    `;
    
    campaigns.forEach((campaign, index) => {
        const statusBadge = getStatusBadge(campaign.status);
        const createdDate = new Date(campaign.created_at).toLocaleDateString();
        const emailsSent = campaign.emails_sent || 0;
        const targetCount = campaign.target_contacts_count || 0;
        const responseRate = targetCount > 0 ? Math.round((campaign.responses_received || 0) / targetCount * 100) : 0;
        
        // Get status icon and color
        const statusIcon = getStatusIcon(campaign.status);
        const rowClass = campaign.status === 'active' ? 'table-success-subtle' : 
                        campaign.status === 'paused' ? 'table-warning-subtle' : 
                        campaign.status === 'draft' ? 'table-info-subtle' : 
                        campaign.status === 'completed' ? 'table-secondary-subtle' : '';
        
        html += `
            <tr class="campaign-row ${rowClass}" data-campaign-id="${campaign.id}">
                <td class="ps-4 py-3">
                    <div class="d-flex align-items-center">
                        <div class="campaign-avatar me-3">
                            <div class="avatar-circle bg-primary text-white d-flex align-items-center justify-content-center">
                                ${campaign.name.charAt(0).toUpperCase()}
                            </div>
                        </div>
                        <div class="campaign-info">
                            <h6 class="campaign-name mb-1 fw-bold text-dark">${campaign.name}</h6>
                            <p class="campaign-desc mb-0 text-muted small">${campaign.description || 'No description provided'}</p>
                            <div class="campaign-meta mt-1">
                                <small class="text-primary">
                                    <i class="fas fa-envelope me-1"></i>${campaign.email_template || 'Default'}
                                </small>
                                <small class="text-muted ms-2">
                                    <i class="fas fa-clock me-1"></i>${campaign.followup_days || 3} days follow-up
                                </small>
                            </div>
                        </div>
                    </div>
                </td>
                <td class="text-center py-3">
                    <div class="status-container">
                        ${statusIcon}
                        ${statusBadge}
                    </div>
                </td>
                <td class="text-center py-3">
                    <span class="badge badge-type bg-gradient bg-secondary text-white px-3 py-2">
                        ${(campaign.type || 'unknown').replace('_', ' ').toUpperCase()}
                    </span>
                </td>
                <td class="text-center py-3">
                    <div class="metric-container">
                        <span class="metric-number fw-bold text-dark fs-5">${targetCount}</span>
                        <div class="metric-label text-muted small">contacts</div>
                    </div>
                </td>
                <td class="text-center py-3">
                    <div class="metric-container">
                        <span class="metric-number fw-bold text-success fs-5">${emailsSent}</span>
                        <div class="metric-label text-muted small">emails</div>
                    </div>
                </td>
                <td class="text-center py-3">
                    <div class="metric-container">
                        <span class="metric-number fw-bold ${responseRate > 15 ? 'text-success' : responseRate > 5 ? 'text-warning' : 'text-danger'} fs-5">
                            ${responseRate}%
                        </span>
                        <div class="metric-label text-muted small">response</div>
                    </div>
                </td>
                <td class="text-center py-3">
                    <div class="date-container">
                        <span class="date-text fw-semibold text-dark">${createdDate}</span>
                        <div class="date-relative text-muted small">${getRelativeDate(campaign.created_at)}</div>
                    </div>
                </td>
                <td class="text-center py-3 pe-4">
                    <div class="action-buttons">
                        <div class="btn-group" role="group">
                            <button type="button" class="btn btn-outline-primary btn-sm rounded-pill me-1" 
                                    onclick="viewCampaignDetails('${campaign.id}')" 
                                    title="View Campaign Details">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button type="button" class="btn btn-outline-info btn-sm rounded-pill me-1" 
                                    onclick="viewCampaignAnalytics('${campaign.id}', '${campaign.name.replace(/'/g, '&apos;')}')"
                                    title="View Analytics">
                                <i class="fas fa-chart-line"></i>
                            </button>
                            <button type="button" class="btn btn-outline-secondary btn-sm rounded-pill me-1" 
                                    onclick="viewCampaignSchedule('${campaign.id}', '${campaign.name.replace(/'/g, '&apos;')}')"
                                    title="View Schedule">
                                <i class="fas fa-clock"></i>
                            </button>
                            <button type="button" class="btn btn-outline-success btn-sm rounded-pill me-1" 
                                    onclick="duplicateCampaign('${campaign.id}', '${campaign.name.replace(/'/g, '&apos;')}')"
                                    title="Duplicate Campaign">
                                <i class="fas fa-copy"></i>
                            </button>
                            <button type="button" class="btn btn-outline-danger btn-sm rounded-pill me-1" 
                                    onclick="deleteSingleCampaign('${campaign.id}', '${campaign.name.replace(/'/g, '&apos;')}')"
                                    title="Delete Campaign">
                                <i class="fas fa-trash"></i>
                            </button>
                            ${campaign.status === 'draft' ? 
                                `<button type="button" class="btn btn-success btn-sm rounded-pill" 
                                         onclick="launchCampaign('${campaign.id}')"
                                         title="Launch Campaign">
                                    <i class="fas fa-rocket"></i>
                                </button>` : ''
                            }
                            ${campaign.status === 'active' ? 
                                `<button type="button" class="btn btn-warning btn-sm rounded-pill" 
                                         onclick="pauseCampaign(${campaign.id})"
                                         title="Pause Campaign">
                                    <i class="fas fa-pause"></i>
                                </button>` : 
                                campaign.status === 'paused' ?
                                `<button type="button" class="btn btn-success btn-sm rounded-pill" 
                                         onclick="resumeCampaign(${campaign.id})"
                                         title="Resume Campaign">
                                    <i class="fas fa-play"></i>
                                </button>` : ''
                            }
                        </div>
                    </div>
                </td>
            </tr>
        `;
    });
    
    html += `
                    </tbody>
                </table>
            </div>
        </div>
        
        <style>
        .campaign-list-container {
            margin-top: 20px;
        }
        
        .campaign-table {
            border: none;
            font-size: 0.9rem;
        }
        
        .campaign-table th {
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 1rem 0.75rem;
            background: linear-gradient(135deg, #343a40 0%, #495057 100%);
        }
        
        .campaign-row {
            border-left: 4px solid transparent;
            transition: all 0.2s ease;
        }
        
        .campaign-row:hover {
            transform: translateX(2px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left-color: #007bff;
        }
        
        .campaign-row.table-success-subtle {
            border-left-color: #28a745;
            background-color: rgba(40, 167, 69, 0.05);
        }
        
        .campaign-row.table-warning-subtle {
            border-left-color: #ffc107;
            background-color: rgba(255, 193, 7, 0.05);
        }
        
        .campaign-row.table-info-subtle {
            border-left-color: #17a2b8;
            background-color: rgba(23, 162, 184, 0.05);
        }
        
        .campaign-row.table-secondary-subtle {
            border-left-color: #6c757d;
            background-color: rgba(108, 117, 125, 0.05);
        }
        
        .avatar-circle {
            width: 45px;
            height: 45px;
            border-radius: 50%;
            font-weight: bold;
            font-size: 1.1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .campaign-name {
            color: #2c3e50;
            font-size: 1rem;
        }
        
        .campaign-desc {
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .campaign-meta small {
            font-size: 0.75rem;
        }
        
        .status-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
        }
        
        .status-icon {
            font-size: 1.2rem;
            margin-bottom: 2px;
        }
        
        .badge-type {
            font-size: 0.75rem;
            font-weight: 500;
            border-radius: 15px;
        }
        
        .metric-container {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        .metric-number {
            line-height: 1;
        }
        
        .metric-label {
            font-size: 0.7rem;
            margin-top: 2px;
        }
        
        .date-container {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        .date-relative {
            font-size: 0.7rem;
            margin-top: 2px;
        }
        
        .action-buttons .btn {
            width: 32px;
            height: 32px;
            padding: 0;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }
        
        .action-buttons .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .action-buttons .btn i {
            font-size: 0.8rem;
        }
        </style>
    `;
    
    return html;
}

function updateCampaignStats(campaigns) {
    const totalCampaigns = campaigns.length;
    const activeCampaigns = campaigns.filter(c => c.status === 'active').length;
    const totalEmails = campaigns.reduce((sum, c) => sum + (c.emails_sent || 0), 0);
    
    // Update stats in UI (support multiple element IDs for different panes)
    const totalCampaignsElement = document.getElementById('totalCampaigns');
    const activeCampaignsElement = document.getElementById('activeCampaigns');
    const totalEmailsElement = document.getElementById('totalEmails');
    const campaignEmailsSentElement = document.getElementById('campaignEmailsSent');
    
    if (totalCampaignsElement) totalCampaignsElement.textContent = totalCampaigns;
    if (activeCampaignsElement) activeCampaignsElement.textContent = activeCampaigns;
    if (totalEmailsElement) totalEmailsElement.textContent = totalEmails;
    if (campaignEmailsSentElement) campaignEmailsSentElement.textContent = totalEmails;
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
    // Set global variable for reference by other functions
    currentCampaignDetailsId = campaignId;
    
    // Also set as data attribute on modal for consistency
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
        'detailsFollowupDays', 'detailsCreatedAt',
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

    // Dates - show in campaign timezone
    const campaignTimezone = getCampaignTimezone(campaign);
    if (campaign.created_at) {
        setElementText('detailsCreatedAt', formatDateInTimezone(campaign.created_at, campaignTimezone));
    }
    if (campaign.updated_at) {
        setElementText('detailsUpdatedAt', formatDateInTimezone(campaign.updated_at, campaignTimezone));
    }

    // Add relative dates for created_at and updated_at
    const createdAtElement = document.getElementById('detailsCreatedAt');
    if (createdAtElement && campaign.created_at) {
        createdAtElement.innerHTML += ` <small class="text-muted">(${getRelativeDate(campaign.created_at)})</small>`;
    }
    const updatedAtElement = document.getElementById('detailsUpdatedAt');
    if (updatedAtElement && campaign.updated_at) {
        updatedAtElement.innerHTML += ` <small class="text-muted">(${getRelativeDate(campaign.updated_at)})</small>`;
    }

    // Status badges
    const statusElement = document.getElementById('detailsCampaignStatus');
    if (statusElement) {
        statusElement.className = `badge ${getStatusBadgeClass(campaign.status)}`;
        statusElement.textContent = (campaign.status || 'unknown').toUpperCase();
    }

    // Metrics
    setElementText('detailsTotalContacts', campaign.total_contacts || campaign.target_contacts_count || 0);
    setElementText('detailsEmailsSent', campaign.sent_emails || campaign.emails_sent || 0);
    setElementText('detailsFailedEmails', campaign.failed_emails || 0);
    setElementText('detailsSuccessRate', `${campaign.success_rate || 0}%`);
    setElementText('detailsResponses', campaign.responses_received || 0);
    setElementText('detailsActiveContacts', campaign.active_contacts || 0);

    // Timeline - show in campaign timezone
    setElementText('detailsFirstEmail', formatDateInTimezone(campaign.first_email_date, campaignTimezone, 'No emails sent yet'));
    setElementText('detailsLastEmail', formatDateInTimezone(campaign.last_email_date, campaignTimezone, 'No emails sent yet'));
    setElementText('detailsUniqueRecipients', campaign.unique_recipients || 0);
    setElementText('detailsTotalEmails', campaign.total_emails || 0);

    // Update campaign action buttons based on status
    updateCampaignActionButtons(campaign);
}

function updateCampaignActionButtons(campaign) {
    const status = campaign.status || 'draft';
    
    // Get button elements
    const launchBtn = document.getElementById('launchCampaignBtn');
    const pauseBtn = document.getElementById('pauseCampaignBtn');
    const resumeBtn = document.getElementById('resumeCampaignBtn');
    const editBtn = document.getElementById('editCampaignBtn');
    const executeNowBtn = document.getElementById('executeNowBtn');
    const resetBtn = document.getElementById('resetCampaignBtn');
    
    // Hide all buttons initially
    [launchBtn, pauseBtn, resumeBtn, editBtn, executeNowBtn, resetBtn].forEach(btn => {
        if (btn) {
            btn.style.display = 'none';
            // Clear any existing onclick handlers
            btn.onclick = null;
        }
    });
    
    // Set onclick handlers with current campaign ID
    const campaignId = campaign.id;
    console.log(`Setting up action buttons for campaign ${campaignId} with status ${status}`);
    
    if (launchBtn) {
        launchBtn.onclick = () => {
            console.log(`Launch button clicked for campaign ${campaignId}`);
            launchCampaign(campaignId);
        };
    }
    if (pauseBtn) {
        pauseBtn.onclick = () => {
            console.log(`Pause button clicked for campaign ${campaignId}`);
            pauseCampaign(campaignId);
        };
    }
    if (resumeBtn) {
        resumeBtn.onclick = () => {
            console.log(`Resume button clicked for campaign ${campaignId}`);
            resumeCampaign(campaignId);
        };
    }
    if (executeNowBtn) {
        executeNowBtn.onclick = () => {
            console.log(`Execute Now button clicked for campaign ${campaignId}`);
            executeCampaignNow(campaignId);
        };
    }
    
    // Show buttons based on campaign status
    if (status === 'draft') {
        if (launchBtn) launchBtn.style.display = 'inline-block';
        if (editBtn) editBtn.style.display = 'inline-block';
    } else if (status === 'active' || status === 'scheduled') {
        if (pauseBtn) pauseBtn.style.display = 'inline-block';
    } else if (status === 'paused') {
        if (resumeBtn) resumeBtn.style.display = 'inline-block';
    }
    
    // Execute Now button - always show for testing purposes
    if (executeNowBtn) {
        executeNowBtn.style.display = 'inline-block';
    }
    
    // Reset button - always show for testing purposes  
    if (resetBtn) {
        resetBtn.onclick = () => {
            console.log(`Reset button clicked for campaign ${campaignId}`);
            resetCampaignForTesting(campaignId);
        };
        resetBtn.style.display = 'inline-block';
    }
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

function getStatusIcon(status) {
    const icons = {
        'active': '<i class="fas fa-play-circle text-success status-icon"></i>',
        'paused': '<i class="fas fa-pause-circle text-warning status-icon"></i>',
        'draft': '<i class="fas fa-edit text-info status-icon"></i>',
        'completed': '<i class="fas fa-check-circle text-secondary status-icon"></i>',
        'scheduled': '<i class="fas fa-clock text-primary status-icon"></i>'
    };
    return icons[status] || '<i class="fas fa-question-circle text-muted status-icon"></i>';
}

function getStatusBadge(status) {
    const badges = {
        'active': '<span class="badge bg-success">Active</span>',
        'paused': '<span class="badge bg-warning">Paused</span>',
        'draft': '<span class="badge bg-info">Draft</span>',
        'completed': '<span class="badge bg-secondary">Completed</span>',
        'scheduled': '<span class="badge bg-primary">Scheduled</span>'
    };
    return badges[status] || '<span class="badge bg-muted">Unknown</span>';
}

function getRelativeDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = now - date;
    const diffSeconds = Math.round(diffTime / 1000);
    const diffMinutes = Math.round(diffSeconds / 60);
    const diffHours = Math.round(diffMinutes / 60);
    const diffDays = Math.round(diffHours / 24);

    if (diffSeconds < 60) return `${diffSeconds}s ago`;
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return `Yesterday`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}


// Add a flag to prevent multiple simultaneous deletions
let isDeletingCampaigns = false;

function deleteAllCampaigns() {
    // Prevent multiple simultaneous executions
    if (isDeletingCampaigns) {
        console.log('Delete already in progress, ignoring duplicate call');
        return;
    }
    
    if (!confirm('Are you sure you want to delete ALL campaigns? This action cannot be undone.')) {
        return;
    }
    
    const deleteBtn = document.getElementById('deleteAllCampaigns');
    if (!deleteBtn) {
        console.error('Delete all campaigns button not found');
        showToast('errorToast', 'Delete button not found');
        return;
    }
    
    // Check if button is already in loading state
    if (deleteBtn.disabled) {
        console.log('Button already disabled, ignoring duplicate call');
        return;
    }
    
    // Set flag and capture original state
    isDeletingCampaigns = true;
    const originalText = deleteBtn.innerHTML;
    console.log('Starting campaign deletion, button original text:', originalText);
    console.log('Button element:', deleteBtn);
    
    deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Deleting...';
    deleteBtn.disabled = true;
    
    // Store button reference in a way that won't get lost
    const buttonToRestore = deleteBtn;
    
    fetch('/api/campaigns/delete-all', {
        method: 'DELETE'
    })
    .then(response => {
        console.log('Delete response status:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Delete response data:', data);
        if (data.success) {
            showToast('successToast', 'All campaigns deleted successfully!');
            
            // Clear any stale campaign state
            currentCampaignDetailsId = null;
            window.lastLoadedCampaigns = [];
            
            // Reload campaigns
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
        console.log('FINALLY block executing - restoring delete button state');
        console.log('buttonToRestore:', buttonToRestore);
        console.log('originalText:', originalText);
        
        try {
            // Always reset the flag
            isDeletingCampaigns = false;
            
            if (buttonToRestore) {
                // Use the captured original text, or fallback to default
                const textToRestore = originalText.includes('spinner') ? 
                    '<i class="fas fa-trash me-1"></i>Delete All' : originalText;
                
                buttonToRestore.innerHTML = textToRestore;
                buttonToRestore.disabled = false;
                console.log('✅ Button state restored successfully to:', textToRestore);
            } else {
                console.error('❌ buttonToRestore is null/undefined');
            }
        } catch (restoreError) {
            console.error('❌ Error restoring button state:', restoreError);
            // Always reset flag even on error
            isDeletingCampaigns = false;
            
            // Fallback: try to find button again
            const fallbackBtn = document.getElementById('deleteAllCampaigns');
            if (fallbackBtn) {
                fallbackBtn.innerHTML = '<i class="fas fa-trash me-1"></i>Delete All';
                fallbackBtn.disabled = false;
                console.log('✅ Fallback button restore successful');
            }
        }
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
    const analyticsContent = document.getElementById('analyticsContent');
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
            console.log('Raw analytics API response:', data);
            if (data.success) {
                console.log('Analytics data being passed to display function:', data.analytics);
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
    try {
        console.log('displayCampaignAnalytics function called with:', analytics, campaignName);
        
        const analyticsContent = document.getElementById('analyticsContent');
        console.log('analyticsContent element found:', analyticsContent);
        
        if (!analyticsContent) {
            console.error('ERROR: analyticsContent element not found!');
            return;
        }
        
        console.log('Displaying analytics:', analytics);
    console.log('Analytics structure check:');
    console.log('- total_clicks:', analytics.total_clicks);
    console.log('- unique_visitors:', analytics.unique_visitors);
    console.log('- unique_clicks:', analytics.unique_clicks);
    console.log('- raw_data:', analytics.raw_data);
    console.log('- raw_data.clicks:', analytics.raw_data?.clicks);
    console.log('- full raw_data structure:', JSON.stringify(analytics.raw_data, null, 2));
    
    // Extract PossibleMinds data - handle multiple possible structures
    let clicks = [];
    if (analytics.raw_data?.clicks) {
        clicks = analytics.raw_data.clicks;
    } else if (analytics.clicks) {
        clicks = analytics.clicks;
    } else if (Array.isArray(analytics.raw_data)) {
        clicks = analytics.raw_data;
    }
    
    console.log('Extracted clicks array:', clicks);
    console.log('Extracted clicks length:', clicks.length);
    console.log('First click object:', clicks[0]);
    
    const totalClicks = analytics.total_clicks || analytics.raw_data?.total_clicks || clicks.length || 0;
    const uniqueVisitors = analytics.unique_visitors || analytics.raw_data?.unique_visitors || 0;
    
    // Calculate unique emails from actual clicks if not provided
    let uniqueEmails = analytics.unique_clicks || analytics.raw_data?.unique_clicks || 0;
    if (uniqueEmails === 0 && clicks.length > 0) {
        const uniqueEmailSet = new Set();
        clicks.forEach(click => {
            const email = click.contact_email || click.recipient;
            if (email) uniqueEmailSet.add(email);
        });
        uniqueEmails = uniqueEmailSet.size;
    }
    
    // Process click data for display
    const companiesData = {};
    const clickDetails = [];
    
    clicks.forEach(click => {
        console.log('Processing click:', click);
        
        // Handle both company formats: "ola_ola" -> "Ola Ola"
        let company = click.company || click.company_slug || 'Unknown';
        if (company.includes('_')) {
            company = company.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
        }
        
        const recipient = click.contact_email || click.recipient || 'Unknown';
        const timestamp = new Date(click.click_timestamp || click.timestamp).toLocaleString();
        const device = getDeviceFromUserAgent(click.user_agent || '');
        const location = getLocationFromIP(click.visitor_ip || click.ip_address || '');
        
        // Count by company
        companiesData[company] = (companiesData[company] || 0) + 1;
        
        // Add to click details
        clickDetails.push({
            timestamp,
            company,
            recipient,
            device,
            location,
            utm_source: click.utm_source || '',
            utm_campaign: click.utm_campaign || '',
            utm_content: click.utm_content || ''
        });
    });
    
    // Sort companies by click count
    const topCompanies = Object.entries(companiesData)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 5);
    
    console.log('Final calculated values:');
    console.log('- totalClicks:', totalClicks);
    console.log('- uniqueEmails:', uniqueEmails);
    console.log('- uniqueVisitors:', uniqueVisitors);
    console.log('- companiesData:', companiesData);
    console.log('- topCompanies:', topCompanies);
    console.log('- clickDetails:', clickDetails);
    
    // Add a debug section to verify data is making it to HTML
    console.log('About to render HTML with these values:');
    console.log('  totalClicks for HTML:', totalClicks);
    console.log('  uniqueEmails for HTML:', uniqueEmails);
    console.log('  topCompanies.length for HTML:', topCompanies.length);
    
    const html = `
        <!-- DEBUG: Testing variable interpolation -->
        <div class="alert alert-info">
            <strong>Debug Info:</strong> 
            totalClicks = ${totalClicks}, 
            uniqueEmails = ${uniqueEmails}, 
            clicksLength = ${clicks.length},
            topCompaniesLength = ${topCompanies.length}
        </div>
        
        <div class="row">
            <!-- Overview Cards -->
            <div class="col-12 mb-4">
                <h5 class="mb-3">Campaign Performance</h5>
                <div class="row g-3">
                    <div class="col-md-3">
                        <div class="card bg-primary text-white">
                            <div class="card-body">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <h6 class="card-subtitle mb-2">Total Contacts</h6>
                                        <h4 class="mb-0">${uniqueEmails || 0}</h4>
                                    </div>
                                    <i class="fas fa-users fa-2x opacity-75"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-success text-white">
                            <div class="card-body">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <h6 class="card-subtitle mb-2">Emails Sent</h6>
                                        <h4 class="mb-0">-</h4>
                                        <small class="opacity-75">External tracking</small>
                                    </div>
                                    <i class="fas fa-paper-plane fa-2x opacity-75"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-info text-white">
                            <div class="card-body">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <h6 class="card-subtitle mb-2">Report Clicks</h6>
                                        <h4 class="mb-0">${totalClicks}</h4>
                                        <small class="opacity-75">${uniqueVisitors} unique</small>
                                    </div>
                                    <i class="fas fa-mouse-pointer fa-2x opacity-75"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card bg-warning text-dark">
                            <div class="card-body">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <h6 class="card-subtitle mb-2">Click Rate</h6>
                                        <h4 class="mb-0">-</h4>
                                        <small class="opacity-75">Need send data</small>
                                    </div>
                                    <i class="fas fa-percentage fa-2x opacity-75"></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Top Companies -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="card-title mb-0"><i class="fas fa-building me-2"></i>Top Engaged Companies</h5>
                    </div>
                    <div class="card-body">
                        ${topCompanies.length > 0 ? 
                            topCompanies.map(([company, count]) => `
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <span class="fw-medium">${company}</span>
                                    <span class="badge bg-primary">${count} click${count > 1 ? 's' : ''}</span>
                                </div>
                            `).join('') :
                            '<p class="text-muted mb-0">No click data available</p>'
                        }
                    </div>
                </div>
            </div>
            
            <!-- Click Details -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="card-title mb-0"><i class="fas fa-mouse-pointer me-2"></i>Recent Clicks</h5>
                    </div>
                    <div class="card-body">
                        ${clickDetails.length > 0 ? 
                            clickDetails.slice(0, 5).map(click => `
                                <div class="border-bottom pb-2 mb-2">
                                    <div class="d-flex justify-content-between">
                                        <span class="fw-medium">${click.company}</span>
                                        <small class="text-muted">${click.timestamp}</small>
                                    </div>
                                    <small class="text-muted">${click.recipient}</small>
                                    ${click.device ? `<br><small class="text-info">${click.device}</small>` : ''}
                                    ${click.location ? `<br><small class="text-success">${click.location}</small>` : ''}
                                </div>
                            `).join('') :
                            '<p class="text-muted mb-0">No click data available</p>'
                        }
                    </div>
                </div>
            </div>
        </div>
        
        ${totalClicks === 0 ? `
            <div class="text-center py-4 mt-4">
                <i class="fas fa-chart-line fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Click Data Available</h5>
                <p class="text-muted">Click analytics from PossibleMinds will appear here once recipients interact with campaign reports.</p>
                <small class="text-muted">Data source: ${analytics.source || 'possibleminds'}</small>
            </div>
        ` : `
            <div class="text-center mt-4">
                <small class="text-muted">Analytics powered by ${analytics.source || 'PossibleMinds'} • ${totalClicks} total clicks tracked</small>
            </div>
        `}
    `;
    
    console.log('Setting analyticsContent.innerHTML with generated HTML');
    analyticsContent.innerHTML = html;
    console.log('Analytics display completed successfully');
    
    } catch (error) {
        console.error('ERROR in displayCampaignAnalytics:', error);
        console.error('Error stack:', error.stack);
        // Fallback error display
        const analyticsContent = document.getElementById('analyticsContent');
        if (analyticsContent) {
            analyticsContent.innerHTML = `
                <div class="alert alert-danger">
                    <h5>Analytics Display Error</h5>
                    <p>Error: ${error.message}</p>
                    <pre>${error.stack}</pre>
                </div>
            `;
        }
    }
}

function launchCampaign(campaignId) {
    console.log(`Launching campaign: ${campaignId}`);
    if (confirm('Are you sure you want to launch this campaign? This will start sending emails to the selected contacts.')) {
        // Show loading state
        const launchBtn = document.querySelector(`[onclick="launchCampaign(${campaignId})"]`);
        const originalText = launchBtn?.innerHTML;
        if (launchBtn) {
            launchBtn.disabled = true;
            launchBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Launching...';
        }
        
        fetch(`/api/campaigns/${campaignId}/launch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('successToast', `🚀 ${data.message}`);
                
                // Refresh campaign data after launch
                setTimeout(() => {
                    loadCampaigns();
                    if (currentCampaignDetailsId == campaignId) {
                        viewCampaignDetails(campaignId);
                    }
                }, 2000);
                
            } else {
                showToast('errorToast', data.message || 'Failed to launch campaign');
            }
        })
        .catch(error => {
            console.error('Error launching campaign:', error);
            showToast('errorToast', 'An error occurred while launching the campaign');
        })
        .finally(() => {
            // Restore button state
            if (launchBtn && originalText) {
                launchBtn.disabled = false;
                launchBtn.innerHTML = originalText;
            }
        });
    }
}

function pauseCampaign(campaignId) {
    console.log(`Pausing campaign: ${campaignId}`);
    if (confirm('Are you sure you want to pause this campaign?')) {
        // Show loading state
        const pauseBtn = document.querySelector(`[onclick="pauseCampaign(${campaignId})"]`);
        const originalText = pauseBtn?.innerHTML;
        if (pauseBtn) {
            pauseBtn.disabled = true;
            pauseBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Pausing...';
        }
        
        fetch(`/api/campaigns/${campaignId}/pause`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('successToast', `⏸️ ${data.message}`);
                
                // Refresh campaign data after pause
                setTimeout(() => {
                    loadCampaigns();
                    if (currentCampaignDetailsId == campaignId) {
                        viewCampaignDetails(campaignId);
                    }
                }, 1000);
                
            } else {
                showToast('errorToast', data.message || 'Failed to pause campaign');
            }
        })
        .catch(error => {
            console.error('Error pausing campaign:', error);
            showToast('errorToast', 'An error occurred while pausing the campaign');
        })
        .finally(() => {
            // Restore button state
            if (pauseBtn && originalText) {
                pauseBtn.disabled = false;
                pauseBtn.innerHTML = originalText;
            }
        });
    }
}

function resumeCampaign(campaignId) {
    console.log(`Resuming campaign: ${campaignId}`);
    if (confirm('Are you sure you want to resume this campaign?')) {
        // Show loading state
        const resumeBtn = document.querySelector(`[onclick="resumeCampaign(${campaignId})"]`);
        const originalText = resumeBtn?.innerHTML;
        if (resumeBtn) {
            resumeBtn.disabled = true;
            resumeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Resuming...';
        }
        
        fetch(`/api/campaigns/${campaignId}/resume`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('successToast', `▶️ ${data.message}`);
                
                // Refresh campaign data after resume
                setTimeout(() => {
                    loadCampaigns();
                    if (currentCampaignDetailsId == campaignId) {
                        viewCampaignDetails(campaignId);
                    }
                }, 1000);
                
            } else {
                showToast('errorToast', data.message || 'Failed to resume campaign');
            }
        })
        .catch(error => {
            console.error('Error resuming campaign:', error);
            showToast('errorToast', 'An error occurred while resuming the campaign');
        })
        .finally(() => {
            // Restore button state
            if (resumeBtn && originalText) {
                resumeBtn.disabled = false;
                resumeBtn.innerHTML = originalText;
            }
        });
    }
}

// Helper function to extract device info from user agent
function getDeviceFromUserAgent(userAgent) {
    if (!userAgent) return 'Unknown';
    
    const ua = userAgent.toLowerCase();
    if (ua.includes('mobile') || ua.includes('android') || ua.includes('iphone')) {
        return 'Mobile';
    } else if (ua.includes('ipad') || ua.includes('tablet')) {
        return 'Tablet';
    } else if (ua.includes('macintosh') || ua.includes('windows') || ua.includes('linux')) {
        return 'Desktop';
    } else {
        return 'Unknown';
    }
}

// Helper function to extract location from IP
function getLocationFromIP(ipAddress) {
    if (!ipAddress) return 'Unknown';
    
    // Handle comma-separated IPs (take the first real IP, skip proxies)
    if (ipAddress.includes(',')) {
        const ips = ipAddress.split(',').map(ip => ip.trim());
        // Take the first IP that's not a common proxy/CDN IP
        ipAddress = ips.find(ip => !ip.startsWith('18.') && !ip.startsWith('172.')) || ips[0];
    }
    
    // For now, just return the IP address  
    // In a real implementation, you'd use a geolocation service
    return ipAddress;
}

function executeCampaignNow(campaignId) {
    if (!confirm('⚠️ TEST MODE: This will execute the campaign IMMEDIATELY bypassing all time delays and business hour restrictions.\n\nAre you sure you want to proceed?')) {
        return;
    }
    
    console.log('🚀 TEST MODE: Executing campaign immediately:', campaignId);
    
    // Show loading state
    const executeBtn = document.getElementById('executeNowBtn') || document.querySelector(`[onclick="executeCampaignNow(${campaignId})"]`);
    const originalText = executeBtn?.innerHTML;
    if (executeBtn) {
        executeBtn.disabled = true;
        executeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Executing...';
    }
    
    fetch(`/api/campaigns/${campaignId}/execute-now`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `🚀 ${data.message}`);
            
            // Show additional info toast
            setTimeout(() => {
                showToast('successToast', '📧 Check the logs and email history for execution progress!');
            }, 2000);
            
            // Refresh campaign data after a short delay to see the results
            setTimeout(() => {
                loadCampaigns();
                if (currentCampaignDetailsId == campaignId) {
                    viewCampaignDetails(campaignId);
                }
            }, 3000);
            
        } else {
            showToast('errorToast', data.message || 'Failed to execute campaign immediately');
        }
    })
    .catch(error => {
        console.error('Error executing campaign immediately:', error);
        showToast('errorToast', 'An error occurred while executing the campaign');
    })
    .finally(() => {
        // Restore button state
        if (executeBtn && originalText) {
            executeBtn.disabled = false;
            executeBtn.innerHTML = originalText;
        }
    });
}

function resetCampaignForTesting(campaignId) {
    if (!confirm('🔄 TEST MODE: This will reset all campaign contacts back to "active" status, allowing you to re-test the campaign execution.\n\nThis will:\n- Reset all contacts to "active" status\n- Set campaign status to "ready"\n- Allow re-execution of the same campaign\n\nAre you sure you want to proceed?')) {
        return;
    }
    
    console.log('🔄 TEST MODE: Resetting campaign for testing:', campaignId);
    
    // Show loading state
    const resetBtn = document.getElementById('resetCampaignBtn') || document.querySelector(`[onclick="resetCampaignForTesting(${campaignId})"]`);
    const originalText = resetBtn?.innerHTML;
    if (resetBtn) {
        resetBtn.disabled = true;
        resetBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Resetting...';
    }
    
    fetch(`/api/campaigns/${campaignId}/reset`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `🔄 ${data.message}`);
            
            // Show additional info about what was reset
            if (data.reset_count > 0) {
                setTimeout(() => {
                    showToast('successToast', `📊 ${data.reset_count} contacts reset to active status. Campaign ready for re-testing!`);
                }, 2000);
            }
            
            // Refresh campaign data to show updated stats
            setTimeout(() => {
                loadCampaigns();
                if (currentCampaignDetailsId == campaignId) {
                    viewCampaignDetails(campaignId);
                }
            }, 3000);
            
        } else {
            showToast('errorToast', data.message || 'Failed to reset campaign for testing');
        }
    })
    .catch(error => {
        console.error('Error resetting campaign for testing:', error);
        showToast('errorToast', 'An error occurred while resetting the campaign');
    })
    .finally(() => {
        // Restore button state
        if (resetBtn && originalText) {
            resetBtn.disabled = false;
            resetBtn.innerHTML = originalText;
        }
    });
}

// Helper function to format a date string into a more readable format in a specific timezone.
function formatDateInTimezone(dateString, timeZone, format = 'long') {
    if (!dateString) {
        return 'N/A';
    }
    try {
        const date = new Date(dateString);
        const options = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            timeZoneName: 'short',
            timeZone: timeZone,
        };
        return new Intl.DateTimeFormat('en-US', options).format(date);
    } catch (e) {
        console.error(`Error formatting date: ${e}`);
        return dateString; // Fallback to original string
    }
}

function viewCampaignSchedule(campaignId, campaignName) {
    console.log('Loading campaign schedule for:', campaignId, campaignName);

    // Get campaign data to access timezone
    const campaignData = getCurrentCampaignData(campaignId);
    const campaignTimezone = campaignData ? getCampaignTimezone(campaignData) : 'UTC'; // Default to UTC

    // Show the schedule modal immediately with loading state
    const modal = new bootstrap.Modal(document.getElementById('campaignScheduleModal'));
    modal.show();

    // Set modal title
    const titleElement = document.getElementById('campaignScheduleTitle');
    if (titleElement) {
        titleElement.textContent = `${campaignName} - Schedule`;
    }

    // Set loading state for schedule content
    const scheduleContent = document.getElementById('scheduleContent');
    if (scheduleContent) {
        scheduleContent.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading schedule...</p>
            </div>
        `;
    }

    // Fetch schedule data
    fetch(`/api/campaigns/${campaignId}/schedule`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayCampaignSchedule(data, campaignName, campaignId, campaignTimezone);
            } else {
                throw new Error(data.message || 'Failed to load schedule');
            }
        })
        .catch(error => {
            console.error('Error loading campaign schedule:', error);
            if (scheduleContent) {
                scheduleContent.innerHTML = `
                    <div class="text-center py-4">
                        <i class="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                        <h5 class="text-danger">Failed to Load Schedule</h5>
                        <p class="text-muted">${error.message}</p>
                        <button class="btn btn-outline-primary" onclick="viewCampaignSchedule(${campaignId}, '${campaignName.replace(/'/g, '&apos;')}')">
                            <i class="fas fa-refresh me-2"></i>Retry
                        </button>
                    </div>
                `;
            }
        });
}

function displayCampaignSchedule(scheduleData, campaignName, campaignId, timeZone) {
    const scheduleContent = document.getElementById('scheduleContent');
    if (!scheduleContent) {
        console.error('scheduleContent element not found');
        return;
    }

    const pendingEmails = scheduleData.pending_emails || [];
    const sentEmails = scheduleData.sent_emails || [];

    const renderTable = (title, emails, isPending) => {
        let rows = '';
        if (emails.length === 0) {
            rows = '<tr><td colspan="4" class="text-center text-muted">No emails in this category.</td></tr>';
        } else {
            emails.forEach(job => {
                const time = isPending ? job.scheduled_time : job.sent_time;
                const formattedTime = formatDateInTimezone(time, timeZone);
                const relativeTime = getRelativeDate(time);
                const statusBadge = getStatusBadge(job.status);
                
                rows += `
                    <tr>
                        <td>${job.recipient_email}</td>
                        <td>${formattedTime}</td>
                        <td>${relativeTime}</td>
                        <td>${statusBadge}</td>
                    </tr>
                `;
            });
        }

        return `
            <div class="mb-4">
                <h5 class="mb-3">${title} (${emails.length})</h5>
                <div class="table-responsive">
                    <table class="table table-sm table-striped table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>Contact</th>
                                <th>${isPending ? 'Scheduled Time' : 'Sent Time'}</th>
                                <th>Relative Time</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    };

    scheduleContent.innerHTML = `
        ${renderTable('Pending Emails', pendingEmails, true)}
        ${renderTable('Sent Emails', sentEmails, false)}
    `;
}


function initializeCampaignSchedule(campaignId) {
    // Store current campaign ID for auto-refresh
    window.currentScheduleCampaignId = campaignId;
    
    // Load initial schedule data
    loadCampaignScheduleData(campaignId);
    
    // Set up auto-refresh every 30 seconds
    if (window.scheduleRefreshInterval) {
        clearInterval(window.scheduleRefreshInterval);
    }
    
    window.scheduleRefreshInterval = setInterval(() => {
        if (window.currentScheduleCampaignId) {
            loadCampaignScheduleData(window.currentScheduleCampaignId);
        }
    }, 30000); // 30 seconds
    
    // Clear interval when modal is closed
    const modal = document.getElementById('campaignScheduleModal');
    if (modal) {
        modal.addEventListener('hidden.bs.modal', () => {
            if (window.scheduleRefreshInterval) {
                clearInterval(window.scheduleRefreshInterval);
                window.scheduleRefreshInterval = null;
            }
            window.currentScheduleCampaignId = null;
        });
    }
}

function loadCampaignScheduleData(campaignId) {
    fetch(`/api/campaigns/${campaignId}/schedule`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayCampaignSchedule(data);
            } else {
                throw new Error(data.error || 'Failed to load schedule');
            }
        })
        .catch(error => {
            console.error('Error loading campaign schedule:', error);
            const scheduleContent = document.getElementById('scheduleContent');
            if (scheduleContent) {
                scheduleContent.innerHTML = `
                    <div class="text-center py-4">
                        <i class="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                        <h5 class="text-danger">Failed to Load Schedule</h5>
                        <p class="text-muted">${error.message}</p>
                        <button class="btn btn-outline-primary" onclick="loadCampaignScheduleData(${campaignId})">
                            <i class="fas fa-refresh me-2"></i>Retry
                        </button>
                    </div>
                `;
            }
        });
}

function displayCampaignSchedule(data) {
    const scheduleContent = document.getElementById('scheduleContent');
    if (!scheduleContent) return;
    
    const { campaign, pending_emails, sent_emails, stats } = data;
    
    // Debug: Log campaign data to see timezone info
    console.log('Campaign data received:', campaign);
    console.log('Campaign timezone setting:', campaign.timezone);
    
    let html = `
        <!-- Campaign Overview -->
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-info-circle me-2"></i>Campaign Overview
                </h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <table class="table table-sm">
                            <tr><th>Status:</th><td><span class="badge bg-${getStatusColor(campaign.status)}">${campaign.status || 'Draft'}</span></td></tr>
                            <tr><th>Total Contacts:</th><td>${stats.total_contacts || 0}</td></tr>
                            <tr><th>Emails Sent:</th><td>${stats.emails_sent || 0}</td></tr>
                            <tr><th>Pending Emails:</th><td>${stats.pending_emails || 0}</td></tr>
                        </table>
                    </div>
                    <div class="col-md-6">
                        <table class="table table-sm">
                            <tr><th>Daily Limit:</th><td>${getCampaignDailyLimit(campaign)} emails</td></tr>
                            <tr><th>Frequency:</th><td>${getCampaignFrequency(campaign)}</td></tr>
                            <tr><th>Timezone:</th><td>${getTimezoneDisplayName(getCampaignTimezone(campaign))}</td></tr>
                            <tr><th>Business Hours:</th><td>${getCampaignBusinessHours(campaign)}</td></tr>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Pending Emails -->
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-clock me-2"></i>Pending Emails (${pending_emails?.length || 0})
                </h5>
            </div>
            <div class="card-body">
    `;
    
    if (pending_emails && pending_emails.length > 0) {
        html += `
            <div class="table-responsive">
                <table class="table table-hover table-sm">
                    <thead class="table-light">
                        <tr>
                            <th>Contact</th>
                            <th>Scheduled Time</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        pending_emails.slice(0, 50).forEach(email => {
            const scheduledTime = new Date(email.scheduled_time);
            let campaignTimezone = getCampaignTimezone(campaign);
            
            // Remove legacy UTC fallback - use actual campaign timezone
            console.log('Campaign timezone for email display:', campaignTimezone);
            
            // Format time in campaign timezone if available
            let timeFormatted;
            try {
                timeFormatted = scheduledTime.toLocaleString('en-US', {
                    timeZone: campaignTimezone,
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZoneName: 'short'
                });
            } catch (e) {
                console.error('Timezone formatting error:', e);
                // Fallback if timezone is invalid
                timeFormatted = scheduledTime.toLocaleString() + ` (${campaignTimezone})`;
            }
            
            const isToday = scheduledTime.toDateString() === new Date().toDateString();
            const isNext24Hours = scheduledTime.getTime() - Date.now() < 24 * 60 * 60 * 1000 && scheduledTime > new Date();
            
            html += `
                <tr class="${isToday ? 'table-warning' : isNext24Hours ? 'table-info' : ''}">
                    <td>${email.contact_email}</td>
                    <td>
                        ${timeFormatted}
                        ${isToday ? '<span class="badge bg-info ms-2">Today</span>' : ''}
                        ${isNext24Hours && !isToday ? '<span class="badge bg-warning ms-2">Next 24h</span>' : ''}
                    </td>
                    <td><span class="badge bg-secondary">${email.status || 'Pending'}</span></td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        if (pending_emails.length > 50) {
            html += `<p class="text-muted text-center mt-2">Showing first 50 of ${pending_emails.length} pending emails</p>`;
        }
    } else {
        html += `<p class="text-muted text-center py-3">No pending emails</p>`;
    }
    
    html += `
            </div>
        </div>
        
        <!-- Recent Sent Emails -->
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-paper-plane me-2"></i>Recent Sent Emails (${sent_emails?.length || 0})
                </h5>
            </div>
            <div class="card-body">
    `;
    
    if (sent_emails && sent_emails.length > 0) {
        html += `
            <div class="table-responsive">
                <table class="table table-hover table-sm">
                    <thead class="table-light">
                        <tr>
                            <th>Contact</th>
                            <th>Sent Time</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        sent_emails.slice(0, 20).forEach(email => {
            const sentTime = new Date(email.date || email.sent_time);
            const campaignTimezone = getCampaignTimezone(campaign);
            
            // Format time in campaign timezone
            let timeFormatted;
            try {
                timeFormatted = sentTime.toLocaleString('en-US', {
                    timeZone: campaignTimezone,
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZoneName: 'short'
                });
            } catch (e) {
                // Fallback if timezone is invalid
                timeFormatted = sentTime.toLocaleString() + ` (${campaignTimezone})`;
            }
            
            const statusColor = email.status === 'sent' ? 'success' : email.status === 'failed' ? 'danger' : 'secondary';
            
            html += `
                <tr>
                    <td>${email.to || email.contact_email}</td>
                    <td>${timeFormatted}</td>
                    <td><span class="badge bg-${statusColor}">${email.status || 'Unknown'}</span></td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
    } else {
        html += `<p class="text-muted text-center py-3">No emails sent yet</p>`;
    }
    
    html += `
            </div>
        </div>
        
        <div class="text-center mt-3">
            <small class="text-muted">Auto-refreshes every 30 seconds</small>
        </div>
    `;
    
    scheduleContent.innerHTML = html;
}

function getStatusColor(status) {
    const colors = {
        'active': 'success',
        'paused': 'warning',
        'draft': 'info',
        'completed': 'secondary',
        'scheduled': 'primary'
    };
    return colors[status] || 'secondary';
}

// Helper function to extract timezone from campaign settings
function getCampaignTimezone(campaign) {
    try {
        if (campaign.campaign_settings) {
            const settings = typeof campaign.campaign_settings === 'string' 
                ? JSON.parse(campaign.campaign_settings) 
                : campaign.campaign_settings;
            return settings.timezone || 'America/Los_Angeles';
        }
        return campaign.timezone || 'America/Los_Angeles';
    } catch (error) {
        console.warn('Error parsing campaign settings for timezone:', error);
        return 'America/Los_Angeles';
    }
}

// Helper function to extract email frequency from campaign settings
function getCampaignFrequency(campaign) {
    try {
        if (campaign.campaign_settings) {
            const settings = typeof campaign.campaign_settings === 'string' 
                ? JSON.parse(campaign.campaign_settings) 
                : campaign.campaign_settings;
            
            if (settings.email_frequency) {
                const freq = settings.email_frequency;
                return `${freq.value} ${freq.unit}`;
            }
        }
        return 'N/A';
    } catch (error) {
        console.warn('Error parsing campaign settings for frequency:', error);
        return 'N/A';
    }
}

// Helper function to extract daily limit from campaign settings
function getCampaignDailyLimit(campaign) {
    try {
        if (campaign.campaign_settings) {
            const settings = typeof campaign.campaign_settings === 'string' 
                ? JSON.parse(campaign.campaign_settings) 
                : campaign.campaign_settings;
            return settings.daily_email_limit || 50;
        }
        return campaign.daily_email_limit || 50;
    } catch (error) {
        console.warn('Error parsing campaign settings for daily limit:', error);
        return 50;
    }
}

// Helper function to extract business hours setting from campaign settings
function getCampaignBusinessHours(campaign) {
    try {
        if (campaign.campaign_settings) {
            const settings = typeof campaign.campaign_settings === 'string' 
                ? JSON.parse(campaign.campaign_settings) 
                : campaign.campaign_settings;
            return settings.respect_business_hours ? 'Enabled' : 'Disabled';
        }
        return campaign.respect_business_hours ? 'Enabled' : 'Disabled';
    } catch (error) {
        console.warn('Error parsing campaign settings for business hours:', error);
        return 'Disabled';
    }
}

function getTimezoneDisplayName(timezone) {
    const timezoneNames = {
        'Pacific/Honolulu': 'Hawaii Time (HST)',
        'America/Anchorage': 'Alaska Time (AKST/AKDT)',
        'America/Los_Angeles': 'Pacific Time (PST/PDT)',
        'America/Phoenix': 'Arizona Time (MST - No DST)',
        'America/Denver': 'Mountain Time (MST/MDT)',
        'America/Chicago': 'Central Time (CST/CDT)',
        'America/New_York': 'Eastern Time (EST/EDT)',
        'America/Halifax': 'Atlantic Time (AST/ADT)',
        'UTC': 'Coordinated Universal Time (UTC)',
        'Europe/London': 'London Time (GMT/BST)',
        'Europe/Paris': 'Paris Time (CET/CEST)',
        'Asia/Kolkata': 'India Standard Time (IST)',
        'Asia/Tokyo': 'Tokyo Time (JST)',
        'Asia/Shanghai': 'Shanghai Time (CST)',
        'Australia/Sydney': 'Sydney Time (AEST/AEDT)'
    };
    return timezoneNames[timezone] || timezone;
}

function duplicateCampaign(campaignId, campaignName) {
    if (!confirm(`Are you sure you want to duplicate the campaign "${campaignName}"?`)) {
        return;
    }
    
    console.log(`Duplicating campaign ${campaignId}: ${campaignName}`);
    
    // Show loading state
    const loadingToast = showToast('infoToast', 'Duplicating campaign...', 5000);
    
    fetch(`/api/campaigns/${campaignId}/duplicate`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', data.message);
            
            // Reload campaigns list to show the duplicated campaign
            setTimeout(() => {
                loadCampaigns();
            }, 1500);
        } else {
            throw new Error(data.message || 'Failed to duplicate campaign');
        }
    })
    .catch(error => {
        console.error('Error duplicating campaign:', error);
        showToast('errorToast', 'Failed to duplicate campaign: ' + error.message);
    });
}

function deleteSingleCampaign(campaignId, campaignName) {
    // Enhanced confirmation dialog with warning about pending emails
    const confirmMessage = `⚠️ WARNING: This will permanently delete the campaign "${campaignName}" and all associated data including:

• All pending email jobs
• Email history records
• Contact associations
• Analytics data

This action cannot be undone. Are you absolutely sure you want to proceed?`;
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    // Second confirmation for extra safety
    const secondConfirm = prompt(`To confirm deletion, please type the campaign name: "${campaignName}"`);
    if (secondConfirm !== campaignName) {
        showToast('errorToast', 'Campaign name does not match. Deletion cancelled.');
        return;
    }
    
    console.log(`Deleting campaign ${campaignId}: ${campaignName}`);
    
    // Show loading state
    showToast('infoToast', 'Deleting campaign and all associated data...', 8000);
    
    fetch(`/api/campaigns/${campaignId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('successToast', `Campaign "${campaignName}" deleted successfully.`);
            
            // Reload campaigns list to reflect the deletion
            setTimeout(() => {
                loadCampaigns();
            }, 1500);
        } else {
            throw new Error(data.message || data.error || 'Failed to delete campaign');
        }
    })
    .catch(error => {
        console.error('Error deleting campaign:', error);
        showToast('errorToast', 'Failed to delete campaign: ' + error.message);
    });
}

// Global function assignments for HTML onclick handlers
window.nextStep = nextStep;
window.previousStep = previousStep;
window.launchCampaign = launchCampaign;
window.pauseCampaign = pauseCampaign;
window.resumeCampaign = resumeCampaign;
window.executeCampaignNow = executeCampaignNow;
window.handleSelectionMethodChange = handleSelectionMethodChange;
window.toggleContactSelection = toggleContactSelection;
window.searchContactsForCampaign = searchContactsForCampaign;
window.clearCampaignSearch = clearCampaignSearch;
window.saveCampaignDraft = saveCampaignDraft;
window.updateContactCount = updateContactCount;
window.viewCampaignDetails = viewCampaignDetails;
window.viewCampaignAnalytics = viewCampaignAnalytics;
window.viewCampaignSchedule = viewCampaignSchedule;
window.launchCampaign = launchCampaign;
window.pauseCampaign = pauseCampaign;
window.resumeCampaign = resumeCampaign;
window.resetCampaignForTesting = resetCampaignForTesting;
window.deleteAllCampaigns = deleteAllCampaigns;
window.duplicateCampaign = duplicateCampaign;
window.deleteSingleCampaign = deleteSingleCampaign;