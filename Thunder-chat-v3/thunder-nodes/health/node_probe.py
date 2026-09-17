#!/usr/bin/env python3
"""Read every hardware signal this box will give up without root, as JSON.

Runs on each node. Odris calls it over SSH with a forced command, so this is
the ONLY thing Odris's key can do on the machine - it reads, it never writes,
and it takes no arguments.

The honesty rule for this whole file: **report what was measured, or say it
could not be measured, and never guess in between.** A dashboard full of
confident percentages invented from nothing is worse than an empty one,
because it gets trusted. Every reading here carries where it came from, and
anything unreadable is reported as unavailable with the reason - which is also
a finding, since "we cannot see the disks" is worth knowing.

Stdlib only. No root, no installs, no GPU compute - reading a GPU's
temperature sensor is not using the GPU.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
from pathlib import Path

HWMON = Path("/sys/class/hwmon")
EDAC = Path("/sys/devices/system/edac/mc")
CPU = Path("/sys/devices/system/cpu")
NET = Path("/sys/class/net")
BLOCK = Path("/sys/block")


def read(path, default=None, as_int=False):
    """Every sysfs read goes through here: missing files and permission
    errors are normal on these boxes and must never stop the probe."""
    try:
        text = Path(path).read_text().strip()
        return int(text) if as_int else text
    except Exception:
        return default


def run(cmd: list[str], timeout: int = 8) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


# ---------------------------------------------------------------- sensors

def hwmon_chips() -> list[dict]:
    """Every hwmon chip with its named readings.

    This is where the useful stuff lives on machines with no lm-sensors
    installed: coretemp for the CPU, jc42 for DIMM temperature, amdgpu or
    nvidia for the card, power_meter for wall draw.
    """
    chips = []
    if not HWMON.is_dir():
        return chips
    for d in sorted(HWMON.glob("hwmon*")):
        name = read(d / "name")
        if not name:
            continue
        chip = {"chip": name, "temps": [], "fans": [], "volts": [], "power": []}
        for f in sorted(d.glob("temp*_input")):
            raw = read(f, as_int=True)
            if raw is None:
                continue
            label = read(f.with_name(f.name.replace("_input", "_label"))) or f.stem
            entry = {"label": label, "celsius": round(raw / 1000, 1)}
            for kind in ("max", "crit"):
                lim = read(f.with_name(f.name.replace("_input", f"_{kind}")), as_int=True)
                if lim:
                    entry[kind] = round(lim / 1000, 1)
            chip["temps"].append(entry)
        for f in sorted(d.glob("fan*_input")):
            rpm = read(f, as_int=True)
            if rpm is not None:
                chip["fans"].append({
                    "label": read(f.with_name(f.name.replace("_input", "_label"))) or f.stem,
                    "rpm": rpm})
        for f in sorted(d.glob("in*_input")):
            mv = read(f, as_int=True)
            if mv is not None:
                chip["volts"].append({
                    "label": read(f.with_name(f.name.replace("_input", "_label"))) or f.stem,
                    "volts": round(mv / 1000, 3)})
        for f in sorted(d.glob("power*_average")) + sorted(d.glob("power*_input")):
            uw = read(f, as_int=True)
            if uw is not None:
                chip["power"].append({"label": f.stem, "watts": round(uw / 1_000_000, 1)})
        if chip["temps"] or chip["fans"] or chip["volts"] or chip["power"]:
            chips.append(chip)
    return chips


def cpu_info() -> dict:
    model = None
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass

    # Throttling is a fact, not an inference: the CPU counted these itself.
    throttle_core = throttle_pkg = 0
    cores = 0
    for d in sorted(CPU.glob("cpu[0-9]*")):
        t = d / "thermal_throttle"
        if t.is_dir():
            cores += 1
            throttle_core += read(t / "core_throttle_count", 0, as_int=True) or 0
            throttle_pkg += read(t / "package_throttle_count", 0, as_int=True) or 0

    load = os.getloadavg()
    return {
        "model": model,
        "cores_seen": cores,
        "load_1m": round(load[0], 2),
        "load_15m": round(load[2], 2),
        "throttle_events_core": throttle_core,
        "throttle_events_package": throttle_pkg,
    }


# ---------------------------------------------------------------- memory

def memory() -> dict:
    info = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, _, v = line.partition(":")
            info[k] = int(v.strip().split()[0])
    except Exception:
        pass
    total = info.get("MemTotal", 0)
    out = {
        "total_mb": total // 1024,
        "available_mb": info.get("MemAvailable", 0) // 1024,
        "swap_total_mb": info.get("SwapTotal", 0) // 1024,
        "swap_used_mb": (info.get("SwapTotal", 0) - info.get("SwapFree", 0)) // 1024,
        "ecc": None,
        "dimms": [],
    }

    # EDAC is the only real RAM health signal available without taking the
    # machine offline for memtest. It exists only on boards with ECC.
    if EDAC.is_dir():
        controllers = []
        for mc in sorted(EDAC.glob("mc[0-9]*")):
            ce = read(mc / "ce_count", as_int=True)
            ue = read(mc / "ue_count", as_int=True)
            if ce is None and ue is None:
                continue
            ranks = []
            # Newer kernels use dimm*, older use csrow*.
            for dimm in sorted(list(mc.glob("dimm*")) + list(mc.glob("csrow*"))):
                d_ce = read(dimm / "dimm_ce_count", as_int=True)
                if d_ce is None:
                    d_ce = read(dimm / "ce_count", as_int=True)
                d_ue = read(dimm / "dimm_ue_count", as_int=True)
                if d_ue is None:
                    d_ue = read(dimm / "ue_count", as_int=True)
                if d_ce is None and d_ue is None:
                    continue
                ranks.append({
                    "slot": read(dimm / "dimm_location") or dimm.name,
                    "label": read(dimm / "dimm_label") or None,
                    "size_mb": read(dimm / "size", as_int=True),
                    "corrected": d_ce or 0,
                    "uncorrectable": d_ue or 0,
                })
            controllers.append({
                "controller": mc.name,
                "type": read(mc / "mc_name"),
                "corrected": ce or 0,
                "uncorrectable": ue or 0,
                "ranks": ranks,
            })
        if controllers:
            out["ecc"] = controllers
            out["dimms"] = [r for c in controllers for r in c["ranks"]]

    # Per-DIMM thermal sensors, where the board has them (jc42 on serverus).
    # Each DIMM has its own jc42 chip, and every one of them calls its reading
    # "temp1_input". Numbering them in the order the kernel enumerates them is
    # what turns four identical readings into "slot 1, slot 2, slot 3, slot 4",
    # which is the entire reason for showing them.
    dimm_temps = []
    slot = 0
    for chip in hwmon_chips():
        if chip["chip"].startswith("jc42"):
            for t in chip["temps"]:
                slot += 1
                dimm_temps.append({"label": f"slot {slot}", "celsius": t["celsius"],
                                   "sensor": t["label"]})
    if dimm_temps:
        out["dimm_temps"] = dimm_temps
    return out


# ---------------------------------------------------------------- storage

def storage() -> dict:
    disks = []
    # Works out for itself how smartctl can be run, so that the moment
    # smartmontools is installed on a node this starts reporting with no code
    # change and nobody needing to remember to say so.
    smart_cmd = None
    if run(["which", "smartctl"]):
        if run(["sudo", "-n", "smartctl", "--version"], timeout=6):
            smart_cmd = ["sudo", "-n", "smartctl"]   # the sudoers rule is in place
        elif os.geteuid() == 0:
            smart_cmd = ["smartctl"]
        else:
            # Installed but not permitted: reading devices needs root, so this
            # is reported as unavailable rather than silently returning nothing.
            smart_cmd = None
    smart_available = smart_cmd is not None
    for d in sorted(BLOCK.iterdir()) if BLOCK.is_dir() else []:
        name = d.name
        if name.startswith(("loop", "ram", "zram", "sr", "dm-")):
            continue
        size_sectors = read(d / "size", 0, as_int=True) or 0
        disk = {
            "device": name,
            "size_gb": round(size_sectors * 512 / 1e9, 1),
            "rotational": read(d / "queue/rotational") == "1",
            "model": read(d / "device/model"),
            "smart": None,
        }
        # ios and ioerr counters the kernel keeps regardless of SMART access.
        disk["io_errors"] = read(d / "device/ioerr_cnt")
        if smart_cmd:
            raw = run(smart_cmd + ["-j", "-H", "-A", f"/dev/{name}"], timeout=15)
            if raw:
                try:
                    s = json.loads(raw)
                    attrs = {}
                    for a in (s.get("ata_smart_attributes", {}) or {}).get("table", []):
                        attrs[a.get("name")] = a.get("raw", {}).get("value")
                    disk["smart"] = {
                        "passed": (s.get("smart_status", {}) or {}).get("passed"),
                        "power_on_hours": (s.get("power_on_time", {}) or {}).get("hours"),
                        "temperature": (s.get("temperature", {}) or {}).get("current"),
                        "reallocated": attrs.get("Reallocated_Sector_Ct"),
                        "pending": attrs.get("Current_Pending_Sector"),
                        "uncorrectable": attrs.get("Offline_Uncorrectable"),
                        "crc_errors": attrs.get("UDMA_CRC_Error_Count"),
                        "wear_leveling": attrs.get("Wear_Leveling_Count"),
                        "percent_used": (s.get("nvme_smart_health_information_log", {})
                                         or {}).get("percentage_used"),
                    }
                except Exception:
                    pass
        disks.append(disk)

    # Only filesystems that actually store things. efivarfs is a ~130KB
    # variable store that sits permanently near full, and reporting it as "97%
    # full, take action" is a false alarm on every machine that has one. The
    # same goes for every other kernel pseudo-filesystem.
    REAL_FS = {"ext2", "ext3", "ext4", "xfs", "btrfs", "f2fs", "jfs", "reiserfs",
               "vfat", "ntfs", "ntfs3", "exfat", "zfs", "overlay"}
    mounts = []
    for line in (run(["df", "-PT"]) or "").splitlines()[1:]:
        parts = line.split()
        if len(parts) < 7 or parts[1] not in REAL_FS:
            continue
        try:
            mounts.append({
                "mount": parts[6],
                "fs": parts[1],
                "used_pct": int(parts[5].rstrip("%")),
                "free_gb": round(int(parts[4]) / 1024 / 1024, 1),
            })
        except ValueError:
            continue

    # A writable filesystem that has gone read-only is a failure in progress.
    # Only these types are worth checking: squashfs (every snap), iso9660 and
    # erofs are read-only by design, and flagging them reported 22 emergencies
    # on a perfectly healthy machine. A health check that cries wolf is one
    # that gets ignored, which is worse than not having it.
    WRITABLE_FS = {"ext2", "ext3", "ext4", "xfs", "btrfs", "f2fs", "jfs", "reiserfs"}
    readonly = []
    try:
        for line in Path("/proc/mounts").read_text().splitlines():
            f = line.split()
            if len(f) < 4 or not f[0].startswith("/dev/"):
                continue
            if f[2] not in WRITABLE_FS:
                continue
            if "ro" in f[3].split(","):
                readonly.append(f[1])
    except Exception:
        pass

    return {"disks": disks, "mounts": mounts, "readonly_mounts": readonly,
            "smart_available": smart_available,
            "smart_installed": bool(run(["which", "smartctl"]))}


# ---------------------------------------------------------------- network

def network() -> list[dict]:
    out = []
    for d in sorted(NET.iterdir()) if NET.is_dir() else []:
        if d.name == "lo" or not (d / "statistics").is_dir():
            continue
        if read(d / "operstate") != "up":
            continue
        s = d / "statistics"
        out.append({
            "iface": d.name,
            "speed_mbps": read(d / "speed", as_int=True),
            "rx_bytes": read(s / "rx_bytes", 0, as_int=True),
            "tx_bytes": read(s / "tx_bytes", 0, as_int=True),
            "rx_errors": read(s / "rx_errors", 0, as_int=True),
            "tx_errors": read(s / "tx_errors", 0, as_int=True),
            "rx_dropped": read(s / "rx_dropped", 0, as_int=True),
            "rx_crc_errors": read(s / "rx_crc_errors", 0, as_int=True),
        })
    return out


# ---------------------------------------------------------------- gpu

def gpu() -> list[dict]:
    """Temperature and fan only. Reading a sensor is not using the card."""
    cards = []
    for chip in hwmon_chips():
        if chip["chip"] in ("amdgpu", "radeon"):
            cards.append({
                "vendor": "amd",
                "chip": chip["chip"],
                "temps": chip["temps"],
                "fans": chip["fans"],
                "power": chip["power"],
            })
    out = run(["nvidia-smi", "--query-gpu=name,temperature.gpu,fan.speed,"
               "power.draw,memory.total,memory.used,ecc.errors.uncorrected.volatile.total",
               "--format=csv,noheader,nounits"])
    if out:
        for line in out.strip().splitlines():
            p = [x.strip() for x in line.split(",")]
            if len(p) >= 6:
                cards.append({
                    "vendor": "nvidia",
                    "name": p[0],
                    "temps": [{"label": "gpu", "celsius": float(p[1])}] if p[1].replace(".", "").isdigit() else [],
                    "fan_pct": p[2] if p[2] not in ("[N/A]", "") else None,
                    "watts": p[3],
                    "vram_total_mb": p[4],
                    "vram_used_mb": p[5],
                    "ecc_uncorrected": p[6] if len(p) > 6 else None,
                })
    return cards


# ---------------------------------------------------------------- kernel

def kernel_events() -> dict:
    """Hardware complaints the kernel has already logged.

    Requires the journal to be readable by this user; when it is not, that is
    reported rather than silently returning zero, because "no errors found"
    and "could not look" must never look the same.
    """
    out = {"readable": False, "io_errors": 0, "mce": 0, "oom": 0, "ata_resets": 0,
           "samples": []}
    text = run(["journalctl", "-k", "--since", "-14 days", "--no-pager", "-q"], timeout=20)
    if text is None:
        return out
    out["readable"] = True
    patterns = {
        "io_errors": re.compile(r"(?i)\b(I/O error|blk_update_request|medium error)"),
        "mce": re.compile(r"(?i)\b(machine check|mce:|hardware error)"),
        "oom": re.compile(r"(?i)\bout of memory|oom-kill"),
        "ata_resets": re.compile(r"(?i)\bata\d+.*(hard resetting link|failed command)"),
    }
    for line in text.splitlines():
        for key, pat in patterns.items():
            if pat.search(line):
                out[key] += 1
                if len(out["samples"]) < 8:
                    out["samples"].append(line[-160:])
    return out


def board() -> dict:
    """Motherboard identity and the bus errors that indict it.

    /sys/class/dmi/id is readable without root (serial numbers are not, and
    are not wanted). BIOS date doubles as the board's age, which is the honest
    basis for advice about ageing capacitors on a 2013 machine.
    """
    dmi = Path("/sys/class/dmi/id")
    info = {k: read(dmi / k) for k in
            ("board_vendor", "board_name", "board_version",
             "bios_version", "bios_date", "product_name", "sys_vendor")}

    # PCIe Advanced Error Reporting: the bus counting its own faults. A slot
    # or riser that is marginal shows up here long before anything crashes.
    aer = {"readable": False, "correctable": 0, "fatal": 0, "nonfatal": 0, "devices": []}
    for dev in sorted(Path("/sys/bus/pci/devices").glob("*")) if Path("/sys/bus/pci/devices").is_dir() else []:
        for kind, key in (("aer_dev_correctable", "correctable"),
                          ("aer_dev_fatal", "fatal"),
                          ("aer_dev_nonfatal", "nonfatal")):
            text = read(dev / kind)
            if text is None:
                continue
            aer["readable"] = True
            total = 0
            for line in text.splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1].isdigit():
                    total += int(parts[1])
            if total:
                aer[key] += total
                aer["devices"].append({"device": dev.name, "kind": key, "count": total})
    info["pcie_errors"] = aer

    # Chipset temperature, where the board exposes it.
    for chip in hwmon_chips():
        if chip["chip"].startswith(("pch", "chipset")) and chip["temps"]:
            info["chipset_temp"] = chip["temps"][0]["celsius"]
    return info


def power() -> dict:
    """What can be known about the power supply, which is usually little.

    Consumer boards without a SuperIO sensor chip expose no voltage rails at
    all, so on most of this fleet the PSU simply cannot be inspected directly.
    That is reported as such - an uninspectable item is a finding, not a pass.
    """
    # A GPU core voltage is not a power-supply rail, and neither is a battery.
    # Counting one as a rail made odris report a healthy PSU on the strength of
    # amdgpu/vddgfx at 0.7V, which is exactly the false all-clear this whole
    # file exists to avoid.
    NOT_PSU = ("amdgpu", "radeon", "nvidia", "i915", "acpitz", "battery")
    rails, watts = [], None
    for chip in hwmon_chips():
        if any(chip["chip"].startswith(x) for x in NOT_PSU):
            continue
        for v in chip["volts"]:
            rails.append({"chip": chip["chip"], **v})
        for p_ in chip["power"]:
            if chip["chip"] == "power_meter":
                watts = p_["watts"]
    # Wall draw alone is useful for trending but says nothing about rail health,
    # so it does not make the supply "inspectable".
    return {"rails": rails, "watts": watts, "inspectable": bool(rails),
            "draw_only": bool(watts and not rails)}


def uptime_info() -> dict:
    up = read("/proc/uptime", "0").split()[0]
    boots = run(["journalctl", "--list-boots", "--no-pager", "-q"])
    return {
        "uptime_hours": round(float(up) / 3600, 1) if up else None,
        "boots_recorded": len(boots.strip().splitlines()) if boots else None,
    }


def main() -> None:
    print(json.dumps({
        "host": socket.gethostname(),
        "at": time.time(),
        "probe_version": 1,
        "kernel": read("/proc/sys/kernel/osrelease"),
        "cpu": cpu_info(),
        "memory": memory(),
        "storage": storage(),
        "network": network(),
        "gpu": gpu(),
        "sensors": hwmon_chips(),
        "board": board(),
        "power": power(),
        "kernel_events": kernel_events(),
        "uptime": uptime_info(),
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
