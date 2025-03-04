/**
 * Reasoning interface for the LLMResearch WebUI.
 */
class ReasoningInterface {
    /**
     * Initialize the reasoning interface.
     * 
     * @param {HTMLElement} reasoningModal - The reasoning modal element
     * @param {HTMLElement} reasoningTask - The reasoning task input element
     * @param {HTMLElement} reasoningStepsInput - The reasoning steps input element
     * @param {HTMLElement} startReasoningButton - The button to start reasoning
     * @param {HTMLElement} cancelReasoningButton - The button to cancel reasoning
     * @param {HTMLElement} reasoningProgress - The reasoning progress element
     * @param {HTMLElement} reasoningProgressBar - The reasoning progress bar element
     * @param {HTMLElement} reasoningStatus - The reasoning status element
     * @param {ChatInterface} chatInterface - The chat interface
     * @param {ApiClient} apiClient - The API client
     * @param {SettingsPanel} settingsPanel - The settings panel
     */
    constructor(
        reasoningModal,
        reasoningTask,
        reasoningStepsInput,
        startReasoningButton,
        cancelReasoningButton,
        reasoningProgress,
        reasoningProgressBar,
        reasoningStatus,
        chatInterface,
        apiClient,
        settingsPanel
    ) {
        this.reasoningModal = reasoningModal;
        this.reasoningTask = reasoningTask;
        this.reasoningStepsInput = reasoningStepsInput;
        this.startReasoningButton = startReasoningButton;
        this.cancelReasoningButton = cancelReasoningButton;
        this.reasoningProgress = reasoningProgress;
        this.reasoningProgressBar = reasoningProgressBar;
        this.reasoningStatus = reasoningStatus;
        this.chatInterface = chatInterface;
        this.apiClient = apiClient;
        this.settingsPanel = settingsPanel;
        
        this.isOpen = false;
        this.isProcessing = false;
        this.subtasks = [];
        this.currentSubtaskIndex = 0;
        
        // Set up event listeners
        this.setupEventListeners();
        this.setupSocketListeners();
    }
    
    /**
     * Set up event listeners for the reasoning interface.
     */
    setupEventListeners() {
        // Cancel reasoning
        this.cancelReasoningButton.addEventListener('click', () => {
            this.closeReasoningModal();
        });
        
        // Start reasoning
        this.startReasoningButton.addEventListener('click', () => {
            this.startReasoning();
        });
        
        // Close modal when clicking outside
        this.reasoningModal.addEventListener('click', (event) => {
            if (event.target === this.reasoningModal && !this.isProcessing) {
                this.closeReasoningModal();
            }
        });
    }
    
    /**
     * Set up Socket.IO event listeners for reasoning events.
     */
    setupSocketListeners() {
        const socket = io();
        
        // Reasoning start event
        socket.on('reasoning_start', (data) => {
            this.handleReasoningStart(data);
        });
        
        // Reasoning subtasks event
        socket.on('reasoning_subtasks', (data) => {
            this.handleReasoningSubtasks(data);
        });
        
        // Reasoning subtask start event
        socket.on('reasoning_subtask_start', (data) => {
            this.handleSubtaskStart(data);
        });
        
        // Reasoning subtask complete event
        socket.on('reasoning_subtask_complete', (data) => {
            this.handleSubtaskComplete(data);
        });
        
        // Reasoning aggregating event
        socket.on('reasoning_aggregating', () => {
            this.handleAggregating();
        });
        
        // Reasoning complete event
        socket.on('reasoning_complete', (data) => {
            this.handleReasoningComplete(data);
        });
        
        // Reasoning error event
        socket.on('reasoning_error', (data) => {
            this.handleReasoningError(data);
        });

        // Subtask error event
        socket.on('subtask_error', (data) => {
            this.handleSubtaskError(data);
        });

        // Timeout event
        socket.on('reasoning_timeout', (data) => {
            this.handleTimeout(data);
        });

        // Reasoning log event
        socket.on('reasoning_log', (data) => {
            this.handleReasoningLog(data);
        });
    }
    
    /**
     * Close the reasoning modal.
     */
    closeReasoningModal() {
        this.isOpen = false;
        this.reasoningModal.classList.remove('active');
    }
    
