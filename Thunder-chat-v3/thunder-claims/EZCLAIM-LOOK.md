# EZClaim — what it looks like and how it behaves

Field notes taken from EZClaim's own YouTube tutorials, watched frame by frame.
The goal is that **Thunder Claims feels like EZClaim to the office**, so this
records the *look and the wording*, not just the features.

Organised **by screen**. Each fact is tagged with the video id it came from.
No screenshots, frames or captions are stored in this repo — they are EZClaim's
copyrighted material and live only in `~/ezclaim-study/` on Main.

**Version seen on screen:** title bar reads `EZClaim Billing - 8.0.670 -
Demo_Company_Jaime_B` (`oZBevrOFRwY`), `8.0.668` (`gO7UQeKlmFM`), `8.0.665`
(`puSJeow-pkk`). So the desktop look below is **EZClaim Premier 8.x, current**.
The separate orange/purple web portal (`DZ0spaFoFz4`) is a **2025 addition**
that sits alongside the desktop app, not a replacement.

---

## 1. Main window — chrome, ribbon, layout

The whole app is one window with an Office-2007-style **ribbon**. It is a
dense, grey, Windows-native look — small text (~11px), thin 1px grey grid
lines, beveled buttons. Not flat, not modern. (`oZBevrOFRwY`, `gO7UQeKlmFM`)

**Title bar:** `<Current tab name> - EZClaim Billing - <version> - <Company>`,
e.g. `Payment Entry - EZClaim Billing - 8.0.670 - Demo_Company_Jaime_B`.
So the title bar always names the screen you are on. (`oZBevrOFRwY`)

**Status bar (bottom left):** `Logged in as: Jaime` (`oZBevrOFRwY`)

### Ribbon tabs (left to right)
`Home` · `Electronic Billing` · `Tools` · `Support` — and in the newer capture
also `Info`. (`oZBevrOFRwY`, `DZ0spaFoFz4`)

### Home ribbon — groups and buttons, in order
Each group has a caption underneath, centred, in small grey text.

| Group caption | Buttons, in order |
|---|---|
| **File** | `Home`, `Print` (split button, has ▾), `Save`, `Close`, `Delete` |
| **Edit** | `Paste`, `Copy`, `Cut`, `Undo`, `Select All`, `Clear` |
| **Find** | `Find` (split button, has ▾) |
| **New** | `Patient`, `Claim`, `Payment`, `Task`, `Statement` |
| **Libraries** | `Payer`, `Physician Facility`, `Libraries` (split, ▾) |
| **Alerts** | `EDI Reports (3 NEW)` / `(4 NEW)` (dropdown), `Reminders`, `Review Incoming (8 Files)` |
| **Support** | `Help Topics`, `Ticket` (newer) / `EZView` (older) |

Greyed-out buttons stay visible and greyed rather than disappearing — `Save`,
`Delete`, `Paste`, `Cut`, `Undo`, `Clear` are grey until something is dirty or
selected. (`oZBevrOFRwY`, `gO7UQeKlmFM`)

Note the **alert counts are baked into the button label** — `EDI Reports
(3 NEW)`, `Review Incoming (8 Files)`. (`DZ0spaFoFz4`)

### Tools ribbon — groups and buttons
| Group caption | Buttons |
|---|---|
| **File** | `Home`, `Print`, `Save`, `Close`, `Delete` |
| **Edit** | (same as Home) |
| **Find** | `Find`, `MerchantTrack` |
| **Import** | `Appointments`, `Pending Data`, `BillFlash ePay` |
| **EZClaimPay** | (group caption under MerchantTrack) |
| **Options** | `Program Setup` |
| **Security** | `Manage Security Settings`, `Change Password` (greyed), `Login as another user` (greyed) |
| **Company** | `Backup` |
| **Support** | `Help Topics`, `EZView` |
(`gO7UQeKlmFM`)

### The four-way split
Below the ribbon the window is split **left / right**, and the left is split
**top / bottom**:

- **Left top — the record grid** with four selector tabs above it:
  `Patients` · `Claims` · `Reports` · `Tasks`, each with a small colour icon.
  The active one looks pressed. (`oZBevrOFRwY`)
- **Left bottom — a detail pane** with its own tab strip:
  `Details` · `Claims` · `Services` · `Payments` · `Documents`. (`oZBevrOFRwY`)
- **Right — a document area with closable document tabs**, e.g.
  `Home ✕`, `Payment Entry ✕`, `Setup ✕`, `Statements ✕`, `EDI Reports ✕`,
  `835_Accepted_Forwarded.rmt ✕`. Tabs carry a small icon and an `✕`.
  A dirty tab shows an asterisk: `Payment Entry*`. (`oZBevrOFRwY`, `puSJeow-pkk`)
  Far right of the tab strip is a single `✕` that closes the document area.

**This "open screens as tabs" model is central to how EZClaim feels.** The
patient grid never goes away; work opens beside it.

---

## 2. The record grid (left top) — and grids generally

Every grid in EZClaim shares the same behaviour and furniture:

1. A grey band above the header reading
   **"Drag a column header here to group by that column"** — grids support
   drag-to-group. (`oZBevrOFRwY`, `gO7UQeKlmFM`)
2. A **magnifying-glass icon** at the right end of that band (search).
3. A **header row** with sort arrows (`▲`) on the sorted column.
4. A **filter row directly under the header**: one editable `Filter` box per
   column, with a small **`✕`** at the far left of that row to clear all
   filters. This is per-column filtering, always visible. (`oZBevrOFRwY`)
5. A **footer** showing `Shown: 30` on the left and column totals on the right,
   e.g. `$4,957.00`. Visibility is configurable
   (`Grid Footer Visibility: Show Footers when Filtering`). (`gO7UQeKlmFM`)
6. A narrow leftmost column of **row icons/checkboxes**.

### Patients grid columns
Two column sets were seen, so **columns are user-configurable**:

- `A…` (icon) · `Name` · `Account #` · `Pri Payer` · `Tot. Cla. Bal.`
  (`oZBevrOFRwY`)
- `A…` (icon) · `Name` · `Classification` · `Eligibility` · `Pat. Bal.`
  (`DZ0spaFoFz4`, `gO7UQeKlmFM`)

`Name` is **`LAST, FIRST M`, upper case** — `BROOKS, PATIENT D`,
`JONES, TOM W`, `MCLEAN, DONNA`. Account numbers are 4-digit (`1000`–`1031`).

### Row colouring — this is a signature of the look
Rows are tinted by meaning, not just selection:
- **Pink/salmon row** = patient owes money / attention (`CARSON, PATIENT`,
  `JONES, TOM W`, both with `$20.00` balances). (`DZ0spaFoFz4`)
- **Green cell** in `Eligibility` = `Active 06/26/25`. (`DZ0spaFoFz4`)
- **Blue** = current selection.
- Alternating row colours are an option (`Alternate Grid Row Colors` checkbox
  in Program Setup → General). (`gO7UQeKlmFM`)

### Eligibility column
Contains two small inline link-buttons per row: **`CHECK`** and **`VIEW`**.
`VIEW` is greyed until there is info; the cell text is `NO INFO` or
`Active <date>` on green. (`DZ0spaFoFz4`, `gO7UQeKlmFM`)

### Claims quick-access grid (left top, `Claims` tab)
Columns: `1st DOS` · `Status` · `Tot. Chg.` · `Tot. Bal.`, with the same filter
row. Footer: `Shown: 9`, `$680.00`, `$140.00`. **Double-clicking a row opens
the claim.** (`oZBevrOFRwY`)

Status values seen: **`Ready to Submit`**, **`Submitted`**, **`Other`**.
(`oZBevrOFRwY`)

### Patient detail pane (left bottom, `Details` tab)
Collapsible sections, each with a `▲`/`▼` chevron on the right:
- **Patient Information** — `Name`, `DOB`, `Address`, `City ST ZIP`
- **Contact Information** — `Primary Phone #`, `Primary Email`
  (with a small `Email` button at the right of the email row)
- **Insurance** — `Primary Payer`, `Pri Payer Phone #`, `Pri Insured's ID`,
  `Secondary Payer`, `Sec Payer Phone #`, `Sec Insured's ID`
- **Physician / Facility Library** (collapsed)

Below it a free-text strip: *"This is the reminder note area"*.
(`DZ0spaFoFz4`, `gO7UQeKlmFM`)

`Payments` tab of that pane: columns `Name` · `Date` · `Amount` · `Pat. Disb.`,
where `Name` is the payer or the word `Patient`. (`DZ0spaFoFz4`)

---

## 3. Home screen (the default document tab)

The Home tab is a **workflow flowchart**, not a dashboard of numbers. Large
labelled icon-boxes joined by grey arrows: (`DZ0spaFoFz4`, `gO7UQeKlmFM`)

