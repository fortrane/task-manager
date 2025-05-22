#!/bin/bash

# Color codes for beautiful output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Function to print colored text
print_color() {
    printf "${2}${1}${NC}\n"
}

# Function to print step with emoji
print_step() {
    echo ""
    print_color "🔄 $1" $CYAN
}

# Function to print success with emoji
print_success() {
    print_color "✅ $1" $GREEN
}

# Function to print warning with emoji
print_warning() {
    print_color "⚠️  $1" $YELLOW
}

# Function to print error with emoji
print_error() {
    print_color "❌ $1" $RED
}

# Function to print info with emoji
print_info() {
    print_color "ℹ️  $1" $BLUE
}

# Beautiful banner
show_banner() {
    echo ""
    print_color "██████████████████████████████████████████████████████████" $PURPLE
    print_color "█                                                        █" $PURPLE
    print_color "█  ████████  ███████  █████  █   █      █   █  █████████ █" $PURPLE
    print_color "█     ██     ██   ██  ██     █  █       ██ ██  ██        █" $PURPLE
    print_color "█     ██     ███████  █████  ███        █ █ █  █████     █" $PURPLE
    print_color "█     ██     ██   ██     ██  █  █       █   █  ██        █" $PURPLE
    print_color "█     ██     ██   ██  █████  █   █      █   █  █████████ █" $PURPLE
    print_color "█                                                        █" $PURPLE
    print_color "█           🚀 TASK MANAGER API SETUP 🚀                 █" $PURPLE
    print_color "█                                                        █" $PURPLE
    print_color "█  📋 FastAPI + PostgreSQL + Telegram Bot               █" $PURPLE
    print_color "█  📊 Prometheus + Grafana + Traefik + Jenkins          █" $PURPLE
    print_color "█  🍎 Optimized for Apple Silicon                        █" $PURPLE
    print_color "█                                                        █" $PURPLE
    print_color "██████████████████████████████████████████████████████████" $PURPLE
    echo ""
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check system requirements
check_requirements() {
    print_step "Checking system requirements..."

    local missing_deps=()

    if ! command_exists docker; then
        missing_deps+=("docker")
    fi

    if ! command_exists docker-compose; then
        missing_deps+=("docker-compose")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        print_info "Please install missing dependencies:"
        for dep in "${missing_deps[@]}"; do
            case $dep in
                "docker")
                    print_info "  • Install Docker Desktop: https://docs.docker.com/desktop/mac/"
                    ;;
                "docker-compose")
                    print_info "  • Docker Compose should come with Docker Desktop"
                    print_info "  • Or install separately: brew install docker-compose"
                    ;;
            esac
        done
        exit 1
    fi

    print_success "All system requirements satisfied!"
}

# Function to check if Docker is running
check_docker_running() {
    print_step "Checking if Docker is running..."

    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running!"
        print_info "Please start Docker Desktop and try again."
        exit 1
    fi

    print_success "Docker is running!"
}

# Function to setup environment file
setup_environment() {
    print_step "Setting up environment configuration..."

    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            print_success "Created .env file from .env.example"
            print_warning "Please update .env file with your actual configuration:"
            print_info "  • TELEGRAM_BOT_TOKEN - Get from @BotFather on Telegram"
            print_info "  • POSTGRES_PASSWORD - Set a secure password"
            print_info "  • Other settings as needed"
        else
            print_error ".env.example file not found!"
            exit 1
        fi
    else
        print_success "Environment file (.env) already exists"
    fi
}

