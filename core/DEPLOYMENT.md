# SIMA MVP - Deployment Guide

## Architecture Overview

```
┌─────────────────────┐
│  Nginx (Port 80)    │ ← Load balancer & reverse proxy
└────────────┬────────┘
             │
     ┌───────┴────────┐
     ↓                ↓
┌──────────────┐  ┌──────────────┐
│   Backend    │  │  Frontend    │
│  FastAPI     │  │  HTML/CSS/JS │
│  (Port 5000) │  │  (Served by  │
└──────────────┘  │  FastAPI)    │
     ↓            └──────────────┘
┌──────────────┐
│ PostgreSQL   │
│ (Port 5432)  │
└──────────────┘
```

## Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Docker & Docker Compose (optional)

### Setup

```bash
cd SIMA_CODEBASE_ORGANIZED/backend/core

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 5000
```

Access:
- Frontend: http://localhost:5000
- API Docs: http://localhost:5000/docs

## Docker Deployment (Recommended)

### Build & Run with Docker Compose

```bash
cd SIMA_CODEBASE_ORGANIZED/backend/core

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services running:
- **Backend**: http://localhost:5000 (via Nginx on port 80)
- **Database**: PostgreSQL on port 5432
- **API Docs**: http://localhost/docs
- **Nginx**: Port 80

### Manual Docker Build

```bash
# Build image
docker build -t sima-backend:latest .

# Run container
docker run -p 5000:5000 \
  -e DATABASE_URL=postgresql://user:pass@db:5432/sima \
  sima-backend:latest
```

## Production Deployment

### AWS EC2

```bash
# Launch EC2 instance (Ubuntu 22.04 LTS)
ssh -i key.pem ubuntu@<instance-ip>

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Clone repository
git clone <repo-url> sima
cd sima/SIMA_CODEBASE_ORGANIZED/backend/core

# Configure environment
cat > .env << EOF
DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/sima
ENVIRONMENT=production
DEBUG=false
EOF

# Deploy
docker-compose -f docker-compose.yml up -d

# Setup SSL with Let's Encrypt
sudo apt-get install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d your-domain.com
```

### Heroku

```bash
# Login to Heroku
heroku login

# Create app
heroku create sima-mvp

# Set buildpack
heroku buildpacks:set heroku/python

# Configure environment
heroku config:set DATABASE_URL=postgresql://...
heroku config:set ENVIRONMENT=production

# Deploy
git push heroku main
```

### DigitalOcean App Platform

1. Fork repository to GitHub
2. Connect GitHub account in App Platform
3. Create new app
4. Configure:
   - **Name**: sima-mvp
   - **Environment**: Production
   - **HTTP Port**: 5000
5. Set environment variables
6. Deploy

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sima

# API
API_HOST=0.0.0.0
API_PORT=5000
API_WORKERS=4

# Security
SECRET_KEY=your-secret-key
DEBUG=false
CORS_ORIGINS=*

# Logging
LOG_LEVEL=INFO
```

## Monitoring & Maintenance

### Check Health

```bash
curl http://localhost:5000/health
```

### View Logs

```bash
# Docker Compose
docker-compose logs -f sima-backend

# Direct
tail -f /tmp/backend.log
```

### Database Backup

```bash
# PostgreSQL dump
pg_dump -U user -d sima > backup.sql

# Restore
psql -U user -d sima < backup.sql
```

## Scaling

### Horizontal Scaling (Multiple Instances)

```yaml
# docker-compose.yml
services:
  backend-1:
    ...
  backend-2:
    ...
  backend-3:
    ...
  
  nginx:
    upstream backend {
      server backend-1:5000;
      server backend-2:5000;
      server backend-3:5000;
    }
```

### Vertical Scaling (Increase Resources)

- Increase CPU/Memory in cloud provider
- Adjust worker count: `API_WORKERS=8`
- Enable connection pooling in database

## Performance Optimization

1. **Enable Gzip** in nginx.conf:
```nginx
gzip on;
gzip_types text/html application/json text/css;
```

2. **Add Caching Headers**:
```nginx
location /static {
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

3. **Database Optimization**:
- Create indexes on frequently queried columns
- Enable query logging to identify slow queries
- Use connection pooling (PgBouncer)

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 5000
lsof -i :5000

# Kill process
kill -9 <PID>
```

### Database Connection Issues
```bash
# Test connection
psql -U user -h localhost -d sima -c "SELECT 1;"

# Check DATABASE_URL format
# Should be: postgresql://user:password@host:port/database
```

### Frontend Not Loading
```bash
# Check if index.html exists
ls -la app/static/index.html

# Clear browser cache (Ctrl+Shift+Delete)

# Check browser console for errors (F12)
```

## CI/CD Pipeline

### GitHub Actions Example

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build Docker image
        run: docker build -t sima-backend:latest .
      
      - name: Push to registry
        run: docker push sima-backend:latest
      
      - name: Deploy to production
        run: docker-compose -f docker-compose.yml up -d
```

## Support & Documentation

- API Docs: http://your-domain.com/docs
- Technical Brief: TECHNICAL_BRIEF_SUMMARY.md
- Architecture: TECHNICAL_ARCHITECTURE.md
