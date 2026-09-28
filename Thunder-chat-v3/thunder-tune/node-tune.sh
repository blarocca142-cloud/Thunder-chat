#!/usr/bin/env bash
# node-tune: the same treatment as Main, for every tower (odris, serverus,
# thunder-cache, thunder-engine) - and Main too, for the network part.
#
#   sudo ./node-tune.sh status|apply|revert
#
#   zram     compressed swap in RAM, half the machine's RAM, zstd, priority
#            above any disk swap. More room before anything touches a disk.
#   cpu      performance governor (original saved and restored on revert).
#   vm       swappiness 150 (prefer zram over dropping cache).
#   network  fq + BBR, 16MB socket buffers, faster TCP reuse. Fleet traffic
#            (tool calls, memory, backups, the archive copy) is many small
#            requests plus a few big transfers; both benefit.
#
# Odris note: its services are root-owned and its root password is lost, so
# this cannot be applied there until root is recovered (see README.md). The
# cache and prefetch in odris_gate.py need no root and work regardless.
set -euo pipefail
OWN=/etc/thunder-node-tune
UNIT=/etc/systemd/system/thunder-node-zram.service
SYSCTL=/etc/sysctl.d/62-thunder-node.conf

say() { printf '  %-9s %s\n' "$1" "$2"; }
need_root() { [[ $EUID -eq 0 ]] || { echo "run with sudo"; exit 1; }; }

status() {
  echo "node-tune on $(hostname)"
  if swapon --show --noheadings | grep -q zram; then say zram "$(swapon --show=NAME,SIZE,PRIO --noheadings | grep zram | xargs)"; else say zram off; fi
  say cpu "$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo n/a)"
  say vm "swappiness $(cat /proc/sys/vm/swappiness)"
  say network "$(sysctl -n net.ipv4.tcp_congestion_control) / $(sysctl -n net.core.default_qdisc)"
}

apply() {
  need_root
  mkdir -p "$OWN"
  half=$(( $(awk '/MemTotal/{print $2}' /proc/meminfo) / 2 ))K
  cat > "$UNIT" <<UNIT
[Unit]
Description=Thunder node compressed RAM swap
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'modprobe zram num_devices=1 && echo zstd > /sys/block/zram0/comp_algorithm && echo $half > /sys/block/zram0/disksize && mkswap /dev/zram0 >/dev/null && swapon -p 100 /dev/zram0'
ExecStop=/bin/sh -c 'swapoff /dev/zram0; echo 1 > /sys/block/zram0/reset'
[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
  swapon --show | grep -q zram0 || systemctl enable --now thunder-node-zram.service

  [[ -f $OWN/governor.orig ]] || cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor > "$OWN/governor.orig" 2>/dev/null || true
  for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do [[ -w $g ]] && echo performance > "$g" || true; done

  modprobe tcp_bbr 2>/dev/null || true
  cat > "$SYSCTL" <<CONF
vm.swappiness=150
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
net.core.rmem_max=16777216
net.core.wmem_max=16777216
net.ipv4.tcp_rmem=4096 131072 16777216
net.ipv4.tcp_wmem=4096 65536 16777216
net.ipv4.tcp_fastopen=3
net.ipv4.tcp_slow_start_after_idle=0
CONF
  sysctl -q -p "$SYSCTL"
  echo applied.; status
}

revert() {
  need_root
  systemctl disable --now thunder-node-zram.service 2>/dev/null || true
  rm -f "$UNIT" "$SYSCTL"
  systemctl daemon-reload
  sysctl -q --system
  orig=$(cat "$OWN/governor.orig" 2>/dev/null || echo powersave)
  for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do [[ -w $g ]] && echo "$orig" > "$g" || true; done
  rm -rf "$OWN"
  echo reverted.; status
}

case "${1:-status}" in status) status;; apply) apply;; revert) revert;; *) echo "usage: $0 status|apply|revert"; exit 2;; esac
