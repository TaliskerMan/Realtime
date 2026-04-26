import os
import time
import re
import json
import subprocess
import requests
import smtplib
from email.message import EmailMessage

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

config = load_config()

UFW_REGEX = re.compile(r'\[UFW BLOCK\].*?SRC=([\d\.]+).*?DPT=(\d+).*?PROTO=([A-Z]+)')

# IP -> last notified timestamp
last_notified = {}

def get_geolocation(ip):
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}", timeout=3)
        data = res.json()
        if data.get("status") == "success":
            return f"{data.get('country', 'Unknown')}"
    except:
        pass
    return "Unknown"

def send_desktop_notification(ip, country, port):
    try:
        # Note: running notify-send from a systemd service might require setting DBUS_SESSION_BUS_ADDRESS or similar
        # For simplicity, we just call it.
        subprocess.run(["notify-send", "UFW Alert", f"Blocked connection from {ip} ({country}) on port {port}"], check=False)
    except Exception as e:
        print(f"Desktop notification failed: {e}")

def send_webhook_notification(ip, country, port):
    webhook_config = config.get("notifications", {}).get("webhook", {})
    if not webhook_config.get("enabled") or not webhook_config.get("url"):
        return
    
    url = webhook_config["url"]
    message = f"UFW Alert: Blocked connection from {ip} ({country}) on port {port}"
    
    try:
        if webhook_config.get("type") == "slack":
            payload = {"text": message}
            requests.post(url, json=payload, timeout=5)
        elif webhook_config.get("type") == "ntfy":
            requests.post(url, data=message.encode('utf-8'), timeout=5)
    except Exception as e:
        print(f"Webhook notification failed: {e}")

def send_email_notification(ip, country, port):
    email_config = config.get("notifications", {}).get("email", {})
    if not email_config.get("enabled"):
        return
    
    try:
        msg = EmailMessage()
        msg.set_content(f"UFW Alert: Blocked connection from {ip} ({country}) on port {port}")
        msg['Subject'] = f"UFW Alert: {ip}"
        msg['From'] = email_config.get("username")
        msg['To'] = email_config.get("to_address")
        
        with smtplib.SMTP(email_config.get("smtp_server"), email_config.get("smtp_port")) as server:
            server.starttls()
            server.login(email_config.get("username"), email_config.get("password"))
            server.send_message(msg)
    except Exception as e:
        print(f"Email notification failed: {e}")

def handle_alert(ip, port, proto):
    now = time.time()
    rate_limit = config.get("rate_limit_seconds", 60)
    
    if ip in last_notified:
        if now - last_notified[ip] < rate_limit:
            return # Rate limited
    
    last_notified[ip] = now
    
    country = get_geolocation(ip)
    print(f"ALERT: Blocked {ip} ({country}) on {port}/{proto}")
    
    notifications = config.get("notifications", {})
    if notifications.get("desktop", {}).get("enabled"):
        send_desktop_notification(ip, country, port)
    if notifications.get("webhook", {}).get("enabled"):
        send_webhook_notification(ip, country, port)
    if notifications.get("email", {}).get("enabled"):
        send_email_notification(ip, country, port)

def tail_log():
    log_file = config.get("log_file", "/var/log/ufw.log")
    if not os.path.exists(log_file):
        print(f"Log file {log_file} does not exist. Waiting...")
        while not os.path.exists(log_file):
            time.sleep(5)
            
    with open(log_file, "r") as f:
        # Go to the end of file
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
            
            if "[UFW BLOCK]" in line:
                match = UFW_REGEX.search(line)
                if match:
                    ip, port, proto = match.groups()
                    handle_alert(ip, port, proto)

if __name__ == "__main__":
    print("Starting UFW Real-Time Notifier...")
    tail_log()
