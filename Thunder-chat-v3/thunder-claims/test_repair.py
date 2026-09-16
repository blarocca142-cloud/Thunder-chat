#!/usr/bin/env python3
"""Tests for repair.py.

The dangerous failure for this module is not missing a repair - it is making
one that should not have been made. A wrong "correction" to a billing code is
worse than leaving the OCR damage visible, because the damage would have been
caught downstream and the correction looks authoritative.

So the tests come in three groups: damage that must be repaired, values that
must be left exactly alone, and ambiguity that must be declined.

    ./test_repair.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from repair import (repair_claim, repair_hcpcs, repair_icd10,  # noqa: E402
                    repair_numeric, repair_sex)

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'pass' if cond else 'FAIL'}  {name}{('  - ' + detail) if detail else ''}")


def repaired(fn, value, expect, *args):
    got, note = fn(value, *args)
    check(f"{value!r} -> {expect!r}", got == expect and note is not None,
          f"got {got!r}, note={note!r}")


def untouched(fn, value, *args):
    got, note = fn(value, *args)
    check(f"{value!r} left alone", got == value and note is None,
          f"got {got!r}, note={note!r}")


def main() -> int:
    print("-- damage that must be repaired --")
    # Every one of these was observed in a real tesseract run on a synthetic page.
    repaired(repair_icd10, "$39.012A", "S39.012A")
    repaired(repair_icd10, "$33.5XXA", "S33.5XXA")
    repaired(repair_icd10, "644.309", "G44.309")
    repaired(repair_icd10, "644,309", "G44.309")
    repaired(repair_icd10, "2. M99.01", "M99.01")
    repaired(repair_icd10, "-$33.5XXA", "S33.5XXA")
    repaired(repair_icd10, "°S16.1XXA", "S16.1XXA")
    repaired(repair_numeric, "9894l", "98941", 5, "CPT")
    repaired(repair_numeric, "O7110", "07110", 5, "CPT")
    repaired(repair_numeric, "O873821421", "0873821421", 10, "NPI")
    repaired(repair_sex, "E", "F")
    repaired(repair_hcpcs, "G02BO", "G0280")

    print("\n-- valid values that must NOT change --")
    for code in ["S13.4XXA", "M54.51", "G44.309", "M99.01", "S39.012A", "M54.2"]:
        untouched(repair_icd10, code)
    untouched(repair_numeric, "98941", 5, "CPT")
    untouched(repair_numeric, "1234567893", 10, "NPI")
    untouched(repair_sex, "M")
    untouched(repair_sex, "F")

    print("\n-- ambiguity that must be declined --")
    # Nothing in the format says which letter this should be, so guessing would
    # be inventing a code.
    untouched(repair_icd10, "XYZ.123")
    untouched(repair_numeric, "ABCDE", 5, "CPT")
    untouched(repair_numeric, "9894", 5, "CPT")      # wrong length
    untouched(repair_numeric, "123456789012", 10, "NPI")
    untouched(repair_sex, "X")
    untouched(repair_sex, "")

    print("\n-- repairs are never silent --")
    claim = {
        "sex": "E",
        "treating_npi": "O873821421",
        "diagnoses": [{"code": "$39.012A"}, {"code": "M99.01"}],
        "procedures": [{"code": "9894l"}, {"code": "97110"}],
    }
    fixed, notes = repair_claim(claim)
    check("every change is reported", len(notes) == 4, f"{len(notes)} notes: {notes}")
    check("values actually corrected",
          fixed["sex"] == "F" and fixed["treating_npi"] == "0873821421"
          and fixed["diagnoses"][0]["code"] == "S39.012A"
          and fixed["procedures"][0]["code"] == "98941")
    check("untouched values stayed untouched",
          fixed["diagnoses"][1]["code"] == "M99.01"
          and fixed["procedures"][1]["code"] == "97110")

    clean = {"sex": "F", "diagnoses": [{"code": "M54.51"}], "procedures": [{"code": "97110"}]}
    _, notes = repair_claim(clean)
    check("a clean claim produces no notes", notes == [], str(notes))

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("failed: " + ", ".join(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
