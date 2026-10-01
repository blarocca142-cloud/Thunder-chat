"""Where the vault's sealed records live: files, or PostgreSQL.

vault.py does all the cryptography and hands this module finished envelopes
(JSON text holding only ciphertext, wrapped keys, nonces and blind-index
tokens). Nothing here ever sees a patient's data in the clear, and nothing
here can decrypt - a stolen database dump is the same ciphertext a stolen
folder of .rec files was.

Two stores, one interface:

- FileStore  - the original layout, one .rec file per record in
               <company>/records/, deleted/ and audit.log beside it.
- PgStore    - PostgreSQL, chosen by THUNDER_VAULT_DB. One schema per
               company (the "company file"), with records / deleted / audit
               tables. Saves are transactional, and a save can be made
               conditional on the revision it was read at, which is what
               stops two people overwriting each other at the database itself
               rather than only in the program.

Every operation takes a `scope` - a Path for files, a schema name for
PostgreSQL - so the server can serve several companies from one process.
"""
from __future__ import annotations

import json
import os
import re
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


class RevConflict(Exception):
    """The record changed since the revision the caller read."""


# --------------------------------------------------------------------------
# files
# --------------------------------------------------------------------------

class FileStore:
    kind = "files"
    _lock = threading.RLock()  # one process serves the office; this makes check-and-write atomic in it

    def _dir(self, scope: Path) -> Path:
        d = Path(scope) / "records"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def path(self, scope: Path, rid: str) -> Path:
        if not rid or "/" in rid or rid.startswith("."):
            raise ValueError(f"bad record id: {rid!r}")
        return self._dir(scope) / f"{rid}.rec"

    def read(self, scope, rid: str) -> str | None:
        p = self.path(scope, rid)
        return p.read_text() if p.exists() else None

    def exists(self, scope, rid: str) -> bool:
        return self.path(scope, rid).exists()

    def rev(self, scope, rid: str) -> int | None:
        body = self.read(scope, rid)
        return None if body is None else json.loads(body).get("rev")

    def write(self, scope, rid: str, body: str, rev: int, expect_rev: int | None = None) -> None:
        p = self.path(scope, rid)
        with self._lock:
            if expect_rev is not None and p.exists():
                have = json.loads(p.read_text()).get("rev")
                # a record saved before the counter was kept outside the
                # ciphertext has none; the program checked it by decrypting
                if have is not None and int(have) != int(expect_rev):
                    raise RevConflict(rid)
            tmp = p.with_suffix(".tmp")
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(body)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(p)  # atomic: never a half-written record

    def ids(self, scope) -> list[str]:
        return [p.stem for p in sorted(self._dir(scope).glob("*.rec"), key=lambda p: p.stat().st_mtime, reverse=True)]

    def retire(self, scope, rid: str, who: str) -> str:
        src = self.path(scope, rid)
        dest_dir = Path(scope) / "deleted"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{rid}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.rec"
        os.replace(src, dest)
        return dest.name

    def deleted(self, scope, rid: str) -> list[str]:
        d = Path(scope) / "deleted"
        return [p.read_text() for p in sorted(d.glob(f"{rid}.*.rec"))] if d.exists() else []

    def audit(self, scope, line: dict) -> None:
        Path(scope).mkdir(parents=True, exist_ok=True)
        fd = os.open(Path(scope) / "audit.log", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            f.write(json.dumps(line) + "\n")

    def audit_lines(self, scope) -> list[dict]:
        p = Path(scope) / "audit.log"
        return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

    @contextmanager
    def transaction(self, scope):
        with self._lock:
            yield


# --------------------------------------------------------------------------
# PostgreSQL
# --------------------------------------------------------------------------

SCHEMA_RE = re.compile(r"^[a-z][a-z0-9_]{0,50}$")

DDL = """
CREATE SCHEMA IF NOT EXISTS {s};
CREATE TABLE IF NOT EXISTS {s}.records (
    id      text PRIMARY KEY,
    body    text NOT NULL,          -- the sealed envelope, exactly as vault.py made it
    rev     integer NOT NULL DEFAULT 0,
    updated timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS records_updated ON {s}.records (updated DESC);
CREATE TABLE IF NOT EXISTS {s}.deleted (
    id   text NOT NULL,
    at   timestamptz NOT NULL DEFAULT now(),
    who  text,
    body text NOT NULL
);
CREATE TABLE IF NOT EXISTS {s}.audit (
    seq  bigserial PRIMARY KEY,
    line jsonb NOT NULL
);
"""


def parse_dsn(dsn: str) -> dict:
    """postgresql://user:pass@host:port/db  or  postgresql://user@/db?host=/run/postgresql
    (a host starting with / is a unix socket directory)."""
    u = urlparse(dsn)
    if u.scheme not in ("postgresql", "postgres"):
        raise ValueError("THUNDER_VAULT_DB must start with postgresql://")
    q = {k: v[0] for k, v in parse_qs(u.query).items()}
    out = {"user": unquote(u.username or os.environ.get("USER", "")), "database": (u.path or "/").lstrip("/") or None}
    if u.password:
        out["password"] = unquote(u.password)
    host = q.get("host") or u.hostname
    port = int(q.get("port") or u.port or 5432)
    if host and host.startswith("/"):
        out["unix_sock"] = f"{host.rstrip('/')}/.s.PGSQL.{port}"
    else:
        out["host"] = host or "localhost"
        out["port"] = port
    return out


class PgStore:
    kind = "postgresql"

    def __init__(self, dsn: str):
        import pg8000.native  # only needed when PostgreSQL is in use
        self._pg = pg8000.native
        self.params = parse_dsn(dsn)
        self._local = threading.local()
        self._ready: set[str] = set()
        self._ready_lock = threading.Lock()

    def _con(self):
        c = getattr(self._local, "con", None)
        if c is None:
            c = self._pg.Connection(**self.params)
            self._local.con = c
            self._local.depth = 0
        return c

    def _run(self, sql: str, **kw):
        try:
            return self._con().run(sql, **kw)
        except (self._pg.InterfaceError, OSError):
            # the connection died (server restart); reconnect once when not mid-transaction
            if getattr(self._local, "depth", 0):
                raise
            self._local.con = None
            return self._con().run(sql, **kw)

    def _schema(self, scope: str) -> str:
        s = str(scope)
        if not SCHEMA_RE.match(s):
            raise ValueError(f"bad company schema name {s!r}")
        if s not in self._ready:
            with self._ready_lock:
                if s not in self._ready:
                    # on the side connection: DDL inside a save's
                    # transaction would vanish if that save rolled back
                    for stmt in DDL.format(s=s).split(";"):
                        if stmt.strip():
                            self._side(stmt)
                    self._ready.add(s)
        return s

    def read(self, scope, rid: str) -> str | None:
        rows = self._run(f"SELECT body FROM {self._schema(scope)}.records WHERE id = :id", id=rid)
        return rows[0][0] if rows else None

    def exists(self, scope, rid: str) -> bool:
        return bool(self._run(f"SELECT 1 FROM {self._schema(scope)}.records WHERE id = :id", id=rid))

    def rev(self, scope, rid: str) -> int | None:
        rows = self._run(f"SELECT rev FROM {self._schema(scope)}.records WHERE id = :id", id=rid)
        return rows[0][0] if rows else None

    def write(self, scope, rid: str, body: str, rev: int, expect_rev: int | None = None) -> None:
        s = self._schema(scope)
        if expect_rev is None:
            self._run(f"INSERT INTO {s}.records (id, body, rev, updated) VALUES (:id, :b, :r, now()) "
                      f"ON CONFLICT (id) DO UPDATE SET body = EXCLUDED.body, rev = EXCLUDED.rev, updated = now()",
                      id=rid, b=body, r=rev)
        else:
            # The check and the write are one statement, so two offices saving
            # the same claim at the same instant cannot both win.
            self._run(f"UPDATE {s}.records SET body = :b, rev = :r, updated = now() WHERE id = :id AND rev = :e",
                      id=rid, b=body, r=rev, e=expect_rev)
            if self._con().row_count == 0:
                if self.exists(scope, rid):
                    raise RevConflict(rid)
                self._run(f"INSERT INTO {s}.records (id, body, rev) VALUES (:id, :b, :r) ON CONFLICT (id) DO NOTHING",
                          id=rid, b=body, r=rev)
                if self._con().row_count == 0:
                    raise RevConflict(rid)
        self._run("SELECT pg_notify('thunder_claims', :m)", m=f"{s}:{rid}")  # for live updates (step 3)

    def ids(self, scope) -> list[str]:
        return [r[0] for r in self._run(f"SELECT id FROM {self._schema(scope)}.records ORDER BY updated DESC, id")]

    def retire(self, scope, rid: str, who: str) -> str:
        s = self._schema(scope)
        with self.transaction(scope):
            self._run(f"INSERT INTO {s}.deleted (id, who, body) SELECT id, :w, body FROM {s}.records WHERE id = :id", id=rid, w=who)
            self._run(f"DELETE FROM {s}.records WHERE id = :id", id=rid)
        self._run("SELECT pg_notify('thunder_claims', :m)", m=f"{s}:{rid}")
        return f"{s}.deleted"

    def deleted(self, scope, rid: str) -> list[str]:
        return [r[0] for r in self._run(f"SELECT body FROM {self._schema(scope)}.deleted WHERE id = :id ORDER BY at", id=rid)]

    def audit(self, scope, line: dict) -> None:
        # Its own connection, outside any transaction: a save that is rolled
        # back must not take the audit line ("AUTHENTICATION FAILED", "stale
        # save refused") down with it.
        self._side(f"INSERT INTO {self._schema(scope)}.audit (line) VALUES (CAST(:l AS jsonb))", l=json.dumps(line))

    def _side(self, sql: str, **kw):
        """A second connection per thread that is never inside a transaction."""
        for attempt in (0, 1):
            c = getattr(self._local, "acon", None)
            if c is None:
                c = self._local.acon = self._pg.Connection(**self.params)
            try:
                return c.run(sql, **kw)
            except (self._pg.InterfaceError, OSError):
                self._local.acon = None
                if attempt:
                    raise

    def schemas(self) -> list[str]:
        return [r[0] for r in self._run("SELECT nspname FROM pg_namespace WHERE nspname LIKE 'c\\_%' ORDER BY 1")]

    def drop_all_for_tests(self) -> None:
        """Only ever on a database whose name ends in _test."""
        if not str(self.params.get("database") or "").endswith("_test"):
            raise SystemExit("refusing to wipe a database whose name does not end in _test")
        for s in self.schemas():
            if SCHEMA_RE.match(s):
                self._run(f"DROP SCHEMA {s} CASCADE")
        self._ready.clear()

    def audit_lines(self, scope) -> list[dict]:
        out = []
        for (line,) in self._run(f"SELECT line FROM {self._schema(scope)}.audit ORDER BY seq"):
            out.append(line if isinstance(line, dict) else json.loads(line))
        return out

    @contextmanager
    def transaction(self, scope):
        """All-or-nothing: a payment and every claim it changes are saved
        together, or none of them is. Nested calls join the outer one."""
        self._con()
        if self._local.depth == 0:
            self._run("START TRANSACTION")
        self._local.depth += 1
        try:
            yield
        except BaseException:
            self._local.depth -= 1
            if self._local.depth == 0:
                self._run("ROLLBACK")
            raise
        self._local.depth -= 1
        if self._local.depth == 0:
            self._run("COMMIT")


def reset():
    """Forget the chosen store (tests switch THUNDER_VAULT_DB on and off)."""
    global _store
    _store = None


_store = None
_store_lock = threading.Lock()


def current():
    """The store this process uses: PostgreSQL when THUNDER_VAULT_DB is set."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                dsn = os.environ.get("THUNDER_VAULT_DB", "").strip()
                _store = PgStore(dsn) if dsn else FileStore()
    return _store
