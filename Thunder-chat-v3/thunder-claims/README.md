# Claims pipeline (prototype)

Scanned document -> OCR -> structured fields -> mechanical validation.

Built against **synthetic patients only**. No real PHI has been near this, and
none should be until the security work below is done and someone qualified has
signed off on compliance.

## Pipeline

    tesseract intake_scan.png ocr --dpi 200
    python3 extract.py ocr.txt      # -> claim.json
    python3 validate.py claim.json  # -> issues.json

## Why the validator exists

The model corrupts things. On the first real run it turned `S46.012A` into
`S$46.012A` and silently dropped the clinic name, Tax ID and NPI. Both were
caught, because format rules and check digits are arithmetic rather than
judgement:

- ICD-10 / CPT / HCPCS format
- NPI Luhn check digit (over the number prefixed with 80840)
- Date logic - service cannot predate injury, nobody is born after their accident
- Required fields for a submittable claim

## What it does NOT do

It cannot tell you whether a code is *clinically* correct for the notes. That
is a human's signature and a fraud exposure if automated. The design is
draft-and-flag, never submit.

## Before this touches a real record

Thunder's API currently has no authentication at all and runs cleartext HTTP.
Both must be fixed first, along with encryption at rest, audit logging, and
tested encrypted backups. Those are technical safeguards only - a documented
risk analysis, written policies, training and BAAs are organisational work that
needs a professional.
