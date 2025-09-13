# FTransport Deployment Guide

This guide covers how to deploy FTransport with proper configuration management and security.

## 🔧 Configuration Management

FTransport uses a layered configuration system with the following precedence (highest to lowest):

1. **Environment Variables** (highest priority)
2. **Environment-specific YAML files** (`config/production.yml`, `config/development.yml`)
3. **Default YAML configuration** (`config/default.yml`)

## 📋 Prerequisites

### Required
- Python 3.11+
- Node.js 18+
- Google Cloud Project with Drive API enabled
- Google Service Account with appropriate permissions

### Optional
- PostgreSQL database (for production)
- Redis (for production caching)
- SMTP server (for notifications)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo>
cd FTransport
```

### 2. Backend Configuration

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.template .env

# Edit .env with your configuration
nano .env
```

**Minimum required environment variables:**
```bash
# Security
SECRET_KEY=your-secure-secret-key-here

# Google Cloud
GOOGLE_SERVICE_ACCOUNT_KEY=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT_ID=your-project-id
NOTEBOOKLM_PROJECT_ID=your-notebooklm-project-id
```

### 3. Frontend Configuration  

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.template .env

# Edit .env
nano .env
```

**Required frontend variables:**
```bash
REACT_APP_API_URL=http://localhost:8000
```

### 4. Start Services

**Backend:**
```bash
cd backend
python -m app.main
```

**Frontend:**
```bash
cd frontend  
npm start
```

## 🏗️ Production Deployment

### 1. Environment-Specific Configuration

Create production config file:

```bash
# backend/config/production.yml
app:
  environment: "production"

database:
  url: "postgresql://user:pass@host:5432/ftransport"
  
api:
  cors_origins:
    - "https://your-frontend-domain.com"

security:
  access_token_expire_minutes: 720  # 12 hours

monitoring:
  log_level: "WARNING"
```

### 2. Environment Variables

Set production environment variables:

```bash
export FTRANSPORT_ENV=production
export SECRET_KEY=your-production-secret-key
export GOOGLE_SERVICE_ACCOUNT_KEY=/secure/path/to/service-account.json
export DATABASE_URL=postgresql://user:pass@host:5432/ftransport
```

### 3. Google Cloud Setup

**Enable Required APIs:**
1. Google Drive API
2. AI Platform API (for NotebookLM)

**Service Account Permissions:**
- Google Drive access
- Cloud Platform access
- NotebookLM Enterprise access

**Share Google Drive Landing Zone:**
If using a specific landing folder, share it with your service account:
```
service-account@your-project.iam.gserviceaccount.com
```

### 4. Production Deployment Options

**Option A: Docker** (Recommended)
```dockerfile
# Example Dockerfile for backend
FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
CMD ["python", "-m", "app.main"]
```

**Option B: Systemd Service**
```ini
[Unit]
Description=FTransport Backend
After=network.target

[Service]
Type=simple
User=ftransport
WorkingDirectory=/opt/ftransport/backend
Environment=FTRANSPORT_ENV=production
ExecStart=/opt/ftransport/venv/bin/python -m app.main
Restart=always

[Install]
WantedBy=multi-user.target
```

**Option C: Cloud Platforms**
- Google Cloud Run
- AWS ECS
- Azure Container Instances
- Heroku

## 🔒 Security Best Practices

### 1. Secrets Management

**Never commit secrets to Git:**
- Use environment variables for all sensitive data
- Use cloud secret management services (Google Secret Manager, AWS Secrets Manager)
- Rotate secrets regularly

### 2. Service Account Security

**Google Service Account:**
- Use least privilege principle
- Store JSON key securely
- Consider using Workload Identity (GKE) or IAM roles (cloud platforms)

### 3. Database Security

**Production Database:**
- Use connection pooling
- Enable SSL/TLS
- Use strong passwords
- Regular backups

### 4. API Security

**Production API:**
- Use HTTPS only
- Enable CORS properly
- Implement rate limiting
- Monitor for unusual activity

## 🧪 Testing Configuration

Test your configuration:

```bash
# Test backend config loading
cd backend
python -c "from app.config import settings; print(f'Environment: {settings.app.environment}')"

# Test Google Cloud access
python -c "from app.services.google_drive_service import GoogleDriveService; svc = GoogleDriveService()"
```

## 📊 Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/api/health

# Check configuration
curl http://localhost:8000/api/health/config
```

### Logging

Logs include configuration loading information:
```
🔧 Loading FTransport configuration for environment: production
✅ Loaded default configuration
✅ Loaded production configuration  
🔐 Environment override: SECRET_KEY
🔐 Environment override: DATABASE_URL
✅ Configuration loaded successfully
```

## 🔄 Configuration Examples

### Development
```yaml
# config/development.yml
database:
  url: "sqlite:///./ftransport_dev.db"
  echo: true

monitoring:
  log_level: "DEBUG"
```

### Staging
```yaml  
# config/staging.yml
database:
  url: "postgresql://user:pass@staging-db:5432/ftransport"

api:
  cors_origins:
    - "https://staging.ftransport.com"
```

### Production
```yaml
# config/production.yml  
database:
  url: "postgresql://user:pass@prod-db:5432/ftransport"

transfer:
  max_concurrent: 10
  max_file_size_gb: 5

monitoring:
  log_level: "ERROR"
```

## 🆘 Troubleshooting

### Configuration Issues

**Problem:** "Config file not found"
**Solution:** Ensure `config/default.yml` exists and is readable

**Problem:** "Google Drive API not enabled"
**Solution:** Enable Google Drive API in Google Cloud Console for your project

**Problem:** "Service account permission denied"  
**Solution:** Check service account has proper roles and shared folder access

### Environment Variables

**Check loaded environment:**
```bash
python -c "from app.config import settings; print(vars(settings))"
```

**Verify Google Cloud setup:**
```bash
python -c "from app.services.google_drive_service import GoogleDriveService; print('✅ Google Drive service working')"
```

## 📞 Support

For deployment issues:
1. Check application logs
2. Verify all environment variables are set
3. Test Google Cloud API access
4. Ensure all required services are running