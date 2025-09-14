# FTransport - Data Migration Platform

A web-based platform for migrating data from shared drives (Google Drive, OneDrive, Dropbox) to NotebookLM Enterprise with real-time progress tracking.

## Features

- **Multi-Source Support**: Google Drive, OneDrive, and Dropbox
- **Real-time Progress**: WebSocket-based live updates
- **File-level Tracking**: Individual file transfer progress
- **Workflow Management**: Prefect-powered robust workflows
- **Enterprise Ready**: OAuth authentication, audit trails

## Architecture

### Backend
- **FastAPI** - REST API server
- **Prefect** - Workflow engine with built-in UI and logging
- **PostgreSQL/SQLite** - Data persistence
- **WebSocket** - Real-time updates

### Frontend
- **React + TypeScript** - Modern web interface
- **Material-UI** - Professional UI components
- **WebSocket Client** - Live progress updates

## Quick Start

### Prerequisites
- **Python 3.11+** with uv package manager
- **Node.js 18+** with npm
- **Google Cloud Project** with service account
- **PostgreSQL** (optional, SQLite works for development)

## 🚀 Recommended Startup Method

### Using the Startup Scripts (Recommended)

The easiest way to start FTransport is using the provided startup scripts that automatically validate configuration and handle all setup:

#### 1. Backend Startup
```bash
cd backend
./start.sh
```

#### 2. Frontend Startup (in a new terminal)
```bash
cd frontend  
./start.sh
```

The startup scripts will:
- ✅ Validate all required configuration
- ✅ Check for missing files and dependencies
- ✅ Install/update dependencies automatically
- ✅ Verify Google Cloud credentials
- ✅ Test configuration loading
- ✅ Provide clear error messages for any issues

## Manual Setup (Alternative)

### Backend Setup

1. **Install uv package manager** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Environment configuration**:
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your configuration
   ```

   **Required environment variables:**
   ```bash
   SECRET_KEY=your-secure-secret-key
   GOOGLE_SERVICE_ACCOUNT_KEY=/path/to/service-account.json
   GOOGLE_CLOUD_PROJECT_ID=your-google-project-id
   NOTEBOOKLM_PROJECT_ID=your-notebooklm-project-id
   ```

### Google Cloud Setup

#### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name (e.g., "ftransport-demo")
4. Note your **Project ID** (this becomes `GOOGLE_CLOUD_PROJECT_ID`)

#### 2. Enable Required APIs

Enable these APIs in your Google Cloud project:

1. **Google Drive API**:
   - Go to [APIs & Services > Library](https://console.cloud.google.com/apis/library)
   - Search for "Google Drive API"
   - Click "Enable"

2. **NotebookLM API** (for enterprise accounts):
   - Search for "NotebookLM" or "AI Platform"
   - Enable if available (enterprise accounts only)

#### 3. Create Service Account

1. Go to [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click "Create Service Account"
3. **Service account details**:
   - Name: `ftransport-service-account`
   - Description: `Service account for FTransport data migration`
4. **Grant roles**:
   - `Editor` (for Google Drive access)
   - `AI Platform Admin` (for NotebookLM - if available)
5. Click "Done"

#### 4. Generate Service Account Key

1. Click on your newly created service account
2. Go to **Keys** tab
3. Click "Add Key" → "Create new key"
4. Select **JSON** format
5. Click "Create"
6. **Download the JSON file** (e.g., `my-project-12345-abcdef123456.json`)

#### 5. Configure Environment Variables

Place the downloaded JSON file in a secure location and update your `.env` file:

```bash
# Path to your downloaded service account JSON file
GOOGLE_SERVICE_ACCOUNT_KEY=/Users/yourname/Downloads/my-project-12345-abcdef123456.json

# Your Google Cloud Project ID (from step 1)
GOOGLE_CLOUD_PROJECT_ID=my-project-12345

# For NotebookLM (usually same as GOOGLE_CLOUD_PROJECT_ID)
NOTEBOOKLM_PROJECT_ID=my-project-12345
```

#### 6. Verify Setup

Test your configuration:
```bash
cd backend
export $(grep -v '^#' .env | xargs)
uv run python -c "
from app.config import settings
print(f'✅ Service Account: {settings.google_service_account_key}')
print(f'✅ Project ID: {settings.google_cloud_project_id}')
"
```

#### 7. Security Best Practices

- **Never commit** the service account JSON file to version control
- **Restrict file permissions**: `chmod 600 /path/to/service-account.json`
- **Use different service accounts** for development and production
- **Regularly rotate** service account keys

3. **Install dependencies and start**:
   ```bash
   # Export environment variables
   export $(grep -v '^#' .env | xargs)
   
   # Install dependencies
   uv sync
   
   # Start the backend
   uv run python -m app.main
   ```

   The API will be available at http://localhost:8000
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/api/health

   **⚠️ Important**: Always export environment variables before starting manually!

### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Environment configuration**:
   ```bash
   cp .env.template .env
   # Edit .env with your backend URL
   ```

3. **Start development server**:
   ```bash
   npm start
   ```

   The frontend will be available at http://localhost:3000

### Prefect Setup

1. **Start Prefect server**:
   ```bash
   prefect server start
   ```

   Prefect UI will be available at http://localhost:4200

2. **Set API URL**:
   ```bash
   prefect config set PREFECT_API_URL=http://localhost:4200/api
   ```

## Usage

1. **Access the web interface** at http://localhost:3000
2. **Create a new transfer** by entering a shared drive URL
3. **Monitor progress** in real-time with file-level details
4. **View transfer history** and detailed logs

## API Endpoints

### Transfers
- `POST /api/transfers/` - Create new transfer
- `GET /api/transfers/` - List all transfers
- `GET /api/transfers/{id}` - Get transfer details
- `DELETE /api/transfers/{id}` - Cancel transfer
- `WS /ws/transfers/{id}` - Real-time progress updates

### Validation
- `POST /api/transfers/validate-url` - Validate shared drive URL

### Health
- `GET /api/health` - Service health check

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ftransport

# Google Cloud (for NotebookLM Enterprise)
GOOGLE_SERVICE_ACCOUNT_KEY=/path/to/service-account.json
NOTEBOOKLM_PROJECT_ID=your-project-id

# Shared Drive APIs
DROPBOX_APP_KEY=your-dropbox-key
ONEDRIVE_CLIENT_ID=your-onedrive-id

# Security
SECRET_KEY=your-secret-key
```

