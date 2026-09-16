#!/usr/bin/env python3
"""Tests for codestore.py.

The filenames here are chosen by a language model and passed in from a phone,
which makes path traversal the risk that actually matters. Most of these tests
are attempts to write outside the store.

    ./test_codestore.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import codestore as cs  # noqa: E402

ROOT = Path(tempfile.mkdtemp(prefix="codestore_")) / "code"
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'pass' if cond else 'FAIL'}  {name}{('  - ' + detail) if detail else ''}")


def main() -> int:
    print("-- saving --")
    rec = cs.save(ROOT, "print('hi')\n", "demo", "hello.py", "python")
    check("file written", (ROOT / "demo" / "hello.py").is_file())
    check("metadata recorded", rec["language"] == "python" and rec["lines"] == 2, str(rec))

    print("\n-- path traversal (the one that matters) --")
    escapes = ["../../../etc/passwd", "..%2f..%2fetc", "/etc/passwd",
               "....//....//evil.py", "sub/dir/nested.py", "..", ".",
               ".ssh/authorized_keys", "a/../../b.py"]
    for bad in escapes:
        try:
            r = cs.save(ROOT, "x = 1\n", "demo", bad, "python")
            written = (ROOT / "demo" / r["name"]).resolve()
            inside = str(written).startswith(str((ROOT / "demo").resolve()))
            check(f"{bad!r} contained", inside and written.is_file(), str(written))
        except ValueError:
            check(f"{bad!r} contained", True, "refused")

    for bad in ["../escape", "/etc", "..", "a/b"]:
        try:
            r = cs.save(ROOT, "x\n", bad, "f.py", "python")
            where = (ROOT / r["project"]).resolve()
            check(f"project {bad!r} contained",
                  str(where).startswith(str(ROOT.resolve())), str(where))
        except ValueError:
            check(f"project {bad!r} contained", True, "refused")

    leaked = [p for p in ROOT.parent.rglob("*") if p.is_file()
              and not str(p.resolve()).startswith(str(ROOT.resolve()))]
    check("nothing written outside the store", not leaked, str(leaked[:3]))

    print("\n-- naming when none is given --")
    r = cs.save(ROOT, "# app/server.py\nimport os\n", "demo", None, "python")
    check("a path comment is used as the name", r["name"] == "server.py", r["name"])
    r = cs.save(ROOT, "def calculate_total():\n    pass\n", "demo", None, "python")
    check("falls back to the first definition",
          r["name"] == "calculate_total.py", r["name"])
    r = cs.save(ROOT, "just some text\n", "demo", None, "")
    check("unknown language becomes .txt", r["name"].endswith(".txt"), r["name"])
    r = cs.save(ROOT, "fun main() {}\n", "demo", None, "kotlin")
    check("kotlin gets .kt", r["name"].endswith(".kt"), r["name"])

    print("\n-- overwriting keeps one step back --")
    cs.save(ROOT, "v1\n", "demo", "iter.py", "python")
    rec = cs.save(ROOT, "v2\n", "demo", "iter.py", "python")
    check("file replaced", cs.read(ROOT, "demo", "iter.py")["content"] == "v2\n")
    check("previous kept", cs.previous(ROOT, "demo", "iter.py") == "v1\n")
    check("replacement reported", rec["replaced"] is True)
    cs.save(ROOT, "v2\n", "demo", "iter.py", "python")
    check("an identical save does not clobber the history",
          cs.previous(ROOT, "demo", "iter.py") == "v1\n")

    print("\n-- listing and reading --")
    files = cs.list_files(ROOT, "demo")
    check("files listed", len(files) >= 4, str(len(files)))
    check("hidden bookkeeping not listed",
          all(not f["name"].startswith(".") for f in files))
    projects = cs.list_projects(ROOT)
    check("projects listed", any(p["project"] == "demo" for p in projects), str(projects))
    check("missing file reads as None", cs.read(ROOT, "demo", "nope.py") is None)
    check("missing project lists empty", cs.list_files(ROOT, "ghost") == [])

    print("\n-- archive --")
    name, blob = cs.archive(ROOT, "demo")
    check("zip named after the project", name == "demo.zip", name)
    check("zip is a real zip", blob[:2] == b"PK", str(blob[:4]))
    import zipfile, io  # noqa: E401
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names = z.namelist()
        check("zip entries are under the project folder",
              all(n.startswith("demo/") for n in names), str(names[:3]))
        check("zip excludes bookkeeping",
              not any(".index.json" in n or "/." in n for n in names), str(names))
    check("empty project archives as None", cs.archive(ROOT, "ghost") is None)

    print("\n-- limits --")
    try:
        cs.save(ROOT, "x" * (cs.MAX_BYTES + 10), "demo", "huge.py", "python")
        check("oversized file refused", False, "it was accepted")
    except ValueError:
        check("oversized file refused", True)
    try:
        cs.save(ROOT, "   ", "demo", "empty.py", "python")
        check("empty content refused", False, "it was accepted")
    except ValueError:
        check("empty content refused", True)

    print("\n-- delete --")
    check("delete works", cs.delete(ROOT, "demo", "hello.py"))
    check("file gone", cs.read(ROOT, "demo", "hello.py") is None)
    check("deleting twice is not an error", cs.delete(ROOT, "demo", "hello.py") is False)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("failed: " + ", ".join(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(ROOT.parent, ignore_errors=True)
