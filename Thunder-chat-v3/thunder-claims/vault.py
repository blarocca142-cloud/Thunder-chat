#!/usr/bin/env python3
"""Encrypted record store for claims.

Every claims system worth using is somebody else's cloud, which means a
business associate agreement and PHI on a disk you do not own. This is the
other option: the records live on a machine the family owns, and they are
encrypted there, individually, so that the disk being stolen or resold or
handed to a repair shop is not a breach.

Design, and why:

**Envelope encryption.** Each record gets its own data key (DEK), and that key
is wrapped by a master key (KEK) held in a separate file. Rotating the master
key then rewraps a few hundred small keys instead of re-encrypting every
record - which is the difference between rotation being routine and rotation
never happening.

**AES-256-GCM everywhere.** Authenticated, so tampering fails loudly rather
than returning quietly wrong data. The record id is mixed in as associated
data, so an attacker cannot swap one patient's ciphertext for another's and
have it still decrypt.

**Blind indexes.** Records are opaque, which would normally mean you cannot
look anything up without decrypting everything. Instead each indexed field
stores an HMAC of its normalised value under a key derived separately from the
KEK. Exact-match lookup works without decrypting a single record. Read the
honest limits of this in the README - it leaks equality, and it is not a
substitute for encryption.

**Audit on every access.** HIPAA wants access recorded, and it is also just
useful: the log is the only way to answer "what did this account read".

Threat model, stated plainly because it is easy to oversell:

- Protected: a powered-off disk, a discarded drive, a stolen backup, a file
  copied out by something with no business reading it, a cloud sync that gets
  hold of the record files.
- **Not** protected: root on this box while it is running. The service must be
  able to read the key, therefore so can root. Encryption at rest is not a
  defence against a live compromise, and nothing here pretends otherwise.

    ./vault.py init
    ./vault.py put claim001 claim.json --index last_name --index claim_number
    ./vault.py get claim001
    ./vault.py find last_name Rodriguez
    ./vault.py verify
    ./vault.py rotate
    ./vault.py backup /media/usb/vault-2026-09-16.tvb
    ./vault.py restore /media/usb/vault-2026-09-16.tvb /tmp/restored
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import io
import json
import os
import secrets
import sys
import tarfile
import threading
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

sys.path.insert(0, str(Path(__file__).parent))
import store  # noqa: E402  where the sealed records live: files or PostgreSQL
from store import RevConflict  # noqa: E402,F401

VAULT = Path(os.environ.get("THUNDER_VAULT", Path(__file__).parent / "vault"))
# The key does NOT live in the vault. If it did, a stolen copy of the data
# directory would carry its own key and this would all be decoration.
KEYFILE = Path(os.environ.get(
    "THUNDER_VAULT_KEY", Path.home() / ".thunder" / "keys" / "vault.key"))

RECORD_VERSION = 1
# ~64MB and a second or so per attempt. Chosen to make a stolen backup
# expensive to attack offline; raise it, never lower it.
SCRYPT = {"n": 2 ** 16, "r": 8, "p": 1, "dklen": 32}
# OpenSSL refuses over 32MB by default, which is below the parameters above.
# This is only a library guard - it does not affect the derived key, so it is
# not stored in the backup header, just applied at both ends.
MAXMEM = 128 * 1024 * 1024
BACKUP_MAGIC = b"THUNDERVAULT1\n"


def b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def unb64(s: str) -> bytes:
    return base64.b64decode(s)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# keys
# --------------------------------------------------------------------------

def key_init(force: bool = False) -> None:
    if KEYFILE.exists() and not force:
        raise SystemExit(
            f"{KEYFILE} already exists. Overwriting it makes every existing\n"
            f"record permanently unreadable. Pass --force only if you mean it.")
    KEYFILE.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(KEYFILE.parent, 0o700)
    payload = {"version": 1, "generation": 1, "keys": {"1": b64(secrets.token_bytes(32))}}
    # Create with 0600 from the start rather than chmod after: between write
    # and chmod the key would be world-readable, which is a real if brief hole.
    fd = os.open(KEYFILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"created {KEYFILE}  (generation 1)")
    print("\nBack this file up somewhere off this machine, encrypted.")
    print("Lose it and the records are gone - there is no recovery path, by design.")


def keys_load() -> tuple[dict[str, bytes], str]:
    if not KEYFILE.exists():
        raise SystemExit(f"no key at {KEYFILE} - run: vault.py init")
    mode = KEYFILE.stat().st_mode & 0o777
    if mode & 0o077:
        raise SystemExit(
            f"{KEYFILE} is mode {mode:o} - readable by other accounts.\n"
            f"Fix with: chmod 600 {KEYFILE}")
    data = json.loads(KEYFILE.read_text())
    return ({g: unb64(k) for g, k in data["keys"].items()},
            str(data["generation"]))


def derive(kek: bytes, purpose: str) -> bytes:
    """One master key, separate subkeys per job. Reusing a key for wrapping and
    for indexing is how a weakness in one becomes a weakness in both."""
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                info=purpose.encode()).derive(kek)


# --------------------------------------------------------------------------
# blind index
# --------------------------------------------------------------------------

def normalize(value: str) -> str:
    """Lookup has to survive how the value was typed. 'Rodriguez ' and
    'rodriguez' must land on the same token or the index finds nothing."""
    s = unicodedata.normalize("NFKD", str(value))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def blind(index_key: bytes, field: str, value: str) -> str:
    token = f"{field}:{normalize(value)}".encode()
    return hmac.new(index_key, token, hashlib.sha256).hexdigest()[:32]


# --------------------------------------------------------------------------
# audit
# --------------------------------------------------------------------------

_actor = threading.local()
_root = threading.local()


def set_root(path) -> None:
    """Point this thread at one company's vault (EZClaim's "company file").
    The claims server serves several companies from one process; each
    request is pinned to the one its session opened. None = THUNDER_VAULT."""
    _root.path = Path(path) if path else None


def root() -> Path:
    return getattr(_root, "path", None) or VAULT


def set_actor(name: str | None) -> None:
    """Name the person behind the calls this thread makes, for the audit log.
    The claims server serves several logged-in people from one process, so
    the Unix account alone would credit every access to the same user."""
    _actor.name = name


def audit(action: str, record: str, ok: bool, note: str = "") -> None:
    """Record ids and actions only. Putting the patient's name in the audit log
    would mean the log itself is PHI sitting in plaintext."""
    line = {
        "at": now(),
        "who": getattr(_actor, "name", None) or os.environ.get("THUNDER_USER") or getpass.getuser(),
        "pid": os.getpid(),
        "action": action,
        "record": record,
        "ok": ok,
        "note": note,
    }
    store.current().audit(scope(), line)


def audit_lines() -> list[dict]:
    return store.current().audit_lines(scope())


# --------------------------------------------------------------------------
# records
# --------------------------------------------------------------------------

def _who() -> str:
    return getattr(_actor, "name", None) or ""


def scope_for(path) -> object:
    """The store scope of one company's folder (see scope())."""
    old = getattr(_root, "path", None)
    set_root(path)
    try:
        return scope()
    finally:
        _root.path = old


