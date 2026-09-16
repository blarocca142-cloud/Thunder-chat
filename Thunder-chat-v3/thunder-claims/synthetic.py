#!/usr/bin/env python3
"""Generate fake patients, and render them as documents that look scanned.

Every person, clinic, insurer and claim number here is invented. Nothing in
this file came from a real record, and nothing real should ever be added to it.
The names are drawn from a deliberately wide pool because a system that reads
"Smith" perfectly and mangles "Nguyen" or "Okonkwo" is not working.

The rendering matters as much as the data. A crisp PNG of a form would flatter
the pipeline - real intake paperwork arrives rotated a degree, a little dark,
photocopied twice, with speckle. So the pages are degraded on purpose. An
accuracy number measured on clean images would be a number about nothing.

Each document is written alongside a `.truth.json` holding exactly what the
extractor is supposed to come back with, which is what makes measurement
possible at all.

    ./synthetic.py 25 out/
"""
from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
REGULAR = FONT_DIR / "DejaVuSans.ttf"
BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"
MONO = FONT_DIR / "DejaVuSansMono.ttf"

FIRST = ["Marisol", "DeAndre", "Nguyen", "Priya", "Tomasz", "Aaliyah", "Seamus",
         "Xiomara", "Ravi", "Fiona", "Jamal", "Ingrid", "Hector", "Yusuf",
         "Clara", "Dimitri", "Ayesha", "Bartholomew", "Lucia", "Kwame",
         "Siobhan", "Rosalinda", "Ezekiel", "Mei", "Oluwaseun"]
LAST = ["Rodriguez", "Okonkwo", "Van Der Berg", "Sandoval", "Kowalczyk",
        "Nakamura", "O'Sullivan", "Hernandez-Cruz", "Patel", "Abernathy",
        "Whitfield", "Lindqvist", "Castellanos", "Al-Rashid", "Petrov",
        "Fitzgerald", "Mbeki", "DiFrancesco", "Choi", "Garibaldi"]
STREETS = ["Maple", "Sycamore", "Industrial", "Old Mill", "Beacon", "Larkspur",
           "Cortland", "Fairbanks", "Winthrop", "Delancey"]
TOWNS = [("Springfield", "OH", "45502"), ("Fairview", "PA", "16415"),
         ("Riverton", "NJ", "08077"), ("Glenwood", "IL", "60425"),
         ("Ashford", "CT", "06278"), ("Dunmore", "PA", "18512")]
# Invented insurers. Any resemblance to a real carrier is not intended.
INSURERS = ["Keystone Mutual Casualty", "Northvale Indemnity",
            "Harborline Auto Group", "Copperfield Assurance",
            "Tri-State Liability Partners", "Meridian Casualty of Ohio"]
CLINICS = ["Riverbend Spine & Injury", "Lakeshore Rehabilitation Associates",
           "Cornerstone Chiropractic Group", "Maplewood Physical Medicine",
           "Anchor Point Injury Care"]
ACCIDENTS = ["Motor vehicle accident - rear ended at stoplight",
             "Motor vehicle accident - T-bone at intersection",
             "Slip and fall - wet floor, grocery",
             "Work injury - lifting, warehouse",
             "Motor vehicle accident - sideswipe, merging"]
# Real-format codes for soft-tissue injury work. Format is what is being
# tested, not clinical judgement - no code here is a recommendation.
DX = [("S13.4XXA", "Sprain of ligaments of cervical spine, initial encounter"),
      ("S33.5XXA", "Sprain of ligaments of lumbar spine, initial encounter"),
      ("M54.2", "Cervicalgia"),
      ("M54.51", "Vertebrogenic low back pain"),
      ("S16.1XXA", "Strain of muscle of neck, initial encounter"),
      ("G44.309", "Post-traumatic headache, unspecified, not intractable"),
      ("S39.012A", "Strain of muscle of lower back, initial encounter"),
      ("M99.01", "Segmental dysfunction of thoracic region")]
