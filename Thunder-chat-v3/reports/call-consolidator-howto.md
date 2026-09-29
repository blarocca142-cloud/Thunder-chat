# Running the call consolidator on a real call sheet

Written 2026-09-29. Verified by running the tool's own synthetic sample on
thunder-main; the commands below are copy-paste ready.

**The directory is `~/call-consolidator` with a hyphen**, not
`~/call_consolidator`. Only the zip in `~/Downloads` uses the underscore, and
that zip is stale (see Gotchas).

The program lives on Main and is **not** part of this repo, deliberately — its
own `.gitignore` refuses every spreadsheet extension so call data cannot be
committed by accident. Nothing here should be copied into `Thunder-chat-v3/`.

---

## 1. What it does

It joins an office **call log** against a **marketing contact list** on the
phone number, and counts. The call log knows which numbers were rung and when;
the contact list knows who those numbers belong to; neither answers "how often
has this office actually contacted this person, and when". Output is one row
per office-number-and-patient-number, with outbound and inbound counted
separately, sorted so repeats are easy to spot. No model is involved — joining
and counting are arithmetic and are done exactly, in code, in a few seconds on
50,000 rows. It is **stateless**: it reads the two sheets you hand it, writes
one file, and remembers nothing between runs.

### Input formats

`.xlsx`, `.xlsm`, old-style `.xls`, and `.csv` / `.tsv` / `.txt` (the delimiter
is sniffed, so comma, tab and semicolon all work). Only the **first sheet** of a
workbook is read. Blank lead-in rows above the header are skipped automatically.

### Column headers

Headers are matched **case-insensitively**, and a header counts as a match if it
*equals*, *starts with*, *ends with*, or merely *contains* one of the names
below — so `Call Start Time` matches `start time`, and `Office Name` matches
`office`. Where a header is missing or meaningless (`Column1`, or no header row
at all) it falls back to sniffing the data: a column where >70% of the first 200
values are ten digits is the phone number, a column that mostly parses as dates
is the timestamp.

The call log runs in one of **two modes**, and which one you get changes the
answer, so check the `columns used` line it prints on every run.

**Direction-aware mode** (what a real CDR export from a phone system gives you)
needs **all three** of these present:

| Field | Header names recognised |
|---|---|
| To number | `To Number`, `Called Number`, `Destination Number`, `Number Called`, `Dialed Number`, `Callee` |
| From number | `From Number`, `Caller Number`, `Calling Number`, `Originating Number`, `Caller ID`, `ANI` |
| Direction | `Direction`, `Call Direction`, `In/Out`, `Call Type` — values must begin with `in` or `out` |

Optional but used if present: `Resource` / `Media Type` / `Line Type` (a value of
`fax` drops the row), `To Name` / `Called Name` / `Destination Name`,
`From Name` / `Caller Name` / `Calling Name`, plus office and date below.

**Single-column mode** (a simple log with one number per row) needs:

| Field | Header names recognised |
|---|---|
| Phone | `Phone`, `Number`, `Phone Number`, `Telephone`, `Tel`, `Mobile`, `Cell`, `Contact Number`, `Called`, `Dialed`, `Dialled`, `Destination` |

Both modes also read, optionally:

| Field | Header names recognised |
|---|---|
| Office | `Office`, `Location`, `Branch`, `Clinic`, `Site`, `From Office`, `Practice`, `Store`, `Office Name` |
| Date/time | `Date`, `Time`, `Datetime`, `Date Time`, `Call Date`, `Timestamp`, `Called At`, `Date of Call`, `When`, `Call Time`, `Start Time` |

The **contact list** needs a phone column (same names as above) and optionally
`First Name` / `Name` / `Contact` / `Full Name` / `Client` / `Customer` /
`Patient` / `Lead`, `Last Name` / `Surname` / `Lastname`, and an office column.
Nothing has to be renamed if the export already uses any of these.

### What it outputs

One spreadsheet — `.xlsx` unless you name a `.csv`, in which case it writes CSV.
Columns, in order:

    Office number · Office location · Name · Also listed as ·
    Caller ID (not a patient-list match) · Patient phone ·
    Times office called out · Times patient called back · Total times contacted ·
    First contact · Last contact · Every contact · In marketing list

Default filename is `consolidated.xlsx`. **Relative paths resolve against
`~/call-consolidator`, not against the directory you launched from**, because
`run.sh` cd's into its own folder first — so give absolute paths for both the
inputs and `--out`.

### Options

    --out PATH          output file (default: consolidated.xlsx)
    --days N            only calls within N days of the *newest call in the file*
                        (not of today — an old export still reports a sane month)
    --sort patient      group every row for one number together (default)
    --sort office       group by office, then by name — better with many offices

---

## 2. Option A — run it on Main from the Windows laptop (PowerShell)

Nothing to install on the laptop. The sheets go up, the report comes back.

Copy the two sheets up (quote the paths — real exports have spaces in the name):

```powershell
scp "C:\Users\blaro\<call-sheet>.xlsx" blayne@10.168.168.10:~/call-consolidator/
scp "C:\Users\blaro\<contact-list>.xlsx" blayne@10.168.168.10:~/call-consolidator/
```

Run it. `run.sh` builds its own virtualenv on first run and needs no sudo:

```powershell
ssh blayne@10.168.168.10 "cd ~/call-consolidator && ./run.sh '<call-sheet>.xlsx' '<contact-list>.xlsx' --out ~/call-consolidator/report.xlsx"
```

