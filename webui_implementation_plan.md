# WebUI Implementation Plan for LLMResearch

## Overview

The current LLMResearch system is a powerful command-line tool with features like multi-step reasoning, web search integration, and URL content extraction. We'll add a web-based user interface that provides a chat-like experience while maintaining access to all existing functionality.

## Architecture

We'll implement a client-server architecture:

1. **Backend**: Flask API server that interfaces with the existing LLMResearch codebase
2. **Frontend**: Modern web interface built with HTML, CSS, and JavaScript

## Project Structure

```
llm_research/
├── webui/
│   ├── __init__.py           # Package initialization
│   ├── server.py             # Flask application
│   ├── api.py                # API endpoints
│   ├── config.py             # WebUI configuration
│   ├── adapters/             # Adapters for LLMResearch functionality
│   │   ├── __init__.py
│   │   ├── conversation.py   # Conversation adapter
│   │   ├── reasoning.py      # Reasoning adapter
│   │   └── file_handler.py   # File handling adapter
│   └── static/               # Static files for the frontend
│       ├── css/
│       │   ├── main.css      # Main stylesheet
│       │   └── themes.css    # Theme stylesheets
│       ├── js/
│       │   ├── app.js        # Main application logic
│       │   ├── api.js        # API client
│       │   ├── chat.js       # Chat interface logic
│       │   └── settings.js   # Settings panel logic
│       ├── img/              # Images and icons
│       └── index.html        # Main HTML page
└── cli.py                    # Updated CLI with WebUI launch option
```

## Implementation Steps

### 1. Create Backend API Server

We'll create a Flask application that exposes the LLMResearch functionality through REST API endpoints.

#### server.py

```python
"""
Flask server for the LLMResearch WebUI.
"""

import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO

def create_app(test_config=None):
    """
    Create and configure the Flask application.
    
    Args:
        test_config: Test configuration to use (optional)
        
    Returns:
        The configured Flask application
    """
    # Create the Flask app
    app = Flask(__name__, static_folder='static')
    
    # Enable CORS
    CORS(app)
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    app.config['socketio'] = socketio
    
    # Load configuration
    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Register API routes
    from llm_research.webui.api import register_routes
    register_routes(app)
    
    # Serve the main page
    @app.route('/')
    def index():
        """Serve the main page."""
        return send_from_directory(app.static_folder, 'index.html')
    
    return app, socketio

def run_server(host='127.0.0.1', port=5000, debug=False):
    """
    Run the Flask server.
    
    Args:
        host: The host to bind to
        port: The port to bind to
        debug: Whether to enable debug mode
    """
    app, socketio = create_app()
    socketio.run(app, host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_server(debug=True)
```

### 2. Design API Endpoints

We'll need the following API endpoints:

#### api.py

