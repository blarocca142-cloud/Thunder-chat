#!/bin/bash -l
# Runs inside tmux session "claude" (started by claude-bridge.service).
# If the bridge exits - a network drop, an update - it comes back by itself.
cd "$HOME/Thunder-chat" || exit 1
while true; do
    claude remote-control
    echo "bridge exited ($(date)) - restarting in 30s; Ctrl+C to stop"
    sleep 30
done
