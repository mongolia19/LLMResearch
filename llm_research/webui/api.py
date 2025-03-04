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
from llm_research.file_handler import FileHandler

# Initialize configuration
config = Config()
file_handler = FileHandler()

# Store active conversations
conversations = {}
reasoning_sessions = {}

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
            
            try:
                llm = get_llm_provider(config, provider_name)
                
                # Import here to avoid circular imports
                from llm_research.webui.adapters.conversation import ConversationAdapter
                conversations[conversation_id] = ConversationAdapter(llm)
            except Exception as e:
                return jsonify({
                    'error': f"Failed to initialize conversation: {str(e)}"
                }), 500
        
        conversation = conversations[conversation_id]
        
        # Add context from files if provided
        context_files = data.get('context_files', [])
        for file_path in context_files:
            if os.path.exists(file_path):
                try:
                    content = file_handler.read_file(file_path)
                    conversation.add_context(f"Content from {os.path.basename(file_path)}:\n\n{content}")
                except Exception as e:
                    return jsonify({
                        'error': f"Failed to read file {file_path}: {str(e)}"
                    }), 500
        
        # Add the user message
        user_message = data.get('message', '')
        conversation.add_message('user', user_message)
        
        # Generate the response
        socketio = current_app.config['socketio']
        
        def create_stream_with_context(app, conversation_id, data, conversation):
            """Helper function to create response stream with proper application context"""
            with app.app_context():
                try:
                    # Get socketio from app config
                    socketio = app.config['socketio']
                    
                    # Get response parameters
                    temperature = data.get('temperature', 0.7)
                    max_tokens = data.get('max_tokens')
                    
                    # Stream the response
                    full_response = ""
                    for chunk in conversation.generate_response_stream(
                        temperature=temperature,
                        max_tokens=max_tokens
                    ):
                        full_response += chunk
                        socketio.emit('response_chunk', {
                            'conversation_id': conversation_id,
                            'chunk': chunk
                        })
                    
                    # Signal completion
                    socketio.emit('response_complete', {
                        'conversation_id': conversation_id,
                        'response': full_response
                    })
                    return True
                except Exception as e:
                    # Log the error
                    import traceback
                    print(f"Error in stream_response: {str(e)}")
                    print(traceback.format_exc())
                    
                    # Get socketio from app config
                    socketio = app.config['socketio']
                    
                    # Emit error event
                    socketio.emit('response_error', {
                        'conversation_id': conversation_id,
                        'error': str(e)
                    })
                    return False

        # Get the app reference before starting the background task
        app = current_app._get_current_object()
        
        # Start the background task with the app reference
        socketio.start_background_task(
            create_stream_with_context,
            app,
            conversation_id,
            data,
            conversation
        )
        
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
        web_search_enabled = data.get('web_search', True)
        extract_url_content = data.get('extract_url', True)
        conversation_id = data.get('conversation_id')  # Get conversation ID if provided
        
        # Create a session ID
        session_id = str(uuid.uuid4())
        
        # Get the conversation if provided
        chat_interface = None
        if conversation_id and conversation_id in conversations:
            chat_interface = conversations[conversation_id]
        
        # Get LLM provider
        try:
            llm = get_llm_provider(config, provider_name)
            
            # Import here to avoid circular imports
            from llm_research.webui.adapters.reasoning import ReasoningAdapter
            # Get the WebSocket logging handler
            from llm_research.webui.utils import send_log_to_client
            
            # Create a wrapper for the WebSocket handler that ensures we have an application context
            def ws_handler_with_context(log_data):
                # Store app reference to avoid context issues
                app = current_app._get_current_object()
                
                # Use the app's context to ensure we're within an application context
                with app.app_context():
                    send_log_to_client(log_data)
            
            reasoning = ReasoningAdapter(
                llm,
                max_steps=steps,
                web_search_enabled=web_search_enabled,
                extract_url_content=extract_url_content,
                ws_handler=ws_handler_with_context,  # Use the wrapper with context
                chat_interface=chat_interface  # Pass the chat interface
            )
            reasoning_sessions[session_id] = reasoning
        except Exception as e:
            return jsonify({
                'error': f"Failed to initialize reasoning: {str(e)}"
            }), 500
        
        # Add context from files if provided
        context = ""
        context_files = data.get('context_files', [])
        for file_path in context_files:
            if os.path.exists(file_path):
                try:
                    content = file_handler.read_file(file_path)
                    context += f"\n\n--- {os.path.basename(file_path)} ---\n\n{content}"
                except Exception as e:
                    return jsonify({
                        'error': f"Failed to read file {file_path}: {str(e)}"
                    }), 500
        
        # Execute the task
        socketio = current_app.config['socketio']
        
        def create_task_with_context(app, session_id, task, steps, context, data, reasoning):
            """Helper function to create task with proper application context"""
            with app.app_context():
                try:
                    # Get socketio from app config
                    socketio = app.config['socketio']
                    
                    # Emit events for each step
                    socketio.emit('reasoning_start', {
                        'session_id': session_id,
                        'task': task,
                        'max_steps': steps
                    })
                    
                    # Execute the reasoning process
                    result = reasoning.solve_task(
                        task=task,
                        context=context if context else None,
                        temperature=data.get('temperature', 0.7),
                        max_tokens=data.get('max_tokens'),
                        max_retries=data.get('retries', 3)
                    )
                    
                    # Emit completion event
                    socketio.emit('reasoning_complete', {
                        'session_id': session_id,
                        'result': result
                    })
                    
                    return True
                except Exception as e:
                    # Log the error
                    import traceback
                    print(f"Error in execute_task: {str(e)}")
                    print(traceback.format_exc())
                    
                    # Get socketio from app config
                    socketio = app.config['socketio']
                    
                    # Emit error event
                    socketio.emit('reasoning_error', {
                        'session_id': session_id,
                        'error': str(e)
                    })
                    return False
                finally:
                    # Clean up regardless of success/failure
                    if session_id in reasoning_sessions:
                        del reasoning_sessions[session_id]

        # Get the app reference before starting the background task
        app = current_app._get_current_object()
        
        # Start the background task with the app reference
        socketio.start_background_task(
            create_task_with_context,
            app,
            session_id,
            task,
            steps,
            context,
            data,
            reasoning
        )
        
        return jsonify({
            'session_id': session_id,
            'status': 'processing'
        })
    
    # Providers API
    @app.route('/api/providers', methods=['GET'])
    def list_providers():
        """
        List all configured LLM providers.
        """
        try:
            providers = config.list_providers()
            default_provider = config.config.get('default_provider')
            
            return jsonify({
                'providers': providers,
                'default_provider': default_provider
            })
        except Exception as e:
            return jsonify({
                'error': f"Failed to list providers: {str(e)}"
            }), 500
    
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
            try:
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
            except Exception as e:
                return jsonify({
                    'error': f"Failed to upload file: {str(e)}"
                }), 500
    
    # Settings API
    @app.route('/api/settings', methods=['GET'])
    def get_settings():
        """
        Get WebUI settings.
        """
        try:
            # Load settings from config
            settings = {
                'theme': 'light',
                'max_history': 100,
                'web_search_enabled': True,
                'extract_url_content': True,
                'temperature': 0.7,
                'max_tokens': None,
                'reasoning_steps': 5,
                'retries': 3
            }
            
            # Try to load from config file
            try:
                with open(os.path.join(current_app.instance_path, 'webui_settings.json'), 'r') as f:
                    saved_settings = json.load(f)
                    settings.update(saved_settings)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            
            return jsonify(settings)
        except Exception as e:
            return jsonify({
                'error': f"Failed to get settings: {str(e)}"
            }), 500
    
    @app.route('/api/settings', methods=['POST'])
    def update_settings():
        """
        Update WebUI settings.
        """
        try:
            data = request.json
            
            # Validate settings
            valid_settings = {
                'theme': data.get('theme', 'light'),
                'max_history': int(data.get('max_history', 100)),
                'web_search_enabled': bool(data.get('web_search_enabled', True)),
                'extract_url_content': bool(data.get('extract_url_content', True)),
                'temperature': float(data.get('temperature', 0.7)),
                'max_tokens': int(data.get('max_tokens')) if data.get('max_tokens') else None,
                'reasoning_steps': int(data.get('reasoning_steps', 5)),
                'retries': int(data.get('retries', 3))
            }
            
            # Save settings to config file
            os.makedirs(current_app.instance_path, exist_ok=True)
            with open(os.path.join(current_app.instance_path, 'webui_settings.json'), 'w') as f:
                json.dump(valid_settings, f, indent=2)
            
            return jsonify({
                'status': 'success',
                'settings': valid_settings
            })
        except Exception as e:
            return jsonify({
                'error': f"Failed to update settings: {str(e)}"
            }), 500