CPT = [("98940", "Chiropractic manipulative treatment, 1-2 regions", 1),
       ("98941", "Chiropractic manipulative treatment, 3-4 regions", 1),
       ("97110", "Therapeutic exercise, each 15 minutes", 2),
       ("97140", "Manual therapy techniques, each 15 minutes", 1),
       ("97012", "Mechanical traction", 1),
       ("97014", "Electrical stimulation, unattended", 1),
       ("99203", "Office visit, new patient, low complexity", 1)]
SUFFIX = ["DC", "PT", "MD", "DO"]


def npi() -> str:
    """A real NPI carries a Luhn check digit over the number prefixed 80840.
    Generating invalid ones would make the validator look better than it is."""
    body = [random.randint(0, 9) for _ in range(9)]
    digits = [int(c) for c in "80840"] + body
    total, parity = 0, (len(digits) + 1) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return "".join(map(str, body)) + str((10 - total % 10) % 10)


def make_patient(seed: int) -> dict:
    random.seed(seed)
    first, last = random.choice(FIRST), random.choice(LAST)
    town, st, zipc = random.choice(TOWNS)
    dob = date(random.randint(1948, 2006), random.randint(1, 12), random.randint(1, 28))
    injury = date(2026, random.randint(1, 8), random.randint(1, 28))
    service = injury + timedelta(days=random.randint(1, 30))
    clinic = random.choice(CLINICS)
    dxs = random.sample(DX, random.randint(2, 4))
    procs = random.sample(CPT, random.randint(2, 4))
    return {
        "patient_name": f"{first} {last}",
        "dob": dob.strftime("%m/%d/%Y"),
        "sex": random.choice(["M", "F"]),
        "address": f"{random.randint(12, 9880)} {random.choice(STREETS)} "
                   f"{random.choice(['St', 'Ave', 'Rd', 'Ln'])}, {town}, {st} {zipc}",
        "phone": f"({random.randint(201, 989)}) 555-{random.randint(100, 999):04d}",
        "insurer": random.choice(INSURERS),
        "claim_number": f"{random.choice('KNHCTM')}{random.randint(10, 99)}-2026-"
                        f"{random.randint(100000, 999999)}",
        "date_of_injury": injury.strftime("%m/%d/%Y"),
        "date_of_service": service.strftime("%m/%d/%Y"),
        "referring_provider": f"{random.choice(FIRST)[0]}. {random.choice(LAST)}, "
                              f"{random.choice(SUFFIX)}",
        "referring_npi": npi(),
        "treating_provider": f"{random.choice(FIRST)[0]}. {random.choice(LAST)}, "
                             f"{random.choice(SUFFIX)}",
        "treating_npi": npi(),
        "clinic_name": clinic,
        "clinic_tax_id": f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
        "clinic_npi": npi(),
        "accident_type": random.choice(ACCIDENTS),
        "diagnoses": [{"code": c, "description": d} for c, d in dxs],
        "procedures": [{"code": c, "description": d, "units": str(u)}
                       for c, d, u in procs],
    }


