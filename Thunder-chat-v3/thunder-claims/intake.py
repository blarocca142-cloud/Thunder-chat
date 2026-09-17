#!/usr/bin/env python3
"""A folder of scans in, a review queue out.

The pieces existed - OCR, extraction, OCR repair, validation, the encrypted
vault - but as four scripts run by hand on one file at a time, which is not
something anyone would use to bill with. This is the tool: point it at a
folder, walk away, come back to a list of what needs a human and what does not.

The measured accuracy decides the design. On 25 synthetic superbills the codes
came back at 94% after repair, and the errors that slipped through were all
free-text OCR noise. That is good enough to draft with and nowhere near good
enough to submit unread, so every claim lands in one of three states:

    BLOCK   something is mechanically wrong - a bad NPI check digit, a
            malformed code, a date that cannot be right. Cannot be billed.
    REVIEW  it passed the checks but something was repaired or is missing.
            A human reads it before it goes anywhere.
    CLEAN   passed every mechanical check with nothing repaired. Still a
            draft. Nothing here is ever submitted by this tool.

Claims go straight into the encrypted vault, and the extraction is never
written to disk in the clear - it exists in memory and goes into the vault or
nowhere. The review queue deliberately carries no patient details either: file
name, record id, status and reasons only. Names come from the vault, where
reading one is decrypted and audited.

    ./intake.py scans/
    ./intake.py scans/ --project march-2026
    ./intake.py scans/ --dry-run        process, report, store nothing

Synthetic patients only until Blayne says otherwise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "thunder-nodes"))
import vault  # noqa: E402
from extract import extract  # noqa: E402
import codelist  # noqa: E402
from repair import parse_note, repair_claim  # noqa: E402
from validate import check  # noqa: E402

try:
    import workpool  # noqa: E402
except Exception:      # the pool is an optimisation, never a dependency
    workpool = None

IMAGES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
PDFS = {".pdf"}
STATE_NAME = "intake_state.json"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str], timeout: int = 180) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def file_id(path: Path) -> str:
    """Identity by content, not name. The same scan re-filed under a new name
    is the same claim, and re-billing it would be worse than missing it."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def ocr_document(path: Path) -> str:
    """Text from an image or a PDF. Multi-page PDFs are joined - a superbill
    that runs onto a second page is still one claim."""
    if path.suffix.lower() in PDFS:
        work = Path(tempfile.mkdtemp(prefix="intake_pdf_"))
        try:
            # 200 dpi: enough for tesseract, and the rendering cost grows fast.
            run(["pdftoppm", "-r", "200", "-png", str(path), str(work / "page")])
            pages = sorted(work.glob("page*.png"))
            return "\n\n".join(
                run(["tesseract", str(p), "stdout", "--dpi", "200"]) or "" for p in pages)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return run(["tesseract", str(path), "stdout", "--dpi", "200"]) or ""


def repair_is_proven(note: str) -> bool:
    """Can this repair stand without a human reading it?

    Only when the real code list settles it: the damaged value is not a code,
    and the repaired value is. That is not a guess the format forced, it is the
    only reading that corresponds to something CMS publishes.

    Anything else is a no. A CPT repair cannot be proven at all while the AMA
    list is unlicensed, and "probably right" is not a standard to bill on.
    """
    parsed = parse_note(note)
    if not parsed:
        return False
    label, before, after = parsed
    if label != "ICD-10":
        return False          # CPT/NPI/sex - no authoritative list to check
    return codelist.icd10_exists(after) is True and \
        codelist.icd10_exists(before) is False


def unknown_codes(claim: dict) -> list[str]:
    """Well-formed codes that are not real codes.

    The format check passes "S39.019A" happily. Only the published list knows
    it does not exist, and a claim carrying one will be rejected by the payer.
    """
    out = []
    for dx in claim.get("diagnoses") or []:
        code = (dx or {}).get("code")
        if code and codelist.icd10_exists(code) is False:
            out.append(f"diagnosis {code} is well-formed but is not a real "
                       f"ICD-10 code")
    return out


def triage(issues: list[dict], repairs: list[str], claim: dict) -> tuple[str, list[str]]:
    """Which pile does this land in, and why."""
    blocks = [i for i in issues if i.get("severity") == "BLOCK"]
    warns = [i for i in issues if i.get("severity") == "WARN"]
    reasons = [f"{i['field']}: {i['problem']}" for i in blocks]
    reasons += unknown_codes(claim)          # a payer would reject these
    if reasons:
        return "BLOCK", reasons

    reasons = [f"{i['field']}: {i['problem']}" for i in warns]
    # Repairs the code list proves are noted but do not cost a review. This is
    # the whole point at thirteen offices: a human should read the doubtful
    # ones, not all of them.
    for r in repairs:
        if not repair_is_proven(r):
            reasons.append(r)
    if not (claim.get("diagnoses") or []):
        reasons.append("no diagnosis codes found on the page")
    if not (claim.get("procedures") or []):
        reasons.append("no procedure codes found on the page")
    return ("REVIEW" if reasons else "CLEAN"), reasons


def load_state(folder: Path) -> dict:
    p = folder / STATE_NAME
    if p.is_file():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"processed": {}}


