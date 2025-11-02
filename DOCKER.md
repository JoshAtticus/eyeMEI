# Docker Deployment Guide for eyeMEI

This guide explains how to build and run the eyeMEI application using Docker.

## Quick Start

### Using Docker Compose (Recommended)

1. **Build and start the application:**
   ```bash
   docker-compose up -d
   ```

2. **Access the services:**
   - Main Application: http://localhost:5000
   - Admin Panel: http://localhost:5001

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop the application:**
   ```bash
   docker-compose down
   ```

### Using Docker CLI

1. **Build the Docker image:**
   ```bash
   docker build -t eyemei:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name eyemei-app \
     -p 5000:5000 \
     -p 5001:5001 \
     -v ${PWD}/databases:/app/databases \
     -v ${PWD}/public:/app/public \
     eyemei:latest
   ```

3. **View logs:**
   ```bash
   docker logs -f eyemei-app
   ```

4. **Stop the container:**
   ```bash
   docker stop eyemei-app
   docker rm eyemei-app
   ```

## Architecture

The Docker container runs two Flask applications:

- **Main Application** (Port 5000): The primary eyeMEI lookup service
- **Admin Panel** (Port 5001): Database management and lookup log review interface

Both services run under Gunicorn for production-grade performance.

## Data Persistence

The following directories are mounted as volumes to persist data:

- `./databases`: Contains all JSON databases and lookup logs
- `./public`: Contains device images and other public assets

## Configuration

### Environment Variables

You can customize the deployment by setting environment variables in a `.env` file:

```env
FLASK_ENV=production
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=120
MAIN_APP_PORT=5000
ADMIN_PANEL_PORT=5001
```

### Resource Limits

To set memory and CPU limits, add to `docker-compose.yml`:

```yaml
services:
  eyemei:
    # ... existing configuration ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 512M
```

## Health Checks

The container includes a health check that verifies the main application is responding. Check status with:

```bash
docker ps
```

Look for `healthy` in the STATUS column.

## Troubleshooting

### Container won't start

Check the logs:
```bash
docker-compose logs eyemei
```

### Port already in use

If ports 5000 or 5001 are already in use, modify the port mappings in `docker-compose.yml`:

```yaml
ports:
  - "8000:5000"  # Main app accessible on host port 8000
  - "8001:5001"  # Admin panel accessible on host port 8001
```

### Rebuild after code changes

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Production Deployment

For production deployments:

1. Use a reverse proxy (nginx, Traefik) for HTTPS
2. Set appropriate worker counts based on CPU cores
3. Configure log rotation
4. Use Docker secrets for sensitive configuration
5. Set up monitoring and alerting

Example nginx configuration:

```nginx
upstream eyemei_app {
    server localhost:5000;
}

upstream eyemei_admin {
    server localhost:5001;
}

server {
    listen 80;
    server_name eyemei.yourdomain.com;

    location / {
        proxy_pass http://eyemei_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name admin.eyemei.yourdomain.com;

    location / {
        proxy_pass http://eyemei_admin;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Updating the Application

1. Pull the latest code
2. Rebuild and restart:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

## Backup

To backup your data:

```bash
# Backup databases
tar -czf eyemei-backup-$(date +%Y%m%d).tar.gz databases/

# Backup with Docker volume
docker run --rm -v eyemei-1_databases:/data -v $(pwd):/backup alpine tar czf /backup/databases-backup.tar.gz /data
```