def scope():
    """The current company in the store's terms: its folder for files, its
    schema for PostgreSQL (c__main for the original vault, c_<name> for the
    others - company names are letters, digits and underscores, unique
    ignoring case, so the schema names cannot collide)."""
    st = store.current()
    if st.kind == "files":
        return root()
    r = root()
    if r.resolve() == VAULT.resolve():
        return "c__main"
    return "c_" + r.name.lower()


def records_dir() -> Path:
    """Files backend only - the folder the .rec files are in."""
    d = root() / "records"
    d.mkdir(parents=True, exist_ok=True)
    return d


def record_path(record_id: str) -> Path:
    """Files backend only."""
    if not record_id or "/" in record_id or record_id.startswith("."):
        raise SystemExit(f"bad record id: {record_id!r}")
    return records_dir() / f"{record_id}.rec"


def _check_id(record_id: str) -> None:
    if not record_id or "/" in record_id or record_id.startswith(".") or len(record_id) > 120:
        raise SystemExit(f"bad record id: {record_id!r}")


def exists(record_id: str) -> bool:
    _check_id(record_id)
    return store.current().exists(scope(), record_id)


def ids() -> list[str]:
    """Every record id, most recently saved first. Nothing decrypted."""
    return store.current().ids(scope())


def raw(record_id: str) -> str | None:
    """The sealed envelope exactly as stored - ciphertext only."""
    _check_id(record_id)
    return store.current().read(scope(), record_id)