def render(p: dict, out: Path, seed: int) -> None:
    """Draw a superbill, then make it look like it came off a scanner."""
    random.seed(seed + 9000)
    W, H = 1700, 1500
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    f = lambda path, size: ImageFont.truetype(str(path), size)  # noqa: E731
    head, bold, reg, mono = f(BOLD, 44), f(BOLD, 26), f(REGULAR, 26), f(MONO, 25)

    y = 70
    d.text((90, y), p["clinic_name"].upper(), font=head, fill=0)
    y += 58
    d.text((90, y), f"Tax ID: {p['clinic_tax_id']}    Facility NPI: {p['clinic_npi']}",
           font=reg, fill=0)
    y += 44
    d.text((90, y), "PATIENT ENCOUNTER / SUPERBILL", font=bold, fill=0)
    y += 20
    d.line((90, y + 22, W - 90, y + 22), fill=0, width=3)
    y += 60

    def field(label: str, value: str, x: int, yy: int, lw: int = 230) -> None:
        d.text((x, yy), label, font=bold, fill=0)
        # Push the value past the label if the label is long. A real form does
        # not print them on top of each other, and letting that happen here
        # would understate accuracy by testing against damage no scan has.
        start = x + max(lw, int(d.textlength(label, font=bold)) + 18)
        d.text((start, yy), value, font=reg, fill=0)

    rows = [
        ("Patient Name:", p["patient_name"], "Date of Birth:", p["dob"]),
        ("Sex:", p["sex"], "Phone:", p["phone"]),
        ("Address:", p["address"], None, None),
        ("Insurance Carrier:", p["insurer"], None, None),
        ("Claim Number:", p["claim_number"], "Date of Injury:", p["date_of_injury"]),
        ("Date of Service:", p["date_of_service"], None, None),
        ("Mechanism of Injury:", p["accident_type"], None, None),
        ("Referring Provider:", p["referring_provider"], "NPI:", p["referring_npi"]),
        ("Treating Provider:", p["treating_provider"], "NPI:", p["treating_npi"]),
    ]
    for l1, v1, l2, v2 in rows:
        field(l1, v1, 90, y, 280)
        if l2:
            field(l2, v2, 1030, y, 190)
        y += 52

    y += 30
    d.text((90, y), "DIAGNOSES (ICD-10)", font=bold, fill=0)
    y += 44
    for i, dx in enumerate(p["diagnoses"], 1):
        d.text((110, y), f"{i}.", font=reg, fill=0)
        d.text((165, y), dx["code"], font=mono, fill=0)
        d.text((420, y), dx["description"], font=reg, fill=0)
        y += 46

    y += 30
    d.text((90, y), "PROCEDURES (CPT)", font=bold, fill=0)
    y += 44
    d.text((110, y), "CODE", font=bold, fill=0)
    d.text((420, y), "DESCRIPTION", font=bold, fill=0)
    d.text((1450, y), "UNITS", font=bold, fill=0)
    y += 44
    for pr in p["procedures"]:
        d.text((110, y), pr["code"], font=mono, fill=0)
        d.text((420, y), pr["description"], font=reg, fill=0)
        d.text((1500, y), pr["units"], font=mono, fill=0)
        y += 46

    y += 60
    d.line((90, y, 800, y), fill=0, width=2)
    d.text((90, y + 12), "Provider signature", font=reg, fill=0)
    d.line((1000, y, W - 90, y), fill=0, width=2)
    d.text((1000, y + 12), "Date", font=reg, fill=0)

    # --- make it a scan, not a screenshot -------------------------------
    img = img.rotate(random.uniform(-0.8, 0.8), resample=Image.BICUBIC,
                     fillcolor=255, expand=False)
    img = img.filter(ImageFilter.GaussianBlur(random.uniform(0.3, 0.8)))
    px = img.load()
    # Speckle. Sparse, because real scanner noise is sparse - a uniform wash
    # would be easier for OCR than the real thing, not harder.
    for _ in range(int(W * H * 0.0015)):
        x, yy = random.randrange(W), random.randrange(H)
        px[x, yy] = random.choice((0, 0, 255))
    # Photocopier contrast drift: slightly grey paper, slightly grey ink.
    img = img.point(lambda v: min(255, max(0, int(v * random.uniform(0.92, 0.99) + 8))))
    img.convert("RGB").save(out, "JPEG", quality=random.randint(62, 80))


def main() -> int:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "synthetic")
    out.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        p = make_patient(1000 + i)
        stem = out / f"case{i:03d}"
        render(p, stem.with_suffix(".jpg"), 1000 + i)
        stem.with_suffix(".truth.json").write_text(json.dumps(p, indent=2))
    print(f"{count} synthetic cases -> {out}/")
    print("Invented people. No real patient data is involved at any point.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
