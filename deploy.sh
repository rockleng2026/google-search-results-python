#!/bin/bash
# Deploy to Ubuntu 22.04

set -e

echo "=========================================="
echo "Web Search API - Deployment Script"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing Docker..."
    apt-get update
    apt-get install -y ca-certificates curl gnupg lsb-release
    
    # Add Docker GPG key
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    apt-get install -y docker-compose
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Copy .env file if not exists
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please edit .env file and add your Google API credentials"
fi

# Create logs directory
mkdir -p logs

# Build and start containers
echo "Building Docker container..."
docker-compose build

echo "Starting service..."
docker-compose up -d

echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo "Service URL: http://your-server-ip:5000"
echo ""
echo "Check status: docker-compose ps"
echo "View logs: docker-compose logs -f"
echo "Stop service: docker-compose down"
echo ""
echo "API Endpoints:"
echo "  GET  /health       - Health check"
echo "  GET  /web_search  - Search"
echo "  POST /web_fetch   - Fetch URL content"
echo ""
echo "Example:"
echo "  curl \"http://localhost:5000/web_search?q=python&num=5\""
echo "  curl -X POST -H \"Content-Type: application/json\" -d '{\"url\":\"https://python.org\"}' http://localhost:5000/web_fetch"