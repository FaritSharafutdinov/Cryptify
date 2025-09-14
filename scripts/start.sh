#!/bin/bash

echo "Starting Criptify Project..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker first."
    exit 1
fi

# Navigate to project directory
cd "$(dirname "$0")/.."

echo "Working directory: $(pwd)"

# Start services with Docker Compose
echo "Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Check service status
echo "Service status:"
docker-compose ps

# Test API endpoints
echo "Testing API endpoints..."
if command -v curl > /dev/null; then
    echo "Testing health endpoint..."
    curl -s http://localhost:8000/health | jq . || echo "Health check failed"
else
    echo "curl not found, skipping API tests"
fi

echo "Criptify project started successfully!"
echo ""
echo "📋 Useful commands:"
echo "  View logs: docker-compose logs -f"
echo "  Stop services: docker-compose down"
echo "  API docs: http://localhost:8000/docs"
echo "  Health check: http://localhost:8000/health"
