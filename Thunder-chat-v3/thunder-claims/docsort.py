"""Sort a scanned or uploaded page into the patient's file, with nobody asked.

What the office does by hand today - look at a page, decide it is a SOAP note
or a bill or an EOB or a signed form, find the dates on it, put it in the
right folder - done on Main when the file is uploaded:

1. Text: the PDF's own text if it has any, otherwise tesseract on the first
   few pages (that is where every bill, EOB and form says what it is).
2. Category by rules first: the CMS-1500 says "HEALTH INSURANCE CLAIM FORM",
   an EOB says "EXPLANATION OF BENEFITS", a SOAP note has Subjective /
   Objective / Assessment / Plan. Rules are exact and instant.
3. Only when the rules cannot tell, Thunder's local model is asked to pick one
   of the same categories (it is not allowed to invent one). The model runs on
   Main; nothing leaves the building.
4. Neither sure -> "Needs Sorting". A page is never filed on a guess.
5. Dates from the page: the date range a bill or EOB covers ("from 08/01/2026
   to 08/15/2026", or the first and last service date), the visit date of a
   SOAP note, the signing date of a form.
6. A warning when the page names a different date of birth than the patient
   it was uploaded to - the costliest filing mistake is the wrong patient.

Nothing here writes anything; claims_web stores what this returns.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from datetime import date, datetime
from pathlib import Path

NEEDS = "Needs Sorting"
CATEGORIES = (
    "SOAP / Treatment Notes",
    "Bills (CMS-1500)",
    "EOB / Carrier Payments",
    "Signed Forms",
    "Legal / Attorney",
    "Insurance Card / ID",
    "X-Ray / Imaging",
    "Outside Medical Records",
    "Correspondence",
    NEEDS,
)
# documents filed before automatic sorting existed
LEGACY = {"Patient File": NEEDS, "Intake / Forms": "Signed Forms", "PIP Forms": "Signed Forms",
          "EOB / Carrier Mail": "EOB / Carrier Payments", "Medical Records": "Outside Medical Records",
          "Attorney": "Legal / Attorney", "Other": NEEDS}
SHORT = {"SOAP / Treatment Notes": "SOAP", "Bills (CMS-1500)": "Bill", "EOB / Carrier Payments": "EOB",
         "Signed Forms": "Signed form", "Legal / Attorney": "Legal", "Insurance Card / ID": "Card / ID",
         "X-Ray / Imaging": "X-ray", "Outside Medical Records": "Outside records",
         "Correspondence": "Letter", NEEDS: "Scan"}


def category_of(name: str) -> str:
    return name if name in CATEGORIES else LEGACY.get(name, NEEDS)


# ---------------------------------------------------------------------------
# text
# ---------------------------------------------------------------------------

MAX_PAGES = 3   # what a page is, and its dates, are on the first pages


def _run(cmd: list[str], data: bytes | None = None, timeout: int = 120) -> str:
    try:
        r = subprocess.run(cmd, input=data, capture_output=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return r.stdout.decode(errors="replace") if r.returncode == 0 else ""


def text_of(pages: list[tuple[str, bytes]]) -> str:
    """Readable text of the first few pages. (mime, raw bytes) per page."""
    out, used = [], 0
    for mime, raw in pages:
        if used >= MAX_PAGES:
            break
        work = Path(tempfile.mkdtemp(prefix="docsort_"))
        try:
            if mime == "application/pdf":
                pdf = work / "in.pdf"
                pdf.write_bytes(raw)
                txt = _run(["pdftotext", "-l", str(MAX_PAGES - used), "-layout", str(pdf), "-"])
                if len(txt.strip()) > 40:            # a PDF with real text: no OCR needed
                    out.append(txt)
                    used += max(1, txt.count("\f"))
                    continue
                _run(["pdftoppm", "-r", "200", "-l", str(MAX_PAGES - used), "-png", str(pdf), str(work / "p")])
                for img in sorted(work.glob("p*.png")):
                    out.append(_run(["tesseract", str(img), "stdout", "--dpi", "200"]))
                    used += 1
            else:
                out.append(_run(["tesseract", "stdin", "stdout", "--dpi", "200"], raw))
                used += 1
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return "\n\f\n".join(t for t in out if t)


# ---------------------------------------------------------------------------
# category, by rules
# ---------------------------------------------------------------------------

# (pattern, weight). Strong, near-unique phrases weigh most.
RULES = {
    "Bills (CMS-1500)": [
        (r"HEALTH INSURANCE CLAIM FORM", 10), (r"NATIONAL UNIFORM CLAIM COMMITTEE|NUCC", 8),
        (r"\bCMS[- ]?1500\b|\bHCFA\b", 8), (r"FEDERAL TAX I\.?D", 3), (r"PATIENT'?S OR AUTHORIZED PERSON'?S SIGNATURE", 4),
        (r"SUPERBILL|STATEMENT OF SERVICES|ITEMIZED (BILL|STATEMENT)", 6), (r"\bCPT\b|PROCEDURES?, SERVICES", 2),
    ],
    "EOB / Carrier Payments": [
        (r"EXPLANATION OF (BENEFITS|REVIEW)|\bE\.?O\.?[BR]\b", 10), (r"REMITTANCE", 6), (r"AMOUNT PAID|PAID AMOUNT|BENEFITS? PAID", 4),
        (r"\bALLOWED\b|ALLOWANCE", 2), (r"CHECK (NO|NUMBER|#)|\bEFT\b", 3), (r"REASON CODE|ADJUSTMENT", 2),
        (r"PIP (PAYMENT|LOG|LEDGER)|PAYMENT SUMMARY|BENEFITS? (EXHAUSTED|DENIED)", 5),
    ],
    "SOAP / Treatment Notes": [
        (r"\bSUBJECTIVE\b", 4), (r"\bOBJECTIVE\b", 4), (r"\bASSESSMENT\b", 3), (r"\bPLAN\b", 1),
        (r"(DAILY|PROGRESS|TREATMENT|OFFICE|VISIT|SOAP) NOTES?", 6), (r"CHIEF COMPLAINT|\bC/C\b", 4),
        (r"PAIN (SCALE|LEVEL)|\bVAS\b|\d+ ?/ ?10\b", 2), (r"SUBLUXATION|SEGMENTS? ADJUSTED|ADJUSTED|PALPATION|RANGE OF MOTION|\bROM\b", 3),
        (r"^\s*[SOAP]\s*:", 2),
    ],
    "Signed Forms": [
        (r"ASSIGNMENT OF BENEFITS|I HEREBY ASSIGN", 9), (r"STANDARD DISCLOSURE AND ACKNOWLEDGE?MENT", 10),
        (r"NOTICE OF (INITIATION|PRIVACY PRACTICES)", 8), (r"\bHIPAA\b", 4), (r"CONSENT (TO|FOR) TREAT", 7),
        (r"AUTHORI[SZ]ATION (TO|FOR) RELEASE|I AUTHORI[SZ]E", 5), (r"(PATIENT|NEW PATIENT) (INTAKE|INFORMATION|REGISTRATION)", 6),
        (r"APPLICATION FOR (FLORIDA )?(NO[- ]FAULT|PIP)|PIP APPLICATION", 8), (r"(PATIENT|GUARDIAN)'?S? SIGNATURE", 3),
    ],
    "Legal / Attorney": [
        (r"LETTER OF (REPRESENTATION|PROTECTION)", 10), (r"ATTORNEYS? AT LAW|LAW (OFFICES?|FIRM|GROUP)", 7),
        (r"\bESQ\.?\b|\bP\.A\.\b", 3), (r"SUBPOENA|DEPOSITION|LIEN\b|COURT|CIRCUIT|PLAINTIFF|DEFENDANT", 5),
        (r"(THIS FIRM|WE) REPRESENTS?", 6),
    ],
    "Insurance Card / ID": [
        (r"INSURANCE (IDENTIFICATION|ID) CARD|PROOF OF INSURANCE", 9), (r"DRIVER'?S? LICEN[CS]E|\bID CARD\b", 6),
        (r"POLICY (NO|NUMBER|#)|MEMBER ID", 3), (r"EFFECTIVE (DATE)?.*EXPIR", 3), (r"\bVIN\b|VEHICLE", 2),
    ],
    "X-Ray / Imaging": [
        (r"RADIOLOGY|RADIOGRAPH", 7), (r"\bX-?RAYS?\b|\bMRI\b|\bCT SCAN\b|IMAGING", 4), (r"\bIMPRESSION\b", 4),
        (r"\bFINDINGS\b", 2), (r"\bVIEWS?\b|LATERAL|AP VIEW|FLEXION|EXTENSION", 2),
    ],
    "Outside Medical Records": [
        (r"EMERGENCY (DEPARTMENT|ROOM)|\bED VISIT|ER VISIT", 7), (r"DISCHARGE (SUMMARY|INSTRUCTIONS)", 7),
        (r"HOSPITAL|MEDICAL CENTER", 3), (r"\bEMS\b|RUN REPORT|PATIENT CARE REPORT", 6), (r"TRIAGE|ATTENDING PHYSICIAN", 3),
    ],
    "Correspondence": [
        (r"^\s*DEAR\b", 3), (r"\bSINCERELY\b|\bREGARDS\b", 3), (r"^\s*RE\s*:", 2), (r"PLEASE (CALL|CONTACT|SEND|FORWARD)", 2),
    ],
}
SURE = 8     # top score needed
MARGIN = 4   # and how far ahead of the runner-up


def rule_scores(text: str) -> dict[str, int]:
    up = text.upper()
    return {cat: sum(w for pat, w in rules if re.search(pat, up, re.M)) for cat, rules in RULES.items()}


def by_rules(text: str) -> tuple[str | None, str]:
    s = sorted(rule_scores(text).items(), key=lambda kv: -kv[1])
    (top, a), (_, b) = s[0], s[1]
    if a >= SURE and a - b >= MARGIN:
        return top, f"rules ({a} vs {b})"
    return None, f"rules unsure ({top} {a}, next {b})"


# ---------------------------------------------------------------------------
# category, by Thunder's model when the rules cannot tell
# ---------------------------------------------------------------------------

def by_model(text: str) -> tuple[str | None, str]:
    """Ask the local model to pick one of CATEGORIES. Any failure, refusal or
    answer outside the list is 'not sure', never a guess."""
    if os.environ.get("THUNDER_DOCSORT_MODEL", "").lower() == "off":   # tests: rules only
        return None, "model off"
    try:
        import extract   # same model, origin gate and context window as claim extraction
        ok, why = extract.model_origin_ok(extract.MODEL)
        if not ok:
            return None, "model refused: " + why
        cats = [c for c in CATEGORIES if c != NEEDS]
        payload = json.dumps({
            "model": extract.MODEL, "stream": False, "format": "json",
            "options": {"temperature": 0, "num_predict": 200, "num_ctx": extract.NUM_CTX},
            "messages": [
                {"role": "system", "content":
                 "You sort pages for a Florida chiropractic billing office. Pick the ONE category the page is, "
                 "from this exact list: " + json.dumps(cats) + '. Return ONLY {"category": "...", "sure": true|false}. '
                 'If you cannot tell, return {"category": "", "sure": false}. Never invent a category.'},
                {"role": "user", "content": "Page text:\n\n" + text[:6000]},
            ]}).encode()
        req = urllib.request.Request(extract.OLLAMA, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            content = (json.loads(r.read().decode()).get("message") or {}).get("content") or "{}"
        ans = json.loads(content)
    except Exception as e:
        return None, f"model unavailable ({type(e).__name__})"
    cat = str(ans.get("category") or "")
    if cat in cats and ans.get("sure") is True:
        return cat, "Thunder"
    return None, "Thunder not sure"


# ---------------------------------------------------------------------------
# dates
# ---------------------------------------------------------------------------

D = r"(\d{1,2})[/-](\d{1,2})[/-](\d{4}|\d{2})\b"


def _mk(m, n, y) -> date | None:
    y = int(y)
    if y < 100:
        y += 2000 if y <= (date.today().year % 100) + 1 else 1900
    try:
        return date(y, int(m), int(n))
    except ValueError:
        return None


def _fmt(d: date) -> str:
    return d.strftime("%m/%d/%Y")


def find_dates(text: str, dob: str = "") -> list[tuple[int, date]]:
    """(position, date) for every plausible date on the page, minus the
    patient's date of birth and anything labelled as a birth date."""
    born = None
    m = re.fullmatch(D, dob.strip()) if dob else None
    if m:
        born = _mk(*m.groups())
    out, today = [], date.today()
    up = text.upper()
    for m in re.finditer(D, text):
        d = _mk(*m.groups())
        if not d or d == born or d.year < 1990 or d > today:
            continue
        before = up[max(0, m.start() - 25):m.start()]
        if re.search(r"D\.?O\.?B|BIRTH|BORN", before):
            continue
        out.append((m.start(), d))
    return out