```
Create Patient ▾ ┐
                 ├→ Create Claim ┬→ Print Claims
Edit Patient ────┘               ├→ Patient Statements
                                 ├→ Enter Payment
                                 └→ Send Claims → View EDI Reports
```

Exact box labels, two lines each: `Create Patient` (has a ▾ split arrow),
`Edit Patient`, `Create Claim`, `Print Claims`, `Patient Statements`,
`Enter Payment`, `Send Claims`, `View EDI Reports`.

**Below the flowchart, a left column of "widget" tiles** — each a big number
with a caption, clickable, selected one highlighted blue:
- `6` Claims Over 90 Days …
- `0` Denied Claims from P…
- `0` Rejected Claim from P…
- `3` Unpaid Patient Co-pays
- `1` Expiring Auths
- `2` Batch Status
- `0` Claims with a Credit B…
(`DZ0spaFoFz4`; a shorter set `2 Batch Status / 6 Claims Over 120 Day… /
2 Expiring Auths` in `oZBevrOFRwY`, and `2 Batch Status / 6 Claims Over 90
Days… / 0 Claims with a Credit…` in `gO7UQeKlmFM` — so the tile set is
configurable.)

**To the right of the tiles, the selected tile's detail grid**, with its own
title bar, e.g. `Rejected Claim from Posted 277-CSR Reports` with columns
`Name` · `Bill Date` · `Note Date` · `Most Recent Claim Note`; or
`Unpaid Patient Co-pays` with `Name` · `Service Date` · `Amount Due` ·
`Amount Paid`; or `Batch Status` with `Exp… Date/Time` · `File Name` ·
`Func. Group Number` · `Original Claim Count` · `Acknowledgement`
(value `Accepted`). (`DZ0spaFoFz4`, `gO7UQeKlmFM`, `oZBevrOFRwY`)

**Bottom of the home tab:** `Updated 2:26 PM` with a **`Refresh`** button.
(`DZ0spaFoFz4`, `oZBevrOFRwY`)

---

## 3b. Patient screen ★

**Double-click a row in the Patients grid to open the patient record.**
(`h-EzAeOTDlQ`) It opens as a document tab labelled
**`BROOKS, PATIENT D (Age: 53)`** — name plus a computed age, with `*` when
dirty.

A **`Patient` ribbon tab** appears while it is open, with groups
`Find` · `New` · `List` · **`Actions`** (`Apply Template`, `Copy Patient`,
`Merge Patient`) · `Quick Reports` · `Support`.

### Section `Patient Information` (labels right-aligned)
| Label | Notes |
|---|---|
| `Name (Last, First, MI):` | **three separate boxes** — `BROOKS` / `PATIENT` / `D` |
| `Classification:` | dropdown — `DR BROOKS` |
| `Address:` and `Address 2:` | |
| `Claim Template:` | dropdown `<Previous Serv…>` plus a `…` button |
| `City ST Zip:` | three boxes — `ANYWHERE` / `NY` / `33333` — plus a small button |
| `Copay Amt:` | `$10.00` **`or Percent`** `0` `%` |
| `DOB:` | date picker `03/21/1966` |
| `Sex:` | dropdown `Male` |
| `Marital:` | dropdown |
| `Diagnosis A1:` `B2:` | `F34.1` — **default diagnoses carried onto new claims** |
| `Employment:` | dropdown |
| `Account #:` | `1003` |
| `E5 to H8` | a **button** that reveals more diagnosis slots; `C3:` `D4:` beside it |

### Section `Patient Contact Information`
`Primary Phone #:` · `Home Phone #:` · `Cell Phone #:` · `Work Phone #:` ·
`Fax #:` · `Primary Email:` (with an `Email` button) · `Secondary Email:`
(with an `Email` button) · **`Appt Reminder Pref:`** (dropdown, `No Reminders`)
· `Emergency Contact:` · `Emergency Phone #:` with `Relation:` beside it

### Section `Physician / Facility Library Entries`
`Billing Provider:` (`HEALTH CLINIC`) and `Rendering Provider:`
(`RENDERING ROBERTS`), each a **dropdown plus a `…` button plus an `✕`**
(pick / open the library entry / clear).

### Insurance — a tabbed sub-panel
Tabs **`Primary Ins`** and **`Secondary Ins`**, with two buttons across the
top: **`Copy information from the patient`** and **`Delete`**.

Fields: `Name (Last, First, MI):` (three boxes) · `Date of Birth:` with `Sex:` ·
`Address:` · `City, State, Zip:` (three boxes) · `Phone #:` · `Employer:` ·
`Payer:` (dropdown + `…` + `✕`) · **`Eligibility:`** (green
`Active 07/24/19` with inline `CHECK` and `VIEW` buttons) · `Insured's ID #:` ·
`Group #:` · `Plan or Program Name:` · `Patient Rel to Insured:` (dropdown,
`Self`) · `Accept Assignment:` (dropdown, `Yes`)

### Right-hand button column
`Save & Close` · `Save` · `Close` · `Delete` · **`Add Ins`** · **`Lookup`** ·
**`Replace All with Insurance from Claim`** (a three-line button) ·
**`Update Claims`**, then two checkboxes: ☑ **`Active`** and ☐ **`Locked`**.

### Patient classifications (`h-EzAeOTDlQ`)
`Classification` is a free per-patient grouping (values seen: `DR BROOKS`,
`MEDICARE`, `GENERAL GROUP`, `INSTITUTIONAL P…`). It is **not shown in the
grid by default** — the video's whole point is that you add it by
**dragging `Classification` from the `Customization` column chooser into the
column header**.

The `Customization` chooser for the patient grid lists (alphabetically, with a
`Search for a column…` box at the top): `Add Payment`, `Address`,
`Another Custom Field`, `Billing Phy Name`, `Cell #`, `City State Zip`,
`Classification`, `D.O.B.`, `Eligibility`, `Email`, `Facility Phy Name`,
`Family Size`, `Fax #`, `First Date of Service`, `First Name`, …

---

## 3c. Claim screen ★

Opens as a document tab labelled **`BELL, DARRELL - 11/23/2018`** —
**patient name plus first date of service**. (`5aJQBFSmkbU`)

A **`Claim` ribbon tab** appears while it is open:

| Group caption | Buttons |
|---|---|
| `Edit` | `Copy`, `Cut`, `Clear`, `Select All`, `Undo` |
| `Find` | `Find` |
| `New` | `Claim`, `Payment`, `Task`, `Patient` |
| `Open` | `Tasks` |
| `List` | `Tasks` |
| **`Actions`** | **`Make Recurring`**, **`Copy Claim`**, **`Save as Template`**, **`Write Off Claim`**, **`Pay Off Claim`** |
| `Quick Reports` | `Quick Reports` |
| `Support` | `Help Topics` |

(On the Patient screen the same `Actions` group instead holds
`Apply Template`, `Copy Patient`, `Merge Patient`, and there is an
`Authorization` / `Services` / `Authorizations` set in `New` / `List`.)

### Top of the claim
- **`Bill To:`** — a wide dropdown reading
  **`Primary (1/1) - GEICO - BELL, DARRELL`**, plus a `…` button.
  The `(1/1)` is the bill-to **sequence** (see `Bill To Sequence` in the report
  filters).
- `Prior Auth #:` — dropdown + `…` + a small **ⓘ** info icon
- `Date of Curr:` — date picker

### Diagnosis block — twelve fixed slots, labelled letter+number
```
Diagnosis A1: [H5316]  B2: [S86901A]  C3: [S62111P]  D4: [S066X3A]
E5: [ ]  F6: [ ]  G7: [ ]  H8: [ ]
I9: [ ]  J10: [ ]  K11: [ ]  L12: [ ]
```
**This is exactly the CMS-1500 box 21 A–L lettering, and EZClaim writes it as
`A1`, `B2` … `L12` — letter *and* ordinal together.** Codes are entered
**without the decimal point** (`H5316`, not `H53.16`).

### Two-month calendar strip
Two month grids side by side (`‹ November › 2018 ›` and `‹ December › 2018 ›`)
with S M T W T F S columns; the service-line date is highlighted (the `23`).
**Clicking a day is how you add a service line for that date** — the same
idea our app already has.

### `Claim Template:` dropdown
Value `<No Template>`.

### Service line entry grid
An **entry row across the top with an `ADD` button**, then the saved lines
below. Hint text between them:
**"Enter the service line data above and click the 'ADD' butt…"**

Columns: `Srvc Date` · `Place` · `Procedure` · **`M1` `M2` `M3` `M4`**
(four modifier columns) · … · `Amt.` · `Balance` · `Resp. Party` ·
`Pat. Amt. Due`. Each saved row has a `＋` expander and an `✕` delete button.
Footer: **`Services: 1`** plus column totals.

