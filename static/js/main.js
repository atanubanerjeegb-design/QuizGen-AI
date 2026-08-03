/**
 * QuizGen.AI - Global Javascript Utilities
 */

document.addEventListener('DOMContentLoaded', function() {
    // Automatically fade out and dismiss flash alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-custom');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

/**
 * Retrieves the global CSRF token from head meta tags.
 * @returns {string} The active CSRF token value.
 */
function getCsrfToken() {
    const tokenMeta = document.querySelector('meta[name="csrf-token"]');
    return tokenMeta ? tokenMeta.getAttribute('content') : '';
}

/**
 * Creates and displays a dynamic toast notification.
 * @param {string} message - Notification text.
 * @param {string} type - 'success', 'danger', 'info', or 'warning'.
 */
function showToast(message, type = 'info') {
    // Check if container exists, create if not
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '1100';
        document.body.appendChild(toastContainer);
    }

    const toastId = 'toast-' + Date.now();
    const borderClass = {
        'success': 'border-success',
        'danger': 'border-danger',
        'warning': 'border-warning',
        'info': 'border-cyan'
    }[type] || 'border-primary';

    const iconClass = {
        'success': 'fa-circle-check text-success',
        'danger': 'fa-circle-exclamation text-danger',
        'warning': 'fa-triangle-exclamation text-warning',
        'info': 'fa-circle-info text-info'
    }[type] || 'fa-circle-info';

    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white bg-dark border ${borderClass} show" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="4000">
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center">
                    <i class="fa-solid ${iconClass} me-2 fs-5"></i>
                    <div>${message}</div>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(toastId);
    const bsToast = new bootstrap.Toast(toastElement);
    bsToast.show();

    // Remove element from DOM after hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}
