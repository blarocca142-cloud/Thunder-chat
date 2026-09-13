#!/usr/bin/env bash
# Temporarily re-allows outbound internet for the ollama service account so
# you can `ollama pull` a new model. Run lock.sh again right after you're done.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo bash unlock.sh"
  exit 1
fi

OLLAMA_UID="$(id -u ollama)"

iptables -D OUTPUT -m owner --uid-owner "$OLLAMA_UID" -j REJECT 2>/dev/null || true

netfilter-persistent save >/dev/null 2>&1 || iptables-save > /etc/iptables/rules.v4 2>/dev/null || true

echo "Unlocked. ollama can reach the internet again - pull what you need, then run:"
echo "  sudo bash lock.sh"