def save_state(folder: Path, state: dict) -> None:
    (folder / STATE_NAME).write_text(json.dumps(state, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", help="folder of scanned claims")
    ap.add_argument("--project", default="claims", help="vault project name")
    ap.add_argument("--dry-run", action="store_true",
                    help="process and report, but store nothing")
    ap.add_argument("--again", action="store_true",
                    help="reprocess documents already done")
    a = ap.parse_args()

    folder = Path(a.folder)
    if not folder.is_dir():
        print(f"no such folder: {folder}")
        return 1

    if not a.dry_run and not vault.KEYFILE.exists():
        print("The vault has no key yet, and claims are not written anywhere else.\n"
              "Create one first (once, ever):\n\n    ./vault.py init\n\n"
              "Or use --dry-run to see what this folder would produce.")
        return 1

    docs = sorted(p for p in folder.iterdir()
                  if p.is_file() and p.suffix.lower() in (IMAGES | PDFS))
    if not docs:
        print(f"no scans in {folder} (looking for {', '.join(sorted(IMAGES | PDFS))})")
        return 1

    state = load_state(folder)
    queue, counts = [], {"CLEAN": 0, "REVIEW": 0, "BLOCK": 0, "FAILED": 0}
    started = time.time()

    # OCR every image up front, spread across whatever machines are free.
    # Images only: a PDF has to be rendered to pages first, and that is handled
    # per-document below. If the pool is unavailable or no other machine has
    # tesseract, this quietly runs everything locally and costs nothing.
    todo = [p for p in docs if file_id(p) not in state["processed"] or a.again]
    prefetched: dict[Path, str] = {}
    images = [p for p in todo if p.suffix.lower() in IMAGES]
    if workpool and len(images) > 1:
        caps = workpool.capabilities()
        machines = [n for n, _ in workpool.workers_for("tesseract", caps)]
        if len(machines) > 1:
            print(f"OCR spread across: {', '.join(machines)}")
            out = workpool.ocr_batch(images)
            report = out.pop("_report", {})
            prefetched = {k: v for k, v in out.items() if v}
            if report.get("placement"):
                print(f"  {report['placement']}  in {report.get('seconds')}s\n")

    print(f"{len(docs)} documents in {folder}\n")
    for path in docs:
        fid = file_id(path)
        if fid in state["processed"] and not a.again:
            print(f"  skip  {path.name}  (already done - use --again to redo)")
            continue

        t = time.time()
        text = prefetched.get(path) or ocr_document(path)
        if not text.strip():
            print(f"  FAIL  {path.name}  nothing readable on the page")
            counts["FAILED"] += 1
            queue.append({"file": path.name, "status": "FAILED",
                          "reasons": ["OCR produced no text - is the scan blank or upside down?"]})
            continue

        try:
            claim = extract(text)
        except Exception as e:
            print(f"  FAIL  {path.name}  extraction failed: {type(e).__name__}")
            counts["FAILED"] += 1
            queue.append({"file": path.name, "status": "FAILED",
                          "reasons": [f"extraction failed: {e}"]})
            continue

        claim, repairs = repair_claim(claim)
        issues = check(claim)
        status, reasons = triage(issues, repairs, claim)
        counts[status] += 1

        record_id = f"{a.project}-{path.stem}-{fid}"
        stored = None
        if not a.dry_run:
            # Straight into the vault. The plaintext extraction is never
            # written to disk - it goes in encrypted or it goes nowhere.
            vault.put(record_id, claim,
                      ["patient_name", "claim_number", "date_of_service"])
            stored = record_id

        # The queue carries NO patient information. It was tempting to put the
        # name here so the list reads nicely, and that would have quietly made
        # this file plaintext PHI sitting next to the encrypted records it
        # exists to protect. Names come from the vault, where reading one is
        # encrypted and audited. Codes and dates are left out for the same
        # reason - a diagnosis with a date is identifying enough in a small
        # practice.
        queue.append({
            "file": path.name,
            "record": stored,
            "status": status,
            "reasons": reasons,
            "repairs": repairs,
            "repairs_proven": [r for r in repairs if repair_is_proven(r)],
            "diagnosis_count": len(claim.get("diagnoses") or []),
            "procedure_count": len(claim.get("procedures") or []),
            "seconds": round(time.time() - t, 1),
        })
        state["processed"][fid] = {"file": path.name, "at": utc(), "status": status}
        mark = {"CLEAN": "ok  ", "REVIEW": "look", "BLOCK": "STOP"}[status]
        # The name is printed to the operator's terminal, which is a person
        # looking at the scan anyway - it is never written to a file.
        print(f"  {mark}  {path.name:28} {claim.get('patient_name', '?')[:22]:24} "
              f"{round(time.time() - t, 1)}s")
        for r in reasons[:3]:
            print(f"          - {r}")

    if not a.dry_run:
        save_state(folder, state)
        # The queue holds names and dates, so it belongs with the encrypted
        # data rather than next to the scans.
        out = vault.VAULT / "review_queue.json"
        vault.VAULT.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"at": utc(), "items": queue}, indent=2))
        # The queue holds patient names and dates. 0600 like everything else.
        os.chmod(out, 0o600)

    done = sum(counts.values())
    print(f"\n{'=' * 58}")
    print(f"{done} processed in {time.time() - started:.0f}s")
    print(f"  CLEAN  {counts['CLEAN']:3}  passed every check, nothing repaired")
    print(f"  REVIEW {counts['REVIEW']:3}  needs a human before it goes anywhere")
    print(f"  BLOCK  {counts['BLOCK']:3}  mechanically wrong, cannot be billed")
    if counts["FAILED"]:
        print(f"  FAILED {counts['FAILED']:3}  could not be read at all")
    if not a.dry_run:
        print(f"\nfiled in the vault as project '{a.project}'")
        print(f"review queue: {vault.VAULT / 'review_queue.json'}")
    print("\nNothing here has been submitted. Every claim is a draft.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
