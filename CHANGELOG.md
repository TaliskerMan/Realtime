# Changelog — UFW Realtime Notifier

All notable changes to the UFW Realtime Notifier project are documented in this file. This project adheres to Semantic Versioning.

---

## [1.1.0] - 2026-06-23

### Fixed
- **Log rotation is now handled.** The tailer detects inode change/truncation
  and reopens the file (tail -F), so monitoring no longer silently stops after
  `logrotate` runs (P0-1).
- **UFW line parsing corrected.** Fields are now extracted independently;
  the previous single ordered regex assumed `DPT` before `PROTO` and would
  fail to match genuine UFW lines (which emit `PROTO` before `DPT`).
- **Desktop notifications no longer fail silently.** Disabled by default for the
  system service (which cannot reach a user session bus); the notifier now
  detects the missing session bus and logs guidance instead (P0-2).
- **`max_attempts_per_limit` is now implemented** as a per-IP sliding-window
  burst limiter instead of being a dead config key (P1-5).
- **Bounded memory.** Per-IP alert state is swept once its window elapses, so a
  scan from thousands of unique IPs no longer grows memory without bound (P1-4).

### Security
- **Runs unprivileged.** The service now runs as a dedicated `ufw-notifier`
  user in `adm` (not root), with a hardened systemd sandbox (P1-6).
- **Config secrets locked down.** The installer installs `config.json` as
  `root:ufw-notifier` mode `640` instead of world-readable (P0-3).
- **Geolocation over HTTPS, cached, and optional** — keeps lookups under the
  free-tier rate ceiling and can be disabled for offline/privacy use (P1-7).

### Added
- `uninstall.sh` that reverts `ufw logging`, disables the service, and removes
  the service user (P2-8).
- Unit tests for the UFW parser and the rate limiter; structured `logging`
  output with levels (P2-9).

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
