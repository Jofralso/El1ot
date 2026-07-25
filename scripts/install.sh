#!/usr/bin/env bash
# ELIOT Installation Script
# Detects hardware, configures system, initializes ELIOT
set -euo pipefail

ELIOT_DIR="${ELIOT_DIR:-/opt/eliot}"
ELIOT_USER="eliot"
VERSION="0.2.0"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()    { echo -e "${GREEN}[ELIOT]${NC} $*"; }
warn()   { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()  { echo -e "${RED}[ERROR]${NC} $*"; }
header() { echo -e "\n${CYAN}=== ELIOT $1 ===${NC}"; }

detect_hardware() {
    header "Hardware Detection"

    ARCH=$(uname -m)
    log "Architecture: $ARCH"

    if [ -f /proc/device-tree/model ]; then
        MODEL=$(cat /proc/device-tree/model)
        log "Device: $MODEL"
        if echo "$MODEL" | grep -qi "jetson"; then
            HARDWARE_TARGET="jetson-orin-nano"
            log "Detected: NVIDIA Jetson"
        elif echo "$MODEL" | grep -qi "raspberry"; then
            HARDWARE_TARGET="raspberry-pi"
            log "Detected: Raspberry Pi"
        else
            HARDWARE_TARGET="dev-machine"
        fi
    else
        HARDWARE_TARGET="dev-machine"
        log "Detected: Development machine"
    fi

    if command -v nvidia-smi &>/dev/null; then
        GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "N/A")
        log "GPU: $GPU_INFO"
        CUDA_AVAILABLE=true
    else
        CUDA_AVAILABLE=false
        log "GPU: Not detected"
    fi

    CPU_CORES=$(nproc)
    MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
    log "CPU: $CPU_CORES cores, Memory: ${MEM_GB}GB"
}

check_dependencies() {
    header "Checking Dependencies"

    MISSING=()

    command -v docker &>/dev/null || MISSING+=("docker")
    command -v docker-compose &>/dev/null || MISSING+=("docker-compose")
    command -v python3 &>/dev/null || MISSING+=("python3")
    command -v git &>/dev/null || MISSING+=("git")
    command -v curl &>/dev/null || MISSING+=("curl")

    if [ ${#MISSING[@]} -gt 0 ]; then
        error "Missing dependencies: ${MISSING[*]}"
        log "Installing missing dependencies..."

        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq
            sudo apt-get install -y -qq docker.io docker-compose python3 python3-pip git curl
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y docker docker-compose python3 python3-pip git curl
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm docker docker-compose python python-pip git curl
        fi
    fi

    log "All dependencies satisfied"
}

setup_directories() {
    header "Setting Up Directories"

    sudo mkdir -p "$ELIOT_DIR"
    sudo mkdir -p /etc/eliot
    sudo mkdir -p /var/log/eliot

    if ! id "$ELIOT_USER" &>/dev/null; then
        sudo useradd -m -s /bin/bash "$ELIOT_USER"
        log "Created user: $ELIOT_USER"
    fi

    sudo chown -R "$ELIOT_USER:$ELIOT_USER" "$ELIOT_DIR"
    log "Directories ready"
}

install_eliot() {
    header "Installing ELIOT v$VERSION"

    if [ -d "$ELIOT_DIR/.git" ]; then
        log "ELIOT already installed, updating..."
        cd "$ELIOT_DIR"
        sudo -u "$ELIOT_USER" git pull origin main
    else
        log "Cloning ELIOT repository..."
        sudo -u "$ELIOT_USER" git clone https://github.com/Jofralso/El1ot.git "$ELIOT_DIR"
    fi

    cd "$ELIOT_DIR"
    sudo -u "$ELIOT_USER" cp .env.example .env

    sudo -u "$ELIOT_USER" sed -i "s/HARDWARE_TARGET=.*/HARDWARE_TARGET=$HARDWARE_TARGET/" .env
    sudo -u "$ELIOT_USER" sed -i "s/CUDA_ENABLED=.*/CUDA_ENABLED=$CUDA_AVAILABLE/" .env
    sudo -u "$ELIOT_USER" sed -i "s/ELIOT_ENV=.*/ELIOT_ENV=production/" .env

    log "Configuration written"
}

build_containers() {
    header "Building Containers"

    cd "$ELIOT_DIR"

    if [ "$HARDWARE_TARGET" = "jetson-orin-nano" ] || [ "$HARDWARE_TARGET" = "jetson-orin" ]; then
        log "Building Jetson-optimized containers..."
        sudo -u "$ELIOT_USER" docker-compose -f docker-compose.prod.yml build
    else
        log "Building standard containers..."
        sudo -u "$ELIOT_USER" docker-compose build
    fi

    log "Containers built"
}

start_services() {
    header "Starting ELIOT Services"

    cd "$ELIOT_DIR"

    if [ "$HARDWARE_TARGET" = "jetson-orin-nano" ] || [ "$HARDWARE_TARGET" = "jetson-orin" ]; then
        sudo -u "$ELIOT_USER" docker-compose -f docker-compose.prod.yml up -d
    else
        sudo -u "$ELIOT_USER" docker-compose up -d
    fi

    log "Waiting for services..."
    sleep 10

    for i in {1..30}; do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            log "ELIOT is running!"
            return 0
        fi
        sleep 2
    done

    warn "Services started but health check pending"
}

setup_systemd() {
    header "Setting Up System Service"

    if [ -f "$ELIOT_DIR/deployment/eliot.service" ]; then
        sudo cp "$ELIOT_DIR/deployment/eliot.service" /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable eliot.service
        log "Systemd service installed and enabled"
    fi
}

print_summary() {
    header "Installation Complete"

    echo ""
    log "Version:     $VERSION"
    log "Directory:   $ELIOT_DIR"
    log "Hardware:    $HARDWARE_TARGET"
    log "CUDA:        $CUDA_AVAILABLE"
    echo ""
    log "Web UI:      http://localhost:8000/ui/"
    log "API:         http://localhost:8000/docs"
    log "Health:      http://localhost:8000/health"
    log "Grafana:     http://localhost:3000"
    echo ""
    log "Commands:"
    log "  cd $ELIOT_DIR && docker-compose ps"
    log "  cd $ELIOT_DIR && docker-compose logs -f"
    log "  sudo systemctl start eliot"
    echo ""
}

main() {
    header "v$VERSION Installer"
    detect_hardware
    check_dependencies
    setup_directories
    install_eliot
    build_containers
    start_services
    setup_systemd
    print_summary
}

main "$@"
