#!/bin/bash

# Enable colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print section headers
section() {
    echo -e "\n${BLUE}==>${NC} ${GREEN}$1${NC}"
}

# Function to check if service is healthy
check_service() {
    local service_name="$1"
    local max_retries=3
    local retry=0
    
    while [ $retry -lt $max_retries ]; do
        if docker compose ps --status running | grep -q "vera-$service_name"; then
            echo -e "${GREEN}✓ Service $service_name is healthy${NC}"
            return 0
        fi
        
        echo -e "${RED}✗ Service $service_name is not healthy, retrying...${NC}"
        sleep 5
        retry=$((retry + 1))
    done
    
    return 1
}

# Function to start service with retries
start_service() {
    local service_name="$1"
    local max_retries=3
    local retry=0
    
    while [ $retry -lt $max_retries ]; do
        echo -e "${BLUE}==>${NC} Starting service $service_name..."
        docker compose up -d "$service_name"
        
        if check_service "$service_name"; then
            echo -e "${GREEN}✓ Service $service_name started successfully${NC}"
            return 0
        fi
        
        echo -e "${RED}✗ Failed to start service $service_name, retrying...${NC}"
        docker compose down
        sleep 5
        retry=$((retry + 1))
    done
    
    echo -e "${RED}✗ Failed to start service $service_name after $max_retries attempts${NC}"
    return 1
}

# Main script
section "Starting Vera project"

# Ensure we're in the project directory
cd "$(dirname "$0")/.."

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}✗ .env file not found! Copying from .env.example...${NC}"
    cp .env.example .env
fi

# Start services in order
critical_services=("postgres" "redis" "app")

for service in "${critical_services[@]}"; do
    if ! start_service "$service"; then
        echo -e "${RED}✗ Failed to start service $service${NC}"
        exit 1
    fi

done

# Wait for services to be ready
section "Waiting for services to be ready..."

for service in "${critical_services[@]}"; do
    if ! check_service "$service"; then
        echo -e "${RED}✗ Service $service is not ready${NC}"
        exit 1
    fi
done

# Run health checks
section "Running health checks..."

# Check PostgreSQL
if ! docker compose exec -T postgres pg_isready -U postgres; then
    echo -e "${RED}✗ PostgreSQL health check failed${NC}"
    exit 1
fi

# Check Redis
if ! docker compose exec -T redis redis-cli ping; then
    echo -e "${RED}✗ Redis health check failed${NC}"
    exit 1
fi

# Check App
if ! curl -s "http://localhost:8000/health" >/dev/null; then
    echo -e "${RED}✗ App health check failed${NC}"
    exit 1
fi

# Start auto-recovery service
section "Starting auto-recovery service..."
python3 scripts/auto_recovery.py &

# All checks passed
echo -e "\n${GREEN}✓ All services started and healthy!${NC}"
echo -e "${GREEN}✓ Auto-recovery service is running in background${NC}"
