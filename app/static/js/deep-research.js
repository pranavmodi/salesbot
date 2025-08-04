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
        // Determine which research type is selected to use the correct endpoint
        const selectedResearchType = getSelectedResearchType();
        const progressUrl = getProgressUrl(selectedResearchType);
        
        fetch(progressUrl)
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
        
        // Determine if this is LLM research or standard research
        const selectedResearchType = getSelectedResearchType();
        const isLLMResearch = selectedResearchType === 'llm_step_by_step';
        
        let status;
        if (isLLMResearch) {
            // LLM research has different status structure
            status = data.current_status || 'not_started';
            if (data.current_step === 'completed') status = 'completed';
            else if (data.current_status && data.current_status.includes('error')) status = 'failed';
            else if (data.current_step && data.current_step.startsWith('step_')) status = 'in_progress';
        } else {
            status = data.research_status || 'pending';
        }
        
        // Update company URL (we'll need to get it from the company details separately)
        const urlElement = document.getElementById('deepResearchCompanyUrl');
        if (urlElement) {
            urlElement.textContent = ''; // We'll populate this from company details if needed
        }

        // Always display LLM research progress
        updateLLMResearchProgress(data);
        
        updateActionButtons(status, data);

        // Start polling if research is in progress
        if (status === 'in_progress') {
            isResearchInProgress = true;
            startProgressPolling();
            showResearchLog();
        }
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

        // BULLETPROOF: Prevent multiple concurrent requests
        if (isResearchInProgress) {
            showError('Research already in progress. Please wait for completion.');
            return;
        }

        const selectedResearchType = getSelectedResearchType();
        const researchConfig = getResearchConfig(selectedResearchType, forceRefresh);
        
        isResearchInProgress = true;
        showResearchLog();
        addLogMessage('Starting AI Deep Research process...');
        
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
        return 'llm_step_by_step';
    }

    function getResearchConfig(researchType, forceRefresh = false) {
        const baseConfig = {
            force_refresh: forceRefresh || document.getElementById('forceRefreshOption')?.checked || false
        };

        // Always use LLM deep research
        const provider = document.getElementById('llmProviderSelect')?.value || 'claude';
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
        // Always use LLM research progress
        updateLLMResearchProgress(data);
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



})(); 