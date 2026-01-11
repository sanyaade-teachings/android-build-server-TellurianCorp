#!/usr/bin/env bash
set -euo pipefail

echo "Android Build Server - Systemd Service Installer"
echo "=================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="android-build"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# Prompt for user to run the service
prompt() {
    local var_name=$1
    local prompt_text=$2
    local default_value=${3:-}
    local input=""

    if [ -t 0 ]; then
        read -r -p "$prompt_text" input
    elif [ -t 1 ] && [ -r /dev/tty ]; then
        read -r -p "$prompt_text" input < /dev/tty
    fi

    if [ -z "$input" ] && [ -n "${default_value}" ]; then
        input="${default_value}"
    fi

    printf -v "$var_name" '%s' "$input"
}

# Detect current user if not root
CURRENT_USER=${SUDO_USER:-$USER}
if [ "$CURRENT_USER" = "root" ]; then
    CURRENT_USER="www-data"
fi

prompt SERVICE_USER "Service user [${CURRENT_USER}]: " "${CURRENT_USER}"
SERVICE_USER=${SERVICE_USER:-${CURRENT_USER}}

# Verify user exists
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "Error: User '$SERVICE_USER' does not exist"
    exit 1
fi

# Get user's primary group
SERVICE_GROUP=$(id -gn "$SERVICE_USER")

# Verify Python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3."
    exit 1
fi

PYTHON_PATH=$(command -v python3)

# Verify server.py exists
if [ ! -f "${SCRIPT_DIR}/server.py" ]; then
    echo "Error: server.py not found in ${SCRIPT_DIR}"
    exit 1
fi

# Check if service already exists
if [ -f "$SERVICE_FILE" ]; then
    echo "Warning: Service file already exists at $SERVICE_FILE"
    prompt OVERWRITE "Overwrite existing service? [y/N]: " "N"
    if [[ ! "${OVERWRITE:-}" =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    # Stop and disable existing service
    systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
    systemctl disable "${SERVICE_NAME}" 2>/dev/null || true
fi

# Create service file
echo "Creating systemd service file..."

# Escape special characters in paths for sed
ESCAPED_SCRIPT_DIR=$(printf '%s\n' "$SCRIPT_DIR" | sed 's/[[\.*^$()+?{|]/\\&/g')
ESCAPED_PYTHON_PATH=$(printf '%s\n' "$PYTHON_PATH" | sed 's/[[\.*^$()+?{|]/\\&/g')

# Create service file from template
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Android Build Server
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${SCRIPT_DIR}
ExecStart=${PYTHON_PATH} ${SCRIPT_DIR}/server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment variables
Environment="PYTHONUNBUFFERED=1"

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Set proper permissions
chmod 644 "$SERVICE_FILE"

# Set ownership of the service directory
echo "Setting ownership of ${SCRIPT_DIR} to ${SERVICE_USER}:${SERVICE_GROUP}..."
chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${SCRIPT_DIR}"

# Ensure required directories exist and are writable
echo "Creating required directories..."
mkdir -p "${SCRIPT_DIR}/artifacts" "${SCRIPT_DIR}/logs" "${SCRIPT_DIR}/status"
chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${SCRIPT_DIR}/artifacts" "${SCRIPT_DIR}/logs" "${SCRIPT_DIR}/status"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service
echo "Enabling ${SERVICE_NAME} service..."
systemctl enable "${SERVICE_NAME}"

# Ask if user wants to start the service
prompt START_SERVICE "Start the service now? [Y/n]: " "Y"
if [[ "${START_SERVICE:-Y}" =~ ^[Yy]$ ]] || [ -z "${START_SERVICE:-}" ]; then
    echo "Starting ${SERVICE_NAME} service..."
    systemctl start "${SERVICE_NAME}"
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        echo "✓ Service started successfully!"
    else
        echo "⚠ Service may have failed to start. Check status with: systemctl status ${SERVICE_NAME}"
    fi
fi

echo ""
echo "Installation complete!"
echo ""
echo "Service management commands:"
echo "  Start:   sudo systemctl start ${SERVICE_NAME}"
echo "  Stop:    sudo systemctl stop ${SERVICE_NAME}"
echo "  Restart: sudo systemctl restart ${SERVICE_NAME}"
echo "  Status:  sudo systemctl status ${SERVICE_NAME}"
echo "  Logs:    sudo journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "Service file location: ${SERVICE_FILE}"
