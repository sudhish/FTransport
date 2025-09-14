#!/bin/bash

# FTransport Frontend Startup Script
# This script validates configuration and starts the React development server

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

print_status "🚀 Starting FTransport Frontend Development Server"
print_status "=============================================="

# Check if we're in the correct directory
if [[ ! -f "package.json" ]]; then
    print_error "Please run this script from the frontend directory"
    print_error "Expected: /path/to/FTransport/frontend/"
    print_error "Current:  $(pwd)"
    exit 1
fi

# Step 1: Check Node.js installation
print_status "📋 Step 1: Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed or not in PATH"
    print_error "Please install Node.js: https://nodejs.org/"
    exit 1
fi

node_version=$(node --version)
print_success "Node.js is installed: $node_version"

# Step 2: Check npm installation
print_status "📋 Step 2: Checking npm installation..."
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed or not in PATH"
    exit 1
fi

npm_version=$(npm --version)
print_success "npm is installed: v$npm_version"

# Step 3: Check package.json
print_status "📋 Step 3: Validating package.json..."
if ! node -e "require('./package.json')" &> /dev/null; then
    print_error "Invalid package.json file"
    exit 1
fi

print_success "package.json is valid"

# Step 4: Install/update dependencies
print_status "📋 Step 4: Installing dependencies..."
if ! npm install; then
    print_error "Failed to install dependencies"
    exit 1
fi

print_success "Dependencies installed successfully"

# Step 5: Check if backend is running
print_status "📋 Step 5: Checking backend connectivity..."
backend_url="http://localhost:8000"

if curl -s -f "$backend_url/api/health" > /dev/null 2>&1; then
    print_success "Backend is running and accessible at $backend_url"
else
    print_warning "Backend is not running at $backend_url"
    print_warning "Please start the backend first:"
    print_warning "  cd ../backend && ./start.sh"
    print_warning ""
    print_warning "The frontend will start anyway, but API calls will fail until the backend is running."
fi

# Step 6: Check for port conflicts
print_status "📋 Step 6: Checking port availability..."
if lsof -i :3000 > /dev/null 2>&1; then
    print_warning "Port 3000 is already in use"
    print_warning "The React dev server will try to use the next available port"
fi

# Step 7: Start the development server
print_status "📋 Step 7: Starting React development server..."
print_success "All validation checks passed!"
print_status "Frontend will be available at: http://localhost:3000"
print_status "Backend API: http://localhost:8000"
print_status ""
print_status "Press Ctrl+C to stop the server"
print_status "=============================================="

# Start the React development server
exec npm start