RANGE = re.compile(r"(?:FROM\s*)?" + D + r"\s*(?:-|–|—|TO|THRU|THROUGH)\s*" + D, re.I)


def dates_for(category: str, text: str, dob: str = "") -> dict:
    """{"from","to"} (or {"date"}) as MM/DD/YYYY, from what the page says."""
    found = find_dates(text, dob)
    if not found:
        return {}
    if category in ("Bills (CMS-1500)", "EOB / Carrier Payments", "Outside Medical Records"):
        spans = []
        for m in RANGE.finditer(text):   # every "from - to" on the page (a bill has one per line)
            a, b = _mk(*m.groups()[:3]), _mk(*m.groups()[3:])
            if a and b and a <= b <= date.today():
                spans.append((a, b))
        if spans:
            return {"from": _fmt(min(a for a, _ in spans)), "to": _fmt(max(b for _, b in spans))}
        ds = sorted(d for _, d in found)
        if category == "EOB / Carrier Payments" and len(ds) > 2:
            ds = ds[:-1]   # the latest date on an EOB is usually when it was printed, not a service date
        return {"from": _fmt(ds[0]), "to": _fmt(ds[-1])}
    up = text.upper()
    labels = {"SOAP / Treatment Notes": r"DATE OF SERVICE|\bDOS\b|VISIT DATE|DATE OF VISIT|\bDATE\b",
              "Signed Forms": r"DATE SIGNED|SIGNATURE.{0,40}DATE|\bDATE\b",
              "X-Ray / Imaging": r"EXAM DATE|DATE OF (EXAM|STUDY)|\bDATE\b"}.get(category, r"\bDATE\b")
    # a date labelled as the accident's is never the document's own date
    own = [(pos, d) for pos, d in found if not re.search(r"(LOSS|INJURY|ACCIDENT|COLLISION|D\.?O\.?I)\W{0,12}$", up[max(0, pos - 30):pos])] or found
    for pos, d in own:
        if re.search(labels, up[max(0, pos - 40):pos]):
            return {"date": _fmt(d)}
    return {"date": _fmt(own[0][1])}


