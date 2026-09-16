#!/usr/bin/env python3
"""Tests for vault.py.

These deliberately attack the vault rather than exercise it. A round trip
proving "it encrypts and decrypts" says almost nothing - the questions worth
answering are whether the plaintext really is absent from the disk, whether a
modified file is refused instead of quietly mis-decrypted, whether one
patient's ciphertext can be moved onto another's record, and whether a backup
actually restores. Every one of those has been a real breach somewhere.

    ./test_vault.py

Runs in a temporary directory. Touches nothing real. The patient is invented.
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

WORK = Path(tempfile.mkdtemp(prefix="vaulttest_"))
os.environ["THUNDER_VAULT"] = str(WORK / "vault")
os.environ["THUNDER_VAULT_KEY"] = str(WORK / "keys" / "vault.key")

sys.path.insert(0, str(Path(__file__).parent))
import vault  # noqa: E402  - env must be set before import

# Entirely fictional. There is no such person, insurer, or claim.
PATIENT = {
    "patient_name": "Marisol Rodriguez",
    "dob": "04/17/1988",
    "phone": "555-0142",
    "address": "88 Fake Street, Nowhere",
    "insurer": "Example Mutual",
    "claim_number": "EM-2026-778120",
    "last_name": "Rodriguez",
    "date_of_injury": "03/02/2026",
    "date_of_service": "03/09/2026",
    "treating_provider": "A. Okonkwo, DC",
    "treating_npi": "1234567893",
    "diagnoses": [{"code": "S13.4", "description": "Sprain of cervical spine"}],
    "procedures": [{"code": "98941", "description": "CMT 3-4 regions", "units": "1"}],
}

PASSED, FAILED = [], []


def check(name: str, condition: bool, detail: str = "") -> None:
    (PASSED if condition else FAILED).append(name)
    print(f"  {'pass' if condition else 'FAIL'}  {name}{('  - ' + detail) if detail else ''}")


def raises(fn) -> tuple[bool, str]:
    try:
        fn()
        return False, "no error raised"
    except BaseException as e:
        return True, f"{type(e).__name__}"


def main() -> int:
    print(f"work dir: {WORK}\n")
    vault.key_init()
    rec = WORK / "claim.json"
    rec.write_text(json.dumps(PATIENT))

    print("\n-- storage --")
    path = vault.put("claim001", PATIENT, ["last_name", "claim_number"])
    check("record written", path.exists())
    check("record is 0600", oct(path.stat().st_mode & 0o777) == "0o600",
          oct(path.stat().st_mode & 0o777))

    raw = path.read_bytes()
    # The point of the whole exercise: none of this may be findable on disk.
    leaks = [s for s in ("Rodriguez", "Marisol", "1988", "EM-2026-778120",
                         "S13.4", "555-0142", "Example Mutual")
             if s.encode() in raw]
    check("no plaintext PHI in the file", not leaks, f"leaked: {leaks}")

    got = vault.get("claim001")
    check("round trip is exact", got == PATIENT)

    print("\n-- tampering --")
    body = json.loads(path.read_text())
    # Flip one bit of ciphertext. GCM must reject it; a cipher without
    # authentication would hand back corrupted records instead.
    ct = bytearray(vault.unb64(body["ct"]))
    ct[len(ct) // 2] ^= 0x01
    tampered = dict(body, ct=vault.b64(bytes(ct)))
    path.write_text(json.dumps(tampered))
    ok, how = raises(lambda: vault.get("claim001"))
    check("one flipped bit is refused", ok, how)
    path.write_text(json.dumps(body))
    check("restored after tamper test", vault.get("claim001") == PATIENT)

    print("\n-- ciphertext relocation --")
    other = dict(PATIENT, patient_name="Someone Else", last_name="Else")
    vault.put("claim002", other, ["last_name"])
    p2 = vault.record_path("claim002")
    b2 = json.loads(p2.read_text())
    # Move claim001's encrypted payload and its key into claim002's file. The
    # record id is authenticated, so this must not open - otherwise one
    # patient's data could be served under another's identity.
    moved = dict(b2, ct=body["ct"], nonce=body["nonce"], dek=body["dek"],
                 wrap_nonce=body["wrap_nonce"], gen=body["gen"])
    p2.write_text(json.dumps(moved))
    ok, how = raises(lambda: vault.get("claim002"))
    check("ciphertext moved to another record is refused", ok, how)
    p2.write_text(json.dumps(b2))

    print("\n-- wrong key --")
    saved = vault.KEYFILE
    alt = WORK / "keys" / "other.key"
    vault.KEYFILE = alt
    vault.key_init()
    ok, how = raises(lambda: vault.get("claim001"))
    check("a different master key cannot open records", ok, how)
    vault.KEYFILE = saved

    print("\n-- key file permissions --")
    os.chmod(vault.KEYFILE, 0o644)
    ok, how = raises(lambda: vault.keys_load())
    check("world-readable key file is refused", ok, how)
    os.chmod(vault.KEYFILE, 0o600)

    print("\n-- blind index --")
    check("exact match found", vault.find("last_name", "Rodriguez") == ["claim001"])
    check("normalised match found", vault.find("last_name", "  rodriguez ") == ["claim001"])
    check("wrong value finds nothing", vault.find("last_name", "Rodrigues") == [])
    token = json.loads(path.read_text())["index"]["last_name"]
    check("index token is not the value",
          "rodriguez" not in token.lower() and len(token) == 32)
    check("unindexed field is not searchable", vault.find("dob", "04/17/1988") == [])

    print("\n-- rotation --")
    before = json.loads(path.read_text())
    vault.rotate()
    after = json.loads(path.read_text())
    check("generation advanced", after["gen"] == before["gen"] + 1)
    # Rewrapping must not touch the record ciphertext - that is what makes
    # rotation cheap enough to do on a schedule.
    check("record ciphertext untouched by rotation", after["ct"] == before["ct"])
    check("wrapped key changed", after["dek"] != before["dek"])
    check("still decrypts after rotation", vault.get("claim001") == PATIENT)
    check("index still works after rotation",
          vault.find("last_name", "Rodriguez") == ["claim001"])
    check("index token was recomputed", after["index"]["last_name"] != token)
    check("verify passes", vault.verify() == 0)

    print("\n-- backup and restore --")
    archive = WORK / "backup.tvb"
    vault.backup(archive, "correct horse battery staple")
    check("archive written", archive.exists())
    check("archive holds no plaintext PHI", b"Rodriguez" not in archive.read_bytes())
    ok, how = raises(lambda: vault.restore(archive, WORK / "bad", "wrong passphrase"))
    check("wrong passphrase is refused", ok, how)
    ok, how = raises(lambda: vault.backup(WORK / "short.tvb", "tooshort"))
    check("short passphrase is refused", ok, how)

    # A modified archive must fail too, including the header - otherwise the
    # scrypt cost could be quietly lowered to make the passphrase guessable.
    bent = WORK / "bent.tvb"
    data = bytearray(archive.read_bytes())
    data[-20] ^= 0x01
    bent.write_bytes(bytes(data))
    ok, how = raises(lambda: vault.restore(bent, WORK / "bad2",
                                           "correct horse battery staple"))
    check("modified archive is refused", ok, how)

    dest = WORK / "restored"
    vault.restore(archive, dest, "correct horse battery staple")
    check("records restored", (dest / "records" / "claim001.rec").exists())
    check("key restored", (dest / "vault.key").exists())

    # The real test of a backup: open it with only what the archive contained.
    vault.VAULT, vault.KEYFILE = dest, dest / "vault.key"
    check("restored vault verifies", vault.verify() == 0)
    check("restored record is byte-identical", vault.get("claim001") == PATIENT)
    vault.VAULT, vault.KEYFILE = WORK / "vault", saved

    print("\n-- audit trail --")
    lines = [json.loads(l) for l in (vault.VAULT / "audit.log").read_text().splitlines()]
    check("failed access is logged",
          any(not l["ok"] and "AUTHENTICATION" in l.get("note", "") for l in lines))
    check("successful reads are logged",
          sum(1 for l in lines if l["action"] == "get" and l["ok"]) >= 3)
    check("rotation is logged", any(l["action"] == "rotate" for l in lines))
    check("audit log carries no patient name",
          "Rodriguez" not in (vault.VAULT / "audit.log").read_text())

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("failed: " + ", ".join(FAILED))
    return 1 if FAILED else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(WORK, ignore_errors=True)
