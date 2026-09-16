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