# ---------------------------------------------------------------------------
# right patient?
# ---------------------------------------------------------------------------

def patient_check(text: str, patient: dict) -> str:
    """"" when nothing contradicts the patient, otherwise a short warning.
    Only a birth date on the page that is NOT this patient's raises it - a
    missing name proves nothing (EOBs often abbreviate it)."""
    up = text.upper()
    dob = str(patient.get("dob") or "").strip()
    mine = None
    m = re.fullmatch(D, dob) if dob else None
    if m:
        mine = _mk(*m.groups())
    for m in re.finditer(r"(D\.?O\.?B\.?|DATE OF BIRTH|BIRTH ?DATE)\W{0,10}" + D, up):
        d = _mk(*m.groups()[1:])
        if d and mine and d != mine:
            return f"this page shows a different date of birth ({_fmt(d)}) - check it belongs to this patient"
    last = str(patient.get("last_name") or "").strip().upper()
    if last and len(last) > 2 and re.search(r"PATIENT( NAME)?\W{0,5}[A-Z]", up) and last not in up:
        return f"this page names a patient but not {last} - check it belongs to this patient"
    return ""


# ---------------------------------------------------------------------------
# all of it
# ---------------------------------------------------------------------------

def carrier_in(text: str, payers: list[str]) -> str:
    up = text.upper()
    for p in sorted(payers, key=len, reverse=True):
        if p and p.upper() in up:
            return p.upper()
    return ""