Add `--days 30` or `--sort office` on the end of that same line if you want them.

Read the output it prints — especially `columns used` and `direction-aware` —
before trusting the numbers. Then bring the report back:

```powershell
scp blayne@10.168.168.10:~/call-consolidator/report.xlsx "C:\Users\blaro\"
```

Tidy up when you're done, so call data isn't left sitting on Main:

```powershell
ssh blayne@10.168.168.10 "rm -f ~/call-consolidator/'<call-sheet>.xlsx' ~/call-consolidator/'<contact-list>.xlsx'"
```

There is also a browser front end (`./run_web.sh`, then
`http://10.168.168.10:8766/` from any machine on the LAN). It binds to the LAN
address and has **no login of any kind**, so start it only while you're using it
and stop it after.

---

## 3. Option B — copy the program to the laptop and run it there with `py`

Better when the sheet shouldn't leave the laptop at all. It is pure Python plus
two packages; no GPU, no network, no Thunder.

Copy the folder down (`-r`, and take it from Main rather than unzipping the one
in Downloads):

```powershell
scp -r blayne@10.168.168.10:~/call-consolidator C:\Users\blaro\
```

Install the two dependencies once:

```powershell
py -m pip install --upgrade openpyxl xlrd
```

Run it from inside the folder:

```powershell
cd C:\Users\blaro\call-consolidator
py consolidate.py "C:\Users\blaro\<call-sheet>.xlsx" "C:\Users\blaro\<contact-list>.xlsx" --out "C:\Users\blaro\report.xlsx"
```

Or double-click `run_desktop.bat` for the point-and-click window (pick two
files, pick the grouping, Run, Save). It uses tkinter, which ships with the
python.org Windows build.

**Linux-only, do not try to run these on Windows:** `run.sh` and `run_web.sh` are
bash scripts and will not work in PowerShell — `consolidate.py` and
`run_desktop.bat` are the Windows entry points. The `.venv/` folder that comes
down with the `scp -r` is a **Linux** virtualenv and is useless on Windows;
delete it and use the `py -m pip install` above instead. `desktop_app.py`
imports `consolidate.py` from the same folder, so keep the two together.

---

## 4. Gotchas

- **`Number Called` alone breaks the run.** That header is claimed as the CDR
  "to number", so unless `From Number` *and* `Direction` are also present the
  tool exits with `Could not find a phone number column`. This is exactly what
  the bundled `sample_calls.xlsx` hits — the README's
  `./run.sh sample_calls.xlsx sample_marketing.xlsx` line does not work as
  written. Fix on a real sheet by renaming that one header to `Phone`, after
  which the same 50,000-row sample ran clean and accounted for all 50,000 calls.
  A real CDR with all three columns is unaffected and takes the better
  direction-aware path.
- **Always read the `columns used` line.** It prints which header it decided was
  which, every run. If it guessed wrong, everything downstream is wrong and
  nothing else will tell you.
- **Direction-aware vs single-column changes the meaning of the counts.** In
  single-column mode `Times office called out` and `Times patient called back`
  are both **0** and only `Total times contacted` is populated — inbound and
  outbound cannot be told apart. Confirmed on the sample run.
- **Excel exports:** save as `.xlsx` or `.csv`, not "Excel 97-2003" unless you
  mean it. An old `.xls` renamed to `.xlsx` is a different binary format and the
  tool says so rather than guessing. Only the first sheet is read, so flatten a
  multi-tab workbook first. If a phone column was stored as a *number*, Excel
  will have eaten the leading zero and may show it as `5.55012E+09` — set that
  column to Text before exporting.
- **Phone formats do not need cleaning.** `(000) 000-0000`, `000.000.0000`,
  `000-000-0000`, `+1` prefixes and bare digits all reduce to the last ten
  digits before matching. Anything shorter than ten digits is treated as an
  internal extension and skipped (it reports the count).
- **Date formats:** ISO, `m/d/Y`, `d/m/Y`, `b d Y` and Excel raw serial numbers
  are all handled. **`d/m/Y` and `m/d/Y` are ambiguous** and US order wins, so a
  UK-ordered export will silently mis-date any day ≤ 12. A row whose date can't
  be read is still counted, just reported as `with no readable date`.
- **Duplicates are handled two different ways.** A number listed twice in the
  contact list under different names is one person — the fullest name wins and
  the rest appear in `Also listed as`. In the call log, a ring-group call logged
  twice (same patient, same direction, under 30 seconds apart, *different*
  office number) is merged into one call; a redial to the *same* office number
  inside 30 seconds is kept, because that is a real second call.
- **Fax rows are dropped** when `Resource` says `fax`, as are rows with a blank
  office-side number (fax broadcasts). Rows whose `Direction` is neither `in…`
  nor `out…` are skipped entirely. All three counts are printed — if they are
  large, the export's columns are probably not what you think.
- **Numbers with nobody attached are kept**, marked `In marketing list: no`,
  with whatever the carrier's caller-ID text said in the `Caller ID` column. A
  call you can't explain is worth seeing.
- **Names are matched by phone number only.** Someone with two numbers appears
  as two rows; there is no fuzzy name matching.
- **The zip in `~/Downloads/call_consolidator_desktop.zip` is stale** — it
  predates the direction-aware CDR handling and the ring-group dedupe. Copy from
  `~/call-consolidator` on Main instead.
- **Don't commit sheets anywhere.** The tool's own repo ignores every
  spreadsheet extension on purpose, and none of this belongs in Thunder-chat.
