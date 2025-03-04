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
        The configured Flask application and SocketIO instance
    """
    # Create the Flask app with correct static file paths
    import os
    static_path = os.path.join(os.path.dirname(__file__), 'static')
    app = Flask(__name__,
                static_folder=static_path,
                static_url_path='/static')
    
    # Enable CORS
    CORS(app)
    
    # Serve static files
    @app.route('/static/<path:filename>')
    def static_files(filename):
        print(f"Serving static file: {filename}")
        try:
            return send_from_directory(app.static_folder, filename)
        except Exception as e:
            print(f"Error serving static file {filename}: {str(e)}")
            raise
    
    # Initialize SocketIO
    socketio = SocketIO(app,
                        cors_allowed_origins="*",
                        ping_timeout=300,  # Increased from default 60 seconds
                        ping_interval=50)  # Send ping every 50 seconds
    app.config['socketio'] = socketio
    
    # WebSocket handler for reasoning logs
    @socketio.on('connect')
    def handle_connect():
        print('Client connected')
        
    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')
        
    from llm_research.webui.utils import send_log_to_client
    
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