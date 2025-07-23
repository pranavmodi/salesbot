// SalesBot CRM - Utility Functions

// Pagination utility functions
function addPaginationLoadingState(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.style.opacity = '0.6';
        container.style.pointerEvents = 'none';
    }
}

function removePaginationLoadingState(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.style.opacity = '1';
        container.style.pointerEvents = 'auto';
    }
}

function generatePageNumbers(currentPage, totalPages, linkClass, dataAttribute) {
    let paginationHTML = '';
    const maxVisiblePages = 5;
    
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const activeClass = i === currentPage ? 'active' : '';
        paginationHTML += `
            <li class="page-item ${activeClass}">
                <a class="page-link ${linkClass}" href="#" ${dataAttribute}="${i}">${i}</a>
            </li>
        `;
    }
    
    return paginationHTML;
}

// Toast notification functions
function showToast(toastId, message) {
    let toastElement = document.getElementById(toastId);
    
    if (!toastElement) {
        toastElement = createToast(toastId, message);
    } else {
        const toastBody = toastElement.querySelector('.toast-body');
        if (toastBody) {
            toastBody.textContent = message;
        }
    }
    
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 3000
    });
    toast.show();
}

function createToast(id, message) {
    const toastHTML = `
        <div id="${id}" class="toast align-items-center text-white bg-success border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    return document.getElementById(id);
}

// Progress bar utility
function updateProgressBar(progressId, countId, value, total) {
    const progressBar = document.getElementById(progressId);
    const countElement = document.getElementById(countId);
    const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
    
    if (progressBar) {
        progressBar.style.width = percentage + '%';
        progressBar.setAttribute('aria-valuenow', percentage);
    }
    if (countElement) {
        countElement.textContent = `${value}/${total}`;
    }
}

// Status badge utilities
function getStatusBadge(status) {
    const badgeClass = getStatusBadgeClass(status);
    return `<span class="badge ${badgeClass}">${status}</span>`;
}

function getStatusBadgeClass(status) {
    switch(status?.toLowerCase()) {
        case 'active': return 'bg-success';
        case 'paused': return 'bg-warning text-dark';
        case 'completed': return 'bg-primary';
        case 'draft': return 'bg-secondary';
        case 'scheduled': return 'bg-info';
        default: return 'bg-light text-dark';
    }
}

function getPriorityBadge(priority) {
    const badgeClass = getPriorityBadgeClass(priority);
    return `<span class="badge ${badgeClass}">${priority}</span>`;
}

function getPriorityBadgeClass(priority) {
    switch(priority?.toLowerCase()) {
        case 'high': return 'bg-danger';
        case 'medium': return 'bg-warning text-dark';
        case 'low': return 'bg-success';
        default: return 'bg-secondary';
    }
}

// Icon utilities for email status
function getEmailStatusIcon(status) {
    switch(status?.toLowerCase()) {
        case 'sent': return 'fas fa-check-circle text-success';
        case 'delivered': return 'fas fa-envelope text-primary';
        case 'opened': return 'fas fa-envelope-open text-info';
        case 'clicked': return 'fas fa-mouse-pointer text-warning';
        case 'replied': return 'fas fa-reply text-success';
        case 'bounced': return 'fas fa-exclamation-triangle text-danger';
        case 'failed': return 'fas fa-times-circle text-danger';
        default: return 'fas fa-clock text-muted';
    }
}

function getEmailStatusClass(status) {
    switch(status?.toLowerCase()) {
        case 'sent': return 'text-success';
        case 'delivered': return 'text-primary';
        case 'opened': return 'text-info';
        case 'clicked': return 'text-warning';
        case 'replied': return 'text-success';
        case 'bounced': return 'text-danger';
        case 'failed': return 'text-danger';
        default: return 'text-muted';
    }
}

// Log level utilities
function getLogLevelIcon(level) {
    switch(level?.toLowerCase()) {
        case 'info': return 'fas fa-info-circle text-info';
        case 'warning': return 'fas fa-exclamation-triangle text-warning';
        case 'error': return 'fas fa-times-circle text-danger';
        case 'success': return 'fas fa-check-circle text-success';
        default: return 'fas fa-circle text-muted';
    }
}

function getLogLevelClass(level) {
    switch(level?.toLowerCase()) {
        case 'info': return 'text-info';
        case 'warning': return 'text-warning';
        case 'error': return 'text-danger';
        case 'success': return 'text-success';
        default: return 'text-muted';
    }
}

// Action type utilities
function getActionTypeIcon(type) {
    switch(type?.toLowerCase()) {
        case 'email': return 'fas fa-envelope';
        case 'follow_up': return 'fas fa-clock';
        case 'research': return 'fas fa-search';
        case 'call': return 'fas fa-phone';
        default: return 'fas fa-tasks';
    }
}

function getActionTypeClass(type) {
    switch(type?.toLowerCase()) {
        case 'email': return 'text-primary';
        case 'follow_up': return 'text-warning';
        case 'research': return 'text-info';
        case 'call': return 'text-success';
        default: return 'text-muted';
    }
}

// Email template display name utility
function getEmailTemplateDisplayName(template) {
    const templates = {
        'cold_outreach': 'Cold Outreach',
        'follow_up': 'Follow Up',
        'introduction': 'Introduction',
        'meeting_request': 'Meeting Request',
        'warm': '🤝 Warm Outreach',
        'alt_subject': '📧 Alternative Subject',
        'deep_research': '🔬 Deep Research',
        'possible_minds': '🏢 Possible Minds Template',
        'custom': 'Custom Template'
    };
    return templates[template] || template;
}

// Export utilities for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        addPaginationLoadingState,
        removePaginationLoadingState,
        generatePageNumbers,
        showToast,
        createToast,
        updateProgressBar,
        getStatusBadge,
        getStatusBadgeClass,
        getPriorityBadge,
        getPriorityBadgeClass,
        getEmailStatusIcon,
        getEmailStatusClass,
        getLogLevelIcon,
        getLogLevelClass,
        getActionTypeIcon,
        getActionTypeClass,
        getEmailTemplateDisplayName
    };
}