# Realtime: UFW Notification System

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
- **Privileges**: Root (`sudo`) access is required for installation and reading system logs.

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
- `log_file`: The path to your UFW log (default: `/var/log/ufw.log`).
- `rate_limit_seconds`: The cooldown period (in seconds) before sending another alert for the same IP (default: `60`).
- `max_attempts_per_limit`: (Reserved for future rate-limit thresholding).

### Notification Methods & Implementation

You can enable or disable specific notification channels by changing the `"enabled"` key to `true` or `false` in the configuration file.

#### 1. Desktop Notifications
Uses `notify-send` to display pop-up alerts on your Linux desktop.
```json
"desktop": {
    "enabled": true
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
    except Exception as e:
        print(f"Telegram notification failed: {e}")
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
    except Exception as e:
        print(f"Pushover notification failed: {e}")
```

**Don't forget** to call your new functions inside the `handle_alert()` method:
```python
def handle_alert(ip, port, proto):
    # ... existing code ...
    
    # Call your custom extensions:
    send_telegram_notification(ip, country, port)
    send_pushover_notification(ip, country, port)
```
