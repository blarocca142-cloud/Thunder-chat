# Claims pipeline (prototype)

Scanned document -> OCR -> structured fields -> mechanical validation.

Built against **synthetic patients only**. No real PHI has been near this, and
none should be until the security work below is done and someone qualified has
signed off on compliance.

## Pipeline

    tesseract intake_scan.png ocr --dpi 200
    python3 extract.py ocr.txt      # -> claim.json
    python3 validate.py claim.json  # -> issues.json
    python3 vault.py put claim001 claim.json --index last_name --index claim_number
    rm claim.json                   # the plaintext copy is the weak link

The last two steps are the point. Everything before them exists in a dozen
products; a claims store that is local *and* encrypted at rest, with lookup
that works without decrypting, is the part nobody sells - because the market
went to the cloud, and the cloud needs a BAA.

## Measured accuracy

Numbers, not impressions. `synthetic.py` invents patients and renders them as
superbills that are then degraded on purpose - rotated, blurred, speckled,
re-compressed - because an accuracy figure measured on a crisp PNG is a figure
about nothing. Each page ships with the truth it was drawn from, so the
pipeline can be scored against it.

    ./synthetic.py 25 cases/
    ./evaluate.py cases/          # raw extractions are cached after the first run
    ./evaluate.py cases/ --no-repair

**25 synthetic documents, ~8s per page:**

| | |
|---|---|
| patient_name, dob, sex, insurer, clinic_name, clinic_npi | 100% |
| NPIs (referring / treating) | 92% |
| claim_number, tax ID, both dates | 96-100% |
| **diagnosis codes** | **94% recall, 94% precision** |
| **procedure codes** | **100% recall, 100% precision** |
| every field on the page exactly right | 8/25 |
| wrong, and nothing flagged it | 6/25 |

The last row is the one that matters and the one to keep driving down. The
others are mostly omissions, and an omission is caught - a required field left
empty is a blocking error. A wrong value that passes every check is what
becomes a wrong claim.

### What the measurement actually found

**The model is not the weak link. OCR is.** Every silent error traced back to
tesseract misreading the page, with the model copying it faithfully - which is
what it was told to do:

    Sex: E                      <- F misread as E
    |. Mbeki, DO                <- I misread as a pipe
    Motor vehicle.accident      <- stray period
    $39.012A / 644.309          <- S and G misread in code positions

Preprocessing does not fix this. Median filtering, 2x upscaling, binarisation
and autocontrast were all tried, and the `$` survives every one of them.

What fixes it is `repair.py`, which uses the field's format as the constraint.
Measured, same pages, same extractions:

| | diagnosis codes |
|---|---|
| no repair | 45% |
| with repair | **94%** |

That is the single largest improvement in the pipeline and it costs no GPU time
at all.

### Honesty about the metric

Scoring counts a stray period in an address as equal to a wrong NPI, which
would make the headline number meaningless - one is noise, the other is a
rejected claim. So cosmetic differences are reported separately (14 of them
across 25 documents). Free text is compared on its words; codes, dates and
numbers are compared strictly.

The remaining silent errors are free-text OCR noise: a dropped phone number, a
pipe in place of an initial, punctuation inside a mechanism-of-injury phrase.
None would change what is billed, but they are still counted, because deciding
they do not matter is not the pipeline's call to make.

The obvious next step is looking codes up in the real CMS ICD-10 release rather
than only checking their shape. That turns "well-formed" into "real", and it
needs the code list on disk.

## The actual tool

    ./vault.py init                  once, ever - creates the master key
    ./intake.py scans/               a folder in, a review queue out
    ./review.py                      what is waiting, worst first
    ./review.py <record>             open one claim (decrypted and audited)

`intake.py` OCRs each scan (images or PDFs), extracts, repairs OCR damage,
validates, and files the result straight into the encrypted vault. Documents
are identified by content hash, so the same scan re-filed under a new name is
not billed twice, and a re-run skips what is already done.

Everything lands in one of three piles:

| | |
|---|---|
| **BLOCK** | mechanically wrong - bad NPI check digit, malformed code, impossible date. Cannot be billed. |
| **REVIEW** | passed the checks, but something was repaired or is missing. A human reads it. |
| **CLEAN** | passed everything with nothing repaired. **Still a draft.** |

