#!/usr/bin/env bash
# Locks a Thunder node's service account to LAN-only network access, same
# pattern as Main's ollama lockdown. Logs every blocked attempt to the
# kernel log (visible via `dmesg` / journalctl -k) so Odris can watch for
# real intrusion signals, not just silently drop them.
#
# Usage: sudo bash lock_node.sh <username>
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo bash lock_node.sh <username>"
  exit 1
fi

if [ -z "${1:-}" ]; then
  echo "Usage: sudo bash lock_node.sh <username>"
  exit 1
fi

TARGET_USER="$1"
TARGET_UID="$(id -u "$TARGET_USER")"
LAN="10.168.168.0/24"

# Clean up any prior run so this is safe to re-run.
iptables -D OUTPUT -m owner --uid-owner "$TARGET_UID" -o lo -j ACCEPT 2>/dev/null || true
iptables -D OUTPUT -m owner --uid-owner "$TARGET_UID" -d "$LAN" -j ACCEPT 2>/dev/null || true
iptables -D OUTPUT -m owner --uid-owner "$TARGET_UID" -j LOG --log-prefix "THUNDER-BLOCKED-EGRESS: " --log-level 4 2>/dev/null || true
iptables -D OUTPUT -m owner --uid-owner "$TARGET_UID" -j REJECT 2>/dev/null || true

iptables -A OUTPUT -m owner --uid-owner "$TARGET_UID" -o lo -j ACCEPT
iptables -A OUTPUT -m owner --uid-owner "$TARGET_UID" -d "$LAN" -j ACCEPT
# Log before rejecting - this is the visibility Blayne asked for.
iptables -A OUTPUT -m owner --uid-owner "$TARGET_UID" -j LOG --log-prefix "THUNDER-BLOCKED-EGRESS: " --log-level 4
iptables -A OUTPUT -m owner --uid-owner "$TARGET_UID" -j REJECT

apt-get install -y iptables-persistent >/dev/null 2>&1 || true
netfilter-persistent save >/dev/null 2>&1 || iptables-save > /etc/iptables/rules.v4 2>/dev/null || true

echo "Locked $TARGET_USER (uid $TARGET_UID): LAN-only, real internet blocked and logged."
echo "Verify: sudo iptables -L OUTPUT -n -v | grep -A2 -B2 $TARGET_UID"
