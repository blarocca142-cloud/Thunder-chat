"""Check extracted claim fields before anyone sees them.

This is the layer that matters. The model will occasionally corrupt a code or
drop a field, and a malformed code is a rejected claim at best. Format rules
and checksums catch mechanical errors deterministically - no second model
needed for the things that can be checked with arithmetic.

What it CANNOT check is whether a code is clinically correct for the notes.
That stays a human's job, and nothing here should imply otherwise.
"""
import json, re, sys
from datetime import date, datetime

ICD10 = re.compile(r"^[A-Z][0-9][0-9ABand]?(\.[0-9A-Z]{1,4})?$", re.I)
CPT = re.compile(r"^[0-9]{5}$")
HCPCS = re.compile(r"^[A-Z][0-9]{4}$")
REQUIRED = ["patient_name", "dob", "date_of_injury", "date_of_service",
            "insurer", "treating_provider", "treating_npi"]


def npi_valid(npi: str) -> bool:
    """NPIs carry a Luhn check digit over the number prefixed with 80840."""
    n = re.sub(r"\D", "", npi or "")
    if len(n) != 10:
        return False
    digits = [int(c) for c in "80840" + n]
    total, parity = 0, len(digits) % 2
    for i, d in enumerate(digits[:-1]):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (total + digits[-1]) % 10 == 0


def parse_date(s: str):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def check(c: dict) -> list[dict]:
    out = []
    def flag(sev, field, msg):
        out.append({"severity": sev, "field": field, "problem": msg})

    for k in REQUIRED:
        if not str(c.get(k) or "").strip():
            flag("BLOCK", k, "required field is empty")

    for who in ("treating_npi", "referring_npi", "clinic_npi"):
        v = str(c.get(who) or "").strip()
        if v and not npi_valid(v):
            flag("BLOCK", who, f"'{v}' fails the NPI check digit")

    for i, dx in enumerate(c.get("diagnoses") or []):
        code = str(dx.get("code") or "").strip()
        if not code:
            flag("BLOCK", f"diagnoses[{i}]", "missing code")
        elif not ICD10.match(code):
            flag("BLOCK", f"diagnoses[{i}]", f"'{code}' is not a valid ICD-10 format")

    for i, pr in enumerate(c.get("procedures") or []):
        code = str(pr.get("code") or "").strip()
        if not code:
            flag("BLOCK", f"procedures[{i}]", "missing code")
        elif not (CPT.match(code) or HCPCS.match(code)):
            flag("BLOCK", f"procedures[{i}]", f"'{code}' is not a valid CPT/HCPCS format")
        units = str(pr.get("units") or "").strip()
        if units and not units.isdigit():
            flag("WARN", f"procedures[{i}].units", f"'{units}' is not a number")

    doi, dos, dob = (parse_date(str(c.get(k) or "")) for k in
                     ("date_of_injury", "date_of_service", "dob"))
    today = date.today()
    if c.get("date_of_injury") and not doi:
        flag("BLOCK", "date_of_injury", "unparseable date")
    if c.get("date_of_service") and not dos:
        flag("BLOCK", "date_of_service", "unparseable date")
    if doi and dos and dos < doi:
        flag("BLOCK", "date_of_service", "service predates the injury")
    if doi and doi > today:
        flag("BLOCK", "date_of_injury", "injury date is in the future")
    if dos and dos > today:
        flag("WARN", "date_of_service", "service date is in the future")
    if dob and doi and dob > doi:
        flag("BLOCK", "dob", "born after the date of injury")

    if not (c.get("clinic_name") or "").strip():
        flag("WARN", "clinic_name", "billing provider name missing - needed on a claim")
    if not (c.get("clinic_tax_id") or "").strip():
        flag("WARN", "clinic_tax_id", "billing Tax ID missing - needed on a claim")
    return out


if __name__ == "__main__":
    claim = json.load(open(sys.argv[1]))
    issues = check(claim)
    blocks = [i for i in issues if i["severity"] == "BLOCK"]
    warns = [i for i in issues if i["severity"] == "WARN"]
    print(f"{len(blocks)} blocking, {len(warns)} warnings\n")
    for i in blocks + warns:
        print(f"  [{i['severity']:5}] {i['field']:22} {i['problem']}")
    print("\nVERDICT:", "HOLD - do not submit" if blocks else "clear of mechanical errors")
    json.dump(issues, open("issues.json", "w"), indent=2)