### Right panel `Claim Information` (read-only label/value list)
`Original Bill Date` · `Status` (`Ready to Submit`) · `Method` (`Electronic`) ·
`Last Printed` · `Last Exported` · `Invoice #`

### Notes at the bottom
A prompt **`Click here to add a new note`**, then an automatic note history
grid — e.g. `11/23/2018 10:32 AM | USER | Claim edited`. **Note entries are
auto-logged as well as typed.**

### `Make Recurring` → `Create Recurring Claim` dialog (`5aJQBFSmkbU`)
- `Generate this claim every:` `1` `Month(s)` (dropdown)
- `Until:` date picker (`11/23/2019`)
- An `Update` button, then
  *"This claim (will be generated on) the Follow(ing dates)"* over a list of
  the generated dates (`12/23/20`, `01/23/20`, `02/23/20`, … `11/23/20`)
- `Delete Selected Date` button
- `Save and Close` / `Cancel`

---

## 4. Payment Entry screen

Opened by `Enter Payment` on the Home flowchart, or the `Payment` button in
the ribbon's New group. Opens as a document tab named `Payment Entry`.
(`oZBevrOFRwY`)

### Top-left header block — "the check"
Labels are right-aligned, fields to their right:
- `Payment Source:` — **two radio buttons, `Patient` and `Payer`**, plus a
  greyed `EZClaimPay` button.
- `Payer:` — dropdown (`None` when empty; `BLUE CROSS` when set)
- `Amount:` — `$0.00`, and `Pmt Date:` with a date picker (`04/19/2021`)
- `Payment Method:` — dropdown (`CHECK`), and `Ref #:` (`99887742`)
- `Add Ref #:`
- `Note:` — with an **`Auto Apply`** button beside it

(`oZBevrOFRwY`)

### Top-right — the existing-payments grid
Columns: `Patient` · `Pmt Amt` · `Applied Amt` · `Remaining` · `Date` ·
`Method` · `Ref #`. A selected row shows two inline buttons at its left:
**`DISBURSE`** and **`MODIFY`**. Above it a banner:
`Payments from BLUE CROSS with a balance:` (`oZBevrOFRwY`)

### Right-hand button column (top to bottom)
`Save & Close` · `Save` · `Close` · `New Pmt` (`oZBevrOFRwY`)

Then a block **`Need to enter more adjustments?`** with `–` and `+` spinner
buttons, and a checkbox list:
- ☑ `Show Adj Reason Codes`
- ☐ `Show Adj Remark Codes`
- ☐ `Show Adj Reason Amount`
- ☐ `Show Payment Reason Codes`
- ☐ `Show Notes`

At the very bottom right, a **`Filter Settings`** panel showing the active
settings as plain text, then a `Filter Settings` button:
```
Filter Settings:
Ignore Responsible Party - Checked
Match By Payer ID - Checked
```
(`oZBevrOFRwY`)

### The service-line grid (centre) — the heart of payment entry
Grouped headers: a plain group, then **`Payment`**, then **`Adjustment 1`**,
then **`Adjustment 2`** spanning their sub-columns.

Columns in order:
`Name` · `Secondary …` · `Proc` · `DOS` · `Charge` · `Responsibl…` ·
`Applied` · `Balance` · **Payment:** `Amt` · **Adjustment 1:** `Amt`, `Code`,
`Reason` · **Adjustment 2:** `Amt`, `Code`, `Reason`

Plus a `Pay` button inline on each row, and a `＋` expander at the left of each
row that opens the existing payments/adjustments on that service line.
Balance values are shown in **red**. Adjustment `Code`/`Reason` cells are
dropdowns. (`oZBevrOFRwY`)

Above the grid on the right: `Remaining: $0.00`, `$0.00 Pay…`.
Footer totals row: `$1,830.00 · $210.00 · $1,520.00 · $0.00 · $0.00 · $0.00`.

### Service Line Filter Settings dialog
Titled **`Service Line Filter Settings`**, with:
- **Grouping Filters**: ☐ `Ignore Responsible Party`, ☐ `Match By Payer ID`
- **One-Time Filters**: ☐ `Hide Service Lines with $0.00 Charges`
- ☐ `Service Line Date Range (Including those with $0.00 balances)`
  with `From:` `01/19/2021` and `To:` `04/19/2021` date pickers
- `OK` / `Cancel`
(`oZBevrOFRwY`)

### Workflow: insurance refund / takeback / reversal (`oZBevrOFRwY`)
> "Refunds, takebacks, or reversals all get entered in the same way that
> regular payments get entered."

1. Home tab → `Enter Payment`.
2. Enter the whole check in the top-left: payer name, amount, date, method,
   check reference number. (Example uses a **zero-dollar check/EOB** holding a
   payment and a reversal that net to zero.)
3. If the service line isn't in the grid, `Filter Settings` (bottom right) →
   show zero-balance claims and/or widen the date range.
4. Expand a service line (`＋`) to see existing payments and adjustments.
5. **To enter the reversal: put the cursor in the `Amt` cell and type a minus
   sign** to make it negative. Reversed adjustments work the same way.
6. Enter the payment and adjustments until `Remaining` is `$0.00`.
7. `Save` → **a confirmation prompt appears asking to confirm saving a
   zero-dollar amount → `Yes`.**
8. Double-click the claim in the lower-left quick-access grid to verify;
   expand the service line with the small plus sign to see original payment
   and new reversal side by side.

### Workflow: patient refund (`7SeDsTtfBNU`)
Scenario: a copay was collected and applied, but wasn't owed — balance shows
as a **credit** (e.g. `$15` credit).
1. Open the claim, expand the service line to see what causes the credit.
2. **Double-click the `Paid` cell of that service line** → a new payment
   window opens.
3. Make sure `Patient` is chosen as the **source**.
4. **The program pre-fills the amount**; put the cursor in and change it.
5. **Type a minus sign for a negative payment / refund.**
6. `Save and Close`, confirm. The refunded payment now shows on the service
   line.

---

## 5. Auto-posting 835 / ERA files

Opened from `EDI Reports`; an `.rmt` file opens as its own document tab named
after the file, e.g. `835_Accepted_Forwarded.rmt`. (`puSJeow-pkk`)

### Header strip (two lines of label: value pairs)
```
835 Payer Name: MEDICARE    Payer ID: 88888    Payment Total: $90.00    Payment Method: ACH
Matching EZClaim Payer Name: MEDICARE    Payer ID: 88888
Payee Name: PROVIDER NAME   Payee ID: 123456786   Check or EFT Trace Number: 11111122222   Payment Date: 03/25/2013
```
(`puSJeow-pkk`)

### Main grid columns, in order
`Status` · `Claim Invoice #` · `Claim Status` · `Patient Name` · `Procedure` ·
`Service Date` · `Line Charged Amt` · `Line Payment Amt` · `Apply Disbursement`
(checkbox) · `Balance` · `CO Amt` · `PR Amt` (`puSJeow-pkk`)

### Status values and their row colours — signature behaviour
- **`BALANCE EXCEE…`** (Balance Exceeded) — **pink/red rows**
- **`IGNORED`** — **green rows**

`Claim Status` holds the human text from the 835, e.g.
`Processed as Primary`, `Processed as Primary, Forwarded HUMANA`.
(`puSJeow-pkk`)

**"Balance Exceeded" means: posting this payment or adjustment would have put
the service line into a negative balance.** (`puSJeow-pkk`)

### Right-hand button column
`Apply Payments and Adjustments` (greyed until ready) · `Close` ·
`Close and Archive` · `Options` · `Run Report`

Then: `Use the following payment date:` with a date picker (`11/24/2020`),
`Recheck Payer Links` (greyed), `View Adjustments Ungrouped`.

At the bottom right, a **legend in plain text** — worth copying verbatim:
```
Apply  - Write off the adjustments amount.
Track  - Post a $0.00 adjustment to allow claim follow-up.
Ignore - Ignore Adjustment.
Help Topics
```
(`puSJeow-pkk`)

A lower detail grid shows adjustment breakdown with columns including
`Group Code`, `Adjustment Description`, `Total Adjustments`, `Processed
Status` (value `Processed`), and rows like `CO - Contractual Obligation`.

---

## 6. Patient Statements screen

Opened via `Patient Statements` on the Home flowchart; document tab named
`Statements`. (`DZ0spaFoFz4`)

### Grid columns, in order
checkbox · `Name` · `Account #` · `Classification` · `Pat Bal` · `Ins Bal` ·
`Pri Payer` · `Last Sta Date` · `Pat Msg`

