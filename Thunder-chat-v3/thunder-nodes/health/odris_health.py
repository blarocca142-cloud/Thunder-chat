#!/usr/bin/env python3
"""Odris: fleet hardware health, scored, with findings and what to do about them.

The goal is getting ahead of failures, so the design follows from what actually
predicts one. A single reading predicts nothing - a disk at 41C is not news.
What predicts failure is a **change**: a temperature climbing at the same load,
a fan slowing, an error counter that was zero last month and is not now. So
every poll is kept, and the scoring compares today against this machine's own
history rather than against a number from a manual.

The second rule is honesty about what cannot be seen. These are consumer boards
with no voltage sensors, no SMART tooling installed and mostly no ECC. A health
page that prints "PSU 98%" from nothing is worse than one that prints "not
inspectable", because the first gets believed. Every component here is either
**measured** - with the reading and the limit shown - or **not assessable**,
with the reason and what it would take to fix that.

That distinction is the whole design. An uninspectable item is a finding, not a
pass.

    ./odris_health.py            serve on :9007
    ./odris_health.py --once     collect once and print
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 9007
HOME = Path(os.path.expanduser("~"))
HISTORY = HOME / "health_history.jsonl"
LATEST = HOME / "health_latest.json"
NODES = ["thunder-main", "thunder-cache", "thunder-engine", "serverus"]
KEEP_SAMPLES = 2000          # a couple of months of hourly polls
# A baseline younger than this is not a baseline. At an hourly poll that is a
# day of readings, which covers an idle night and a working afternoon.
MIN_BASELINE_HOURS = 24
POLL_SECONDS = 3600

_lock = threading.Lock()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------- collection

def probe_remote(node: str) -> dict | None:
    """Run the probe on a node over SSH.

    -n matters: without it the session waits on a stdin that never closes when
    this runs unattended, and the collector hangs forever on the first node.
    """
    try:
        r = subprocess.run(["ssh", "-n", node], capture_output=True, text=True, timeout=60)
        out = r.stdout.strip()
        return json.loads(out) if out.startswith("{") else None
    except Exception:
        return None


def probe_local() -> dict | None:
    probe = HOME / "node_probe.py"
    if not probe.is_file():
        return None
    try:
        r = subprocess.run([sys.executable, str(probe)],
                           capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout) if r.stdout.strip().startswith("{") else None
    except Exception:
        return None


def collect() -> dict:
    raw = {}
    local = probe_local()
    if local:
        raw["odris"] = local
    for node in NODES:
        data = probe_remote(node)
        if data:
            raw[node] = data
    return raw


# ---------------------------------------------------------------- history

def remember(raw: dict) -> None:
    """One compact line per poll. Only what trends are computed from, because
    the full probe every hour would be megabytes of duplicated inventory."""
    slim = {}
    for node, d in raw.items():
        temps = {}
        for chip in d.get("sensors", []):
            for t in chip.get("temps", []):
                temps[f"{chip['chip']}/{t['label']}"] = t["celsius"]
        fans = {}
        for chip in d.get("sensors", []):
            for f in chip.get("fans", []):
                fans[f"{chip['chip']}/{f['label']}"] = f["rpm"]
        mem = d.get("memory", {})
        ecc_ce = sum(c.get("corrected", 0) for c in (mem.get("ecc") or []))
        ecc_ue = sum(c.get("uncorrectable", 0) for c in (mem.get("ecc") or []))
        slim[node] = {
            "temps": temps,
            "fans": fans,
            "load": d.get("cpu", {}).get("load_15m"),
            "throttle": d.get("cpu", {}).get("throttle_events_core", 0),
            "ecc_ce": ecc_ce,
            "ecc_ue": ecc_ue,
            "pcie_corr": (d.get("board", {}).get("pcie_errors", {}) or {}).get("correctable", 0),
            "io_errors": d.get("kernel_events", {}).get("io_errors", 0),
        }
    with _lock:
        with HISTORY.open("a") as f:
            f.write(json.dumps({"at": time.time(), "nodes": slim}) + "\n")
        lines = HISTORY.read_text().splitlines()
        if len(lines) > KEEP_SAMPLES:
            HISTORY.write_text("\n".join(lines[-KEEP_SAMPLES:]) + "\n")


def history_for(node: str) -> list[dict]:
    if not HISTORY.is_file():
        return []
    out = []
    for line in HISTORY.read_text().splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if node in rec.get("nodes", {}):
            out.append({"at": rec["at"], **rec["nodes"][node]})
    return out


def trend(node: str, key: str, current: float | None,
          min_samples: int = 12) -> tuple[float | None, str | None]:
    """How far today sits from this machine's own normal.

    Compared against its own median rather than a spec number: a CPU that has
    always idled at 55C is fine, and the same CPU at 55C after a year at 40C is
    a dust problem. The baseline excludes the most recent samples so a slow
    drift cannot quietly redefine what normal is.
    """
    hist = history_for(node)
    if current is None or len(hist) < min_samples:
        return None, None
    # A baseline has to span time, not just count samples. Fifteen readings
    # taken over half an hour produced "package temperature up 8C on its usual
    # 36C" on a machine doing nothing - the values swing 33 to 44 naturally,
    # and a busy minute became a fault. Idle-to-busy variation within one
    # afternoon is not a trend; a month of afternoons is.
    span_hours = (hist[-1]["at"] - hist[0]["at"]) / 3600
    if span_hours < MIN_BASELINE_HOURS:
        return None, None
    values = [h["temps"].get(key) for h in hist[:-3]] if key.count("/") else []
    values = [v for v in values if isinstance(v, (int, float))]
    if len(values) < min_samples:
        return None, None
    base = statistics.median(values)
    delta = round(current - base, 1)
    if delta >= 12:
        return delta, f"up {delta}C on its own {len(values)}-sample normal of {base:.0f}C"
    if delta >= 7:
        return delta, f"up {delta}C on its usual {base:.0f}C"
    return delta, None


# ---------------------------------------------------------------- gpu hours

RUNTIME = HOME / "gpu_runtime.json"


def accrue_gpu_runtime(raw: dict) -> dict:
    """Keep a running total of GPU hours, because the card will not.

    A drive records its own power-on hours in SMART. A GPU records nothing -
    there is no odometer to read, and nvidia-smi has no lifetime counter. The
    only way to know how long a card has worked is to have been watching, so
    this counts from the first time it was asked and says so.

    Each poll adds the real elapsed time since the previous one, not the poll
    interval: a missed poll or a machine that was off must not silently count
    as hours of service.
    """
    now = time.time()
    state = {}
    if RUNTIME.is_file():
        try:
            state = json.loads(RUNTIME.read_text())
        except json.JSONDecodeError:
            state = {}

    for node, d in raw.items():
        for card in d.get("gpu", []):
            name = card.get("name") or card.get("chip") or "gpu"
            key = f"{node}/{name}"
            entry = state.get(key) or {
                "node": node, "card": name, "watching_since": utc(),
                "powered_hours": 0.0, "busy_hours": 0.0, "energy_wh": 0.0,
                "samples": 0,
            }
            last = entry.get("last_seen_at")
            gap = (now - last) / 3600 if last else 0.0
            # A gap longer than three polls means the box was off or
            # unreachable; counting it would invent hours that never happened.
            if 0 < gap <= (POLL_SECONDS * 3) / 3600:
                entry["powered_hours"] += gap
                watts = None
                try:
                    watts = float(card.get("watts"))
                except (TypeError, ValueError):
                    pass
                util = None
                try:
                    util = float(card.get("utilization"))
                except (TypeError, ValueError):
                    pass
                if watts:
                    entry["energy_wh"] += watts * gap
                # Busy means actually working. An idle card still draws power
                # and still counts as powered, which are different questions.
                if (util is not None and util >= 10) or (watts and watts > 80):
                    entry["busy_hours"] += gap
            entry["last_seen_at"] = now
            entry["last_seen"] = utc()
            entry["samples"] = entry.get("samples", 0) + 1
            state[key] = entry

    RUNTIME.write_text(json.dumps(state, indent=2))
    return state


def runtime_for(node: str, card: str) -> dict | None:
    if not RUNTIME.is_file():
        return None
    try:
        state = json.loads(RUNTIME.read_text())
    except json.JSONDecodeError:
        return None
    return state.get(f"{node}/{card}")


# ---------------------------------------------------------------- scoring

def item(name: str, status: str, score: int | None, detail: str,
         findings: list[dict] | None = None, readings: list[dict] | None = None) -> dict:
    return {
        "component": name,
        "status": status,          # ok | watch | attention | unknown
        "score": score,            # None when not assessable - never invented
        "detail": detail,
        "findings": findings or [],
        "readings": readings or [],
    }


def finding(what: str, why: str, fix: str, severity: str = "watch") -> dict:
    return {"finding": what, "why": why, "fix": fix, "severity": severity}


def score_cpu(node: str, d: dict) -> dict:
    cpu = d.get("cpu", {})
    cores = []
    package = None
    for chip in d.get("sensors", []):
        if chip["chip"] != "coretemp":
            continue
        for t in chip["temps"]:
            if "Package" in t["label"]:
                package = t
            elif "Core" in t["label"]:
                cores.append(t)
    readings = [{"label": "load (15m)", "value": cpu.get("load_15m")}]
    findings = []
    score = 100

    if package:
        crit = package.get("crit") or package.get("max") or 100
        readings.append({"label": "package temp", "value": f"{package['celsius']}C",
                         "limit": f"{crit}C"})
        headroom = crit - package["celsius"]
        if headroom < 5:
            score -= 45
            findings.append(finding(
                f"Package at {package['celsius']}C, {headroom:.0f}C from its {crit}C limit",
                "At the limit the chip throttles itself, so everything gets slower before "
                "anything looks broken.",
                "Clean the heatsink and case fans first - dust is the usual cause and costs "
                "nothing to rule out. If it is still hot when clean, the paste has dried.",
                "attention"))
        elif headroom < 20:
            score -= 15
            findings.append(finding(
                f"Package at {package['celsius']}C, {headroom:.0f}C of headroom",
                "Working, but with little margin for a hot day or a long render.",
                "Worth a dust-out at the next opportunity.", "watch"))
        delta, note = trend(node, "coretemp/Package id 0", package["celsius"])
        if note:
            score -= 20
            findings.append(finding(
                f"Package temperature {note}",
                "A rising temperature at the same workload is the classic signature of dust "
                "building up or thermal paste drying out. This is the signal worth acting on "
                "early, because it appears months before anything fails.",
                "Clean the heatsink and fans. If the rise persists, replace the thermal paste.",
                "attention"))

    if len(cores) >= 2:
        temps = [c["celsius"] for c in cores]
        spread = round(max(temps) - min(temps), 1)
        idle = (cpu.get("load_15m") or 0) < 0.5
        if spread >= 15 and idle:
            # Seen on serverus: core 0 at 44C with the rest at 28C and the
            # machine doing nothing. That is one core handling interrupts, not
            # a crooked heatsink, and calling it a fault would be the third
            # false alarm in a day.
            readings.append({"label": "core spread",
                             "value": f"{spread}C (at idle - not diagnostic)"})
        elif spread >= 15:
            score -= 25
            findings.append(finding(
                f"{spread}C spread between hottest and coolest core under load",
                "Cores on one die should sit within a few degrees. A wide spread means the "
                "cooler is making uneven contact - crooked mount, or paste that has dried "
                "unevenly.",
                "Reseat the cooler and apply fresh thermal paste.", "attention"))

    throttles = cpu.get("throttle_events_core", 0)
    readings.append({"label": "throttle events", "value": throttles})
    if throttles:
        score -= 30
        findings.append(finding(
            f"CPU has thermally throttled {throttles} times",
            "The chip counted these itself - it got hot enough to slow down to protect "
            "itself. Not a prediction, a record of it already happening.",
            "Clean the cooler and check the case fans are spinning. Repaste if it continues.",
            "attention"))

    score = max(0, min(100, score))
    status = "ok" if score >= 85 else "watch" if score >= 60 else "attention"
    detail = cpu.get("model") or "CPU"
    return item("CPU", status, score, detail, findings, readings)


def score_ram(node: str, d: dict) -> dict:
    mem = d.get("memory", {})
    readings = [
        {"label": "installed", "value": f"{mem.get('total_mb', 0) // 1024} GB"},
        {"label": "available", "value": f"{mem.get('available_mb', 0) // 1024} GB"},
    ]
    findings = []

    for t in mem.get("dimm_temps", []):
        readings.append({"label": f"DIMM {t['label']}", "value": f"{t['celsius']}C"})

    ecc = mem.get("ecc")
    if not ecc:
        # The honest answer, and the most common one on this fleet.
        findings.append(finding(
            "Memory health cannot be assessed on this board",
            "There is no ECC, so the hardware has no way to notice or report a bit error. "
            "Nothing is wrong - it simply cannot be seen from software while the machine "
            "is running.",
            "The only real check is an offline pass of memtest86+ from a USB stick, worth "
            "doing once if this box ever crashes unexplained.",
            "info"))
        return item("RAM", "unknown", None,
                    f"{mem.get('total_mb', 0) // 1024} GB, no ECC", findings, readings)

    total_ce = sum(c.get("corrected", 0) for c in ecc)
    total_ue = sum(c.get("uncorrectable", 0) for c in ecc)
    score = 100
    readings.append({"label": "corrected errors", "value": total_ce})
    readings.append({"label": "uncorrectable", "value": total_ue})

    for c in ecc:
        for rank in c.get("ranks", []):
            label = rank.get("label") or rank.get("slot") or "rank"
            if rank.get("corrected") or rank.get("uncorrectable"):
                readings.append({
                    "label": f"slot {label}",
                    "value": f"{rank.get('corrected', 0)} corrected, "
                             f"{rank.get('uncorrectable', 0)} uncorrectable"})

    if total_ue:
        score -= 70
        bad = [r.get("label") or r.get("slot") for c in ecc for r in c.get("ranks", [])
               if r.get("uncorrectable")]
        findings.append(finding(
            f"{total_ue} uncorrectable memory errors" + (f" on {', '.join(filter(None, bad))}" if bad else ""),
            "ECC caught an error it could not repair. That is a failing module, and it can "
            "corrupt data silently between now and replacement.",
            "Replace the module in that slot. If the slot is unlabelled, swap the two "
            "modules and see whether the errors follow the stick or stay with the slot.",
            "attention"))
    elif total_ce:
        score -= 20
        bad = [r.get("label") or r.get("slot") for c in ecc for r in c.get("ranks", [])
               if r.get("corrected")]
        findings.append(finding(
            f"{total_ce} corrected errors" + (f" on {', '.join(filter(None, bad))}" if bad else ""),
            "ECC found and fixed these, so no data was harmed. A handful over years is "
            "normal; a count that climbs week on week is a module on its way out.",
            "Note the number. If it rises noticeably at the next check, reseat that module, "
            "then replace it if the count keeps climbing.",
            "watch"))

    status = "ok" if score >= 85 else "watch" if score >= 60 else "attention"
    return item("RAM", status, max(0, score),
                f"{mem.get('total_mb', 0) // 1024} GB with ECC", findings, readings)


def score_drives(node: str, d: dict) -> dict:
    st = d.get("storage", {})
    ke = d.get("kernel_events", {})
    disks = st.get("disks", [])
    findings, readings = [], []
    score = 100
    assessable = st.get("smart_available")

    for disk in disks:
        kind = "HDD" if disk.get("rotational") else "SSD"
        readings.append({"label": f"/dev/{disk['device']}",
                         "value": f"{disk['size_gb']} GB {kind}"})
        s = disk.get("smart") or {}
        if s:
            if s.get("power_on_hours"):
                years = s["power_on_hours"] / 8766
                readings.append({"label": f"{disk['device']} powered on",
                                 "value": f"{s['power_on_hours']}h ({years:.1f} yr)"})
                if years >= 5:
                    holds = disk.get("mounts") or []
                    boots = any(m in ("/", "/boot") for m in holds)
                    where = f" carrying {', '.join(holds)}" if holds else ""
                    findings.append(finding(
                        f"/dev/{disk['device']} has {years:.1f} years of runtime{where}",
                        ("This is the drive the machine boots from. Its health counters are "
                         "clean, but at this age a failure takes the whole node down rather "
                         "than costing one filesystem."
                         if boots else
                         "Age alone is not failure - the counters here are clean. Past about "
                         "five years the odds change enough to matter for anything that is "
                         "not copied elsewhere."),
                        ("Keep a copy of the system configuration somewhere else, so this "
                         "machine can be rebuilt rather than reconstructed from memory."
                         if boots else
                         "Check that what it holds exists somewhere else too."),
                        "watch" if boots else "info"))
            for key, label in (("reallocated", "reallocated sectors"),
                               ("pending", "pending sectors"),
                               ("uncorrectable", "uncorrectable sectors")):
                v = s.get(key)
                if isinstance(v, int) and v > 0:
                    score -= 40
                    findings.append(finding(
                        f"/dev/{disk['device']}: {v} {label}",
                        "The drive has found parts of itself it cannot use. This number only "
                        "goes up, and it is the single best warning a disk gives before it "
                        "fails.",
                        "Copy anything important off this drive now, then plan to replace it. "
                        "Do not wait for the number to grow.",
                        "attention"))
            if isinstance(s.get("percent_used"), int) and s["percent_used"] >= 80:
                score -= 25
                findings.append(finding(
                    f"/dev/{disk['device']} is at {s['percent_used']}% of its write endurance",
                    "SSDs wear out by writing. At this point it is near the end of its rated life.",
                    "Plan a replacement. It will usually go read-only rather than die outright.",
                    "watch"))
            if s.get("passed") is False:
                score -= 60
                findings.append(finding(
                    f"/dev/{disk['device']} reports SMART FAILED",
                    "The drive itself is predicting its own failure.",
                    "Replace it now and copy the data off first.", "attention"))

    for m in st.get("mounts", []):
        if m["used_pct"] >= 90:
            score -= 20
            findings.append(finding(
                f"{m['mount']} is {m['used_pct']}% full ({m['free_gb']} GB left)",
                "A filesystem that fills up takes services down with it, and on the root "
                "filesystem it can stop the machine booting.",
                "Clear space, or move the large directories onto one of the spare drives.",
                "attention" if m["used_pct"] >= 95 else "watch"))
        readings.append({"label": m["mount"], "value": f"{m['used_pct']}% used, "
                                                       f"{m['free_gb']} GB free"})

    if st.get("readonly_mounts"):
        score -= 50
        findings.append(finding(
            f"Filesystem remounted read-only: {', '.join(st['readonly_mounts'])}",
            "Linux does this when it sees errors it cannot ignore. It is a failure already "
            "in progress, not a warning.",
            "Check the kernel log for the device, run a filesystem check, and treat the "
            "drive as suspect until proven otherwise.", "attention"))

    if ke.get("readable"):
        if ke.get("io_errors"):
            score -= 35
            findings.append(finding(
                f"{ke['io_errors']} I/O errors in the last 14 days",
                "The kernel failed to read or write a block. Cable, controller or drive.",
                "Reseat the SATA and power cables first - they are free to rule out. If it "
                "persists on the same device, suspect the drive.", "attention"))
        if ke.get("ata_resets"):
            score -= 20
            findings.append(finding(
                f"{ke['ata_resets']} SATA link resets in the last 14 days",
                "The link between board and drive dropped and recovered. Most often a "
                "marginal cable, sometimes a failing port.",
                "Swap the SATA cable, and move the drive to a different port to tell cable "
                "from port.", "watch"))

    # A rescue having run is the loudest thing this page can say: a drive was
    # found failing and the machine already acted on it.
    for dev, r in (d.get("rescue", {}).get("drives") or {}).items():
        why = "; ".join(r.get("reasons", [])) or "failing"
        if r.get("status") == "copied":
            score -= 60
            findings.append(finding(
                f"/dev/{dev} is failing - data was automatically copied off it",
                f"Odris found {why}. Everything mounted on that drive has been copied to "
                f"{r.get('destination')} ({r.get('needed_gb')} GB). The copy is a rescue, "
                f"not a backup - the drive is still failing and still in the machine.",
                "Replace the drive. The rescued copy is on a healthy disk in the same "
                "machine, so it is safe from this failure but not from the next one.",
                "attention"))
        elif r.get("status") == "no_destination":
            score -= 60
            findings.append(finding(
                f"/dev/{dev} is failing and there is nowhere to copy it to",
                f"Odris found {why}, and no healthy disk in this machine has room for the "
                f"{r.get('needed_gb')} GB on it. Nothing has been copied.",
                "Free space on another drive or attach one, then the next check will copy "
                "it automatically. Do this today.",
                "attention"))

    if not assessable and st.get("smart_installed"):
        findings.append(finding(
            "smartmontools is installed but cannot read the drives",
            "Reading a drive's health counters needs root, and this account does not have "
            "permission. The package is there - only the permission is missing.",
            "One line, with the root password: echo \"$USER ALL=(root) NOPASSWD: "
            "/usr/sbin/smartctl\" | sudo tee /etc/sudoers.d/smartctl && sudo chmod 440 "
            "/etc/sudoers.d/smartctl",
            "info"))
        return item("Drives", "watch", None,
                    f"{len(disks)} drives, SMART installed but not permitted",
                    findings, readings)

    if not assessable:
        findings.append(finding(
            "SMART data is not available - the best failure warning is switched off",
            "smartmontools is not installed, so the drives' own health counters cannot be "
            "read. Everything above comes from the filesystem and kernel instead, which only "
            "notice a problem once it is already happening.",
            "One-time setup, needs the root password: "
            "sudo apt install smartmontools, then allow reading without a password with "
            "sudo visudo and a line for smartctl. This is the single biggest improvement "
            "available to this whole health system.",
            "info"))
        status = "unknown" if not findings[:-1] else "watch"
        return item("Drives", status, None,
                    f"{len(disks)} drives, no SMART access", findings, readings)

    score = max(0, min(100, score))
    status = "ok" if score >= 85 else "watch" if score >= 60 else "attention"
    return item("Drives", status, score, f"{len(disks)} drives", findings, readings)


def score_gpu(node: str, d: dict) -> dict:
    cards = d.get("gpu", [])
    if not cards:
        return item("GPU", "unknown", None, "no GPU in this machine", [], [])
    findings, readings = [], []
    score = 100
    for c in cards:
        name = c.get("name") or c.get("chip")
        readings.append({"label": "card", "value": name})
        for t in c.get("temps", []):
            readings.append({"label": t["label"], "value": f"{t['celsius']}C"})
            limit = t.get("crit") or t.get("max") or 90
            if t["celsius"] >= limit - 5:
                score -= 40
                findings.append(finding(
                    f"{name} at {t['celsius']}C, close to its {limit}C limit",
                    "The card will throttle to protect itself, which shows up as generations "
                    "taking longer for no obvious reason.",
                    "Clean the card's fans and heatsink. On a card this age, fresh paste and "
                    "new thermal pads make a large difference.", "attention"))
            elif t["celsius"] >= limit - 20:
                score -= 10
        if c.get("watts"):
            readings.append({"label": "power draw", "value": f"{c['watts']} W"})
        if c.get("vram_total_mb"):
            readings.append({"label": "VRAM",
                             "value": f"{c.get('vram_used_mb')} / {c['vram_total_mb']} MB"})
        if c.get("utilization") is not None:
            readings.append({"label": "utilisation", "value": f"{c['utilization']}%"})
        rt = runtime_for(node, name)
        if rt:
            since = (rt.get("watching_since") or "")[:10]
            readings.append({"label": "hours powered (counted here)",
                             "value": f"{rt['powered_hours']:.1f} h since {since}"})
            readings.append({"label": "hours actually working",
                             "value": f"{rt['busy_hours']:.1f} h"})
            if rt.get("energy_wh"):
                readings.append({"label": "energy used",
                                 "value": f"{rt['energy_wh'] / 1000:.2f} kWh"})
        ecc = c.get("ecc_uncorrected")
        if ecc not in (None, "N/A", "[N/A]", "0"):
            score -= 40
            findings.append(finding(
                f"{name} reports {ecc} uncorrected VRAM errors",
                "Memory on the card is producing errors it cannot fix, which corrupts "
                "whatever it is generating.",
                "Stop using it for anything that matters and test with a memory stress tool.",
                "attention"))
        for f_ in c.get("fans", []):
            readings.append({"label": f"fan {f_['label']}", "value": f"{f_['rpm']} rpm"})
            if f_["rpm"] == 0:
                findings.append(finding(
                    f"{name} fan reading 0 rpm",
                    "Either the card is idle and the fan is stopped by design, which is "
                    "normal, or the fan has failed. The reading alone cannot tell you which.",
                    "Check it by eye while the card is working.", "info"))
    score = max(0, min(100, score))
    status = "ok" if score >= 85 else "watch" if score >= 60 else "attention"
    return item("GPU", status, score, cards[0].get("name") or cards[0].get("chip"),
                findings, readings)


def score_board(node: str, d: dict) -> dict:
    b = d.get("board", {})
    aer = b.get("pcie_errors", {}) or {}
    findings, readings = [], []
    score = 100
    readings.append({"label": "board", "value": " ".join(
        filter(None, [b.get("board_vendor"), b.get("board_name")])) or "unknown"})
    if b.get("bios_date"):
        readings.append({"label": "BIOS", "value": f"{b.get('bios_version')} ({b['bios_date']})"})
    if b.get("chipset_temp") is not None:
        readings.append({"label": "chipset temp", "value": f"{b['chipset_temp']}C"})

    if aer.get("readable"):
        readings.append({"label": "PCIe corrected errors", "value": aer.get("correctable", 0)})
        if aer.get("fatal") or aer.get("nonfatal"):
            score -= 50
            findings.append(finding(
                f"{aer.get('fatal', 0) + aer.get('nonfatal', 0)} fatal PCIe bus errors",
                "A card and the board are failing to talk reliably. On a machine with a GPU "
                "this is the sort of fault that shows up as a crash mid-generation.",
                "Power down, reseat the card, and check the riser if one is fitted. Clean the "
                "slot contacts.", "attention"))
        elif aer.get("correctable", 0) > 100:
            score -= 15
            findings.append(finding(
                f"{aer['correctable']} corrected PCIe errors",
                "The bus is retrying more than it should. Recovered every time so far, but it "
                "is the early form of the fault above.",
                "Reseat the card at the next shutdown.", "watch"))
    else:
        findings.append(finding(
            "PCIe error counters are not exposed by this kernel or board",
            "Bus health cannot be checked here. Not a fault - just not visible.",
            "Nothing to do.", "info"))

    if d.get("kernel_events", {}).get("mce"):
        score -= 40
        findings.append(finding(
            f"{d['kernel_events']['mce']} machine check events logged",
            "The CPU or chipset reported a hardware error to the kernel. These are rare and "
            "always worth reading properly.",
            "Look at the kernel log entries themselves before drawing conclusions - they name "
            "the component.", "attention"))

    score = max(0, min(100, score))
    status = "ok" if score >= 85 else "watch" if score >= 60 else "attention"
    return item("Motherboard", status, score,
                b.get("board_name") or "board", findings, readings)


def score_psu(node: str, d: dict) -> dict:
    p = d.get("power", {})
    findings, readings = [], []

    if p.get("watts") is not None:
        readings.append({"label": "draw at the wall", "value": f"{p['watts']} W"})
    for rail in p.get("rails", []):
        readings.append({"label": rail["label"], "value": f"{rail['volts']} V"})

    if p.get("draw_only"):
        findings.append(finding(
            "Only total draw is visible, not the individual rails",
            "This board reports what the machine pulls at the wall but has no sensors on "
            "the 12V, 5V and 3.3V rails, so the supply's own condition cannot be judged. "
            "The draw figure is still useful: watched over weeks, a rising idle draw is a "
            "sign of a supply losing efficiency.",
            "Nothing to do now. The number is being recorded so the trend exists later.",
            "info"))
        return item("PSU", "unknown", None, f"{p['watts']} W at the wall, rails not visible",
                    findings, readings)

    if not p.get("inspectable"):
        # True of almost every board in this fleet, and worth saying plainly.
        findings.append(finding(
            "The power supply cannot be measured on this board",
            "There is no voltage sensor chip fitted, so the 12V, 5V and 3.3V rails are "
            "invisible to software. This is normal for a desktop board and is not itself a "
            "problem - it just means a failing supply will give no warning here.",
            "The symptoms to watch for are reboots under load with nothing in the logs, and "
            "a failure to power on from cold. A cheap mains power meter at the plug is the "
            "practical way to watch draw over time if you want the data.",
            "info"))
        uptime = d.get("uptime", {})
        if uptime.get("uptime_hours") is not None:
            readings.append({"label": "uptime",
                             "value": f"{uptime['uptime_hours']:.0f} h"})
        return item("PSU", "unknown", None, "not inspectable on this board",
                    findings, readings)

    score = 100
    for rail in p.get("rails", []):
        label, v = rail["label"].lower(), rail["volts"]
        for nominal in (12.0, 5.0, 3.3):
            if str(int(nominal)) in label and abs(v - nominal) / nominal > 0.05:
                score -= 40
                findings.append(finding(
                    f"{rail['label']} reading {v} V against a nominal {nominal} V",
                    "More than 5% off is outside spec. A sagging rail under load is how a "
                    "tired supply announces itself before it takes something with it.",
                    "Replace the power supply. Do not wait - a failing one can damage what it "
                    "is feeding.", "attention"))
    status = "ok" if score >= 85 else "watch" if score >= 60 else "attention"
    detail = (f"{len(p['rails'])} rails within spec" if score == 100
              else "rail out of spec")
    return item("PSU", status, max(0, score), detail, findings, readings)


def score_node(node: str, d: dict) -> dict:
    parts = [
        score_cpu(node, d),
        score_ram(node, d),
        score_drives(node, d),
        score_gpu(node, d),
        score_board(node, d),
        score_psu(node, d),
    ]
    scored = [p["score"] for p in parts if p["score"] is not None]
    # The node score is the worst component, not the average: a machine with a
    # dying disk is not "mostly healthy" because its CPU is cool.
    overall = min(scored) if scored else None
    attention = [p for p in parts if p["status"] == "attention"]
    watch = [p for p in parts if p["status"] == "watch"]
    unknown = [p for p in parts if p["status"] == "unknown"]
    status = ("attention" if attention else "watch" if watch else
              "ok" if scored else "unknown")
    return {
        "node": node,
        "host": d.get("host", node),
        "status": status,
        "score": overall,
        "assessed": len(scored),
        "not_assessable": [p["component"] for p in unknown],
        "summary": (f"{len(attention)} needing attention, {len(watch)} to watch"
                    if attention or watch else
                    ("all measurable parts look fine" if scored else "nothing measurable")),
        "components": parts,
        "uptime_hours": d.get("uptime", {}).get("uptime_hours"),
        "kernel": d.get("kernel"),
    }


def build(raw: dict) -> dict:
    nodes = [score_node(n, d) for n, d in raw.items()]
    order = {"attention": 0, "watch": 1, "unknown": 2, "ok": 3}
    nodes.sort(key=lambda n: (order.get(n["status"], 4), n["score"] if n["score"] is not None else 101))
    worst = nodes[0]["status"] if nodes else "unknown"
    return {
        "at": utc(),
        "fleet_status": worst,
        "nodes_reporting": len(nodes),
        "nodes_expected": len(NODES) + 1,
        "attention": sum(1 for n in nodes for c in n["components"] if c["status"] == "attention"),
        "nodes": nodes,
    }


def refresh() -> dict:
    raw = collect()
    remember(raw)
    accrue_gpu_runtime(raw)
    report = build(raw)
    LATEST.write_text(json.dumps(report, indent=2))
    return report


# ---------------------------------------------------------------- serving

class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok", "service": "fleet health"})
        if self.path in ("/fleet/health", "/"):
            # Served from the last poll so the phone never waits on four SSH
            # round trips; /fleet/health/refresh forces a fresh one.
            if LATEST.is_file():
                return self._send(200, json.loads(LATEST.read_text()))
            return self._send(200, refresh())
        if self.path == "/gpu/runtime":
            state = {}
            if RUNTIME.is_file():
                try:
                    state = json.loads(RUNTIME.read_text())
                except json.JSONDecodeError:
                    pass
            return self._send(200, {
                "note": ("A GPU keeps no lifetime counter of its own, so these "
                         "are hours observed since Odris started watching - not "
                         "the card's total life."),
                "cards": list(state.values())})

        if self.path == "/fleet/health/refresh":
            return self._send(200, refresh())
        return self._send(404, {"error": "not found"})

    def log_message(self, *a):
        pass


def poller() -> None:
    while True:
        try:
            refresh()
        except Exception as e:
            print(f"poll failed: {e}", flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    if "--once" in sys.argv:
        print(json.dumps(refresh(), indent=2))
        sys.exit(0)
    threading.Thread(target=poller, daemon=True).start()
    print(f"fleet health on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