def sort_text(text: str, patient: dict, payers: list[str] | None = None, ask_model=by_model) -> dict:
    """What claims_web stores for an upload: category, dates, title, how it
    was decided, and any wrong-patient warning."""
    if len(text.strip()) < 15:
        cat, how = NEEDS, "no readable text"
    else:
        cat, how = by_rules(text)
        if not cat and ask_model:
            cat, how2 = ask_model(text)
            how = how + "; " + how2
        cat = cat or NEEDS
    when = dates_for(cat, text, str(patient.get("dob") or "")) if cat != NEEDS else {}
    who = carrier_in(text, payers or []) if cat in ("EOB / Carrier Payments", "Bills (CMS-1500)", "Insurance Card / ID") else ""
    span = (when["from"] + (" – " + when["to"] if when.get("to") != when.get("from") else "")) if when.get("from") else when.get("date", "")
    title = " ".join(x for x in (SHORT[cat], span, who) if x)
    return {"category": cat, "how": how, "title": title, "warning": patient_check(text, patient) if text.strip() else "",
            "sort_date": when.get("to") or when.get("date") or "", **when}


def sort_upload(pages: list[tuple[str, bytes]], patient: dict, payers: list[str] | None = None, ask_model=by_model) -> dict:
    return sort_text(text_of(pages), patient, payers, ask_model)


def sort_key(meta: dict) -> tuple:
    """Newest first within a category, by the date on the page."""
    s = meta.get("sort_date") or meta.get("date") or ""
    try:
        return (datetime.strptime(s, "%m/%d/%Y").date(),)
    except ValueError:
        return (date.min,)
