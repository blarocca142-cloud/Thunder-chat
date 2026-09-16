#!/usr/bin/env python3
"""Measure the pipeline against known truth.

Without this the claims work is a demo. Anyone can show one document being read
correctly; the question that decides whether this saves the family money is how
often it is wrong, on which fields, and - most importantly - **how often it is
wrong in a way nothing catches**.

That last number is the one that matters. An error the validator flags costs a
few seconds of someone's attention. An error that passes validation silently
becomes a wrong claim, and finding those is the entire point of measuring.

    ./synthetic.py 25 cases/
    ./evaluate.py cases/

Reports per-field accuracy, code-level precision and recall, and the count of
silent errors. Uses synthetic patients only.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract import extract  # noqa: E402
from repair import repair_claim  # noqa: E402
from validate import check  # noqa: E402

SCALARS = ["patient_name", "dob", "sex", "address", "phone", "insurer",
           "claim_number", "date_of_injury", "date_of_service",
           "referring_provider", "referring_npi", "treating_provider",
           "treating_npi", "clinic_name", "clinic_tax_id", "clinic_npi",
           "accident_type"]


def norm(v) -> str:
    return " ".join(str(v or "").split()).strip().lower()


def loose(field: str, v: str) -> str:
    """A second, forgiving comparison.

    Reporting "01/05/2026" as wrong because the form said "1/5/2026" would be
    measuring formatting, not reading. Numbers are compared as digits and dates
    as their parts, so the strict number stays honest while this one says
    whether the actual value was understood.
    """
    v = norm(v)
    if field in ("dob", "date_of_injury", "date_of_service"):
        parts = re.findall(r"\d+", v)
        if len(parts) == 3:
            m, dd, y = parts
            y = y if len(y) == 4 else ("20" + y if int(y) < 50 else "19" + y)
            return f"{int(m):02d}/{int(dd):02d}/{y}"
    if field in ("phone", "referring_npi", "treating_npi", "clinic_npi",
                 "clinic_tax_id"):
        return re.sub(r"\D", "", v)
    if field == "sex":
        return v[:1]
    # Free text: OCR sprays stray punctuation ("Motor vehicle.accident",
    # "PA.18512", "lifting; warehouse"). Counting those the same as a wrong
    # sex letter or a wrong NPI would make the headline number meaningless -
    # one is noise on a claim, the other is a rejected claim. Punctuation is
    # compared separately, below, rather than ignored entirely.
    return re.sub(r"[^a-z0-9 ]", "", v).strip()


def ocr(image: Path) -> str:
    r = subprocess.run(["tesseract", str(image), "stdout", "--dpi", "200"],
                       capture_output=True, text=True)
    return r.stdout


def codes(items, key="code") -> set[str]:
    return {norm(i.get(key)).upper().replace(" ", "")
            for i in (items or []) if isinstance(i, dict) and i.get(key)}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    # Measured both ways on purpose: a repair step that is not compared against
    # its absence is an unproven claim.
    use_repair = "--no-repair" not in sys.argv
    folder = Path(args[0] if args else "synthetic")
    truths = sorted(folder.glob("*.truth.json"))
    if not truths:
        print(f"no cases in {folder} - run: ./synthetic.py 25 {folder}")
        return 1

    strict = {f: 0 for f in SCALARS}
    lenient = {f: 0 for f in SCALARS}
    wrong_examples: dict[str, list[tuple[str, str]]] = {f: [] for f in SCALARS}
    dx_hit = dx_total = dx_returned = 0
    px_hit = px_total = px_returned = 0
    silent_errors: list[str] = []
    caught_errors = 0
    repairs: list[str] = []
    cosmetic = 0
    ocr_time = model_time = 0.0
    done = 0

    for tpath in truths:
        stem = tpath.name.replace(".truth.json", "")
        image = tpath.with_name(stem + ".jpg")
        if not image.exists():
            continue
        truth = json.loads(tpath.read_text())

        # The raw extraction is cached because it is the slow part (~50s a
        # page) and it is also the part that does NOT change when the
        # post-processing does. Without this, comparing a repair step against
        # its absence means paying for the whole model run twice.
        cache = tpath.with_name(stem + ".raw.json")
        if cache.exists():
            got = json.loads(cache.read_text())
        else:
            t = time.time()
            text = ocr(image)
            ocr_time += time.time() - t

            t = time.time()
            try:
                got = extract(text)
            except Exception as e:
                print(f"{stem}: extraction failed - {type(e).__name__}: {e}")
                continue
            model_time += time.time() - t
            cache.write_text(json.dumps(got, indent=2))
        done += 1

        if use_repair:
            got, notes = repair_claim(got)
            repairs.extend(notes)

        case_wrong: list[str] = []
        for f in SCALARS:
            exact = norm(got.get(f)) == norm(truth[f])
            near = loose(f, got.get(f)) == loose(f, truth[f])
            strict[f] += exact
            lenient[f] += near
            if not near:
                case_wrong.append(f)
            elif not exact:
                cosmetic += 1
                if len(wrong_examples[f]) < 3:
                    wrong_examples[f].append((truth[f], str(got.get(f, ""))))

        want, have = codes(truth["diagnoses"]), codes(got.get("diagnoses"))
        dx_hit += len(want & have)
        dx_total += len(want)
        dx_returned += len(have)
        if want != have:
            case_wrong.append("diagnoses")

        want, have = codes(truth["procedures"]), codes(got.get("procedures"))
        px_hit += len(want & have)
        px_total += len(want)
        px_returned += len(have)
        if want != have:
            case_wrong.append("procedures")

        # The safety question: when the extraction was wrong, did the
        # mechanical validator notice anything at all?
        issues = check(got)
        flagged = bool(issues)
        if case_wrong and flagged:
            caught_errors += 1
        elif case_wrong:
            silent_errors.append(f"{stem}: {', '.join(case_wrong)}")

        mark = "ok " if not case_wrong else ("flg" if flagged else "SIL")
        print(f"  {mark} {stem}  {len(case_wrong)} wrong", flush=True)

    if not done:
        print("nothing evaluated")
        return 1

    print(f"\n{'=' * 64}\n{done} synthetic cases\n{'=' * 64}")
    print(f"\n{'field':<22}{'exact':>10}{'value':>10}")
    for f in SCALARS:
        print(f"  {f:<20}{strict[f] / done:>9.0%}{lenient[f] / done:>10.0%}")

    print(f"\n{'diagnoses':<22}", end="")
    print(f"recall {dx_hit / dx_total:.0%}  precision "
          f"{dx_hit / dx_returned if dx_returned else 0:.0%}  "
          f"({dx_hit}/{dx_total} found, {dx_returned} returned)")
    print(f"{'procedures':<22}", end="")
    print(f"recall {px_hit / px_total:.0%}  precision "
          f"{px_hit / px_returned if px_returned else 0:.0%}  "
          f"({px_hit}/{px_total} found, {px_returned} returned)")

    clean = done - caught_errors - len(silent_errors)
    print(f"\n{'=' * 64}")
    print(f"fully correct           {clean}/{done}  ({clean / done:.0%})")
    print(f"wrong, validator flagged {caught_errors}/{done}")
    print(f"wrong, NOTHING flagged   {len(silent_errors)}/{done}   <- the ones that matter")
    for s in silent_errors[:12]:
        print(f"    {s}")

    print(f"\ncosmetic differences (punctuation/formatting only): {cosmetic}")
    print(f"\nOCR repairs applied: {len(repairs)}"
          f"{' (disabled)' if not use_repair else ''}")
    for r in repairs[:8]:
        print(f"    {r}")

    if model_time:
        print(f"\ntiming   OCR {ocr_time / done:.1f}s  model {model_time / done:.1f}s  "
              f"per document {(ocr_time + model_time) / done:.1f}s")
    else:
        print("\ntiming   served from cached extractions (delete *.raw.json to re-run)")

    worst = sorted(SCALARS, key=lambda f: lenient[f])[:5]
    print("\nweakest fields:")
    for f in worst:
        if lenient[f] == done:
            continue
        print(f"  {f} ({lenient[f] / done:.0%})")
        for want, got_v in wrong_examples[f]:
            print(f"      want {want!r}")
            print(f"      got  {got_v!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