Nothing is ever submitted. A repaired code always means REVIEW, because a
repair is a guess the format forced - correct, but not something to bill on
without a glance.

### The review queue holds no patient data

It was tempting to put names in it so the list reads nicely. That would have
made the queue plaintext PHI sitting beside the encrypted records it exists to
protect. It carries file name, record id, status and reasons only - not even
codes and dates, since a diagnosis with a date is identifying enough in a
small practice. Names come from the vault via `review.py`, where the read is
decrypted and **audited**, because looking at a patient's data is an event
worth recording even when it is you.

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

## The vault

`vault.py` is the encrypted record store. `test_vault.py` is 34 checks against
it, most of them attacks rather than round trips.

    ./vault.py init                         # master key, once
    ./vault.py put ID file.json --index last_name
    ./vault.py get ID
    ./vault.py find last_name Rodriguez     # nothing decrypted
    ./vault.py list                         # nothing decrypted
    ./vault.py verify                       # open everything
    ./vault.py rotate                       # new key generation
    ./vault.py backup /media/usb/vault.tvb
    ./vault.py restore /media/usb/vault.tvb /tmp/check

### How it is built, and why

**Envelope encryption.** Each record has its own AES-256-GCM data key, wrapped
by a master key kept in `~/.thunder/keys/vault.key` - deliberately *outside*
the vault directory, because a stolen data directory that carries its own key
is not encrypted in any useful sense.

Rotation therefore rewraps a few hundred small keys instead of re-encrypting
every record. That is the difference between key rotation being a routine
command and being something that never actually happens.

**Authenticated, with the record id bound in.** GCM means a modified file
fails loudly instead of returning quietly wrong data, which on a claim is the
difference between a rejection and a wrong leg. The record id is authenticated
too, so one patient's ciphertext cannot be moved onto another patient's record
and still open. Both are tested.

**Blind indexes.** Encrypted records normally cannot be searched without
decrypting all of them. Instead each indexed field stores an HMAC of its
normalised value under a key derived separately from the master key, so exact
match works with nothing decrypted. Lookup survives spacing, case and accents.

**Audit on every access**, successful or not, including authentication
failures. Record ids only - a name in the log would make the log itself PHI
sitting in plaintext.

### Backups

`backup` writes one passphrase-encrypted file containing the records **and the
key**, because a backup without the key restores nothing. That means the
passphrase is the only thing between a stolen backup and every record in it:
make it long, and never store it beside the backup. scrypt at n=2^16 makes
offline guessing expensive, and the parameters are authenticated so nobody can
quietly weaken them.

A backup you have never restored is a guess. `restore` prints the exact
`verify` command to run against the restored copy; the test suite does that on
every run, opening a restored vault using only what the archive contained.

### What it protects against, and what it does not

Protected: a powered-off or discarded disk, a drive handed to a repair shop, a
stolen backup, a record file copied out by something with no business reading
it, a cloud sync that gets hold of the files.

**Not** protected: root on this machine while it is running. The service has to
read the key, so anything running as root can too. Encryption at rest is not a
defence against a live compromise and should never be described as one.

Two narrower limits worth knowing:

- A blind index **leaks equality**. Two records with the same surname carry the
  same token, so someone holding the files learns how many patients share a
  name without learning the name. Anyone who also holds the index key can test
  guesses against a name list. Index only what you need to search by - which is
  why `dob` is not indexed above.
- Record **size and count are visible**, as are timestamps. That is inherent to
  files on a disk.

### Losing the key

There is no recovery path. That is a design decision, not an oversight - a
master key with a backdoor is not a master key. Back up
`~/.thunder/keys/vault.key` off this machine, encrypted, before there is
anything in the vault worth keeping.

## Before this touches a real record

Done: authentication, TLS, encryption at rest, audit logging, encrypted backups
with a tested restore.

Still outstanding, and none of it is code: a documented risk analysis, written
policies, workforce training, and BAAs with anyone who touches the data. Those
need a professional. Having good crypto is not the same as being compliant, and
the gap is mostly paperwork.
