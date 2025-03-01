"""Utility functions for the WebUI."""

from flask import current_app

def send_log_to_client(log_data):
    """Send log message to connected clients"""
    socketio = current_app.config['socketio']
    socketio.emit('reasoning_log', log_data)