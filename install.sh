#!/bin/bash

# UFW Notifier Installation Script

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

echo "Installing UFW Notifier..."

INSTALL_DIR="/opt/ufw-notifier"
mkdir -p "$INSTALL_DIR"

cp ufw_watcher.py "$INSTALL_DIR/"
cp config.json "$INSTALL_DIR/"

# Install dependencies if needed
echo "Installing dependencies..."
apt-get update
apt-get install -y python3-requests libnotify-bin

echo "Setting up systemd service..."
cp ufw-notifier.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable ufw-notifier.service
systemctl start ufw-notifier.service

echo "Configuring UFW Logging..."
ufw logging medium

echo "Installation complete!"
echo "Check status with: systemctl status ufw-notifier.service"