def deleted_bodies(record_id: str) -> list[str]:
    _check_id(record_id)
    return store.current().deleted(scope(), record_id)


def rev_of(record_id: str) -> int:
    """The record's revision counter without decrypting it (records written
    before the counter was kept outside the ciphertext are opened once)."""
    _check_id(record_id)
    r = store.current().rev(scope(), record_id)
    if r is not None:
        return int(r)
    if not exists(record_id):
        return 0
    try:
        return int((get(record_id).get("_rev") or {}).get("n") or 0)
    except BaseException:
        return 0


@contextmanager
def transaction():
    """All the writes inside happen together or not at all (PostgreSQL), or
    with no other save in between (files)."""
    with store.current().transaction(scope()):
        yield


def put(record_id: str, obj: dict, index_fields: list[str], expect_rev: int | None = None) -> str:
    """Seal and store one record. With expect_rev, the save only happens if
    the stored record is still at that revision (RevConflict otherwise) - the
    check and the write are one step, so two people cannot both win."""
    _check_id(record_id)
    keys, gen = keys_load()
    kek = keys[gen]
    created = now()
    old = store.current().read(scope(), record_id)
    if old is not None:
        created = json.loads(old).get("created", created)

    dek = secrets.token_bytes(32)
    plaintext = json.dumps(obj, separators=(",", ":")).encode()

    # The record id is authenticated, not just encrypted, so a ciphertext
    # moved to another record's file fails to open instead of silently
    # attributing one patient's data to another.
    rec_nonce = secrets.token_bytes(12)
    ct = AESGCM(dek).encrypt(
        rec_nonce, plaintext, f"{record_id}|{RECORD_VERSION}".encode())

    # Generation is authenticated in the wrap so a rotated key cannot be
    # replayed against an old wrapper.
    wrap_nonce = secrets.token_bytes(12)
    wrapped = AESGCM(derive(kek, "vault/wrap")).encrypt(
        wrap_nonce, dek, f"{record_id}|{gen}".encode())

    rev = int((obj.get("_rev") or {}).get("n") or 0) if isinstance(obj.get("_rev"), dict) else 0
    index_key = derive(kek, "vault/index")
    index = {}
    for field in index_fields:
        value = obj.get(field)
        if isinstance(value, str) and value.strip():
            index[field] = blind(index_key, field, value)

    body = {
        "id": record_id,
        "v": RECORD_VERSION,
        "gen": int(gen),
        "created": created,
        "updated": now(),
        "wrap_nonce": b64(wrap_nonce),
        "dek": b64(wrapped),
        "nonce": b64(rec_nonce),
        "ct": b64(ct),
        "index": index,
        # The revision counter also sits outside the ciphertext so the store
        # can check it without a key. It is not trusted for anything else:
        # the authoritative _rev is inside, under the record's GCM tag.
        "rev": rev,
    }
    try:
        # Atomic either way: a crash mid-write leaves the old record intact,
        # never a half-written one that will not decrypt.
        store.current().write(scope(), record_id, json.dumps(body, indent=2), rev, expect_rev, _who())
    except RevConflict:
        audit("put", record_id, False, f"stale save refused (expected rev {expect_rev})")
        raise
    audit("put", record_id, True, f"indexed:{','.join(index) or 'none'}")
    return record_id