```python
"""
API endpoints for the LLMResearch WebUI.
"""

import os
import json
import uuid
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename

from llm_research.config import Config
from llm_research.llm import get_llm_provider
from llm_research.webui.adapters.conversation import ConversationAdapter
from llm_research.webui.adapters.reasoning import ReasoningAdapter
from llm_research.webui.adapters.file_handler import FileHandlerAdapter

# Initialize adapters
config = Config()
file_handler = FileHandlerAdapter()

# Store active conversations
conversations = {}

def register_routes(app):
    """
    Register API routes with the Flask application.
    
    Args:
        app: The Flask application
    """
    # Chat API
    @app.route('/api/chat', methods=['POST'])
    def chat():
        """
        Handle chat messages and generate responses.
        """
        data = request.json
        
        # Get or create conversation
        conversation_id = data.get('conversation_id')
        if not conversation_id or conversation_id not in conversations:
            conversation_id = str(uuid.uuid4())
            provider_name = data.get('provider')
            llm = get_llm_provider(config, provider_name)
            conversations[conversation_id] = ConversationAdapter(llm)
        
        conversation = conversations[conversation_id]
        
        # Add context from files if provided
        context_files = data.get('context_files', [])
        for file_path in context_files:
            if os.path.exists(file_path):
                content = file_handler.read_file(file_path)
                conversation.add_context(content)
        
        # Add the user message
        user_message = data.get('message', '')
        conversation.add_message('user', user_message)
        
        # Generate the response
        socketio = current_app.config['socketio']
        
        def stream_response():
            for chunk in conversation.generate_response_stream():
                socketio.emit('response_chunk', {
                    'conversation_id': conversation_id,
                    'chunk': chunk
                })
        
        # Start streaming in a background thread
        socketio.start_background_task(stream_response)
        
        return jsonify({
            'conversation_id': conversation_id,
            'status': 'streaming'
        })
    
    # Reasoning API
    @app.route('/api/reasoning', methods=['POST'])
    def reasoning():
        """
        Perform multi-step reasoning on a task.
        """
        data = request.json
        
        # Get task and parameters
        task = data.get('task', '')
        steps = data.get('steps', 5)
        provider_name = data.get('provider')
        
        # Get LLM provider
        llm = get_llm_provider(config, provider_name)
        
        # Create reasoning adapter
        reasoning = ReasoningAdapter(llm, max_steps=steps)
        
        # Add context from files if provided
        context = ""
        context_files = data.get('context_files', [])
        for file_path in context_files:
            if os.path.exists(file_path):
                content = file_handler.read_file(file_path)
                context += f"\n\n--- {os.path.basename(file_path)} ---\n\n{content}"
        
        # Execute the task
        socketio = current_app.config['socketio']
        
        def execute_task():
            # Emit events for each step
            socketio.emit('reasoning_start', {
                'task': task,
                'max_steps': steps
            })
            
            # Decompose the task
            subtasks = reasoning.task_decomposition(task, context)
            
            socketio.emit('reasoning_subtasks', {
                'subtasks': subtasks
            })
            
            # Execute subtasks
            results = []
            for i, subtask in enumerate(subtasks):
                socketio.emit('reasoning_subtask_start', {
                    'index': i,
                    'subtask': subtask
                })
                
                result = reasoning.execute_step(subtask, context)
                results.append(result)
                
                socketio.emit('reasoning_subtask_complete', {
                    'index': i,
                    'result': result
                })
            
            # Aggregate results
            socketio.emit('reasoning_aggregating', {})
            final_result = reasoning.aggregate_results(task, subtasks, results)
            
            socketio.emit('reasoning_complete', {
                'result': final_result
            })
        
        # Start reasoning in a background thread
        socketio.start_background_task(execute_task)
        
        return jsonify({
            'status': 'processing'
        })
    
    # Providers API
    @app.route('/api/providers', methods=['GET'])
    def list_providers():
        """
        List all configured LLM providers.
        """
        providers = config.list_providers()
        default_provider = config.config.get('default_provider')
        
        return jsonify({
            'providers': providers,
            'default_provider': default_provider
        })
    
    # File upload API
    @app.route('/api/files', methods=['POST'])
    def upload_file():
        """
        Upload a file for context.
        """
        if 'file' not in request.files:
            return jsonify({
                'error': 'No file part'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'error': 'No selected file'
            }), 400
        
        if file:
            filename = secure_filename(file.filename)
            upload_folder = os.path.join(current_app.instance_path, 'uploads')
            
            # Ensure the upload folder exists
            os.makedirs(upload_folder, exist_ok=True)
            
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            return jsonify({
                'filename': filename,
                'path': file_path
            })
    
    # Settings API
    @app.route('/api/settings', methods=['GET'])
    def get_settings():
        """
        Get WebUI settings.
        """
        # Load settings from config
        settings = {
            'theme': 'light',
            'max_history': 100,
            'web_search_enabled': True,
            'extract_url_content': True
        }
        
        return jsonify(settings)
    
    @app.route('/api/settings', methods=['POST'])
    def update_settings():
        """
        Update WebUI settings.
        """
        data = request.json
        
        # Update settings in config
        # ...
        
        return jsonify({
            'status': 'success'
        })
```

### 3. Create Frontend Interface

The frontend will be a responsive web application with a chat interface.

#### index.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLMResearch WebUI</title>
    <link rel="stylesheet" href="css/main.css">
    <link rel="stylesheet" href="css/themes.css">
    <script src="https://cdn.socket.io/4.4.1/socket.io.min.js"></script>
