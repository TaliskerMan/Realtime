# Realtime: UFW Notification System

**Version 1.0.0** · see [CHANGELOG.md](CHANGELOG.md)

A robust, background-running system that monitors server firewall logs in real-time and alerts users of unauthorized external connection attempts via multiple notification channels.

## Features
- **Real-Time Log Tailing**: Non-blocking log monitor for `/var/log/ufw.log`.
- **Intelligent Rate Limiting**: Avoids alert fatigue by preventing duplicate notifications from the same IP within a configured timeframe.
- **Data Enrichment**: Automatically geolocates the source IP to identify the country of origin.
- **Multiple Notification Channels**: Support for Desktop popups, Webhooks (Slack/ntfy), and SMTP Emails.

---

## Prerequisites
Before installing Realtime, ensure your system meets the following requirements:
- **Operating System**: Linux distribution using `systemd` (e.g., Ubuntu, Debian, CentOS).
- **Firewall**: `ufw` (Uncomplicated Firewall) must be installed, enabled, and actively blocking traffic.
- **Python**: Python 3 must be installed.
- **Privileges**: Root (`sudo`) is required to **install** (create the service user, write the unit). The daemon itself runs as a dedicated unprivileged user (`ufw-notifier`) in the `adm` group — it does **not** run as root.

---

## Downloading and Installing

Follow these step-by-step instructions to get the service running:

### Step 1: Clone the Repository
Download the Realtime service to your local machine:
```bash
git clone https://github.com/TaliskerMan/Realtime.git
cd Realtime
```

### Step 2: Make the Installer Executable
Ensure the installation script has the necessary permissions to run:
```bash
chmod +x install.sh
```

### Step 3: Run the Installer
Run the installation script with root privileges. The script will automatically:
- Create the installation directory at `/opt/ufw-notifier`.
- Copy the necessary Python script and configuration file.
- Install required dependencies (`python3-requests` and `libnotify-bin`).
- Set up and enable the systemd daemon service.
- Set UFW logging to `medium` so that blocked connections are written to the logs.

```bash
sudo ./install.sh
```

---

## Configuration

The service is configured via a JSON file located at `/opt/ufw-notifier/config.json`. You can adjust monitoring rules and notification settings here.