In the newer capture (`uqRGjzNM-KE`) the `Classification` column is absent, so
the set is: checkbox · `Name` · `Account #` · `Pat Bal` · `Ins Bal` ·
`Pri Payer` · `Last Sta Date` · `Pat Msg`. **Columns are added by right-clicking
any column header → "grid columns" chooser** (`uqRGjzNM-KE`).

Sample row: `SAMPLE, PATI… | 1005 | GENERAL GR… | $10.00 | $30.00 |
BLUE CROSS | 10/30/2016 | Please Pay within …`

Footer: `Shown: 4. Checked: 4.` then `$60.00` and `$355.00`. (`DZ0spaFoFz4`)
Newer: `Shown: 21. Checked: 0.` with `$1,395.50` and `$0.00` (`uqRGjzNM-KE`).

**`Pat Msg` is a per-patient statement message** typed straight into the grid
cell; `Global Message` at the bottom prints on *all* statements
(`uqRGjzNM-KE`). Global message values seen: `Happy Holidays`,
`***Stay Home, Stop the Spread, Save Lives***`.

### What populates the grid (`uqRGjzNM-KE`)
> "the grid will show a list of patients that have a balance greater than a
> penny"

- `Min. Pat. Bal.` defaults to **`$0.01`** — filters out patients who owe
  nothing, and can be raised to suppress statements for trivial balances.
- `Min. Sta. Cycle` = **days since a statement was last generated** (default
  `30`). A patient who hasn't had one in 30 days is listed.
- **Troubleshooting tip given:** if an expected patient is missing, set the
  cycle to `0` and click `Refresh`.

### The printed statement (Preview) — layout (`uqRGjzNM-KE`)
Opens in a separate **`Preview`** window with its own menu bar (`File`,
`View`, `Background`), a toolbar, a zoom box (`75%`), and a status bar
`Page 1 of 1`.

The page itself, top to bottom:
- Top-left, the practice address block: `NAME / ADDRESS / ADDR2 /
  CITY, ST 12345`
- Top-right: the word **`Statement`**, then `05/11/2020`,
  `Account No: 1030`, `Page:1/1`
- A gap, then the **patient address block** positioned for a window envelope:
  `JANE MORRISON / 803 WHITE HAGUE WAY / PONTIAC, MI 48311`
- A ruled table with columns:
  `Date` · `Description` · `Proc` · `Transaction Amount` ·
  `Insurance Balance` · `Patient Balance`
  Row: `4/24/20 | 15 Minute Office Visit (Established Patient) | 99213 |
  $85.00 | $0.00 | $85.00`, with a second description line
  `Patient Responsibility`
- The free-text message near the bottom (`New Test Message`)
- **A bottom aging-bucket strip, ruled above and below:**
  `0-30` · `31-60` · `61-90` · `91-120` · `Over 120` · `Ins. Bal.` ·
  `Please Pay`
  with amounts under each (`$85.00 $0.00 $0.00 $0.00 $0.00 $0.00 $85.00`)

**This aging strip is the classic medical-statement look and is what the
office will expect at the bottom of a printed bill.**

### Right-hand panel, top to bottom
- `Statement Format:` dropdown — value **`Statement`**
- Buttons: `Print` · `Preview` · `Options` · `Close`
- Selection buttons: **`Check All`** (highlighted blue) · `Uncheck All` ·
  `Check Selected` · `Uncheck Selected`
- ☐ `Include $0 Patient Balance Claims`
- `Min. Pat. Bal.` — `$0.01`
- `Min. Sta. Cycle` — `30` (spinner)
- `Refresh` button
- ☐ `Count Payment Requests as Statements`
- `Send SMS Payment Request` · `Send Email Payment Request` ·
  `View EZClaimPay Log`

### Bottom of screen
`Global Message:` dropdown, value `Happy Holidays`. (`DZ0spaFoFz4`)

---

## 7. Program Setup (Tools → Program Setup)

Opens as a document tab named `Setup`. Three columns: an **`Options` list on
the left** (a plain list box, selected item highlighted), the **selected
pane in the middle** (its title centred and bold at the top), and
**`Save` / `Save & Close` / `Close` buttons on the right**. (`gO7UQeKlmFM`)

### The Options list, in exact order
```
General
Main Screen
Patient
Patient Custom Fields
Claim
Claim Custom Fields
Printing Claims
Printing Institutional Claims
Sending Claims
Payment
Document Linking
Company
Patient Eligibility
Task
Interface
```
(`gO7UQeKlmFM`)

### General pane
- `Theme:` dropdown — value **`Caramel`**. (This is why the whole app is
  orange/tan. Themes are a first-class setting.)
- ☐ `Alternate Grid Row Colors`
- ☐ `When using 'INSERT DATE AND TIME' buttons, insert the date and time at
  the bottom.`
- ☑ `Allow feature usage reporting`
- `Grid Footer Visibility:` dropdown — `Show Footers when Filtering`

### Patient pane
- ☑ `Automatic Account Numbers:`
- `Next Account Number:` `1012`
- `Next Account Number Prefix:` (blank)
- ☑ `Require Account Numbers:`
- ☑ `Require Account Numbers Entered to be Unique`
- `Automatic Patient Template:` dropdown — `None`
- `Initial Accept Assignment:` dropdown — `Yes`

### Printing Claims pane
- `Printer Alignment` — a numbered 4-step instruction block ending in a
  **`Print Test Page`** button; adjustments in **100ths of an inch**
  ("a value of 50 equals 1/2 inch"), with `Up/Dn` and `Left/Right` spinners
  labelled `+ Value moves up/down/right/left`.
- `Initial ICD Indicator:` `ICD-10`
- `Font Setting` — `Font:` `Courier New`, `Size:` `12`
- `Print Form with Data:` dropdown — `Preview Only`
- `1500 Form Printer:` dropdown
- Right column: `Bottom Margin`, `Carrier Area Location Adjustment`
  (`Up/Dn`, `L/R`), `Vertical Shift Adjustment`, `Horizontal Shift
  Adjustment`
- `Formats` block: `Box 24 - Date of Service:` `MMDDYYYY`,
  `All Other Dates:` `MMDDYYYY`, `Account Number:` `Account #`
- A checkbox about box `31, 32, or 33` being cut off — *"Use smaller font and
  tighter spacing in those boxes."*
(`gO7UQeKlmFM`)

### Company pane
Just `Company Description:` — a multi-line text box:
```
Community Counseling
555 Main Street, Suite 100
Anytown, MI  55555
```
(`gO7UQeKlmFM`)

---

## 8. Payer library & the Payment Matching Key

(`QqvTxnAk2uE`)

- Payers live in a **Payer Library**, reached by the `Payer` button in the
  ribbon's Libraries group, and there is a separate **`Find Payer` grid**.
- The payer entry form has a **`Payment Matching Key` field at the bottom**.
- **What it does:** makes the program treat several payer entries as *the same
  payer* for posting/payment-entry purposes. The stated use case is having
  multiple United Healthcare entries (some for electronic claims, some for
  paper) — set a matching key of `UHC` on all of them.
- **Recommended way to set it (per the narrator):** from `Find Payer`, select
  the payers (click first, hold `Shift`, click last), **right-click the
  selected entries → `Set Payment Matching Key`**, type the key. This avoids
  typos vs. typing it per-payer.
- Guidance: *"less is more… a single word or acronym is a good payment
  matching key."*

**This confirms a right-click context menu with bulk actions on grid
selections, and shift-click multi-select.**

---

## 9. The web portal — EZClaim Premier + Pay (2025, `DZ0spaFoFz4`)

A **completely different, modern look** from the desktop app: white, flat,
rounded cards, a dark-navy left icon rail, ALL-CAPS buttons. Runs in Chrome.
It does **not** replace the desktop app — payments taken here post back into
desktop EZClaim in real time.

**Left nav rail**, icon over label, top to bottom:
`Home` · `Patient` · `Claim` · `Analytics` · `Payment` (highlighted when
active) · `Libraries` · `Account Settings` · `Help`, with a `>` expander at the
top.

**Top bar:** EZClaim logo top-left; a centred `Site` search box with a
magnifier; user initials top-right.

**Every page** has: a `< RETURN` outlined button, then a **breadcrumb**
(`Payment > Payment entry > Create payment > Payment by EZClaimPay`), then a
large bold page title.

### Payment entry page
- `Source selection` section: *"Select the type and the desired source to
  proceed."* with a `Payment source` dropdown (`Patient`).
- Buttons: `SAVE CREDIT CARD` (outlined, with card icon) on the left;
  `CREATE NEW PAYMENT` (solid navy) and `DISBURSE PAYMENT` (greyed) on the
  right.
