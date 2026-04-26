# Realtime: UFW Notification System

A robust, background-running system that monitors server firewall logs in real-time and alerts users of unauthorized external connection attempts via multiple notification channels.

## Features
- **Real-Time Log Tailing**: Non-blocking log monitor for `/var/log/ufw.log`.
- **Intelligent Rate Limiting**: Avoids alert fatigue by preventing duplicate notifications from the same IP within a configured timeframe.
- **Data Enrichment**: Automatically geolocates the source IP to identify the origin of the block.
- **Multiple Notification Channels**:
  - Desktop alerts using `notify-send`.
  - Webhooks (Slack, Discord, ntfy.sh).
  - Email alerts via SMTP.

## Architecture & Tech Stack
- **Log Generation**: UFW (iptables frontend) + rsyslog or journald
- **Core Engine**: Python 3
- **Service Management**: systemd
- **Enrichment**: IP-API for geolocation

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/Realtime.git
   cd Realtime
   ```

2. Make the installer executable:
   ```bash
   chmod +x install.sh
   ```

3. Run the installation script as root:
   ```bash
   sudo ./install.sh
   ```

## Configuration
Edit `/opt/ufw-notifier/config.json` to enable or disable specific notification channels and configure your credentials or webhooks. Then, restart the service:

```bash
sudo systemctl restart ufw-notifier.service
```

## Running & Managing
Check the status of the daemon:
```bash
systemctl status ufw-notifier.service
```

Stop the daemon:
```bash
sudo systemctl stop ufw-notifier.service
```
