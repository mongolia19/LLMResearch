/**
 * Chat interface for the LLMResearch WebUI.
 */
class ChatInterface {
    /**
     * Initialize the chat interface.
     * 
     * @param {HTMLElement} messagesContainer - The container for chat messages
     * @param {HTMLElement} inputElement - The input element for user messages
     * @param {HTMLElement} sendButton - The button to send messages
     */
    constructor(messagesContainer, inputElement, sendButton) {
        this.messagesContainer = messagesContainer;
        this.inputElement = inputElement;
        this.sendButton = sendButton;
        this.contextFiles = [];
        this.onSendCallback = null;
        this.messageIdCounter = 0;
        
        // Set up event listeners
        this.setupEventListeners();
    }
    
    /**
     * Set up event listeners for the chat interface.
     */
    setupEventListeners() {
        // Send button click event
        this.sendButton.addEventListener('click', () => {
            this.sendMessage();
        });
        
        // Input keydown event (Enter to send)
        this.inputElement.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea
        this.inputElement.addEventListener('input', () => {
            this.inputElement.style.height = 'auto';
            this.inputElement.style.height = `${Math.min(this.inputElement.scrollHeight, 200)}px`;
        });
    }
    
    /**
     * Send a message.
     */
    sendMessage() {
        const message = this.inputElement.value.trim();
        
        if (!message) {
            return;
        }
        
        // Clear the input
        this.inputElement.value = '';
        this.inputElement.style.height = 'auto';
        
        // Call the send callback if set
        if (this.onSendCallback) {
            this.onSendCallback(message);
        }
        
        // Re-enable input after sending
        this.setInputEnabled(true);
    }
    
    /**
     * Add a message to the chat.
     * 
     * @param {string} role - The role of the message sender ('user', 'assistant', or 'system')
     * @param {string} content - The message content
     * @param {string} id - Optional message ID for updating later
     * @returns {string} - The message ID
     */
    addMessage(role, content, id = null) {
        // Generate a message ID if not provided
        const messageId = id || `msg-${++this.messageIdCounter}`;
        
        // Create the message element
        const messageElement = document.createElement('div');
        messageElement.className = `message ${role}`;
        messageElement.id = messageId;
        
        // Create the message content element
        const contentElement = document.createElement('div');
        contentElement.className = 'message-content';
        contentElement.innerHTML = this.formatMessageContent(content);
        
        // Add the content to the message
        messageElement.appendChild(contentElement);
        
        // Add the message to the container
        this.messagesContainer.appendChild(messageElement);
        
        // Scroll to the bottom
        this.scrollToBottom();
        
        return messageId;
    }
    
    /**
     * Append content to an existing message.
     * 
     * @param {string} role - The role of the message sender
     * @param {string} content - The content to append
     * @param {string} id - The message ID
     */
    appendToMessage(role, content, id) {
        const messageElement = document.getElementById(id);
        
        if (!messageElement) {
            return this.addMessage(role, content, id);
        }
        
        const contentElement = messageElement.querySelector('.message-content');
        const currentContent = contentElement.innerHTML;
        contentElement.innerHTML = this.formatMessageContent(currentContent + content);
        
        // Scroll to the bottom
        this.scrollToBottom();
    }
    
    /**
     * Format message content for display.
     * 
     * @param {string} content - The raw message content
     * @returns {string} - The formatted content
     */
    formatMessageContent(content) {
        // Replace newlines with <br>
        let formatted = content.replace(/\n/g, '<br>');
        
        // Format code blocks
        formatted = formatted.replace(/```([a-z]*)\n([\s\S]*?)\n```/g, (match, language, code) => {
            return `<pre><code class="language-${language}">${this.escapeHtml(code)}</code></pre>`;
        });
        
        // Format inline code
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        return formatted;
    }
    
    /**
     * Escape HTML special characters.
     * 
     * @param {string} html - The HTML to escape
     * @returns {string} - The escaped HTML
     */
    escapeHtml(html) {
        const div = document.createElement('div');
        div.textContent = html;
        return div.innerHTML;
    }
    
    /**
     * Scroll the messages container to the bottom.
     */
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    /**
     * Set the callback for when a message is sent.
     * 
     * @param {Function} callback - The callback function
     */
    onSendMessage(callback) {
        this.onSendCallback = callback;
    }
    
    /**
     * Enable or disable the input.
     * 
     * @param {boolean} enabled - Whether the input should be enabled
     */
    setInputEnabled(enabled) {
        this.inputElement.disabled = !enabled;
        this.sendButton.disabled = !enabled;
        
        if (enabled) {
            this.inputElement.focus();
        }
    }
    
    /**
     * Add a context file.
     * 
     * @param {string} filePath - The path to the file
     */
    addContextFile(filePath) {
        if (!this.contextFiles.includes(filePath)) {
            this.contextFiles.push(filePath);
        }
    }
    
    /**
     * Get the context files.
     * 
     * @returns {string[]} - The context files
     */
    getContextFiles() {
        return this.contextFiles;
    }
    
    /**
     * Clear the context files.
     */
    clearContextFiles() {
        this.contextFiles = [];
    }
    
    /**
     * Clear the chat history.
     */
    clearHistory() {
        // Keep system and assistant messages (preserve reasoning process)
        const preservedMessages = Array.from(this.messagesContainer.querySelectorAll('.message.system, .message.assistant'));
        
        // Clear the container
        this.messagesContainer.innerHTML = '';
        
        // Add back the preserved messages
        preservedMessages.forEach(message => {
            this.messagesContainer.appendChild(message);
        });
        
        // Add a system message indicating the history was cleared
        this.addMessage('system', '聊天历史已清除');
    }

    /**
     * Show reasoning steps in the input area.
     *
     * @param {string} content - The content to display
     */
    showReasoningSteps(content) {
        // Add to chat history first
        const messageId = this.addMessage('system', content);
        
        // Create a temporary element to hold the content
        const tempElement = document.createElement('div');
        tempElement.className = 'reasoning-steps';
        tempElement.innerHTML = this.formatMessageContent(content);
        
        // Insert before the input element
        this.inputElement.parentNode.insertBefore(tempElement, this.inputElement);
        
        // Scroll to show the new content
        this.scrollToBottom();
    }
}
