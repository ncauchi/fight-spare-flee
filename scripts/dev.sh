#!/bin/bash
# dev.sh - Start all services for development

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
LOBBY_SERVICE_DIR="./backend"
GAME_SERVICE_DIR="./backend"
FRONTEND_DIR="./client"

LOBBY_PORT=5000
GAME_PORT=5001
FRONTEND_PORT=5173  # Vite default

# Store PIDs for cleanup
PIDS=()

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

# Trap Ctrl+C and other termination signals
trap cleanup SIGINT SIGTERM EXIT

# Function to prefix output lines
prefix_output() {
    local prefix=$1
    local color=$2
    while IFS= read -r line; do
        echo -e "${color}\033[1m[${prefix}]${NC} $line"
    done
}

# Function to start a service
start_service() {
    local name=$1
    local dir=$2
    local command=$3
    local color=$4
    local prefix=$5
    
    echo -e "${GREEN}Starting ${name}...${NC}"
    (
        cd "$dir"
        # Redirect both stdout and stderr through prefix function
        $command 2>&1 | prefix_output "$prefix" "$color"
    ) &
    PIDS+=($!)
    sleep 1
}

# Parse arguments
NUM_CLIENTS=1
if [ "$1" == "--clients" ] && [ -n "$2" ]; then
    NUM_CLIENTS=$2
fi

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  Starting Development Environment${NC}"
echo -e "${GREEN}================================${NC}\n"

# Start Lobby Service
start_service "Lobby Service" "$LOBBY_SERVICE_DIR" \
    "python room_manager.py" "$CYAN" "Lobby"
echo -e "${GREEN}✓ Lobby Service running on http://localhost:${LOBBY_PORT}${NC}\n"

# Start Game Service
start_service "Game Service" "$GAME_SERVICE_DIR" \
    "python game_manager.py" "$BLUE" "Game"
echo -e "${GREEN}✓ Game Service running on http://localhost:${GAME_PORT}${NC}\n"

# Start Frontend(s)
if [ $NUM_CLIENTS -eq 1 ]; then
    start_service "Frontend" "$FRONTEND_DIR" \
        "npm run dev" "$YELLOW" "Frontend"
    echo -e "${BLUE}✓ Frontend running on http://localhost:${FRONTEND_PORT}${NC}\n"
else
    echo -e "${BLUE}Starting ${NUM_CLIENTS} frontend clients...${NC}\n"
    for i in $(seq 1 $NUM_CLIENTS); do
        port=$((FRONTEND_PORT + i - 1))
        start_service "Frontend Client $i" "$FRONTEND_DIR" \
            "npm run dev -- --port $port --strictPort" "$YELLOW" "Client$i"
        echo -e "${GREEN}✓ Client $i: http://localhost:${port}${NC}"
        sleep 2  # Stagger starts to avoid port conflicts
    done
    echo ""
fi

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  All services started!${NC}"
echo -e "${GREEN}================================${NC}\n"

echo -e "${YELLOW}Services:${NC}"
echo -e "  Lobby:    http://localhost:${LOBBY_PORT}"
echo -e "  Game:     http://localhost:${GAME_PORT}"
if [ $NUM_CLIENTS -eq 1 ]; then
    echo -e "  Frontend: http://localhost:${FRONTEND_PORT}"
else
    for i in $(seq 1 $NUM_CLIENTS); do
        port=$((FRONTEND_PORT + i - 1))
        echo -e "  Client $i: http://localhost:${port}"
    done
fi

echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Wait for all background processes
wait