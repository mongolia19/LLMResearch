# WebUI Requirements

## Backend Dependencies

```
Flask==2.2.3
Flask-CORS==3.0.10
Flask-SocketIO==5.3.2
python-socketio==5.7.2
python-engineio==4.3.4
Werkzeug==2.2.3
```

## Frontend Dependencies

These will be loaded from CDNs, no installation required:

- Socket.IO Client (v4.4.1)

## Installation Instructions

1. Install the backend dependencies:

```bash
pip install -r webui_requirements.txt
```

2. No frontend installation is needed as dependencies are loaded from CDNs.

## Development Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/LLMResearch.git
cd LLMResearch
```

2. Install the package in development mode:

```bash
pip install -e .
```

3. Install WebUI dependencies:

```bash
pip install -r webui_requirements.txt
```

4. Run the WebUI:

```bash
python -m llm_research webui
```

5. Open your browser and navigate to:

```
http://127.0.0.1:5000
```

## Production Deployment

For production deployment, we recommend using Gunicorn with Nginx:

1. Install Gunicorn:

```bash
pip install gunicorn
```

2. Create a systemd service file (for Linux):

```ini
[Unit]
Description=LLMResearch WebUI
After=network.target

[Service]
User=yourusername
WorkingDirectory=/path/to/LLMResearch
ExecStart=/path/to/gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 "llm_research.webui.server:create_app()"
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

3. Configure Nginx as a reverse proxy:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

4. Start the service:

```bash
sudo systemctl start llmresearch-webui
sudo systemctl enable llmresearch-webui
```

## Docker Deployment

Alternatively, you can use Docker for deployment:

1. Create a Dockerfile:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY . .
RUN pip install -e .
RUN pip install -r webui_requirements.txt
RUN pip install gunicorn gevent gevent-websocket

EXPOSE 5000

CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "-w", "1", "--bind", "0.0.0.0:5000", "llm_research.webui.server:create_app()"]
```

2. Build and run the Docker container:

```bash
docker build -t llmresearch-webui .
docker run -p 5000:5000 llmresearch-webui