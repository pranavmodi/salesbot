// Deep Research Modal functionality
(function() {
    'use strict';
    
    let currentResearchCompanyId = null;
    let researchProgressInterval = null;
    let isResearchInProgress = false;

    document.addEventListener('DOMContentLoaded', function() {
        console.log("Deep research functionality loaded.");
        
        // Initialize deep research modal event listeners
        initializeDeepResearchModal();

        // Delegated event listener for Deep Research buttons
        document.body.addEventListener('click', function(event) {
            const button = event.target.closest('.deep-research-btn');
            if (button) {
                event.preventDefault();
                const companyId = button.dataset.companyId;
                const companyName = button.dataset.companyName;

                console.log(`🚨 BUTTON CLICK: Deep Research button clicked for: ${companyName} (${companyId})`);
                
                if (!companyId) {
                    console.error('🚨 ERROR: No company ID found on deep research button');
                    alert('Error: No company ID found. Please refresh the page and try again.');
                    return;
                }
                
                openDeepResearchModal(companyId, companyName);
            }
        });
    });

    function initializeDeepResearchModal() {
        // Action button event listeners
        document.getElementById('startDeepResearchBtn')?.addEventListener('click', startDeepResearch);
        document.getElementById('forceRefreshDeepBtn')?.addEventListener('click', () => startDeepResearch(true));
        document.getElementById('resumeDeepResearchBtn')?.addEventListener('click', resumeDeepResearch);
        document.getElementById('stopResearchBtn')?.addEventListener('click', stopResearch);
        document.getElementById('viewStrategicReportBtn')?.addEventListener('click', viewStrategicReport);
        document.getElementById('publishReportBtn')?.addEventListener('click', publishReport);

        // Research type selection event listeners
        document.querySelectorAll('.research-type-card').forEach(card => {
            card.addEventListener('click', function() {
                const radio = this.querySelector('input[type="radio"]');
                if (radio) {
                    radio.checked = true;
                    updateResearchTypeSelection();
                }
            });
        });

        document.querySelectorAll('input[name="researchType"]').forEach(radio => {
            radio.addEventListener('change', updateResearchTypeSelection);
        });

        // Initialize research type selection
        updateResearchTypeSelection();

        // Modal focus and accessibility management
        const modal = document.getElementById('deepResearchModal');
        if (modal) {
            // Allow modal to close even during research - background jobs continue running
            modal.addEventListener('hide.bs.modal', function(event) {
                // No longer prevent closing - background jobs are safe to continue
                // User can check progress by reopening the modal
            });
            
            // Cleanup when modal is actually closed
            modal.addEventListener('hidden.bs.modal', function() {
                if (researchProgressInterval) {
                    clearInterval(researchProgressInterval);
                    researchProgressInterval = null;
                }
                currentResearchCompanyId = null;
                isResearchInProgress = false;
            });

            // Ensure proper focus management when modal shows
            modal.addEventListener('shown.bs.modal', function() {
                modal.removeAttribute('aria-hidden');
                modal.setAttribute('aria-modal', 'true');
            });
        }
    }

    function openDeepResearchModal(companyId, companyName) {
        console.log(`🚨 MODAL OPENED: Deep Research modal opened for company ${companyName} (ID: ${companyId})`);
        currentResearchCompanyId = companyId;
        
        // Update modal title
        const modalTitle = document.getElementById('deepResearchCompanyName');
        if (modalTitle) {
            modalTitle.textContent = companyName;
        }

        // Reset modal state
        resetModalState();

        // Load current research progress (this could potentially trigger research)
        console.log(`🚨 LOADING PROGRESS: About to load research progress - this should NOT trigger new research`);
        loadResearchProgress(companyId);

        // Show modal
        const modalElement = document.getElementById('deepResearchModal');
        if (modalElement) {
            const bsModal = new bootstrap.Modal(modalElement);
            bsModal.show();
        }
    }

    function resetModalState() {
        // Reset progress display
        const progressContainer = document.getElementById('deepResearchProgress');
        if (progressContainer) {
            progressContainer.innerHTML = `
                <div class="d-flex justify-content-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading progress...</span>
                    </div>
                </div>
            `;
        }

        // Reset steps
        const stepsContainer = document.getElementById('deepResearchSteps');
        if (stepsContainer) {
            stepsContainer.innerHTML = '';
        }

        // Hide log
        const logContainer = document.getElementById('deepResearchLog');
        if (logContainer) {
            logContainer.style.display = 'none';
        }

        // Hide publish status
        hidePublishStatus();

        // Reset action buttons
        updateActionButtons('loading');
    }

    function loadResearchProgress(companyId) {
        // Determine which research type is selected to use the correct endpoint
        const selectedResearchType = getSelectedResearchType();
        const progressUrl = getProgressUrl(selectedResearchType);
        
        console.log(`🚨 PROGRESS CHECK: Loading progress from ${progressUrl} - this is READ-ONLY, should NOT trigger research`);
        
        fetch(progressUrl)
            .then(response => response.json())
            .then(data => {
                console.log(`🚨 PROGRESS LOADED: Research progress loaded for company ${companyId}:`, data);
                displayResearchProgress(data);
            })
            .catch(error => {
                console.error(`🚨 PROGRESS ERROR: Error loading research progress for company ${companyId}:`, error);
                showError('Failed to load research progress');
            });
    }

    function displayResearchProgress(data) {
        console.log(`🚨 PROGRESS DISPLAY: Displaying progress data for company ${currentResearchCompanyId}:`, data);
        
        // Handle the actual response structure from the API
        if (!data.success) {
            console.error(`🚨 PROGRESS ERROR: Failed to display progress for company ${currentResearchCompanyId}:`, data.error);
            showError(data.error || 'Failed to load research progress');
            return;
        }
        
        // Determine if this is LLM research or standard research
        const selectedResearchType = getSelectedResearchType();
        const isLLMResearch = selectedResearchType === 'llm_step_by_step';
        
        let status;
        if (isLLMResearch) {
            // LLM research has different status structure - use research_status as primary
            status = data.research_status || 'pending';
            
            // Override only for specific cases
            if (data.current_step === 'completed' || data.is_complete) {
                status = 'completed';
            } else if (data.current_status && data.current_status.includes('error')) {
                status = 'failed';
            } else if (data.current_status && (
                data.current_status.includes('background_job_running') || 
                data.current_status.includes('Background research') ||
                data.current_status.includes('Research session created') ||
                data.current_status.includes('OpenAI research queued') ||
                data.current_status.includes('OpenAI research in_progress') ||
                data.current_status.includes('Executing step') ||
                data.current_status.includes('research queued') ||
                data.current_status.includes('research in_progress') ||
                data.research_status === 'in_progress'
            )) {
                status = 'in_progress';
            }
        } else {
            status = data.research_status || 'pending';
        }
        
        console.log(`🚨 STATUS DETERMINED: Status for company ${currentResearchCompanyId} determined as: ${status}`);
        
        // Update company URL (we'll need to get it from the company details separately)
        const urlElement = document.getElementById('deepResearchCompanyUrl');
        if (urlElement) {
            urlElement.textContent = ''; // We'll populate this from company details if needed
        }

        // Always display LLM research progress using new dynamic functions
        displayProgressBar(data);
        displayResearchSteps(data);
        
        updateActionButtons(status, data);

        // Start polling if research is in progress
        if (status === 'in_progress') {
            console.log(`🚨 POLLING START: Starting progress polling for in-progress research on company ${currentResearchCompanyId}`);
            isResearchInProgress = true;
            startProgressPolling();
            showResearchLog();
        } else {
            console.log(`🚨 NO POLLING: Research not in progress for company ${currentResearchCompanyId}, status: ${status}`);
            
            // If status is pending but user might expect research to be running, show helpful message
            if (status === 'pending' && data.current_status && data.current_status !== 'not_started') {
                addLogMessage(`🚨 STATUS INFO: Research status is pending. Current status: ${data.current_status}. Click 'Start Deep Research' to begin.`);
            }
            
            // Reset research in progress flag if not actually in progress
            isResearchInProgress = false;
        }
    }


    function updateActionButtons(status, data = null) {
        console.log(`🚨 BUTTON UPDATE: Updating action buttons for company ${currentResearchCompanyId} with status: ${status}`);
        
        const startBtn = document.getElementById('startDeepResearchBtn');
        const forceBtn = document.getElementById('forceRefreshDeepBtn');
        const resumeBtn = document.getElementById('resumeDeepResearchBtn');
        const stopBtn = document.getElementById('stopResearchBtn');
        const viewReportBtn = document.getElementById('viewStrategicReportBtn');
        const reportFormatButtons = document.getElementById('reportFormatButtons');
        const publishBtn = document.getElementById('publishReportBtn');

        // Hide all buttons first and re-enable them (in case they were disabled)
        [startBtn, forceBtn, resumeBtn, stopBtn, viewReportBtn, publishBtn].forEach(btn => {
            if (btn) {
                btn.style.display = 'none';
                btn.disabled = false;
                btn.classList.remove('disabled');
            }
        });

        // Hide report format buttons
        if (reportFormatButtons) reportFormatButtons.style.display = 'none';

        switch (status) {
            case 'loading':
                console.log(`🚨 BUTTON STATE: Loading state - no action buttons shown`);
                // Show loading state
                break;
            case 'pending':
                console.log(`🚨 BUTTON STATE: Pending state - showing START button for company ${currentResearchCompanyId}`);
                if (startBtn) startBtn.style.display = 'inline-block';
                break;
            case 'in_progress':
                console.log(`🚨 BUTTON STATE: In-progress state - showing STOP button for company ${currentResearchCompanyId}`);
                if (stopBtn) stopBtn.style.display = 'inline-block';
                break;
            case 'completed':
                console.log(`🚨 BUTTON STATE: Completed state - showing FORCE REFRESH and REPORT buttons for company ${currentResearchCompanyId}`);
                if (forceBtn) forceBtn.style.display = 'inline-block';
                if (viewReportBtn) viewReportBtn.style.display = 'inline-block';
                if (reportFormatButtons) reportFormatButtons.style.display = 'inline-block';
                if (publishBtn) publishBtn.style.display = 'inline-block';
                updateReportLinks();
                checkAndToggleGeneratePdfsButton();
                break;
            case 'failed':
                console.log(`🚨 BUTTON STATE: Failed state - showing RESUME and START buttons for company ${currentResearchCompanyId}`);
                if (resumeBtn) resumeBtn.style.display = 'inline-block';
                if (startBtn) startBtn.style.display = 'inline-block';
                break;
            default:
                console.log(`🚨 BUTTON STATE: Default state (${status}) - showing START button for company ${currentResearchCompanyId}`);
                if (startBtn) startBtn.style.display = 'inline-block';
        }
    }

    function updateReportLinks() {
        if (!currentResearchCompanyId) return;

        const htmlReportLink = document.getElementById('viewHtmlReportLink');
        const pdfReportLink = document.getElementById('downloadPdfReportLink');
        const basicResearchPdfLink = document.getElementById('downloadBasicResearchPdfLink');
        const embedReportLink = document.getElementById('viewEmbedReportLink');

        if (htmlReportLink) {
            htmlReportLink.href = `/api/public/reports/${currentResearchCompanyId}`;
        }
        if (pdfReportLink) {
            pdfReportLink.href = `/api/public/reports/${currentResearchCompanyId}/pdf`;
        }
        if (basicResearchPdfLink) {
            basicResearchPdfLink.href = `/api/public/reports/${currentResearchCompanyId}/basic-research.pdf`;
        }
        if (embedReportLink) {
            embedReportLink.href = `/api/public/reports/${currentResearchCompanyId}/embed`;
        }
    }

    function checkAndToggleGeneratePdfsButton() {
        const btn = document.getElementById('generatePdfsBtn');
        if (!btn || !currentResearchCompanyId) return;

        fetch(`/api/public/reports/${currentResearchCompanyId}/info`)
            .then(r => r.json())
            .then(info => {
                const missingFinal = !info.has_pdf_report;
                const missingBasic = !info.has_basic_research_pdf;
                btn.style.display = (missingFinal || missingBasic) ? 'block' : 'none';
                btn.onclick = () => generatePdfs();
            })
            .catch(() => {
                btn.style.display = 'block';
                btn.onclick = () => generatePdfs();
            });
    }

    function generatePdfs() {
        if (!currentResearchCompanyId) return;
        const btn = document.getElementById('generatePdfsBtn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';
        }
        fetch(`/api/companies/${currentResearchCompanyId}/generate-pdfs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
            .then(r => r.json())
            .then(res => {
                if (!res.success) throw new Error(res.error || 'Failed to generate PDFs');
                showSuccess('PDFs generated successfully');
                updateReportLinks();
                checkAndToggleGeneratePdfsButton();
            })
            .catch(err => {
                showError(`Failed to generate PDFs: ${err.message}`);
            })
            .finally(() => {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<i class=\"fas fa-cogs me-2\"></i>Generate PDFs';
                }
            });
    }

    function displayProgressBar(data) {
        console.log('🚨 DISPLAY PROGRESS: displayProgressBar called with data:', data);
        const progressContainer = document.getElementById('deepResearchProgress');
        if (!progressContainer) {
            console.error('🚨 ERROR: deepResearchProgress container not found!');
            return;
        }

        const percentage = data.progress_percentage || 0;
        const currentStatus = data.current_status || data.llm_research_step_status || (data.research_status === 'pending' ? 'Not Started' : 'Loading...');
        const provider = data.llm_research_provider ? data.llm_research_provider.toUpperCase() : (data.research_status === 'pending' ? 'None' : 'AI');
        
        console.log(`🚨 PROGRESS DATA: ${percentage}% - Status: ${currentStatus} - Provider: ${provider}`);
        
        progressContainer.innerHTML = `
            <div class="card border-info">
                <div class="card-header bg-info text-white">
                    <h6 class="mb-0">
                        <i class="fas fa-chart-line me-2"></i>Research Progress: ${Math.round(percentage)}%
                    </h6>
                </div>
                <div class="card-body">
                    <div class="progress mb-3" style="height: 8px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated bg-info" 
                             role="progressbar" 
                             style="width: ${percentage}%" 
                             aria-valuenow="${percentage}" 
                             aria-valuemin="0" 
                             aria-valuemax="100">
                        </div>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="status-info">
                            <strong>Status:</strong> <span class="text-info">${currentStatus}</span>
                        </div>
                        <div class="provider-info">
                            <small class="text-muted">Provider: ${provider.toUpperCase()}</small>
                        </div>
                    </div>
                    ${data.llm_research_started_at ? `
                        <div class="mt-2">
                            <small class="text-muted">Started: ${new Date(data.llm_research_started_at).toLocaleString()}</small>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    function canTriggerStep(stepNumber, stepDetails) {
        // Check if previous steps are completed
        if (stepNumber === 2) {
            // Step 2 can be triggered if step 1 is completed
            const step1 = stepDetails.find(step => (step.step || stepDetails.indexOf(step) + 1) === 1);
            return step1 && (step1.is_completed || step1.status === 'completed') && !step1.has_error && step1.status !== 'error';
        } else if (stepNumber === 3) {
            // Step 3 can be triggered if both step 1 and step 2 are completed
            const step1 = stepDetails.find(step => (step.step || stepDetails.indexOf(step) + 1) === 1);
            const step2 = stepDetails.find(step => (step.step || stepDetails.indexOf(step) + 1) === 2);
            return step1 && (step1.is_completed || step1.status === 'completed') && !step1.has_error && step1.status !== 'error' &&
                   step2 && (step2.is_completed || step2.status === 'completed') && !step2.has_error && step2.status !== 'error';
        }
        return false;
    }

    function displayResearchSteps(data) {
        console.log('🚨 DISPLAY STEPS: displayResearchSteps called with data:', data);
        const stepsContainer = document.getElementById('deepResearchSteps');
        if (!stepsContainer) {
            console.error('🚨 ERROR: deepResearchSteps container not found!');
            return;
        }

        const stepDetails = data.step_details || [];
        const currentStep = data.current_step || 'step_1';
        
        console.log(`🚨 STEPS DATA: ${stepDetails.length} steps - Current: ${currentStep}`);
        
        let stepsHtml = '<div class="row g-3">';
        
        stepDetails.forEach((step, index) => {
            const stepNum = step.step || (index + 1);
            const isActive = currentStep === `step_${stepNum}` && data.research_status !== 'pending';
            const isCompleted = step.status === 'completed';
            const hasError = step.status === 'error';
            const isPending = data.research_status === 'pending' || (!isCompleted && !hasError && !isActive);
            
            // For manual trigger: step should not be completed, not have error, not be active, but prerequisites should be met
            const canShowManualTrigger = !isCompleted && !hasError && !isActive && stepNum > 1;
            const canTrigger = canTriggerStep(stepNum, stepDetails);
            
            // For Step 1: Allow manual paste option and copy prompt option
            const canShowPasteOption = stepNum === 1 && !isCompleted && !hasError && !isActive;
            const canShowCopyPrompt = stepNum === 1;
            
            // Debug logging for manual triggers
            if (stepNum > 1) {
                console.log(`🔧 Manual Trigger Debug - Step ${stepNum}:`, {
                    stepNum,
                    isCompleted,
                    hasError,
                    isActive,
                    canShowManualTrigger,
                    canTrigger,
                    stepStatus: step.status,
                    overallStatus: data.research_status
                });
            }
            
            let statusIcon = 'fas fa-circle text-muted';
            let statusText = 'Pending';
            let cardClass = 'border-light';
            
            if (hasError) {
                statusIcon = 'fas fa-exclamation-circle text-danger';
                statusText = 'Error';
                cardClass = 'border-danger';
            } else if (isCompleted) {
                statusIcon = 'fas fa-check-circle text-success';
                statusText = 'Completed';
                cardClass = 'border-success';
            } else if (isActive) {
                statusIcon = 'fas fa-spinner fa-spin text-primary';
                statusText = 'In Progress';
                cardClass = 'border-primary';
            } else if (isPending) {
                statusIcon = 'fas fa-circle text-muted';
                statusText = 'Ready to Start';
                cardClass = 'border-light';
            }
            
            stepsHtml += `
                <div class="col-md-4">
                    <div class="card ${cardClass} h-100">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-2">
                                <span class="badge badge-step me-2">${stepNum}</span>
                                <h6 class="mb-0">${step.name || `Step ${stepNum}`}</h6>
                            </div>
                            <p class="text-muted small mb-2">${step.description || 'Processing...'}</p>
                            <div class="step-status">
                                <i class="${statusIcon} me-1"></i>
                                <small class="fw-bold">${statusText}</small>
                            </div>
                            ${step.has_results ? `
                                <button class="btn btn-sm btn-outline-primary mt-2" onclick="viewStepResults(${stepNum})">
                                    <i class="fas fa-eye me-1"></i>View Results
                                </button>
                            ` : ''}
                            ${canShowManualTrigger && canTrigger ? `
                                <div class="mt-2">
                                    <button id="manualTriggerStep${stepNum}" 
                                            class="btn btn-sm btn-success" 
                                            onclick="manualTriggerStep(${stepNum})"
                                            title="Previous step completed - click to start Step ${stepNum}">
                                        <i class="fas fa-play me-1"></i>Start Step ${stepNum}
                                    </button>
                                    <div class="text-muted small mt-1">
                                        <i class="fas fa-info-circle me-1"></i>Ready to start
                                    </div>
                                </div>
                            ` : ''}
                            ${canShowCopyPrompt || canShowPasteOption ? `
                                <div class="mt-2">
                                    ${canShowCopyPrompt ? `
                                        <button class="btn btn-sm btn-outline-info me-1" 
                                                onclick="copyResearchPrompt(${stepNum})"
                                                title="Copy the research prompt to use in external deep research tools">
                                            <i class="fas fa-copy me-1"></i>Copy Prompt
                                        </button>
                                    ` : ''}
                                    ${canShowPasteOption ? `
                                        <button class="btn btn-sm btn-outline-success" 
                                                onclick="togglePasteOption(${stepNum})"
                                                title="Paste your own research content instead of running AI research">
                                            <i class="fas fa-paste me-1"></i>Paste Research
                                        </button>
                                    ` : ''}
                                    ${canShowPasteOption ? `
                                        <div id="pasteSection${stepNum}" class="mt-2" style="display: none;">
                                        <label class="form-label small">Paste your research content:</label>
                                        <textarea id="pasteContent${stepNum}" 
                                                class="form-control" 
                                                rows="6" 
                                                placeholder="Paste comprehensive company research content here. This will be used as Step 1 Basic Research instead of running AI research."></textarea>
                                        <div class="mt-2">
                                            <button class="btn btn-sm btn-success" 
                                                    onclick="submitPastedResearch(${stepNum})"
                                                    title="Submit pasted content as Step 1 research">
                                                <i class="fas fa-check me-1"></i>Submit Research
                                            </button>
                                            <button class="btn btn-sm btn-secondary ms-1" 
                                                    onclick="togglePasteOption(${stepNum})"
                                                    title="Cancel paste and close">
                                                <i class="fas fa-times me-1"></i>Cancel
                                            </button>
                                        </div>
                                        <div class="text-muted small mt-1">
                                            <i class="fas fa-info-circle me-1"></i>This will skip AI research and use your content directly. Steps 2 and 3 will be triggered automatically.
                                        </div>
                                        </div>
                                    ` : ''}
                                </div>
                            ` : ''}
                            ${hasError && step.error_message ? `
                                <div class="alert alert-danger mt-2 mb-0 py-1">
                                    <small>${step.error_message}</small>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        
        stepsHtml += '</div>';
        
        // Add some custom CSS for step badges
        const customStyles = `
            <style>
                .badge-step {
                    background-color: #6c757d;
                    color: white;
                    width: 24px;
                    height: 24px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 0.75rem;
                }
                .border-primary .badge-step {
                    background-color: #0d6efd;
                }
                .border-success .badge-step {
                    background-color: #198754;
                }
                .border-danger .badge-step {
                    background-color: #dc3545;
                }
            </style>
        `;
        
        stepsContainer.innerHTML = customStyles + stepsHtml;
    }

    function viewStepResults(stepNumber) {
        if (!currentResearchCompanyId) return;
        
        // Open the step detail modal
        const modal = document.getElementById('stepDetailModal');
        const modalLabel = document.getElementById('stepDetailModalLabel');
        const content = document.getElementById('stepDetailContent');
        
        modalLabel.textContent = `Step ${stepNumber} Results`;
        content.innerHTML = `
            <div class="d-flex justify-content-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
        
        // Show the modal
        const stepModal = new bootstrap.Modal(modal);
        stepModal.show();
        
        // Load the step content
        fetch(`/api/companies/${currentResearchCompanyId}/llm-step-results/${stepNumber}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Parse markdown content if marked library is available
                    let contentHtml = data.content || 'No content available';
                    if (typeof marked !== 'undefined' && data.content) {
                        try {
                            contentHtml = marked.parse(data.content);
                        } catch (e) {
                            console.warn('Failed to parse markdown, showing as plain text:', e);
                            contentHtml = `<pre style="white-space: pre-wrap; line-height: 1.6;">${data.content}</pre>`;
                        }
                    }
                    
                    content.innerHTML = `
                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0">${data.step_name || `Step ${stepNumber}`}</h6>
                            </div>
                            <div class="card-body">
                                <div class="research-content markdown-content" style="line-height: 1.6;">
                                    ${contentHtml}
                                </div>
                            </div>
                        </div>
                    `;
                } else {
                    content.innerHTML = `
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            ${data.message || 'Unable to load step results'}
                        </div>
                    `;
                }
            })
            .catch(error => {
                content.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        Error loading step results: ${error.message}
                    </div>
                `;
            });
    }

    // Expose viewStepResults to global scope for onclick handlers
    window.viewStepResults = viewStepResults;
    
    function manualTriggerStep(stepNumber) {
        if (!currentResearchCompanyId) return;
        
        const confirmMessage = `Are you sure you want to manually trigger Step ${stepNumber}?`;
        if (!confirm(confirmMessage)) return;
        
        const endpoint = `/api/companies/${currentResearchCompanyId}/manual-trigger-step-${stepNumber}`;
        
        // Show loading state
        const triggerBtn = document.getElementById(`manualTriggerStep${stepNumber}`);
        if (triggerBtn) {
            triggerBtn.disabled = true;
            triggerBtn.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i>Triggering...`;
        }
        
        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                addLogMessage(`✅ ${data.message}`);
                // Refresh research data to show updated status
                setTimeout(() => {
                    checkResearchProgress();
                }, 1000);
            } else {
                addLogMessage(`❌ Failed to trigger Step ${stepNumber}: ${data.error}`);
                showError(data.error);
            }
        })
        .catch(error => {
            addLogMessage(`❌ Error triggering Step ${stepNumber}: ${error.message}`);
            showError(`Failed to trigger Step ${stepNumber}: ${error.message}`);
        })
        .finally(() => {
            // Reset button state
            if (triggerBtn) {
                triggerBtn.disabled = false;
                triggerBtn.innerHTML = `<i class="fas fa-play me-1"></i>Trigger Step ${stepNumber}`;
            }
        });
    }
    
    // Manual trigger buttons are now integrated directly into the step display
    
    // Expose manual trigger functions to global scope
    window.manualTriggerStep = manualTriggerStep;

    function viewStrategicReport() {
        if (!currentResearchCompanyId) return;
        
        // Open the HTML report in a new tab
        const reportUrl = `/api/public/reports/${currentResearchCompanyId}`;
        window.open(reportUrl, '_blank');
    }

    function startDeepResearch(forceRefresh = false) {
        if (!currentResearchCompanyId) {
            console.error('🚨 ERROR: No company ID selected for research');
            showError('No company selected for research');
            return;
        }

        // BULLETPROOF: Prevent multiple concurrent requests
        if (isResearchInProgress) {
            console.error('🚨 BLOCKED: Multiple research attempts prevented - research already in progress');
            addLogMessage('🚨 BLOCKED: Research already in progress. Please wait for completion.');
            showError('Research already in progress. Please wait for completion.');
            return;
        }
        
        const selectedResearchType = getSelectedResearchType();
        console.log(`🚨 DEEP RESEARCH TRIGGERED: Starting research for company ${currentResearchCompanyId}, type: ${selectedResearchType}`);
        
        const researchConfig = getResearchConfig(selectedResearchType, forceRefresh);
        
        isResearchInProgress = true;
        showResearchLog();
        console.log(`🚨 DEEP RESEARCH API REQUEST: About to make API call to ${researchConfig.url}`);
        addLogMessage(`🚨 DEEP RESEARCH INITIATED: Starting AI Deep Research process for company ${currentResearchCompanyId}...`);
        
        // DISABLE ALL RESEARCH BUTTONS TO PREVENT SPAM CLICKS
        const startBtn = document.getElementById('startDeepResearchBtn');
        const forceBtn = document.getElementById('forceRefreshDeepBtn');
        [startBtn, forceBtn].forEach(btn => {
            if (btn) {
                btn.disabled = true;
                btn.classList.add('disabled');
            }
        });

        fetch(researchConfig.url, {
            method: researchConfig.method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: researchConfig.body
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log(`🚨 DEEP RESEARCH SUCCESS: API call succeeded for company ${currentResearchCompanyId}`);
                addLogMessage(`🚨 RESEARCH STARTED: ${data.message || 'Research started successfully'}`);
                updateActionButtons('in_progress');
                startProgressPolling();
            } else {
                console.error(`🚨 DEEP RESEARCH ERROR: API call failed for company ${currentResearchCompanyId}: ${data.error}`);
                addLogMessage(`🚨 ERROR: ${data.error}`);
                showError(data.error);
                isResearchInProgress = false;
            }
        })
        .catch(error => {
            console.error('Error starting research:', error);
            addLogMessage(`Error: ${error.message}`);
            showError('Failed to start research');
            isResearchInProgress = false;
        });
    }

    function resumeDeepResearch() {
        // Resume functionality not needed for LLM research - it handles continuation automatically
        showError('Resume not needed - LLM research continues automatically from interruptions');
    }

    function stopResearch() {
        if (researchProgressInterval) {
            clearInterval(researchProgressInterval);
            researchProgressInterval = null;
        }
        isResearchInProgress = false;
        addLogMessage('Research stopped by user');
        updateActionButtons('pending');
        
        // Restore normal modal behavior now that research is stopped
        const modal = document.getElementById('deepResearchModal');
        if (modal) {
            modal.removeAttribute('aria-hidden');
            modal.setAttribute('aria-modal', 'true');
        }
    }

    function startProgressPolling() {
        if (researchProgressInterval) {
            clearInterval(researchProgressInterval);
        }

        researchProgressInterval = setInterval(() => {
            if (!isResearchInProgress || !currentResearchCompanyId) {
                clearInterval(researchProgressInterval);
                researchProgressInterval = null;
                return;
            }

            // CRITICAL FIX: Use only the correct LLM progress endpoint
            fetch(`/api/companies/${currentResearchCompanyId}/llm-step-progress`)
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        addLogMessage(`Progress error: ${data.error || 'Unknown error'}`);
                        return;
                    }
                    
                    displayProgressBar(data);
                    displayResearchSteps(data);
                    
                    // Manual trigger buttons are now shown directly in step cards

                    if (data.research_status === 'completed') {
                        addLogMessage('Research completed successfully!');
                        isResearchInProgress = false;
                        updateActionButtons('completed', data);
                        clearInterval(researchProgressInterval);
                        researchProgressInterval = null;
                        showSuccess('Deep research completed successfully!');
                    } else if (data.research_status === 'failed') {
                        addLogMessage(`Research failed: ${data.research_error || 'Unknown error'}`);
                        isResearchInProgress = false;
                        updateActionButtons('failed', data);
                        clearInterval(researchProgressInterval);
                        researchProgressInterval = null;
                        showError('Research failed. You can try to resume or start fresh.');
                    }
                })
                .catch(error => {
                    console.error('Error polling progress:', error);
                    addLogMessage(`Polling error: ${error.message}`);
                });
        }, 2000); // Poll every 2 seconds
    }

    function showResearchLog() {
        console.log('🚨 SHOW LOG: showResearchLog() called');
        const logContainer = document.getElementById('deepResearchLog');
        if (logContainer) {
            logContainer.style.display = 'block';
            console.log('🚨 LOG VISIBLE: Research log container is now visible');
        } else {
            console.error('🚨 LOG ERROR: deepResearchLog container not found!');
        }
    }

    function addLogMessage(message) {
        console.log('🚨 ADD LOG: addLogMessage() called with:', message);
        const logContent = document.getElementById('logContent');
        if (logContent) {
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = `<div class="log-entry">[${timestamp}] ${message}</div>`;
            logContent.innerHTML += logEntry;
            logContent.scrollTop = logContent.scrollHeight;
            console.log('🚨 LOG ADDED: Message added to log container');
        } else {
            console.error('🚨 LOG ERROR: logContent container not found!');
        }
        
        // Also show in console for debugging
        console.log(`[Deep Research] ${message}`);
    }

    // Global function to add log messages from external sources
    window.addDeepResearchLog = function(message) {
        addLogMessage(message);
    };

    // Global functions that need to be accessible from HTML
    window.toggleResearchLog = function() {
        const logContainer = document.querySelector('.log-container');
        if (logContainer) {
            logContainer.style.display = logContainer.style.display === 'none' ? 'block' : 'none';
        }
    };

    window.viewStepContent = function(stepNumber) {
        // Old step viewing not supported - use LLM step viewing instead
        showError('This feature is only available for LLM Deep Research. Please use the LLM research option.');
    };

    function showStepDetailModal(stepName, content, stepNumber) {
        const modal = document.getElementById('stepDetailModal');
        const title = document.getElementById('stepDetailModalLabel');
        const contentDiv = document.getElementById('stepDetailContent');
        const downloadBtn = document.getElementById('downloadStepBtn');

        if (title) title.textContent = stepName;
        
        if (contentDiv) {
            if (stepNumber === 3) {
                // Render markdown for final report
                contentDiv.innerHTML = `<div class="markdown-content">${marked.parse(content)}</div>`;
            } else {
                // Show as preformatted text
                contentDiv.innerHTML = `<pre class="step-content">${content}</pre>`;
            }
        }

        if (downloadBtn) {
            downloadBtn.onclick = () => downloadStepContent(stepName, content, stepNumber);
        }

        if (modal) {
            new bootstrap.Modal(modal).show();
        }
    }

    function downloadStepContent(stepName, content, stepNumber) {
        const filename = `${stepName.replace(/\s+/g, '_').toLowerCase()}.${stepNumber === 3 ? 'md' : 'txt'}`;
        const blob = new Blob([content], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }

    function getStatusBadgeClass(status) {
        switch (status) {
            case 'completed': return 'bg-success';
            case 'in_progress': return 'bg-warning';
            case 'failed': return 'bg-danger';
            case 'pending': return 'bg-secondary';
            default: return 'bg-secondary';
        }
    }

    function showSuccess(message) {
        const toast = document.getElementById('successToast');
        if (toast) {
            const body = toast.querySelector('.toast-body');
            if (body) body.textContent = message;
            new bootstrap.Toast(toast).show();
        }
    }

    function showError(message) {
        const toast = document.getElementById('errorToast');
        if (toast) {
            const body = toast.querySelector('.toast-body');
            if (body) body.textContent = message;
            new bootstrap.Toast(toast).show();
        }
    }

    function publishReport() {
        if (!currentResearchCompanyId) {
            showError('No company selected for publishing');
            return;
        }

        // First get the company details to prepare the payload
        fetch(`/api/companies/${currentResearchCompanyId}`)
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    throw new Error(data.error || 'Failed to fetch company details');
                }

                const company = data.company;
                if (!company.html_report && !company.markdown_report) {
                    throw new Error('No report available to publish');
                }

                // Show publish status as loading
                showPublishStatus('loading', 'Publishing report to possibleminds.in...');

                // Prepare payload matching backend structure
                const payload = {
                    company_id: `comp_${company.id}`,
                    company_name: company.company_name,
                    company_website: company.website_url || "",
                    contact_id: `contact_frontend_user`,
                    generated_date: new Date().toISOString().split('T')[0],
                    html_report: company.html_report || "",
                    pdf_report_base64: company.pdf_report_base64 || ""
                };

                // Log the raw content being published
                // console.log('📝 RAW CONTENT LOGGING: Publishing content to possibleminds.in (Frontend)');
                // console.log('📝 Company:', company.company_name);
                // console.log('📝 Website:', company.website_url || 'N/A');
                // console.log('📝 Content Length:', company.markdown_report ? company.markdown_report.length : 0, 'characters');
                // console.log('📝 RAW MARKDOWN CONTENT START:');
                // console.log('='.repeat(80));
                // console.log(company.markdown_report);
                // console.log('='.repeat(80));
                // console.log('📝 RAW MARKDOWN CONTENT END');
                
                // // Log the complete JSON payload being sent
                // console.log('📝 COMPLETE JSON PAYLOAD START:');
                // console.log('-'.repeat(80));
                // console.log(JSON.stringify(payload, null, 2));
                // console.log('-'.repeat(80));
                // console.log('📝 COMPLETE JSON PAYLOAD END');

                // Make the publish request
                return fetch(window.NETLIFY_PUBLISH_URL || 'https://possibleminds.in/.netlify/functions/publish-report-persistent', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
            })
            .then(response => {
                // Log the complete response from possibleminds.in
                console.log('📝 POSSIBLEMINDS.IN RESPONSE START:');
                console.log('~'.repeat(80));
                console.log('Status Code:', response.status);
                console.log('Response Headers:', Object.fromEntries(response.headers.entries()));
                console.log('Response OK:', response.ok);
                console.log('~'.repeat(80));
                console.log('📝 POSSIBLEMINDS.IN RESPONSE END');
                
                if (!response.ok) {
                    // Try to get response text for better error messages
                    return response.text().then(text => {
                        console.log('📝 ERROR RESPONSE BODY:', text);
                        let errorMsg = `HTTP ${response.status}: ${response.statusText}`;
                        if (text) {
                            try {
                                const errorData = JSON.parse(text);
                                errorMsg += ` - ${errorData.error || errorData.message || text}`;
                            } catch (e) {
                                errorMsg += ` - ${text}`;
                            }
                        }
                        throw new Error(errorMsg);
                    });
                }
                return response.json();
            })
            .then(result => {
                // Log the successful publishing details
                console.log('📝 PUBLISHING SUCCESS LOG:');
                console.log('📝 Full Response:', result);
                console.log('📝 Published URL:', result.data?.publishUrl || result.publishUrl || 'Not found');
                console.log('📝 Success Status:', result.success);
                
                if (result.success) {
                    const publishUrl = result.data?.publishUrl || result.publishUrl;
                    showPublishStatus('success', 'Report published successfully!', publishUrl, result);
                    addLogMessage(`Report published successfully: ${publishUrl}`);
                    addLogMessage(`Full response: ${JSON.stringify(result, null, 2)}`);
                } else {
                    throw new Error(result.error || 'Unknown publish error');
                }
            })
            .catch(error => {
                console.error('Error publishing report:', error);
                let errorMessage = error.message;
                
                // If the error has response data, try to extract more details
                if (error.response) {
                    try {
                        errorMessage += ` (Status: ${error.response.status})`;
                    } catch (e) {
                        // Ignore parsing errors
                    }
                }
                
                showPublishStatus('error', `Publication failed: ${errorMessage}`);
                addLogMessage(`Publication error: ${errorMessage}`);
                addLogMessage(`Full error details: ${JSON.stringify(error, Object.getOwnPropertyNames(error), 2)}`);
            });
    }

    function showPublishStatus(status, message, publishUrl = null, fullResponse = null) {
        const container = document.getElementById('publishStatusContainer');
        const alert = document.getElementById('publishStatusAlert');
        const text = document.getElementById('publishStatusText');
        const spinner = document.getElementById('publishSpinner');
        const successIcon = document.getElementById('publishSuccessIcon');
        const errorIcon = document.getElementById('publishErrorIcon');
        const urlContainer = document.getElementById('publishUrlContainer');
        const urlLink = document.getElementById('publishedReportUrl');

        if (!container || !alert || !text) return;

        // Show the container
        container.style.display = 'block';

        // Hide all icons and spinner first
        [spinner, successIcon, errorIcon].forEach(el => {
            if (el) el.style.display = 'none';
        });

        // Update message
        text.textContent = message;

        // Update status-specific styling and icons
        switch (status) {
            case 'loading':
                alert.className = 'alert alert-info';
                if (spinner) spinner.style.display = 'block';
                if (urlContainer) urlContainer.style.display = 'none';
                
                // Hide debug container during loading
                const debugContainer = document.getElementById('publishDebugContainer');
                if (debugContainer) debugContainer.style.display = 'none';
                break;
            case 'success':
                alert.className = 'alert alert-success';
                if (successIcon) successIcon.style.display = 'block';
                if (publishUrl && urlContainer && urlLink) {
                    urlLink.href = publishUrl;
                    urlLink.textContent = publishUrl;
                    urlContainer.style.display = 'block';
                    
                    // Add additional response details if available
                    if (fullResponse && fullResponse.data) {
                        const responseDetails = document.createElement('div');
                        responseDetails.className = 'mt-2 small text-muted';
                        responseDetails.innerHTML = `
                            <strong>Response Details:</strong><br>
                            ${fullResponse.data.reportId ? `Report ID: ${fullResponse.data.reportId}<br>` : ''}
                            ${fullResponse.data.companySlug ? `Company Slug: ${fullResponse.data.companySlug}<br>` : ''}
                            ${fullResponse.message ? `Message: ${fullResponse.message}<br>` : ''}
                        `;
                        
                        // Remove any existing response details
                        const existingDetails = urlContainer.querySelector('.response-details');
                        if (existingDetails) {
                            existingDetails.remove();
                        }
                        
                        responseDetails.className += ' response-details';
                        urlContainer.appendChild(responseDetails);
                    }
                    
                    // Show debug information
                    if (fullResponse) {
                        const debugContainer = document.getElementById('publishDebugContainer');
                        const rawResponse = document.getElementById('publishRawResponse');
                        
                        if (debugContainer && rawResponse) {
                            debugContainer.style.display = 'block';
                            rawResponse.textContent = JSON.stringify(fullResponse, null, 2);
                        }
                    }
                }
                break;
            case 'error':
                alert.className = 'alert alert-danger';
                if (errorIcon) errorIcon.style.display = 'block';
                if (urlContainer) urlContainer.style.display = 'none';
                
                // Hide debug container during error (for now)
                const errorDebugContainer = document.getElementById('publishDebugContainer');
                if (errorDebugContainer) errorDebugContainer.style.display = 'none';
                break;
        }
    }

    function hidePublishStatus() {
        const container = document.getElementById('publishStatusContainer');
        const debugContainer = document.getElementById('publishDebugContainer');
        
        if (container) {
            container.style.display = 'none';
        }
        
        if (debugContainer) {
            debugContainer.style.display = 'none';
        }
    }

    // Research Type Selection Functions
    function getSelectedResearchType() {
        // Always return LLM research since it's the only option
        const researchType = 'llm_step_by_step';
        console.log(`🚨 RESEARCH TYPE: Selected research type: ${researchType}`);
        return researchType;
    }

    function getResearchConfig(researchType, forceRefresh = false) {
        const baseConfig = {
            force_refresh: forceRefresh || document.getElementById('forceRefreshOption')?.checked || false
        };

        // Always use LLM deep research
        const provider = document.getElementById('llmProviderSelect')?.value || 'perplexity';
        return {
            url: `/api/companies/${currentResearchCompanyId}/llm-step-research`,
            method: 'POST',
            body: JSON.stringify({
                ...baseConfig,
                provider: provider
            })
        };
    }

    function updateResearchTypeSelection() {
        const selectedType = getSelectedResearchType();
        
        // Update card visual states
        document.querySelectorAll('.research-type-card').forEach(card => {
            const radio = card.querySelector('input[type="radio"]');
            if (radio && radio.checked) {
                card.classList.add('border-primary');
                card.classList.remove('border-light');
            } else {
                card.classList.remove('border-primary');
                card.classList.add('border-light');
            }
        });

        // Update the LLM provider select visibility
        const llmProviderSelect = document.getElementById('llmProviderSelect');
        if (llmProviderSelect) {
            llmProviderSelect.style.display = selectedType === 'llm_step_by_step' ? 'inline-block' : 'none';
        }

        // Update start button text
        const startBtn = document.getElementById('startDeepResearchBtn');
        if (startBtn) {
            startBtn.innerHTML = '<i class="fas fa-brain me-1"></i>Start Deep Research';
        }

        console.log(`Research type updated: ${selectedType}`);
    }

    // Progress polling needs to be updated for different research types
    function getProgressUrl(researchType) {
        // Always use LLM progress endpoint
        return `/api/companies/${currentResearchCompanyId}/llm-step-progress`;
    }

    // Update progress polling to handle different research types
    function startProgressPolling() {
        if (researchProgressInterval) {
            clearInterval(researchProgressInterval);
        }

        const selectedResearchType = getSelectedResearchType();
        
        researchProgressInterval = setInterval(() => {
            if (!isResearchInProgress || !currentResearchCompanyId) {
                clearInterval(researchProgressInterval);
                researchProgressInterval = null;
                return;
            }

            const progressUrl = getProgressUrl(selectedResearchType);
            
            fetch(progressUrl)
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        addLogMessage(`Progress error: ${data.error || 'Unknown error'}`);
                        return;
                    }
                    
                    updateResearchProgress(data, selectedResearchType);
                    
                    // Check completion for LLM research
                    const isComplete = data.current_step === 'completed' || data.is_complete;
                    
                    if (isComplete) {
                        addLogMessage('Research completed successfully!');
                        isResearchInProgress = false;
                        updateActionButtons('completed', data);
                        clearInterval(researchProgressInterval);
                        researchProgressInterval = null;
                        showSuccess('Deep research completed successfully!');
                    } else if (data.research_status === 'failed' || (data.current_status && data.current_status.includes('error'))) {
                        addLogMessage(`Research failed: ${data.research_error || data.error || 'Unknown error'}`);
                        isResearchInProgress = false;
                        updateActionButtons('failed', data);
                        clearInterval(researchProgressInterval);
                        researchProgressInterval = null;
                        showError('Research failed. You can try to resume or start fresh.');
                    }
                })
                .catch(error => {
                    console.error('Error polling progress:', error);
                    addLogMessage(`Progress polling error: ${error.message}`);
                });
        }, 2000); // Poll every 2 seconds
    }

    function updateResearchProgress(data, researchType) {
        // Always use new dynamic LLM research progress functions
        displayProgressBar(data);
        displayResearchSteps(data);
    }

    function updateLLMResearchProgress(data) {
        const progressContainer = document.getElementById('deepResearchProgress');
        if (!progressContainer) return;

        const progressPercentage = data.progress_percentage || 0;
        const currentStep = data.current_step || 'step_1';
        const stepDetails = data.step_details || [];
        const currentStatus = data.current_status || 'not_started';

        // Determine progress bar class based on status
        let progressClass = 'progress-bar-striped progress-bar-animated bg-info';
        if (currentStep === 'completed') {
            progressClass = 'bg-success';
        } else if (currentStatus.includes('error')) {
            progressClass = 'bg-danger';
        } else if (currentStep && currentStep.startsWith('step_')) {
            progressClass = 'progress-bar-striped progress-bar-animated bg-warning';
        }

        // Create user-friendly status text
        let statusText = currentStatus;
        if (currentStep === 'completed') {
            statusText = 'Research Completed';
        } else if (currentStatus.includes('error')) {
            statusText = 'Research Failed';
        } else if (currentStep === 'step_1') {
            statusText = 'Conducting Web Research';
        } else if (currentStep === 'step_2') {
            statusText = 'Analyzing Strategy';
        } else if (currentStep === 'step_3') {
            statusText = 'Generating Report';
        } else if (currentStatus === 'not_started') {
            statusText = 'Ready to Start';
        }

        // Update progress bar
        progressContainer.innerHTML = `
            <div class="research-progress-header mb-3">
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">AI Deep Research Progress</h6>
                    <span class="badge ${getStatusBadgeClass(currentStatus)}">${statusText}</span>
                </div>
            </div>
            <div class="progress mb-2" style="height: 20px;">
                <div class="progress-bar ${progressClass}" 
                     role="progressbar" 
                     style="width: ${progressPercentage}%" 
                     aria-valuenow="${progressPercentage}" 
                     aria-valuemin="0" 
                     aria-valuemax="100">
                    ${Math.round(progressPercentage)}%
                </div>
            </div>
            <div class="d-flex justify-content-between small text-muted">
                <span>Start</span>
                <span>${data.steps_completed || 0} of ${data.total_steps || 3} steps completed</span>
                <span>Finished</span>
            </div>
        `;

        // Update steps display
        updateLLMStepsDisplay(stepDetails);
    }

    function updateLLMStepsDisplay(stepDetails) {
        const stepsContainer = document.getElementById('deepResearchSteps');
        if (!stepsContainer) return;

        let stepsHtml = '<div class="llm-research-steps">';
        
        stepDetails.forEach((step, index) => {
            const statusClass = step.status === 'completed' ? 'text-success' : 
                               step.status === 'error' ? 'text-danger' :
                               step.status === 'prompt_ready' ? 'text-warning' : 'text-muted';
            const statusIcon = step.status === 'completed' ? 'fa-check-circle' :
                              step.status === 'error' ? 'fa-exclamation-circle' :
                              step.status === 'prompt_ready' ? 'fa-clock' : 'fa-circle';

            // Get user-friendly step names
            let stepName = step.name;
            let stepDescription = step.description;
            if (step.step === 1) {
                stepName = 'Web Research & Data Collection';
                stepDescription = 'Gathering comprehensive company intelligence using AI web search';
            } else if (step.step === 2) {
                stepName = 'Strategic Analysis';
                stepDescription = 'Analyzing business strategy, market position, and opportunities';
            } else if (step.step === 3) {
                stepName = 'Report Generation';
                stepDescription = 'Creating comprehensive business intelligence reports';
            }

            // Show spinner for active steps
            const isActive = step.status === 'in_progress' || (step.status === 'prompt_ready' && !step.has_results);
            const spinnerHtml = isActive ? `
                <div class="spinner-border spinner-border-sm text-primary me-2" role="status">
                    <span class="visually-hidden">Processing...</span>
                </div>
            ` : '';

            stepsHtml += `
                <div class="llm-step-card card mb-2 ${step.status === 'completed' ? 'border-success' : step.status === 'error' ? 'border-danger' : isActive ? 'border-warning' : ''}">
                    <div class="card-body">
                        <div class="d-flex align-items-center">
                            <div class="step-icon me-3">
                                ${spinnerHtml}
                                <i class="fas ${statusIcon} ${statusClass}"></i>
                            </div>
                            <div class="step-info flex-grow-1">
                                <h6 class="mb-1">${stepName}</h6>
                                <small class="text-muted">${stepDescription}</small>
                                ${step.has_error ? `<div class="mt-1"><small class="text-danger"><i class="fas fa-exclamation-triangle me-1"></i>${step.error_message}</small></div>` : ''}
                            </div>
                            <div class="step-actions">
                                ${step.has_error ? `
                                    <button class="btn btn-sm btn-outline-danger" onclick="showErrorDetails('${step.error_message.replace(/'/g, "\\'")}', '${stepName}')">
                                        <i class="fas fa-exclamation-triangle"></i> View Error
                                    </button>
                                ` : step.has_results ? `
                                    <button class="btn btn-sm btn-outline-primary" onclick="viewLLMStepContent('step_${step.step}')">
                                        <i class="fas fa-eye"></i> View Results
                                    </button>
                                ` : isActive ? `
                                    <span class="badge bg-warning">Processing...</span>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        stepsHtml += '</div>';
        stepsContainer.innerHTML = stepsHtml;
    }


    // Global function for viewing LLM step content
    window.viewLLMStepContent = function(stepName) {
        if (!currentResearchCompanyId) return;
        
        const url = `/api/companies/${currentResearchCompanyId}/llm-step/${stepName}`;
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show step content in modal or new window
                    const modal = new bootstrap.Modal(document.getElementById('stepDetailModal'));
                    document.getElementById('stepDetailModalLabel').textContent = data.step_title;
                    document.getElementById('stepDetailContent').innerHTML = `
                        <div class="step-content">
                            <div class="mb-3">
                                <strong>Content Type:</strong> <span class="badge bg-info">${data.content_type}</span>
                                <strong class="ms-3">Length:</strong> ${data.word_count} words
                            </div>
                            <pre class="bg-light p-3 rounded" style="white-space: pre-wrap; max-height: 60vh; overflow-y: auto;">${data.content}</pre>
                        </div>
                    `;
                    modal.show();
                } else {
                    showError(`Failed to load step content: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Error loading step content:', error);
                showError('Failed to load step content');
            });
    };

    // Global function to show error details
    window.showErrorDetails = function(errorMessage, stepName) {
        const modal = new bootstrap.Modal(document.getElementById('stepDetailModal'));
        const modalTitle = document.getElementById('stepDetailModalLabel');
        const modalContent = document.getElementById('stepDetailContent');
        
        modalTitle.textContent = `Error in ${stepName}`;
        modalContent.innerHTML = `
            <div class="alert alert-danger">
                <h6><i class="fas fa-exclamation-triangle me-2"></i>Research Error</h6>
                <p class="mb-0">${errorMessage}</p>
                
                <hr>
                <h6>Common Solutions:</h6>
                <ul class="mb-0">
                    <li><strong>Rate Limiting (429):</strong> Wait a few minutes and try again</li>
                    <li><strong>Quota Exceeded:</strong> Check your API billing and plan limits</li>
                    <li><strong>Authentication (401):</strong> Verify API keys in configuration</li>
                    <li><strong>Network Issues:</strong> Check internet connection and try again</li>
                </ul>
                
                <div class="mt-3">
                    <button class="btn btn-warning btn-sm" onclick="retryFailedStep('${stepName}')">
                        <i class="fas fa-redo me-1"></i>Retry Step
                    </button>
                </div>
            </div>
        `;
        
        modal.show();
    };
    
    // Global function to retry a failed step
    window.retryFailedStep = function(stepName) {
        // Close the error modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('stepDetailModal'));
        if (modal) modal.hide();
        
        // Show retry confirmation
        if (confirm(`Retry ${stepName}? This will restart the research step.`)) {
            // Trigger research restart with force refresh
            if (currentResearchCompanyId) {
                console.log(`Retrying ${stepName} for company ${currentResearchCompanyId}`);
                // You could implement a retry mechanism here
                location.reload(); // Simple solution: reload the page
            }
        }
    };
    
    // Global function to refresh modal (called after reset)
    window.refreshDeepResearchModal = function(companyId) {
        console.log(`🚨 REFRESH MODAL: Refreshing deep research modal for company ${companyId}`);
        if (currentResearchCompanyId && currentResearchCompanyId.toString() === companyId.toString()) {
            console.log(`🚨 MODAL RESET: Resetting modal state and reloading progress`);
            // Reset modal state
            resetModalState();
            // Load fresh progress data
            loadResearchProgress(companyId);
        } else {
            console.log(`🚨 MODAL SKIP: Modal not for this company (current: ${currentResearchCompanyId}, requested: ${companyId})`);
        }
    };
    
    // Make loadResearchProgress available globally for external refresh calls  
    window.loadResearchProgress = loadResearchProgress;

    // Manual paste functionality for Step 1
    window.togglePasteOption = function(stepNum) {
        const pasteSection = document.getElementById(`pasteSection${stepNum}`);
        const pasteBtn = document.querySelector(`button[onclick="togglePasteOption(${stepNum})"]`);
        
        if (pasteSection) {
            const isVisible = pasteSection.style.display !== 'none';
            if (isVisible) {
                pasteSection.style.display = 'none';
                if (pasteBtn) {
                    pasteBtn.innerHTML = '<i class="fas fa-paste me-1"></i>Paste Research';
                    pasteBtn.classList.remove('btn-outline-secondary');
                    pasteBtn.classList.add('btn-outline-success');
                }
            } else {
                pasteSection.style.display = 'block';
                if (pasteBtn) {
                    pasteBtn.innerHTML = '<i class="fas fa-times me-1"></i>Cancel Paste';
                    pasteBtn.classList.remove('btn-outline-success');
                    pasteBtn.classList.add('btn-outline-secondary');
                }
                // Focus on textarea
                const textarea = document.getElementById(`pasteContent${stepNum}`);
                if (textarea) {
                    setTimeout(() => textarea.focus(), 100);
                }
            }
        }
    };

    window.submitPastedResearch = function(stepNum) {
        const textarea = document.getElementById(`pasteContent${stepNum}`);
        const content = textarea ? textarea.value.trim() : '';
        
        if (!content) {
            showError('Please paste some research content before submitting.');
            return;
        }
        
        if (content.length < 100) {
            if (!confirm('The pasted content seems quite short. Are you sure you want to proceed?')) {
                return;
            }
        }
        
        // Show loading state
        const submitBtn = document.querySelector(`button[onclick="submitPastedResearch(${stepNum})"]`);
        const originalText = submitBtn ? submitBtn.innerHTML : '';
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Submitting...';
        }
        
        // Get the selected provider from the modal
        const providerElement = document.getElementById('llmProviderSelect');
        console.log(`🔍 PROVIDER ELEMENT:`, providerElement);
        console.log(`🔍 PROVIDER ELEMENT VALUE:`, providerElement?.value);
        console.log(`🔍 PROVIDER OPTIONS:`, providerElement ? Array.from(providerElement.options).map(o => `${o.value} (selected: ${o.selected})`) : 'null');
        
        const selectedProvider = providerElement?.value || 'perplexity';
        console.log(`🚀 MANUAL PASTE: Submitting with provider: ${selectedProvider}`);
        
        // Submit pasted content to backend
        const requestData = {
            step: stepNum,
            content: content,
            manual_paste: true,
            provider: selectedProvider
        };
        
        fetch(`/api/companies/${currentResearchCompanyId}/llm-step-manual-paste`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const autoProgressionMsg = data.auto_progression === 'auto_progression_started' 
                    ? ' Steps 2 and 3 have been automatically triggered.' 
                    : (data.auto_progression === 'auto_progression_failed' || data.auto_progression === 'auto_progression_error' 
                        ? ' Auto-progression of Steps 2 and 3 encountered an issue - please trigger manually if needed.' 
                        : '');
                        
                showSuccess(`Research content submitted successfully!${autoProgressionMsg}`);
                addLogMessage(`Step ${stepNum} completed with manual paste content (${content.length} characters)${autoProgressionMsg}`);
                
                // If auto-progression started, show polling message
                if (data.auto_progression === 'auto_progression_started') {
                    addLogMessage('🤖 AUTO-PROGRESSION: Steps 2 and 3 are now running automatically...');
                    // Start progress polling to show the automatic progression
                    startProgressPolling();
                }
                
                // Hide paste section
                togglePasteOption(stepNum);
                
                // Refresh the research progress to show updated state
                loadResearchProgress(currentResearchCompanyId);
                
            } else {
                throw new Error(data.error || 'Failed to submit pasted content');
            }
        })
        .catch(error => {
            console.error('Error submitting pasted research:', error);
            showError(`Failed to submit research content: ${error.message}`);
        })
        .finally(() => {
            // Restore button state
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });
    };

    // Copy research prompt functionality
    window.copyResearchPrompt = function(stepNum) {
        if (!currentResearchCompanyId) {
            showError('No company selected');
            return;
        }
        
        // Show loading state
        const copyBtn = document.querySelector(`button[onclick="copyResearchPrompt(${stepNum})"]`);
        const originalText = copyBtn ? copyBtn.innerHTML : '';
        if (copyBtn) {
            copyBtn.disabled = true;
            copyBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Generating...';
        }
        
        // Fetch the research prompt
        fetch(`/api/companies/${currentResearchCompanyId}/research-prompt`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Copy to clipboard
                navigator.clipboard.writeText(data.research_prompt).then(() => {
                    showSuccess(`Research prompt copied to clipboard! (${data.word_count} words)`);
                    addLogMessage(`Research prompt copied for ${data.company_name} (${data.prompt_length} characters)`);
                    
                    // Show temporary success state
                    if (copyBtn) {
                        copyBtn.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
                        copyBtn.classList.remove('btn-outline-info');
                        copyBtn.classList.add('btn-success');
                        
                        // Reset after 2 seconds
                        setTimeout(() => {
                            copyBtn.innerHTML = originalText;
                            copyBtn.classList.remove('btn-success');
                            copyBtn.classList.add('btn-outline-info');
                        }, 2000);
                    }
                    
                }).catch(err => {
                    console.error('Failed to copy to clipboard:', err);
                    // Fallback: show the prompt in a modal for manual copying
                    showPromptModal(data.research_prompt, data.company_name);
                });
                
            } else {
                throw new Error(data.message || 'Failed to generate research prompt');
            }
        })
        .catch(error => {
            console.error('Error fetching research prompt:', error);
            showError(`Failed to generate research prompt: ${error.message}`);
        })
        .finally(() => {
            // Restore button state
            if (copyBtn) {
                copyBtn.disabled = false;
                if (copyBtn.innerHTML.includes('Generating')) {
                    copyBtn.innerHTML = originalText;
                }
            }
        });
    };

    // Show prompt in modal for manual copying (fallback)
    function showPromptModal(prompt, companyName) {
        const modal = new bootstrap.Modal(document.getElementById('stepDetailModal'));
        const modalTitle = document.getElementById('stepDetailModalLabel');
        const modalContent = document.getElementById('stepDetailContent');
        
        modalTitle.textContent = `Research Prompt for ${companyName}`;
        modalContent.innerHTML = `
            <div class="mb-3">
                <label class="form-label">Copy this prompt to use in external deep research tools:</label>
                <textarea class="form-control" rows="12" readonly id="promptTextarea">${prompt}</textarea>
            </div>
            <div class="d-flex justify-content-between">
                <button class="btn btn-primary" onclick="document.getElementById('promptTextarea').select(); document.execCommand('copy'); showSuccess('Prompt copied to clipboard!');">
                    <i class="fas fa-copy me-1"></i>Copy to Clipboard
                </button>
                <div class="text-muted small">
                    ${prompt.length} characters • ${prompt.split(' ').length} words
                </div>
            </div>
        `;
        
        modal.show();
        
        // Auto-select the text for easy copying
        setTimeout(() => {
            const textarea = document.getElementById('promptTextarea');
            if (textarea) {
                textarea.select();
            }
        }, 500);
    }

})(); 