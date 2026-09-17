#!/usr/bin/env python3
"""Copy the things that exist in exactly one place, encrypted, to another machine.

The repository is on GitHub, so the code is safe. Everything that makes this
fleet *this* fleet is not: the vault master key, the TLS certificate authority,
Thunder's memory and profile, the code vault, the audit log, the bearer tokens.
All of it on one 2014 desktop with four drives and no copy anywhere.

Serverus has five terabytes of empty storage and a different set of disks in a
different box. That is the whole idea.

**The archive is encrypted, and that is not optional.** It contains the vault
master key and the CA private key. Writing it to serverus in the clear would
mean serverus silently holds the keys to the claims data and the ability to
impersonate Main to the phone. Encrypted, a stolen serverus is a stolen box of
noise.

**The passphrase lives on Main and nowhere else.** That is the honest trade: it
makes the nightly run unattended, and it means an attacker who takes serverus
gets nothing. It also means that if Main's disk dies and you have not written
the passphrase down somewhere physical, the backups are scrap. Write it down.

A backup that has never been restored is a rumour, so --verify does a real one:
fetches the newest archive back, decrypts it, unpacks it, and checks the vault
key it contains actually opens a record.

    ./backup.py                 run one now
    ./backup.py --verify        prove the newest archive restores
    ./backup.py --list          what exists, where, how old
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import secrets
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HERE = Path(__file__).parent
DATA = HERE / "thunder-data"
PASSPHRASE_FILE = Path(os.path.expanduser("~")) / ".thunder" / "backup.pass"
MAGIC = b"THUNDERBACKUP1\n"
SCRYPT = {"n": 2 ** 16, "r": 8, "p": 1, "dklen": 32}
MAXMEM = 128 * 1024 * 1024

# Two machines, because one remote copy is one failure away from none.
# Candidate folders per node, best first: a big data drive beats a home
# directory, because on serverus the home directory sits on sda - the
# six-year-old disk the machine boots from, which is the last place a backup
# should live. Whichever is writable wins, and if only home is, it is used with
# a warning rather than failing.
DESTINATION_CANDIDATES = {
    "serverus": ["/mnt/bulk/thunder-backups", "/mnt/archive/thunder-backups",
                 "/mnt/cache3/thunder-backups", "~/thunder-backups"],
    "thunder-engine": ["~/thunder-backups"],
}
KEEP = 14

# What cannot be reconstructed. Deliberately not "everything" - the generated
# media is large and reproducible, and a backup big enough to be a chore is a
# backup that gets turned off.
SOURCES = [
    (Path(os.path.expanduser("~")) / ".thunder" / "keys", "keys"),
    (DATA / "memory", "memory"),
    (DATA / "code", "code"),
    (DATA / "tls", "tls"),
    (DATA / "tokens.json", "tokens.json"),
    (DATA / "audit.log", "audit.log"),
    (DATA / "app_release.json", "app_release.json"),
    (HERE.parent / "thunder-claims" / "vault", "claims_vault"),
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def passphrase() -> str:
    """Read it, or make one on first run and tell him to write it down."""
    if PASSPHRASE_FILE.is_file():
        return PASSPHRASE_FILE.read_text().strip()
    PASSPHRASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(PASSPHRASE_FILE.parent, 0o700)
    # Six words from a generous alphabet: long enough that scrypt at these
    # parameters makes guessing hopeless, short enough to copy onto paper.
    words = "-".join(secrets.token_hex(3) for _ in range(6))
    fd = os.open(PASSPHRASE_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(words)
    print("=" * 66)
    print("A backup passphrase has been generated. WRITE IT DOWN ON PAPER:\n")
    print(f"    {words}\n")
    print("It lives at ~/.thunder/backup.pass on Main and nowhere else.")
    print("If Main's disk dies and this is not written down, every backup")
    print("it has made is unreadable. That is the whole point of it being")
    print("encrypted, and the whole risk of it being automatic.")
    print("=" * 66)
    return words


def build_archive() -> tuple[bytes, list[str]]:
    buf = io.BytesIO()
    included = []
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, name in SOURCES:
            if path.exists():
                tar.add(path, arcname=name)
                included.append(name)
    return buf.getvalue(), included


def encrypt(raw: bytes, phrase: str) -> bytes:
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    header = json.dumps({"kdf": "scrypt", **SCRYPT, "salt": salt.hex(),
                         "nonce": nonce.hex(), "at": utc()}).encode()
    key = hashlib.scrypt(phrase.encode(), salt=salt, maxmem=MAXMEM, **SCRYPT)
    # The header is authenticated, so nobody can weaken the scrypt parameters
    # and then attack the passphrase cheaply.
    ct = AESGCM(key).encrypt(nonce, raw, header)
    return MAGIC + len(header).to_bytes(4, "big") + header + ct


def decrypt(blob: bytes, phrase: str) -> bytes:
    if not blob.startswith(MAGIC):
        raise ValueError("not a Thunder backup")
    off = len(MAGIC)
    hlen = int.from_bytes(blob[off:off + 4], "big")
    header = blob[off + 4:off + 4 + hlen]
    ct = blob[off + 4 + hlen:]
    meta = json.loads(header)
    params = {k: meta[k] for k in ("n", "r", "p", "dklen")}
    key = hashlib.scrypt(phrase.encode(), salt=bytes.fromhex(meta["salt"]),
                         maxmem=MAXMEM, **params)
    return AESGCM(key).decrypt(bytes.fromhex(meta["nonce"]), ct, header)


def ssh(node: str, cmd: str, stdin: bytes | None = None, timeout: int = 600):
    r = subprocess.run(["ssh", "-n" if stdin is None else "-T",
                        "-o", "BatchMode=yes", node, cmd],
                       input=stdin, capture_output=True, timeout=timeout)
    return r.returncode == 0, r.stdout, r.stderr.decode(errors="replace")[-300:]


def destinations() -> list[tuple[str, str, bool]]:
    """(node, folder, is_fallback) - the first candidate this node can write to."""
    out = []
    for node, candidates in DESTINATION_CANDIDATES.items():
        chosen, fallback = None, False
        for folder in candidates:
            ok, _, _ = ssh(node, f"mkdir -p {folder} 2>/dev/null && "
                                 f"test -w {folder} && echo ok", timeout=25)
            if ok:
                chosen = folder
                fallback = folder.startswith("~")
                break
        if chosen:
            out.append((node, chosen, fallback))
        else:
            print(f"  {node}: nowhere writable found")
    return out


def push(blob: bytes, name: str) -> list[dict]:
    out = []
    for node, folder, fallback in destinations():
        if fallback and node == "serverus":
            print(f"  ! {node}: only the home directory is writable, and that "
                  f"lives on the drive it boots from.\n"
                  f"    For a copy on a different disk, once:\n"
                  f"      ssh {node} \"sudo mkdir -p /mnt/bulk/thunder-backups "
                  f"&& sudo chown \\$USER /mnt/bulk/thunder-backups\"")
        ok, _, err = ssh(node, f"chmod 700 {folder} 2>/dev/null; "
                               f"cat > {folder}/{name} && chmod 600 {folder}/{name}",
                         stdin=blob)
        out.append({"node": node, "path": f"{folder}/{name}", "ok": ok,
                    "error": None if ok else err})
        print(f"  {'sent to' if ok else 'FAILED  '} {node}:{folder}/{name}"
              f"{'' if ok else '  ' + err}")
        if ok:
            # Keep the last KEEP, delete the rest. Unbounded backups fill the
            # disk and then the next one fails silently.
            ssh(node, f"ls -1t {folder}/thunder-*.tbk 2>/dev/null | "
                      f"tail -n +{KEEP + 1} | xargs -r rm -f")
    return out


def newest_remote() -> tuple[str, str] | None:
    for node, folder, _ in destinations():
        ok, out, _ = ssh(node, f"ls -1t {folder}/thunder-*.tbk 2>/dev/null | head -1")
        name = out.decode().strip()
        if ok and name:
            return node, name
    return None


def verify() -> int:
    """Fetch the newest archive, decrypt it, and prove the key inside works.

    Checking that a file exists is not verification. This unpacks it and uses
    the vault key it contains to open a real record, which is the only claim
    worth making about a backup.
    """
    target = newest_remote()
    if not target:
        print("no backups found on any destination")
        return 1
    node, path = target
    print(f"verifying {node}:{path}")
    ok, blob, err = ssh(node, f"cat {path}")
    if not ok or not blob:
        print(f"  could not fetch it: {err}")
        return 1
    print(f"  fetched {len(blob) / 1024:.0f} KB")

    try:
        raw = decrypt(blob, passphrase())
    except Exception as e:
        print(f"  DECRYPT FAILED: {e}")
        return 1
    print("  decrypted")

    work = Path(tempfile.mkdtemp(prefix="verify_"))
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
            for m in tar.getmembers():
                if ".." in Path(m.name).parts or m.issym() or m.islnk():
                    print(f"  refusing unsafe entry {m.name}")
                    return 1
            tar.extractall(work, filter="data")
        names = sorted(p.name for p in work.iterdir())
        print(f"  unpacked: {', '.join(names)}")

        key = work / "keys" / "vault.key"
        records = work / "claims_vault" / "records"
        if not key.is_file():
            print("  NO VAULT KEY IN THE ARCHIVE - restoring this would not "
                  "recover the claims")
            return 1
        os.chmod(key, 0o600)
        if records.is_dir() and any(records.glob("*.rec")):
            sys.path.insert(0, str(HERE.parent / "thunder-claims"))
            import vault as v
            v.VAULT, v.KEYFILE = work / "claims_vault", key
            one = next(records.glob("*.rec")).stem
            claim = v.get(one)
            print(f"  the key in this archive opened {one}: "
                  f"{len(claim)} fields recovered")
        else:
            print("  (no claims in the vault yet - key present and readable)")
        print("\nRestore verified. This archive is a real recovery, not a file "
              "that happens to exist.")
        return 0
    finally:
        subprocess.run(["rm", "-rf", str(work)], check=False)


def listing() -> int:
    for node, folder, _ in destinations():
        ok, out, _ = ssh(node, f"ls -lht {folder}/thunder-*.tbk 2>/dev/null | head -5")
        print(f"{node}:{folder}")
        text = out.decode(errors="replace").strip()
        print("\n".join(f"  {l}" for l in text.splitlines()) if text else "  (none)")
    return 0


def main() -> int:
    if "--verify" in sys.argv:
        return verify()
    if "--list" in sys.argv:
        return listing()

    phrase = passphrase()
    raw, included = build_archive()
    blob = encrypt(raw, phrase)
    name = f"thunder-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}.tbk"
    print(f"{len(included)} items, {len(blob) / 1024:.0f} KB encrypted")
    print(f"  {', '.join(included)}")
    results = push(blob, name)
    sent = sum(1 for r in results if r["ok"])
    (DATA / "backup_state.json").write_text(json.dumps(
        {"at": utc(), "archive": name, "bytes": len(blob),
         "included": included, "destinations": results}, indent=2))
    if sent == 0:
        print("\nNOTHING WAS COPIED. The backup exists nowhere.")
        return 1
    print(f"\ncopied to {sent} of {len(DESTINATION_CANDIDATES)} machines")
    if sent < len(DESTINATION_CANDIDATES):
        print("One destination failed. One copy is one failure from none.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
