/**
 * Reasoning interface for the LLMResearch WebUI.
 */
class ReasoningInterface {
    /**
     * Initialize the reasoning interface.
     * 
     * @param {HTMLElement} reasoningButton - The button to toggle reasoning mode
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
        reasoningButton,
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
        this.reasoningButton = reasoningButton;
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
        // Toggle reasoning mode
        this.reasoningButton.addEventListener('click', () => {
            this.toggleReasoningModal();
        });
        
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

        // Reasoning log event
        socket.on('reasoning_log', (data) => {
            this.handleReasoningLog(data);
        });
    }
    
    /**
     * Toggle the reasoning modal.
     */
    toggleReasoningModal() {
        this.isOpen = !this.isOpen;
        
        if (this.isOpen) {
            this.reasoningModal.classList.add('active');
            
            // Set the steps from settings
            const settings = this.settingsPanel.getCurrentSettings();
            this.reasoningStepsInput.value = settings.reasoning_steps;
            
            // Focus the task input
            setTimeout(() => {
                this.reasoningTask.focus();
            }, 100);
        } else {
            this.reasoningModal.classList.remove('active');
        }
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
    async startReasoning() {
        const task = this.reasoningTask.value.trim();
        
        if (!task) {
            alert('请输入任务描述');
            return;
        }
        
        // Get settings
        const settings = this.settingsPanel.getCurrentSettings();
        const steps = parseInt(this.reasoningStepsInput.value, 10);
        
        // Show progress UI
        this.isProcessing = true;
        this.reasoningProgress.style.display = 'block';
        this.reasoningProgressBar.style.width = '0%';
        this.reasoningStatus.textContent = '准备中...';
        
        // Disable form controls
        this.reasoningTask.disabled = true;
        this.reasoningStepsInput.disabled = true;
        this.startReasoningButton.disabled = true;
        this.cancelReasoningButton.disabled = true;
        
        try {
            // Add a message to the chat
            this.chatInterface.addMessage('system', `开始多步骤推理: "${task}"`);
            
            // Start reasoning
            await this.apiClient.startReasoning(task, {
                steps: steps,
                provider: settings.provider,
                temperature: settings.temperature,
                web_search: settings.web_search_enabled,
                extract_url: settings.extract_url_content,
                context_files: this.chatInterface.getContextFiles()
            });
            
            // Close the modal after a delay
            setTimeout(() => {
                this.resetReasoningUI();
                this.closeReasoningModal();
            }, 1000);
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
        
        // Enable form controls
        this.reasoningTask.disabled = false;
        this.reasoningStepsInput.disabled = false;
        this.startReasoningButton.disabled = false;
        this.cancelReasoningButton.disabled = false;
        
        // Clear task input
        this.reasoningTask.value = '';
        
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
}