</head>
<body class="theme-light">
    <div class="app-container">
        <header class="app-header">
            <h1>LLMResearch</h1>
            <div class="header-controls">
                <button id="settings-toggle" class="icon-button" title="Settings">
                    <span class="icon">⚙️</span>
                </button>
                <button id="theme-toggle" class="icon-button" title="Toggle Theme">
                    <span class="icon">🌓</span>
                </button>
            </div>
        </header>
        
        <main class="app-main">
            <div class="chat-container">
                <div class="chat-messages" id="chat-messages">
                    <!-- Messages will be dynamically added here -->
                    <div class="message system">
                        <div class="message-content">
                            Welcome to LLMResearch WebUI. How can I help you today?
                        </div>
                    </div>
                </div>
                
                <div class="chat-input">
                    <textarea id="user-input" placeholder="Type your message..."></textarea>
                    <div class="input-controls">
                        <button id="file-button" class="icon-button" title="Upload File">
                            <span class="icon">📎</span>
                        </button>
                        <button id="send-button">Send</button>
                    </div>
                </div>
            </div>
            
            <div class="settings-panel" id="settings-panel">
                <h3>Settings</h3>
                
                <div class="setting-group">
                    <label for="provider-select">LLM Provider:</label>
                    <select id="provider-select">
                        <option value="openai">OpenAI</option>
                        <option value="custom">Custom</option>
                    </select>
                </div>
                
                <div class="setting-group">
                    <label for="web-search-toggle">Web Search:</label>
                    <input type="checkbox" id="web-search-toggle" checked>
                </div>
                
                <div class="setting-group">
                    <label for="extract-url-toggle">Extract URL Content:</label>
                    <input type="checkbox" id="extract-url-toggle" checked>
                </div>
                
                <div class="setting-group">
                    <label for="reasoning-steps">Reasoning Steps:</label>
                    <input type="number" id="reasoning-steps" min="1" max="10" value="5">
                </div>
                
                <div class="setting-group">
                    <label for="temperature">Temperature:</label>
                    <input type="range" id="temperature" min="0" max="1" step="0.1" value="0.7">
                    <span id="temperature-value">0.7</span>
                </div>
                
                <div class="setting-group">
                    <button id="clear-history">Clear Chat History</button>
                </div>
            </div>
        </main>
        
        <div class="file-upload-modal" id="file-upload-modal">
            <div class="modal-content">
                <h3>Upload File</h3>
                <form id="file-upload-form">
                    <input type="file" id="file-input">
                    <div class="modal-buttons">
                        <button type="button" id="cancel-upload">Cancel</button>
                        <button type="submit">Upload</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    
    <script src="js/api.js"></script>
    <script src="js/chat.js"></script>
    <script src="js/settings.js"></script>
    <script src="js/app.js"></script>
</body>
</html>
```

#### main.css

```css
/* Base styles */
:root {
    --font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    --border-radius: 8px;
    --transition-speed: 0.3s;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: var(--font-family);
    line-height: 1.6;
    transition: background-color var(--transition-speed), color var(--transition-speed);
}

.app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-width: 1200px;
    margin: 0 auto;
}

/* Header */
.app-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid var(--border-color);
}

.header-controls {
    display: flex;
    gap: 0.5rem;
}

/* Main content */
.app-main {
    display: flex;
    flex: 1;
    overflow: hidden;
}

/* Chat container */
.chat-container {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
}

.message {
    margin-bottom: 1rem;
    max-width: 80%;
}

.message.user {
    margin-left: auto;
}

.message.assistant {
    margin-right: auto;
}

.message.system {
    margin: 1rem auto;
    max-width: 90%;
    text-align: center;
    opacity: 0.8;
}

.message-content {
    padding: 0.75rem 1rem;
    border-radius: var(--border-radius);
}

/* Chat input */
.chat-input {
    display: flex;
    flex-direction: column;
    padding: 1rem;
    border-top: 1px solid var(--border-color);
}

