#!/bin/bash
# Quick start script for minimal LlamaGuard-7b service

echo "🚀 Starting Minimal LlamaGuard-7b Service"
echo "========================================"

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "📦 Using Docker deployment..."
    
    # Build and run with Docker Compose
    docker-compose up --build -d
    
    echo "⏳ Waiting for service to start..."
    sleep 30
    
    # Test the service
    echo "🧪 Testing service..."
    python test_integration.py
    
    echo "✅ Service is running at http://localhost:8000"
    echo "📖 API docs available at http://localhost:8000/docs"
    
else
    echo "🐍 Using Python deployment..."
    
    # Check if Python is available
    if command -v python3 &> /dev/null; then
        echo "Installing dependencies..."
        pip install -r requirements.txt
        
        echo "Starting service..."
        python api.py
    else
        echo "❌ Python3 not found. Please install Python 3.11+"
        exit 1
    fi
fi
