#!/bin/bash

# Shield AI Monitoring Setup Script
# Configura e inicia el stack completo de monitoreo

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}"
    echo "============================================="
    echo "        Shield AI Monitoring Setup"
    echo "============================================="
    echo -e "${NC}"
}

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

check_requirements() {
    print_step "Checking requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "All requirements met!"
}

setup_directories() {
    print_step "Setting up directories..."
    
    # Create directories if they don't exist
    mkdir -p config/grafana
    mkdir -p dashboards
    
    print_success "Directories created!"
}

check_backend() {
    print_step "Checking Shield AI Backend..."
    
    # Check if backend is running on port 8000
    if ! curl -s http://localhost:8000/health &> /dev/null; then
        print_warning "Shield AI Backend not detected on port 8000"
        print_warning "Make sure to start the backend before monitoring can collect metrics"
    else
        print_success "Shield AI Backend is running!"
    fi
}

start_monitoring() {
    print_step "Starting monitoring stack..."
    
    # Pull latest images
    print_step "Pulling Docker images..."
    docker-compose pull
    
    # Start services
    print_step "Starting services..."
    docker-compose up -d
    
    # Wait for services to be ready
    print_step "Waiting for services to start..."
    sleep 10
    
    print_success "Monitoring stack started!"
}

verify_services() {
    print_step "Verifying services..."
    
    services=(
        "prometheus:9090:/api/v1/status/config"
        "grafana:3000:/api/health"
        "alertmanager:9093/-/healthy"
        "node-exporter:9100/metrics"
    )
    
    for service in "${services[@]}"; do
        IFS=':' read -r name port path <<< "$service"
        
        echo -n "  Checking $name... "
        if curl -s http://localhost:$port$path &> /dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
            print_warning "$name is not responding on port $port"
        fi
    done
}

print_access_info() {
    echo -e "${BLUE}"
    echo "============================================="
    echo "      Monitoring Services Access Info"
    echo "============================================="
    echo -e "${NC}"
    
    echo -e "${GREEN}Grafana Dashboard:${NC} http://localhost:3000"
    echo -e "  Username: admin"
    echo -e "  Password: admin123"
    echo ""
    
    echo -e "${GREEN}Prometheus:${NC} http://localhost:9090"
    echo -e "${GREEN}AlertManager:${NC} http://localhost:9093"
    echo -e "${GREEN}Node Exporter:${NC} http://localhost:9100"
    echo ""
    
    echo -e "${GREEN}Backend Metrics:${NC} http://localhost:8000/metrics"
    echo -e "${GREEN}Backend Health:${NC} http://localhost:8000/metrics/health"
    echo ""
    
    echo -e "${BLUE}=============================================${NC}"
}

show_help() {
    echo "Shield AI Monitoring Setup Script"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  start    Start the monitoring stack (default)"
    echo "  stop     Stop the monitoring stack"
    echo "  restart  Restart the monitoring stack"
    echo "  status   Show status of services"
    echo "  logs     Show logs from all services"
    echo "  clean    Stop and remove all containers and volumes"
    echo "  help     Show this help message"
    echo ""
}

stop_monitoring() {
    print_step "Stopping monitoring stack..."
    docker-compose down
    print_success "Monitoring stack stopped!"
}

restart_monitoring() {
    print_step "Restarting monitoring stack..."
    docker-compose down
    docker-compose up -d
    sleep 10
    print_success "Monitoring stack restarted!"
}

show_status() {
    print_step "Checking service status..."
    docker-compose ps
}

show_logs() {
    print_step "Showing logs from all services..."
    docker-compose logs -f
}

clean_monitoring() {
    print_warning "This will remove all monitoring containers and data!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Cleaning monitoring stack..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        print_success "Monitoring stack cleaned!"
    else
        echo "Operation cancelled."
    fi
}

# Main script
main() {
    case "${1:-start}" in
        "start")
            print_header
            check_requirements
            setup_directories
            check_backend
            start_monitoring
            verify_services
            print_access_info
            ;;
        "stop")
            stop_monitoring
            ;;
        "restart")
            restart_monitoring
            verify_services
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "clean")
            clean_monitoring
            ;;
        "help")
            show_help
            ;;
        *)
            echo "Invalid option: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"