#user-input {
    width: 100%;
    min-height: 60px;
    max-height: 200px;
    padding: 0.75rem;
    border-radius: var(--border-radius);
    resize: vertical;
    font-family: var(--font-family);
    border: 1px solid var(--border-color);
    background-color: var(--input-bg-color);
    color: var(--text-color);
}

.input-controls {
    display: flex;
    justify-content: space-between;
    margin-top: 0.5rem;
}

#send-button {
    padding: 0.5rem 1.5rem;
    border-radius: var(--border-radius);
    border: none;
    background-color: var(--primary-color);
    color: white;
    cursor: pointer;
    transition: background-color var(--transition-speed);
}

#send-button:hover {
    background-color: var(--primary-color-hover);
}

/* Settings panel */
.settings-panel {
    width: 300px;
    padding: 1rem;
    border-left: 1px solid var(--border-color);
    overflow-y: auto;
    transform: translateX(100%);
    transition: transform var(--transition-speed);
}

.settings-panel.active {
    transform: translateX(0);
}

.setting-group {
    margin-bottom: 1.5rem;
}

.setting-group label {
    display: block;
    margin-bottom: 0.5rem;
}

/* File upload modal */
.file-upload-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--transition-speed);
}

.file-upload-modal.active {
    opacity: 1;
    pointer-events: auto;
}

.modal-content {
    background-color: var(--bg-color);
    padding: 2rem;
    border-radius: var(--border-radius);
    width: 90%;
    max-width: 500px;
}

.modal-buttons {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 1.5rem;
}

/* Responsive design */
@media (max-width: 768px) {
    .app-main {
        flex-direction: column;
    }
    
    .settings-panel {
        width: 100%;
        border-left: none;
        border-top: 1px solid var(--border-color);
        transform: translateY(100%);
    }
    
    .settings-panel.active {
        transform: translateY(0);
    }
    
    .message {
        max-width: 90%;
    }
}
```

#### app.js

```javascript
// Main application logic

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

// Initialize file upload modal
const fileUploadModal = document.getElementById('file-upload-modal');
const fileUploadForm = document.getElementById('file-upload-form');
const fileInput = document.getElementById('file-input');
const fileButton = document.getElementById('file-button');
const cancelUploadButton = document.getElementById('cancel-upload');

// Event listeners
document.addEventListener('DOMContentLoaded', async () => {
    // Load settings
    const appSettings = await api.getSettings();
    settings.updateSettings(appSettings);
    
    // Load providers
    const providers = await api.getProviders();
    settings.updateProviders(providers);
    
    // Set up Socket.IO event listeners
    setupSocketListeners();
});

// Set up chat event listeners
chat.onSendMessage(async (message) => {
    // Add user message to chat
    chat.addMessage('user', message);
    
    // Disable input while processing
    chat.setInputEnabled(false);
    
    try {
        // Get current settings
        const currentSettings = settings.getCurrentSettings();
        
        // Send message to API
        const response = await api.sendMessage(message, {
            provider: currentSettings.provider,
            web_search: currentSettings.web_search_enabled,
            extract_url: currentSettings.extract_url_content,
            temperature: currentSettings.temperature
        });
        
        // Create assistant message placeholder
        chat.addMessage('assistant', '', response.conversation_id);
    } catch (error) {
        console.error('Error sending message:', error);
        chat.addMessage('system', 'Error: Failed to send message. Please try again.');
        chat.setInputEnabled(true);
    }
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
        const result = await api.uploadFile(file);
        fileUploadModal.classList.remove('active');
        
        // Add system message about the file
        chat.addMessage('system', `File uploaded: ${file.name}`);
        
        // Store the file path for context
        chat.addContextFile(result.path);
    } catch (error) {
        console.error('Error uploading file:', error);
        chat.addMessage('system', 'Error: Failed to upload file. Please try again.');
    }
});

