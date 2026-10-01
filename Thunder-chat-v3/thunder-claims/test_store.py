#!/usr/bin/env python3
"""The record store, attacked on both backends: files and PostgreSQL.

    ./test_store.py                                   # files only
    THUNDER_VAULT_DB=postgresql://...thunder_claims_test ./test_store.py   # and PostgreSQL

The PostgreSQL run wipes every company schema in that database first, so it
refuses a database whose name does not end in _test. Invented data only.
"""
import json
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

WORK = Path(tempfile.mkdtemp(prefix="storetest_"))
os.environ["THUNDER_VAULT"] = str(WORK / "vault")
os.environ["THUNDER_VAULT_KEY"] = str(WORK / "keys" / "vault.key")
DSN = os.environ.pop("THUNDER_VAULT_DB", "")

sys.path.insert(0, str(Path(__file__).parent))
import store  # noqa: E402
import vault  # noqa: E402

PASSED = FAILED = 0


def check(name, ok, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  pass  {name}")
    else:
        FAILED += 1
        print(f"  FAIL  {name}  {detail}")


def refused(fn):
    try:
        fn()
    except (SystemExit, store.RevConflict, ValueError):
        return True
    return False


def use(dsn):
    if dsn:
        os.environ["THUNDER_VAULT_DB"] = dsn
    else:
        os.environ.pop("THUNDER_VAULT_DB", None)
    store.reset()
    vault.set_root(None)
    if dsn:
        store.current().drop_all_for_tests()
    else:
        shutil.rmtree(WORK / "vault", ignore_errors=True)


def rec(n, name="SAMPLE, AVERY"):
    return {"patient_name": name, "_rev": {"n": n, "by": "test", "at": "now"}}


def suite(label, dsn):
    print(f"\n== {label} ==")
    use(dsn)
    vault.set_actor("tester")

    vault.put("pt-1", rec(1), ["patient_name"])
    check("round trip", vault.get("pt-1")["patient_name"] == "SAMPLE, AVERY")
    check("stored copy is ciphertext only", "SAMPLE" not in vault.raw("pt-1"))
    check("revision readable without the key", vault.rev_of("pt-1") == 1)
    vault.put("pt-2", rec(1, "EXAMPLE, JORDAN"), ["patient_name"])
    check("newest first", vault.ids()[0] == "pt-2", vault.ids())
    check("blind-index find", vault.find("patient_name", "example, jordan") == ["pt-2"])

    # lost edits, at the store itself
    vault.put("pt-1", rec(2), ["patient_name"], expect_rev=1)
    check("save at the current revision goes through", vault.rev_of("pt-1") == 2)
    check("save from a stale copy is refused", refused(lambda: vault.put("pt-1", rec(2, "STALE, COPY"), ["patient_name"], expect_rev=1)))
    check("...and changed nothing", vault.get("pt-1")["patient_name"] == "SAMPLE, AVERY")
    check("the refusal is in the audit log", any(a["action"] == "put" and not a["ok"] and "stale" in a["note"] for a in vault.audit_lines()))

    # two people pressing Save on the same record at the same instant
    wins, errs = [], []
    gate = threading.Barrier(8)

    def racer(i):
        vault.set_root(None)
        vault.set_actor(f"desk{i}")
        gate.wait()
        try:
            vault.put("pt-1", rec(3, f"RACER, {i}"), ["patient_name"], expect_rev=2)
            wins.append(i)
        except store.RevConflict:
            pass
        except BaseException as e:
            errs.append(repr(e))
    ts = [threading.Thread(target=racer, args=(i,)) for i in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    check("8 simultaneous saves of one record: exactly one wins", len(wins) == 1 and not errs, (wins, errs))
    check("...and the stored record is the winner's", vault.get("pt-1")["patient_name"] == f"RACER, {wins[0] if wins else '?'}")

    if dsn:
        # the web server starts a thread per request: connections must not pile up
        def visit():
            vault.set_root(None)
            vault.get("pt-1")
            with vault.transaction():
                vault.exists("pt-2")
        for _ in range(3):
            batch = [threading.Thread(target=visit) for _ in range(60)]
            [t.start() for t in batch]
            [t.join() for t in batch]
        for _ in range(150):
            t = threading.Thread(target=visit)
            t.start()
            t.join()
        n = store.current()._run("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")[0][0]
        check(f"330 request threads leave at most the pool's {store.PgStore.POOL_MAX} connections open", n <= store.PgStore.POOL_MAX, n)

    # all or nothing
    try:
        with vault.transaction():
            vault.put("pay-1", rec(1, "PAYMENT"), [])
            vault.put("pt-2", rec(2, "CHANGED, BY PAYMENT"), ["patient_name"], expect_rev=1)
            raise RuntimeError("crash halfway")
    except RuntimeError:
        pass
    if dsn:
        check("a failed save leaves nothing half-done", not vault.exists("pay-1") and vault.get("pt-2")["patient_name"] == "EXAMPLE, JORDAN")
    else:
        check("files: the transaction at least serialises (no rollback on files)", vault.exists("pay-1"))
    with vault.transaction():
        with vault.transaction():
            vault.put("pay-2", rec(1, "NESTED"), [])
    check("nested transactions commit once", vault.exists("pay-2"))
    check("the store still works after a rollback", refused(lambda: vault.put("pt-2", rec(9), [], expect_rev=7)) and vault.rev_of("pt-2") in (1, 2))

    # tampering and relocation, in the store's own copy
    st, sc = store.current(), vault.scope()
    good1, good2 = st.read(sc, "pt-1"), st.read(sc, "pt-2")
    b = json.loads(good1)
    b["ct"] = b["ct"][:-4] + ("AAAA" if not b["ct"].endswith("AAAA") else "BBBB")
    st.write(sc, "pt-1", json.dumps(b), 3)
    check("a modified record is refused, not mis-decrypted", refused(lambda: vault.get("pt-1")))
    st.write(sc, "pt-1", good2, 3)
    check("another patient's envelope under this id is refused", refused(lambda: vault.get("pt-1")))
    b2 = json.loads(good2)
    b2["id"] = "pt-1"
    st.write(sc, "pt-1", json.dumps(b2), 3)
    check("...even with its id rewritten to match", refused(lambda: vault.get("pt-1")))
    check("verify reports the bad record", vault.verify() == 1)
    st.write(sc, "pt-1", good1, 3)
    check("restored record opens again", vault.get("pt-1")["patient_name"].startswith("RACER"))
    check("bad ids are refused", refused(lambda: vault.get("../x")) and refused(lambda: vault.exists("")))

    # recoverable delete
    vault.retire("pay-2")
    check("deleted record is gone from the list", "pay-2" not in vault.ids() and not vault.exists("pay-2"))
    check("...but kept, still sealed", len(vault.deleted_bodies("pay-2")) == 1 and "NESTED" not in vault.deleted_bodies("pay-2")[0])
    check("...and the audit names who", any(a["action"] == "delete" and a["record"] == "pay-2" and a["who"] == "tester" for a in vault.audit_lines()))

    # companies are separate
    vault.set_root(WORK / "companies" / "Tampa_Office")
    check("another company starts empty", vault.ids() == [])
    vault.put("pt-9", rec(1, "TAMPA, ONLY"), [])
    vault.set_root(None)
    check("...and its record is not in Main", "pt-9" not in vault.ids())

    # key rotation and backup work off the store
    vault.rotate()
    check("rotation rewraps every record and they still open", vault.verify() == 0 and vault.get("pt-1")["patient_name"].startswith("RACER"))
    out = WORK / f"b-{label}.tvb"
    vault.backup(out, "a long test passphrase")
    dest = WORK / f"r-{label}"
    vault.restore(out, dest, "a long test passphrase")
    check("backup restores to files that verify", sorted(p.stem for p in (dest / "records").glob("*.rec")) == sorted(vault.ids())
          and (dest / "audit.log").exists())


def migration(dsn):
    print("\n== moving a company from files to PostgreSQL ==")
    use("")
    vault.set_actor("tester")
    # an old-style record: no revision counter outside the ciphertext
    vault.put("pt-old", rec(5, "LEGACY, RECORD"), ["patient_name"])
    p = vault.record_path("pt-old")
    b = json.loads(p.read_text())
    del b["rev"]
    p.write_text(json.dumps(b, indent=2))
    vault.put("cl-1", rec(2, "CLAIM"), [])
    vault.put("cl-gone", rec(1, "DELETED"), [])
    vault.retire("cl-gone")
    files_ids = sorted(vault.ids())
    files_audit = len(vault.audit_lines())
    os.environ["THUNDER_VAULT_DB"] = dsn
    store.reset()
    store.current().drop_all_for_tests()
    out = vault.migrate_to_db()
    check("migrated counts", out["records"] == 2 and out["deleted"] == 1 and out["audit"] == files_audit, out)
    check("same records, every one opens", sorted(vault.ids()) == files_ids and vault.verify() == 0)
    check("identical envelopes (nothing re-encrypted)", vault.raw("cl-1") == vault.record_path("cl-1").read_text())
    check("an old record gets its revision from inside the ciphertext", vault.rev_of("pt-old") == 5)
    check("deleted records came across", len(vault.deleted_bodies("cl-gone")) == 1)
    check("the files are left where they were", vault.record_path("cl-1").exists() and vault.record_path("pt-old").exists())
    check("migrating twice is refused", refused(vault.migrate_to_db))
    check("stale saves are refused on migrated records too", refused(lambda: vault.put("pt-old", rec(5), [], expect_rev=4)))
    vault.put("pt-old", rec(6, "LEGACY, EDITED"), [], expect_rev=5)
    check("...and a current one goes through", vault.get("pt-old")["patient_name"] == "LEGACY, EDITED")


print("store tests")
vault.key_init()
suite("files", "")
if DSN:
    if not store.parse_dsn(DSN).get("database", "").endswith("_test"):
        raise SystemExit("THUNDER_VAULT_DB must name a database ending in _test for this")
    suite("postgresql", DSN)
    migration(DSN)
    store.current().drop_all_for_tests()
else:
    print("\n(set THUNDER_VAULT_DB to a *_test database to run the PostgreSQL half)")
shutil.rmtree(WORK, ignore_errors=True)
print(f"\n{PASSED} passed, {FAILED} failed")
sys.exit(1 if FAILED else 0)
