/**
 * BuyBuddy API Integration JavaScript
 * Helper functions for interacting with the BuyBuddy API
 */

class BuyBuddyAPI {
    constructor(apiKey = null) {
        this.apiKey = apiKey;
        this.baseUrl = '/api';
    }
    
    /**
     * Set API key for authentication
     * @param {string} apiKey - The API key to use for requests
     */
    setApiKey(apiKey) {
        this.apiKey = apiKey;
    }
    
    /**
     * Get product recommendations
     * @param {Array} productIds - Array of product IDs to get recommendations for
     * @param {Object} options - Additional options (limit, min_confidence)
     * @returns {Promise} - Promise resolving to recommendations
     */
    async getRecommendations(productIds, options = {}) {
        if (!productIds || !productIds.length) {
            throw new Error('Product IDs are required');
        }
        
        const payload = {
            product_ids: productIds,
            limit: options.limit || 5,
            min_confidence: options.minConfidence || 0.1
        };
        
        return this._makeRequest(`${this.baseUrl}/recommend`, 'POST', payload);
    }
    
    /**
     * Upload product data
     * @param {Array} products - Array of product objects
     * @returns {Promise} - Promise resolving to upload result
     */
    async uploadProducts(products) {
        if (!products || !products.length) {
            throw new Error('Products array is required');
        }
        
        return this._makeRequest(`${this.baseUrl}/products`, 'POST', { products });
    }
    
    /**
     * Upload transaction data
     * @param {Array} transactions - Array of transaction objects
     * @returns {Promise} - Promise resolving to upload result
     */
    async uploadTransactions(transactions) {
        if (!transactions || !transactions.length) {
            throw new Error('Transactions array is required');
        }
        
        return this._makeRequest(`${this.baseUrl}/transactions`, 'POST', { transactions });
    }
    
    /**
     * Get configuration
     * @returns {Promise} - Promise resolving to current configuration
     */
    async getConfig() {
        return this._makeRequest(`${this.baseUrl}/config`, 'GET');
    }
    
    /**
     * Update configuration
     * @param {Object} config - Configuration parameters to update
     * @returns {Promise} - Promise resolving to updated configuration
     */
    async updateConfig(config) {
        return this._makeRequest(`${this.baseUrl}/config`, 'PUT', config);
    }
    
    /**
     * Check job status
     * @param {number} jobId - ID of the job to check
     * @returns {Promise} - Promise resolving to job status
     */
    async checkJobStatus(jobId) {
        if (!jobId) {
            throw new Error('Job ID is required');
        }
        
        return this._makeRequest(`${this.baseUrl}/jobs/${jobId}`, 'GET');
    }
    
    /**
     * Make API request
     * @param {string} url - URL to request
     * @param {string} method - HTTP method
     * @param {Object} data - Request data
     * @returns {Promise} - Promise resolving to response data
     * @private
     */
    async _makeRequest(url, method, data = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        // Add API key if available
        if (this.apiKey) {
            options.headers['X-API-Key'] = this.apiKey;
        }
        
        // Add request body for POST/PUT requests
        if (data && (method === 'POST' || method === 'PUT')) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            const responseData = await response.json();
            
            if (!response.ok) {
                throw new Error(responseData.error || 'API request failed');
            }
            
            return responseData;
        } catch (error) {
            console.error('API request error:', error);
            throw error;
        }
    }
}

// Initialize with demo API key if available
const buyBuddyApi = new BuyBuddyAPI();

// Export for module usage
if (typeof module !== 'undefined' && typeof module.exports !== 'undefined') {
    module.exports = BuyBuddyAPI;
}