def get(record_id: str) -> dict:
    keys, _ = keys_load()
    _check_id(record_id)
    text = store.current().read(scope(), record_id)
    if text is None:
        audit("get", record_id, False, "not found")
        raise SystemExit(f"no such record: {record_id}")
    body = json.loads(text)
    if body.get("id") != record_id:
        audit("get", record_id, False, "AUTHENTICATION FAILED")
        raise SystemExit(f"record {record_id} failed authentication (it holds another record's envelope).")
    gen = str(body["gen"])
    if gen not in keys:
        audit("get", record_id, False, f"no key for generation {gen}")
        raise SystemExit(
            f"record {record_id} is wrapped with key generation {gen}, which is\n"
            f"not in {KEYFILE}. A retired key was removed too early.")
    try:
        dek = AESGCM(derive(keys[gen], "vault/wrap")).decrypt(
            unb64(body["wrap_nonce"]), unb64(body["dek"]),
            f"{record_id}|{gen}".encode())
        plaintext = AESGCM(dek).decrypt(
            unb64(body["nonce"]), unb64(body["ct"]),
            f"{record_id}|{body['v']}".encode())
    except Exception:
        # GCM failing means wrong key or altered bytes. Both are worth an
        # alarm, and neither should be reported as "empty record".
        audit("get", record_id, False, "AUTHENTICATION FAILED")
        raise SystemExit(
            f"record {record_id} failed authentication.\n"
            f"Either the key is wrong or the file has been modified. It has NOT\n"
            f"been decrypted, and this is logged.")
    audit("get", record_id, True)
    return json.loads(plaintext)


def retire(record_id: str) -> str:
    """Delete, the recoverable way: the still-encrypted record moves to
    deleted/ (or the deleted table) with a timestamp, and the audit log says
    who did it. Nothing is decrypted and nothing is shredded - a mistaken
    delete can be put back."""
    if not exists(record_id):
        audit("delete", record_id, False, "no such record")
        raise SystemExit(f"no such record: {record_id}")
    where = store.current().retire(scope(), record_id, _who())
    audit("delete", record_id, True, where)
    return where


def bodies():
    """(id, envelope dict) for every record - ciphertext only."""
    st, sc = store.current(), scope()
    for rid in sorted(st.ids(sc)):
        text = st.read(sc, rid)
        if text is not None:
            yield rid, json.loads(text)


def find(field: str, value: str) -> list[str]:
    """Exact-match lookup with nothing decrypted."""
    keys, gen = keys_load()
    want = blind(derive(keys[gen], "vault/index"), field, value)
    hits = [rid for rid, b in bodies() if b.get("index", {}).get(field) == want]
    audit("find", f"{field}={len(hits)} hits", True)
    return hits


def verify() -> int:
    """Open every record. The only honest way to know the vault is intact and
    the keys still work - and the thing to run before trusting a backup."""
    keys, _ = keys_load()
    ok = bad = 0
    for rid, body in bodies():
        try:
            if body.get("id") != rid:
                raise ValueError("envelope belongs to another record")
            gen = str(body["gen"])
            dek = AESGCM(derive(keys[gen], "vault/wrap")).decrypt(
                unb64(body["wrap_nonce"]), unb64(body["dek"]),
                f"{body['id']}|{gen}".encode())
            AESGCM(dek).decrypt(unb64(body["nonce"]), unb64(body["ct"]),
                                f"{body['id']}|{body['v']}".encode())
            ok += 1
        except Exception as e:
            bad += 1
            print(f"  FAIL {rid}: {type(e).__name__}")
    audit("verify", f"{ok} ok / {bad} failed", bad == 0)
    print(f"{ok} records verified, {bad} failed")
    return 1 if bad else 0


