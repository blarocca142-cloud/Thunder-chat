#!/usr/bin/env python3
"""Automatic filing of scans, on made-up pages of every kind the office gets.

    python3 test_docsort.py

The model is replaced by a stub here (and in one check made to fail), so this
runs anywhere; the rules must carry the common pages on their own.
Every name, number and carrier below is invented.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import docsort  # noqa: E402

PASSED = FAILED = 0


def check(name, ok, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  pass  {name}")
    else:
        FAILED += 1
        print(f"  FAIL  {name}  {detail}")


PT = {"last_name": "DELGADO", "first_name": "ROSA", "dob": "08/27/1974"}
PAYERS = ["GULF COAST AUTO INSURANCE", "SUNSHINE STATE CASUALTY"]
no_model = None


def model_says(cat):
    return lambda text: (cat, "Thunder")


PAGES = {
    "Bills (CMS-1500)": """HEALTH INSURANCE CLAIM FORM
APPROVED BY NATIONAL UNIFORM CLAIM COMMITTEE (NUCC) 02/12
SUNSHINE STATE CASUALTY   PO BOX 7710 ORLANDO FL
2. PATIENT'S NAME  DELGADO, ROSA M     3. PATIENT'S BIRTH DATE 08/27/1974
24. A. DATE(S) OF SERVICE  From 08/04/2026 To 08/04/2026   98941  65 00
                           From 08/06/2026 To 08/06/2026   97140  45 00
25. FEDERAL TAX I.D. NUMBER 59-0000001
12. PATIENT'S OR AUTHORIZED PERSON'S SIGNATURE  SIGNATURE ON FILE""",
    "EOB / Carrier Payments": """GULF COAST AUTO INSURANCE
EXPLANATION OF REVIEW
Patient: DELGADO, ROSA   Claim #: GU-261373
Dates of service 08/01/2026 - 08/15/2026
Billed 540.00  Allowed 432.00  Amount Paid 345.60
Reason code 45 - charge exceeds fee schedule
Check number 55017   Printed 09/20/2026""",
    "SOAP / Treatment Notes": """SUNSHINE SPINE & REHAB - DAILY NOTE
Patient: Delgado, Rosa    Date of service: 08/06/2026
S: Neck pain 6/10, better than last visit. Headaches less frequent.
O: Palpation tenderness C3-C6, ROM reduced in rotation. Subluxation C5.
A: Cervical sprain improving.
P: Segments adjusted C5, T4. Continue 3x/week.""",
    "Signed Forms": """ASSIGNMENT OF BENEFITS
I hereby assign to Sunshine Spine & Rehab all personal injury protection benefits
payable for services rendered.
Patient's signature ____Rosa Delgado______   Date 06/04/2026""",
    "Legal / Attorney": """BAY AREA INJURY LAW, P.A.
ATTORNEYS AT LAW
RE: Our client Rosa Delgado, date of loss 06/03/2026
Please be advised that this firm represents the above patient. LETTER OF REPRESENTATION.
Kindly forward all records and bills to our office.""",
    "Insurance Card / ID": """FLORIDA AUTOMOBILE INSURANCE IDENTIFICATION CARD
SUNSHINE STATE CASUALTY  Policy Number SU-0099812
Effective 01/15/2026 Expiration 01/15/2027  VEHICLE 2019 TOYOTA  VIN 1N4AL3AP0JC000000""",
    "X-Ray / Imaging": """RADIOLOGY REPORT
EXAM: X-RAY CERVICAL SPINE 4 VIEWS   Exam date: 06/04/2026
FINDINGS: Straightening of the normal cervical lordosis. No fracture.
IMPRESSION: Findings consistent with muscle spasm.""",
    "Outside Medical Records": """TAMPA GENERAL MEDICAL CENTER - EMERGENCY DEPARTMENT
Arrival 06/03/2026 Discharge 06/03/2026
Triage: MVC, neck pain. Attending physician: (demo)
DISCHARGE INSTRUCTIONS: follow up with chiropractor.""",
    "Correspondence": """June 20, 2026
Dear Office Manager,
RE: Rosa Delgado
Please call our office to schedule a records pickup.
Sincerely,
Front desk""",
}

print("each kind of page goes to its own folder, by rules alone")
for cat, text in PAGES.items():
    r = docsort.sort_text(text, PT, PAYERS, ask_model=no_model)
    check(f"{cat}", r["category"] == cat, r)

