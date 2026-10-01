#!/usr/bin/env python3
"""Fill a company file with made-up patients, so the program can be shown to
someone without empty screens - and without a single real person in it.

    python3 demo_data.py Demo_Office

Twenty invented Florida PIP patients, each with a different crash and
different injuries: rear-ends, T-bones, a cyclist, a pedestrian, a motorcycle,
a rideshare passenger, a teenager in the back seat, a brand-new patient from
yesterday. Each gets diagnoses that fit the injury, the X-rays and treatment a
chiropractic office would actually do for it, a visit history, and claims in
every state the Florida rules produce: paid, partly paid, overdue, a demand
letter out, an IME cut-off, benefits exhausted, under investigation, a bill
going late, care started after the 14 days.

Everything is made up. Phone numbers are 555 numbers, street addresses are
invented, carriers and the attorney firm are fictional, and NPIs are
generated to pass the check digit and belong to nobody. Any resemblance of a
name to a real person is chance - nothing here came from a real record.
Diagnosis codes are real ICD-10-CM codes (checked against the CMS list) so
the claims validate the way real ones would. Dates are relative to today.

It only ever writes into the named company, creates the company if it does
not exist, and refuses to touch a company that already has records.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import claims_web as cw  # noqa: E402
import validate  # noqa: E402
import vault  # noqa: E402

USER = "demo"
TODAY = date.today()


def day(days_ago: int) -> date:
    return TODAY - timedelta(days=days_ago)


def d(days_ago: int) -> str:
    return day(days_ago).strftime("%m/%d/%Y")


def fmt(x: date) -> str:
    return x.strftime("%m/%d/%Y")


def fake_npi(seed: int) -> str:
    """Ten digits that pass the NPI check digit - generated, not looked up."""
    base = f"19{seed:07d}"[:9]
    for last in range(10):
        n = base + str(last)
        if validate.npi_valid(n):
            return n
    raise RuntimeError("no check digit")


# Fictional carriers. Real Florida PIP carriers mail EOBs from PO boxes like these.
PAYERS = [
    ("GULF COAST AUTO INSURANCE", "PO BOX 5501\nTAMPA, FL 33601", "(555) 555-0141", "ATTN PIP DEMANDS\nPO BOX 5502\nTAMPA, FL 33601"),
    ("SUNSHINE STATE CASUALTY", "PO BOX 7710\nORLANDO, FL 32801", "(555) 555-0142", "LEGAL - PIP DEMAND UNIT\nPO BOX 7711\nORLANDO, FL 32801"),
    ("PALMETTO MUTUAL AUTO", "PO BOX 3300\nJACKSONVILLE, FL 32201", "(555) 555-0143", "PIP DEMAND LETTERS\nPO BOX 3301\nJACKSONVILLE, FL 32201"),
    ("BAYSIDE PIP INSURANCE", "PO BOX 9020\nST PETERSBURG, FL 33701", "(555) 555-0144", "CLAIMS LEGAL\nPO BOX 9021\nST PETERSBURG, FL 33701"),
    ("CORAL KEY AUTO & HOME", "PO BOX 4410\nMIAMI, FL 33101", "(555) 555-0145", "PIP DEMAND - CLAIMS LEGAL\nPO BOX 4411\nMIAMI, FL 33101"),
    ("MANATEE TRAIL INSURANCE CO", "PO BOX 2200\nSARASOTA, FL 34230", "(555) 555-0146", "ATTN PIP LITIGATION\nPO BOX 2201\nSARASOTA, FL 34230"),
]
ATTORNEY = ("BAY AREA INJURY LAW (DEMO)", "(555) 555-0190")

CODES = {
    "99203": ("New patient exam, low complexity", 150), "99204": ("New patient exam, moderate complexity", 225),
    "99213": ("Established patient visit", 95), "99214": ("Established patient visit, moderate", 140),
    "98940": ("Chiropractic manipulation, 1-2 regions", 55), "98941": ("Chiropractic manipulation, 3-4 regions", 65),
    "97140": ("Manual therapy, each 15 min", 45), "97110": ("Therapeutic exercise, each 15 min", 50),
    "97112": ("Neuromuscular re-education, each 15 min", 52), "97530": ("Therapeutic activities, each 15 min", 55),
    "97012": ("Mechanical traction", 35), "97014": ("Electrical stimulation, unattended", 30),
    "97035": ("Ultrasound, each 15 min", 32), "97010": ("Hot or cold packs", 15),
    "72050": ("X-ray cervical spine, 4-5 views", 160), "72070": ("X-ray thoracic spine, 2 views", 110),
    "72100": ("X-ray lumbar spine, 2-3 views", 125), "73030": ("X-ray shoulder, 2+ views", 95),
    "73560": ("X-ray knee, 1-2 views", 85), "73110": ("X-ray wrist, 3+ views", 90),
    "73610": ("X-ray ankle, 3+ views", 90), "73502": ("X-ray hip, 2-3 views", 110),
}
XRAY = {"neck": "72050", "midback": "72070", "lowback": "72100", "shoulder": "73030", "knee": "73560",
        "wrist": "73110", "ankle": "73610", "hip": "73502"}
SPINE = {"neck", "midback", "lowback"}
DX = {
    "S13.4XXA": "Sprain of ligaments of cervical spine (whiplash)", "S16.1XXA": "Strain of muscle at neck level",
    "S23.3XXA": "Sprain of ligaments of thoracic spine", "S29.012A": "Strain of muscle of back wall of thorax",
    "S33.5XXA": "Sprain of ligaments of lumbar spine", "S39.012A": "Strain of muscle of lower back",
    "S06.0X0A": "Concussion without loss of consciousness", "S06.0X1A": "Concussion with LOC of 30 minutes or less",
    "G44.309": "Post-traumatic headache", "M54.12": "Radiculopathy, cervical region",
    "M54.17": "Radiculopathy, lumbosacral region", "M54.2": "Cervicalgia", "M54.50": "Low back pain",
    "S43.401A": "Sprain of right shoulder joint", "S43.402A": "Sprain of left shoulder joint",
    "S40.012A": "Contusion of left shoulder", "S80.01XA": "Contusion of right knee", "S80.02XA": "Contusion of left knee",
    "S63.501A": "Sprain of right wrist", "S63.502A": "Sprain of left wrist", "S93.401A": "Sprain of right ankle",
    "S20.211A": "Contusion of right front wall of thorax (seat belt / airbag)", "S70.02XA": "Contusion of left hip",
    "S30.0XXA": "Contusion of lower back and pelvis", "S03.40XA": "Sprain of jaw (TMJ)",
}

# first, last, mi, sex, age, street, city, zip, what happened, diagnoses, body regions,
# visits (99 = still in treatment, through this week), days since the accident, days to first visit,
# how the billing went, EMC, attorney
PEOPLE = [
    ("DANIEL", "WHITAKER", "R", "M", 34, "4120 W BAYVIEW CIR", "TAMPA", "33607",
     "Rear-ended at a red light on Dale Mabry Hwy; driver, belted", ["S13.4XXA", "S16.1XXA", "G44.309"], ["neck"], 14, 150, 2, "paid", "yes", False),
    ("ROSA", "DELGADO", "M", "F", 52, "811 PELICAN WALK DR", "BRANDON", "33511",
     "T-boned at an intersection; front passenger", ["S13.4XXA", "S33.5XXA", "S43.402A"], ["neck", "lowback", "shoulder"], 16, 120, 1, "ime", "yes", True),
    ("TYLER", "BROOKS", "J", "M", 19, "2207 LAKE MIRROR LN", "LAKELAND", "33801",
     "Hit by a car while riding his bicycle; thrown onto the hood", ["S06.0X0A", "S80.01XA", "S63.501A"], ["knee", "wrist"], 99, 30, 3, "active", "yes", False),
    ("LINDA", "MOORE", "K", "F", 67, "1530 HARBOR OAKS CT", "CLEARWATER", "33755",
     "Side-swiped on US-19 while changing lanes; driver", ["S13.4XXA", "M54.12", "S23.3XXA"], ["neck", "midback"], 10, 95, 2, "overdue", "yes", False),
    ("MARCUS", "HILL", "D", "M", 41, "77 CENTRAL PALM AVE N", "ST PETERSBURG", "33701",
     "Rear-ended by a box truck at highway speed; driver", ["S33.5XXA", "M54.17", "S39.012A"], ["lowback"], 12, 170, 2, "demand", "yes", True),
    ("PRIYA", "SHAH", "", "F", 29, "13402 BRUCE B DOWNS PL", "TAMPA", "33612",
     "Rideshare passenger; car struck from behind; went to the ER first", ["S13.4XXA", "S16.1XXA"], ["neck"], 12, 110, 4, "exhausted", "no", False),
    ("JAMES", "O'CONNOR", "P", "M", 58, "9921 RIVERBEND MANOR WAY", "RIVERVIEW", "33569",
     "Pedestrian struck by a reversing car in a parking lot", ["S70.02XA", "S30.0XXA", "S33.5XXA"], ["lowback", "hip"], 10, 200, 3, "paid", "yes", False),
    ("ASHLEY", "NGUYEN", "T", "F", 24, "26015 CYPRESS HOLLOW DR", "WESLEY CHAPEL", "33544",
     "Low-speed head-on collision; driver; airbag deployed", ["S20.211A", "S13.4XXA", "S03.40XA"], ["neck", "midback"], 99, 80, 1, "fee", "yes", False),
    ("ROBERT", "JENKINS", "L", "M", 46, "3008 STRAWBERRY FIELD RD", "PLANT CITY", "33563",
     "Laid his motorcycle down avoiding a car that cut him off", ["S43.401A", "S93.401A", "S80.02XA"], ["shoulder", "ankle"], 99, 75, 2, "investigation", "yes", True),
    ("CARMEN", "RUIZ", "A", "F", 38, "6115 N ARMENIA AVE", "TAMPA", "33604",
     "Rear-ended in stop-and-go traffic on I-275; driver", ["S13.4XXA", "S33.5XXA", "G44.309"], ["neck", "lowback"], 99, 40, 1, "active", "yes", False),
    ("KEVIN", "PATEL", "S", "M", 31, "11530 SUMMIT VIEW CT", "TEMPLE TERRACE", "33617",
     "Car hydroplaned on a wet road into a guardrail; driver", ["S23.3XXA", "S29.012A", "S39.012A"], ["midback", "lowback"], 99, 65, 2, "late", "yes", False),
    ("GRACE", "THOMPSON", "E", "F", 71, "1820 FAIRWAY GREENS BLVD", "SUN CITY CENTER", "33573",
     "Struck on the driver's side while turning left", ["S13.4XXA", "M54.2", "S40.012A"], ["neck", "shoulder"], 16, 230, 2, "paid", "yes", False),
    ("HECTOR", "MORALES", "", "M", 27, "2413 E COLUMBUS DR", "TAMPA", "33605",
     "Back-seat passenger; vehicle rear-ended at highway speed; brief blackout", ["S06.0X1A", "G44.309", "S13.4XXA"], ["neck"], 99, 22, 1, "active", "yes", False),
    ("MEGAN", "FOSTER", "R", "F", 35, "16220 GUNN HWY APT 4", "ODESSA", "33556",
     "Rear-ended in a school pickup line; waited to see if it would pass", ["S16.1XXA", "S13.4XXA"], ["neck"], 99, 50, 19, "late_care", "yes", False),
    ("ANDRE", "WILLIAMS", "J", "M", 44, "1209 E 21ST AVE", "TAMPA", "33605",
     "Delivery van struck by a driver running a stop sign; on the clock", ["S33.5XXA", "S43.402A", "M54.50"], ["lowback", "shoulder"], 12, 140, 2, "paid", "yes", True),
    ("SOFIA", "ALVAREZ", "I", "F", 16, "4517 W SAN MIGUEL ST", "TAMPA", "33629",
     "Back-seat passenger in the family car, rear-ended; mother is the guardian", ["S13.4XXA", "S23.3XXA"], ["neck", "midback"], 99, 18, 2, "active", "yes", False),
    ("WILLIAM", "CARTER", "H", "M", 62, "18044 CORTEZ BLVD", "BROOKSVILLE", "34601",
     "Rear-ended while towing a trailer on SR-50; driver", ["S33.5XXA", "M54.17", "S13.4XXA"], ["lowback", "neck"], 10, 100, 3, "overdue", "yes", False),
    ("JASMINE", "LEE", "", "F", 30, "305 S HYDE PARK AVE", "TAMPA", "33606",
     "Cycling when a parked driver opened a car door into her", ["S40.012A", "S63.502A", "S80.01XA"], ["shoulder", "wrist"], 10, 160, 1, "paid", "yes", False),
    ("BRIAN", "KOWALSKI", "M", "M", 50, "1312 PARSONS AVE", "SEFFNER", "33584",
     "Rear-ended by a driver looking at a phone; driver", ["S13.4XXA", "S16.1XXA", "M54.12"], ["neck"], 12, 130, 2, "fee", "yes", False),
    ("NATALIE", "PRICE", "C", "F", 42, "6703 SEA GRAPE DR", "APOLLO BEACH", "33572",
     "Rear-ended yesterday on the Selmon Expressway; first visit today", ["S13.4XXA", "S16.1XXA"], ["neck"], 1, 1, 1, "new", "", False),
]


def visit_dates(doi_ago: int, delay: int, n: int) -> list[int]:
    """Days-ago of each visit: three a week at first, then twice a week."""
    out, ago = [], doi_ago - delay
    gaps = [2, 2, 3, 2, 2, 3, 3, 4, 3, 4]
    i = 0
    while len(out) < n and ago >= 0:
        out.append(ago)
        ago -= gaps[min(i, len(gaps) - 1)] if i < 6 else 3 + (i % 2)
        i += 1
    return out


def visit_lines(first: bool, regions: list[str], dx_count: int, k: int, concussion: bool) -> list[tuple[str, str]]:
    """(code, pointer) for one visit."""
    spinal = [r for r in regions if r in SPINE]
    ptr = " ".join(str(x) for x in range(1, min(dx_count, 4) + 1))
    lines = []
    if first:
        lines.append(("99204" if concussion else "99203", ptr))
        for r in regions[:2]:
            lines.append((XRAY[r], ptr))
    elif k % 6 == 0:
        lines.append(("99214" if concussion else "99213", ptr))   # re-exam every few weeks
    if spinal:
        lines.append(("98941" if len(spinal) >= 2 else "98940", ptr))
    rot = (["97140", "97110", "97012", "97014"] if spinal else ["97140", "97110", "97035", "97530"])
    if first:
        lines.append((rot[3] if not spinal else "97014", ptr))
    else:
        lines.append((rot[k % 2], ptr))
        lines.append((rot[2 + k % 2] if k > 2 else "97112", ptr))
    return lines


def main(company: str) -> int:
    c = cw.company(company) or cw.new_company(company)
    vault.set_root(c["path"])
    cw._ctx.company = c
    vault.set_actor(USER)
    if vault.ids():
        print(f"{company} already has records - not touching it. Pick a new company name.")
        return 1

    cw.set_settings({"statement": {"return_name": "SUNSHINE SPINE & REHAB (DEMO)", "return_addr1": "100 DEMO WAY SUITE 5",
                                   "return_city": "TAMPA", "return_state": "FL", "return_zip": "33601", "return_phone": "(555) 555-0100"},
                     "setup": {"initial_state": "FL", "default_billing": "SUNSHINE SPINE & REHAB LLC", "default_rendering": "JOHN SAMPLE DC"}})
    billing = {"name": "SUNSHINE SPINE & REHAB LLC", "role": "billing", "npi": fake_npi(1001), "tax_id": "59-0000001",
               "address": "100 DEMO WAY SUITE 5, TAMPA, FL 33601", "phone": "(555) 555-0100"}
    docs = [{"name": "JOHN SAMPLE DC", "role": "treating", "npi": fake_npi(2002)},
            {"name": "ELENA MARSH DC", "role": "treating", "npi": fake_npi(2003)}]
    ref = {"name": "MARY EXAMPLE MD", "role": "referring", "npi": fake_npi(3003)}
    for p in (billing, *docs, ref):
        cw.save("provider", None, p, USER)
    for name, addr, phone, dem in PAYERS:
        cw.save("payer", None, {"name": name, "address": addr, "phone": phone, "demand_address": dem}, USER)
    for code, (desc, chg) in CODES.items():
        cw.save("procedure", None, {"code": code, "modifier": "", "description": desc, "charge": chg, "units": 1}, USER)
    for tname, codes in (("Spinal adjustment visit", ("98941", "97140", "97012")), ("New patient - neck", ("99203", "72050", "98940")),
                         ("Extremity visit", ("97140", "97110", "97035"))):
        cw.save("template", None, {"name": tname, "procedures": [
            {"code": k, "description": CODES[k][0], "charge": CODES[k][1], "units": "1", "pointer": "1"} for k in codes]}, USER)

    pay_queue, counts = [], {"claims": 0, "visits": 0}
    for i, (first, last, mi, sex, age, street, city, zipc, how, dxs, regions, nvis, doi_ago, delay, story, emc, atty) in enumerate(PEOPLE):
        payer = PAYERS[i % len(PAYERS)]
        doc = docs[i % 2]
        visits = visit_dates(doi_ago, delay, nvis)
        counts["visits"] += len(visits)
        first_ago = visits[0]
        dob = day(365 * age + 37 * i + 11)
        notice = fmt(day(first_ago - 6)) if i % 3 == 0 and first_ago >= 6 else ""
        pt = cw.save("patient", None, {
            "last_name": last, "first_name": first, "mi": mi, "dob": fmt(dob), "sex": sex,
            "address": street, "city": city, "state": "FL", "zip": zipc,
            "phone": f"(555) 555-{1100 + i * 7:04d}", "cell_phone": f"(555) 555-{2100 + i * 7:04d}",
            "emergency_contact": ("MOTHER - ANA ALVAREZ" if age < 18 else ""), "emergency_phone": ("(555) 555-2999" if age < 18 else ""),
            "relationship": "Child" if age < 18 else "Self", "accept_assignment": "Yes",
            "insurer": payer[0], "insurer_address": payer[1].replace("\n", ", "), "claim_number": f"{payer[0][:2]}-{26_0000 + i * 1373}",
            "date_of_injury": d(doi_ago), "accident_type": "Auto accident - " + how, "accident_state": "FL",
            "first_treatment": d(first_ago), "pip_notice_sent": notice,
            "emc": emc, "emc_by": (ref["name"] + " " + d(max(first_ago - 10, 0))) if emc == "yes" else "",
            "pip_paid_others": "1650.00" if story == "exhausted" else ("410.00" if i % 4 == 1 else ""),
            "adjuster_name": f"{['K. RIVERS', 'T. OKAFOR', 'D. SALAZAR', 'M. BECK', 'J. TRAN', 'L. HOWARD'][i % 6]} (DEMO)",
            "adjuster_phone": f"(555) 555-{300 + i:04d}",
            "attorney": ATTORNEY[0] if atty else "", "attorney_phone": ATTORNEY[1] if atty else "",
            "dx1": dxs[0], "dx2": dxs[1] if len(dxs) > 1 else "", "dx3": dxs[2] if len(dxs) > 2 else "",
            "clinic_name": billing["name"], "clinic_npi": billing["npi"], "clinic_tax_id": billing["tax_id"],
            "clinic_address": billing["address"], "treating_provider": doc["name"], "treating_npi": doc["npi"],
            "referring_provider": ref["name"], "referring_npi": ref["npi"],
            "reminder": {"ime": "IME done - get the report before the next visit is billed.",
                         "demand": "Demand letter mailed - watch for the green card / payment.",
                         "exhausted": "No EMC on file and PIP is nearly used up - ask Dr. Example for the EMC.",
                         "investigation": "Carrier is investigating - answer records requests fast.",
                         "new": "Brand new - mail the PIP notice of initiation this week.",
                         "late_care": "First visit was 19 days after the crash - PIP may refuse (14-day rule)."}.get(story, ""),
        }, USER)
        pid, p = pt["id"], pt["data"]
        dx = [{"code": x, "description": DX[x]} for x in dxs]

        # service lines, visit by visit, packed into claims of at most 6 lines (one CMS-1500 each)
        concussion = any(x.startswith("S06") for x in dxs)
        groups, cur = [], []
        for k, v in enumerate(visits):
            lines = [{"date": d(v), "code": code, "description": CODES[code][0], "charge": f"{CODES[code][1]:.2f}",
                      "units": "1", "pointer": ptr} for code, ptr in visit_lines(k == 0, regions, len(dxs), k, concussion)]
            if cur and len(cur) + len(lines) > 6:
                groups.append(cur)
                cur = []
            cur += lines[:6]
        if cur:
            groups.append(cur)

        ime_ago = doi_ago - 60       # the IME cut-off date for that story
        used = 1650.0 if story == "exhausted" else 0.0
        limit = 2500.0 if emc != "yes" else 10000.0
        demand_done = False
        for g, lines in enumerate(groups):
            first_dos = max(int((TODAY - datetime_of(x["date"])).days) for x in lines)
            last_dos = min(int((TODAY - datetime_of(x["date"])).days) for x in lines)
            sent_ago = last_dos - 7          # the office bills weekly, so the last week or so is not billed yet
            tr = {"billing": "draft", "method": "paper"}
            billed = sent_ago >= 3 and story != "new" and not (story == "late" and g == 1)   # one old claim never mailed
            if billed:
                tr.update(billing="sent", sent_date=d(sent_ago), received_date=d(max(sent_ago - 4, 0)), last_printed=d(sent_ago))
            pay = None
            if billed and sent_ago >= 30:
                charge = sum(float(x["charge"]) for x in lines)
                if story in ("paid", "active", "late", "late_care"):
                    pay = ("full", sent_ago - 26)
                elif story == "fee":
                    pay = ("fee", sent_ago - 26)
                    tr.update(denial_code="fee", denial_date=d(sent_ago - 26), denial_reason="Reduced to 200% of the Medicare Part B fee schedule")
                elif story == "ime":
                    if first_dos > ime_ago:
                        pay = ("full", sent_ago - 26)
                    else:
                        tr.update(billing="denied", denial_code="ime", denial_date=d(sent_ago - 18),
                                  denial_reason=f"Benefits withdrawn per IME dated {d(ime_ago)}")
                elif story == "exhausted":
                    room = limit - used
                    if room > 1:
                        paid = min(charge * 0.68, room)
                        used += paid
                        pay = ("cap", sent_ago - 26, paid)
                    else:
                        tr.update(billing="denied", denial_code="exhausted", denial_date=d(sent_ago - 20),
                                  denial_reason="PIP benefits exhausted ($2,500 - no EMC determination on file)")
                elif story == "demand" and not demand_done:
                    demand_done = True
                    tr.update(demand_address=payer[3].replace("\n", ", "), demand_sent=d(15),
                              demand_cert=f"9407 1000 0000 {4000 + i:04d} {1000 + g:04d} 0{g}", demand_received=d(11))
                elif story == "investigation":
                    tr.update(fraud_notice=d(max(sent_ago - 20, 1)))
            claim = {**{k: p.get(k, "") for k in ("patient_name", "account_number", "dob", "sex", "phone", "insurer", "insurer_address", "claim_number",
                                                  "date_of_injury", "accident_type", "accident_state", "first_treatment", "pip_notice_sent",
                                                  "adjuster_name", "adjuster_phone", "clinic_name", "clinic_npi", "clinic_tax_id", "clinic_address",
                                                  "treating_provider", "treating_npi", "referring_provider", "referring_npi", "attorney", "attorney_phone")},
                     "patient_id": pid, "address": f"{street}, {city}, FL {zipc}", "insurance_type": "other", "place_of_service": "11",
                     "date_of_service": lines[0]["date"], "diagnoses": dx, "procedures": lines, "tracking": tr}
            saved = cw.save("claim", None, claim, USER)
            counts["claims"] += 1
            if pay:
                pay_queue.append((payer[0], saved["id"], lines, pay))

    # payments, as the carriers' checks would have come in
    for n, (payer, cid, lines, pay) in enumerate(pay_queue):
        how, when = pay[0], pay[1]
        alloc, total = [], 0.0
        left = pay[2] if how == "cap" else None
        for li, ln in enumerate(lines):
            chg = float(ln["charge"])
            paid = round(chg * (0.55 if how == "fee" else 0.68), 2)
            if left is not None:
                paid = round(max(min(paid, left), 0), 2)
                left -= paid
            entry = {"claim_id": cid, "line": li, "paid": f"{paid:.2f}"}
            if how != "fee":   # full: 80% of the fee schedule paid, the rest is the contractual reduction
                entry["adjustments"] = [{"amt": f"{chg - paid:.2f}", "group": "CO", "reason": "45"}]
            alloc.append(entry)
            total += paid
        cw.save("payment", None, {"source": "payer", "payer": payer, "date": d(max(when, 1)), "method": "CHECK" if n % 3 else "EFT",
                                  "ref": f"{55000 + n * 17}", "amount": f"{total:.2f}", "lines": alloc}, USER)

    for subj, due, who in (("Call Gulf Coast about Linda Moore's overdue bills", 0, "blayne"),
                           ("Get the IME report for Rosa Delgado", 2, "blayne"),
                           ("Mail PIP notice of initiation - Natalie Price", 1, "blayne"),
                           ("Ask Dr. Example for an EMC on Priya Shah", 3, "blayne"),
                           ("Check green card on Marcus Hill demand letter", 5, "blayne")):
        cw.save("task", None, {"subject": subj, "due": d(-due), "start": d(0), "status": "Not Started", "priority": "High" if due < 2 else "Normal",
                               "assigned": who, "about": ""}, USER)
    n = {k: sum(1 for _ in cw.records(k)) for k in ("patient", "claim", "payment", "payer", "procedure", "template", "task")}
    print(f"{company}: " + ", ".join(f"{v} {k}s" for k, v in n.items()) + f", {counts['visits']} visits")
    print("Everything in it is made up. Open it from the orange Thunder Claims button > Companies.")
    return 0


def datetime_of(s: str) -> date:
    m, dd, y = s.split("/")
    return date(int(y), int(m), int(dd))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: demo_data.py <CompanyName>   (e.g. Demo_Office)")
    raise SystemExit(main(sys.argv[1]))
