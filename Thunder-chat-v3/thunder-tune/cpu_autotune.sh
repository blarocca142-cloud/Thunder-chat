#!/usr/bin/env bash
# cpu_autotune: get a locked Haswell (i7-4790 on Lenovo's Q87 board) to hold
# its top turbo, the homebrew way - through the CPU's own control registers,
# no BIOS flash. Everything written here is volatile: a reboot undoes it.
# Only settings that pass the stress test are saved for boot.
#
#   sudo ./cpu_autotune.sh probe     speed under load, throttling, power limits, lock bits
#   sudo ./cpu_autotune.sh tune      step the undervolt down, stress-test each step, keep a margin
#   sudo ./cpu_autotune.sh revert    zero offsets, remove the boot unit
#
# Tools (free): intel-undervolt (writes MSR 0x150 / power limits safely),
# linux-tools turbostat (real clocks and throttle reasons), stress-ng.
#   sudo apt install intel-undervolt linux-tools-common linux-tools-$(uname -r) stress-ng
#
# Why undervolt instead of overclock: the multiplier is locked and Lenovo's
# BIOS hides Haswell's limited-unlock bins. Lower voltage = less heat = the
# chip stays at 3.8-4.0GHz instead of backing off. Haswell (4th gen) predates
# Intel's Plundervolt lockdown, so the voltage offset register still works.
set -euo pipefail
CONF=/etc/intel-undervolt.conf
STEP=${STEP:-10}          # mV per step
FLOOR=${FLOOR:--120}      # never go below this
MARGIN=${MARGIN:-20}      # back off this much from the last stable step
SECS=${SECS:-120}         # stress time per step

need() { command -v "$1" >/dev/null || { echo "missing $1 - see the apt line at the top"; exit 1; }; }
root() { [[ $EUID -eq 0 ]] || { echo "run with sudo"; exit 1; }; }

probe() {
  root; need turbostat; need stress-ng
  modprobe msr
  echo "== package power limits (MSR 0x610)"
  python3 - <<'PY'
import struct
def msr(reg):
    with open("/dev/cpu/0/msr", "rb") as f:
        f.seek(reg)
        return struct.unpack("<Q", f.read(8))[0]
unit = 1 / (1 << (msr(0x606) & 0xF))          # the chip's own power unit
v = msr(0x610)
pl1 = (v & 0x7FFF) * unit; pl2 = ((v >> 32) & 0x7FFF) * unit
print(f"  PL1 {pl1:.0f} W, PL2 {pl2:.0f} W (i7-4790 is rated 84 W)")
print(f"  locked: {'YES - the BIOS will not let these change' if v >> 63 else 'no - they can be raised'}")
PY
  echo "== 30s all-core load: real clocks, temperature, throttle reasons"
  stress-ng --cpu "$(nproc)" --timeout 30s >/dev/null 2>&1 &
  turbostat --quiet --show Busy%,Bzy_MHz,PkgTmp,PkgWatt --interval 5 --num_iterations 5 2>/dev/null | tail -4
  wait
  echo "  i7-4790 should hold ~3800 MHz all-core. Lower = it is being held back (heat or power limit)."
  echo "== throttle log since boot"
  grep -H . /sys/devices/system/cpu/cpu0/thermal_throttle/*_count 2>/dev/null | sed 's/^/  /'
}

apply_offset() {  # $1 = mV (negative)
  cat > "$CONF" <<C
# written by cpu_autotune.sh
undervolt 0 'CPU' $1
undervolt 1 'GPU' 0
undervolt 2 'CPU Cache' $1
undervolt 3 'System Agent' 0
undervolt 4 'Analog I/O' 0
C
  intel-undervolt apply >/dev/null
}

stable() {  # stress the step; any error, MCE or crash-in-progress = unstable
  local before; before=$(dmesg | grep -ci "machine check\|mce:" || true)
  if ! stress-ng --cpu "$(nproc)" --cpu-method matrixprod --verify --timeout "${SECS}s" >/tmp/cpu_autotune.log 2>&1; then
    return 1
  fi
  grep -qi "fail" /tmp/cpu_autotune.log && return 1
  [[ $(dmesg | grep -ci "machine check\|mce:" || true) -eq $before ]]
}

tune() {
  root; need intel-undervolt; need stress-ng
  modprobe msr
  echo "Stepping the core+cache offset down ${STEP}mV at a time, ${SECS}s of verified stress each."
  echo "If the machine hard-freezes, just reboot: nothing is saved until the end."
  best=0
  for ((mv=-STEP; mv>=FLOOR; mv-=STEP)); do
    apply_offset "$mv"
    printf '  %4d mV ... ' "$mv"
    if stable; then echo stable; best=$mv; else echo "ERRORS - stopping"; break; fi
  done
  final=$(( best == 0 ? 0 : best + MARGIN ))
  (( final > 0 )) && final=0
  apply_offset "$final"
  echo "Last stable ${best} mV; keeping ${final} mV (${MARGIN} mV margin)."
  echo "Final check at the kept setting..."
  stable && echo "  passed" || { apply_offset 0; echo "  failed - reverted to 0"; exit 1; }
  systemctl enable --now intel-undervolt.service 2>/dev/null || true
  echo "Saved for boot. Run 'probe' again to see the clock difference."
}

revert() {
  root
  [[ -x $(command -v intel-undervolt) ]] && apply_offset 0 || true
  systemctl disable intel-undervolt.service 2>/dev/null || true
  rm -f "$CONF"
  echo "reverted: offsets 0, nothing applied at boot."
}

case "${1:-}" in probe) probe;; tune) tune;; revert) revert;; *) sed -n '2,20p' "$0";; esac
