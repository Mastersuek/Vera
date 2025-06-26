#!/bin/bash
set -euo pipefail

# Enable colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print section headers
section() {
    echo -e "\n${BLUE}==>${NC} ${GREEN}$1${NC}"
}

# Check if .env.test exists, if not create from .env.example
if [ ! -f .env.test ] && [ -f .env.example ]; then
    section "Creating .env.test from .env.example"
    cp .env.example .env.test
    # Update test-specific settings
    sed -i 's/^ENV=.*/ENV=test/' .env.test
    sed -i 's/^DEBUG=.*/DEBUG=True/' .env.test
    sed -i 's/^POSTGRES_USER=.*/POSTGRES_USER=test/' .env.test
    sed -i 's/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=test/' .env.test
    sed -i 's/^POSTGRES_DB=.*/POSTGRES_DB=test/' .env.test
    sed -i 's/^REDIS_PASSWORD=.*/REDIS_PASSWORD=test/' .env.test
fi

# Ensure test database is ready
section "Starting test database..."
docker compose -f docker-compose.test.yml up -d test-db test-redis

# Wait for database to be ready
section "Waiting for test database to be ready..."
until docker compose -f docker-compose.test.yml exec -T test-db pg_isready -U test -d test; do
    sleep 1
done

# Run tests
section "Running tests..."
docker compose -f docker-compose.test.yml up \
    --build \
    --abort-on-container-exit \
    --exit-code-from test \
    test

# Stop test containers
section "Cleaning up..."
docker compose -f docker-compose.test.yml down -v

echo -e "\n${GREEN}✓ Tests completed!${NC}"