- A search box, then a filter funnel icon, `EXPORT`, `PRINT`.
- Grid columns: `Select` (radio) · `Patient Name` ⇅ · `Date of birth` ⇅ ·
  `Total Patient Balance` · `Total Insurance Balance`.
- Pagination footer: `1 – 1 of 1` with `|<  <  >  >|`.

### Create payment page
- **`Selected patient` card**: `Patient:`, `Date of birth:`,
  `Total Patient balance:` (`$4,115.00`), `Total Insurance balance:`
  (`($100.00)` — **negative money in parentheses**).
- **`Payment information`**: `Payment method *` dropdown, `Amount *` (`$0`),
  `Payment date*` (with calendar icon, hint `MM/DD/YYYY`), `Reference #`.
  Fields are Material-style outlined boxes with the label notched into the
  border; required marked `*`.
- **`Payment method` dropdown options, in order:** `EZClaimPay`, `None`,
  `Cash`, `Check`, `CC`, `EFT`, …
- Buttons `AUTO APPLY` (outlined) and `SAVE CHANGES` (solid navy).
- Below: a `Search` box, funnel icon, `ADD ADJUSTMENT IN THE TABLE`, `EXPORT`,
  `PRINT`.

### Payment by EZClaimPay page
- `New Payment` heading, `Use Credit card information:` with **three radio
  options**: `Saved on file` / `Read from a terminal` / `Type in manually`.
  - `Saved on file` → a `SELECT A CREDIT CARD` button and a read-only
    `Card on file` box (`Mastercard …5454 12/25`).
  - `Read from a terminal` → a `Terminal` dropdown.
  - `Type in manually` → ☐ `The card holder provided their card information
    through the mail`.
- `Patient: Patient, Brooks D (Account# 1073)`
- ☐ `Save card information on file`, ☐ `Add platform fee`
- Three charge rows, each `label | total | button`:
  - `Charge Balance: $2,260.00` | `Total Charge Balance: $2,260.00` |
    `CHARGE BALANCE`
  - `Charge COPAY: $10.00` | `Total Charge COPAY: $10.00` | `CHARGE COPAY`
  - `Charge Amount` input (`$0`) | `Total Charge Amount: $0.00` |
    `CHARGE AMOUNT` (greyed)
- Success modal: green check circle, **"Credit card charged successfully"**,
  buttons `GO TO NEW PAYMENT` (outlined) and `GO TO DISBURSEMENT GRID`
  (solid navy).

Portal features named in the narration: view patient balances and copays
including current and past due, swipe cards with a terminal, payment plans,
recurring payments, saved cards on file, and payments from **SMS reminders,
email payment links, and QR codes on statements** — all auto-posting back.

---

## 9b. EDI Reports screen

`View EDI Reports` on the Home flowchart, or the `EDI Reports (n NEW)`
ribbon dropdown. Document tab `EDI Reports`. (`ciHa8ZgTTKE`, `vZb1Uzv7I7c`)

- Top-left: `Connection:` dropdown (`TriZetto`).
- Hint text under it: **`Double click to View`**.
- Top-right: `Search for Keyword` box and a `Clear` button.
- Grid columns: `Name` · `Date Created` · `Type` · `Payer` · `Pmt Amt` ·
  `Date` · `Trace Number` · `Method` · `Note`, with checkboxes at the left.
  `Type` value is `ERA - ANSI 835`; `Method` is `ACH`.
- File names are literal, e.g. `835_Accepted.rmt`,
  `835_Accepted_Deductible.rmt[ARCHIVED]`, `835_Denied.rmt[ARCHIVED]`,
  `835_Payer_Not_Linked.rmt[ARCHIVED]`, `835_Service_Line_Not_Found.rmt`.
  **Unopened files appear at the top of the list in bold** (`ciHa8ZgTTKE`).
- A lower detail pane shows the check in monospace label/value form:
  `Payer Name:`, `Payee Name:`, `Payment Total:`, `Payment Date:`,
  `Payment Method:`, `Trace Number:`.
- Right-hand button column: `Open` · `Save Notes` · `Export File` ·
  **`Get Reports`** · **`Add Reports`** · `Refresh Reports` · `Close` ·
  `Check All` (split, ▾).
- Bottom right: ☑ `Show Archived`, then a caption **`Apply to Checked`** over
  `Archive` (split, ▾) and `Delete`.

`Get Reports` downloads from the clearinghouse; `Add Reports` opens a browse
dialog for a file already on disk — **and then asks whether to delete the
source file** (`vZb1Uzv7I7c`).

---

## 9c. Auto-posting workflow and the ANSI 835 Posting Options dialog

### Posting workflow (`ciHa8ZgTTKE`)
1. `View EDI Reports` → `Get Reports` (or `Add Reports` for a saved file).
2. **Double-click the file to open it.** You are then **asked to confirm the
   payer** — EZClaim matches by payer name, and asks you to pick when there is
   no exact match or more than one. (Picking wrong is recoverable: close the
   file and reopen, choosing the other payer.)
3. **Nothing posts yet** — the whole screen is a review step.
   *"We always give you a chance to review the data before posting."*
4. Review the grid; `＋` drills into per-service-line adjustment detail;
   `Open Claim` opens the claim itself.
5. Set each adjustment's action: **`Apply` / `Track` / `Ignore`** (radio
   columns in the lower grid).
   **Guidance given verbatim:** *"only apply adjustments you intend to write
   off; all other adjustments should be left to track, especially patient
   responsibility amounts."*
6. `Apply Payments and Adjustments` (top right) to post.
7. **After posting, rows go green if everything posted; problem lines show
   red with a warning message.**
8. `Run Report` to print a posting report.
9. `Close and Archive` — archives the file and returns you to `EDI Reports`.

### ANSI 835 Posting Options dialog (`N2hFJQDke_I`, `ciHa8ZgTTKE`)
Titled **`ANSI 835 Posting Options`**. Opened by the `Options` button.
It is itself a grid with the standard group band and filter row.

**Top grid — default action per adjustment reason code.** Columns:
`Apply` · `Track` · `Ignore` (three radio columns) · `Reason` · `Description`.
Rows are the CARC codes with their text, e.g.
```
1  Deductible Amount
2  Coinsurance Amount
3  Co-Pay Balance Due
4  The procedure code is inconsistent with the modifier used or a r…
5  The procedure code/type of bill is inconsistent with the place of…
6  The procedure/revenue code is inconsistent with the patient's a…
7  The procedure/revenue code is inconsistent with the patient's g…
8  The procedure code is inconsistent with the provider type/spec…
9  The diagnosis is inconsistent with the patient's age. Usage: Ref…
10 The diagnosis is inconsistent with the patient's gender. Usage:…
11 The diagnosis is inconsistent with the procedure. Usage: Refer t…
12 The diagnosis is inconsistent with the provider type. Usage: Ref…
13 The date of death precedes the date of service.
14 The date of birth follows the date of service.
```
**Default: every adjustment except `45` is set to `Track`** — stated as *"the
safest default action as it prevents accidental write-offs."* (`N2hFJQDke_I`)

Buttons on the right: `Save & Close` · `Cancel`, then
`Apply Selected` · `Track Selected` · `Ignore Selected` (bulk actions on a
multi-row selection).

**`Additional Options` block at the bottom (exact labels, in order):**
- ☐ `Overwrite existing allowed amounts when posting the 835`
  — seldom checked; only relevant if you enter payer allowed amounts manually
  in the procedure code library.
- ☑ `Use 835 payment date` — uses the check date; unchecked uses today's.
  **Does not apply to the already-open file** — change the date by hand or
  close and reopen.
- ☑ `Apply zero dollar disbursements` — needed when claims must go on to a
  secondary payer. Overridable per line via the `Apply Disbursement` checkbox
  on the preview screen.
- ☑ `Allow payments and adjustments greater than the balance to be applied`
  — *"an option we frequently see checked"*; allows an overpayment to post and
  take the line into a **credit / negative balance**. Without it, overpayments
  must be entered manually. **This is the setting behind the "Balance
  Exceeded" warning.**
- ☐ `Don't apply reversals of previous payments and adjustments`
- ☐ `Group adjustments by 'Claim Status' instead of 'Processed Status'`

On `Save & Close` the program **asks whether to apply the new settings to the
currently open file** — answer `Yes`.

### Lower adjustment grid on the 835 screen (`ciHa8ZgTTKE`)
Columns: `Apply Adjustment` · `Track Adjustment` · `Ignore Adjustment`
(radios) · `Group Code` · `Reason Code` · `Adjustment Description` ·
`Total Adjustments` · `Processed Status`.
Sample rows:
```
CO - Contractual Obligations | 45  | Charge exceeds fee schedule/maximum allowable or contra… | $80.00  | Processed
CO - Contractual Obligations | 181 | Procedure code was invalid on the date of service.       | $100.00 | Processed
PR - Patient Responsibility   | 2   | Coinsurance Amount                                      | $40.00  | Processed
```

