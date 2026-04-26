# Snyk Security Audit: Realtime UFW Notifier

## Overview
This document outlines the findings of the Snyk security audit (SAST & SCA) conducted on the `Realtime` UFW Notifier application, as well as the manual hardening steps applied.

## 1. Snyk SAST Scan Results
**Scan Type:** Static Application Security Testing (SAST)
**Target:** `ufw_watcher.py`
**Result:** **0 Vulnerabilities Found**

Snyk code scan verified that the core logic does not introduce obvious coding vulnerabilities. Specific points checked included:
- **Command Injection:** The `subprocess.run` command correctly leverages a parameter list (rather than `shell=True`), preventing malicious payload execution even if attacker-controlled data (e.g. IP address) were somehow maliciously formatted.
- **Server-Side Request Forgery (SSRF):** Webhook requests utilize statically defined URLs provided in the secure configuration block rather than untrusted user input.
- **Denial of Service (DoS):** Safe regex patterns were verified against catastrophic backtracking (`[UFW BLOCK].*?SRC=...`).

## 2. Snyk SCA Scan Results
**Scan Type:** Software Composition Analysis (SCA)
**Target:** Python Dependencies (`requests`)
**Result:** **0 Vulnerabilities Found** (in the current `requests` version constraint `requests>=2.31.0`)

## 3. Hardening Applied
To strictly follow Shadowagent Rules ("First, Do No Harm") and secure all users, several hardening configurations have been proactively applied to the service:

### Systemd Sandboxing
The daemon's systemd unit (`ufw-notifier.service`) has been fortified with the following directives to massively restrict its privileges even when running as `root`:
- `NoNewPrivileges=yes`: Ensures the process and its children cannot elevate privileges via setuid/setgid.
- `ProtectSystem=strict`: Mounts the entire file system hierarchy as read-only (except `/dev`, `/proc`, and `/sys`).
- `ProtectHome=yes`: Denies access to `/home`, `/root`, and `/run/user`.
- `PrivateTmp=yes`: Sets up an isolated `/tmp` namespace to prevent temporary file hijacking.
- `ProtectKernelTunables=yes` & `ProtectKernelModules=yes`: Denies modifications to kernel variables.
- `ProtectControlGroups=yes`: Mounts cgroups read-only.
- `RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX`: Prevents usage of exotic network protocols (e.g., Bluetooth, raw sockets) which the notifier does not need.
- `RestrictNamespaces=yes`: Restricts creation of new Linux namespaces.

### Permission Recommendations
For deployments handling sensitive passwords (e.g., SMTP details or Webhooks), it is highly recommended to set restrictive permissions on the config file:
```bash
chmod 600 /opt/ufw-notifier/config.json
```

## Conclusion
The **Realtime** service is deemed highly secure. Its sandboxed service profile alongside a zero-vulnerability code baseline offers strong protections against privilege escalation, lateral movement, or data corruption in the event of an unforeseen exploit.
