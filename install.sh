#!/bin/bash
# UFW Notifier Installation Script
set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root" >&2
  exit 1
fi

echo "Installing UFW Notifier..."

INSTALL_DIR="/opt/ufw-notifier"
SERVICE_USER="ufw-notifier"

# Dedicated unprivileged service user (no shell, no home), in 'adm' so it can
# read /var/log/ufw.log (root:adm 0640). Created idempotently.
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  echo "Creating service user '$SERVICE_USER'..."
  useradd --system --no-create-home --shell /usr/sbin/nologin --groups adm "$SERVICE_USER"
else
  usermod -aG adm "$SERVICE_USER"
fi

mkdir -p "$INSTALL_DIR"
cp ufw_watcher.py "$INSTALL_DIR/"

# Only install config.json if absent, so an upgrade never overwrites the
# admin's secrets. Lock it down: it holds the SMTP password / webhook URL (P0-3).
if [ ! -f "$INSTALL_DIR/config.json" ]; then
  cp config.json "$INSTALL_DIR/config.json"
fi
chown root:"$SERVICE_USER" "$INSTALL_DIR/config.json"
chmod 640 "$INSTALL_DIR/config.json"   # readable by the service user, not world

echo "Installing dependencies..."
apt-get update
apt-get install -y python3-requests libnotify-bin

echo "Setting up systemd service..."
cp ufw-notifier.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable ufw-notifier.service
systemctl restart ufw-notifier.service

echo "Configuring UFW Logging..."
ufw logging medium

echo "Installation complete!"
echo "Check status with: systemctl status ufw-notifier.service"