### Full 835 preview grid column list (`ciHa8ZgTTKE`, wider capture)
`Status` · `Claim Invoice #` · `Claim Status` · `Patient Name` · `Procedure` ·
`Service Date` · `Line Charged Amt` · `Line Payment Amt` ·
`Apply Disbursement` (checkbox) · `Balance` · `CO Amt` · `PR Amt` ·
`OA Amt` · `CR Amt` · `PI Amt`

---

## 9d. The three 835 warning screens

These are worth knowing because they define EZClaim's *vocabulary for things
going wrong*, which the office will already use.

### "Balance Exceeded" (`puSJeow-pkk`)
Status `BALANCE EXCEE…` on a **pink/red row**. Means posting would push the
service line **negative**. Fixed by the `Allow payments and adjustments
greater than the balance to be applied` option, or by correcting the claim.

### "Payer Not Linked" (`m85vv2jh148`)
A modal titled **`Payer Not Linked`** with `OK`:
> "One or more service lines referenced by this 835 are not linked to the payer
> you selected. Disbursement and adjustment information will not be applied to
> these service lines."

Causes given: duplicate payers in the payer library and the wrong one picked;
or Medicare forwarded the claim to a secondary you didn't know about; or simply
picking the wrong payer from the dropdown.
Fix: **double-click the red status message to open the claim**, add the
secondary payer or fix the payer ID, then click **`Recheck Payer Links`** (or
close and reopen the file). You can still post without fixing it.

### "Service Line Not Found" (`qG699P9sC0o`)
> "One or more service lines referenced by this 835 could not be found in your
> claims. Disbursement and adjustment information related to the missing
> service lines won't be applied unless you match the service line manually."

Affected lines show **`SRVC…` / "service line not found" in red**.
Causes: the claim wasn't sent from EZClaim, the claim was changed afterwards,
or the payer bundled/unbundled codes.

**Fix — the `Find Service Line` dialog.** Double-click the red warning to open
a modal titled `Find Service Line` with a header line of the 835's data:
`Patient: JONES, TOM W    DOS: 12/17/2019    Procedure: 99999
Charge: $50.00    Units: 1`
Below it a grid with the usual group band and filter row, columns:
`Name` · `Srvc Date` · `Place` · `Proc…` · `M1` · `Charges` · `Units` ·
`Adjs` · `Paid` · `Balance`.
**EZClaim pre-fills the filter row with name, service date and procedure code**
to try to find the match. Footer reads `Shown: 0 (Filtered)` when nothing
matches. The instruction given: *"remove some of the data in the filter row —
put your cursor into a cell and back out the data until you find the service
line"*, then click **`Select`**. Repeat until every line is matched.

---

## 9e. Payment Modification screen (modify or delete a payment)

Document tab **`Payment Modification`**; title bar `Payment Modification -
EZClaim Billing - 8.0.664`. (`Y_glBgEkSHs`)

- Top left, same `Payment Source:` radio pair (`Patient` / `Payer`) and
  `Payer:` dropdown, then a block captioned **`Payment Details`**:
  `Amount:` (`$233.00`), `Pmt Date:` (`10/26/2020`), `Payment Method:` (`EFT`),
  `Ref #:` (`8899776`), `Add Ref #:`, `Note:`.
- Top right, caption **`Select the payment to be modified:`** over a grid with
  columns `Name` · `Pmt Amt` · `Disbursed` · `Remaining` · `Date` · `Method` ·
  `Ref #1`.
- Lower grid (the disbursements of the selected payment), columns:
  `Name` · `DOS` · `Proc Code` · `Mod` · `Line Charge` · `Line Balance` ·
  `Applied` · `Reason`, each row with an **`✕`** button at the left to remove
  that disbursement.
- Right-hand button column: `Save & Close` · `Save` · `Close` · **`Reset`** ·
  **`Delete`** · `Void / Refund EZClaimPay` (greyed).

---

## 9f. Physician / Facility Library

Ribbon → Libraries group → `Physician Facility`. Document tab
`Physician/Facility Library`. (`i-7SoiBCpjk`)

**Left list, captioned `Physician / Facility Library Entries:`**, a two-column
grid `Name` · `Classification`, whose first row is the literal
**`Add new entry…`**:
```
Add new entry…
DME PROVIDER         Ordering
EZCLAIM MEDICAL CLINIC  Facility
HEALTH CLINIC        Billing
REFERRING JONES      Referring
REFERRING MIKE       Referring
RENDERING MATTHEWS   Rendering
RENDERING ROBERTS    Rendering
SUPERVISING DAVID    Supervising
```
**`Classification` values: `Billing`, `Facility`, `Ordering`, `Referring`,
`Rendering`, `Supervising`.**
Under the list is a `Type notes here…` free-text box.

**Right-hand form, field by field:**
- `Display Name (Required):` — `HEALTH CLINIC`
- `Classification:` dropdown (`Billing`) and ☑ `Signature on File`
- `Type:` — radio pair **`Person`** / **`Non-Person`**
- `Last Name (if Person) or Organization Name (if Non-Person):`
- `First Name:` and `Middle:`
- `Address Line 1:` (`100 MAIN STREET`), `Address Line 2:` (`SUITE 200`)
- `City, State, ZIP:` (`ROCHESTER` | `MI` | `555554444`)
- `Telephone:` (`(444) 666-5555`) and `Fax:`
- `Email:` with a small `Email` button
- ☐ `Mark as Inactive` and **`Taxonomy Code:`** (`208D00000X`)
- Section **`Primary ID Numbers:`** — `NPI:` (`1012023034`) with a
  **`Lookup NPI`** hyperlink beside it, `Tax ID Type:` dropdown
  (`24 - Tax ID`), `Tax ID:` (`987654312`)
- Section **`Additional ID Numbers:`** — a grid `Payer` · `ID Type` ·
  `ID Number` with the placeholder row **`Click here to add a new row`**
- Right buttons: `Save & New` · `Save & Close` · `Close` · `Delete` ·
  **`Pay to Address`**
- Bottom right, a radio group captioned **`Entries That Are:`** —
  ⦿ `Active` / ○ `Inactive` / ○ `All`

The video also shows the **raw ANSI 837 text** with loop annotations
(`Loop 1000A - SUBMITTER NAME`, `Loop 2010AA - BILLING PROVIDER NAME`,
`Loop 2310B - RENDERING PROVIDER NAME`, `Loop 2400 - Service Line`) to show
where the taxonomy code lands (`PRV*BI*PXC*208D00000X`).

---

## 9g. Tasks

Fourth grid tab, `Tasks`. (`h8BdQO3FuPw`)

**Grid columns:** two narrow icon columns (`O…`, `O…`) · `Due Date` ·
`Subject` · `Assigned To` · `Status`.
Sample subjects: `Update BCBS …`, `Check On Hold Claims`, `Rejected Claim`,
`CO-181`. `Status` values seen: **`Not Started`**.
Under the grid: `Include:` ☐ `Completed` ☐ `Assigned to Others` (checked).

**Detail pane below, captioned `Task Information`**, label/value rows:
`Subject` · `Start Date` · `Due Date` · `Show Reminder` (checkbox) ·
`Reminder Date` · `Reminder Time` · `Status` · `Priority` (`Normal`) ·
`Progress` · `Created By` (`USER`) · `Assigned To` (`USER`).

**Creating tasks in bulk from rejections** — from a rejection report tab
(e.g. `Rejections - 20181012.1.277`) with columns `Rejection Date` ·
`Report` · `Name` · `1st DOS` · `Bill Date` · `Total Charge` ·
`Total Balance` · `Bill To`, and right-hand buttons `Check All` (split, ▾),
**`Create Tasks`**, `Close`.

`Create Tasks` opens a modal **`Create New Task from Rejections`**:
- `Subject:` (pre-filled `Rejected Claim`)
- `Assigned To:` dropdown
- `Start date:` (`None`) and `Status:` (`Not Started`)
- `Due date:` (`None`) and `Priority:` (`Normal`)
- `Associated Payer:` (`<Claim Bill-To Payer>`) with a picker and an `✕`
- ☐ `Reminder:`
- A radio pair ⦿ `Use Rejection Note` / ○ `Other` over a large notes box
- `OK` / `Cancel`

Confirmation toast: **`Task(s) Created — 1 task has been created.`** with `OK`.

---

## 9h. Statement Options dialog

`Options` button on the Statements screen. Modal titled **`Statement Options`**.
Intro line: *"The following options will be used when printing and exporting
statements."* (`-JrFNkPqilw`)