## Development

### Project Structure

```
FTransport/
├── backend/
│   ├── app/
│   │   ├── routers/          # API endpoints
│   │   ├── services/         # External service integrations
│   │   ├── workflows.py      # Prefect workflows
│   │   ├── database.py       # Database models
│   │   └── main.py          # FastAPI application
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── hooks/           # Custom hooks
│   │   ├── services/        # API client
│   │   └── types/           # TypeScript definitions
│   └── package.json
└── CLAUDE.md                # Product requirements
```

### Adding New Drive Types

1. **Create service class** in `backend/app/services/`
2. **Update drive detector** in `drive_detector.py`
3. **Add to workflow** in `workflows.py`
4. **Update frontend types** in `types/index.ts`

## NotebookLM Integration

### Enterprise vs Non-Enterprise Accounts

**NotebookLM Enterprise (Google Workspace)**:
- Full integration with NotebookLM Enterprise API
- Real notebook creation and file uploads
- Requires Google Workspace account with NotebookLM Enterprise enabled

**Non-Enterprise Google Accounts (Personal/Standard)**:
- **Mock mode fallback** - System simulates NotebookLM operations
- All file processing and transfer logic works normally
- Mock notebook IDs generated (e.g., `mock_notebook_ftransport_transfer_12345...`)
- Perfect for testing and development

### Mock Mode Behavior

When NotebookLM Enterprise API is not available, FTransport automatically falls back to mock mode:

- ✅ **Full file discovery and processing**
- ✅ **Complete progress tracking** 
- ✅ **Transfer workflow validation**
- 🔄 **Simulated notebook creation** with realistic IDs
- 📝 **Detailed logging** of what would happen in production

**How to identify mock mode:**
- Notebook IDs start with `mock_notebook_`
- Transfer logs show "Testing NotebookLM API connectivity..." followed by fallback
- Transfer completes successfully but with simulated uploads

### Enabling Real NotebookLM

To use real NotebookLM Enterprise:
1. **Google Workspace account** with NotebookLM Enterprise enabled
2. **Service account** with NotebookLM API permissions
3. **Correct API endpoints** configured for your region
4. **NOTEBOOKLM_PROJECT_ID** environment variable set

## Production Deployment

### Backend
- Use PostgreSQL for production database
- Set up Redis for Prefect workers
- Configure proper authentication secrets
- Enable HTTPS with reverse proxy

### Frontend
- Build production bundle: `npm run build`
- Serve with nginx or similar
- Configure API_URL for backend

### Monitoring
- Prefect UI provides workflow monitoring
- Database logs all transfer operations
- WebSocket connections for real-time updates

## Security

- OAuth 2.0 for shared drive access
- Service account for NotebookLM Enterprise
- JWT tokens for API authentication
- No persistent storage of user credentials
- HTTPS for all data in transit

## Troubleshooting

### Common Issues

#### "Google Drive service not initialized"
- **Cause**: Environment variables not loaded or service account key file missing
- **Solution**: 
  1. Use the startup script: `./start.sh` (recommended)
  2. Or manually export environment variables: `export $(grep -v '^#' .env | xargs)`
  3. Verify service account key file exists and is readable

#### "Configuration validation failed"
- **Cause**: Missing or invalid configuration in .env file
- **Solution**: 
  1. Run the startup script to see detailed validation errors
  2. Check that all required environment variables are set
  3. Verify file paths exist and are accessible

#### "Port already in use"
- **Cause**: Another process is using port 8000 (backend) or 3000 (frontend)
- **Solution**:
  ```bash
  # Kill processes on ports
  lsof -ti:8000 | xargs kill -9  # Backend
  lsof -ti:3000 | xargs kill -9  # Frontend
  ```

#### Frontend can't connect to backend
- **Cause**: Backend not running or CORS configuration issue
- **Solution**:
  1. Ensure backend is running on http://localhost:8000
  2. Check backend health: `curl http://localhost:8000/api/health`
  3. Verify CORS origins in backend configuration

### Configuration Validation

You can test your configuration without starting the full server:

```bash
cd backend
export $(grep -v '^#' .env | xargs)
uv run python -m app.config_validator
```

### Startup Script Benefits

The provided startup scripts (`./start.sh`) prevent common issues by:
- ✅ Automatically loading environment variables
- ✅ Validating all required configuration
- ✅ Checking file permissions and paths
- ✅ Installing/updating dependencies
- ✅ Providing clear error messages

**Always prefer using `./start.sh` over manual startup methods.**

## Support

For issues and feature requests, check the project documentation or create an issue in the repository.