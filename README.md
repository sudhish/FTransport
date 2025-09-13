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
- Python 3.11+
- Node.js 18+
- Redis (for Prefect)
- PostgreSQL (optional, SQLite works for development)

### Backend Setup

1. **Install dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Environment configuration**:
   ```bash
   cp .env.template .env
   # Edit .env with your configuration
   ```

   **Required environment variables:**
   ```bash
   SECRET_KEY=your-secure-secret-key
   GOOGLE_SERVICE_ACCOUNT_KEY=/path/to/service-account.json
   GOOGLE_CLOUD_PROJECT_ID=your-google-project-id
   NOTEBOOKLM_PROJECT_ID=your-notebooklm-project-id
   ```

3. **Start the server**:
   ```bash
   python -m app.main
   ```

   The API will be available at http://localhost:8000
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/api/health

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

## Support

For issues and feature requests, check the project documentation or create an issue in the repository.