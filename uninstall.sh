#!/bin/bash
# UFW Notifier Uninstaller — reverses everything install.sh did.
set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root" >&2
  exit 1
fi

INSTALL_DIR="/opt/ufw-notifier"
SERVICE_USER="ufw-notifier"

echo "Stopping and disabling service..."
systemctl stop ufw-notifier.service 2>/dev/null || true
systemctl disable ufw-notifier.service 2>/dev/null || true
rm -f /etc/systemd/system/ufw-notifier.service
systemctl daemon-reload

echo "Removing installed files..."
rm -rf "$INSTALL_DIR"

echo "Reverting UFW logging to default (low)..."
# install.sh set 'ufw logging medium'; restore the UFW default.
ufw logging low || true

if id -u "$SERVICE_USER" >/dev/null 2>&1; then
  echo "Removing service user '$SERVICE_USER'..."
  userdel "$SERVICE_USER" || true
fi

echo "Uninstall complete."
echo "Note: python3-requests and libnotify-bin were left installed; remove them"
echo "manually if they are not needed elsewhere."
