# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p databases/raw_data admin_templates public/images/devices static/css static/js templates /var/log/supervisor

# Create supervisor configuration
RUN echo '[supervisord]\n\
nodaemon=true\n\
user=root\n\
logfile=/dev/stdout\n\
logfile_maxbytes=0\n\
pidfile=/var/run/supervisord.pid\n\
\n\
[program:eyemei-app]\n\
command=gunicorn --bind 0.0.0.0:3002 --workers 4 --timeout 120 --access-logfile - --error-logfile - wsgi:app\n\
directory=/app\n\
autostart=true\n\
autorestart=true\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
environment=PYTHONUNBUFFERED="1"\n\
\n\
[program:eyemei-admin]\n\
command=gunicorn --bind 0.0.0.0:3003 --workers 2 --timeout 120 --access-logfile - --error-logfile - admin_panel:app\n\
directory=/app\n\
autostart=true\n\
autorestart=true\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
environment=PYTHONUNBUFFERED="1"\n\
' > /etc/supervisor/conf.d/eyemei.conf

# Expose ports for both main app and admin panel
EXPOSE 3002 3003

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