**Two address columns side by side:**
- **`Return Address`** — `Name:`, `Address 1:`, `Address 2:`,
  `City ST Zip:` (three boxes), `Phone #:`, then
  ☐ `Use Patient's Billing Provider's Address Instead`
- **`Pay To Address`** — gated by ☐ `Use a 'Pay To Address' different than the
  'Return Address'` at the top; its fields (`Name:`, `Address 1:`,
  `Address 2:`, `City ST Zip:`) stay greyed until that is ticked.
  **Note printed in the dialog:** *"Note: No 'Pay To Address' is shown on the
  'Standard' statement format."*

**Left checkbox column:**
- ☐ `Hide Diagnostic Codes`
- ☐ `Hide Procedure Codes`
- ☐ `Hide Aging Section`
- ☐ `Include Insurance Balances in Aging`

**Middle checkbox column:**
- ☐ `Show Payment Reason Descriptions`
- ☑ `Include $0 Balance Service Lines`
- ☑ `Include $0 Patient Balance Service Lines`
- `Days of History` — spinner, value `30`

**Right column:**
- ☑ `Show Last Payment Information`
- ☐ `Show Tracking Adjustments with the following Reason Codes:` with a
  combo below it containing `1, 2, 3`

Buttons: `OK` / `Cancel`.

**`Statement Format:` dropdown** on the Statements screen selects the layout;
the value seen throughout is `Statement` (the "Standard" format referenced in
the note above).

---

## 9i. Conditional formatting — how the row colours are made

**The pink/green row tinting is not hardcoded — it is user-defined conditional
formatting on any grid.** (`erCHIBu51xw`)

A modal titled **`Custom Condition`** with the heading
**`Format cells that match the following condition:`**:
- A condition builder row starting with an `And` node and a `＋` to add
  clauses, e.g.
  `[Patient Balance] Is greater than $0.00` or
  `[Claim Status] Begins with <enter a value>`,
  each clause with a pencil (edit) and a `⊗` (remove) icon.
- A **`with`** dropdown choosing the format. Options seen, in order:
  ```
  Bold Text
  Green Fill with Bold Text
  Green Fill
  Green Fill with Green Text
  Green Text
  Italic Text
  Red Bold Text
  Red Fill
  Red Fill with Red Text
  Red Text
  Strikethrough Text
  Yellow Fill with Yellow Text
  ```
- ☐ **`Apply formatting to an entire row`** — this is what turns a cell rule
  into the whole-row pink/green tint seen on the patient grid.
- `OK` / `Cancel`.

So the look to copy is: **"patient balance > 0" → Red Fill, applied to the
entire row.** That single rule produces the salmon rows that dominate every
EZClaim screenshot.

---

## 9j. Find grids (`Find Claim`, `Find Service Line`, `Find Payer`)

Reached from the ribbon `Find` split button. Each opens as its own document
tab (`Find Claim`, `Find Service Line`). (`erCHIBu51xw`, `CN2twFAShj0`,
`QqvTxnAk2uE`)

### `Find Claim` grid columns, in order
`OPEN` (an inline button on every row) · `Name` · `1st DOS` · `Claim Status` ·
`Bill Date` · `Total Charge` · `Total Balance` · `Insurance Balance` ·
`Patient Balance` · `Rendering Physician` · `Billing Physician` · `Claim ID`

`Claim Status` values seen: **`On Hold`**, **`Other`**, **`Ready to Submit`**.
(`erCHIBu51xw`) — added to the earlier list of `Submitted`.

### `Find Service Line` grid columns
`OPEN` · `Name` · `Srvc Date` · `Place` · `Procedure` · `M1` · `Charges` ·
`Units` · `Adjs` · `Paid` · `Balance` (`CN2twFAShj0`)

Typing `brook` into the `Name` filter cell narrows instantly — **the filter row
is the primary way people search in EZClaim**, not a separate search box.

### Column chooser
Right-click a column header → a floating panel titled **`Customization`**
listing the available-but-hidden columns, which you drag into the header.
Entries seen: `1st DOS`, `Bill To`, `Billing Phy`, `Claim ID`,
`Classification`, `Created Date`, `Custom Currency Value`, `Custom Date Value`,
`Custom Number Value`, `Custom Text Value`, `Custom True / False Value`,
`Diagnosis`, `Exported`, `Facility`, `Invoice #`, `Last DOS`, `Modified Date`…
(`PsLZgSmi_qs`)

---

## 9k. Widgets (the Home-screen tiles)

Home tiles are configurable objects from a **`Widget Library`**, opened as a
document tab. (`PsLZgSmi_qs`)

**Library grid columns:** `Show` (checkbox) · `Name` · `Description`, and
three inline buttons per row at the right: **`EDIT`** · **`COPY`** ·
**`DELETE`**.

**The stock widget list, with their descriptions as written:**
| Name | Description |
|---|---|
| `Claims Over 90 Days (Max 50)` | Shows the oldest 50 claims that are over 90 days due. |
| `Unpaid Patient Co-pays` | Shows service lines that have a patient amount due that the patient has not fully paid. |
| `Batch Status` | |
| `Expiring Auths` | Shows a list of active authorizations that are within 30 days or 3 units of expiring. |
| `Rejected Claim from Posted 277-CSR Reports` | |
| `Denied Claims from Posted 835 Files` | |
| `Claims with a Credit Balance (Max 50)` | Shows the 50 claims with the highest credit balance. |
| `Overdue Statements` | Shows a list of patients that have had 2 or more statements in the last 75 days without making a payment and … |
| (further rows, partly occluded) | "…that have not been fully disbursed", "…have not been applied to any service line charges", "…riginal Bill Date 45-60 days old with no disbursements applied", "…riginal Bill Date greater than 90 days old with no disbursements applied", "…are 'Ready to Submit' and 'Electronic' that have an Auth number assigned but the ser…", "…riginal Bill Date 60-90 days old with no disbursements applied", "…es that have a future date." |

**Widget editor modal** — titled `<Widget Name> … (UNSAVED)`:
- `Widget Name:` text box
- `Description:` multi-line box
- `# of Rows:` — `50`
- **`Click Action:`** dropdown — `Show Claim`
- **`Layout:`** — a live preview of the widget's own grid, with its title bar
  (`Claims Over 90 Days (Max 50)`) and columns (`Name` · `Bill Date` ·
  `Ins. Bal.` · `Tot. Bal.`), footer `Shown: 6`
- `OK` / `Cancel`

So each tile is: a name, a row cap, a click action, and a column layout —
and the big number on the Home screen is that widget's row count.

---

## 9l. Claim List Report — the report filter panel

(`N9QcUnB5kkY`) Reports are driven by a long **label / value grid of filters**,
grouped into collapsible sections with a `▲` chevron. Each value is a dropdown
defaulting to **`All`**.

**Section `Claim`:**
`Claim Bill To Payer` · `Bill To Sequence` · `Claim Primary Payer` ·
`Claim Rendering Provider` · `Claim Billing Provider` · `Claim Facility` ·
`Claim Ordering Provider` · `Invoice # Starts With` · `Claim Minimum Balance` ·
`Insurance Minimum Balance` · `Patient Minimum Balance` · `Printed` ·
`Exported` · `Self Pay` · `Claim Balance Is` · `Claim Classification`

**Section `Patient`:**
`Patient Classification` · `Patient` (with a picker and an `✕`) ·
`Account # Starts With` · `Active Status`

**Date sections above** use paired `Start` / `End` rows whose values are
`No Start Date` / `No End Date`, e.g. under `Last Printed Date`.

---

## 9m. Send Claims + the Errors and Warnings screen

(`sTZilSPX-Fc`, release 616 and later — **this is the current behaviour**)

**What changed:** the `Check for Errors` button is **gone** from the Send
Claims tab. Error checking now runs **automatically** when you click
**`Create and Send Batch`**. A popup says it is checking; if anything is found
you get a chance to review before anything uploads.

**Error vs Warning — EZClaim's exact distinction, worth copying:**
- **`Error`** = data missing that is important enough to **prevent upload**
  (example given: missing billing provider).
- **`Warning`** = data may be missing or incomplete, **the claim will still
  upload**, but will most likely be rejected at the clearinghouse or payer.

Honest caveat stated in the video: *"this functionality is not a complete claim
scrubbing system and will not catch all errors. It will catch most of your data
entry errors though."*

### `Errors and Warnings` document tab
Grid columns: `Severity` · `Message` · `Name` · `DOB` · `Account #` ·
`Srvc Date` · `Procedure`.

Real messages seen (useful as wording for our own scrubber):
```
Place of Service is missing.
The Insured's ID # is missing.
Needs DX
This service line must have a primary disbursement (enter a $0.00 di…
The Payer ID for 'CIGNA HEALTHCARE' is missing. Please add the Pa…
The Other Insured's ID # is missing.
Procedure Code is missing.
```
**Double-click a row to jump to the claim and fix it.**

