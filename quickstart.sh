#!/bin/bash
# Quick Start Script for Autonomous Orchestrator
# Usage: ./quickstart.sh [install|run|test|stop]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Banner
show_banner() {
    clear
    echo -e "${PURPLE}"
    echo "    █████╗ ███████╗████████╗██╗  ██╗███████╗██████╗ "
    echo "   ██╔══██╗██╔════╝╚══██╔══╝██║  ██║██╔════╝██╔══██╗"
    echo "   ███████║█████╗     ██║   ███████║█████╗  ██████╔╝"
    echo "   ██╔══██║██╔══╝     ██║   ██╔══██║██╔══╝  ██╔══██╗"
    echo "   ██║  ██║███████╗   ██║   ██║  ██║███████╗██║  ██║"
    echo "   ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝"
    echo -e "${NC}"
    echo -e "${CYAN}   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}              AUTONOMOUS ORCHESTRATOR v7.0 - QUICK START${NC}"
    echo -e "${CYAN}   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Check dependencies
check_dependencies() {
    echo -e "${BLUE}🔍 Checking dependencies...${NC}"
    
    local missing=()
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        missing+=("Python 3.11+")
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        missing+=("pip")
    fi
    
    # Check git
    if ! command -v git &> /dev/null; then
        missing+=("git")
    fi
    
    if [ ${#missing[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ All dependencies found${NC}"
        return 0
    else
        echo -e "${RED}❌ Missing dependencies: ${missing[*]}${NC}"
        return 1
    fi
}

# Install
install() {
    show_banner
    echo -e "${BLUE}📦 Installing Autonomous Orchestrator...${NC}"
    echo ""
    
    # Check dependencies
    if ! check_dependencies; then
        echo -e "${YELLOW}⚠️  Please install missing dependencies first.${NC}"
        exit 1
    fi
    
    # Clone aether-grid if not exists
    if [ ! -d "../aether-grid" ]; then
        echo -e "${BLUE}📥 Cloning aether-grid repository...${NC}"
        git clone https://github.com/onegayunicorn/aether-grid.git ../aether-grid
    fi
    
    # Create virtual environment
    echo -e "${BLUE}🐍 Creating virtual environment...${NC}"
    python3 -m venv venv
    
    # Activate and install
    echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Generate sovereign key
    echo -e "${BLUE}🔐 Generating sovereign key...${NC}"
    SOVEREIGN_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "SOVEREIGN_KEY=$SOVEREIGN_KEY" > .env
    echo "✅ Sovereign key saved to .env"
    
    # Copy config
    if [ ! -f "config.yaml" ]; then
        echo -e "${BLUE}⚙️  Copying example config...${NC}"
        cp config.example.yaml config.yaml
    fi
    
    echo ""
    echo -e "${GREEN}✅ Installation complete!${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "  ${CYAN}source venv/bin/activate${NC}  # Activate virtual environment"
    echo -e "  ${CYAN}python3 orchestrator.py${NC}     # Start orchestrator"
    echo ""
}

# Run
run() {
    show_banner
    echo -e "${BLUE}🚀 Starting Autonomous Orchestrator...${NC}"
    echo ""
    
    # Check if venv exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Check for .env file
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}⚠️  No .env file found. Generating sovereign key...${NC}"
        SOVEREIGN_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        echo "SOVEREIGN_KEY=$SOVEREIGN_KEY" > .env
    fi
    
    # Start orchestrator
    echo -e "${GREEN}Starting orchestrator...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""
    
    python3 orchestrator.py
}

# Test
test() {
    show_banner
    echo -e "${BLUE}🧪 Running tests...${NC}"
    echo ""
    
    # Check if venv exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Install test dependencies
    pip install -r requirements.txt pytest pytest-asyncio httpx
    
    # Run tests
    pytest tests/ -v
}

# Stop
stop() {
    show_banner
    echo -e "${BLUE}🛑 Stopping Autonomous Orchestrator...${NC}"
    echo ""
    
    # Find and kill orchestrator processes
    pids=$(ps aux | grep "python3 orchestrator.py" | grep -v grep | awk '{print $2}')
    if [ -z "$pids" ]; then
        echo -e "${YELLOW}⚠️  No orchestrator processes found${NC}"
    else
        for pid in $pids; do
            echo -e "${RED}🔴 Killing process $pid${NC}"
            kill $pid
        done
        echo -e "${GREEN}✅ Orchestrator stopped${NC}"
    fi
    
    # Also kill any bridge or service processes
    pids=$(ps aux | grep -E "(orchestrator_bridge|auth_service)" | grep -v grep | awk '{print $2}')
    if [ -z "$pids" ]; then
        echo -e "${YELLOW}⚠️  No service processes found${NC}"
    else
        for pid in $pids; do
            echo -e "${RED}🔴 Killing service process $pid${NC}"
            kill $pid
        done
        echo -e "${GREEN}✅ All services stopped${NC}"
    fi
}

# Main
case "${1:-help}" in
    install)
        install
        ;;
    run)
        run
        ;;
    test)
        test
        ;;
    stop)
        stop
        ;;
    *)
        show_banner
        echo -e "${YELLOW}Usage:${NC} ./quickstart.sh [install|run|test|stop]"
        echo ""
        echo -e "${YELLOW}Commands:${NC}"
        echo -e "  ${CYAN}install${NC}  - Install dependencies and setup"
        echo -e "  ${CYAN}run${NC}     - Start the orchestrator"
        echo -e "  ${CYAN}test${NC}    - Run test suite"
        echo -e "  ${CYAN}stop${NC}    - Stop all processes"
        echo ""
        ;;
esac
