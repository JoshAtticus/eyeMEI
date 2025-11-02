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

# Make the startup script executable
RUN chmod +x /app/start.sh

# Expose ports for both main app and admin panel
EXPOSE 5000 5001

# Set the startup command
CMD ["/app/start.sh"]