### Core Settings
- `log_file`: The path to your UFW log (default: `/var/log/ufw.log`). The tailer is rotation-aware — it reopens the file after `logrotate` rotates or truncates it, so monitoring never silently stops.
- `rate_limit_seconds`: The sliding window (in seconds) over which alerts per IP are counted (default: `60`).
- `max_attempts_per_limit`: Maximum alerts per IP **within each window** before further alerts for that IP are suppressed (default: `5`). Set to `1` for one alert per window per IP.
- `geolocation`: `{ "enabled": true, "cache_ttl_seconds": 3600 }`. Lookups use **HTTPS** and are **cached per IP** (so a scan costs at most one lookup per TTL, staying under ip-api's free-tier ceiling). Set `enabled: false` for fully offline / privacy-sensitive operation — note that, when enabled, each blocked IP is sent to the third-party ip-api.com service.

### Notification Methods & Implementation

You can enable or disable specific notification channels by changing the `"enabled"` key to `true` or `false` in the configuration file.

#### 1. Desktop Notifications
Uses `notify-send` to display pop-up alerts. **Disabled by default**, because the
system service runs as an unprivileged daemon with no access to your graphical
session bus — a root/system service simply cannot deliver desktop pop-ups, and
defaulting it on would fail silently. Desktop alerts work only when Realtime runs
inside your user session, e.g. as a `systemctl --user` unit where
`DBUS_SESSION_BUS_ADDRESS`/`XDG_RUNTIME_DIR` are set. For headless servers, use
**webhook** or **email** instead.
```json
"desktop": {
    "enabled": false
}
```

#### 2. Webhook Notifications (Slack, Discord, ntfy.sh)
Sends a POST request to a specified URL. Great for team chat integrations or push notification apps like ntfy.
```json
"webhook": {
    "enabled": true,
    "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "type": "slack" // options: "slack", "ntfy"
}
```

#### 3. Email Alerts (SMTP)
Dispatches an email alert with the blocked connection details. Requires an active SMTP server or email provider.
```json
"email": {
    "enabled": true,
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "username": "alerts@example.com",
    "password": "your_password",
    "to_address": "admin@example.com"
}
```

> **Note**: Whenever you modify `/opt/ufw-notifier/config.json`, you must restart the service to apply changes:
> ```bash
> sudo systemctl restart ufw-notifier.service
> ```

---

## Managing the Service

Once installed, Realtime runs as a background `systemd` daemon. You can manage it using standard systemctl commands.

**Check the status and view recent logs:**
```bash
sudo systemctl status ufw-notifier.service
```

**Stop the service:**
```bash
sudo systemctl stop ufw-notifier.service
```

**Start the service:**
```bash
sudo systemctl start ufw-notifier.service
```

---

## Uninstalling

To completely remove Realtime and revert the system changes it made (including
restoring UFW logging to its default and removing the service user):
```bash
sudo ./uninstall.sh
```

---

## Security notes
- **Least privilege:** the daemon runs as the unprivileged `ufw-notifier` user
  (in `adm` for log read access), not root, with a hardened systemd sandbox
  (`NoNewPrivileges`, `ProtectSystem=strict`, `PrivateTmp`, a syscall filter,
  and an empty capability set).
- **Credentials:** `config.json` holds the SMTP password and webhook URL. The
  installer sets it `root:ufw-notifier` mode `640` (readable by the service,
  not world-readable). Keep it that way, and prefer a dedicated low-privilege
  mailbox/app password over a primary account password.
- **Privacy:** geolocation sends each blocked IP to ip-api.com over HTTPS when
  enabled. Disable it (`geolocation.enabled: false`) if you don't want that.

---

## Extending Realtime: Additional Warning Methods

Because Realtime is written in standard Python, it is highly extensible. If you want to add new notification channels, you can modify `/opt/ufw-notifier/ufw_watcher.py` and call your new function inside the `handle_alert()` function.

Here are examples of additional warning methods you can implement:

### Example 1: Telegram Bot Integration
You can easily send alerts to a Telegram chat using the Telegram Bot API.

**Add this function to `ufw_watcher.py`:**
```python
def send_telegram_notification(ip, country, port):
    bot_token = "YOUR_BOT_TOKEN"
    chat_id = "YOUR_CHAT_ID"
    message = f"UFW Alert: Blocked {ip} ({country}) on port {port}"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
    except requests.RequestException as e:
        logger.error("Telegram notification failed: %s", e)
```

### Example 2: Pushover Notification
Pushover is excellent for immediate mobile device push notifications.

**Add this function to `ufw_watcher.py`:**
```python
def send_pushover_notification(ip, country, port):
    user_key = "YOUR_USER_KEY"
    api_token = "YOUR_API_TOKEN"
    message = f"UFW Alert: Blocked {ip} ({country}) on port {port}"
    url = "https://api.pushover.net/1/messages.json"
    
    payload = {
        "token": api_token,
        "user": user_key,
        "message": message,
        "title": "UFW Alert"
    }
    
    try:
        requests.post(url, data=payload, timeout=5)
    except requests.RequestException as e:
        logger.error("Pushover notification failed: %s", e)
```

**Don't forget** to call your new functions inside the `handle_alert()` function,
after the `country` has been resolved:
```python
def handle_alert(config, limiter, geo, ip, port, proto):
    # ... existing code (rate-limit check, country = geo.country_for(ip)) ...

    # Call your custom extensions:
    send_telegram_notification(ip, country, port)
    send_pushover_notification(ip, country, port)
```