    /**
     * Start the reasoning process.
     */
    async startReasoning(message) {
        if (!message) {
            return;
        }
        
        // Get settings
        const settings = this.settingsPanel.getCurrentSettings();
        const steps = settings.reasoning_steps || 5;
        
        // Show progress UI
        this.isProcessing = true;
        this.reasoningProgress.style.display = 'block';
        this.reasoningProgressBar.style.width = '0%';
        this.reasoningStatus.textContent = '准备中...';
        
        try {
            // Add a message to the chat
            this.chatInterface.addMessage('system', `开始多步骤推理: "${message}"`);
            
            // Start reasoning
            await this.apiClient.startReasoning(message, {
                steps: steps,
                provider: settings.provider,
                temperature: settings.temperature,
                web_search: settings.web_search_enabled,
                extract_url: settings.extract_url_content,
                context_files: this.chatInterface.getContextFiles()
            });
        } catch (error) {
            console.error('Reasoning error:', error);
            this.chatInterface.addMessage('system', `推理错误: ${error.message}`);
            this.resetReasoningUI();
        }
    }
    
    /**
     * Reset the reasoning UI.
     */
    resetReasoningUI() {
        // Reset processing state
        this.isProcessing = false;
        
        // Hide progress UI
        this.reasoningProgress.style.display = 'none';
        
        // Reset subtasks
        this.subtasks = [];
        this.currentSubtaskIndex = 0;
    }
    
    /**
     * Handle reasoning start event.
     * 
     * @param {Object} data - The event data
     */
    handleReasoningStart(data) {
        this.reasoningStatus.textContent = `开始分析任务: "${data.task}"`;
        this.reasoningProgressBar.style.width = '10%';
    }
    
    /**
     * Handle reasoning subtasks event.
     * 
     * @param {Object} data - The event data
     */
    handleReasoningSubtasks(data) {
        this.subtasks = data.subtasks;
        this.currentSubtaskIndex = 0;
        
        // Update progress
        this.reasoningProgressBar.style.width = '20%';
        this.reasoningStatus.textContent = `任务已分解为 ${this.subtasks.length} 个子任务`;
        
        // Add subtasks to chat
        let subtasksMessage = '任务已分解为以下子任务:\n';
        this.subtasks.forEach((subtask, index) => {
            subtasksMessage += `${index + 1}. ${subtask}\n`;
        });
        
        this.chatInterface.addMessage('system', subtasksMessage);
    }
    
    /**
     * Handle subtask start event.
     * 
     * @param {Object} data - The event data
     */
    handleSubtaskStart(data) {
        // Validate index
        if (!this.subtasks || data.index >= this.subtasks.length) {
            console.error('Invalid subtask index:', data.index);
            return;
        }

        this.currentSubtaskIndex = data.index;
        
        // Update progress
        const progress = 20 + (data.index / this.subtasks.length) * 60;
        this.reasoningProgressBar.style.width = `${progress}%`;
        this.reasoningStatus.textContent = `执行子任务 ${data.index + 1}/${this.subtasks.length}: "${data.subtask}"`;
        
        // Add to chat
        this.chatInterface.addMessage('system', `执行子任务 ${data.index + 1}/${this.subtasks.length}: "${data.subtask}"`);
    }
    
    /**
     * Handle subtask complete event.
     * 
     * @param {Object} data - The event data
     */
    handleSubtaskComplete(data) {
        // Validate index
        if (!this.subtasks || data.index >= this.subtasks.length) {
            console.error('Invalid subtask index:', data.index);
            return;
        }

        // Update progress
        const progress = 20 + ((data.index + 1) / this.subtasks.length) * 60;
        this.reasoningProgressBar.style.width = `${progress}%`;
        this.reasoningStatus.textContent = `子任务 ${data.index + 1}/${this.subtasks.length} 完成`;
        
        // Add to chat
        this.chatInterface.addMessage('assistant', data.result);
    }
    
    /**
     * Handle aggregating event.
     */
    handleAggregating() {
        // Update progress
        this.reasoningProgressBar.style.width = '80%';
        this.reasoningStatus.textContent = '整合结果中...';
        
        // Add to chat
        this.chatInterface.addMessage('system', '整合所有子任务结果...');
    }
    
