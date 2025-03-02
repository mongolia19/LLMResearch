/**
 * API client for the LLMResearch WebUI.
 */
class ApiClient {
    /**
     * Initialize the API client.
     */
    constructor() {
        this.baseUrl = window.location.origin;
        this.activeConversationId = null;
        this.activeReasoningSessionId = null;
    }

    /**
     * Send a message to the API.
     * 
     * @param {string} message - The message to send
     * @param {Object} options - Additional options
     * @returns {Promise<Object>} - The API response
     */
    async sendMessage(message, options = {}) {
        try {
            const response = await fetch(`${this.baseUrl}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.activeConversationId,
                    provider: options.provider,
                    temperature: options.temperature,
                    max_tokens: options.max_tokens,
                    context_files: options.context_files || []
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to send message');
            }

            const data = await response.json();
            this.activeConversationId = data.conversation_id;
            return data;
        } catch (error) {
            console.error('API error:', error);
            throw error;
        }
    }

    /**
     * Start a reasoning task.
     * 
     * @param {string} task - The task to reason about
     * @param {Object} options - Additional options
     * @returns {Promise<Object>} - The API response
     */
    async startReasoning(task, options = {}) {
        try {
            const response = await fetch(`${this.baseUrl}/api/reasoning`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task: task,
                    steps: options.steps || 5,
                    provider: options.provider,
                    temperature: options.temperature,
                    max_tokens: options.max_tokens,
                    web_search: options.web_search,
                    extract_url: options.extract_url,
                    retries: options.retries || 3,
                    context_files: options.context_files || [],
                    conversation_id: this.activeConversationId  // Pass the active conversation ID
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to start reasoning');
            }

            const data = await response.json();
            this.activeReasoningSessionId = data.session_id;
            return data;
        } catch (error) {
            console.error('API error:', error);
            throw error;
        }
    }

    /**
     * Get the list of available LLM providers.
     * 
     * @returns {Promise<Object>} - The API response
     */
    async getProviders() {
        try {
            const response = await fetch(`${this.baseUrl}/api/providers`);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to get providers');
            }

            return await response.json();
        } catch (error) {
            console.error('API error:', error);
            throw error;
        }
    }

    /**
     * Upload a file.
     * 
     * @param {File} file - The file to upload
     * @returns {Promise<Object>} - The API response
     */
    async uploadFile(file) {
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${this.baseUrl}/api/files`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to upload file');
            }

            return await response.json();
        } catch (error) {
            console.error('API error:', error);
            throw error;
        }
    }

    /**
     * Get WebUI settings.
     * 
     * @returns {Promise<Object>} - The API response
     */
    async getSettings() {
        try {
            const response = await fetch(`${this.baseUrl}/api/settings`);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to get settings');
            }

            return await response.json();
        } catch (error) {
            console.error('API error:', error);
            throw error;
        }
    }

    /**
     * Update WebUI settings.
     * 
     * @param {Object} settings - The settings to update
     * @returns {Promise<Object>} - The API response
     */
    async updateSettings(settings) {
        try {
            const response = await fetch(`${this.baseUrl}/api/settings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to update settings');
            }

            return await response.json();
        } catch (error) {
            console.error('API error:', error);
            throw error;
        }
    }
}