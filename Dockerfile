# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GUNICORN_PID=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p databases/raw_data admin_templates public/images/devices static/css static/js templates

# Expose ports for both main app and admin panel
EXPOSE 5000 5001

# Create a startup script
RUN echo '#!/bin/bash\n\
# Start the admin panel in the background\n\
gunicorn --bind 0.0.0.0:5001 --workers 2 --timeout 120 admin_panel:app &\n\
\n\
# Start the main application\n\
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 wsgi:app\n\
' > /app/start.sh && chmod +x /app/start.sh

# Set the startup command
CMD ["/app/start.sh"]
