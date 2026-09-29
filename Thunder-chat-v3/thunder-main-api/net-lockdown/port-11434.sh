#!/usr/bin/env bash
# Firewalls Ollama's port 11434 INBOUND to the machines that actually use it.
#
# lock.sh is the other half of this and does the opposite direction: it stops
# the ollama *process* from reaching the internet. Nothing stopped the
# internet - or any box on the LAN - from reaching *it*. Ollama has no
# authentication of any kind, so anyone who can open a socket to 11434 can
# run inference, list models, and delete them.
#
# Ollama stays bound to 0.0.0.0 (OLLAMA_HOST in the systemd drop-in). Binding
# it to 127.0.0.1 instead would be simpler, but it would cut off the two
# remote callers below, which are meant to be there.
#
# WHO IS ALLOWED, and why each one is real:
#
#   127.0.0.1    thunder-main itself (app.py OLLAMA=http://127.0.0.1:11434)
#   10.168.168.15  odris   - odris_admin.py:18 points its admin dashboard at
#                            http://10.168.168.10:11434
#   10.168.168.11  cache   - /home/blayne-cache/cache_worker.py:19. This is
#                            the overnight batch coding worker. It is an
#                            *active, enabled* systemd service
#                            (thunder-cache.service) and it has no GPU of its
#                            own, so every job it runs is an inference call to
#                            Main. lock.sh's own header says so too: "Cache
#                            and other nodes call Main's Ollama directly, so
#                            this is not just loopback-only."
#
# Everything else on the LAN is dropped, which is the part that matters:
# thunder-engine (.12) and serverus (.13) have no business here. Serverus runs
# its own Ollama for embeddings - Main calls out to it, not the reverse.
#
# Re-runnable: the rules live in their own chain, which is flushed each time,
# so this never stacks up duplicates and never touches the OUTPUT egress rules
# that lock.sh installed.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo bash port-11434.sh"
  exit 1
fi

CHAIN="THUNDER-OLLAMA-IN"
PORT=11434
ALLOW=("10.168.168.15" "10.168.168.11")

# --- IPv4 -------------------------------------------------------------------
iptables -N "$CHAIN" 2>/dev/null || true
iptables -F "$CHAIN"

# Loopback first: this is how app.py, consolidate.py and extract.py get in.
iptables -A "$CHAIN" -i lo -j ACCEPT
iptables -A "$CHAIN" -s 127.0.0.0/8 -j ACCEPT
for ip in "${ALLOW[@]}"; do
  iptables -A "$CHAIN" -s "$ip" -j ACCEPT
done
# An already-open conversation keeps working; only new ones are judged.
iptables -A "$CHAIN" -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A "$CHAIN" -j LOG --log-prefix "THUNDER-OLLAMA-DROP: " --log-level 4 -m limit --limit 5/min
iptables -A "$CHAIN" -j DROP

# Hook it up exactly once.
iptables -D INPUT -p tcp --dport "$PORT" -j "$CHAIN" 2>/dev/null || true
iptables -I INPUT 1 -p tcp --dport "$PORT" -j "$CHAIN"

# --- IPv6 -------------------------------------------------------------------
# `ss` shows Ollama on *:11434, which is the v6 wildcard accepting v4-mapped
# connections. Leaving v6 open would make the whole v4 rule set decorative.
ip6tables -N "$CHAIN" 2>/dev/null || true
ip6tables -F "$CHAIN"
ip6tables -A "$CHAIN" -i lo -j ACCEPT
ip6tables -A "$CHAIN" -s ::1/128 -j ACCEPT
ip6tables -A "$CHAIN" -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
ip6tables -A "$CHAIN" -j DROP
ip6tables -D INPUT -p tcp --dport "$PORT" -j "$CHAIN" 2>/dev/null || true
ip6tables -I INPUT 1 -p tcp --dport "$PORT" -j "$CHAIN"

# Same persistence the egress lockdown uses, so this survives a reboot.
netfilter-persistent save >/dev/null 2>&1 || {
  iptables-save > /etc/iptables/rules.v4
  ip6tables-save > /etc/iptables/rules.v6
}

echo "Port $PORT is now reachable only from localhost, ${ALLOW[*]}."
echo
echo "Verify:"
echo "  curl -s http://127.0.0.1:$PORT/api/version                      # works"
echo "  ssh odris curl -s -m 5 http://10.168.168.10:$PORT/api/version   # works"
echo "  ssh thunder-cache curl -s -m 5 http://10.168.168.10:$PORT/api/version  # works (batch worker)"
echo "  ssh thunder-engine curl -s -m 5 http://10.168.168.10:$PORT/api/version # times out"
echo
echo "Undo with: sudo bash unlock-11434.sh"