# Function to check available ports
check_ports() {
    print_step "Checking if required ports are available..."

    local ports=(80 8000 8080 8081 5432 9090 3001)
    local busy_ports=()

    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            busy_ports+=($port)
        fi
    done

    if [ ${#busy_ports[@]} -ne 0 ]; then
        print_warning "Some ports are already in use: ${busy_ports[*]}"
        print_info "You may need to stop other services or modify port configuration"
        read -p "🤔 Do you want to continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Setup cancelled by user"
            exit 0
        fi
    else
        print_success "All required ports are available!"
    fi
}

# Function to build and start services
start_services() {
    print_step "Building and starting Docker services..."

    # Pull/build images with progress
    print_info "📦 Pulling and building Docker images..."
    docker-compose build --parallel

    if [ $? -ne 0 ]; then
        print_error "Failed to build Docker images!"
        exit 1
    fi

    print_success "Docker images built successfully!"

    # Start services
    print_info "🚀 Starting all services..."
    docker-compose up -d

    if [ $? -ne 0 ]; then
        print_error "Failed to start services!"
        exit 1
    fi

    print_success "All services started successfully!"
}

# Function to wait for services to be ready
wait_for_services() {
    print_step "Waiting for services to be ready..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        print_info "🔍 Health check attempt $attempt/$max_attempts..."

        # Check if API is responding
        if curl -s http://localhost:8000/ >/dev/null 2>&1; then
            print_success "API service is ready!"
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            print_error "Services failed to start properly after $max_attempts attempts"
            print_info "Check logs with: docker-compose logs"
            exit 1
        fi

        sleep 2
        ((attempt++))
    done
}

# Function to show service status and URLs
show_service_info() {
    print_step "Service Information"

    echo ""
    print_color "🌐 Service URLs:" $BOLD
    print_color "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" $CYAN

    printf "%-25s %s\n" "📱 Main API:" "http://localhost:8000"
    printf "%-25s %s\n" "📱 API (via Traefik):" "http://api.localhost"
    printf "%-25s %s\n" "📚 API Documentation:" "http://api.localhost/docs"
    printf "%-25s %s\n" "📊 Prometheus:" "http://prometheus.localhost"
    printf "%-25s %s\n" "📈 Grafana:" "http://grafana.localhost (admin/admin)"
    printf "%-25s %s\n" "🔧 Jenkins:" "http://jenkins.localhost"
    printf "%-25s %s\n" "🚦 Traefik Dashboard:" "http://localhost:8080"
    printf "%-25s %s\n" "📊 Metrics Endpoint:" "http://localhost:8000/metrics"

    echo ""
    print_color "🐳 Docker Services Status:" $BOLD
    print_color "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" $CYAN
    docker-compose ps

    echo ""
    print_color "💡 Useful Commands:" $BOLD
    print_color "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" $CYAN
    printf "%-30s %s\n" "📋 View logs:" "docker-compose logs -f [service]"
    printf "%-30s %s\n" "🔄 Restart service:" "docker-compose restart [service]"
    printf "%-30s %s\n" "🛑 Stop all services:" "./setup.sh clean"
    printf "%-30s %s\n" "🧪 Run tests:" "docker-compose exec api pytest tests/ -v"
    printf "%-30s %s\n" "📊 Load testing:" "docker-compose exec api locust -f tests/locustfile.py"
}

# Function to clean up everything
clean_environment() {
    print_step "Cleaning up Task Manager environment..."

    print_info "🛑 Stopping all services..."
    docker-compose down

    print_info "🗑️  Removing containers, networks, and images..."
    docker-compose down --rmi all --volumes --remove-orphans

    # Remove any dangling containers related to the project
    print_info "🧹 Cleaning up Docker system..."
    docker system prune -f

    print_success "Environment cleaned successfully!"
    print_info "To start again, run: ./setup.sh"
}

# Function to show help
show_help() {
    show_banner
    echo ""
    print_color "📖 Usage:" $BOLD
    print_color "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" $CYAN
    printf "%-20s %s\n" "./setup.sh" "Start the complete Task Manager environment"
    printf "%-20s %s\n" "./setup.sh clean" "Stop and clean up everything"
    printf "%-20s %s\n" "./setup.sh help" "Show this help message"
    echo ""

    print_color "🎯 What this script does:" $BOLD
    print_color "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" $CYAN
    printf "%s\n" "• ✅ Checks system requirements (Docker, Docker Compose)"
    printf "%s\n" "• 🔧 Sets up environment configuration (.env file)"
    printf "%s\n" "• 🚀 Builds and starts all services with Docker Compose"
    printf "%s\n" "• 🏥 Waits for services to be healthy and ready"
    printf "%s\n" "• 📊 Shows service URLs and useful information"
    printf "%s\n" "• 🧹 Provides cleanup functionality"
    echo ""
}

# Main execution
main() {
    # Check command line arguments
    case "${1:-start}" in
        "clean")
            show_banner
            clean_environment
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        "start"|"")
            show_banner
            print_color "🎉 Welcome to Task Manager API Setup!" $BOLD
            print_info "This script will set up your complete development environment"
            echo ""

            check_requirements
            check_docker_running
            setup_environment
            check_ports
            start_services
            wait_for_services
            show_service_info

            echo ""
            print_color "🎉 Task Manager API is now running!" $GREEN
            print_color "🚀 Your development environment is ready to use!" $GREEN
            echo ""
            ;;
        *)
            print_error "Unknown command: $1"
            print_info "Use './setup.sh help' for usage information"
            exit 1
            ;;
    esac
}

# Check if script is being run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi