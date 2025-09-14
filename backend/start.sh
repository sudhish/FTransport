#!/bin/bash

# FTransport Backend Startup Script
# This script validates configuration and starts the backend server

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a file exists
check_file_exists() {
    local file_path="$1"
    local description="$2"
    
    if [[ -f "$file_path" ]]; then
        print_success "$description found: $file_path"
        return 0
    else
        print_error "$description not found: $file_path"
        return 1
    fi
}

# Function to validate environment variable
validate_env_var() {
    local var_name="$1"
    local description="$2"
    local is_required="${3:-true}"
    
    if [[ -n "${!var_name}" ]]; then
        print_success "$description: ✓"
        return 0
    else
        if [[ "$is_required" == "true" ]]; then
            print_error "$description: ✗ (REQUIRED)"
            return 1
        else
            print_warning "$description: ✗ (OPTIONAL)"
            return 0
        fi
    fi
}

# Function to validate file path from environment variable
validate_env_file_path() {
    local var_name="$1"
    local description="$2"
    local is_required="${3:-true}"
    
    if [[ -n "${!var_name}" ]]; then
        if [[ -f "${!var_name}" ]]; then
            print_success "$description: ✓ (${!var_name})"
            return 0
        else
            print_error "$description: ✗ File not found: ${!var_name}"
            return 1
        fi
    else
        if [[ "$is_required" == "true" ]]; then
            print_error "$description: ✗ Environment variable $var_name not set"
            return 1
        else
            print_warning "$description: ✗ (OPTIONAL)"
            return 0
        fi
    fi
}

print_status "🚀 Starting FTransport Backend Server"
print_status "======================================"

# Check if we're in the correct directory
if [[ ! -f "app/main.py" ]]; then
    print_error "Please run this script from the backend directory"
    print_error "Expected: /path/to/FTransport/backend/"
    print_error "Current:  $(pwd)"
    exit 1
fi

# Step 1: Check if .env file exists
print_status "📋 Step 1: Checking configuration files..."
if ! check_file_exists ".env" ".env configuration file"; then
    print_error "Please create a .env file with your configuration"
    print_error "You can copy from .env.example: cp .env.example .env"
    exit 1
fi

# Step 2: Load environment variables
print_status "📋 Step 2: Loading environment variables..."
set -a  # Automatically export all variables
source .env
set +a  # Stop automatically exporting

print_success "Environment variables loaded from .env"

# Step 3: Validate required configuration
print_status "📋 Step 3: Validating configuration..."

validation_failed=false

# Critical configuration checks
print_status "Critical Configuration:"
validate_env_var "DATABASE_URL" "Database URL" || validation_failed=true
validate_env_var "SECRET_KEY" "Secret Key" || validation_failed=true

# Google Cloud configuration
print_status "Google Cloud Configuration:"
validate_env_file_path "GOOGLE_SERVICE_ACCOUNT_KEY" "Google Service Account Key" || validation_failed=true
validate_env_var "GOOGLE_CLOUD_PROJECT_ID" "Google Cloud Project ID" || validation_failed=true

# Optional but recommended configuration
print_status "Optional Configuration:"
validate_env_var "NOTEBOOKLM_PROJECT_ID" "NotebookLM Project ID" false
validate_env_var "GOOGLE_DRIVE_LANDING_ZONE" "Google Drive Landing Zone" false
validate_env_var "DROPBOX_APP_KEY" "Dropbox App Key" false
validate_env_var "ONEDRIVE_CLIENT_ID" "OneDrive Client ID" false

# Check secret key security (warning only for development)
if [[ "$SECRET_KEY" == "your-secret-key-here-change-in-production-REQUIRED" ]]; then
    print_warning "Using default secret key - CHANGE THIS IN PRODUCTION!"
    print_warning "This is acceptable for development but MUST be changed for production"
fi

# Fail if validation errors occurred
if [[ "$validation_failed" == "true" ]]; then
    print_error "Configuration validation failed!"
    print_error "Please fix the issues above and try again."
    exit 1
fi

print_success "Configuration validation passed!"

# Step 4: Check uv installation
print_status "📋 Step 4: Checking uv installation..."
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed or not in PATH"
    print_error "Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

print_success "uv is installed: $(uv --version)"

# Step 5: Install/update dependencies
print_status "📋 Step 5: Installing dependencies..."
if [[ -f "pyproject.toml" ]]; then
    if ! uv sync; then
        print_error "Failed to install dependencies with uv sync"
        exit 1
    fi
elif [[ -f "requirements.txt" ]]; then
    if ! uv pip install -r requirements.txt; then
        print_error "Failed to install dependencies with uv pip install"
        exit 1
    fi
else
    print_error "No pyproject.toml or requirements.txt found"
    exit 1
fi

print_success "Dependencies installed successfully"

# Step 6: Validate Python environment
print_status "📋 Step 6: Validating Python environment..."
if ! uv run python -c "import sys; print(f'Python {sys.version}')" &> /dev/null; then
    print_error "Python environment validation failed"
    exit 1
fi

print_success "Python environment ready"

# Step 7: Test configuration loading
print_status "📋 Step 7: Testing configuration loading..."
if ! uv run python -c "
from app.config import settings
if not settings.google_service_account_key:
    raise Exception('Google service account key not loaded')
print('✓ Configuration loaded successfully')
"; then
    print_error "Configuration loading test failed"
    exit 1
fi

print_success "Configuration loading test passed"

# Step 8: Start the server
print_status "📋 Step 8: Starting FTransport backend server..."
print_success "All validation checks passed!"
print_status "Server will be available at: http://localhost:8000"
print_status "Health check: http://localhost:8000/api/health"
print_status "API docs: http://localhost:8000/docs"
print_status ""
print_status "Press Ctrl+C to stop the server"
print_status "======================================"

# Start the server with environment variables loaded
exec uv run python -m app.main