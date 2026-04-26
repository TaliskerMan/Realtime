# Realtime: Local Setup & Testing Guide

This guide provides step-by-step instructions for installing, configuring, and safely testing the **Realtime** UFW notification system directly on your local Linux machine.

## Step 1: Install Dependencies & Setup
Since you've already cloned and created the repository, we can proceed straight to installation.

1. Ensure the installation script has executable permissions:
   ```bash
   chmod +x /home/freecode/antigrav/Realtime/install.sh
   ```
2. Run the installation script as root. This will copy the necessary files to `/opt/ufw-notifier`, set up UFW logging, install dependencies, and initialize the systemd service:
   ```bash
   sudo /home/freecode/antigrav/Realtime/install.sh
   ```

## Step 2: Configure Notifications
By default, desktop notifications are enabled in the code. To customize your alerts (e.g., adding Discord/Slack webhooks or adjusting rate limits), you'll need to edit the active configuration file located in `/opt/ufw-notifier`.

1. Open the configuration file:
   ```bash
   sudo nano /opt/ufw-notifier/config.json
   ```
2. Adjust your settings. For local testing, ensure the `desktop` notification block is enabled:
   ```json
   "desktop": {
       "enabled": true
   }
   ```
3. Secure the configuration file so unauthorized users cannot read your webhooks or email passwords:
   ```bash
   sudo chmod 600 /opt/ufw-notifier/config.json
   ```

## Step 3: Start and Verify the Service
After making any changes to `/opt/ufw-notifier/config.json`, you must restart the daemon.

1. Restart the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart ufw-notifier.service
   ```
2. Verify that it is running securely in the background:
   ```bash
   systemctl status ufw-notifier.service
   ```

## Step 4: How to Test the Notifier Safely
To verify the system is working, we can simulate a mock UFW block event manually so you don't have to wait for an actual attack.

### Option A: Simulate a Log Entry (Safest & Fastest)
Instead of blocking real traffic, you can inject a mock UFW block line directly into the system log file. 

1. Run the following command to simulate an unauthorized SSH (Port 22) connection attempt from a generic IP (e.g., Google's `8.8.8.8`):
   ```bash
   echo "[UFW BLOCK] IN=eth0 OUT= MAC=00:00:00:00:00:00:00:00:00:00:00:00:08:00 SRC=8.8.8.8 DST=192.168.1.100 LEN=40 TOS=0x00 PREC=0x00 TTL=245 ID=54321 PROTO=TCP SPT=43210 DPT=22 WINDOW=1024 RES=0x00 SYN URGP=0" | sudo tee -a /var/log/ufw.log
   ```
2. Within a fraction of a second, you should see your desktop notification pop up (and receive any configured webhook/email alerts)! Note that due to the rate limiter, sending this exact command multiple times within a minute will only trigger one notification.

### Option B: Trigger a Real Block
If you want to test the firewall itself, you can temporarily block another device on your network (like your smartphone) and attempt to connect to your machine.
1. Find your smartphone's local IP address (e.g., `192.168.1.50`).
2. Block it via UFW:
   ```bash
   sudo ufw deny from 192.168.1.50
   ```
3. Attempt to connect from your phone to your local machine (e.g., try visiting a local web server or SSH).
4. You should receive a notification natively.
5. **Important:** Remember to delete the rule afterward!
   ```bash
   sudo ufw delete deny from 192.168.1.50
   ```

## Monitoring Live Logs
If you ever need to debug the application, see what it's catching in real-time, or check if the rate-limiter is actively suppressing spam, you can tail the daemon's output:
```bash
journalctl -u ufw-notifier.service -f
```
