#!/bin/bash
# Run script for Autonomous Orchestrator
# Usage: ./run.sh [start|stop|restart|status|logs]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if exists
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Activate venv if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Function to check if orchestrator is running
is_running() {
    pgrep -f "python3 orchestrator.py" > /dev/null 2>&1
    return $?
}

# Function to get PID
get_pid() {
    pgrep -f "python3 orchestrator.py" | head -n 1
}

# Start
start() {
    if is_running; then
        echo -e "${YELLOW}⚠️  Orchestrator is already running (PID: $(get_pid))${NC}"
        return 0
    fi
    
    echo -e "${BLUE}🚀 Starting Autonomous Orchestrator...${NC}"
    
    # Check for sovereign key
    if [ -z "$SOVEREIGN_KEY" ]; then
        echo -e "${YELLOW}⚠️  No SOVEREIGN_KEY found in .env. Generating...${NC}"
        SOVEREIGN_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        echo "SOVEREIGN_KEY=$SOVEREIGN_KEY" > .env
        echo -e "${GREEN}✅ Sovereign key generated and saved to .env${NC}"
    fi
    
    # Start in background
    nohup python3 orchestrator.py > orchestrator.log 2>&1 &
    
    # Wait for startup
    sleep 2
    
    if is_running; then
        PID=$(get_pid)
        echo -e "${GREEN}✅ Orchestrator started (PID: $PID)${NC}"
        echo -e "${YELLOW}📍 Access at: http://localhost:8081${NC}"
        echo -e "${YELLOW}📜 Logs: tail -f orchestrator.log${NC}"
    else
        echo -e "${RED}❌ Failed to start orchestrator${NC}"
        echo -e "${YELLOW}Check orchestrator.log for errors${NC}"
        return 1
    fi
}

# Stop
stop() {
    if ! is_running; then
        echo -e "${YELLOW}⚠️  Orchestrator is not running${NC}"
        return 0
    fi
    
    echo -e "${BLUE}🛑 Stopping Autonomous Orchestrator...${NC}"
    
    PID=$(get_pid)
    kill $PID
    
    # Wait for shutdown
    sleep 2
    
    if ! is_running; then
        echo -e "${GREEN}✅ Orchestrator stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  Orchestrator did not stop gracefully. Force killing...${NC}"
        kill -9 $PID
        sleep 1
        if ! is_running; then
            echo -e "${GREEN}✅ Orchestrator force stopped${NC}"
        else
            echo -e "${RED}❌ Failed to stop orchestrator${NC}"
            return 1
        fi
    fi
}

# Restart
restart() {
    echo -e "${BLUE}🔄 Restarting Autonomous Orchestrator...${NC}"
    stop
    sleep 1
    start
}

# Status
status() {
    if is_running; then
        PID=$(get_pid)
        UPTIME=$(ps -p $PID -o etimes=)
        echo -e "${GREEN}✅ Orchestrator is running${NC}"
        echo -e "   PID: $PID"
        echo -e "   Uptime: ${UPTIME}s"
        echo -e "   Logs: orchestrator.log"
    else
        echo -e "${RED}❌ Orchestrator is not running${NC}"
    fi
    
    # Check for log file
    if [ -f "orchestrator.log" ]; then
        SIZE=$(du -h orchestrator.log | cut -f1)
        echo -e "   Log size: $SIZE"
    fi
}

# Logs
logs() {
    if [ -f "orchestrator.log" ]; then
        echo -e "${BLUE}📜 Orchestrator Logs (Ctrl+C to exit):${NC}"
        echo "============================================"
        tail -f orchestrator.log
    else
        echo -e "${YELLOW}⚠️  No log file found. Start the orchestrator first.${NC}"
    fi
}

# Main
case "${1:-help}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        echo -e "${PURPLE}"
        echo "    █████╗ ███████╗████████╗██╗  ██╗"
        echo "   ██╔══██╗██╔════╝╚══██╔══╝██║  ██║"
        echo "   ███████║█████╗     ██║   ███████║"
        echo "   ██╔══██║██╔══╝     ██║   ██╔══██║"
        echo "   ██║  ██║███████╗   ██║   ██║  ██║"
        echo "   ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝"
        echo -e "${NC}"
        echo ""
        echo -e "${GREEN}Autonomous Orchestrator v7.0 - Run Script${NC}"
        echo ""
        echo -e "${YELLOW}Usage:${NC} ./run.sh [start|stop|restart|status|logs]"
        echo ""
        echo -e "${YELLOW}Commands:${NC}"
        echo -e "  ${CYAN}start${NC}   - Start the orchestrator"
        echo -e "  ${CYAN}stop${NC}    - Stop the orchestrator"
        echo -e "  ${CYAN}restart${NC} - Restart the orchestrator"
        echo -e "  ${CYAN}status${NC} - Check orchestrator status"
        echo -e "  ${CYAN}logs${NC}   - View orchestrator logs"
        echo ""
        ;;
esac
