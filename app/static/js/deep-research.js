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

                console.log(`Deep Research button clicked for: ${companyName} (${companyId})`);
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

        // Modal focus and accessibility management
        const modal = document.getElementById('deepResearchModal');
        if (modal) {
            // Prevent modal from closing when research is in progress
            modal.addEventListener('hide.bs.modal', function(event) {
                if (isResearchInProgress) {
                    event.preventDefault();
                    event.stopPropagation();
                    
                    // Maintain proper ARIA attributes for accessibility
                    setTimeout(() => {
                        modal.removeAttribute('aria-hidden');
                        modal.setAttribute('aria-modal', 'true');
                        if (modal.style.display === 'none') {
                            modal.style.display = 'block';
                        }
                    }, 0);
                    
                    showError('Cannot close modal while research is in progress. Please stop the research first.');
                    return false;
                }
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
        currentResearchCompanyId = companyId;
        
        // Update modal title
        const modalTitle = document.getElementById('deepResearchCompanyName');
        if (modalTitle) {
            modalTitle.textContent = companyName;
        }

        // Reset modal state
        resetModalState();

        // Load current research progress
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
        fetch(`/api/companies/${companyId}/research/progress`)
            .then(response => response.json())
            .then(data => {
                console.log('Research progress loaded:', data);
                displayResearchProgress(data);
            })
            .catch(error => {
                console.error('Error loading research progress:', error);
                showError('Failed to load research progress');
            });
    }

    function displayResearchProgress(data) {
        // Handle the actual response structure from the API
        if (!data.success) {
            showError(data.error || 'Failed to load research progress');
            return;
        }
        
        const status = data.research_status || 'pending';
        
        // Update company URL (we'll need to get it from the company details separately)
        const urlElement = document.getElementById('deepResearchCompanyUrl');
        if (urlElement) {
            urlElement.textContent = ''; // We'll populate this from company details if needed
        }

        // Display progress based on status
        displayProgressBar(data);
        displayResearchSteps(data);
        updateActionButtons(status, data);

        // Start polling if research is in progress
        if (status === 'in_progress') {
            isResearchInProgress = true;
            startProgressPolling();
            showResearchLog();
        }
    }

    function displayProgressBar(data) {
        const progressContainer = document.getElementById('deepResearchProgress');
        if (!progressContainer) return;

        const status = data.research_status || 'pending';
        const completedSteps = data.steps_completed || 0;
        const totalSteps = data.total_steps || 3;

        const progressPercentage = status === 'completed' ? 100 : (completedSteps / totalSteps) * 100;

        let progressClass = 'bg-info';
        if (status === 'completed') progressClass = 'bg-success';
        else if (status === 'failed') progressClass = 'bg-danger';
        else if (status === 'in_progress') progressClass = 'bg-warning';

        progressContainer.innerHTML = `
            <div class="research-progress-header mb-3">
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">Research Progress</h6>
                    <span class="badge ${getStatusBadgeClass(status)}">${status.replace('_', ' ').toUpperCase()}</span>
                </div>
            </div>
            <div class="progress mb-2" style="height: 20px;">
                <div class="progress-bar ${progressClass}" role="progressbar" 
                     style="width: ${progressPercentage}%" 
                     aria-valuenow="${progressPercentage}" 
                     aria-valuemin="0" 
                     aria-valuemax="100">
                    ${Math.round(progressPercentage)}%
                </div>
            </div>
            <div class="d-flex justify-content-between small text-muted">
                <span>0%</span>
                <span>${completedSteps} of ${totalSteps} steps completed</span>
                <span>100%</span>
            </div>
        `;
    }

    function displayResearchSteps(data) {
        const stepsContainer = document.getElementById('deepResearchSteps');
        if (!stepsContainer) return;

        const steps = [
            { 
                name: 'Basic Research', 
                key: 'step_1',
                description: 'Gathering basic company information and overview',
                icon: 'fas fa-search'
            },
            { 
                name: 'Strategic Analysis', 
                key: 'step_2',
                description: 'Analyzing business strategy and competitive position',
                icon: 'fas fa-chart-line'
            },
            { 
                name: 'Final Report', 
                key: 'step_3',
                description: 'Generating comprehensive markdown report',
                icon: 'fas fa-file-alt'
            }
        ];

        let stepsHtml = '<div class="research-steps-container">';
        
        steps.forEach((step, index) => {
            const stepStatus = data.step_statuses?.[step.key];
            const isCompleted = stepStatus?.completed || false;
            const isActive = data.research_status === 'in_progress' && !isCompleted;
            
            let stepClass = 'step-pending';
            if (isCompleted) stepClass = 'step-completed';
            else if (isActive) stepClass = 'step-active';

            stepsHtml += `
                <div class="research-step ${stepClass}" data-step="${index + 1}">
                    <div class="step-header d-flex align-items-center">
                        <div class="step-icon me-3">
                            <i class="${step.icon}"></i>
                        </div>
                        <div class="step-info flex-grow-1">
                            <h6 class="step-title mb-1">${step.name}</h6>
                            <p class="step-description mb-0 text-muted">${step.description}</p>
                        </div>
                        <div class="step-status ms-2">
                            ${isCompleted ? '<i class="fas fa-check-circle text-success"></i>' : 
                              isActive ? '<div class="spinner-border spinner-border-sm text-warning" role="status"></div>' :
                              '<i class="fas fa-circle text-muted"></i>'}
                        </div>
                        ${isCompleted ? `
                            <button class="btn btn-sm btn-outline-primary ms-2" onclick="window.viewStepContent(${index + 1})">
                                <i class="fas fa-eye"></i> View
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;
        });
        
        stepsHtml += '</div>';
        stepsContainer.innerHTML = stepsHtml;
    }

    function updateActionButtons(status, data = null) {
        const startBtn = document.getElementById('startDeepResearchBtn');
        const forceBtn = document.getElementById('forceRefreshDeepBtn');
        const resumeBtn = document.getElementById('resumeDeepResearchBtn');
        const stopBtn = document.getElementById('stopResearchBtn');
        const viewReportBtn = document.getElementById('viewStrategicReportBtn');
        const reportFormatButtons = document.getElementById('reportFormatButtons');
        const publishBtn = document.getElementById('publishReportBtn');

        // Hide all buttons first
        [startBtn, forceBtn, resumeBtn, stopBtn, viewReportBtn, publishBtn].forEach(btn => {
            if (btn) btn.style.display = 'none';
        });

        // Hide report format buttons
        if (reportFormatButtons) reportFormatButtons.style.display = 'none';

        switch (status) {
            case 'loading':
                // Show loading state
                break;
            case 'pending':
                if (startBtn) startBtn.style.display = 'inline-block';
                break;
            case 'in_progress':
                if (stopBtn) stopBtn.style.display = 'inline-block';
                break;
            case 'completed':
                if (forceBtn) forceBtn.style.display = 'inline-block';
                if (viewReportBtn) viewReportBtn.style.display = 'inline-block';
                if (reportFormatButtons) reportFormatButtons.style.display = 'inline-block';
                if (publishBtn) publishBtn.style.display = 'inline-block';
                updateReportLinks();
                break;
            case 'failed':
                if (resumeBtn) resumeBtn.style.display = 'inline-block';
                if (startBtn) startBtn.style.display = 'inline-block';
                break;
            default:
                if (startBtn) startBtn.style.display = 'inline-block';
        }
    }

    function updateReportLinks() {
        if (!currentResearchCompanyId) return;

        const htmlReportLink = document.getElementById('viewHtmlReportLink');
        const pdfReportLink = document.getElementById('downloadPdfReportLink');
        const embedReportLink = document.getElementById('viewEmbedReportLink');

        if (htmlReportLink) {
            htmlReportLink.href = `/api/public/reports/${currentResearchCompanyId}`;
        }
        if (pdfReportLink) {
            pdfReportLink.href = `/api/public/reports/${currentResearchCompanyId}/pdf`;
        }
        if (embedReportLink) {
            embedReportLink.href = `/api/public/reports/${currentResearchCompanyId}/embed`;
        }
    }

    function viewStrategicReport() {
        if (!currentResearchCompanyId) return;
        
        // Open the HTML report in a new tab
        const reportUrl = `/api/public/reports/${currentResearchCompanyId}`;
        window.open(reportUrl, '_blank');
    }

    function startDeepResearch(forceRefresh = false) {
        if (!currentResearchCompanyId) return;

        const url = `/api/companies/${currentResearchCompanyId}/research`;
        const method = 'POST';
        const body = forceRefresh ? JSON.stringify({ force_refresh: true }) : JSON.stringify({});

        isResearchInProgress = true;
        showResearchLog();
        addLogMessage('Starting deep research process...');

        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: body
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                addLogMessage('Research started successfully');
                updateActionButtons('in_progress');
                startProgressPolling();
            } else {
                addLogMessage(`Error: ${data.error}`);
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
        if (!currentResearchCompanyId) return;

        addLogMessage('Resuming research process...');
        
        fetch(`/api/companies/${currentResearchCompanyId}/research/resume`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                addLogMessage('Research resumed successfully');
                isResearchInProgress = true;
                updateActionButtons('in_progress');
                startProgressPolling();
            } else {
                addLogMessage(`Error: ${data.error}`);
                showError(data.error);
            }
        })
        .catch(error => {
            console.error('Error resuming research:', error);
            addLogMessage(`Error: ${error.message}`);
            showError('Failed to resume research');
        });
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

            fetch(`/api/companies/${currentResearchCompanyId}/research/progress`)
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        addLogMessage(`Progress error: ${data.error || 'Unknown error'}`);
                        return;
                    }
                    
                    displayProgressBar(data);
                    displayResearchSteps(data);

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
        const logContainer = document.getElementById('deepResearchLog');
        if (logContainer) {
            logContainer.style.display = 'block';
        }
    }

    function addLogMessage(message) {
        const logContent = document.getElementById('logContent');
        if (logContent) {
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = `<div class="log-entry">[${timestamp}] ${message}</div>`;
            logContent.innerHTML += logEntry;
            logContent.scrollTop = logContent.scrollHeight;
        }
    }

    // Global functions that need to be accessible from HTML
    window.toggleResearchLog = function() {
        const logContainer = document.querySelector('.log-container');
        if (logContainer) {
            logContainer.style.display = logContainer.style.display === 'none' ? 'block' : 'none';
        }
    };

    window.viewStepContent = function(stepNumber) {
        if (!currentResearchCompanyId) return;

        fetch(`/api/companies/${currentResearchCompanyId}/research/step/${stepNumber}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showStepDetailModal(data.step_title, data.content, stepNumber);
                } else {
                    showError('Failed to load step content');
                }
            })
            .catch(error => {
                console.error('Error loading step content:', error);
                showError('Failed to load step content');
            });
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
                if (!company.markdown_report) {
                    throw new Error('No markdown report available to publish');
                }

                // Show publish status as loading
                showPublishStatus('loading', 'Publishing report to possibleminds.in...');

                // Prepare payload for Netlify function
                const payload = {
                    company_name: company.company_name,
                    markdown_report: company.markdown_report,
                    company_website: company.website_url || ''
                };

                // Make the publish request
                return fetch('https://possibleminds.in/.netlify/functions/publish-report', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
            })
            .then(response => {
                if (!response.ok) {
                    // Try to get response text for better error messages
                    return response.text().then(text => {
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



})(); 