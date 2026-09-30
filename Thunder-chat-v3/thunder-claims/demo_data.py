#!/usr/bin/env python3
"""Fill a company file with made-up data, so the program can be shown to
someone without empty screens - and without a single real person in it.

    python3 demo_data.py Demo_Office

Every name, address, phone number, carrier, NPI and claim number here is
invented (phones are 555 numbers, NPIs are generated to pass the check digit
and belong to nobody on purpose). Dates are relative to today, so the Florida
PIP clocks show a realistic mix: bills due soon, one late, carriers overdue,
a demand letter out, some paid.

It only ever writes into the named company, creates the company if it does
not exist, and refuses to touch a company that already has records.
"""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import claims_web as cw  # noqa: E402
import validate  # noqa: E402
import vault  # noqa: E402

USER = "demo"
TODAY = date.today()


def d(days_ago: int) -> str:
    return (TODAY - timedelta(days=days_ago)).strftime("%m/%d/%Y")


def fake_npi(seed: int) -> str:
    """Ten digits that pass the NPI check digit - generated, not looked up."""
    base = f"19{seed:07d}"[:9]
    for last in range(10):
        n = base + str(last)
        if validate.npi_valid(n):
            return n
    raise RuntimeError("no check digit")


PAYERS = [
    ("GULF COAST AUTO INSURANCE", "PO BOX 5501\nTAMPA, FL 33601", "(555) 555-0141", "ATTN PIP DEMANDS\nPO BOX 5502\nTAMPA, FL 33601"),
    ("SUNSHINE STATE CASUALTY", "PO BOX 7710\nORLANDO, FL 32801", "(555) 555-0142", "LEGAL - PIP DEMAND UNIT\nPO BOX 7711\nORLANDO, FL 32801"),
    ("PALMETTO MUTUAL AUTO", "PO BOX 3300\nJACKSONVILLE, FL 32201", "(555) 555-0143", "PIP DEMAND LETTERS\nPO BOX 3301\nJACKSONVILLE, FL 32201"),
    ("BAYSIDE PIP INSURANCE", "PO BOX 9020\nST PETERSBURG, FL 33701", "(555) 555-0144", "CLAIMS LEGAL\nPO BOX 9021\nST PETERSBURG, FL 33701"),
]
CODES = [("99203", "", "New patient exam, low complexity", 150), ("99213", "", "Established patient visit", 95),
         ("98940", "", "Chiropractic manipulation, 1-2 regions", 55), ("98941", "", "Chiropractic manipulation, 3-4 regions", 65),
         ("97140", "", "Manual therapy, each 15 min", 45), ("97110", "", "Therapeutic exercise, each 15 min", 50),
         ("97012", "", "Mechanical traction", 35), ("97014", "", "Electrical stimulation, unattended", 30),
         ("72040", "", "X-ray cervical spine, 2-3 views", 120)]
FIRST = ["AVERY", "JORDAN", "MORGAN", "CASEY", "RILEY", "TAYLOR", "QUINN", "HARPER", "ROWAN", "EMERSON", "SKYLER", "PARKER"]
LAST = ["SAMPLE", "EXAMPLE", "TESTER", "DEMOSON", "PLACEHOLDER", "FICTION", "MADEUP", "NOTREAL", "SPECIMEN", "PRETEND", "MOCKLEY", "DUMMIT"]
DX = [("S13.4XXA", "Sprain of ligaments of cervical spine"), ("S33.5XXA", "Sprain of ligaments of lumbar spine"),
      ("S16.1XXA", "Strain of muscle at neck level"), ("M54.2", "Cervicalgia"), ("S39.012A", "Strain of muscle of lower back")]


