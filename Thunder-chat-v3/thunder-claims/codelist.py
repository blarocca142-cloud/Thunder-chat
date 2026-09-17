#!/usr/bin/env python3
"""Does this code actually exist?

The validator checks that a code is well-formed. That catches "$39.012A" and
misses "S39.013A" - a perfectly shaped code for an injury nobody had. Format
tells you the shape; only the real list tells you whether it is a code at all.

This is also what makes automatic clearing safe. A repair that turns "$39.012A"
into "S39.012A" is a guess the format forced. The same repair, where the result
is one of 98,186 codes CMS actually publishes and the alternatives are not, is
a conclusion. The first needs a human; the second does not.

ICD-10-CM is published by CMS and is free to redistribute, so the code list
ships with this repo and works offline. Refresh it once a year in October when
the new edition lands:

    ./codelist.py --fetch

**CPT is not here and cannot be.** It is copyrighted by the AMA and cannot be
redistributed. If the practice licenses it, drop a file of codes at
codes/cpt.txt, one per line, and procedure codes get verified the same way.
Until then they are format-checked only, which is stated rather than glossed.
"""
from __future__ import annotations

import re
import sys
import urllib.request
import zipfile
from functools import lru_cache
from io import BytesIO
from pathlib import Path

CODES = Path(__file__).parent / "codes"
ICD10_FILE = CODES / "icd10cm_2026.txt"
CPT_FILE = CODES / "cpt.txt"
HCPCS_FILE = CODES / "hcpcs.txt"
CMS_URL = "https://www.cms.gov/files/zip/2026-code-descriptions-tabular-order.zip"


def normalise(code: str) -> str:
    """CMS lists codes without the decimal point; pages print them with one."""
    return re.sub(r"[^A-Z0-9]", "", (code or "").upper())


@lru_cache(maxsize=1)
def icd10() -> frozenset[str]:
    if not ICD10_FILE.is_file():
        return frozenset()
    return frozenset(l.strip() for l in ICD10_FILE.read_text().splitlines() if l.strip())


@lru_cache(maxsize=1)
def cpt() -> frozenset[str]:
    """Empty unless the practice has supplied its licensed list."""
    if not CPT_FILE.is_file():
        return frozenset()
    return frozenset(normalise(l) for l in CPT_FILE.read_text().splitlines() if l.strip())


@lru_cache(maxsize=1)
def hcpcs() -> frozenset[str]:
    if not HCPCS_FILE.is_file():
        return frozenset()
    return frozenset(normalise(l) for l in HCPCS_FILE.read_text().splitlines() if l.strip())


def icd10_exists(code: str) -> bool | None:
    """True, False, or None when there is no list to check against.

    None matters: "we cannot tell" and "it is wrong" must never look the same,
    because one of them is a reason to stop and the other is not.
    """
    known = icd10()
    if not known:
        return None
    return normalise(code) in known


def procedure_exists(code: str) -> bool | None:
    n = normalise(code)
    if re.match(r"^[0-9]{5}$", n):
        known = cpt()
        return None if not known else n in known
    if re.match(r"^[A-Z][0-9]{4}$", n):
        known = hcpcs()
        return None if not known else n in known
    return None


def fetch() -> int:
    print(f"downloading {CMS_URL}")
    with urllib.request.urlopen(CMS_URL, timeout=180) as r:
        blob = r.read()
    with zipfile.ZipFile(BytesIO(blob)) as z:
        name = next((n for n in z.namelist() if "codes" in n and n.endswith(".txt")
                     and "addenda" not in n), None)
        if not name:
            print("could not find the codes file in the archive")
            return 1
        text = z.read(name).decode(errors="replace")
    codes = []
    for line in text.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and re.match(r"^[A-Z][0-9A-Z]{2,7}$", parts[0]):
            codes.append(parts[0])
    CODES.mkdir(exist_ok=True)
    ICD10_FILE.write_text("\n".join(sorted(set(codes))) + "\n")
    print(f"{len(set(codes))} codes written to {ICD10_FILE}")
    return 0


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        sys.exit(fetch())
    print(f"ICD-10-CM : {len(icd10()):>6} codes  ({ICD10_FILE.name})")
    print(f"CPT       : {len(cpt()):>6} codes  "
          f"{'(supply codes/cpt.txt - AMA licensed, cannot ship)' if not cpt() else ''}")
    print(f"HCPCS     : {len(hcpcs()):>6} codes  "
          f"{'(optional, codes/hcpcs.txt)' if not hcpcs() else ''}")
    for c in ("S13.4XXA", "S39.012A", "M54.51", "S39.013A", "ZZ9.999"):
        v = icd10_exists(c)
        print(f"  {c:12} {'exists' if v else 'NOT A REAL CODE' if v is False else 'unknown'}")
