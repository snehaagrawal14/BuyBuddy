/**
 * BuyBuddy Demo Interface JavaScript
 * Handles interactive elements on the demo page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Handle the product selection form
    const productForm = document.getElementById('productForm');
    const productSelect = document.getElementById('productSelect');
    
    if (productForm) {
        productForm.addEventListener('submit', function(e) {
            // Ensure at least one product is selected
            if (productSelect.selectedOptions.length === 0) {
                e.preventDefault();
                alert('Please select at least one product to get recommendations');
            }
        });
    }
    
    // Initialize tooltips if using Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (typeof bootstrap !== 'undefined') {
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Add highlighting effect to recommendation items
    const recommendationItems = document.querySelectorAll('.recommended-products .card');
    recommendationItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.classList.add('border-primary');
        });
        
        item.addEventListener('mouseleave', function() {
            this.classList.remove('border-primary');
        });
    });
    
    // Format confidence and support values to percentage display
    const formatPercentages = () => {
        const percentElements = document.querySelectorAll('[data-format="percent"]');
        percentElements.forEach(el => {
            const value = parseFloat(el.textContent);
            if (!isNaN(value)) {
                el.textContent = `${(value * 100).toFixed(1)}%`;
            }
        });
    };
    
    // Apply percentage formatting
    formatPercentages();
    
    // Copy API response to clipboard functionality
    const apiResponseElement = document.querySelector('.api-response');
    if (apiResponseElement) {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'btn btn-sm btn-outline-light position-absolute top-0 end-0 m-2';
        copyBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
        copyBtn.title = 'Copy to clipboard';
        
        copyBtn.addEventListener('click', function() {
            const code = apiResponseElement.querySelector('code');
            const textArea = document.createElement('textarea');
            textArea.value = code.textContent;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            
            // Show feedback
            this.innerHTML = '<i class="bi bi-check-lg"></i>';
            setTimeout(() => {
                this.innerHTML = '<i class="bi bi-clipboard"></i>';
            }, 1500);
        });
        
        apiResponseElement.style.position = 'relative';
        apiResponseElement.appendChild(copyBtn);
    }
    
    // Add custom behavior for multi-select on mobile
    if (productSelect && window.innerWidth < 768) {
        productSelect.addEventListener('touchend', function(e) {
            // Add custom handling for better mobile experience if needed
            const instructionText = document.querySelector('.form-text');
            if (instructionText) {
                instructionText.textContent = 'Tap items to select multiple products';
            }
        });
    }
});
