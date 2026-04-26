# Realtime: UFW Notification System Setup Guide

**Realtime** is a lightweight, background-running daemon that monitors your Linux Uncomplicated Firewall (UFW) logs in real-time. It actively watches for unauthorized connection attempts and instantly alerts you via your preferred channels—preventing alert fatigue with built-in rate limiting and providing actionable context via IP geolocation.

---

## 🚀 Features
- **Real-Time Log Tailing**: Non-blocking log monitor for `/var/log/ufw.log`.
- **Intelligent Rate Limiting**: Avoids alert fatigue by preventing duplicate notifications from the same IP within a configured timeframe.
- **Data Enrichment**: Automatically geolocates the source IP to identify the origin of the block.
- **Multiple Notification Channels**:
  - Desktop alerts using `notify-send`.
  - Webhooks (Slack, Discord, ntfy.sh).
  - Email alerts via SMTP.
- **Set and Forget**: Runs reliably in the background as a `systemd` service with automatic failure recovery.

---

## 🛠 Prerequisites
- **OS**: Linux distribution with `systemd`.
- **Firewall**: UFW (Uncomplicated Firewall) installed and active.
- **Python**: Python 3.6+
- **Privileges**: `root` or `sudo` access for installation and reading log files.

---

## 📦 Installation

1. **Clone the Repository**
   Download the project to your local machine:
   ```bash
   git clone https://github.com/yourusername/Realtime.git
   cd Realtime
   ```

2. **Make the Installer Executable**
   ```bash
   chmod +x install.sh
   ```

3. **Run the Installation Script**
   Execute the installer as root. This script copies files to `/opt/ufw-notifier`, installs necessary dependencies (`python3-requests`, `libnotify-bin`), elevates UFW logging to `medium` so blocks are properly logged, and sets up the systemd service.
   ```bash
   sudo ./install.sh
   ```

---

## ⚙️ Configuration

All settings are managed via the `/opt/ufw-notifier/config.json` file. You can modify this file to tailor the alerts to your needs.

### Rate Limiting
To prevent a flood of notifications when a botnet scans your server, Realtime limits the alerts per IP.
- `rate_limit_seconds`: The time window (in seconds) during which a single IP is allowed only one alert (default: `60`).
- `max_attempts_per_limit`: The maximum allowed hits before rate-limiting applies (default: `50`).

### Notification Channels

#### 1. Desktop Notifications
Displays native pop-ups on your Linux desktop.
```json
"desktop": {
    "enabled": true
}
```

#### 2. Webhooks (Slack, Discord, ntfy.sh)
Pushes a JSON payload to a specified webhook URL.
```json
"webhook": {
    "enabled": true,
    "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "type": "slack" // Use "slack" for Slack/Discord, or "ntfy" for ntfy.sh
}
```

#### 3. Email Alerts
Sends an email for blocked connections via an SMTP server (e.g., Gmail, SendGrid, or your own mail server).
```json
"email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your_email@gmail.com",
    "password": "your_app_password",
    "to_address": "admin@yourdomain.com"
}
```

**Note**: After modifying the `config.json` file, you must restart the daemon to apply changes:
```bash
sudo systemctl restart ufw-notifier.service
```

---

## 🖥 Usage & Service Management

Realtime runs automatically in the background via `systemd`. Here are the essential commands to manage the service:

- **Check Status**: See if the daemon is running and view recent output logs.
  ```bash
  systemctl status ufw-notifier.service
  ```
- **Restart the Service**: Apply configuration changes or reboot the daemon.
  ```bash
  sudo systemctl restart ufw-notifier.service
  ```
- **Stop the Service**: Halt all monitoring and alerts.
  ```bash
  sudo systemctl stop ufw-notifier.service
  ```
- **View Daemon Logs**: Look at the raw output of the python script.
  ```bash
  journalctl -u ufw-notifier.service -f
  ```

---

## 🔧 Potential Tweaks & Customizations

1. **Changing the Log Target**
   If your UFW logs are stored somewhere other than `/var/log/ufw.log` (e.g., in `syslog` or `messages`), update the `log_file` parameter in `config.json` to point to the correct path.

2. **Adjusting Alert Verbiage**
   You can customize the alert text by editing `/opt/ufw-notifier/ufw_watcher.py`. Search for `message = f"UFW Alert: Blocked connection from...` in the `send_webhook_notification` or `send_email_notification` functions to change what data is presented.

3. **Restricting Monitoring to Specific Ports**
   If you only want alerts for specific ports (e.g., SSH port 22), you can modify the `handle_alert` function in `ufw_watcher.py`:
   ```python
   def handle_alert(ip, port, proto):
       if port != "22":
           return # Ignore non-SSH blocks
       # ... rest of function ...
   ```

4. **Hardening Permissions**
   For maximum security, you can create a dedicated `ufw-notifier` system user, give it read-only access to `/var/log/ufw.log`, and change the `User=root` line in `/etc/systemd/system/ufw-notifier.service` to `User=ufw-notifier`.

---

## 🐛 Troubleshooting

- **No Alerts Firing?**
  1. Ensure UFW logging is enabled: `sudo ufw logging medium`.
  2. Verify that `/var/log/ufw.log` exists and contains `[UFW BLOCK]` entries.
  3. Check the daemon logs for errors: `journalctl -u ufw-notifier.service -n 50`.
- **Desktop Notifications Not Showing?**
  Systemd services run as root in the background and may not have access to your desktop user's D-Bus session. If you rely heavily on desktop notifications, consider running the script as your local user or utilizing Webhooks/ntfy.sh for mobile pushes instead.
