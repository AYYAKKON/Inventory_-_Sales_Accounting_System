// Inventory Management System - JavaScript

// Document Ready
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    applySmoothScrolling();
});

/**
 * Initialize all event listeners
 */
function initializeEventListeners() {
    // Auto-dismiss alerts after 5 seconds
    dismissAlerts();
    
    // Image thumbnail navigation
    initImageThumbnails();
    
    // Form validation
    initFormValidation();
    
    // Search functionality
    initSearch();
}

/**
 * Auto-dismiss alert messages
 */
function dismissAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-persistent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}

/**
 * Initialize image thumbnail navigation
 */
function initImageThumbnails() {
    const thumbnails = document.querySelectorAll('.thumbnail-img');
    const carousel = document.querySelector('#productCarousel');
    
    if (!carousel) return;
    
    thumbnails.forEach((thumb, index) => {
        thumb.addEventListener('click', function() {
            const carouselInstance = bootstrap.Carousel.getInstance(carousel);
            carouselInstance.to(index);
            
            // Update active state
            thumbnails.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Update thumbnail active state when carousel changes
    carousel.addEventListener('slide.bs.carousel', function(event) {
        thumbnails.forEach((thumb, index) => {
            thumb.classList.toggle('active', index === event.to);
        });
    });
}

/**
 * Initialize form validation
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!this.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            this.classList.add('was-validated');
        });
    });
}

/**
 * Initialize search functionality
 */
function initSearch() {
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function() {
            // Could add autocomplete or real-time search here
            console.log('Search query:', this.value);
        }, 300));
    }
}

/**
 * Debounce function for search input
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func.apply(this, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Smooth scrolling for anchor links
 */
function applySmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Format currency for display
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}

/**
 * Show confirmation dialog before deletion
 */
function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this item?');
}

/**
 * Loading state for buttons
 */
function setButtonLoading(button, isLoading) {
    if (isLoading) {
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
        button.classList.add('loading');
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalText;
        button.classList.remove('loading');
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toastHtml = `
        <div class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    const toastElement = document.createElement('div');
    toastElement.innerHTML = toastHtml;
    toastContainer.appendChild(toastElement.firstElementChild);
    
    const bsToast = new bootstrap.Toast(toastElement.firstElementChild);
    bsToast.show();
}

/**
 * Create toast container if it doesn't exist
 */
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}

/**
 * Update stock display
 */
function updateStockDisplay(quantity, lowStockLevel) {
    const stockBadge = document.querySelector('[data-stock-badge]');
    if (!stockBadge) return;
    
    stockBadge.classList.remove('bg-success', 'bg-warning', 'bg-danger', 'bg-secondary');
    
    if (quantity === 0) {
        stockBadge.classList.add('bg-secondary');
        stockBadge.textContent = 'Out of Stock';
    } else if (quantity <= lowStockLevel) {
        stockBadge.classList.add('bg-danger');
        stockBadge.textContent = `${quantity} units (Low Stock)`;
    } else {
        stockBadge.classList.add('bg-success');
        stockBadge.textContent = `${quantity} units`;
    }
}

/**
 * Initialize tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize popovers
 */
function initializePopovers() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Export functions for use in other scripts
window.inventory = {
    formatCurrency,
    confirmDelete,
    setButtonLoading,
    showToast,
    updateStockDisplay,
    initializeTooltips,
    initializePopovers
};