print("dates from the page")
r = docsort.sort_text(PAGES["Bills (CMS-1500)"], PT, PAYERS, no_model)
check("bill: first and last service date, never the birth date", r.get("from") == "08/04/2026" and r.get("to") == "08/06/2026", r)
check("bill title names what, when and who", r["title"] == "Bill 08/04/2026 – 08/06/2026 SUNSHINE STATE CASUALTY", r["title"])
r = docsort.sort_text(PAGES["EOB / Carrier Payments"], PT, PAYERS, no_model)
check("EOB: the 'from - to' range it covers, not the print date", r.get("from") == "08/01/2026" and r.get("to") == "08/15/2026", r)
check("EOB title carries the carrier", "GULF COAST AUTO INSURANCE" in r["title"], r["title"])
check("EOBs sort by the end of the period they cover", r["sort_date"] == "08/15/2026", r)
r = docsort.sort_text(PAGES["SOAP / Treatment Notes"], PT, PAYERS, no_model)
check("SOAP note: its date of service", r.get("date") == "08/06/2026" and r["title"] == "SOAP 08/06/2026", r)
r = docsort.sort_text(PAGES["Signed Forms"], PT, PAYERS, no_model)
check("signed form: the date it was signed", r.get("date") == "06/04/2026", r)
r = docsort.sort_text(PAGES["Legal / Attorney"] + "\nDated 06/20/2026", PT, PAYERS, no_model)
check("attorney letter: dated when written, not the date of loss", r.get("date") == "06/20/2026", r)
eob2 = "EXPLANATION OF BENEFITS\nAmount paid 120.00\nService 07/02/2026\nService 07/09/2026\nService 07/16/2026\nDate printed 08/30/2026"
r = docsort.sort_text(eob2, PT, PAYERS, no_model)
check("EOB with only single dates: first to last service, print date dropped", (r.get("from"), r.get("to")) == ("07/02/2026", "07/16/2026"), r)

print("not sure -> Thunder, then Needs Sorting, never a guess")
vague = "Page 2 of 3\nContinued from previous page\nSee attached\n07/01/2026"
r = docsort.sort_text(vague, PT, PAYERS, ask_model=no_model)
check("rules unsure and no model: Needs Sorting", r["category"] == docsort.NEEDS and r["title"].startswith("Scan"), r)
r = docsort.sort_text(vague, PT, PAYERS, ask_model=model_says("Correspondence"))
check("rules unsure: Thunder's answer is used", r["category"] == "Correspondence" and "Thunder" in r["how"], r)
r = docsort.sort_text(vague, PT, PAYERS, ask_model=lambda t: (None, "Thunder not sure"))
check("Thunder not sure either: Needs Sorting", r["category"] == docsort.NEEDS, r)
r = docsort.sort_text(PAGES["SOAP / Treatment Notes"], PT, PAYERS, ask_model=model_says("Legal / Attorney"))
check("a page the rules are sure of never goes to the model", r["category"] == "SOAP / Treatment Notes", r)
r = docsort.sort_text("   ", PT, PAYERS, ask_model=model_says("Legal / Attorney"))
check("a blank or unreadable scan: Needs Sorting", r["category"] == docsort.NEEDS and r["how"] == "no readable text", r)
import extract  # noqa: E402
_orig = extract.model_origin_ok
extract.model_origin_ok = lambda m=None: (False, "blocked for the test")
cat, how = docsort.by_model("EXPLANATION OF ...")
check("a model that fails the origin check is never used", cat is None and "refused" in how, how)
extract.model_origin_ok = _orig

print("wrong patient")
other = PAGES["Bills (CMS-1500)"].replace("08/27/1974", "02/11/1990")
r = docsort.sort_text(other, PT, PAYERS, no_model)
check("a different date of birth on the page is flagged", "different date of birth" in r["warning"], r)
check("the right patient's own page is not", docsort.sort_text(PAGES["Bills (CMS-1500)"], PT, PAYERS, no_model)["warning"] == "")
r = docsort.sort_text(PAGES["SOAP / Treatment Notes"].replace("Delgado, Rosa", "Whitaker, Daniel"), PT, PAYERS, no_model)
check("a page naming another patient is flagged", "not DELGADO" in r["warning"], r)

print("old folders map to the new ones")
check("EOB / Carrier Mail -> EOB / Carrier Payments", docsort.category_of("EOB / Carrier Mail") == "EOB / Carrier Payments")
check("Patient File -> Needs Sorting", docsort.category_of("Patient File") == docsort.NEEDS)

print("real OCR on a scanned page")
work = Path(tempfile.mkdtemp())
lines = PAGES["EOB / Carrier Payments"].splitlines()
stream = "BT /F1 14 Tf 60 740 Td 18 TL " + " ".join(f"({l}) Tj T*" for l in lines) + " ET"
objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"]
pdf, offs = b"%PDF-1.4\n", []
for i, o in enumerate(objs, 1):
    offs.append(len(pdf))
    pdf += f"{i} 0 obj\n{o}\nendobj\n".encode()
xref = len(pdf)
pdf += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
pdf += f"trailer << /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
(work / "eob.pdf").write_bytes(pdf)
r = docsort.sort_upload([("application/pdf", pdf)], PT, PAYERS, no_model)
check("a PDF with text is read directly and filed", r["category"] == "EOB / Carrier Payments" and r.get("to") == "08/15/2026", r)
subprocess.run(["pdftoppm", "-r", "200", "-png", "-singlefile", str(work / "eob.pdf"), str(work / "scan")], check=True)
png = (work / "scan.png").read_bytes()
r = docsort.sort_upload([("image/png", png)], PT, PAYERS, no_model)
check("a scanned image goes through OCR and is filed", r["category"] == "EOB / Carrier Payments" and r.get("from") == "08/01/2026", r)

print(f"\n{PASSED} passed, {FAILED} failed")
sys.exit(1 if FAILED else 0)