// Set up Socket.IO event listeners
function setupSocketListeners() {
    // Chat response streaming
    socket.on('response_chunk', (data) => {
        chat.appendToMessage('assistant', data.chunk, data.conversation_id);
    });
    
    socket.on('response_complete', (data) => {
        chat.setInputEnabled(true);
    });
    
    // Reasoning events
    socket.on('reasoning_start', (data) => {
        chat.addMessage('system', `Starting multi-step reasoning: "${data.task}"`);
    });
    
    socket.on('reasoning_subtasks', (data) => {
        let subtasksMessage = 'Breaking down into subtasks:\n';
        data.subtasks.forEach((subtask, index) => {
            subtasksMessage += `${index + 1}. ${subtask}\n`;
        });
        
        chat.addMessage('system', subtasksMessage);
    });
    
    socket.on('reasoning_subtask_start', (data) => {
        chat.addMessage('system', `Working on subtask ${data.index + 1}: "${data.subtask}"`);
    });
    
    socket.on('reasoning_subtask_complete', (data) => {
        chat.addMessage('assistant', data.result);
    });
    
    socket.on('reasoning_aggregating', () => {
        chat.addMessage('system', 'Aggregating results...');
    });
    
    socket.on('reasoning_complete', (data) => {
        chat.addMessage('assistant', data.result);
        chat.setInputEnabled(true);
    });
}
```

### 4. Integration with CLI

We'll update the CLI to add a command for launching the WebUI:

```python
@cli.command()
@click.option("--host", default="127.0.0.1", help="The host to bind to")
@click.option("--port", default=5000, help="The port to bind to")
@click.option("--debug/--no-debug", default=False, help="Enable debug mode")
def webui(host, port, debug):
    """
    Launch the web user interface.
    """
    from llm_research.webui.server import run_server
    
    click.echo(f"Starting WebUI server at http://{host}:{port}")
    run_server(host=host, port=port, debug=debug)
```

### 5. Adapter Classes

We'll create adapter classes to interface with the existing LLMResearch functionality:

#### adapters/conversation.py

```python
"""
Adapter for conversation functionality.
"""

from typing import List, Dict, Any, Optional, Iterator

from llm_research.llm.base import BaseLLM
from llm_research.conversation import Conversation as LLMConversation

class ConversationAdapter:
    """
    Adapter for the LLMResearch conversation functionality.
    """
    
    def __init__(self, llm: BaseLLM):
        """
        Initialize the conversation adapter.
        
        Args:
            llm: The LLM provider to use
        """
        self.conversation = LLMConversation(llm)
    
    def add_context(self, context: str) -> None:
        """
        Add context to the conversation.
        
        Args:
            context: The context to add
        """
        self.conversation.add_context(context)
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation.
        
        Args:
            role: The role of the message sender
            content: The message content
        """
        self.conversation.add_message(role, content)
    
    def generate_response(self, **kwargs) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            **kwargs: Additional parameters for the LLM
            
        Returns:
            The generated response
        """
        return self.conversation.generate_response(**kwargs)
    
    def generate_response_stream(self, **kwargs) -> Iterator[str]:
        """
        Generate a streaming response from the LLM.
        
        Args:
            **kwargs: Additional parameters for the LLM
            
        Returns:
            An iterator yielding response chunks
        """
        return self.conversation.generate_response_stream(**kwargs)
```

## Required Dependencies

### Backend
- Flask
- Flask-CORS
- Flask-SocketIO
- Werkzeug
- Existing LLMResearch dependencies

### Frontend
- HTML5/CSS3
- JavaScript (ES6+)
- Socket.IO client

## Implementation Timeline

1. **Phase 1: Basic Setup** (1-2 days)
   - Create project structure
   - Set up Flask server
   - Implement basic HTML/CSS layout

2. **Phase 2: Core Functionality** (2-3 days)
   - Implement chat API endpoint
   - Create basic chat UI
   - Connect frontend to backend

3. **Phase 3: Advanced Features** (3-4 days)
   - Implement reasoning visualization
   - Add file upload functionality
   - Integrate web search features

4. **Phase 4: Polish and Testing** (1-2 days)
   - Improve UI/UX
   - Add responsive design
   - Test across different browsers and devices

## Next Steps

1. Create the basic project structure
2. Implement the Flask server with core API endpoints
3. Develop the frontend chat interface
4. Integrate with existing LLMResearch functionality
5. Test and refine the user experience