Right-hand button column: `Check All` (split, ▾) · **`Create Tasks`** ·
**`Set Claim Status to 'On Hold'`** (a dropdown — any status) · `Close` ·
**`Report`** (print or export the errors and warnings).

Note the title bar on this capture reads `…Demo_Company_Jaime_B_PERMANENT`
and the patient grid carries extra columns `Pat. Bal.`, `Tot. Cla…`,
`Ins. Bal.`, **`Pat. Unapplied Bal.`**, with **negative balances shown in
parentheses** — `($25.00)`, `($150.00)`, `($122.00)`.

---

## 9n. Find grids: filter editor, sorting, saved layouts

(`p4sCfOq7ftc`) This is how EZClaim users actually work, so it matters for
feel.

### Sorting
- Click a column header → A→Z; click again → Z→A.
- **Shift-click additional columns to sort by more than one.**
- A sorted column shows an **up arrow (ascending) or down arrow
  (descending)**.

### Filtering
- Type into the **filter row** cell — e.g. `90834` in `Procedure` — and the
  grid narrows live, with totals updating at the footer.
- For anything more than one value, use the **Filter Editor**, reached two
  ways:
  1. **Right-click a column header → `Filter Editor`** from the submenu.
     *Tip given: right-click from the column you want to filter and the editor
     is pre-filled with that field.*
  2. **Hover a column header and click the small filter icon** that appears —
     this gives a checkbox list of the distinct values, plus a
     **`Numeric Filters`** tab with `greater than` / value dropdowns.

### Saved layouts
- **Right-click a column header → `Save Layout`**, give it a name
  (e.g. `Service lines with balance`).
- Saved layouts appear as **clickable entries along the bottom of the grid**
  and persist when the grid is closed and reopened.
- **They update in real time** as charges and payments are entered.
- **Layouts are per user and per grid.**

Worked examples given: private-pay patients (`Primary Payer` `is blank`),
and service lines where `Claim Status equals Ready to Submit` — the latter
*"because you can't view CPT codes from the send claim screen."*

### Creating a widget from a grid
**Right-click any column header → `Add as Widget`.** The widget dialog opens
pre-filled from the current filter. This is how the eight stock widgets are
extended. (`PsLZgSmi_qs`)

### The `Find` ribbon menu — full item list (`5aJQBFSmkbU`)
`Find Patient` · `Find Claim` · `Find Service` · `Find Payment` ·
`Find Task` · `Find Adjustment` · `Find Payer` · `Find Physician` ·
`Find Disbursement` · `Find Claim Note`

### `Find Task` grid columns (`2ZgChe2rNnE`)
`OPEN` · `Name` · `Payer` · `Subject` · `Start Date` · `Due Date` · `Status` ·
`Priority` · `% Complete`

---

## 10. Reports (names only so far)

From the overview video's report list (`_UZktuXNBxc`):
`Accounts Receivable` · `Adjustments` · `Authorizations` ·
`Carrier Mail Labels` · `Claims List` · `Dispursments` [sic — spelled that way
on screen] · `EZClaim Receipt` …

---

## Colour and type notes

- Desktop app theme seen is **`Caramel`** — tan/orange ribbon and window
  chrome, grey grids, blue selection, pink/salmon for "owes money" or
  "problem", green for "good"/"ignored". Themes are switchable in Program
  Setup → General.
- Type is small and dense, Windows system UI font; claim printing uses
  **Courier New 12**.
- Money is right-aligned; **negatives appear in parentheses** in the web
  portal (`($100.00)`) and with a leading minus typed by the user in the
  desktop grid.
- Balances that need attention render **red** in the payment grid.

---

## Gaps vs Thunder Claims today

Read against `claims_web.html` as it stands. Ordered by **what an EZClaim user
would notice first**.

1. **No ribbon.** EZClaim's whole navigation is a ribbon with named groups
   (`File / Edit / Find / New / Libraries / Alerts / Support`). We have a
   left tab strip (`Patients / Claims / Insurers / Providers`) and a right-hand
   button column (`Save & Close / Save / Close / Print / Scrub`). The button
   *names* match well — `Save & Close`, `Save`, `Close` are exactly EZClaim's
   payment-entry column — but there is no ribbon and no `New` group.

2. **No payment entry screen at all.** This is the single biggest gap. EZClaim
   has a whole `Payment Entry` document tab: check header (payer, amount,
   date, method, ref #), a service-line grid with `Payment` / `Adjustment 1` /
   `Adjustment 2` grouped columns, `Auto Apply`, `Remaining`, per-line `Pay`
   buttons, and the minus-sign convention for refunds/reversals. We have only
   four fields on the claim record: `Amount paid $`, `Date paid`,
   `Date submitted`, `Denial reason`. We cannot post a payment against a
   *service line*, cannot record adjustments with reason codes, and have no
   concept of a check that spans patients.

3. **No per-column filter row.** Every EZClaim grid has a permanent filter box
   under each column header plus an `✕` to clear. We have one `Filter by name`
   box spanning all columns.

4. **No "drag a column header here to group by that column"** band, and no
   grouping at all. It appears above every EZClaim grid and is part of the
   look even when unused.

5. **No grid footers with totals.** EZClaim shows `Shown: 30` and column
   money totals under every grid. We have a `totals` element on the claims tab
   only.

6. **Our grids are far narrower.** EZClaim patients grid: `Name`,
   `Account #`, `Classification`, `Eligibility`, `Pri Payer`,
   `Tot. Cla. Bal.` / `Pat. Bal.`. Ours: `Name`, `DOB`, `Insurance`. We have
   **no account number at all**, no classification, no eligibility, no
   patient balance on the list.

7. **No account numbers.** EZClaim auto-assigns them (`Next Account Number:
   1012`, optional prefix, require-unique), shows them in grids and on
   statements, and they are how the office refers to a patient. We key off a
   name.

8. **No row colouring by state.** EZClaim tints rows pink when money is owed
   and green when eligible/ignored, in the grid itself. We use status pills
   (`Ready` / `Submitted` / `Paid` / `Partly paid` / `Denied`) on one column.
   The pill *names* are close to EZClaim's `Ready to Submit` / `Submitted` —
   worth matching exactly.

9. **No detail pane under the grid.** EZClaim's lower-left pane
   (`Details / Claims / Services / Payments / Documents`) means you can see a
   patient's insurance and payment history without opening anything. We have
   nothing there.

10. **No patient statements.** EZClaim has a whole statements screen with
    check-all selection, `Min. Pat. Bal.`, `Min. Sta. Cycle`, statement format,
    global message, and a print/preview path. We print a CMS-1500 only. Given
    the family office **prints and mails**, this is a real workflow gap, not a
    cosmetic one.

11. **No document tabs.** EZClaim opens each screen as a closable tab beside a
    grid that never disappears, and marks dirty tabs with `*`. We have a single
    `Home` + one record tab.

12. **No Program Setup.** No theme, no printer alignment (EZClaim's is
    elaborate — 100ths of an inch, test page, per-box shifts), no account
    number policy, no company description, no font/format settings.

13. **No libraries UI parity.** We have Insurers and Providers lists, but no
    `Payment Matching Key`, no multi-select + right-click bulk actions, and no
    `Find Payer` grid.

14. **No eligibility check.** EZClaim shows `CHECK` / `VIEW` inline buttons and
    an `Active <date>` green cell per patient.

15. **No 835/ERA auto-posting**, and no `Apply` / `Track` / `Ignore` vocabulary.
    Out of scope while we are print-and-mail, but it is the vocabulary the
    office will expect around adjustments.

16. **No home-screen workflow flowchart or widget tiles.** EZClaim's Home is
    `Create Patient → Create Claim → Print Claims / Statements / Enter Payment
    / Send Claims → View EDI Reports` plus count tiles (`Claims Over 90 Days`,
    `Unpaid Patient Co-pays`, `Expiring Auths`, `Claims with a Credit Balance`).
    Our Home has three buttons and a totals block. The **tiles in particular
    are cheap for us to add and are the first thing the office sees.**

17. **No tasks.** EZClaim has a `Tasks` grid tab and a `Task` button in the
    ribbon's New group.

18. **Wording differences to consider aligning**: EZClaim says
    `1st DOS` (we match), `Tot. Chg.` / `Tot. Bal.` (we say `Tot. Bal.` —
    match), `Pri Payer` (we say `Insurance`), `Ready to Submit` (we say
    `Ready`), `Pat. Bal.`, `Ins Bal`, `Account #`.

---

*Study in progress — more videos to follow.*
