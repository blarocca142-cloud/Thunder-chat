# Honeyfiles

Files that exist only so that touching them raises an alarm.

    python3 canary/canary.py plant     # write the decoys
    systemctl enable --now thunder-canary

## What this is and is not

**Detection, not protection.** It cannot stop a breach, and by the time
someone reads these they are already inside. What it gives you is *immediate*
notice, which is the difference between knowing now and knowing in six months.

The signal has no false positives by construction: nothing legitimate ever
opens these files, so one access is one alert and it always means something.
That is rare enough in security tooling to be worth the twenty lines.

It is **not** a substitute for authentication, TLS or encryption at rest. Those
are the locks. This is the tripwire behind them.

## Where the alerts go

- `thunder-data/canary_alerts.log`
- the system journal at `auth.crit`, tagged `thunder-canary`
- `GET /status` -> `canary[]`, and `state` becomes `security_alert`
- `GET /system` -> `canary[]`

The app already surfaces `state`, so a hit shows up without further work.

## Planted decoys

Named as the first things anyone would reach for:

- `~/patients_2026_backup.csv`
- `~/billing_export_Q3.csv`
- `~/.ssh/id_rsa_backup`
- `thunder-data/patient_records_export.json`
- `thunder-data/credentials_backup.txt`

Each opens with a plausible header so it survives a glance. The remainder is
filler and a note explaining that the access has already been logged.

**Do not ever put real data in one**, and do not `cat` them yourself out of
curiosity - you will page yourself.
