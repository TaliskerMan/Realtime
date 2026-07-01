#!/usr/bin/env python3
"""UFW Real-Time Notifier.

Tails the UFW log, extracts ``[UFW BLOCK]`` events, optionally geolocates the
source IP, and dispatches desktop/webhook/email alerts with per-IP rate
limiting. Designed to run unattended as a systemd service.
"""

import logging
import os
import re
import json
import subprocess
import time
from collections import deque
from email.message import EmailMessage
import smtplib

import requests

__version__ = "1.0.0"

CONFIG_PATH = os.environ.get(
    "UFW_NOTIFIER_CONFIG",
    os.path.join(os.path.dirname(__file__), "config.json"),
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("ufw-notifier")

# Fields are extracted independently because real UFW log lines emit them in
# the order SRC ... PROTO ... DPT (a single ordered regex that expects DPT
# before PROTO silently fails to match genuine input).
_SRC_RE = re.compile(r'SRC=([\d.]+)')
_DPT_RE = re.compile(r'DPT=(\d+)')
_PROTO_RE = re.compile(r'PROTO=([A-Z0-9]+)')


def parse_block_line(line):
    """Return (ip, port, proto) for a ``[UFW BLOCK]`` line, else None."""
    if "[UFW BLOCK]" not in line:
        return None
    src = _SRC_RE.search(line)
    dpt = _DPT_RE.search(line)
    proto = _PROTO_RE.search(line)
    if src and dpt and proto:
        return src.group(1), dpt.group(1), proto.group(1)
    return None


def load_config(path=CONFIG_PATH):
    """Load JSON config; return {} on failure (logged)."""
    resolved = os.path.realpath(os.path.join(CONFIG_DIR, path))
    if not resolved.startswith(CONFIG_DIR + os.sep):
        logger.error("Rejected config path outside allowed dir: %s", path)
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error("Error loading config %s: %s", path, e)
        return {}


class RateLimiter:
    """Per-IP sliding-window burst limiter.

    Allows up to ``max_attempts`` alerts per IP within each ``window`` seconds;
    further alerts for that IP inside the window are suppressed. Entries age out
    of memory once their window elapses, so memory stays bounded to the set of
    IPs seen within the last ``window`` seconds (P1-4).
    """

    def __init__(self, window_seconds, max_attempts):
        self.window = max(1, int(window_seconds))
        self.max_attempts = max(1, int(max_attempts))
        self._hits = {}  # ip -> deque[timestamps]
        self._last_sweep = 0.0

    def allow(self, ip, now=None):
        """Return True if an alert for *ip* is permitted at time *now*."""
        now = time.time() if now is None else now
        # Sweep first so it never deletes the entry we are about to populate.
        self._maybe_sweep(now)

        cutoff = now - self.window
        dq = self._hits.get(ip)
        if dq is None:
            dq = deque()
            self._hits[ip] = dq
        while dq and dq[0] <= cutoff:
            dq.popleft()

        if len(dq) >= self.max_attempts:
            return False
        dq.append(now)
        return True

    def _maybe_sweep(self, now):
        """Periodically drop IPs whose windows have fully expired."""
        if now - self._last_sweep < self.window:
            return
        self._last_sweep = now
        cutoff = now - self.window
        for ip in list(self._hits.keys()):
            dq = self._hits[ip]
            while dq and dq[0] <= cutoff:
                dq.popleft()
            if not dq:
                del self._hits[ip]

    def __len__(self):
        return len(self._hits)


class GeoCache:
    """Per-IP geolocation lookups over HTTPS with a TTL cache.

    Caching means a scan from one IP costs at most one lookup per TTL, keeping
    well under ip-api's free-tier rate ceiling. Enrichment can be disabled
    entirely for offline/privacy-sensitive deployments.
    """

    def __init__(self, enabled=True, ttl_seconds=3600):
        self.enabled = enabled
        self.ttl = ttl_seconds
        self._cache = {}  # ip -> (timestamp, country)

    def country_for(self, ip, now=None):
        if not self.enabled:
            return "Unknown"
        now = time.time() if now is None else now
        cached = self._cache.get(ip)
        if cached and (now - cached[0]) < self.ttl:
            return cached[1]
        country = self._lookup(ip)
        self._cache[ip] = (now, country)
        return country

    @staticmethod
    def _lookup(ip):
        try:
            res = requests.get(
                f"https://ip-api.com/json/{ip}?fields=status,country",
                timeout=3,
            )
            data = res.json()
            if data.get("status") == "success":
                return data.get("country", "Unknown")
        except requests.RequestException as e:
            logger.debug("Geolocation lookup failed for %s: %s", ip, e)
        return "Unknown"


def send_desktop_notification(ip, country, port):
    """Best-effort desktop notification.

    Desktop alerts only work when the daemon runs inside a user graphical
    session (e.g. a ``systemctl --user`` unit) where DBUS_SESSION_BUS_ADDRESS /
    XDG_RUNTIME_DIR are set. A root/system service cannot reach a user's session
    bus, so we detect that and log instead of failing silently (P0-2).
    """
    if not (os.environ.get("DBUS_SESSION_BUS_ADDRESS") or os.environ.get("XDG_RUNTIME_DIR")):
        logger.warning(
            "Desktop notification skipped: no session bus (run as a --user "
            "service for desktop alerts, or use webhook/email)."
        )
        return
    try:
        subprocess.run(
            ["notify-send", "UFW Alert",
             f"Blocked connection from {ip} ({country}) on port {port}"],
            check=False,
        )
    except FileNotFoundError:
        logger.warning("notify-send not found; install libnotify-bin for desktop alerts")
    except Exception as e:
        logger.error("Desktop notification failed: %s", e)


def send_webhook_notification(config, ip, country, port):
    webhook_config = config.get("notifications", {}).get("webhook", {})
    if not webhook_config.get("enabled") or not webhook_config.get("url"):
        return
    url = webhook_config["url"]
    message = f"UFW Alert: Blocked connection from {ip} ({country}) on port {port}"
    try:
        if webhook_config.get("type") == "slack":
            requests.post(url, json={"text": message}, timeout=5)
        elif webhook_config.get("type") == "ntfy":
            requests.post(url, data=message.encode('utf-8'), timeout=5)
    except requests.RequestException as e:
        logger.error("Webhook notification failed: %s", e)


def send_email_notification(config, ip, country, port):
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
        logger.error("Email notification failed: %s", e)


def handle_alert(config, limiter, geo, ip, port, proto):
    if not limiter.allow(ip):
        return  # Rate limited / burst exceeded.

    country = geo.country_for(ip)
    logger.info("ALERT: Blocked %s (%s) on %s/%s", ip, country, port, proto)

    notifications = config.get("notifications", {})
    if notifications.get("desktop", {}).get("enabled"):
        send_desktop_notification(ip, country, port)
    if notifications.get("webhook", {}).get("enabled"):
        send_webhook_notification(config, ip, country, port)
    if notifications.get("email", {}).get("enabled"):
        send_email_notification(config, ip, country, port)


def _process_line(line, config, limiter, geo):
    parsed = parse_block_line(line)
    if parsed:
        ip, port, proto = parsed
        handle_alert(config, limiter, geo, ip, port, proto)


def tail_log(config, limiter, geo):
    """Follow the UFW log with rotation/truncation handling (tail -F).

    Reopens the file when the inode changes (logrotate moved/created a new file)
    or when the file shrinks below our current offset (truncation), so the
    daemon keeps alerting after a rotation instead of silently going dark (P0-1).
    """
    log_file = config.get("log_file", "/var/log/ufw.log")
    while not os.path.exists(log_file):
        logger.info("Log file %s does not exist. Waiting...", log_file)
        time.sleep(5)

    f = open(log_file, "r")
    f.seek(0, os.SEEK_END)
    cur_ino = os.fstat(f.fileno()).st_ino

    try:
        while True:
            line = f.readline()
            if line:
                _process_line(line, config, limiter, geo)
                continue

            # No new data: check for rotation/truncation before sleeping.
            time.sleep(0.5)
            try:
                st = os.stat(log_file)
            except FileNotFoundError:
                continue  # Rotated away; wait for the replacement to appear.

            rotated = st.st_ino != cur_ino
            truncated = st.st_size < f.tell()
            if rotated or truncated:
                logger.info(
                    "Log %s %s; reopening.",
                    log_file,
                    "rotated" if rotated else "truncated",
                )
                f.close()
                f = open(log_file, "r")
                cur_ino = os.fstat(f.fileno()).st_ino
                # Read the new file from the start so no early lines are missed.
    finally:
        f.close()


def main():
    config = load_config()
    limiter = RateLimiter(
        window_seconds=config.get("rate_limit_seconds", 60),
        max_attempts=config.get("max_attempts_per_limit", 1),
    )
    geo_cfg = config.get("geolocation", {})
    geo = GeoCache(
        enabled=geo_cfg.get("enabled", True),
        ttl_seconds=geo_cfg.get("cache_ttl_seconds", 3600),
    )
    logger.info("Starting UFW Real-Time Notifier v%s...", __version__)
    tail_log(config, limiter, geo)


if __name__ == "__main__":
    main()
