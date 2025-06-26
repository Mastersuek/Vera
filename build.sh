#!/bin/bash
set -euo pipefail

# Enable BuildKit
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print section headers
section() {
    echo -e "\n${BLUE}==>${NC} ${GREEN}$1${NC}"
}

# Build the application
section "Building application..."
docker build \
    --target production \
    -t vera-app:latest \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    --cache-from type=local,src=.docker-cache \
    --cache-to type=local,dest=.docker-cache-new,mode=max \
    .

# Move new cache to be used for next build
if [ -d ".docker-cache-new" ]; then
    section "Updating build cache..."
    rm -rf .docker-cache
    mv .docker-cache-new .docker-cache
fi

# Run tests in the container
section "Running tests..."
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test

# Scan for vulnerabilities
section "Scanning for vulnerabilities..."
if ! command -v docker scan &> /dev/null; then
    echo "Docker Scan not found. Install with: curl -fsSL https://raw.githubusercontent.com/docker/scan-cli-plugin/main/install_install.sh | sh"
else
    docker scan --accept-license --version
    docker scan --exclude-base --severity high --file Dockerfile vera-app:latest
fi

# Show image size
section "Build complete!"
docker images | grep vera-app

echo -e "\n${GREEN}✓ Build successful!${NC}"
echo "To start the application, run: docker compose up -d"
