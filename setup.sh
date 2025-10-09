#!/bin/bash

# FastAPI Guardrails Service Setup Script
# This script sets up the complete development and production environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
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

check_requirements() {
    print_status "Checking system requirements..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
    
    print_success "All requirements are met!"
}

setup_environment() {
    print_status "Setting up environment variables..."
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        cp env.example .env
        print_warning "Created .env file from template. Please update with your values."
    else
        print_status ".env file already exists."
    fi
    
    # Create necessary directories
    mkdir -p logs models data monitoring/grafana/dashboards monitoring/grafana/datasources nginx/ssl
    
    print_success "Environment setup complete!"
}

install_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Created virtual environment."
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    pip install --upgrade pip
    pip install -r enhanced_requirements.txt
    
    # Download spaCy model
    python -m spacy download en_core_web_sm
    
    print_success "Dependencies installed!"
}

build_docker_images() {
    print_status "Building Docker images..."
    
    # Build the main application image
    docker build -t guardrails-api:latest .
    
    # Build development image
    docker build --target development -t guardrails-api:dev .
    
    # Build testing image
    docker build --target testing -t guardrails-api:test .
    
    print_success "Docker images built!"
}

run_tests() {
    print_status "Running tests..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Start Redis for tests
    docker run -d --name test-redis -p 6379:6379 redis:7-alpine
    
    # Wait for Redis to be ready
    sleep 5
    
    # Run tests
    pytest tests/ -v --cov=enhanced_guardrails --cov-report=html --cov-report=xml
    
    # Stop test Redis
    docker stop test-redis
    docker rm test-redis
    
    print_success "Tests completed!"
}

start_development() {
    print_status "Starting development environment..."
    
    # Start services with docker-compose
    docker-compose up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to start..."
    sleep 30
    
    # Check if services are running
    if curl -f http://localhost:8000/v1/guardrails/health > /dev/null 2>&1; then
        print_success "Development environment is running!"
        print_status "API available at: http://localhost:8000"
        print_status "API docs at: http://localhost:8000/docs"
        print_status "Grafana at: http://localhost:3000 (admin/admin)"
        print_status "Prometheus at: http://localhost:9090"
    else
        print_error "Failed to start development environment. Check logs with: docker-compose logs"
        exit 1
    fi
}

start_production() {
    print_status "Starting production environment..."
    
    # Check if .env.prod exists
    if [ ! -f .env.prod ]; then
        print_error ".env.prod file not found. Please create it with production values."
        exit 1
    fi
    
    # Start production services
    docker-compose -f docker-compose.prod.yml up -d
    
    print_success "Production environment started!"
}

run_load_tests() {
    print_status "Running load tests..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install Locust if not already installed
    pip install locust
    
    # Start the application
    docker-compose up -d
    
    # Wait for application to be ready
    sleep 30
    
    # Run load tests
    locust -f tests/load_test.py --host=http://localhost:8000 --users=50 --spawn-rate=5 --run-time=60s --headless --html=load-test-report.html
    
    print_success "Load tests completed! Report saved as load-test-report.html"
}

cleanup() {
    print_status "Cleaning up..."
    
    # Stop all containers
    docker-compose down
    docker-compose -f docker-compose.prod.yml down
    
    # Remove test containers
    docker stop test-redis 2>/dev/null || true
    docker rm test-redis 2>/dev/null || true
    
    # Remove unused images
    docker image prune -f
    
    print_success "Cleanup complete!"
}

show_help() {
    echo "FastAPI Guardrails Service Setup Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  setup       - Complete setup (check requirements, install deps, build images)"
    echo "  dev         - Start development environment"
    echo "  prod        - Start production environment"
    echo "  test        - Run tests"
    echo "  load-test   - Run load tests"
    echo "  build       - Build Docker images"
    echo "  cleanup     - Clean up containers and images"
    echo "  help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup    # Complete setup"
    echo "  $0 dev      # Start development"
    echo "  $0 test     # Run tests"
}

# Main script
case "${1:-help}" in
    setup)
        check_requirements
        setup_environment
        install_dependencies
        build_docker_images
        print_success "Setup complete! Run '$0 dev' to start development environment."
        ;;
    dev)
        start_development
        ;;
    prod)
        start_production
        ;;
    test)
        run_tests
        ;;
    load-test)
        run_load_tests
        ;;
    build)
        build_docker_images
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
