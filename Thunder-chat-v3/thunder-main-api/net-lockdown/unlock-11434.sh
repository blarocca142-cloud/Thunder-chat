#!/usr/bin/env bash
# Undoes port-11434.sh: port 11434 goes back to being reachable by anything
# that can route to Main. The OUTPUT egress rules from lock.sh are untouched.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo bash unlock-11434.sh"
  exit 1
fi

CHAIN="THUNDER-OLLAMA-IN"
PORT=11434

for ipt in iptables ip6tables; do
  $ipt -D INPUT -p tcp --dport "$PORT" -j "$CHAIN" 2>/dev/null || true
  $ipt -F "$CHAIN" 2>/dev/null || true
  $ipt -X "$CHAIN" 2>/dev/null || true
done

netfilter-persistent save >/dev/null 2>&1 || {
  iptables-save > /etc/iptables/rules.v4
  ip6tables-save > /etc/iptables/rules.v6
}

echo "Unlocked. Port $PORT is open to the LAN again."
