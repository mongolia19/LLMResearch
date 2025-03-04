/**
 * Main application logic for the LLMResearch WebUI.
 */
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize Socket.IO connection
    const socket = io();
    
    // Initialize API client
    const api = new ApiClient();
    
    // Initialize chat interface
    const chat = new ChatInterface(
        document.getElementById('chat-messages'),
        document.getElementById('user-input'),
        document.getElementById('send-button')
    );
    
    // Initialize settings panel
    const settings = new SettingsPanel(
        document.getElementById('settings-panel'),
        document.getElementById('settings-toggle'),
        document.getElementById('theme-toggle'),
        document.getElementById('provider-select'),
        document.getElementById('web-search-toggle'),
        document.getElementById('extract-url-toggle'),
        document.getElementById('reasoning-steps'),
        document.getElementById('temperature'),
        document.getElementById('temperature-value'),
        document.getElementById('clear-history')
    );
    
    // Initialize reasoning interface
    const reasoning = new ReasoningInterface(
        document.getElementById('reasoning-modal'),
        document.getElementById('reasoning-task'),
        document.getElementById('reasoning-steps-input'),
        document.getElementById('start-reasoning'),
        document.getElementById('cancel-reasoning'),
        document.getElementById('reasoning-progress'),
        document.getElementById('reasoning-progress-bar'),
        document.getElementById('reasoning-status'),
        chat,
        api,
        settings
    );
    
    // Initialize file upload modal
    const fileUploadModal = document.getElementById('file-upload-modal');
    const fileUploadForm = document.getElementById('file-upload-form');
    const fileInput = document.getElementById('file-input');
    const fileButton = document.getElementById('file-button');
    const cancelUploadButton = document.getElementById('cancel-upload');
    
    // Load settings from localStorage
    settings.loadLocalSettings();
    
    try {
        // Load settings from server
        const appSettings = await api.getSettings();
        settings.updateSettings(appSettings);
        
        // Load providers
        const providers = await api.getProviders();
        settings.updateProviders(providers);
    } catch (error) {
        console.error('Failed to load initial data:', error);
        chat.addMessage('system', '加载初始数据失败，请刷新页面重试');
    }
    
    // Set up chat event listeners
    chat.onSendMessage(async (message) => {
        // Add user message to chat
        chat.addMessage('user', message);
        
        // Disable input while processing
        chat.setInputEnabled(false);

        try {
            // Get current settings
            const currentSettings = settings.getCurrentSettings();
            
            // Use reasoning mode for all messages
            await reasoning.startReasoning(message);
        } catch (error) {
            console.error('Error sending message:', error);
            chat.addMessage('system', `错误: ${error.message}`);
            chat.setInputEnabled(true);
        }
    });
    
    // Set up settings event listeners
    settings.onClearHistory(() => {
        chat.clearHistory();
        chat.clearContextFiles();
    });
    
    // Set up file upload event listeners
    fileButton.addEventListener('click', () => {
        fileUploadModal.classList.add('active');
    });
    
    cancelUploadButton.addEventListener('click', () => {
        fileUploadModal.classList.remove('active');
    });
    
    fileUploadForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        if (!fileInput.files.length) {
            return;
        }
        
        const file = fileInput.files[0];
        
        try {
            // Show loading message
            chat.addMessage('system', `正在上传文件: ${file.name}...`);
            
            // Upload the file
            const result = await api.uploadFile(file);
            
            // Hide the modal
            fileUploadModal.classList.remove('active');
            
            // Add success message
            chat.addMessage('system', `文件上传成功: ${file.name}`);
            
            // Store the file path for context
            chat.addContextFile(result.path);
            
            // Reset the file input
            fileInput.value = '';
        } catch (error) {
            console.error('Error uploading file:', error);
            chat.addMessage('system', `文件上传失败: ${error.message}`);
        }
    });
    
    // Set up Socket.IO event listeners
    socket.on('connect', () => {
        console.log('Connected to server');
    });
    
    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        chat.addMessage('system', '与服务器的连接已断开，请刷新页面重试');
    });
    
    // Chat response streaming
    socket.on('response_chunk', (data) => {
        chat.appendToMessage('assistant', data.chunk, data.conversation_id);
    });
    
    socket.on('response_complete', (data) => {
        chat.setInputEnabled(true);
    });
    
    socket.on('response_error', (data) => {
        chat.addMessage('system', `错误: ${data.error}`);
        chat.setInputEnabled(true);
    });
    
    // Focus the input field
    document.getElementById('user-input').focus();
});