    /**
     * Handle reasoning complete event.
     * 
     * @param {Object} data - The event data
     */
    handleReasoningComplete(data) {
        // Update progress
        this.reasoningProgressBar.style.width = '100%';
        this.reasoningStatus.textContent = '推理完成';
        
        // Add to chat
        this.chatInterface.addMessage('assistant', data.result);
        
        // Reset UI after a delay
        setTimeout(() => {
            this.resetReasoningUI();
            this.closeReasoningModal();
        }, 1000);
    }
    
    /**
     * Handle reasoning error event.
     * 
     * @param {Object} data - The event data
     */
    handleReasoningError(data) {
        // Update status
        this.reasoningStatus.textContent = `错误: ${data.error}`;
        
        // Add to chat
        this.chatInterface.addMessage('system', `推理错误: ${data.error}`);
        
        // Reset UI after a delay
        setTimeout(() => {
            this.resetReasoningUI();
        }, 3000);
    }

    /**
     * Handle subtask error event.
     *
     * @param {Object} data - The event data
     */
    handleSubtaskError(data) {
        // Calculate progress percentage
        const progress = 20 + ((data.index + 1) / this.subtasks.length) * 60;
        
        // Update progress bar
        this.reasoningProgressBar.style.width = `${progress}%`;
        
        // Update status text
        this.reasoningStatus.textContent = `子任务 ${data.index + 1}/${this.subtasks.length} 失败`;
        
        // Add error message to chat
        this.chatInterface.addMessage(
            'system',
            `子任务 ${data.index + 1}/${this.subtasks.length} 失败: ${data.error}`
        );
    }
    
    /**
     * Handle reasoning log event.
     *
     * @param {Object} data - The event data
     */
    /**
     * Handle timeout event.
     *
     * @param {Object} data - The event data
     */
    handleTimeout(data) {
        // Update status
        this.reasoningStatus.textContent = '推理超时';
        
        // Add to chat
        this.chatInterface.addMessage('system', '推理过程超时，请尝试简化任务或增加时间限制');
        
        // Reset UI
        this.resetReasoningUI();
    }

    handleReasoningLog(data) {
        // Handle structured log messages
        if (typeof data === 'object' && data.type) {
            // The enhanced_ws_handler in the ReasoningAdapter will handle displaying
            // these messages in the chat history, so we don't need to duplicate them here.
            // Just update the UI based on the log type
            
            const message = data.message || '';
            
            // Update progress bar and status based on log type
            switch (data.type) {
                case 'decomposition_start':
                    this.reasoningStatus.textContent = '分析任务中...';
                    this.reasoningProgressBar.style.width = '10%';
                    break;
                    
                case 'decomposition_complete':
                    this.reasoningStatus.textContent = '任务分解完成';
                    this.reasoningProgressBar.style.width = '20%';
                    
                    // Update subtasks if available
                    if (data.subtasks && Array.isArray(data.subtasks)) {
                        this.subtasks = data.subtasks;
                        this.currentSubtaskIndex = 0;
                    }
                    break;
                    
                case 'subtask_start':
                    if (data.subtask_index !== undefined && data.total_subtasks) {
                        const progress = 20 + (data.subtask_index / data.total_subtasks) * 60;
                        this.reasoningProgressBar.style.width = `${progress}%`;
                        this.reasoningStatus.textContent = `执行子任务 ${data.subtask_index + 1}/${data.total_subtasks}`;
                    }
                    break;
                    
                case 'subtask_complete':
                    if (data.subtask_index !== undefined && data.total_subtasks) {
                        const progress = 20 + ((data.subtask_index + 1) / data.total_subtasks) * 60;
                        this.reasoningProgressBar.style.width = `${progress}%`;
                        this.reasoningStatus.textContent = `子任务 ${data.subtask_index + 1}/${data.total_subtasks} 完成`;
                    }
                    break;
                    
                case 'aggregation_start':
                    this.reasoningProgressBar.style.width = '80%';
                    this.reasoningStatus.textContent = '整合结果中...';
                    break;
                    
                case 'aggregation_complete':
                    this.reasoningProgressBar.style.width = '100%';
                    this.reasoningStatus.textContent = '推理完成';
                    break;
            }
        }
        // Handle simple string log messages (legacy format)
        else if (typeof data === 'string' || data.message) {
            const message = typeof data === 'string' ? data : data.message;
            // Only add non-empty messages to avoid cluttering the chat
            if (message && message.trim()) {
                this.chatInterface.addMessage('system', message);
            }
        }
    }
}