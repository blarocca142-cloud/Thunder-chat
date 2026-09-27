#!/usr/bin/env bash
# thunder-tune: make Main's hardware work harder for Thunder.
#
#   sudo ./tune.sh status     what is applied, what is not
#   sudo ./tune.sh apply      apply everything below (idempotent)
#   sudo ./tune.sh revert     undo everything this script did
#   python3 bench.py          measure tokens/sec before and after
#
# Every change is a file this script owns, so revert is exact:
#   1. zram      - compressed RAM. 12GB of swap that lives in RAM, zstd-packed,
#                  tried before the SSD swap. Ordinary pages (Python, the API,
#                  caches) compress ~2-3x, so the 32GB board holds more before
#                  it touches disk. Model weights are already 4-bit and barely
#                  compress; this frees room AROUND the model, not inside it.
#   2. ollama    - flash attention + 8-bit KV cache (context memory on the GPU
#                  roughly halved: ~2x the context in the same VRAM), 4
#                  parallel requests (Forge runs its candidates at once
#                  instead of queueing), 2 models resident (coding + medical,
#                  no reload when switching), models stay loaded 24h.
#   3. gpu       - persistence mode (no cold start per request) and a 300W
#                  power limit. LLM decoding is memory-bound, so the 3090
#                  loses little speed below its 350W default and runs cooler -
#                  and its GDDR6X throttles on heat long before it runs out of
#                  power. Re-applied at boot. bench.py measures the trade.
#   4. cpu/vm    - performance governor, and swappiness 150 so the kernel
#                  prefers zram (cheap) over dropping file cache.
set -euo pipefail

OWN=/etc/thunder-tune
ZRAM_UNIT=/etc/systemd/system/thunder-zram.service
GPU_UNIT=/etc/systemd/system/thunder-gpu.service
OLLAMA_DROPIN=/etc/systemd/system/ollama.service.d/thunder-tune.conf
SYSCTL=/etc/sysctl.d/61-thunder-tune.conf
ZRAM_SIZE=${ZRAM_SIZE:-12G}
GPU_WATTS=${GPU_WATTS:-300}

need_root() { [[ $EUID -eq 0 ]] || { echo "run with sudo"; exit 1; }; }
say() { printf '  %-10s %s\n' "$1" "$2"; }

status() {
  echo "thunder-tune status"
  if swapon --show=NAME,SIZE,PRIO --noheadings 2>/dev/null | grep -q zram; then
    say zram "on: $(swapon --show=NAME,SIZE,PRIO --noheadings | grep zram | xargs)"
    zramctl --output NAME,ALGORITHM,DATA,COMPR,TOTAL --noheadings 2>/dev/null | sed 's/^/             /'
  else say zram off; fi
  if [[ -f $OLLAMA_DROPIN ]]; then say ollama "tuned: $(grep -o 'OLLAMA_[A-Z_]*=[^"]*' $OLLAMA_DROPIN | xargs)"; else say ollama default; fi
  if command -v nvidia-smi >/dev/null; then
    say gpu "$(nvidia-smi --query-gpu=persistence_mode,power.limit,temperature.gpu,clocks_throttle_reasons.active --format=csv,noheader)"
  fi
  say cpu "governor $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo n/a)"
  say vm "swappiness $(cat /proc/sys/vm/swappiness), page-cluster $(cat /proc/sys/vm/page-cluster)"
}

apply() {
  need_root
  mkdir -p "$OWN"

  # 1. zram - a oneshot unit so it survives reboots without extra packages.
  cat > "$ZRAM_UNIT" <<UNIT
[Unit]
Description=Thunder compressed RAM swap (zram, zstd)
Before=ollama.service
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'modprobe zram num_devices=1 && echo zstd > /sys/block/zram0/comp_algorithm && echo $ZRAM_SIZE > /sys/block/zram0/disksize && mkswap /dev/zram0 >/dev/null && swapon -p 100 /dev/zram0'
ExecStop=/bin/sh -c 'swapoff /dev/zram0; echo 1 > /sys/block/zram0/reset'
[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
  swapon --show | grep -q zram0 || systemctl enable --now thunder-zram.service

  # 2. ollama
  mkdir -p "$(dirname "$OLLAMA_DROPIN")"
  cat > "$OLLAMA_DROPIN" <<CONF
# written by thunder-tune; remove with tune.sh revert
[Service]
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_NUM_PARALLEL=4"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_KEEP_ALIVE=24h"
CONF
  systemctl daemon-reload
  systemctl restart ollama

  # 3. gpu
  if command -v nvidia-smi >/dev/null; then
    cat > "$GPU_UNIT" <<UNIT
[Unit]
Description=Thunder GPU settings (persistence, power limit)
After=nvidia-persistenced.service
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/nvidia-smi -pm 1
ExecStart=/usr/bin/nvidia-smi -pl $GPU_WATTS
ExecStop=/bin/sh -c '/usr/bin/nvidia-smi -pl $(nvidia-smi --query-gpu=power.default_limit --format=csv,noheader,nounits | cut -d. -f1)'
[Install]
WantedBy=multi-user.target
UNIT
    systemctl daemon-reload
    systemctl enable thunder-gpu.service >/dev/null
    systemctl restart thunder-gpu.service
  fi

  # 4. cpu / vm
  [[ -f $OWN/governor.orig ]] || cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor > "$OWN/governor.orig" 2>/dev/null || true
  echo "vm.swappiness=150" > "$SYSCTL"
  sysctl -q -p "$SYSCTL"
  for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    [[ -w $g ]] && echo performance > "$g" || true
  done

  echo "applied."; status
}

revert() {
  need_root
  systemctl disable --now thunder-zram.service 2>/dev/null || true
  systemctl disable --now thunder-gpu.service 2>/dev/null || true
  rm -f "$ZRAM_UNIT" "$GPU_UNIT" "$OLLAMA_DROPIN" "$SYSCTL"
  systemctl daemon-reload
  systemctl restart ollama || true
  sysctl -q --system
  orig=$(cat "$OWN/governor.orig" 2>/dev/null || echo powersave)
  for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    [[ -w $g ]] && echo "$orig" > "$g" || true
  done
  rm -rf "$OWN"
  echo "reverted."; status
}

case "${1:-status}" in
  status) status ;;
  apply) apply ;;
  revert) revert ;;
  *) echo "usage: $0 status|apply|revert"; exit 2 ;;
esac
