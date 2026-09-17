#!/usr/bin/env python3
"""When a drive starts failing, get the data off it without being asked.

A drive reporting pending or uncorrectable sectors is not a warning to read in
the morning - it is a fire. The window between the first bad sector and an
unreadable disk can be days, and it can be hours. Waiting for someone to notice
a dashboard is how data gets lost.

So this runs on each node on a timer, looks at its own drives, and if one is
failing it copies what is on it to a healthy disk in the same machine. It runs
on the node rather than from Odris because the data is here and Odris has only
a read-only probe key - detection is Odris's job, acting is the owner's.

WHAT IT WILL NOT DO, because an automatic copy that goes wrong is worse than
no copy at all:

- It never deletes or overwrites anything. Everything lands in a new
  timestamped directory, so a mistake costs disk space and nothing else.
- It refuses a destination on the same physical disk. Copying a dying drive
  onto itself is the most obvious way to achieve nothing.
- It refuses a destination without 25% headroom over what is being copied.
  Filling a healthy disk to rescue a failing one turns one problem into two.
- It will not copy a whole root filesystem. A running OS copied file-by-file
  does not boot and is mostly noise; /etc, /home, /root and /var/log are what
  a rebuild actually needs.
- It tries once per drive per day. A failing disk that cannot be copied will
  not be hammered every half hour.

This is rescue, not backup. It is the thing that happens when the warning
already fired, and it is no substitute for a real copy of anything that
matters.

    ./node_rescue.py --dry-run           what it would do right now
    ./node_rescue.py --simulate sdb      pretend sdb is failing, plan only
    ./node_rescue.py                     act if anything is failing
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
STATE = HOME / "rescue_state.json"
LOG = HOME / "rescue.log"
LOCK = HOME / ".rescue.lock"

HEADROOM = 1.25          # destination must hold this multiple of the data
RETRY_HOURS = 24
# Only what a rebuild needs. Copying a live root filesystem wholesale produces
# something that does not boot and takes hours doing it.
ROOT_PATHS = ["/etc", "/home", "/root", "/var/log", "/var/spool/cron"]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    line = f"{utc()}  {msg}"
    print(line, flush=True)
    try:
        with LOG.open("a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run(cmd: list[str], timeout: int = 30) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def smart_cmd() -> list[str] | None:
    if not run(["which", "smartctl"]):
        return None
    if run(["sudo", "-n", "smartctl", "--version"], timeout=6):
        return ["sudo", "-n", "smartctl"]
    return ["smartctl"] if os.geteuid() == 0 else None


def disks() -> list[str]:
    block = Path("/sys/block")
    return [d.name for d in sorted(block.iterdir())
            if not d.name.startswith(("loop", "ram", "zram", "sr", "dm-"))]


def disk_mounts() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    text = run(["lsblk", "-nro", "KNAME,PKNAME,MOUNTPOINT"])
    if not text:
        return out
    parent, mounted = {}, []
    for line in text.splitlines():
        parts = line.split(None, 2)
        if not parts:
            continue
        k = parts[0]
        pk = parts[1] if len(parts) > 1 and parts[1] else ""
        mp = parts[2].strip() if len(parts) > 2 else ""
        if pk:
            parent[k] = pk
        if mp and mp != "[SWAP]":
            mounted.append((k, mp))
    for k, mp in mounted:
        node = k
        for _ in range(6):
            if node not in parent:
                break
            node = parent[node]
        out.setdefault(node, []).append(mp)
    return out


def assess(dev: str, sc: list[str] | None) -> tuple[str, list[str]]:
    """Is this disk failing? Returns (verdict, reasons).

    Only hard evidence counts. Age is not failure, temperature is not failure,
    and a drive that is merely old must never trigger a copy - the whole design
    depends on this firing rarely and meaning it.
    """
    if not sc:
        return "unknown", ["no SMART access"]
    raw = run(sc + ["-j", "-H", "-A", f"/dev/{dev}"], timeout=30)
    if not raw:
        return "unknown", ["smartctl returned nothing"]
    try:
        s = json.loads(raw)
    except json.JSONDecodeError:
        return "unknown", ["smartctl output unreadable"]

    reasons = []
    if (s.get("smart_status", {}) or {}).get("passed") is False:
        reasons.append("SMART self-assessment FAILED")

    attrs = {}
    for a in (s.get("ata_smart_attributes", {}) or {}).get("table", []):
        attrs[a.get("name")] = (a.get("raw", {}) or {}).get("value")
    for key, why in (("Current_Pending_Sector", "pending sectors"),
                     ("Offline_Uncorrectable", "uncorrectable sectors"),
                     ("Reallocated_Sector_Ct", "reallocated sectors")):
        v = attrs.get(key)
        if isinstance(v, int) and v > 0:
            reasons.append(f"{v} {why}")

    nvme = s.get("nvme_smart_health_information_log", {}) or {}
    if isinstance(nvme.get("percentage_used"), int) and nvme["percentage_used"] >= 95:
        reasons.append(f"{nvme['percentage_used']}% of write endurance used")
    if isinstance(nvme.get("media_errors"), int) and nvme["media_errors"] > 0:
        reasons.append(f"{nvme['media_errors']} media errors")

    return ("failing" if reasons else "ok"), reasons


def readonly_mounts() -> list[str]:
    WRITABLE = {"ext2", "ext3", "ext4", "xfs", "btrfs", "f2fs"}
    out = []
    try:
        for line in Path("/proc/mounts").read_text().splitlines():
            f = line.split()
            if len(f) >= 4 and f[0].startswith("/dev/") and f[2] in WRITABLE:
                if "ro" in f[3].split(","):
                    out.append(f[1])
    except Exception:
        pass
    return out


def usage(path: str) -> tuple[int, int]:
    """(used bytes, free bytes) for the filesystem at path."""
    try:
        st = os.statvfs(path)
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        return total - free, free
    except Exception:
        return 0, 0


def pick_destination(need: int, bad_disk: str, mounts: dict[str, list[str]],
                     failing: set[str]) -> str | None:
    """The roomiest healthy filesystem on a different physical disk."""
    best, best_free = None, 0
    for disk, points in mounts.items():
        if disk == bad_disk or disk in failing:
            continue
        for mp in points:
            if mp in ("/boot", "/boot/efi"):
                continue
            _, free = usage(mp)
            if free < need * HEADROOM:
                continue
            if free > best_free:
                best, best_free = mp, free
    return best


def already_tried(dev: str) -> bool:
    if not STATE.is_file():
        return False
    try:
        state = json.loads(STATE.read_text())
    except Exception:
        return False
    last = state.get(dev, {}).get("last_attempt", 0)
    return (time.time() - last) < RETRY_HOURS * 3600


def record(dev: str, entry: dict) -> None:
    state = {}
    if STATE.is_file():
        try:
            state = json.loads(STATE.read_text())
        except Exception:
            pass
    state[dev] = {**state.get(dev, {}), **entry, "last_attempt": time.time()}
    STATE.write_text(json.dumps(state, indent=2))


def copy(sources: list[str], dest_root: Path, dry: bool) -> dict:
    results = []
    for src in sources:
        name = src.strip("/").replace("/", "_") or "root"
        target = dest_root / name
        cmd = ["rsync", "-aHAX", "--partial", "--info=stats2",
               "--exclude=/proc/*", "--exclude=/sys/*", "--exclude=/dev/*",
               "--exclude=/run/*", "--exclude=lost+found",
               f"{src.rstrip('/')}/", str(target) + "/"]
        # Normal I/O priority on purpose: when a disk is dying, finishing the
        # copy matters more than keeping the machine snappy.
        if shutil.which("ionice"):
            cmd = ["ionice", "-c2", "-n4", "nice", "-n", "5"] + cmd
        if dry:
            log(f"  WOULD COPY {src} -> {target}")
            results.append({"source": src, "target": str(target), "dry_run": True})
            continue
        log(f"  copying {src} -> {target}")
        target.mkdir(parents=True, exist_ok=True)
        started = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=12 * 3600)
            ok = r.returncode in (0, 24)   # 24 = files vanished mid-copy, benign
            results.append({
                "source": src, "target": str(target), "ok": ok,
                "seconds": round(time.time() - started),
                "rsync_exit": r.returncode,
                "error": (r.stderr or "")[-400:] if not ok else None,
            })
            log(f"  {'done' if ok else 'FAILED'} {src} in "
                f"{round(time.time() - started)}s (rsync {r.returncode})")
        except Exception as e:
            results.append({"source": src, "target": str(target), "ok": False,
                            "error": str(e)})
            log(f"  FAILED {src}: {e}")
    return {"copies": results}


def main() -> int:
    dry = "--dry-run" in sys.argv
    simulate = None
    if "--simulate" in sys.argv:
        i = sys.argv.index("--simulate")
        if i + 1 < len(sys.argv):
            simulate = sys.argv[i + 1]
            dry = True          # simulation never writes

    # One at a time. A second run starting while a copy is in flight would
    # fight the first for a disk that is already struggling.
    try:
        import fcntl
        lock = LOCK.open("w")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception:
        log("another rescue is already running; leaving it alone")
        return 0

    sc = smart_cmd()
    mounts = disk_mounts()
    ro = readonly_mounts()
    verdicts = {}
    for dev in disks():
        verdict, reasons = assess(dev, sc)
        if simulate and dev == simulate:
            verdict, reasons = "failing", ["SIMULATED for testing"]
        # A filesystem the kernel forced read-only is failing whatever SMART says.
        for mp in mounts.get(dev, []):
            if mp in ro:
                verdict = "failing"
                reasons = reasons + [f"{mp} remounted read-only by the kernel"]
        verdicts[dev] = (verdict, reasons)

    failing = {d for d, (v, _) in verdicts.items() if v == "failing"}
    if not failing:
        log("all drives ok, nothing to rescue" if not dry else
            "all drives ok (dry run)")
        return 0

    for dev in sorted(failing):
        verdict, reasons = verdicts[dev]
        log(f"DRIVE FAILING: /dev/{dev} - {'; '.join(reasons)}")
        if already_tried(dev) and not dry:
            log(f"  already attempted within {RETRY_HOURS}h, not repeating")
            continue

        points = mounts.get(dev, [])
        if not points:
            log(f"  /dev/{dev} has nothing mounted - nothing to copy")
            record(dev, {"status": "nothing_mounted", "reasons": reasons})
            continue

        # The root filesystem is handled as a set of directories, not wholesale.
        sources: list[str] = []
        for mp in points:
            if mp == "/":
                sources.extend([p for p in ROOT_PATHS if Path(p).is_dir()])
            elif mp in ("/boot", "/boot/efi"):
                continue
            else:
                sources.append(mp)
        if not sources:
            log(f"  nothing worth copying from /dev/{dev}")
            record(dev, {"status": "nothing_to_copy", "reasons": reasons})
            continue

        need = sum(usage(s)[0] if Path(s).is_mount() else
                   sum(f.stat().st_size for f in Path(s).rglob("*")
                       if f.is_file() and not f.is_symlink())
                   for s in sources)
        dest = pick_destination(need, dev, mounts, failing)
        if not dest:
            log(f"  NO SAFE DESTINATION for {need / 1e9:.1f} GB - refusing to copy. "
                f"Free space is needed on a healthy disk in this machine.")
            record(dev, {"status": "no_destination", "reasons": reasons,
                         "needed_gb": round(need / 1e9, 1)})
            continue

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        dest_root = Path(dest) / f"rescue-{os.uname().nodename}-{dev}-{stamp}"
        log(f"  rescuing {need / 1e9:.1f} GB to {dest_root}")
        result = copy(sources, dest_root, dry)
        if not dry:
            record(dev, {"status": "copied", "reasons": reasons,
                         "destination": str(dest_root),
                         "needed_gb": round(need / 1e9, 1), **result})
            log(f"  rescue finished for /dev/{dev}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