def main(company: str) -> int:
    c = cw.company(company) or cw.new_company(company)
    vault.set_root(c["path"])
    cw._ctx.company = c
    vault.set_actor(USER)
    if any(vault.records_dir().glob("*.rec")):
        print(f"{company} already has records - not touching it. Pick a new company name.")
        return 1
    rnd = random.Random(20260930)

    cw.set_settings({"statement": {"return_name": "SUNSHINE SPINE & REHAB (DEMO)", "return_addr1": "100 DEMO WAY SUITE 5",
                                   "return_city": "TAMPA", "return_state": "FL", "return_zip": "33601", "return_phone": "(555) 555-0100"},
                     "setup": {"initial_state": "FL", "default_billing": "SUNSHINE SPINE & REHAB LLC", "default_rendering": "JOHN SAMPLE DC"}})
    billing = {"name": "SUNSHINE SPINE & REHAB LLC", "role": "billing", "npi": fake_npi(1001), "tax_id": "59-0000001",
               "address": "100 DEMO WAY SUITE 5, TAMPA, FL 33601", "phone": "(555) 555-0100"}
    rend = {"name": "JOHN SAMPLE DC", "role": "treating", "npi": fake_npi(2002)}
    ref = {"name": "MARY EXAMPLE MD", "role": "referring", "npi": fake_npi(3003)}
    for p in (billing, rend, ref):
        cw.save("provider", None, p, USER)
    for name, addr, phone, dem in PAYERS:
        cw.save("payer", None, {"name": name, "address": addr, "phone": phone, "demand_address": dem}, USER)
    for code, mod, desc, chg in CODES:
        cw.save("procedure", None, {"code": code, "modifier": mod, "description": desc, "charge": chg, "units": 1}, USER)
    by = {x[0]: x for x in CODES}
    cw.save("template", None, {"name": "Adjustment visit", "procedures": [
        {"code": k, "description": by[k][2], "charge": by[k][3], "units": "1", "pointer": "1"} for k in ("98941", "97140", "97012")]}, USER)
    cw.save("template", None, {"name": "New patient exam", "procedures": [
        {"code": k, "description": by[k][2], "charge": by[k][3], "units": "1", "pointer": "1"} for k in ("99203", "72040", "98941")]}, USER)

    # each patient: (days since accident, visits' days-ago, how far the billing got)
    stories = [
        (20, [16, 14, 12], "draft"),               # bill soon
        (70, [60, 58], "draft_late"),             # past the 35-day window
        (45, [40, 38, 36], "sent_recent"),         # carrier's clock running
        (95, [85, 83], "sent_overdue"),            # carrier overdue - demand allowed
        (120, [110, 108, 106], "paid"),            # paid, fee-schedule reduction
        (90, [80, 78], "partial"),                 # partly paid
        (150, [140, 138], "denied_ime"),           # IME cut-off
        (160, [150, 148], "demand"),               # demand letter out
        (30, [25, 23], "sent_recent"),
        (200, [190, 188, 186], "paid"),
        (15, [10], "draft"),
        (110, [100, 98], "sent_overdue"),
    ]
    pay_lines = []
    for i, (doi_ago, visits, story) in enumerate(stories):
        payer = PAYERS[i % len(PAYERS)]
        first, last = FIRST[i], LAST[i]
        dob = d(365 * rnd.randint(22, 64) + rnd.randint(0, 300))
        emc = "yes" if i % 3 else "no"
        pt = cw.save("patient", None, {
            "last_name": last, "first_name": first, "dob": dob, "sex": "M" if i % 2 else "F",
            "address": f"{100 + i * 7} PRETEND ST", "city": "TAMPA", "state": "FL", "zip": "33602", "phone": f"(555) 555-01{10 + i:02d}",
            "insurer": payer[0], "insurer_address": payer[1].replace("\n", ", "), "claim_number": f"DEMO-{7000 + i * 13}",
            "date_of_injury": d(doi_ago), "accident_type": "Motor vehicle accident", "accident_state": "FL",
            "first_treatment": d(max(visits)), "pip_notice_sent": d(max(visits) - 10) if i % 4 == 0 else "",
            "emc": emc, "emc_by": "MARY EXAMPLE MD" if emc == "yes" else "", "adjuster_name": f"ADJUSTER {LAST[(i + 3) % 12]}",
            "adjuster_phone": f"(555) 555-02{10 + i:02d}", "clinic_name": billing["name"], "clinic_npi": billing["npi"],
            "clinic_tax_id": billing["tax_id"], "clinic_address": billing["address"], "treating_provider": rend["name"], "treating_npi": rend["npi"],
            "referring_provider": ref["name"], "referring_npi": ref["npi"]}, USER)
        pid, p = pt["id"], pt["data"]
        dx = [{"code": DX[i % 5][0], "description": DX[i % 5][1]}, {"code": DX[(i + 2) % 5][0], "description": DX[(i + 2) % 5][1]}]
        lines = []
        for j, v in enumerate(sorted(visits, reverse=True)):
            codes = ["99203", "72040", "98941"] if j == 0 else ["98941", "97140", "97012"]
            for k in codes:
                lines.append({"date": d(v), "code": k, "description": by[k][2], "charge": f"{by[k][3]:.2f}", "units": "1", "pointer": "1 2"})
        lines = lines[:6]
        tr = {"billing": "draft", "method": "paper"}
        first_dos = max(visits)
        if story in ("sent_recent", "sent_overdue", "paid", "partial", "denied_ime", "demand"):
            sent_ago = first_dos - 12
            tr.update(billing="sent", sent_date=d(sent_ago), received_date=d(sent_ago - 5), last_printed=d(sent_ago))
        if story == "denied_ime":
            tr.update(billing="denied", denial_date=d(20), denial_code="ime", denial_reason="Benefits withdrawn per IME dated " + d(30))
        if story == "demand":
            tr.update(demand_address=payer[3].replace("\n", ", "), demand_sent=d(12), demand_cert="9407 1000 0000 0000 0000 01", demand_received=d(8))
        claim = {**{k: p.get(k, "") for k in ("patient_name", "account_number", "dob", "sex", "phone", "insurer", "insurer_address", "claim_number",
                                              "date_of_injury", "accident_type", "accident_state", "first_treatment", "pip_notice_sent",
                                              "adjuster_name", "adjuster_phone", "clinic_name", "clinic_npi", "clinic_tax_id", "clinic_address",
                                              "treating_provider", "treating_npi", "referring_provider", "referring_npi")},
                 "patient_id": pid, "address": f"{p['address']}, TAMPA, FL 33602", "insurance_type": "other", "place_of_service": "11",
                 "date_of_service": d(first_dos), "diagnoses": dx, "procedures": lines, "tracking": tr}
        saved = cw.save("claim", None, claim, USER)
        if story in ("paid", "partial"):
            pay_lines.append((payer[0], saved["id"], lines, story, first_dos))

    # payments: PIP pays 80% of the fee schedule; the rest is a CO-45 reduction
    for n, (payer, cid, lines, story, first_dos) in enumerate(pay_lines):
        alloc, total = [], 0.0
        for li, ln in enumerate(lines):
            chg = float(ln["charge"])
            if story == "partial" and li % 2:
                continue
            paid = round(chg * 0.8 * 0.85, 2)
            alloc.append({"claim_id": cid, "line": li, "paid": f"{paid:.2f}",
                          "adjustments": [{"amt": f"{chg - paid:.2f}", "group": "CO", "reason": "45"}]})
            total += paid
        cw.save("payment", None, {"source": "payer", "payer": payer, "date": d(max(first_dos - 45, 3)), "method": "CHECK" if n % 2 else "EFT",
                                  "ref": f"DEMO{55000 + n}", "amount": f"{total:.2f}", "lines": alloc}, USER)

    for subj, due, about in (("Call Gulf Coast about overdue bill", 1, ""), ("Get IME report for denied claim", 3, ""),
                             ("Mail PIP notice of initiation for new patient", 0, "")):
        cw.save("task", None, {"subject": subj, "due": d(-due), "start": d(0), "status": "Not Started", "priority": "Normal",
                               "assigned": "blayne", "about": about}, USER)
    counts = {k: sum(1 for _ in cw.records(k)) for k in ("patient", "claim", "payment", "payer", "procedure", "template", "task")}
    print(f"{company}: " + ", ".join(f"{v} {k}s" for k, v in counts.items()))
    print("Everything in it is made up. Open it from the orange Thunder Claims button > Companies.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: demo_data.py <CompanyName>   (e.g. Demo_Office)")
    raise SystemExit(main(sys.argv[1]))
