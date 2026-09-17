#!/usr/bin/env python3
"""Repair OCR damage in coded fields, using the format as the constraint.

Measured on synthetic superbills, the extraction is not the weak link - OCR is.
Tesseract reliably reads `S39.012A` as `$39.012A` and `G44.309` as `644.309`,
and the model then copies them faithfully, because copying exactly is what it
was told to do. Preprocessing helps a little and does not fix it: the `$`
survives median filtering, upscaling, binarisation and autocontrast.

What does fix it is knowing the shape of the field. An ICD-10 code begins with
a letter, always. So a leading `$` is not an ambiguous reading - it is wrong,
and `$`/`S` is one of the best-known OCR confusions there is. A CPT code is
five digits, so a letter inside one is wrong the same way.

Two rules keep this honest:

1. **Only repair where the format leaves no choice.** If a character is
   plausible where it sits, it is left alone. Guessing at a genuinely ambiguous
   code would be inventing billing data.
2. **Never repair silently.** Every change is returned so it can be shown to
   whoever reviews the claim. An automatic correction nobody sees is how a
   transcription error becomes a systematic one.

This is still a shape check, not a validity check. `S39.012A` and `S39.013A`
are both well-formed, and nothing here can tell you which one the page said.
The stronger version of this module looks codes up in the real CMS ICD-10
release and picks the valid candidate; that is the next step, and it needs the
code list on disk.
"""
from __future__ import annotations

import re

# Confusions that actually occur in this direction. Kept deliberately short -
# a generous table would "fix" things that were never broken.
TO_LETTER = {"$": "S", "5": "S", "6": "G", "0": "O", "1": "I", "8": "B", "2": "Z"}
# Keyed uppercase: every lookup upper-cases the character first, so a
# lowercase key here would simply never match.
TO_DIGIT = {"O": "0", "D": "0", "Q": "0", "I": "1", "L": "1", "|": "1",
            "S": "5", "$": "5", "B": "8", "Z": "2", "G": "6", "T": "7"}


def _fix(ch: str, want: str) -> str | None:
    """Return the corrected character, or None if it cannot be resolved."""
    if want == "alpha":
        return ch.upper() if ch.isalpha() else TO_LETTER.get(ch)
    if want == "digit":
        return ch if ch.isdigit() else TO_DIGIT.get(ch.upper() if ch.isalpha() else ch)
    return ch


def repair_icd10(code: str) -> tuple[str, str | None]:
    """ICD-10-CM: letter, digit, (digit|A|B), then optionally '.' + up to four.

    Returns (code, note). note is None when nothing was changed.
    """
    raw = (code or "").strip().upper()
    if not raw:
        return code, None
    # A comma for a decimal point is the other common scanner error.
    s = raw.replace(",", ".").replace(" ", "")
    # The list number off the page sometimes lands inside the code ("2. M99.01").
    # Only stripped when followed by whitespace in the original, so that a real
    # code misread as digits ("644.309") is never mistaken for a list index.
    # "3... $16.1XXA" and "4.\u00b0 S16.1XXA" both came off real pages: the list
    # number arrives with a run of dots or a speck attached. One dot was not
    # enough, and these blocked two claims out of four in the first batch run.
    s = re.sub(r"^\d{1,2}[.)]+\s*", "", raw.replace(",", ".")).replace(" ", "") or s
    # Leading rubbish from bullets and specks ("-", "\u00b0"). Characters that carry
    # meaning are kept: "$" is a misread "S", so it must survive to be repaired.
    s = re.sub(r"^[^A-Z0-9]+", lambda m: "".join(
        c for c in m.group() if c in TO_LETTER), s)
    s = re.sub(r"[^A-Z0-9]+$", "", s)
    s = re.sub(r"[^A-Z0-9.]", lambda m: TO_LETTER.get(m.group(), m.group()), s)

    head, _, tail = s.partition(".")
    if len(head) < 3:
        return raw, None

    out = []
    for i, ch in enumerate(head):
        # Positions 0/1 are rigid. Position 2 accepts A or B as well, so it is
        # only corrected when it is clearly neither a digit nor A/B.
        if i == 0:
            fixed = _fix(ch, "alpha")
        elif i == 1:
            fixed = _fix(ch, "digit")
        elif i == 2:
            fixed = ch if (ch.isdigit() or ch in "AB") else _fix(ch, "digit")
        else:
            fixed = ch
        if fixed is None:
            return raw, None  # ambiguous - leave it for a human and the validator
        out.append(fixed)
    fixed_code = "".join(out) + (f".{tail}" if tail else "")
    if fixed_code == raw:
        return raw, None
    return fixed_code, f"OCR repair: {raw} -> {fixed_code}"


