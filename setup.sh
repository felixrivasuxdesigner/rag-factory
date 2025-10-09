#!/bin/bash

# RAG Factory - One-Command Setup Script
# This script starts all services and prepares the system for first use

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              🏭 RAG Factory Setup                        ║
║                                                           ║
║   Production-ready RAG system in minutes                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Function to print status
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

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

print_success "Prerequisites check passed"

# Check if services are already running
if docker ps | grep -q "rag-factory\|ollama\|rag-worker"; then
    print_warning "Some RAG Factory services are already running"
    echo -e "${YELLOW}Do you want to restart them? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "Stopping existing services..."
        docker-compose -f docker/docker-compose.yml down
    else
        print_status "Continuing with existing services..."
    fi
fi

# Start Docker services
print_status "Starting Docker services (this may take a few minutes)..."
docker-compose -f docker/docker-compose.yml up -d

# Wait for services to be healthy
print_status "Waiting for services to be healthy..."

max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        health_response=$(curl -s http://localhost:8000/health)

        if echo "$health_response" | grep -q '"api":"healthy"' && \
           echo "$health_response" | grep -q '"database":"healthy"' && \
           echo "$health_response" | grep -q '"redis":"healthy"' && \
           echo "$health_response" | grep -q '"ollama":"healthy"'; then
            print_success "All services are healthy!"
            break
        fi
    fi

    retry_count=$((retry_count + 1))
    echo -n "."
    sleep 2
done

echo ""

if [ $retry_count -eq $max_retries ]; then
    print_error "Services did not become healthy in time"
    echo "Check logs with: docker-compose -f docker/docker-compose.yml logs"
    exit 1
fi

# Download Ollama models
print_status "Checking Ollama models..."

# Check if embedding model exists
if docker exec ollama ollama list 2>/dev/null | grep -q "mxbai-embed-large"; then
    print_success "Embedding model (mxbai-embed-large) already downloaded"
else
    print_status "Downloading embedding model (mxbai-embed-large, ~669MB)..."
    docker exec ollama ollama pull mxbai-embed-large
    print_success "Embedding model downloaded"
fi

# Check if LLM model exists
if docker exec ollama ollama list 2>/dev/null | grep -q "gemma3:1b-it-qat"; then
    print_success "LLM model (gemma3:1b-it-qat) already downloaded"
else
    print_status "Downloading LLM model (gemma3:1b-it-qat, ~1GB)..."
    docker exec ollama ollama pull gemma3:1b-it-qat
    print_success "LLM model downloaded"
fi

# Verify frontend is accessible
print_status "Verifying frontend accessibility..."
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    print_success "Frontend is accessible"
else
    print_warning "Frontend may take a few more seconds to start"
fi

# Print success message with access information
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}║              ✅ Setup Complete!                           ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}🌐 Access Points:${NC}"
echo "  • Dashboard:    http://localhost:3000"
echo "  • API:          http://localhost:8000"
echo "  • API Docs:     http://localhost:8000/docs"
echo ""

echo -e "${BLUE}📊 Service Status:${NC}"
docker-compose -f docker/docker-compose.yml ps
echo ""

echo -e "${BLUE}📚 Next Steps:${NC}"
echo "  1. Open the dashboard: http://localhost:3000"
echo "  2. Create your first RAG project"
echo "  3. Add a data source (try the pre-configured examples!)"
echo "  4. Run your first ingestion job"
echo ""

echo -e "${BLUE}📖 Documentation:${NC}"
echo "  • API Usage:    cat API_USAGE.md"
echo "  • Architecture: cat CLAUDE.md"
echo "  • Contributing: cat CONTRIBUTING.md"
echo ""

echo -e "${BLUE}🛠️  Useful Commands:${NC}"
echo "  • View logs:    docker-compose -f docker/docker-compose.yml logs -f"
echo "  • Stop all:     docker-compose -f docker/docker-compose.yml down"
echo "  • Restart:      docker-compose -f docker/docker-compose.yml restart"
echo ""

# Try to open browser (platform-specific)
echo -e "${YELLOW}Opening dashboard in your browser...${NC}"
if command -v open &> /dev/null; then
    # macOS
    open http://localhost:3000
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open http://localhost:3000
elif command -v start &> /dev/null; then
    # Windows (Git Bash)
    start http://localhost:3000
else
    echo -e "${YELLOW}Please open http://localhost:3000 in your browser${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Happy RAG building!${NC}"
echo ""
