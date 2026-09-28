#!/usr/bin/env bash
# Thunder Turbo: llama-server with speculative decoding for the main model.
#
#   ./turbo.sh model <ollama-model>          path of an Ollama model's GGUF blob
#   sudo ./turbo.sh install <target> <draft> write + start the system unit
#   ./turbo.sh bench                          tokens/sec, turbo vs plain Ollama
#
# Speculative decoding: the draft (a small model with the SAME tokenizer, e.g.
# a 0.6B or 1.7B from the target's family) guesses the next several tokens and
# the target checks them all in one pass. Accepted guesses are free tokens;
# output is identical to the target alone, only faster.
#
# Runs as the `ollama` user, so it inherits the egress lockdown: the model
# server can reach the LAN and nothing else, exactly like Ollama. Reads the
# GGUFs Ollama already downloaded - nothing is duplicated.
set -euo pipefail
BIN=${LLAMA_SERVER:-/usr/local/bin/llama-server}
UNIT=/etc/systemd/system/thunder-turbo.service
PORT=${TURBO_PORT:-8081}
CTX=${TURBO_CTX:-32768}

blob() {
  # The FROM line of an Ollama model is the path of its GGUF.
  ollama show --modelfile "$1" | awk '/^FROM /{print $2; exit}'
}

case "${1:-}" in
  model) blob "$2" ;;
  install)
    [[ $EUID -eq 0 ]] || { echo "run with sudo"; exit 1; }
    target=$(blob "$2"); draft=$(blob "$3")
    [[ -r $target && -r $draft ]] || { echo "could not find GGUFs for $2 / $3"; exit 1; }
    cat > "$UNIT" <<UNIT
[Unit]
Description=Thunder Turbo - llama-server with speculative decoding
After=network-online.target ollama.service
[Service]
User=ollama
Group=ollama
ExecStart=$BIN -m $target -md $draft -ngl 99 -ngld 99 --spec-type draft-simple --spec-draft-n-max 16 --spec-draft-n-min 1 \\
  -c $CTX -fa on -ctk q8_0 -ctv q8_0 --jinja --parallel 2 --host 127.0.0.1 --port $PORT
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
UNIT
    systemctl daemon-reload && systemctl enable --now thunder-turbo
    echo "started. Then set THUNDER_BACKEND=llamacpp for thunder-main and restart it."
    ;;
  bench)
    python3 "$(dirname "$0")/turbo_bench.py" ;;
  *) sed -n '2,15p' "$0" ;;
esac