def repair_numeric(code: str, length: int, label: str) -> tuple[str, str | None]:
    """CPT (5 digits), NPI (10 digits) - anything that is digits and nothing else."""
    original = (code or "").strip()
    if not original:
        return code, None
    s = re.sub(r"[\s\-().]", "", original.upper())
    out = []
    for ch in s:
        fixed = _fix(ch, "digit")
        if fixed is None:
            # Unresolvable. Return the value untouched - not an upper-cased
            # version of it, which would be an edit disguised as a no-op.
            return original, None
        out.append(fixed)
    fixed_code = "".join(out)
    if len(fixed_code) != length:
        return original, None  # wrong length: not a repair, a different problem
    if fixed_code == original:
        return original, None
    return fixed_code, f"OCR repair ({label}): {original} -> {fixed_code}"


def repair_hcpcs(code: str) -> tuple[str, str | None]:
    """HCPCS: one letter then four digits."""
    raw = (code or "").strip().upper()
    s = re.sub(r"[\s\-().]", "", raw)
    if len(s) != 5:
        return raw, None
    first = _fix(s[0], "alpha")
    rest = [_fix(c, "digit") for c in s[1:]]
    if first is None or any(r is None for r in rest):
        return raw, None
    fixed_code = first + "".join(rest)
    return (fixed_code, f"OCR repair (HCPCS): {raw} -> {fixed_code}") if fixed_code != raw else (raw, None)


# Sex has exactly two accepted values on a claim form, so a reading outside
# that set is wrong by definition. E/F and H/M are the confusions that occur.
SEX_CONFUSION = {"E": "F", "P": "F", "R": "F", "H": "M", "N": "M", "W": "M"}


def repair_sex(value: str) -> tuple[str, str | None]:
    raw = (value or "").strip()
    if not raw:
        return value, None
    first = raw[0].upper()
    if first in ("M", "F"):
        return raw, None
    fixed = SEX_CONFUSION.get(first)
    if not fixed:
        return raw, None
    return fixed, f"OCR repair (sex): {raw} -> {fixed}"


NOTE = re.compile(r"^OCR repair(?: \(([^)]+)\))?: (.+?) -> (.+)$")


def parse_note(note: str) -> tuple[str, str, str] | None:
    """(label, before, after) from a repair note.

    Lives here, beside the code that writes these strings, so the writer and
    the reader cannot drift apart. Callers need the before-and-after to judge
    whether a repair can be trusted without a human.
    """
    m = NOTE.match(note or "")
    if not m:
        return None
    return (m.group(1) or "ICD-10"), m.group(2), m.group(3)


def repair_claim(claim: dict) -> tuple[dict, list[str]]:
    """Repair every coded field in an extracted claim.

    Returns the claim and the list of changes. Show the changes to a human -
    that is the whole point of returning them separately.
    """
    notes: list[str] = []
    out = dict(claim)

    for dx in out.get("diagnoses") or []:
        if isinstance(dx, dict) and dx.get("code"):
            fixed, note = repair_icd10(dx["code"])
            if note:
                dx["code"] = fixed
                notes.append(note)

    for pr in out.get("procedures") or []:
        if not isinstance(pr, dict) or not pr.get("code"):
            continue
        raw = str(pr["code"]).strip().upper()
        # A HCPCS code starts with a letter; CPT is five digits. Decide by
        # what the value looks like rather than assuming one or the other.
        if re.match(r"^[A-Z$0-9][0-9OlISB]{4}$", raw) and not raw[0].isdigit() \
                and raw[0] not in TO_DIGIT:
            fixed, note = repair_hcpcs(raw)
        else:
            fixed, note = repair_numeric(raw, 5, "CPT")
        if note:
            pr["code"] = fixed
            notes.append(note)

    if out.get("sex"):
        fixed, note = repair_sex(str(out["sex"]))
        if note:
            out["sex"] = fixed
            notes.append(note)

    for field in ("treating_npi", "referring_npi", "clinic_npi"):
        if out.get(field):
            fixed, note = repair_numeric(str(out[field]), 10, field)
            if note:
                out[field] = fixed
                notes.append(note)

    return out, notes


if __name__ == "__main__":
    for bad in ["$39.012A", "644.309", "$33.5XXA", "M99.01", "644,309",
                "S13.4XXA", "9894l", "98941", "O7110"]:
        fixed, note = repair_icd10(bad) if not bad[0].isdigit() or "." in bad or "," in bad \
            else repair_numeric(bad, 5, "CPT")
        print(f"  {bad:12} -> {fixed:12} {note or ''}")
