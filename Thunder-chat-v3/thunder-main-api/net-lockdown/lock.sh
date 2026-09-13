#!/usr/bin/env bash
# Blocks internet access for the ollama service account, but still allows
# the internal Thunder LAN (10.168.168.0/24) - Cache and other nodes call
# Main's Ollama directly, so this is not just loopback-only. Ollama needs
# zero internet access to do inference - only to pull a NEW model. Run
# unlock.sh before pulling a model, then lock.sh again after.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo bash lock.sh"
  exit 1
fi

OLLAMA_UID="$(id -u ollama)"
LAN="10.168.168.0/24"

# Remove any pre-existing rules from a prior run so this is safe to re-run.
iptables -D OUTPUT -m owner --uid-owner "$OLLAMA_UID" -o lo -j ACCEPT 2>/dev/null || true
iptables -D OUTPUT -m owner --uid-owner "$OLLAMA_UID" -d "$LAN" -j ACCEPT 2>/dev/null || true
iptables -D OUTPUT -m owner --uid-owner "$OLLAMA_UID" -j REJECT 2>/dev/null || true

# Allow loopback (the FastAPI app on this same box talks to Ollama over 127.0.0.1)...
iptables -A OUTPUT -m owner --uid-owner "$OLLAMA_UID" -o lo -j ACCEPT
# ...and the internal Thunder LAN (Cache, Engine, Serverus, Odris, the phone).
iptables -A OUTPUT -m owner --uid-owner "$OLLAMA_UID" -d "$LAN" -j ACCEPT
# Reject everything else - i.e. the actual internet - the ollama process tries to send out.
iptables -A OUTPUT -m owner --uid-owner "$OLLAMA_UID" -j REJECT

apt-get install -y iptables-persistent >/dev/null 2>&1 || true
netfilter-persistent save >/dev/null 2>&1 || iptables-save > /etc/iptables/rules.v4 2>/dev/null || true

echo "Locked. The ollama process (uid $OLLAMA_UID) can reach the Thunder LAN ($LAN) but nothing on the real internet."
echo "Verify with: sudo iptables -L OUTPUT -n -v | grep -A1 -B1 owner"