def rotate(drop_old: bool = False) -> None:
    """New master key generation; rewrap every DEK under it.

    Record ciphertexts are untouched, which is what makes this cheap enough to
    actually do. The old generation is kept by default so that a backup taken
    before the rotation still restores.
    """
    data = json.loads(KEYFILE.read_text())
    keys = {g: unb64(k) for g, k in data["keys"].items()}
    old_gen = str(data["generation"])
    new_gen = str(int(old_gen) + 1)
    new_kek = secrets.token_bytes(32)
    keys[new_gen] = new_kek

    new_wrap = derive(new_kek, "vault/wrap")
    new_index = derive(new_kek, "vault/index")
    moved = 0
    st, sc = store.current(), scope()
    for rid, body in bodies():
        gen = str(body["gen"])
        dek = AESGCM(derive(keys[gen], "vault/wrap")).decrypt(
            unb64(body["wrap_nonce"]), unb64(body["dek"]),
            f"{body['id']}|{gen}".encode())
        nonce = secrets.token_bytes(12)
        body["wrap_nonce"] = b64(nonce)
        body["dek"] = b64(AESGCM(new_wrap).encrypt(
            nonce, dek, f"{body['id']}|{new_gen}".encode()))
        body["gen"] = int(new_gen)
        # Index tokens are keyed off the KEK, so they have to be recomputed -
        # which needs the plaintext. Same cost as a decrypt, once.
        if body.get("index"):
            obj = json.loads(AESGCM(dek).decrypt(
                unb64(body["nonce"]), unb64(body["ct"]),
                f"{body['id']}|{body['v']}".encode()))
            body["index"] = {f: blind(new_index, f, obj[f])
                             for f in body["index"] if isinstance(obj.get(f), str)}
        st.write(sc, rid, json.dumps(body, indent=2), int(body.get("rev") or 0))
        moved += 1

    if drop_old:
        keys = {new_gen: new_kek}
    data = {"version": 1, "generation": int(new_gen),
            "keys": {g: b64(k) for g, k in keys.items()}}
    fd = os.open(KEYFILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    audit("rotate", f"generation {old_gen} -> {new_gen}", True, f"{moved} records")
    print(f"rotated to generation {new_gen}, rewrapped {moved} records")
    if drop_old:
        print("old generations dropped - backups taken before now will NOT restore")


# --------------------------------------------------------------------------
# move a company from files to PostgreSQL
# --------------------------------------------------------------------------

def _open(body: dict, keys: dict) -> dict:
    gen = str(body["gen"])
    dek = AESGCM(derive(keys[gen], "vault/wrap")).decrypt(
        unb64(body["wrap_nonce"]), unb64(body["dek"]), f"{body['id']}|{gen}".encode())
    return json.loads(AESGCM(dek).decrypt(
        unb64(body["nonce"]), unb64(body["ct"]), f"{body['id']}|{body['v']}".encode()))


def migrate_to_db() -> dict:
    """Copy this company's records, deleted records and audit log from its
    folder into PostgreSQL, byte for byte - still sealed, nothing re-encrypted.
    Then check: same ids, identical envelopes, every record opens. The files
    are left exactly where they were; deleting them is a separate decision."""
    pg = store.current()
    if pg.kind != "postgresql":
        raise SystemExit("set THUNDER_VAULT_DB to the PostgreSQL database first")
    fs, src, sc = store.FileStore(), root(), scope()
    if not (src / "records").is_dir():
        raise SystemExit(f"{src} has no records/ folder - nothing to move")
    if pg.ids(sc):
        raise SystemExit(f"{sc} in the database already has records - not mixing two copies")
    keys, _ = keys_load()
    rids = sorted(fs.ids(src), key=lambda r: (src / "records" / f"{r}.rec").stat().st_mtime)
    with pg.transaction(sc):
        for rid in rids:   # oldest first, so the newest-first order carries over
            text = fs.read(src, rid)
            body = json.loads(text)
            rev = body.get("rev")
            if rev is None:  # saved before the counter lived outside the ciphertext
                rev = int((_open(body, keys).get("_rev") or {}).get("n") or 0)
            pg.write(sc, rid, text, int(rev))
            pg._run(f"UPDATE {sc}.records SET updated = to_timestamp(:t) WHERE id = :id",
                    t=(src / "records" / f"{rid}.rec").stat().st_mtime, id=rid)
        dd = src / "deleted"
        ndel = 0
        for f in sorted(dd.glob("*.rec")) if dd.exists() else []:
            rid, ts = f.name[:-4].rsplit(".", 1)
            at = datetime.strptime(ts, "%Y%m%d-%H%M%S").astimezone(timezone.utc)
            pg._run(f"INSERT INTO {sc}.deleted (id, at, who, body) VALUES (:id, :at, '', :b)",
                    id=rid, at=at, b=f.read_text())
            ndel += 1
        lines = fs.audit_lines(src)
        for line in lines:
            pg._run(f"INSERT INTO {sc}.audit (line) VALUES (CAST(:l AS jsonb))", l=json.dumps(line))
    # check, from the database's side
    if sorted(pg.ids(sc)) != sorted(rids):
        raise SystemExit("MIGRATION CHECK FAILED: the database does not hold the same records")
    for rid in rids:
        if pg.read(sc, rid) != fs.read(src, rid):
            raise SystemExit(f"MIGRATION CHECK FAILED: {rid} differs")
        _open(json.loads(pg.read(sc, rid)), keys)
    out = {"schema": sc, "records": len(rids), "deleted": ndel, "audit": len(lines)}
    audit("migrate", f"{len(rids)} records to {sc}", True, f"{ndel} deleted, {len(lines)} audit lines")
    return out


# --------------------------------------------------------------------------
# backup
# --------------------------------------------------------------------------

def _backup_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.scrypt(passphrase.encode(), salt=salt, maxmem=MAXMEM, **SCRYPT)


def _tar_bytes(tar, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o600
    info.mtime = int(datetime.now().timestamp())
    tar.addfile(info, io.BytesIO(data))


def backup(out: Path, passphrase: str | None = None) -> None:
    """One passphrase-encrypted file holding the records AND the key.

    A backup without the key restores nothing, so it has to carry both - which
    means the passphrase is the only thing between a stolen backup and the
    records. Make it long, and do not store it with the backup.
    """
    if passphrase is None:
        passphrase = getpass.getpass("backup passphrase: ")
        if passphrase != getpass.getpass("again: "):
            raise SystemExit("passphrases differ")
    if len(passphrase) < 12:
        raise SystemExit(
            "passphrase under 12 characters. This is the single secret\n"
            "protecting every record in the backup - use a long one.")

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(KEYFILE, arcname="vault.key")
        n = 0
        st, sc = store.current(), scope()
        for rid in sorted(st.ids(sc)):
            text = st.read(sc, rid)
            if text is not None:
                _tar_bytes(tar, f"records/{rid}.rec", text.encode())
                n += 1
        lines = st.audit_lines(sc)
        if lines:
            _tar_bytes(tar, "audit.log", "".join(json.dumps(x) + "\n" for x in lines).encode())
    raw = buf.getvalue()

    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    header = json.dumps({"kdf": "scrypt", **{k: v for k, v in SCRYPT.items()},
                         "salt": b64(salt), "nonce": b64(nonce),
                         "at": now()}).encode()
    # The header is authenticated too, so nobody can quietly downgrade the
    # scrypt parameters to make the passphrase cheap to attack.
    ct = AESGCM(_backup_key(passphrase, salt)).encrypt(nonce, raw, header)

    out.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(BACKUP_MAGIC)
        f.write(len(header).to_bytes(4, "big"))
        f.write(header)
        f.write(ct)
    audit("backup", str(out), True, f"{n} records")
    print(f"{out}  {out.stat().st_size / 1024:.0f} KB  {n} records")
    print("\nA backup you have never restored is a guess. Test it:")
    print(f"  ./vault.py restore {out} /tmp/restore-test")


def restore(archive: Path, dest: Path, passphrase: str | None = None) -> None:
    raw = archive.read_bytes()
    if not raw.startswith(BACKUP_MAGIC):
        raise SystemExit(f"{archive} is not a Thunder vault backup")
    off = len(BACKUP_MAGIC)
    hlen = int.from_bytes(raw[off:off + 4], "big")
    off += 4
    header = raw[off:off + hlen]
    ct = raw[off + hlen:]
    meta = json.loads(header)
    if passphrase is None:
        passphrase = getpass.getpass("backup passphrase: ")
    params = {k: meta[k] for k in ("n", "r", "p", "dklen")}
    key = hashlib.scrypt(passphrase.encode(), salt=unb64(meta["salt"]),
                         maxmem=MAXMEM, **params)
    try:
        plain = AESGCM(key).decrypt(unb64(meta["nonce"]), ct, header)
    except Exception:
        raise SystemExit("wrong passphrase, or the backup has been modified.")

    dest.mkdir(parents=True, exist_ok=True)
    os.chmod(dest, 0o700)
    with tarfile.open(fileobj=io.BytesIO(plain), mode="r:gz") as tar:
        for member in tar.getmembers():
            # Never trust paths out of an archive: an entry named
            # ../../.ssh/authorized_keys would otherwise be written there.
            name = member.name.lstrip("/")
            if ".." in Path(name).parts or member.issym() or member.islnk():
                raise SystemExit(f"refusing unsafe archive entry: {member.name}")
            member.name = name
            tar.extract(member, dest, filter="data")
    for path in dest.rglob("*"):
        os.chmod(path, 0o700 if path.is_dir() else 0o600)
    n = len(list((dest / "records").glob("*.rec"))) if (dest / "records").exists() else 0
    print(f"restored {n} records and the key to {dest}  (taken {meta.get('at')})")
    print("\nVerify it actually opens:")
    print(f"  THUNDER_VAULT={dest} THUNDER_VAULT_KEY={dest}/vault.key ./vault.py verify")


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="create the master key")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("put", help="encrypt a JSON file into the vault")
    p.add_argument("record_id")
    p.add_argument("json_file")
    p.add_argument("--index", action="append", default=[],
                   help="field to make searchable (repeatable)")

    p = sub.add_parser("get", help="decrypt a record to stdout")
    p.add_argument("record_id")

    p = sub.add_parser("find", help="look up by an indexed field")
    p.add_argument("field")
    p.add_argument("value")

    sub.add_parser("list", help="record ids and dates, nothing decrypted")
    sub.add_parser("verify", help="open every record")
    sub.add_parser("migrate-to-db", help="copy this company's files into THUNDER_VAULT_DB (files are kept)")

    p = sub.add_parser("rotate", help="new key generation, rewrap all records")
    p.add_argument("--drop-old", action="store_true",
                   help="discard retired keys (old backups stop restoring)")

    p = sub.add_parser("backup", help="passphrase-encrypted archive")
    p.add_argument("out")
    p.add_argument("--passphrase-env", help="read passphrase from this env var")

    p = sub.add_parser("restore", help="restore an archive")
    p.add_argument("archive")
    p.add_argument("dest")
    p.add_argument("--passphrase-env")

    a = ap.parse_args()

    if a.cmd == "init":
        key_init(a.force)
    elif a.cmd == "put":
        obj = json.loads(Path(a.json_file).read_text())
        print(f"encrypted -> {put(a.record_id, obj, a.index)}")
    elif a.cmd == "get":
        print(json.dumps(get(a.record_id), indent=2))
    elif a.cmd == "find":
        hits = find(a.field, a.value)
        print("\n".join(hits) if hits else "no match")
    elif a.cmd == "list":
        for _rid, b in bodies():
            print(f"{b['id']:24} gen {b['gen']}  updated {b['updated'][:19]}  "
                  f"indexed: {','.join(b.get('index', {})) or '-'}")
    elif a.cmd == "verify":
        return verify()
    elif a.cmd == "migrate-to-db":
        print(json.dumps(migrate_to_db()))
    elif a.cmd == "rotate":
        rotate(a.drop_old)
    elif a.cmd == "backup":
        pw = os.environ.get(a.passphrase_env) if a.passphrase_env else None
        backup(Path(a.out), pw)
    elif a.cmd == "restore":
        pw = os.environ.get(a.passphrase_env) if a.passphrase_env else None
        restore(Path(a.archive), Path(a.dest), pw)
    return 0


if __name__ == "__main__":
    sys.exit(main())
