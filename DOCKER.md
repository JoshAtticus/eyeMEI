# Docker Deployment Guide for eyeMEI

This guide explains how to build and run the eyeMEI application using Docker.

## Quick Start

### Using Docker Compose (Recommended - Separate Containers)

This approach runs the main app and admin panel in separate containers, which is the most reliable method.

1. **Build and start the application:**
   ```bash
   docker-compose up -d
   ```

2. **Access the services:**
   - Main Application: http://localhost:3002
   - Admin Panel: http://localhost:3003

3. **View logs:**
   ```bash
   # All services
   docker-compose logs -f
   
   # Main app only
   docker-compose logs -f eyemei-app
   
   # Admin panel only
   docker-compose logs -f eyemei-admin
   ```

4. **Stop the application:**
   ```bash
   docker-compose down
   ```

### Using Single Container (Alternative - Supervisor)

If you prefer running both services in a single container using supervisor:

1. **Build the Docker image:**
   ```bash
   docker build -t eyemei:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name eyemei-app \
     -p 3002:3002 \
     -p 3003:3003 \
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

### Separate Container Architecture (docker-compose.yml)

The recommended setup uses two separate Docker containers:

- **eyemei-app** (Port 3002): The primary eyeMEI lookup service
  - Runs with 4 Gunicorn workers
  - Isolated environment prevents conflicts
  
- **eyemei-admin** (Port 3003): Database management and lookup log review interface
  - Runs with 2 Gunicorn workers
  - Shares database volume with main app

Both services run under Gunicorn for production-grade performance. This architecture eliminates the `GUNICORN_FD` environment variable conflicts that can occur when running multiple Gunicorn instances in a single process space.

### Single Container Architecture (Dockerfile)

The alternative setup uses supervisor to manage both services in one container. This is simpler but slightly less isolated than the multi-container approach.

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

If ports 3002 or 3003 are already in use, modify the port mappings in `docker-compose.yml`:

```yaml
ports:
  - "8000:3002"  # Main app accessible on host port 8000
  - "8001:3003"  # Admin panel accessible on host port 8001
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
    server localhost:3002;
}

upstream eyemei_admin {
    server localhost:3003;
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
