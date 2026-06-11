# Changelog — UFW Realtime Notifier

All notable changes to the UFW Realtime Notifier project are documented in this file. This project adheres to Semantic Versioning.

---

## [1.0.0] - 2026-06-10

### Added
- **Real-Time Firewall Log Monitoring:** Implemented tail loop tracing `/var/log/ufw.log` for UFW block tags.
- **Log Enrichment & Geolocation:** Integrated IP geolocation lookup to identify source country origins via HTTP query.
- **Alert Fatigue Protection:** Added configurable IP-based notification cooldown rate-limiting.
- **Desktop Alerts:** Integrated pop-up notifications via `notify-send` / `libnotify-bin`.
- **Webhook Alerts:** Integrated HTTP POST integrations supporting Slack payloads and ntfy.sh messaging channels.
- **Email Alerts:** Integrated SMTP message dispatch using native Python `smtplib` and `email.message`.
- **Automated Installer script:** Created `install.sh` to configure options, move assets, setup `ufw-notifier.service` systemd unit, install apt packages, and elevate UFW logging levels.
