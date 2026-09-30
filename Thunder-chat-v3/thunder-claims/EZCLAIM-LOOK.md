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

The full range captured is **8.0.460 → 8.0.670**, plus the separate older
product **EZClaim Advanced 10** — see the timeline in §11, which corrects a
few earlier guesses about what changed when. `Demo_Company_Jaime_B` is a
**company file name**, set at install (§1c, §11).

There are **two different web products called "portal"**: EZClaim Premier + Pay
(2025, `DZ0spaFoFz4`, §9) takes card payments; the EZClaim Portal (2017,
`D5CVTNTdCHw`, §9o) is a read-only provider reporting view. Neither replaces
the desktop app.

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

**`Help Topics` is on the ribbon of every tab and is always available
regardless of which screen you're on** (`ikUIM2AVURQ`). It opens a real help
system with a **topic tree on one side and keyword search** — there is a
topic called `Grids` that documents exactly the behaviour in §2. Support is
also surfaced in-product as a phone number and address:
**877-650-0904 / support@ezclaim.com**. EZClaim is **Windows-only**, and the
webinar tells Mac users on emulation that missing right-click menus are
expected and to call support.

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

## 1b. The three areas — EZClaim's own framing

The navigation tutorial names the layout explicitly, and this is the vocabulary
to design against (`B2WenGr6fcQ`):

1. **The ribbon bar** — "acts as a menu system to access all areas of the
   program." **It is dynamic:** *"as we open patients and claims you will
   notice additional ribbon bars that appear with items relevant to items
   you're working on."* (Hence the `Patient` and `Claim` ribbon tabs in §3b
   and §3c.)
2. **The search pane** — the left side. *"Here you will find all of your
   patients, claims, reports and tasks. Within each tab are additional detail
   screens that allow you to quickly find information without opening
   additional screens."*
3. **The main work area** — the right side. *"When the program opens the
   homepage is shown automatically. Every time a new item is opened a new tab
   will appear."* Return home via the `Home` ribbon icon or the `Home` tab;
   close a tab with its `✕`.

**Several records can be open at once** — e.g. tabs
`Home ✕`, `BROOKS, PATIENT D (Age: 48) ✕`, `CARSON, PATIENT (Age: 66) ✕`
side by side (`B2WenGr6fcQ`).

**One rule worth copying exactly:**
> "the search pane will only show **active** patients, whereas the find window
> will show **all** patients whether they're active or not"

That is what the `Active` / `Locked` checkboxes on the patient screen and the
`Entries That Are: Active / Inactive / All` radio group in the library are for.

---

## 1c. The orange EZ button — the Office menu and **company files** ★

The round orange **EZ button** at the very top-left (above the ribbon tabs, in
the title bar) is an Office-2007 "Office button". Clicking it drops a two-pane
menu (`tJsKQEAoRw4`):

| Left column | Right column |
|---|---|
| `New Company...` | **`Recent Companies:`** — a list of company files, each with a **pin** icon to keep it at the top |
| `Open Company...` | |
| `Save` (greyed) | |
| `Print ▸` | |
| `Backup Company...` | |
| `Exit` | |

**This is the single biggest structural fact about EZClaim that was missing
from these notes: a *company file* is a whole separate database.** A billing
service keeps one company file per provider office, and
`Open Company...` → pick → `OK` switches the entire program to it. Everything
is per-company: patients, claims, **all libraries** (physician, payer,
procedure code), **all reports, all claim batches and all EDI reports**, and
every Program Setup option. Nothing is shared. (`tJsKQEAoRw4`)

EZClaim is explicit that this maps onto the clearinghouse's own structure: with
TriZetto a billing service gets a **parent site ID** and one **child site ID**
per provider, and *"you would set up all of your child sites as separate
company files"*, each with its own site ID in the Connection Library.

**The alternative, for offices that want one database:** put every doctor in
one company file and separate them with the **`Classification`** field, which
is a column on the patients grid and filterable like any other. Classification
values seen in the demo data are literally doctor names — `DR BROOKS`,
`DR. SMITH` — alongside payer-ish ones like `MEDICARE`, `GENERAL G…`. The
patients-grid footer then reads `Shown: 5 (Filtered)`. (`tJsKQEAoRw4`)

**Title bar carries the company name**, which is how you know which database
you are in: `Home - EZClaim Billing - 8.0.596 - Demo_Company_Jaime_B`.

---

## 1d. Users, permissions and the activity log (`tJsKQEAoRw4`)

`Tools` → `Manage Security Settings` opens a document tab whose title bar reads
**`User Management`**.

- Top left: a radio pair **`Don't Require User Authentication`** /
  **`Require User Authentication`** — so login is *off by default*.
- Left list: `Add new entry...` then the users (`Jaime`, `Jane`, `Mike`,
  `ReadOnly`, `Sandy`).
- Right: `Username:`, `Password:`, `Confirmation:`, **`Windows User:`**
  (so a user can be mapped to a Windows account), then a two-column
  permissions grid `Permission` / `Allowed` (checkboxes).

**The permission list, in screen order — this is EZClaim's own idea of what
the dangerous verbs are:**
```
Full access to all areas of the program (if granted, overrides all other permissions).
Manage patient statements
Print or preview paper claims
Manage data entry libraries
Unlock Claims
Submit claims and retrieve reports
Add or edit patient records
Delete patient records
Add or edit claims
Delete claims
Add, edit, and delete payments and adjustments
Add, edit, delete, or view document links
View documents linked to patients
Print, preview, and export reports
Manage payer/physician/auth libraries
Unlock Patients
Merge Patients
Review Data for Import
Manage Add-On Services
```
Selecting a row prints its description in a strip along the bottom.
Buttons: `New` · `Save` · `Close` · `Delete` · **`Log`**.

**`Log`** opens the audit view: *"login and logout times and from what computer
they did it from."*

**The consequence EZClaim calls out, and it matters to us:** if you don't
create users, *"everybody and everything just gets tagged as generic user"* —
you can see it in the demo data, where the `Created User` / `Modified User`
columns and the claim-note `USER` column read `USER` or `ADMIN` for the
unattributed work and the real name (`Jaime`) only after login. There are two
reports for this (`User Claim Activity`, `User Patient Activity`), and
`Created User` / `Modified User` are **column-chooser columns on `Find Claim`**.

---

## 1e. The Rule Library — user-definable validation rules ★ (`tJsKQEAoRw4`)

EZClaim has a **validation-rule engine**, described on camera as
*"kind of an easter-egg feature, hidden feature within the program"* that
customers are not expected to configure themselves — you call support and they
set rules up for you.

Document tab / title bar: **`Rule Library`**. Layout is a list captioned
**`Rule Types`**:
```
Sending claims
Saving a patient
Saving a payer library entry
Saving a physician library entry
```
with a description strip under it (`These rules are used to validate claims
before they are sent.`) and two buttons, **`Edit Rules`** and `Close`.

So the rules fire at **four** moments, not only at send time. The shipped ones
that a user will already have met:

- the **physician library** refusing to save and popping one message at a time
  — *"why am I missing a zip code"*, then *"I need a tax ID for this field"* —
  i.e. **one validation message per attempt, not a list**;
- `Send Claims` → `Check for Errors`, which *"is checking up against our
  validation rules for sending claims — is there a billing provider, if it's a
  secondary claim it's looking for a primary payment."*

Named example of a customer-requested rule: *"checking patient relationship to
insured, to make sure that it is checked as spouse or child if it's not self."*

**EZClaim is explicit that this does not validate codes** — *"it just is a
simple check to see if you have any missing elements that might be required."*
That is exactly the line our `Scrub` button should draw too.

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

### Grid behaviour — the full rule set (`B2WenGr6fcQ`, `p4sCfOq7ftc`)

**Grid customisation is per user.** *"When you customize a grid it applies only
to you. It will not affect other users on the system."*

EZClaim's own names for the parts: **grouping panel** (the drag band),
**column headings**, **filter row**, **rows**.

**Sorting**
- Click a heading → ascending, shown by a **triangle** in the heading.
- Click again → descending, **triangle flips**.
- **Shift-click** further headings to sort by several columns; each gets a
  triangle.
- **Right-click a heading → `Clear Sorting`.**

**Filtering**
- Type the first few letters into the filter row; **the grid changes
  dynamically as you type**.
- **`✕` at the far left of the filter row clears the filter.**
- **The `%` wildcard matches text *within* the column** — typing `%tom` in
  `Name` finds `JONES, TOM W`. Footer then reads **`Shown: 1 (Filtered)`**.
- Filter in one or more columns at once.
- **Filter menu:** click the small filter icon in a heading → a checkbox list
  of the available values, **including blank and non-blank**.

**Columns**
- **Drag headings left or right to reorder.**
- **Right-click a heading → `Column Chooser`** → a floating list of available
  columns; **drag an item into position** — *"notice the location arrows that
  show you where the column will be placed when dropped."*
- **Remove a column by dragging it out of the grid** — an **`X` indicator**
  appears.
- **Drag a column edge to resize, or double-click the edge to auto-fit.**
- **Right-click a heading → `Restore Grid`** to undo all customisation.

### Column-heading right-click menu — the complete list, in exact order

Captured whole and unoccluded in `ikUIM2AVURQ`. **This one menu is the entire
grid feature set**, and it is the same on every grid in the program:

```
Sort Ascending              (A→Z icon)
Sort Descending             (Z→A icon)
Clear Sorting
Group By This Column
Hide Group By Box
Hide This Column
Column Chooser
Best Fit
Best Fit (all columns)
Filter Editor...
Show Find Panel
Hide Auto Filter Row
Conditional Formatting     ▸
Hide Footer
Save Layout
Restore Grid
Print Grid
Export to                  ▸
Add as Widget
```

Note what that implies and earlier videos only hinted at: the grouping band,
the filter row and the footer are all **toggleable from this menu**
(`Hide Group By Box`, `Hide Auto Filter Row`, `Hide Footer`), and
**`Export to`** is a submenu (PDF, Excel, "and some other various file").
`Set Payment Matching Key` appears additionally on the payer grid when rows
are selected.

### The four areas of a grid — EZClaim's own teaching order (`ikUIM2AVURQ`)

The webinar names exactly four:

1. **Group-by area** (top) — drag a column header up into it to group; e.g.
   dragging `Primary Payer` up groups all claims under collapsible payer
   headings. Drag the header back down to ungroup.
2. **Column headers.**
3. **Filter row.**
4. **Footer area** (bottom) — shows **totals for any *numeric* column that is
   visible**, and the **bottom-left always shows the row count**
   (`Shown: 11 (Filtered)`).

**The visual tell that something is a grid:** *"all of my column headers change
colour as I hover over them with the mouse."* If headers highlight on hover,
every feature above is available.

### Where grids appear — it is nearly everywhere (`ikUIM2AVURQ`)

*"Premier is a SQL-based program and so it makes extensive use of this grid
technology."* Named as grids: the **patient quick-access pane**, the **claim
tab** beside it, the **`Details` / `Claims` / `Services` / `Payments` detail
tabs** below, **every `Find` window**, the **service-line grid inside a claim**,
and the **patient statement screen**. Effectively every list of data in the
program is the same control with the same nineteen-item menu.

**Rows**
- **Double-click a row to open the item** in the work area.
- Rows carry inline buttons for specific tasks (`OPEN`, `Pay`, `CHECK`,
  `VIEW`, `DISBURSE`, `MODIFY`, `EDIT`/`COPY`/`DELETE`).
- The leftmost icon cell has its own action — on the patient grid it offers
  **`Add Claim`** (`b1AJePNYbcs`).

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

  **The sequence has a third form, `Final`, and EZClaim drives it
  automatically** (`uEox7GQtBhI`, `tJsKQEAoRw4`). Full set seen:
  `Primary (1/1)`, `Primary (1/2)`, `Secondary (2/2)`, and
  **`Final (F/2) - Patient - BROOKS, PATIENT D`** — where the responsible party
  is the patient and the `Resp. Party` cell on each service line flips from the
  payer name to **`Patient`**. Posting an 835 or writing a claim off is what
  advances it, not the user. See §9c for the exact rule.
- `Prior Auth #:` — dropdown + `…` + a small **ⓘ** info icon.
  In 8.0.596 the empty state shows the placeholder text **`Auth Available`**
  in the dropdown (`tJsKQEAoRw4`).
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
below. Two hint texts are used:
- **"Enter the service line data above and click the 'ADD' butt…"**
- **"Click a date on the calendars above to enter a new service line"**
  (`sEgz49YE1lI`)

**The hint is dynamic and counts the template's lines** (`-vHuSb1e9iU`). With
a template selected — `Claim Template: 2 Region Adjustment with Massage and
Ultrasound` — it changes to
**`Click a date on the calendars above to enter the 3 services line from the
selected template`**, and one click on a date adds all three lines at once
(`98940`, `97124`, `97035`, each `$25`–`$55`, `Units 1`). The grammar is wrong
in EZClaim's own UI ("3 services line"); the behaviour — *a template is a set
of service lines, and the hint tells you how many you are about to get* — is
worth copying exactly.

**Two more columns appear at 8.0.655/656** (`TDIWTgfUJ2g`): a **`Sort`** column
and **`SrvID`**, plus a `Print…` checkbox column and a trailing `…` ellipsis
button per row. `SrvID` is the service line's own id, which is what the 835
matcher (§9d) is trying to find.

**Full column list** (`sEgz49YE1lI`):
`Srvc Date` · `Place` · `Procedure` · **`M1` `M2` `M3` `M4`** ·
**`Diag. #`** · `Charges` · `Units` · `Adjs` · `Paid` · `Applied Amt.` ·
`Balance` · `Resp. Pa…` · `Pat. Amt.`

`Place` defaults to `11`; `Diag. #` holds the diagnosis pointer as a **number**
(`1`), not the letter. `Resp. Pa…` shows the payer (`MEDICAR…`).
Each saved row has a `＋` expander and an `✕` delete button.
Footer: **`Services: 0`** plus a full row of column totals.

### Right panel — collapsible sections, and it is **editable**
Not a read-only summary: each row is a dropdown, date picker or checkbox.

**`Claim Information`**
`Original Bill Date` · **`Status`** (`Ready to Submit`) · **`Method`**
(`Electronic`) · `Last Printed` · `Last Exported` · `Invoice #` ·
`Claim ID` (greyed, `New` until saved, then a number) · ☐ **`Locked`**

**`Physician Library Entries`** — each a dropdown + `…` + `✕`:
`Rendering Provider` (`KEVIN ROBERTS`) · `Referring Provider` (`None`) ·
**`Service Facility`** (`None`) · `Billing Provider` (`HEALTH CLINIC`)

**`Printing Options`** — ☐ `Totals on Last Page`

**`Date Information`** — `Admitted Date` (and more below the fold)

### Right-hand button column (`sEgz49YE1lI`)
`Save & Close` · `Save` · `Close` · `Delete` ·
**`Hide Notes`** (split button, ▾ → `Expand` / `Shrink`) ·
**`Scrub`** · **`Status`**

**EZClaim calls its claim check `Scrub` too** — our button name already
matches.

### Notes at the bottom
A prompt **`Click here to add a new note`** over a notes grid with columns
**`Time Stamp` · `User` · `Note` · `Balance`**, a filter row, and an `✕` per
row. Entries are both typed and **auto-logged**, and each records the claim
balance at that moment:
```
05/13/2014 11:43 AM | USER | This is a user note   | $0.00
05/13/2014 11:40 AM | USER | Claim created.       | $180.00
11/23/2018 10:32 AM | USER | Claim edited
```
Clearinghouse 277 messages land in this same note area (§9m3).

**The notes grid is wider than that.** In the 8.0.581 and 8.0.596 captures it
carries the **whole money position at the moment of the note** — after `Note`
come `Units`, `Charges`, `Adjs`, `Paid` and `Balance` columns, so a single note
row reads `11/30/2016 11:21 AM | USER | MEDICARE: Payments Applied. | 2 |
$100.00 | $40.00 | $20.00 | $40.00`. It is a **running ledger with commentary**,
not a comment box. (`uEox7GQtBhI`, `tJsKQEAoRw4`)

**Auto-logged notes cannot be deleted; typed ones can.** In `tJsKQEAoRw4` the
manually entered rows (`Need to verify Insurance`, `This is a test for
Dr. Jones`) carry an `✕` delete box and the machine-written ones
(`Claim Balance Written Off`, `Adjustments Applied`, `Claim created.`) do not.
That is a real audit property and worth copying.

**Auto-logged note vocabulary, collected across videos** (`uEox7GQtBhI`,
`tJsKQEAoRw4`, `ctXeB-wct-A`):
```
Claim created.
Claim edited.
Claim insurance information edited.
Claim information updated from Find Claim screen.
Claim exported: MEDICARE: File: 'C:\…\EDIExports\160429_09524156'
Adjustments Applied
Claim Balance Written Off
MEDICARE: Payments Applied.
MEDICARE: Applied Payments Removed.
MEDICARE: Processed as Primary
MEDICARE: Payment data applied from 835 file '835_Accepted.txt'.
REJECTED - MEDICARE  (followed by the full 277 text)
```
Note the shape: **payer-sourced events are prefixed with the payer name and a
colon**, local edits are not. Deleting an auto-posted payment writes
`Applied Payments Removed.` rather than erasing the earlier notes — the history
is append-only.

**`Note Templates`** (`tJsKQEAoRw4`): a claim or patient note cell has a
right-click → **`Insert Note Template`**, filled from a **note template
library** where each entry has a name and a body. *"The program can handle many
notes there."* This is how an office keeps its follow-up wording consistent;
cheap for us and it removes a lot of typing on a phone.

**`ICD Indicator`** (`tJsKQEAoRw4`, 8.0.596): an extra `Claim Information` row
between `Method` and `Invoice #`, value `ICD-10`. Not present in the 8.0.581
capture, so it arrived between those builds.

**The `Locked` checkbox is real and is in every capture** — 8.0.581, 8.0.596
and 8.0.655 all show `Locked` as the last row of `Claim Information`
(`uEox7GQtBhI`, `tJsKQEAoRw4`, `ctXeB-wct-A`). No video shows what it *does*,
but the security model does: `Unlock Claims` and `Unlock Patients` are
**separate grantable permissions** (§1d), so locking is meant as a
supervisor-controlled state, not a personal convenience. See the printing
section at the end for the help-manual claim about it greying out fields.

**`Tasks` on the `Claim` ribbon carries a count** — the button reads
**`Tasks (1)`** when the open claim has one task linked to it (`uEox7GQtBhI`).
Same idiom as `EDI Reports (3 NEW)`.

### Document tab title
`BROOKS, PATIENT D` before a service line exists, becoming
**`BROOKS, PATIENT D - 04/09/2014`** once there is a first DOS, with `*` while
dirty.

### Claim status values (collected across all videos)
`Ready to Submit` · `Submitted` · `On Hold` · `Other`
(`oZBevrOFRwY`, `erCHIBu51xw`, `uqRGjzNM-KE`, `sTZilSPX-Fc`)
`Method` values: `Electronic` (and paper, implied by the `All Electronic`
filter on Send Claims).

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
buttons — **these add or remove whole `Adjustment N` column groups** — and a
checkbox list that toggles sub-columns:
- ☑ `Show Adj Reason Codes`
- ☑ `Show Adj Remark Codes`
- ☐ `Show Adj Reason Amount`
- ☐ `Show Payment Reason Codes`
- ☐ `Show Notes`

With remark codes on, each `Adjustment N` group has **four** sub-columns:
`Amt` · `Code` · `Reason` · **`Remark`** (`QiiFx0hCFMU`).

### When `Payment Source` is `Patient` rather than `Payer` (`QiiFx0hCFMU`)
The `Payer:` dropdown is replaced by a **`Patient:`** dropdown, the banner
reads `Payments from TESTING, MEGAN R with a balance:`, and
**`Match By Payer ID` greys out** (it is meaningless for a patient payment)
while `Ignore Responsible Party` stays available. In this build the filter
options sit directly on the rail rather than behind the `Filter Settings`
button: ☑ `Ignore Responsible Party`, ☐ `Match By Payer ID`,
☐ `Include $0.00 Balance Service Lines From DOS:` with a date picker.

The service-line grid also carries a **`Claim ID`** column here
(`1248`, `1247`, `1242`…), and **every payment row in the top-right grid gets
its own `DISBURSE` / `MODIFY` pair**, not just the selected one.

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

### Status column values — the complete set (`uEox7GQtBhI`)

The `Status` column is **blank before posting and that is the good case** —
*"it's typically blank when you first open an 835, and that's a good thing;
that means the program was able to find all the service lines it was supposed
to."* After posting it fills in. Values seen, with their row treatment:

| Value | When | Look |
|---|---|---|
| *(blank)* | before posting, everything matched | normal |
| **`APPLIED`** | posted successfully | **green row** |
| **`IGNORED`** | adjustment ignored | **green row** |
| **`MATCHED`** | this payment was already posted; nothing done | green row |
| **`SRVC LINE NOT FOUND`** | no matching service line | **bold red text**, normal row, tooltip repeats the text |
| **`PAYER NOT LINKED`** | payer not on the claim | **bold red text** |
| **`BALANCE EXCEE…`** | would go negative | **pink/red row** |

`Claim Status` (the payer's own word for what it did) values seen:
`Processed as Primary`, `Processed as Primary, Forwarded HUMANA`,
**`Reversal of Previo…`**, and **`Denied`** — the last rendered as
**bold red text on a pink cell** (`uEox7GQtBhI`).

### Group codes seen in the adjustment grid
```
CO - Contractual Obligations
PR - Patient Responsibility
OA - Other Adjustments
CR - Correction and Reversals
PI - Payer Initiated Reductions
```
(`uEox7GQtBhI`)

### Adjustment-grid right-click menu
`Create Tasks Linked to Claims` · `Print Grid` · `Export to ▸` (`uEox7GQtBhI`)

### Service-line grid right-click menu
Two items only: **create tasks linked to the claim**, and **remove the
connection from the service line** — the latter described as *"a little trick
that can be used to skip a particular disbursement if you want to."*
(`uEox7GQtBhI`)

### `View Adjustments Ungrouped` — and the one-way door ★

The lower grid normally **summarises**: one row per (group code, reason code),
so you `Apply` or `Ignore` *all* the 45s at once. The
**`View Adjustments Ungrouped`** button explodes it to one row per service
line, giving per-patient control. Columns change to:

`Action` (an in-cell dropdown) · `Group Code` · `Reason Code` ·
**`Remark Codes`** · `Adjustment` · `Procedure` · `Charge` · `DOS` ·
`Patient` (`uEox7GQtBhI`)

Multi-select and right-click sets `Apply` / `Track` / `Ignore` on the whole
selection, and you can drag a column into the group-by band and set a whole
group at once.

**Once ungrouped you cannot regroup** — the button greys out, verified on
screen. Stated reason: *"you obviously might have made some granular changes
that we wouldn't be able to summarise anymore because it wouldn't make sense."*

### Remark codes live in the child grid
Drilling into an adjustment row shows the individual service lines **and the
remark codes**. If a remark was given at *claim* level EZClaim **repeats it
onto every service line of that claim** rather than hiding it. (`uEox7GQtBhI`)

### Why the whole screen is service-line-shaped, in EZClaim's words
> "The reason we show service lines instead of claims is because … in medical
> billing, they actually pay the actual service line. So it's much easier to
> work with individual service lines than the overall claim."

Which is the same reason our four flat payment fields on the claim are the
wrong shape (gap 2).

### The vocabulary, stated up front (`uEox7GQtBhI`)
- **payment** — the total amount of the check or EFT
- **disbursement** — what is applied to each individual service line;
  *"if you add up all the disbursements, that should equal the total payment"*
- **adjustment** — a write-off
- **835 = ERA = EOB** — *"they all represent the same thing"*

### `Run Report` is a split button, and the useful one is not a report
`Run Report ▾` offers several outputs including a lines-with-errors report and
a **`Posting Grid`** — *"really not a report at all, but a grid"* — a
spreadsheet-shaped view of **all disbursements and adjustments in one place**,
filterable, and **exportable to Excel via the column-header right-click →
`Export to`**. Caveat given on camera: it contains **service-line information
only**, so claim-level and provider-level adjustments are missing from it.
(`uEox7GQtBhI`)

---

## 5b. The auto-posting scenarios — what goes wrong and what EZClaim does

All from the 80-minute auto-posting webinar (`uEox7GQtBhI`), which is the
single best source on this screen. Captured at **8.0.581**.

### Posting the same 835 twice
The program recognises it: a warning says you already have a payment from this
payer with this reference number and amount, and asks whether to continue. If
you go ahead, the lines come back **`MATCHED`** on a green board and
**nothing is double-posted**. *"It's not going to hurt anything to post it
twice."*

### Deleting an auto-posted payment — and the four things it does NOT undo ★
From `Find Payment` → `MODIFY` → `Delete`, you get a second prompt asking
whether to delete the **adjustments** posted with it (normally yes).
What comes back is **only the payment and the adjustments**. It does **not**:

- remove the `Original Reference Number` it wrote onto the claim,
- change `Bill To` back from Secondary to Primary,
- change the claim `Status` back from `Ready to Submit` to `Submitted`,
- remove the claim notes (they are append-only — you get a new
  `Applied Payments Removed.` note instead).

**This is the honest version of "undo" and it is worth stealing the honesty:**
the stated purpose is *"maybe you applied some adjustments and you actually
wanted to track them — this is a way you could undo that so you could redo the
835 posting again"*, not a full reversal.

### One 835 file containing two checks → **split it**
Double-clicking pops a chooser. You can `Select` each payment one at a time,
but the recommendation is unambiguous: use the **`Split`** button at the bottom
left. EZClaim writes two new files — `835_Multiple_Payments_1.txt` and
`_2.txt`, each with its own auto-note — then asks whether to archive the
original (say yes). *"Just makes life much easier."*

### `Payer Not Linked` — the two causes
1. The payment is from a payer **not on the claim at all** — classically
   Medicare forwarded to a secondary the office didn't know about. Fix: open
   the claim, add the secondary in the claim insured window, save, then click
   **`Recheck Payer Links`** — the row disappears from the warning group and
   drops to the bottom of the list, clean.
2. **The payer library has no payer ID**, or has duplicate entries where one
   has an ID and one doesn't. Matching is **payer ID first, then name**. Fix is
   in the library, not the claim.

There is also a **merge utility for duplicate payers** — *"I think you hold the
control key and click the payer icon"* — with a recommendation to call support
before using it.

### `Service Line Not Found` → the `Find Service Line` matcher
Exact modal text (`uEox7GQtBhI`, title **`Service Lines Not Found`**):
```
One or more service lines referenced by this 835 could not be found in your claims.
Disbursement and adjustment information related to the missing service lines won't
be applied, unless you match the service lines manually.
To manually match a service line that wasn't found, double-click on it.
```
Causes given: the claim was never entered in EZClaim (common for new
customers); or **the payer recoded** — *"you might have sent in code A and
they've returned code B"*, and *"I've seen scenarios where they've split one
service line into two, two service lines into one."*

Double-clicking the red line opens **`Find Service Line`** with a header strip
of the 835's own data and the grid's **filter row pre-filled** with patient,
DOS and procedure code — so it shows nothing. The technique is to **delete the
filter value that is wrong** (usually the procedure code), tab out, and the
right line appears; the screen refreshes to show it matched. Repeat per line,
then post normally.

If you simply can't match it: *"Premier will post what it can and just leave
the remaining balance on that payment."*

### `$0.00` payments — and why you still post them
Header reads `Payment Total: $0.00` and **`Payment Method: No Payment`**.
Typically early-year deductible: the payer sends contractual obligations and a
patient-responsibility deductible and pays nothing. **Post it anyway** — not
for the money but because applying the CO adjustment is what flips `Bill To`
down to `Patient` so the office can bill a statement.

> "Even though the payment is zero, it's still important to post the
> information so the claims can move through the process."

### Reversals — why a reason code appears twice
When an 835 contains both payments and reversals the adjustment grid lists the
same reason code (e.g. 45) on **two rows**, distinguished by the
`Processed Status` column: **`Processed`** vs **`Reversal`**, with the reversal
carrying `CR - Correction and Reversals` and a negative amount in parentheses
(`($20.00)`). *"It's not an error or a mistake — it's just saying, maybe I
don't want to post the 45 adjustment reversal."*

### Claim- and provider-level adjustments — the hardest case ★

These have **no service line to attach to**, so EZClaim cannot post them and
does not pretend to. What it does instead:

1. On opening the file, a notification warns there are claim or provider level
   adjustments.
2. `OK` opens a modal titled **`Claim or Provider Level Adjustments`** showing
   a monospaced block, with **`OK` and a `Print` button**:
   ```
   Claim Account Number: 42-1004
   Claim Level Adjustment:
   Group Code: Payer Initiated Reductions
   Reason Code: 85-Interest amount.
   Amount: 1
   ```
   **You are told to print this**, because the posting screen that follows does
   not carry the information.
3. Post as normal. Because the check was $41 and the lines only total $40, a
   warning fires saying so. *"This is an expected window. It's not an error."*
4. Then you fix it by hand.

**The manual fix, which is a genuine piece of tribal knowledge:**
- The `Claim Account Number: 42-1004` decodes as **claim ID 42** (the `42-`
  prefix), so `Find Claim` → filter `Claim ID` = 42.
- Open the claim, click a date on the calendar to add a **new service line**.
- Type a made-up procedure code — literally **`INTEREST`** — with `Charges`
  `$0.00`.
- Double-click the `Adjs` cell, add an adjustment with group code
  payer-initiated, reason `85`, and **amount `-1`**:
  > "You typically enter adjustments as a positive number, but in this case
  > the payer is giving us money, so we need to enter a negative adjustment."
- Date: **`T` is a keyboard shortcut for today** in EZClaim date cells.
- The claim now shows a $1 balance; go back to the payment and `Pay` it.

**For *provider*-level adjustments** (not attachable to any one claim) the
advice is to *"make up a pseudo patient, maybe even with the provider's name"*
and post to dummy claims there.

### Denied claims — a stated product limitation
> "The program is designed to completely skip any type of payment information
> from denied claims … right now you do not have the capability of applying a
> zero dollar payment from a claim that has a status of denied."

Denied adjustments are **tracked, never applied**. The distinction EZClaim
draws: `Processed as Primary` with $0 means *"we processed it and paid you
nothing"* (postable); `Denied` means *"we didn't even process the claim"*
(not postable). They acknowledged on camera that this is a pain point and that
payers code it inconsistently.

### Secondary billing — the exact rule ★
After posting, EZClaim changes `Bill To` and `Status` **from the 835's claim
status, not at random**:

| 835 claim status | `Bill To` | `Status` |
|---|---|---|
| `Processed as Primary` | → Secondary | → **`Ready to Submit`** |
| `Processed as Primary, Forwarded to additional payers` | → Secondary | **stays `Submitted`** |
| any, with no secondary on the claim | → **Patient** | |

It also sets **`Method`** to paper if the secondary doesn't accept electronic,
and writes the **`Original Reference Number`** onto the claim (needed for
secondary billing). *"We can only act on the data that's in the 835. If the
payer is not coding that right, there's nothing we can do."*

Also stated: the adjustment reason codes and payment data posted onto the claim
**are** the primary's EOB information that a secondary asks for — *"there's no
need to send the paper EOB because we're applying all that information to the
claim for you."*

### Corrected / replacement claims
Change the **resubmission code** dropdown on the claim, keep the original
reference number, set the status back to `Ready to Submit`. *"I urge you to
contact the payer and ask them how they want to receive that."*

### Finding tracked adjustments afterwards
`Find` → **`Find Adjustment`**. A tracked adjustment is recognisable by its
**$0.00 amount**, and there is a dedicated **`Track Only`** checkbox column.
The grid has the same right-click actions (`Create Tasks`, `Create Claim
Notes`), so you can filter by reason code and work them even if you forgot to
create tasks at posting time.

### The posting-options defaults, restated
All options are **global, not per-file**: *"whatever options you set on that
option screen applies to all, and not only this posting, but all future
postings as well."* The presenter's own setup: **everything `Track` except
`45`, which is `Apply`** — and a recommendation to also set **`A2`** to apply,
*"for some reason they seem to have two different codes to represent
contractual obligation."*

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

### Custom fields — `Patient Custom Fields` / `Claim Custom Fields` ★

(`ikUIM2AVURQ`) Two of those Options entries are user-defined columns, and
they matter more than their position in the list suggests.

- Each entity (patient, claim) gets a fixed set of typed slots. Until renamed
  they appear in the column chooser under their generic names —
  **`Custom Text Value`, `Custom Number Value`, `Custom Date Value`,
  `Custom Currency Value`, `Custom True / False Value`**.
- In Program Setup you **rename a slot and set its type**. The worked example
  renames a claim slot to **`Family Size`** and sets it to number.
- The renamed field then appears **in the column chooser under its new name,
  in alphabetical order**, and can be added to any grid, filtered, sorted and
  conditionally formatted like any other column. (Confirmed on screen: the
  `Customization` panel lists `Family Size` between `Facility` and
  `First Name`.)
- **Hard warning given, verbatim:** *"Those are for internal only — none of the
  custom fields export onto claims, either electronically or if you're printing
  paper claims."*

So EZClaim's answer to "we need to track something the form doesn't have" is a
handful of typed, renameable, grid-visible internal columns. That is a small
feature with a large footprint, and it is the reason a practice can run its
whole follow-up process inside the grids.

### Audit columns available on every grid (`ikUIM2AVURQ`)
`Created User` · `Created Timestamp` · `Modified User` · `Modified Timestamp`
— pulled from the **workstation's system clock**, and blank for records created
before user accounts were set up. Also on `Find Patient`: **`Last Seen`**
(pulls from EZClaim's **scheduling** program) and **`Last Date of Service`**
(from the patient record).

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

> **Note: there are two different web products called "portal", eight years
> apart, and they are not the same thing.** §9 below is
> **EZClaim Premier + Pay (2025)** — payer-facing, takes card payments, dark
> navy rail. §9o is the **EZClaim Portal (2017)** — provider-facing, read-only
> reporting, orange accents, built by a third party. Don't merge them.

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

The rule for which button: **FTP senders use `Get Reports`; non-FTP senders use
`Add Reports`** (`ctXeB-wct-A`).

### The `Type` column — EZClaim's own taxonomy (`ctXeB-wct-A`)
```
Claim Acknowledgement   the ANSI 277
Claim Status Data       TriZetto's .dat — human readable
Claim Status Report     TriZetto's .csr
ERA – ANSI 835          a remittance
Text Document           a 999, or anything unparsed
Daily Verification      a .rec
```
**Only ANSI files get the smart behaviour.** *"Premier will only analyse ANSI
EDI files; although you can view other types of reports such as text files,
only the ANSI files will have the capabilities that I discussed today."*

**TriZetto sends three versions of the 277 and you should only open one.**
The `.dat` is human-readable and the **`.csr` is an incomplete version — it
contains truncated text, meaning your rejection reasons are cut off**. The
instruction is explicit: open the **`Claim Acknowledgement` 277**, not the
`.csr` or `.dat`. (`ctXeB-wct-A`)

### The `Note` column is auto-written, and its two formats ★
EZClaim reads the file header on import and writes the note for you. You can
edit or delete it freely; `Save Notes` persists the edit and the tab title
shows **`EDI Reports… (UNSAVED)`** until you do. (`uEox7GQtBhI`)

- **For an 835:** `<payer> <amount> <trace number> <payment date>` —
  `MEDICARE $130.00 11111122222 03/25/2013`. Negative amounts appear in
  parentheses: `MEDICARE ($90.00) 11111133333 03/25/2013`.
- **For a 277:** a count — **`2 Claims, 1 Rejected`**, `4 Claims, 2 Rejected`.
- **For a 999:** `Accepted` or `Rejected`.

*"This is important because it sometimes makes it easy to go back and find an
835 based on the trace number or the dollar amount."* The demonstrated search
is `%111` in the `Note` filter cell — see the wildcard rule in §2.

### The extra columns are not on by default
`Payer`, `Pmt Amt`, `Date` (the check date), `Trace Number` and `Method` are
**added from the column chooser** — they are newer additions to this screen.
(`ctXeB-wct-A`)

### Archiving
`Archive` does **not** delete: *"it's just kind of putting them into a
different area so they don't clutter up your list."* Archived rows reappear
when ☑ `Show Archived` is ticked and carry an **`[ARCHIVED]` suffix in the
`Name`**. The advice is to archive every 835 once posted.

### New reports are bold and at the top; opened ones sink
*"The new reports will download in a bold font and be at the top of your list;
after you open a report it will move to the bottom of the report list."*
(`ctXeB-wct-A`)

### The preview pane's size limit
The lower pane quick-views the header only. **If the 835 is larger than 500 KB
you must double-click to see the full data** — *"the program doesn't want to
slow things down by loading up megabyte files."* (`uEox7GQtBhI`)

For an unparseable type the pane prints, verbatim:
```
Double click the report file to view the contents.

You cannot 'Quick View' this file type.

'Quick View' is only intended for non-ANSI, non-HTML, text-based reports.

'999Accepted.txt' has been found to contain data that may be ANSI-based.
```

---

## 9b2. Opening a 999 — EZClaim decodes the ANSI for you (`ctXeB-wct-A`)

Double-clicking a 999 opens a **document tab named after the file** containing
a pretty-printed decode, not the raw EDI. It is monospaced and sectioned:

```
Analyzing File: 999Accepted.txt

ISA Header Information
------------------------------------------------
ISA*00*          *00*          *27*PPPPPP        *27*XXXXXX     *100914*1025*^*00501*000000218*0*T*:
------------------------------------------------
Interchange Sender ID: PPPPPP
Interchange Receiver ID: XXXXXX
Interchange Date: 100914
Interchange Time: 1025
Interchange Control Number: 000000218
Usage Indicator: Test

GS Header Information
...
Transaction Set: 999

***** The following number matches the group control number sent with the claims *****
***** The submission report shows the group control number(s) used for the batch *****
Functional Group Control Number: 27

  Transaction Set Control Number: 000000001
  Transaction Set Acknowledgement Code: A - Accepted
Functional Group Acknowledgement Code: A - Accepted

Number of Transaction Sets Included: 1
Number of Received Transaction Sets: 1
Number of Accepted Transaction Sets: 1

------------------------------------------------
End of Output
EZClaim Premier Billing - Version 4.6.24705.01. Commit Hash: 4d1af962ca0fede10beb01d197367c2f90e92c97
```

The rejected variant swaps in `R - Rejected` and adds
`Transaction Set Syntax Error Code: 6 - Missing or Invalid Transaction Set
Identifier`, with `Number of Accepted Transaction Sets: 0`.

Two things worth taking from this:

1. **The decode is annotated for the reader**, not dumped — the `*****` lines
   tell you what the control number is *for*. That is a good model for what our
   scrubber output should look like.
2. **The footer is the real build identity.** `8.0.655` in the title bar is a
   marketing number; the assembly version is `4.6.24705.01` and it prints a
   **git commit hash**. Useful if we ever need to pin behaviour to a build.

**Do not confuse batch status with claim status** — repeated twice on camera:
> "Just because the batch was accepted does not mean that the claims were
> accepted. It just means that the batch was accepted — it's made it through
> the door and they're going to look at your claims."

---

## 9b3. Opening a 277 — the `Rejections` tab and `Claims Not Found`

### What happens on double-click (`ctXeB-wct-A`)
1. A short summary dialog: how many claims in the file were updated.
2. **Accepted claims get a note written silently** — *"if the claim was
   accepted for adjudication we really don't need to look at the claim, so we
   just add the accepted note behind the scenes."*
3. **If anything was rejected, a new document tab appears**, titled
   `Rejections - <report file name>` (title bar too).

### The `Rejections` tab
Grid columns, in order:
`Rejection Date` · `Report` · `Name` · `1st DOS` · `Bill Date` ·
`Total Charge` · `Total Balance` · `Bill To`, with a checkbox per row and a
**`+` expander**.

Footer: `Shown: 1. Checked: 0.`
Right-hand buttons: **`Check All`** (split, ▾) · **`Create Tasks`** · `Close`.

`Report` values seen: `Claim Acknowledgement`,
`RECORD OF CLAIMS RECE…` (from a `.csr`).

**Expanding a row** reveals a child grid with `Date` · `Note` · `Category` on a
**salmon/pink row**, holding the payer's own words. A real example, and this is
the wording the office reads every morning:
```
REJECTED - MEDICARE
Acknowledgement/Rejected for Invalid Information - The claim/encounter has invalid
information as specified in the Status details and has been rejected.
Returned to Entity. Note: This code requires use of an Entity Code.
Returned to Entity Acknowledgement/Returned as unprocessable claim-The claim/encounter
has been rejected and has not been entered into the adjudication system.
Entity acknowledges receipt of claim/encounter Acknowledgement/Acceptance into
adjudication system-The claim/encounter has been accepted into the adjudication system.
CTN=160412123456,Member Not Found.
11111E2222233344, Member Not Found.
```
The same text is written into the claim's notes grid **and** into the linked
task's note area, so it is visible from all three places.

Double-clicking anywhere on a rejection **opens the claim** to fix it. The
demonstrated loop: fix the insured ID, set status back to `Ready to Submit`,
save and close.

**`Create Tasks` is the point of the screen.** Check the rejections you can't
fix today, click `Create Tasks`, and a `Task(s) Created` dialog confirms
`1 task has been created.` The new task's subject is prefilled
**`Rejected Claim`**, it captures the patient name and claim date, and you can
choose to **use the rejection note as the task's note**.

### The `Claims Not Found` import dialog ★ (`ctXeB-wct-A`)
When a 277 references a claim EZClaim can't match, a modal opens titled with
the file name:
`'7890123456_Claim_Status_Report.csr' Import - Claims Not Found`

Grid columns: an inline **`Find`** button per row, then
`Status` · `Patient` · `First DOS` · `Last DOS` · `Charges` ·
`Claim Invoice #` · `Note`.
`Note` values: `ACCEPTED - Clearingh…`, `REJECTED - Clearingh…`.
Buttons: `OK` · `Cancel`.

Clicking **`Find`** opens `Find Claim` **pre-filtered by patient name and
date**; you widen the filter until the claim appears and select it, which
forces the connection. Causes given: a **name spelling mismatch** between your
data and the payer's, or claims that were sent from a previous program.

If you can't match it, closing is harmless — *"the only thing that's happening
is the status update isn't being imported on this one."*

**The practical advice, worth repeating to the office:** when the payer spells
a name differently (`Sarah` vs `Sara`), **change your data to match theirs**,
even if theirs is wrong. *"It will make your life a little bit easier."*

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

**Re-confirmed field for field at 8.0.596** (`tJsKQEAoRw4`) — this screen has
not changed across the build range, and `Dr. Smith / Billing` and
`DAVID DOCTOR / Supervising` join the entry list. One behaviour to add: this is
the screen that demonstrates EZClaim's **validation rules** (§1e). Saving an
incomplete entry pops **one missing-field message at a time** — *"why am I
missing a zip code"*, then on the next attempt *"I need a tax ID for this
field"* — rather than listing everything wrong at once. Whether that is good is
arguable; it is at least what the office is used to.

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

### The rest of the conditional-formatting submenu (`ikUIM2AVURQ`)

`Highlight Cell Rules → Custom Condition` is only the first entry. The submenu
also offers, Excel-style:

- **Colour scales** — a gradient across the column, so low balances shade
  differently from high ones.
- **Data bars** — an in-cell bar proportional to the value; the bar's extent is
  adjustable.
- **Icon sets.**
- **`Manage Rules`** — lists every rule on the grid with **up/down ordering,
  and higher rules supersede lower ones**. This is how you control which rule
  wins when two match.
- **`Clear Rules`.**

Two behaviours worth copying:

1. **A rule survives hiding the column it tests.** The worked example sets
   `[Pat. Unapplied Bal.] Is greater than $0.00 → Green Fill, entire row`, then
   **removes the `Pat. Unapplied Bal.` column from the grid** — the green rows
   stay. *"Now you just have a visual indicator that we have some unapplied
   money for these patients."* Colour becomes a way to surface a fact you don't
   have screen width to show as a column.
2. **It changes display only.** *"It's not changing or harming your data in any
   way — please feel free to play around with the filter editors and custom
   conditions."* Encouraging experimentation is part of how the product is
   taught.

Confirmed on screen at `8.0.600`: the dialog is exactly as documented above —
`Custom Condition` title bar, `Format cells that match the following
condition:`, an `And` node with a `＋`, the clause
`[Pat. Unapplied Bal.] Is greater than $0.00` with pencil and `⊗` icons, a
`with [Bold Text ▾]` dropdown, `☐ Apply formatting to an entire row`, and
`OK` / `Cancel`.

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

Seen again in `ikUIM2AVURQ` with its furniture clear: the panel is titled
**`Customization`**, has a **`Search for a column...`** box with a magnifier at
the top, and is a **scrollable alphabetical list** (`Diag. 5` … `Diag. 9`,
`Facility`, `Family Size`, `First Name`, `Ins Amt Paid`, `Insurance Balance`,
`Invoice #`). **Double-click an entry to add it**, or drag it — two white
arrows mark the drop point. Removing a column is the reverse: drag the header
out until a **black `X`** appears and drop. *"This doesn't delete your data —
removing a column is just hiding it from your view."*

### `Find Claim` grid, second column set (`ikUIM2AVURQ`)
`OPEN` · `Name` · `Active` (checkbox) · `Billing Physician` · `1st DOS` ·
`Total Charge` · `Total Balance` · `Primary Payer` · `Rendering Physician` ·
`Account #`

### `Find Adjustment` grid columns (`ikUIM2AVURQ`)
`OPEN` · `Patient Name` · `Code (Group Code)` · `Reason` · `Remark Codes` ·
`Adj Amount` · `Adj Date` · `Payer` · `Svc Date` · `Procedure Code` ·
`Svc Balance`

Confirmed at 8.0.581 (`uEox7GQtBhI`) with one addition: a **`Track Only`
checkbox column** sitting between `Remark Codes` and `Adj Amount`. That is how
you find tracked adjustments later — they are also recognisable by their
**$0.00 `Adj Amount`**, shown in parentheses when negative (`($1.00)`).

### `Find Payment` grid columns (`uEox7GQtBhI`)
**Two** inline button columns, not one: **`MODIFY`** and **`DISBURSE`**, then
`Name` · `Amount` · `Remaining Bal.` · `Pmt Date` · `Method` · `Ref #` ·
`Add'l Ref #` · `Note`. Footer `Shown: 3` with money totals under `Amount` and
`Remaining Bal.`

This is worth noting as an idiom: **EZClaim puts the verb in the row**, so a
grid is a launcher as well as a list. `OPEN`, `MODIFY`, `DISBURSE`, `Find`
(on the Claims Not Found dialog), `CHECK` / `VIEW` (eligibility on the patients
grid) are all the same pattern.

### `Find Task` grid columns (`ctXeB-wct-A`, 8.0.655)
`OPEN` · `Name` · `Payer` · `Subject` · `Start Date` · `Due Date` ·
`Priority` · `Status` · `% Complete`

Row right-click menu, in order:
`Copy` · `Select All` · `Open Task...` · `Mark as ▸` · `Set Priority to ▸` ·
`Assign to ▸` · `Remove Reminder` · `Delete Task...`

### The `Find` ribbon menu — full list at 8.0.581 (`uEox7GQtBhI`)
```
Find Patient
Find Claim
Find Service
Find Payment
Find Task
Find Adjustment
Find Payer
Find Physician
Find Disbursement
Find Claim Note
```
Ten grids. Note it is **`Find Service`**, not "Find Service Line" — the
`Find Service Line` title belongs to the 835 matching modal (§9d), which is a
different screen.

### `Find Claim` columns at 8.0.596 (`tJsKQEAoRw4`)
`OPEN` · `Name` · **`Created User`** · **`Modified User`** · `1st DOS` ·
`Claim Status` · `Bill Date` · `Total Charge` · `Total Balance` ·
`Insurance Balance` · `Patient Balance` · `Rendering Physician` ·
`Billing Physician` · `Claim ID`

The two user columns are the payoff of setting users up (§1d) — *"to know who
created the patient and who was the last to modify."*

### `Find Claim Note` is its own grid, and that answers an obvious question
Asked on camera whether claim notes can be a column on `Find Claim`, the answer
was no: *"we actually separate them out … if you want to search your notes or
see them, we actually have it as its own separate grid."* It has its own column
chooser and its own right-click actions, and notes added anywhere appear there
immediately. (`tJsKQEAoRw4`)

---

## 9j2. Bulk actions — the row right-click menu, per grid ★

(`ikUIM2AVURQ`) Distinct from the *column-header* menu above: **right-clicking
a row** gives actions, and **they differ by grid**. Select a range first —
*"click the top one, hold shift, click the bottom, then right-click and the
action applies in bulk."*

| Grid | Row right-click actions |
|---|---|
| `Find Patient` | Change status (Active / Inactive) · Create Tasks · Quick Reports |
| `Find Claim` | Set Claim Status · Write Off Selected Claims (posts an adjustment) · Pay Off Selected Claims (opens payment entry) · Create Task · Create Claim Notes · Quick Reports |
| `Find Service` | `Select All` · `Write Off Service Line(s)...` · `Create Claim Notes Linked to Selected Claim(s)...` · `Set Responsible Party ▸` |
| `Find Payment` | Change Payor Name · Modify Payment · Disburse Payment |
| `Find Task` | Mark Claim Progress · Change Priority · Change Assigned To · Remove Reminders · Delete Task |
| `Find Adjustment` | Write Off Service Line · Create Task · Create Claim Note · Delete Adjustments (bulk) |
| `Find Disbursement` | **none** — only `Copy Text` / `Select All` |
| `Find Claim Note` | Set Claim Status · Write Off · Pay Off · Quick Reports |

**Greying rules observed on `Find Payment`:** `Disburse` and `Modify` grey out
once a payment is **fully disbursed**; `Change Payor Name` greys out when the
payment is a **patient** payment rather than a payer payment.

**The `Find Claim` menu, captured verbatim at 8.0.596** (`tJsKQEAoRw4`) —
this is the exact wording and order:
```
Copy Text
Select All
Set Claim Status...          ▸  Ready to Submit
                                Submitted
                                On Hold
                                Other
Write Off Selected Claim(s)...
Pay Off Selected Claim(s)...        (greys out when nothing is payable)
Create Tasks Linked to Selected Claim(s)...
Create Claim Notes Linked to Selected Claim(s)...
Quick Reports...
```
Note the status submenu is the **complete** claim-status list — four values,
including the literal `Other`.

**What `Write Off Selected Claim(s)` actually does**, demonstrated: it opens a
small dialog where you choose an adjustment **reason code** — and *"you can
even create your own reason codes"*; the presenter typed `W` to jump to a
custom `WORD` write-off code — then posts an adjustment for the **full
remaining balance** on every selected claim, writes a
`Claim Balance Written Off` + `Adjustments Applied` pair into each claim's
notes, and flips `Bill To` to `Final (F/2) - Patient`. One right-click, forty
claims. (`tJsKQEAoRw4`)

**Creating claim notes in bulk is newer than the rest.** Described as *"one of
the other newer features that was entered in recently"*: select several claims,
right-click, type one note, `OK`, and it lands on all of them — *"extremely
efficient to be able to add notes to multiple claims at once."* Combined with
note templates (§3c) this is how an office logs "called payer 3/14, on file"
across a batch.

**Tasks can be created from almost anywhere**, not just the find grids:
right-click a patient in the left quick-access pane, right-click a claim, or
click `Task` on the `Claim` ribbon of an open claim. *"It's very easy to build
a comprehensive follow-up list for anything that you may have to do within the
program."* (`tJsKQEAoRw4`)

This is a real workflow, not a convenience: writing off forty stale claims is
select-all → right-click → write off, and it posts the adjustments for you.

### Per-user vs company-wide — the rule ★
Stated twice and explicitly:

- **Per user:** column layouts, added/removed columns, sorting, filters, saved
  layouts, conditional-formatting rules. *"If you wanted this done on all of
  your Premier workstations it would have to be done for every user."*
- **Company-file-wide:** **widgets.** *"Once you create a widget all of the
  other users will be able to see them."*

There is **no way to copy conditional-formatting rules between users** — the
vendor's own suggestion is *"take a screenshot of your rules and save them for
reference when you're building them for the next user."* Worth knowing: if we
build the equivalent, making rules shareable is a genuine improvement, not
just parity.

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

### What widgets are *for* (`ikUIM2AVURQ`)

Asked directly in the webinar Q&A, and the answer is design intent worth
copying:

- They are **a glimpse of your data**, and *"some people use them as work lists
  for the day."*
- **The goal is to drive each widget's count to zero.** *"Some of the main
  thought behind these widgets is that you really want to have their count
  down to one or zero."* A tile reading `7` on `Claims Over 120 Days` means
  seven claims to chase today — aging, timely-filing risk.
- Created from any filtered grid by **right-click → `Add as Widget`**: name,
  description, `# of Rows`, click action. Rows are unlimited but
  *"I would suggest putting in a limit if you have thousands — it does take
  quite a bit of processing power."*
- **Widgets are the one thing that is company-file-wide**, so one person builds
  the worklist and the whole office sees it. Everything else about a grid is
  per user.

### The tile column as it actually appears, by build

The left-hand tile column is scrollable and each tile is **an icon, a big
number and a truncated caption**; below the column sits `Updated 7:19 AM` and
a small refresh button. Clicking a tile loads its grid on the right under a
centred caption that is the widget's **full** name.

**8.0.655 (`ctXeB-wct-A`), in order:**
`Unpaid Patient Co-pays` 3 · `Expiring Auths` 1 · `Batch Status` 2 ·
`Rejected Claim from …` 0 · `Denied Claims from P…` 0 ·
`Claims Over 90 Days …` 6 · `Claims with a Credit …` 0 ·
`Overdue Statements` 0

**8.0.596 (`tJsKQEAoRw4`):** `Batch Status` · `Claims Over 120 Day…` ·
`Claims Over 90 Days …` · `Claims with a Credit …` ·
**`Claims wo Disb. 45-6…`** · plus a user-made **`Rendering Widget`**

**8.0.581 (`uEox7GQtBhI`):** `Claims Over 120 Day…` 7 ·
`Claims with a Credit …` 0 · **`Payments with Balan…`** 0 ·
**`Undisbursed Paymen…`** 0 · `Batch Status` 2

So the shipped set has drifted across builds, which is itself the point:
**the tile column is data, not chrome.**

### Detail-grid columns per tile (`ctXeB-wct-A`, `uEox7GQtBhI`, `tJsKQEAoRw4`)
| Tile | Grid columns |
|---|---|
| `Claims Over 120 Days (Max 50)` | `Name` · `Bill Date` · `Tot. Bal.` |
| `Claims Over 90 Days (Max 50)` | `Name` · `Bill Date` · `Tot. Bal.` |
| `Unpaid Patient Co-pays` | `Name` · `Service Date` · `Amount Due` · `Amount Paid` |
| `Batch Status` | `Exported Date / Time` · `File Name` · `Func. Group Number` · `Original Claim Count` · `Acknowledgement` |
| `Rejected Claim from Posted 277-CSR Reports` | `Name` · `Bill Date` · `Note Date` · `Most Recent Claim Note` |
| `Denied Claims from Posted 835 Files` | same four |
| a user-made claims widget | inherits the `Find Claim` column layout it was built from |

**`Batch Status` is the one to copy first.** It is a two-line answer to "did
this morning's batch go out and did the clearinghouse take it" —
`Acknowledgement` reads `Accepted` or `Rejected` per exported file, straight
off the 999. The presenter's words: *"I like to use this as kind of a pulse on
the practice, letting you know that batches are going out and being
accepted."* (`ctXeB-wct-A`)

**`Rejected Claim from …` is explicitly a backstop, not the workflow.**
*"I don't recommend using this as your end-all be-all for finding your rejected
claims … I highly recommend making use of the task system to make sure that you
are not letting any slip through the cracks, but this is a nice little
backup."* Working the task and resubmitting drops the claim off the tile.

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

## 9m2. Send Claims screen

Document tab `Send Claims`, reached from `Send Claims` on the Home flowchart
or the `Electronic Billing` ribbon. (`Q6ytCiouF4I`)

**Header row:**
- `Connection:` dropdown (`Clearinghouse`) with a `…` button
- `Submitter/Receiver:` dropdown (`CLEARINGHOUSE - ANSI 837 w/~`) with a `…`

**Grid columns:** checkbox · `Name` · `1st DOS` · `Tot. Chg.` · `Tot. Bal.` ·
`Billing` · `Billing NPI` · `Bill To Sequ…` · `Payer`
Footer: **`Shown: 2, Checked: 0, Charges Checked: $0.00`**

**Right-hand button column:**
`Check for Errors` (split, ▾) — **removed in release 616, see §9m** ·
**`Create and Send Batch`** · `Close` · `Check All` · `Uncheck All` ·
`Check Selected` · `Uncheck Selected` · **`Select Previous Batch`**

**Bottom right:** ☐ `Export as a Zip File`, then a radio group captioned
**`Claims that are:`** — ⦿ `Ready to Submit` / ○ `All Electronic` / ○ `All`.

### What makes a claim appear in the list — the rule (`Q6ytCiouF4I`)
**A claim shows up only when `Claim Status` = `Ready to Submit` *and*
`Method` = `Electronic`.** Change either and it drops off the list.
The `Claims that are:` radios widen this: `All Electronic` ignores status,
`All` ignores both. *"Under most circumstances this filter is set to Ready to
Submit."*

### Sending — the happy path
1. `Send Claims` → the list of claims ready to submit.
2. `Check All` (or select a subset — *"helpful if you want to batch your claims
   by provider or payer"*).
3. `Create and Send Batch`. (In older builds, `Check for Errors` first.)
4. **A green confirmation message** on successful upload.
5. You are offered a **printed/exported claims report** — `No` skips it.
6. **The status flips from `Ready to Submit` to `Submitted`, so the claims
   disappear from the list.**

### Connection Library
Document tab `Connection Library`, same two-pane library shape as the
Physician/Facility Library: an `Entry Name` list whose first row is
**`Add new entry…`** (then `Clearinghouse`), and a form with `Name:`
(placeholder *"Type entry name here…"*) and `Type:` (`None selected`).
Buttons: `Save & New` · `Save & Close` · `Close` · `Delete` ·
**`Test Connection`**.

---

## 9m3. Claim status messages and the rejected-claims workflow

(`JX5Esi1Vzp0`) This is the loop the office actually lives in, and it is worth
copying wholesale.

A clearinghouse 277 / 277CA report arrives as **two files** in `EDI Reports`:
- a **`.dat`** — *"the human readable version"*, `Type` = `Claim Status Report`.
  Double-click to view; **printing switches to landscape**.
- a **`.csr`** — the machine version *"used by the program to attach messages
  to the claim history."*

**Double-clicking the `.csr` posts the messages onto each claim's history.**
A confirmation shows how many claims the file contained. If any were rejected,
**a window opens listing the rejected claims** — this is where the workflow
starts.

- Click the **`＋`** at the left of a row to drill into the claim history —
  which merges notes from **EZClaim, the clearinghouse and potentially the
  payer**.
- **The posted messages stay permanently in the claim note area.**
- Few claims → double-click and fix them here.
- Many claims, or later → tick them and click **`Create Tasks`** (see §9g).
  *"The advantage of using tasks is they can be assigned to other users, have
  due dates, show popup reminders."*
- Then: open the claim from the task, review the status notes, fix it,
  **mark it `Ready to Submit`**, mark the task complete, next.

### EDI Reports grid — `Type` and extra columns (`JX5Esi1Vzp0`)
`Type` values seen: `Claim Status Report`, `ERA - ANSI 835`, `Text Document`,
`Daily Verification`. This capture also shows a **`Size`** column (`2.33 KB`)
and adds an **`Un-Archive`** button under `Apply to Checked`.

Hint text in the preview pane when a file can't be previewed:
```
Double click the report file to view the contents.
You cannot 'Quick View' this file type.
'Quick View' is only intended for non-ANSI, non-HTML, text-based reports.
```

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

Confirmed and extended by `ikUIM2AVURQ`: they render as a **row of buttons
along the bottom-left of the grid, below the footer** — a single button reading
`KR Claims` (named for the rendering provider's initials) sits under the
`Find Claim` grid. **Unlimited buttons**, and *"they are dynamic — real time —
so when more claims are added that fit the criteria they will display."*
**Right-click a saved-layout button to move, update or rename it.** An **`✕` in
the upper-left of the filter row clears all filters** and returns the grid to
full at any time.

Seen again at 8.0.596 with two buttons under `Find Claim` — **`Brooks claims`**
and **`On Hold Claims`** (`tJsKQEAoRw4`) — which is exactly the two use cases
EZClaim names for them: *"say you were working on claims for a certain patient
… or if you are just looking to check your on hold claims quickly."*

The same video restates the per-user rule in plain terms, and it is the
argument for making ours shareable: *"while I'm logged in as Jamie and I have
mine set up in a certain specific way, if somebody else were to come into the
office and log in as Sandy, they could have their grid set up in a completely
different way. It is user specific."*

**The `%` wildcard, confirmed a third time** (`uEox7GQtBhI`): typing `%111`
into a filter cell means *contains* rather than *starts with* —
*"the percent sign is a wildcard character … that's actually just a good
technique on any of the find grids."* It is used on the EDI Reports `Note`
column to find an 835 by trace number, and on patient first names.

This is the feature to steal wholesale. A saved layout is a named, live,
one-click work queue built by the user out of filters they already understand —
no query language, no admin, no report builder. It is how an EZClaim user makes
their morning worklist.

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

## 9o. The *other* web portal — EZClaim Portal (2017, `D5CVTNTdCHw`) ★

Dated **June 28th, 2017**, hosted by Andy Henry. This is a **read-only,
provider-facing reporting portal** at `https://portal.ezclaim.com`, sold at
**$10 per user per month**. Its purpose, in the billing-service webinar's
words: *"give providers access to some reports without giving them complete
access to your Premier program. They will only be able to see what you want
them to."* (`tJsKQEAoRw4`)

The page footer reads `2017 © Copyright by CIM Consulting, L.L.C.`
**That is not a third party — it is EZClaim's own legal entity.** The Premier
installer's licence agreement (`XBFxco5x5Ek`) says
`Copyright (C) 1997-2015 CIM Consulting, L.L.C.` and describes the EULA as
*"a legally binding contract between you (the licensee) and CIM Consulting,
L.L.C."* So EZClaim is the product name and CIM Consulting is the company,
going back to 1997.

### Chrome
White, flat, Bootstrap-era; `EZclaim | Portal` logo top-left with the word
`Portal` in orange; a **thin orange bar** under the header; grey footer.
Top-right: `Logged in as: support@ezclaim.com  Logout`, and beneath it
**`Connected to: EZClaim_TestDatabase22 ▾`** — a company-file picker, so the
portal sits on top of the same multi-database model as the desktop (§1c).

**Nav bar, left to right:**
`Patients` · `Widgets` · `Reports` · `Dashboards` · `Manage Users` ·
`Manage Group Permissions` · `Log`

### `Patients` page
Split screen: list left, **report viewer right**. The list is a card captioned
`Patients` with a gear icon, and a table whose **first column is a per-row
report launcher** — a dropdown (`Claim List`) above a **`Show`** button on each
row. Then `Patient Name` · `Account #` · `Classification` ·
`Primary Insured's ID #` · `Primary Payer` · `Pat Bal`.

**The filter row under the headers is there too** — the desktop grid idiom
carried onto the web, which is the right instinct.

Pager at the bottom: `Page 1 of 1 (8 items)`, numbered buttons,
`Page size: 20`.

The right pane starts with placeholder text **`Click 'Show' button to view
report`**, then renders the report with a toolbar: search, print, export
icons, `Page 1 of 1` navigation, and an **export-format dropdown defaulting to
`PDF`**.

### `Reports` page
A left sidebar captioned `Reports` listing every report by name (the inventory
in §10), a middle **`Preview <Report> Report`** criteria panel that is a
faithful copy of the desktop's, and the same viewer on the right.

**The criteria panel is the desktop's, label for label** — `General`
(`Group By`, `Show Service Line Detail`), `Dates` (`Original Bill Date`,
`Claim Paid Date`, `Claim Created Date`, `1st DOS`, `Last Exported Date`,
`Last Printed Date`), `Claim` (`Claim Bill To Payer`, `Bill To Sequence`,
`Claim Primary Payer`, `Claim Rendering Provider`, …), all defaulting to `All`
/ `No Start Date` / `No End Date`. **One report engine, two front ends.**

### `Manage Users`
Page heading `Manage Users - All Company Files`. Two buttons stacked in the
first column: **`New User`** and **`New Manager`** — so there are two user
kinds. Columns:
`Email` · `Phone Number` · `User Type` · `Note` · `Confirmed` · `Disabled` ·
`Disabled Message` · `Company Permissions and Associated Groups` · `Delete`,
with a filter row. Empty state: **`No data to display`**.

**`Create New User` form:**
`Email:*` · `Confirm Email:*` · `Phone Number:*` · **`NPI:*`** ·
`Account Note:` (placeholder **`Not visible to client`**), then
**`Company Permissions:`** — one checkbox **per company file**, each with a
group dropdown beside it (`EZClaim_TestDatabase22` ☑ `testing`; `EZClaim1` ☐
`No groups available for con…`; `EZClaimTestDB3` ☐ `Default`).
Buttons `Add` / `Cancel`.

**`NPI` is a required field on a portal user** — because a portal user *is* a
provider, and access is scoped per company file. That is a clean model and it
is the one a family billing operation would actually need if Dad's providers
ever wanted to look at their own numbers.

### `Manage Group Permissions`
Grid: `New` · `Name` · `Notes` · `Users in Group` · `Delete`, with an `Edit`
button per row. `Edit` opens a modal **`Group Properties`** with four tabs:

`General` · **`Patient Reports`** · `Widgets` · `Reports`

The `Patient Reports` tab is a captioned checkbox list
(`Permitted Patient Reports:`) with **`Select None` / `Select All`** buttons
and `Save` / `Cancel`. So permissions are **per report, per group** — and the
same shape repeats for widgets and for the general reports.

### The pitch slides
`Portal Benefits`: *Reduce Delays in Communication · Visibility for Providers ·
Low-Price Tag, only $10/month per user.*
`Features Overview`: *Patient Information (Name, DOB, Primary Payer, Account #,
Balance and more!) · Run Reports (**Admins can limit which reports users can
see**) · Widgets · NEW Feature: **Dashboards** — graphically view data through
charts and graphs.*
Contact: `877-650-0904` / `sales@ezclaim.com`.

**Why this matters to us more than the 2025 Pay portal:** it is the exact shape
of the thing Blayne will eventually want — a *read-only, permissioned, per-user
view onto the billing data for someone who is not the biller* — and EZClaim
priced it at $10/user/month and shipped it as a bolt-on rather than building it
into the program. Our claims web screen on :8770 is already a web front end
onto the same data; the missing pieces are groups, per-report permissions and
a user who is not `blayne`.

---

## 10. Reports screen ★

The `Reports` tab is the **third of the four left-hand grid tabs**. Selecting
it replaces the record grid with a **report list**, and puts a
**`Report Criteria`** panel underneath. (`5mj4eSiGSv0`)

### Report list — exact names, in the order shown
```
Accounts Receivable
Adjustments
Authorizations
Claim List
Disbursements
Patient Demographics
Patient Ledger
Patient List
Patient Notes
Patient Services
Payment List
Procedure Code Summary
Production Summary
```
(scrolls further). Each row has **two small icons at the left** (run / preview
variants). Column header is just `Report Name`.

**Below the list, a one-line description of the selected report**, e.g.
`AR report showing the outstanding balances to` (Accounts Receivable) or
`Shows patient name, invoice #, primary` (Claim List).

The overview video (`_UZktuXNBxc`) also names `Carrier Mail Labels` and
`EZClaim Receipt`, and spells Disbursements as `Dispursments` on its slide —
the in-program spelling is **`Disbursements`**.

### The rest of the list — **it is not thirteen reports** (`tJsKQEAoRw4`)
Scrolling to the bottom at 8.0.596 shows the tail of the same alphabetical
list, and it adds **eight more**:
```
Patient Receipt
Patient Services
Payment List
Procedure Code Summary
Production Summary
Refund List
Statement History
Transaction List
Transaction List with Disbursements
User Claim Activity
User Patient Activity
```
So the new names are **`Patient Receipt`**, **`Refund List`**,
**`Statement History`**, **`Transaction List`**,
**`Transaction List with Disbursements`**, **`User Claim Activity`**,
**`User Patient Activity`**, plus **`Insurance Follow-Up`** (named in the same
video's Q&A). Call it **twenty-plus**, not thirteen, and correct that wherever
we have quoted the smaller number.

**The description strip carries a creation date**, which implies reports are
data rather than code: selecting `User Patient Activity` shows
`Shows the username and number of patients they have worked on. Also shows
patient note detail.  Created 9/28/2016`.

### What EZClaim's own staff recommend for A/R — and against ★
Asked how to run an A/R report, the answer was notably against their own
built-in one (`tJsKQEAoRw4`):

> "Although we do have a defined A/R report, accounts receivable, it's not what
> I would recommend using. I would actually use our **Claim List** — it's a
> simpler, more straightforward list. You can choose specific criteria … say if
> you just wanted to see claims that have a minimum balance of $1 … you have
> totals at the bottom and these can be sub-grouped and divided out in many
> different ways."

And for chasing payers specifically: **`Insurance Follow-Up`** — *"this will
show you what's outstanding and is useful if you're doing claim follow-up."*
It prints **landscape**, and shows patient date of birth, insured ID, codes and
the **aging of the balance**.

Worth carrying into our own design: the report that ships with the obvious name
is not the one the vendor's own trainers use. If we build one A/R view, build
the **filtered claim list with totals**, not the classic aging report.

### The full report inventory — **it is thirty-plus, and some are per-customer** ★

The EZClaim Portal's `Reports` page (`D5CVTNTdCHw`) lists the same reports in a
single scrolling column, which is the most complete inventory in any capture:
```
Accounts Receivable
Accounts Receivable including Zero Balances
Accounts Receivable with Balances (No Credits)
Adjustments
Appointment List
Appointment Status Summary
AR Lovaas Institute
Authorizations
Claim List
Claim Notes
Claim Statement
Claim Statement - No Ins or Adj
Daily Schedule by Resource
Deleted Records
Delivery Ticket
Deposit Slip
Deposit Slip - Disbursements
Diagnosis Code Usage Count
Disbursements
Insurance Followup
Patient Address List
Patient Balances
Patient Demographics
Patient Followup
Patient ICD-9 to ICD-10 Worksheet
Patient Insurance ID List
Patient Ledger
Patient Ledger - Elite Radiology
Patient Ledger - Enils
Patient List
Patient Mailing Labels
Patient Notes
Patient Receipt
Patient Services
Payment List
Procedure Code Summary
Production Summary
Receipt
Refund List
Statement History
Transaction List
Transaction List with Disbursements
User Claim Activity
User Patient Activity
```
(still scrolling past `Receipt`, so this is a floor, not a ceiling —
`-vHuSb1e9iU` and `TDIWTgfUJ2g` supply the entries the portal list cuts off.)

**Three of these are named after customers** — `AR Lovaas Institute`,
`Patient Ledger - Elite Radiology`, `Patient Ledger - Enils`. Combined with the
`Created 9/28/2016` / `Updated 08/17/2018` dates in the description strip, the
conclusion is firm: **reports are a data layer EZClaim adds to per site, not
compiled features.** Anyone can get a bespoke report by asking.

Where we quote "thirteen reports" in the gaps list below, that number came from
one visible screenful and is wrong. **The real gap is bigger and the real
lesson is different**: what we need is not thirteen reports but *a report
engine plus a criteria panel*, so that the next request is a definition rather
than a release.

### `Download Reports` — reports are literally downloaded content ★ (`Iv8z-duJ_OI`)

This settles it. `Support` ribbon → **`Updates`** group → **`Download Reports`**
opens a document tab that is a **store of reports fetched from EZClaim over the
internet**. (Captured at 8.0.460, Aero blue.)

Grid columns: checkbox · `Name` · a status column (`Existing` / `Updated`,
and `New` by implication) · `Description` · **`Released`** (a date).

Right-hand buttons: **`Download Checked Reports`** · `Close` ·
**`Check New and Updated`** (split, ▾) · `Uncheck All` · `Check Selected` ·
`Uncheck Selected`.

**The panel's own help text, verbatim — worth copying the honesty:**
```
Reports that aren't already installed on your system are listed in bold.
Downloading a report that you already have installed will restore that
report to its default settings and layout.
```
Confirmation dialog: **`7 report(s) downloaded.`** After downloading, the row's
status flips from `Updated` to `Existing` and the bold goes away.

Descriptions here match the ones in the report list exactly, `Updated <date>`
suffix and all — e.g.
`AR report showing the outstanding balances to patients and payers as of the
given aging date.  Updated 4/7/2014`. One more report name surfaces:
**`Nelco Forms`** (`This is a standard patient statement. Updated 1/10/2014`).

**So the model is:** the program ships with a report *engine* and a criteria
panel; individual reports are versioned, dated, downloadable definitions that
a site installs, updates, and can have customised for them. **That is the
architecture to copy** — not a folder of thirty hard-coded report functions.

### Reports are navigable — **drill-down** ★ (`-vHuSb1e9iU`)
The report preview is not a picture. **Clicking a row in the rendered report
opens the underlying record as a document tab**, stacking alongside whatever
else is open:
- clicking a patient line opens the **patient** tab (`Doedoe, Johnny (Age: 21)`)
- clicking a claim line opens the **claim** tab (`IVY, ABIGAIL - 09/13/2018`)

So the A/R report *is* the worklist — you read it and click straight through to
fix things, without going back to a find grid. Cheap for us (our report rows
already know their record id) and it removes the most annoying part of paper
reports.

Each report row in the list carries **two small icons**: the second one's
tooltip is **`Preview`**.

### The printed report layout, in detail (`-vHuSb1e9iU`, `D5CVTNTdCHw`)
Top of page: report name left in large type, **practice address block right**
(`Community Counseling / 555 Main Street, Suite 100 / Anytown, MI 55555`).

Then a **criteria echo line in small type**, so the paper says how it was
filtered:
```
Group By: Claim Billing Provider, Show Service Line Detail: Checked
Group By: None, 1st DOS: This Month, 1st DOS: 06/01/2017 00:00:00, 1st DOS: 06/30/2017 00:00:00
```
**Copy this.** A printed report that doesn't say what it filtered on is a
support call waiting to happen.

`Claim List` column band:
`Name` · `Inv # or ID` · `Diag` · `1st DOS` · `Bill Date` · `$0 Bal Dt`
(or `Paid Date`) · `Charges` · `Pat Disb` · `Ins Disb` · `Adjs` · `Balance`

**Three nesting levels, by indentation and weight**, when grouped and detailed:
```
Acme Treatment Services                        605.00  .00  .00  .00   605.00   ← group, bold
  Doedoe, Johnny                               500.00  .00  .00  .00   500.00   ← patient
  94   F1120  06/01/17  08/06/19               500.00  .00  .00  .00   500.00   ← claim, bold
       06/01/17  90837  AJ  1                  125.00  .00  .00  .00   125.00   ← service line
```
Money is right-aligned and printed **without a `$`** inside the table (`605.00`,
`.00`) — the currency symbol appears only in headers and the address block.
A leading zero is dropped: zero is `.00`, not `0.00`.

Last row is **`Grand Totals`**, and it carries counts as well as money:
`Grand Totals    Claim Count: 4    Units: 20    1,000.00  .00  .00  .00  1,000.00`

### Relative date ranges in the criteria panel (`D5CVTNTdCHw`)
Date filters are not only `All` / start / end. The first dropdown offers named
ranges — **`This Month`** was selected and auto-filled `6/1/2017` and
`6/30/2017` into the two boxes below, with an **`✕` to clear back to `All`**.
So the criteria panel has both relative and absolute dates, and the relative
choice resolves to concrete dates you can then edit.

### `Report Criteria` panel
A label/value grid with collapsible sections (`▲`), every value a dropdown
defaulting to **`All`**, or a date dropdown defaulting to
`No Start Date` / `No End Date`.

**Accounts Receivable criteria** (`5mj4eSiGSv0`):
- `General`: `Aging as of Date` (`06/12/2014`), `Group By` (`None`),
  ☐ `Calculate Aging by DOS`, ☐ `Hide Detail`
- `Claim`: `Claim Primary Payer`, `Claim Rendering Provider`, `Claim Status`
- `Patient`: `Patient Classification`, `Patient` (with a picker and `✕`)

**Claim List criteria**: `General`: `Group By` (`None`),
☐ `Show Service Line Detail`; `Dates`: `Original Bill Date`,
`Claim Paid Date`, `Claim Created Date`, `1st DOS` — each with `Start` / `End`
rows; `Claim`: `Claim Bill To Payer`, `Bill To Sequence`,
`Claim Primary Payer`, `Claim Rendering Provider`, `Claim Billing Provider`,
`Invoice # Starts With`, `Claim Minimum Balance`, … (full list in §9l)

**Multi-select payer dropdown**: `Claim Bill To Payer` opens a **checkbox
list** headed `(Select All)`, then `BLUE CROSS`, `HUMANA`,
`INSTITUTIONAL PAYER`, `MEDICAID`, `MEDICARE`, `VALUE OPTIONS`, with
`OK` / `Cancel`.

### Report output
Opens as **its own document tab named after the report** (several `Claim List`
tabs can be open at once), containing an embedded preview with a menu bar
(`File`, `View`, `Background`), a toolbar, and a zoom box (`100%`), footer
`Page 1 of 1`.

**Printed `Claim List` layout:**
- Title `Claim List` top-left; **practice name and address top-right**
  (`Community Counseling / 555 Main Street, Suite 100 / Anytown, MI 55555`)
- A line echoing the criteria:
  `Group By: None, Show Service Line Detail: Unchecked`
- Column headings:
  `Name` · `Inv # or ID` · `Diag` · `1st DOS` · `Bill Date` · `Paid Date` ·
  `Charges` · `Pat Disb` · `Ins Disb` · `Adjs` · `Balance`
- Rows are **grouped under the patient name**, with the patient's totals on
  the name line and each claim indented beneath (invoice number in the first
  column). With `Show Service Line Detail` checked, service lines indent a
  further level showing DOS, procedure and units.
- With `Group By: Claim Rendering Provider`, provider names become the
  outer group headers (`RENDERING NOT SELECTED`, `EDWARD MATTHEWS`) with
  their own subtotals.
- Ends with a **`Grand Totals`** line.
- Money is printed **without dollar signs**, zero as `.00`.

### Support ribbon (`5mj4eSiGSv0`)
Groups and buttons: `Support` → `Help Topics`; `Updates` →
**`Download Reports`**; `License` → `Register Software`; `About` →
`About EZClaim Billing`.
(The widgets video also mentions a **`Download Widgets`** button on this
ribbon.)

---

## 11. Old vs new — which look is current

The videos span roughly 2013–2025 and **the chrome changed once**, so it is
worth knowing which screenshots to copy.

| | **Older (≈8.0.46x–8.0.47x)** | **Current (≈8.0.65x–8.0.67x)** |
|---|---|---|
| Seen in | `5mj4eSiGSv0`, `7Sl9bwm3CxU` | `oZBevrOFRwY`, `gO7UQeKlmFM`, `puSJeow-pkk`, `DZ0spaFoFz4`, `h-EzAeOTDlQ` |
| Window chrome | **Aero blue** gradient title bar, glassy | **Caramel** tan/orange, flat |
| Ribbon | Larger icons, more padding | Tighter, smaller icons |
| Alerts group | `EDI Reports`, **`Messages`**, `Review Incoming` | `EDI Reports (n NEW)` ▾, `Reminders`, `Review Incoming (n Files)` |
| Support group | `Help Topics`, `EZView` | `Help Topics`, **`Ticket`** (newest) |
| Home flowchart | includes a **`Coding Advisor`** box | no `Coding Advisor` |
| Home widgets | two side-by-side panels with a `SHOW WIDGET` dropdown ("classic view") | a **column of tiles** + detail grid ("tile view") |
| Payment Entry right rail | filter checkboxes laid out loose (`Ignore Responsible Party`, `Match By Payer ID`, `Include $0.00 Balance Service Lines From DOS:` + date) | collapsed into a **`Filter Settings`** button with the state summarised as text |
| Payment Entry adjustments | `Adjustment 1` only | `Adjustment 1` **and** `Adjustment 2` |
| Send Claims | had a **`Check for Errors`** button | **removed in release 616** — checking is automatic on `Create and Send Batch` (`sTZilSPX-Fc`) |

### There is an older *product*, not just an older build: **EZClaim Advanced 10** ★

`TDIWTgfUJ2g` is a side-by-side sales comparison, and it is the only capture of
**EZClaim Advanced 10 Release 11** — a separate, cheaper product, not an early
Premier. Knowing what it looks like matters because **some small offices are
still on it**, and if the family business ever worked with one, this is the
look they would describe.

**Chrome:** classic Win32. A **menu bar**
(`File · Edit · Patient · Claim · Libraries · Tools · Electronic Claims! ·
View · Support/Help · EZClaim.com!`) over a **large-icon toolbar with text
labels**: `New Patient`, `Patient Template`, `Find Patient`, `Find Claim`,
`New Claim`, `Electronic Claims`, `Payer Library`, `Physician Library`,
`Report List`, `Backup Data`, `Exit Program`. **No ribbon, no document tabs.**

Title bar names the record, not the screen:
`SAMPLE, PATIENT (Age: 12) - 10134 - Dr. Doctor - EZClaim Advanced 10 Release 11`

**Layout:** patient list top-left with a `Group: All Groups` dropdown; a
tabbed detail panel top-right; a claims grid across the bottom with a
**filter strip of checkboxes** —
`Filters - Only Show Claims:` ☑`Not Printed` ☑`Not Exported` ☑`Not Permanent`
☑`Not Paid` ☑`Not Archived`.

**Instead of document tabs it uses a tab strip of claims**: `Patient/Insured
Info`, `Physician/Diagnostic Info`, `Payers/Other Info`, `New Charges`, then
**one tab per existing claim labelled by date and amount** (`10/22/2019
$200.00`, `5/28/2019 $74.00`…) with ◀ ▶ scroll arrows. Cramped, but note the
idea: the claim history *is* the navigation.

**Security is three shared passwords, and that is the whole point of the
video.** A `Security` tab captioned `Program Access Security` with
`Admin Password` / `User Password` / `Read Only Password` and confirmations.
Its own warning text:
> "IMPORTANT: If the password is lost or forgotten, there will be a charge to
> reset the password."
> "If all of the passwords are left blank, the program WILL NOT ask for a
> password at start up."

The video overlays the caption **"No User Tracking"** across it — which is
exactly the gap Premier's `User Management` (§1d) fills.

**Other Advanced-only details worth recording**, since several are things
Premier hides in Program Setup:
- `Payers/Other Info` tab has two orange panels with
  `Click to Select Primary Payer` / `Click to Select Secondary Payer` and
  `Clear Primary` / `Clear Secondary`, plus `Primary Claim Filing Ind:` (`BL`),
  `Responsibility Sequence:`, `Patient Relationship to Other Insured`
  (`Self / Spouse / Child / Other`).
- Sub-tabs `EDI Notes`, `Optional Billing Data`, `Misc Patient Data`,
  `Provider ID Numbers`, `Indicators`, `Print Options`, `Contact Info`.
- **`Print Options` per patient** (Premier moves this to Program Setup):
  ☐`If any dollar amount is zero, leave blank (don't print zeros).`
  ☐`If the Amount Paid (Box 29) is zero, leave blank`
  ☐`Summarize Service Line Items`, plus
  `Box 24A (Date's of Service) Format: MM DD YY`,
  `General Date Format: MM DD YYYY`, `Currency Format: DD CC`.
- ☐`Lock Record` and ☑`Patient Is Active` — **the ancestors of Premier's
  `Locked` / `Active`**, and here `Lock Record` is plainly a per-record flag.
- `New Charges` service grid columns: `From` · `To` · `Place` · `EMG` ·
  `Procedure Code` · `Modifiers` · `Diagnosis Pointer` · `Charge` ·
  `Applied Amt` · `Units` · `EPSDT Qual` · `Print/Export` · `Rend Prov ID` ·
  `CMN`, each row with its own `Del` button, footer `Line Count 3`.
- Right rail: `Print 1500` · `Preview` · `Notes` · `Reports` ·
  `View Extra Fields` · **`Scrub Setup`** · **`Scrub Claim`** · `Ambulance` ·
  `Chiropractic` · `Attach CMN` · `Claim Status`.
  **`Scrub` is older than Premier** — and `Scrub Setup` sitting beside
  `Scrub Claim` says the scrubber was configurable from the start.
- Payment entry is a modal, **`Line Item Payments and Adjustments`**, with
  `Patient Amount Due`, `Allowed/Approved Amt`, an adjustment row
  (type dropdown `Contract Adj`, amount, date, `Ref 2/Deposit #`,
  `Reason Code`, `Payment Note`, `Add`), a grid
  `Del · Payment Type · Amount · Date · Reference 1 · Ref 2/Deposit # ·
  Reason Code · Payment Note`, a per-line summary
  (`$200.00 Service Charge On 10/22/2019` / `$175.00 Applied Amount` /
  `$25.00 Balance - Responsible Party: 2 Secondary Insurance`), and the
  navigation button **`Goto Next Service Line`**. Hint text:
  `Double click a payment line item to edit.`

**The through-line:** `Scrub`, per-service-line payment application,
responsible-party sequencing and the `Locked` flag are all present in Advanced
10. They are not Premier inventions — they are **the vocabulary of this corner
of the industry**, which is more reason to adopt the words rather than invent
our own.

### Install, licensing and the second app (`XBFxco5x5Ek`, dated 3/4/2016)

Worth recording because two of these explain things seen elsewhere.

- Delivered as `EZClaim_Premier_Trial_Installer.exe`, a **free 30-day trial**
  downloaded from `ezclaim.com`. The download page in 2016 offered **two
  products side by side** — `EZClaim Premier` **OR** `Advanced 10 Medical
  Billing` — confirming Advanced was still sold, not retired.
- **InstallAware Wizard.** The step that matters is **`Company Name`**:
  > Enter the company name (letters, numbers, and underscore characters only):

  default `Demo_Company`. **This is where `Demo_Company_Jaime_B` in every title
  bar comes from** — the company file is named at install and the charset is
  restricted, which is why every capture shows underscores.
- Finish step has ☑ `Run EZClaim Premier now`.
- **Two desktop icons are installed: `Billing` and `Scheduling`.** EZClaim
  ships a **separate scheduling application**, which is what the
  `Appointment List`, `Appointment Status Summary` and
  `Daily Schedule by Resource` reports belong to. Nothing in any of the 46
  videos shows the Scheduling app itself.
- **`Register Software`** dialog (`Support` ribbon → `License`):
  `Registration Number` · `Key Code` · **`Concurrent Billing Users`** (`1`) ·
  **`Concurrent Scheduling Users`** · `License` (dropdown) · `Software`… ,
  a green **`Registered`** badge, and buttons `Renew via Internet` ·
  `Renew via Phone` · `Cancel` · `Save & Close`. Success message:
  `Valid registration details retrieved.`

  **Licensing is by concurrent users, counted separately for Billing and
  Scheduling** — which is the commercial reason `Manage Security Settings`
  exists and why `Require User Authentication` is off by default.

### The build range is wider than "old and new" — a timeline ★

The skipped videos filled in the middle of the range, and they change the
picture: **the Aero-blue → caramel change is early, and the other differences
are spread out.** Builds now seen on screen, in order:

| Build | Seen in | What it tells us |
|---|---|---|
| *(Advanced 10 Rel. 11)* | `TDIWTgfUJ2g` | a different product entirely — menus + toolbar, no ribbon, three shared passwords |
| 8.0.460 | `Iv8z-duJ_OI` | Aero blue; Home uses the **classic two-panel widget view** with a `SHOW` dropdown; `Support` ribbon has `Download Reports` |
| 8.0.46x–47x | `5mj4eSiGSv0`, `7Sl9bwm3CxU` | Aero blue chrome, `Coding Advisor`, `Messages` in Alerts |
| **8.0.553** (3/2016) | `Uu2b0eS6iQo` | **caramel already**, tile widget view, `Coding Advisor`; Alerts reads a plain `EDI Reports` with **no `(n NEW)` count**; flowchart says `Patient Statement` singular |
| **8.0.581** | `uEox7GQtBhI` | **already caramel**, still has `Coding Advisor`, `EZView`, no `Ticket` |
| **8.0.596** | `tJsKQEAoRw4` | caramel, `Coding Advisor`, adds `ICD Indicator` to the claim, `Database Maintenance` on the Tools ribbon |
| 8.0.600 | `ikUIM2AVURQ` | caramel; grid behaviour identical to the newest |
| **8.0.655/656** | `ctXeB-wct-A`, `TDIWTgfUJ2g` | **`Coding Advisor` is gone** from the Home flowchart; still `EZView`, no `MerchantTrack`/`EZClaimPay`; claim service grid gains `Sort` and `SrvID` columns |
| 8.0.664–670 | `Y_glBgEkSHs`, `oZBevrOFRwY`, `gO7UQeKlmFM` | `Ticket`, `MerchantTrack`, `EZClaimPay`, `Pending Data`, `BillFlash ePay` |

So, correcting the table above:

- **Caramel chrome is not "the new look"** — it was already in place by
  **8.0.553 in March 2016**, and the Aero-blue captures (8.0.460) are much
  older than the release numbers suggested. The changeover sits between
  **8.0.47x and 8.0.553**.
- **The alert counts baked into button labels (`EDI Reports (3 NEW)`) arrived
  after 8.0.553** — at 553 the button is just `EDI Reports`, though
  `Review Incoming (6 Files)` already carries its count.
- **The widget tile view replaced the classic two-panel view between 8.0.460
  and 8.0.553**, and the classic view survives as a Program Setup option
  (§11 below).
- **`Coding Advisor` disappeared between 8.0.596 and 8.0.655**, not at the
  chrome change.
- **`EZClaimPay` / `MerchantTrack` / `BillFlash ePay` are the genuinely recent
  additions** — absent at 655, present at 668. They are the payments business,
  not the billing program, which is why they matter least to us.
- `Database Maintenance` sat on the Tools ribbon at 8.0.596 and is not in the
  later captures.

**The stable parts across the whole 8.0.46x–8.0.670 range** are the ones worth
copying with confidence: the grid behaviour, the claim screen layout, the
`Apply/Track/Ignore` 835 vocabulary, the notes grid, the ribbon group names,
and the `LAST, FIRST M` upper-case naming.

**Copy the caramel look.** The two view modes for widgets are a real setting:
Program Setup → `Main Screen` → widget layout, **tile** (default) or
**classic**; changing it needs the admin password (`PsLZgSmi_qs`).

Also note the older Payment Entry showed the hint
**`Payments from the selected payer with a balance (Double click to disburse):`**
and `Remaining:` in **red** when money is unapplied (`7Sl9bwm3CxU`) — the red
`Remaining` is still there in the current build.

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

Read against `claims_web.html` (866 lines) and `claims_web.py` as they stand
on branch `claude/adoring-keller-htwwch`. Ordered by **what an EZClaim user
would notice first** on day one.

### What we already match (worth saying, so it isn't re-done)
- **`Save & Close` / `Save` / `Close` in a right-hand button column** — this is
  exactly EZClaim's layout on the claim, patient, payment and library screens.
- **A `Scrub` button** — EZClaim's claim screen has the same button, same name.
- **`Print`** on the same rail.
- **Clicking a date on a two-month calendar to add a service line** — this is
  EZClaim's own idiom, hint text and all.
- **A left record list with a right work area**, and a `Home` tab.
- CMS-1500 box numbers shown beside field labels (`11c`, `21`, `24A`, `33a`) —
  EZClaim does *not* do this, and it is arguably better for a small office.
- `1st DOS` and `Tot. Bal.` column names are already EZClaim's.

### What the second pass changed about this list ★

Read this before the numbered gaps below — the nine skipped videos moved three
things and added two that were not on the list at all.

**Moved up:**

- **Gap 19 (no reports) is bigger and differently shaped than written.**
  It is not thirteen reports, it is **thirty-plus**, several named after
  individual customers, delivered as **downloadable, dated definitions**
  through `Support` → `Download Reports` (§10). The gap is not "write thirteen
  reports"; it is **"have a report engine and a criteria panel"** — after
  which new reports are definitions, not releases. That reframing makes gap 19
  both larger and cheaper than it looked.
- **Gap 18 (no 835/ERA auto-posting) deserves more respect.** It was filed as
  out of scope while we are print-and-mail, and that is still right for *doing*
  it. But `uEox7GQtBhI` shows the vocabulary is load-bearing:
  `Apply` / `Track` / `Ignore`, the group codes `CO/PR/OA/CR/PI`, `Processed as
  Primary` vs `Denied`, and the secondary-billing rule table in §5b. The office
  **already thinks in these words**. Adopting the vocabulary costs nothing and
  is most of the benefit; `Track` in particular (post a $0.00 adjustment so the
  claim stays followable) is a genuinely good idea we could use today.
- **Gap 13 (claim notes) was understated.** EZClaim's notes grid is not a
  comment box — it carries the **money position at the time of each note**
  (units, charges, adjustments, paid, balance), it is **append-only for
  machine-written entries** (no `✕` on those rows), and it is where the payer's
  own rejection text lands verbatim. It is an audit log with commentary. That
  is a better model than what gap 13 describes and it is close to free for us.

**Two new gaps, both structural:**

- **22. No concept of a user.** Everything we have is one login, `blayne`,
  and every record change is anonymous. EZClaim has named users, a nineteen-item
  permission list, `Created User` / `Modified User` columns on grids, an
  activity `Log`, and two reports about who did what (§1d). Their own warning
  is the relevant one: without users *"everybody and everything just gets
  tagged as generic user."* **For a system that will hold claims data this is
  not a nicety** — it is the difference between an audit trail and a file.
  It also gates the thing in §9o that Blayne will eventually want: a read-only
  view for someone who is not the biller.
- **23. No validation-rule layer.** Our `Scrub` is code. EZClaim has a
  **`Rule Library`** with rules firing at four moments — sending a claim,
  saving a patient, saving a payer, saving a physician (§1e) — that support
  configures per site. Crucially, EZClaim is explicit that it **does not
  validate codes**, only presence of required elements. We should draw the same
  line, out loud, so nobody reads "Scrub" as "this checked my coding."

**One thing to stop saying:** the gaps below reference "the thirteen built-in
reports" in a couple of places. That number came from one visible screenful
and is wrong — see §10.

### The gaps

1. **Nothing looks like a ribbon.** EZClaim's entire navigation is a ribbon of
   named groups — `File / Edit / Find / New / Libraries / Alerts / Support` —
   and it is **dynamic**: opening a patient or claim adds a `Patient` or
   `Claim` ribbon tab carrying that record's actions (`Make Recurring`,
   `Copy Claim`, `Save as Template`, `Write Off Claim`, `Pay Off Claim`,
   `Merge Patient`…). We have a four-button tab strip and a fixed button rail.
   This is the first thing the office will notice and the biggest single
   source of "this isn't EZClaim".

2. **No payment entry, and no payments model at all.** EZClaim's `Payment
   Entry` is a whole screen: a check header (source radio `Patient`/`Payer`,
   payer, amount, date, method, ref #), a service-line grid with grouped
   `Payment` / `Adjustment 1` / `Adjustment 2` columns, per-line `Pay`
   buttons, `Auto Apply`, a red `Remaining`, and `Filter Settings`. Plus a
   separate `Payment Modification` screen to edit or delete a posted payment.
   We have four flat fields on the claim (`Amount paid $`, `Date paid`,
   `Date submitted`, `Denial reason`). We cannot:
   - post one check across several patients or claims,
   - apply money to a **specific service line**,
   - record an adjustment with a CARC reason code,
   - enter a **refund or reversal** (EZClaim's convention: type a minus sign
     in the amount cell),
   - see a patient's payment history.

3. **No per-column filter row.** Every EZClaim grid has a permanent filter box
   under each header, an `✕` to clear, and — importantly — the **`%` wildcard**
   for "contains" (`%tom` finds `JONES, TOM W`), plus a filter-icon menu with
   blank/non-blank. We have one `Filter by name` box across all columns.
   **This is cheap to add and is how EZClaim users search for everything.**

3b. **No saved layouts, and this is the one I under-rated.** In EZClaim you
    filter a grid however you like, right-click → `Save Layout`, name it, and
    it becomes a **button under the grid** that is live from then on — new
    claims matching the criteria appear in it automatically. Unlimited
    buttons, renameable, per user. It is how an EZClaim biller builds their
    own morning worklist without asking anyone for a report. We have nothing
    in this shape, and it is mostly a filter-serialisation problem — small
    code for a feature the office would use hourly. (`ikUIM2AVURQ`,
    `p4sCfOq7ftc`)

3c. **No bulk row actions.** EZClaim: shift-select forty rows, right-click,
    and write them all off (posting the adjustments), set their claim status,
    pay them off, create tasks or claim notes against them, or change the
    responsible party — with a different action set per grid (see §9j2). We
    have single-record editing only. For a practice cleaning up aged A/R this
    is the difference between an afternoon and a minute. (`ikUIM2AVURQ`)

3d. **No group-by, no `Print Grid`, no `Export to`.** EZClaim's column-header
    menu is nineteen items (§2) and three of them matter a lot: dragging a
    column into the group-by band to collapse claims under each payer;
    printing the grid as it currently stands; and exporting it to PDF or
    Excel. Export in particular is how EZClaim users answer any question the
    thirteen built-in reports don't — they filter a grid and send it to Excel.
    Without it every unanticipated question becomes a feature request to us.
    (`ikUIM2AVURQ`)

4. **No account numbers.** EZClaim auto-assigns them (`Next Account Number`,
   optional prefix, require-unique, all in Program Setup), shows `Account #`
   in the patients grid, on statements and on reports, and the office refers
   to patients by them. We key entirely off the name.

5. **No patient statements.** EZClaim has a full statements screen —
   check-all selection, `Min. Pat. Bal.` ($0.01), `Min. Sta. Cycle` (30 days),
   per-patient `Pat Msg`, a `Global Message`, `Preview`, and a printed layout
   with a window-envelope address block and the classic aging strip
   (`0-30 / 31-60 / 61-90 / 91-120 / Over 120 / Ins. Bal. / Please Pay`).
   **The family office prints and mails — this is a workflow gap, not
   cosmetic.** We print a CMS-1500 and nothing else.

6. **No row colouring by state.** EZClaim tints whole rows: pink/salmon when
   the patient owes money, green for eligible/ignored. It is user-defined
   conditional formatting (`[Patient Balance] Is greater than $0.00` →
   `Red Fill` → ☑ `Apply formatting to an entire row`), but the *effect* is
   what the office recognises. We use a status pill in one column.

7. **No grid footers with totals or counts.** EZClaim puts `Shown: 30`,
   `Shown: 1 (Filtered)`, `Shown: 4. Checked: 4.` and money totals under every
   grid. We have a totals block on the claims tab only.

8. **Our grids carry far fewer columns, and none can be changed.** EZClaim
   patients grid: `Name`, `Account #`, `Classification`, `Eligibility`,
   `Pri Payer`, `Pat. Bal.`, `Tot. Cla. Bal.`, `Ins. Bal.`,
   `Pat. Unapplied Bal.` — and any of them can be dragged in from a
   `Column Chooser`, reordered, resized, removed, sorted multi-column with
   shift-click, and **saved as a named layout** that persists. Ours are three
   fixed columns.

9. **No detail pane under the record list.** EZClaim's lower-left pane has
   tabs `Details / Claims / Services / Payments / Documents` and shows the
   selected patient's address, phones, primary and secondary insurance, and
   payment history **without opening anything**. We have nothing there — you
   must open the record.

10. **No secondary insurance, and a much thinner patient record.** EZClaim's
    patient screen has `Primary Ins` / `Secondary Ins` tabs, each with the
    insured's own name/DOB/sex/address/employer, `Insured's ID #`, `Group #`,
    `Plan or Program Name`, `Patient Rel to Insured`, `Accept Assignment`,
    plus a `Copy information from the patient` button. It also has
    `Classification`, `Copay Amt` (or percent), default diagnoses carried onto
    new claims, a `Claim Template`, four phone numbers, two emails, emergency
    contact, and `Active` / `Locked` flags. We store name, DOB, sex, address,
    phone, insurer.

11. **No document tabs.** EZClaim keeps the record list visible and opens each
    patient, claim, report and 835 file as its own closable tab — several at
    once (`BROOKS, PATIENT D (Age: 48)`, `CARSON, PATIENT (Age: 66)`), with
    `*` when dirty, and the title bar naming the active screen. We have `Home`
    plus one record tab.

12. **No tasks.** EZClaim has a `Tasks` grid tab, a `Task` button in the
    ribbon, `Subject / Assigned To / Due Date / Status / Priority /
    % Complete`, reminders, and — the part that matters — **`Create Tasks` in
    bulk from a list of rejected claims**. That is how the office works
    rejections. We have nothing.

13. **No claim notes with history.** EZClaim's claim has a notes grid
    (`Time Stamp / User / Note / Balance`) that **auto-logs** `Claim created.`
    / `Claim edited` with the balance at the time, and is where clearinghouse
    277 rejection messages get posted. We have a single free-text `Notes`
    textarea.

14. **No Program Setup.** No theme, no printer alignment (EZClaim's is
    elaborate: 100ths of an inch, `Print Test Page`, per-box shifts for boxes
    31/32/33, `Courier New 12`, date formats), no account-number policy, no
    company description, no grid-footer or row-colour options.

15. **Thin libraries.** We have Insurers and Providers lists. EZClaim's
    `Physician / Facility Library` has a `Classification` per entry
    (`Billing / Facility / Ordering / Referring / Rendering / Supervising`),
    `Person` vs `Non-Person`, `Signature on File`, `Taxonomy Code`,
    `Tax ID Type`, a `Lookup NPI` link, `Additional ID Numbers` per payer,
    a `Pay to Address`, `Mark as Inactive`, and an
    `Entries That Are: Active / Inactive / All` filter. The payer library adds
    a **`Payment Matching Key`** (settable in bulk by right-clicking a
    multi-selection in `Find Payer`).

16. **No home-screen workflow flowchart or widget tiles.** EZClaim's Home is
    the flowchart (`Create Patient → Create Claim → Print Claims / Patient
    Statements / Enter Payment / Send Claims → View EDI Reports`) plus a
    column of count tiles (`Claims Over 90 Days`, `Unpaid Patient Co-pays`,
    `Expiring Auths`, `Claims with a Credit Balance`, `Overdue Statements`,
    `Batch Status`) each opening a detail grid, with `Updated 2:26 PM` and a
    `Refresh`. **The tiles are cheap for us to build and are the first thing
    the office looks at each morning.**

    EZClaim's design intent for them, stated in `ikUIM2AVURQ`: each tile is a
    worklist whose **count you are trying to drive to zero**, and widgets are
    the **only** grid customisation that is company-wide rather than per user,
    so one person builds the list and everyone works it. If we copy one thing
    about the Home screen, copy that.

16b. **No custom fields.** EZClaim gives every patient and claim a handful of
     renameable typed slots (`Custom Text / Number / Date / Currency /
     True-False Value`), configured in Program Setup, which then behave as
     ordinary grid columns — filterable, sortable, conditionally formattable.
     It is the pressure valve that stops every practice-specific need becoming
     a code change, and EZClaim is explicit that they are **internal only and
     never exported onto a claim, paper or electronic**. Cheap for us, and it
     would absorb a lot of future "can it also track…" requests.
     (`ikUIM2AVURQ`)

17. **Claim screen is missing several things EZClaim users expect:**
    - a **`Bill To`** selector with sequence (`Primary (1/1) - GEICO - …`) —
      we have a flat `Bill To` text field
    - **twelve diagnosis slots** labelled `A1 … L12` (we have a dynamic list)
    - **four modifier columns** `M1 M2 M3 M4` (we have one `M1`)
    - a numeric **`Diag. #`** pointer per line (we use letters)
    - `Prior Auth #`, `Date of Curr`, `Admitted Date`, `Service Facility`,
      `Claim Template`, `Invoice #`, `Locked`
    - per-line `Adjs`, `Paid`, `Applied Amt.`, `Resp. Party`, `Pat. Amt.`
    - `Make Recurring` (generate every N months until a date)

18. **No 835/ERA auto-posting**, and none of its vocabulary —
    `Apply` / `Track` / `Ignore`, `Balance Exceeded`, `Payer Not Linked`,
    `Service Line Not Found`, `Recheck Payer Links`, `Close and Archive`.
    Out of scope while we are print-and-mail, but this is the language the
    office uses about adjustments, and `Track` (post a $0.00 adjustment to
    keep the claim followable) is a genuinely good idea worth stealing.

19. **No reports.** EZClaim ships thirteen (`Accounts Receivable`,
    `Adjustments`, `Authorizations`, `Claim List`, `Disbursements`,
    `Patient Demographics`, `Patient Ledger`, `Patient List`, `Patient Notes`,
    `Patient Services`, `Payment List`, `Procedure Code Summary`,
    `Production Summary`) each with a `Report Criteria` panel and a printable
    grouped output with `Grand Totals`. We have none.

20. **No eligibility check** (`CHECK` / `VIEW` inline buttons, green
    `Active <date>` cell), and no `Errors and Warnings` screen separating
    **`Error`** (blocks submission) from **`Warning`** (submits but will
    likely reject) — a distinction our scrubber could adopt immediately.

21. **Wording to align.** EZClaim says `Pri Payer` (we say `Insurance`),
    `Ready to Submit` (we say `Ready`), `Account #`, `Pat. Bal.`, `Ins Bal`,
    `Tot. Chg.`, `Srvc Date` (we say `Svc Date`), `Proc` / `Procedure`,
    `Place` (we say `Place`), `Resp. Party`, `Disbursement` for applying money
    to a line. Negative money is shown **in parentheses** — `($100.00)`.
    Patient names are **`LAST, FIRST M` in upper case** throughout.

22. **No concept of a user** — see "What the second pass changed" above.
    Named users, a permission list, `Created User` / `Modified User` on every
    grid, and an activity log. (`tJsKQEAoRw4`, §1d)

23. **No validation-rule layer** — our `Scrub` is code; EZClaim's is a
    configurable `Rule Library` firing at four save points, and it is explicit
    that it checks required elements, **not codes**. (`tJsKQEAoRw4`, §1e)

24. **No company files.** EZClaim's whole database is switchable from the EZ
    button, and a billing service runs one per provider office, with every
    library, report, batch and setting scoped to it (§1c). We have one
    database. This is not urgent — Dad and one more user come later — but it
    is worth knowing now, because **retro-fitting a tenant boundary is much
    harder than leaving room for one.** The cheap version today is EZClaim's
    own fallback: a `Classification` field on the patient, filterable from the
    grid.

### The revised top of the list

Ordered by what the office notices first, with the second pass folded in:

1. the ribbon (gap 1)
2. the per-column filter row with `%` (gap 3) — still the cheapest real win
3. payment entry and a payments model (gap 2)
4. saved layouts (gap 3b) and bulk row actions (gap 3c)
5. **a report engine with a criteria panel** (gap 19, reframed)
6. patient statements (gap 5)
7. **users and an audit trail** (gap 22, new)
8. account numbers (gap 4)
9. the notes grid as a money-carrying, append-only log (gap 13, upgraded)
10. widget tiles, especially `Batch Status` (gap 16)

Gaps 18 (835 posting) and 24 (company files) stay out of scope as *features*,
but their **vocabulary** and their **shape** should inform what we build now.

---

## Printing (from EZClaim's help manual, not video) ⚠

**Everything in this section is unverified by video.** It comes from a separate
review of EZClaim's written help manual, not from any of the 46 captures. It is
recorded here because printer alignment is the part of paper billing that
generates the most support calls, and because the family office prints and
mails. Treat each point as a claim to confirm, not as an observation.

Where a video does bear on a point, it is noted inline.

### `Home` → `Print` → **`Printer Adjustment`** dialog
Reported contents:

- **`Print Test Page`** — prints a calibration sheet.
- **`Vertical Shift Adjustment`** and **`Horizontal Shift Adjustment`** — shift
  the whole form. The stated calibration method is to
  **align the `X` in the Medicare box on the red CMS-1500**, i.e. you nudge
  until one known mark lands correctly and everything else follows.
- **`Carrier Area Location Adjustment`** — moves **only the Bill To address
  block**, independently of the rest of the form, *so it shows through a window
  envelope*.
- **`Print Form with Data`** — a three-way setting:
  **`Preview Only` / `Always` / `Never`**. This is whether the red CMS-1500
  *form itself* is drawn along with the data, or whether the data alone is
  printed onto a pre-printed form.
- **`Font Settings`**.
- A **`Bottom Margin`** checkbox that **shrinks the font in boxes 31–33** to
  make long provider names and addresses fit.

### Other manual-sourced claims
- **Double-clicking the `Procedure` code on a service line opens a
  `Procedure Code Lookup`**, filtered by **Bill To payer**, **billing
  provider** and **rate class** — so the same CPT can carry a different fee
  depending on who is being billed.
- **A claim `Locked` checkbox greys out the claim fields but still allows
  notes and payments.**

### What the videos say about these

| Manual claim | Video evidence |
|---|---|
| `Locked` checkbox exists on the claim | **Confirmed.** Present as the last row of `Claim Information` at 8.0.581, 8.0.596 and 8.0.655 (`uEox7GQtBhI`, `tJsKQEAoRw4`, `ctXeB-wct-A`), and as `Lock Record` in Advanced 10 (`TDIWTgfUJ2g`). |
| `Locked` greys fields but allows notes and payments | **Not shown.** No capture ever ticks it. **Indirectly supported**, though: `Unlock Claims` and `Unlock Patients` are separate grantable permissions (§1d), which only makes sense if locking blocks editing while leaving the record usable. |
| Printer alignment in 100ths of an inch, `Print Test Page`, per-box shifts for 31/32/33, `Courier New 12` | **Consistent with** the `Printing Claims` pane of Program Setup already recorded in §7 from `gO7UQeKlmFM`. The `Printer Adjustment` dialog under `Home` → `Print` is a *different* entry point and is **not** in any capture. |
| `Print Form with Data` = Preview Only / Always / Never | **Not seen** under that name. Advanced 10 has a per-patient ☐`Print Form & Data` checkbox (`TDIWTgfUJ2g`), which is plausibly the two-state ancestor of the three-state Premier setting — but that is inference, not confirmation. |
| `Carrier Area Location Adjustment` moves the Bill To block for window envelopes | **Not seen.** Consistent with the printed *statement* layout, where the patient address block is positioned for a window envelope (§6, `uqRGjzNM-KE`). |
| `Bottom Margin` checkbox shrinks the font in boxes 31–33 | **Not seen.** §7 records per-box shifts for boxes 31/32/33 from `gO7UQeKlmFM`, so those three boxes are known to get special treatment — which makes the claim plausible. |
| Procedure Code Lookup filtered by payer / billing provider / rate class | **Not directly seen, and nothing contradicts it.** `uEox7GQtBhI` does show double-clicking the **`Adjs`** cell opening an adjustment editor, so double-click-a-cell-to-open-an-editor is definitely the idiom on this grid. The auto-posting webinar also mentions *"allowed amount … some users will enter the allowed amount during data entry"* in the procedure code library, which implies per-payer pricing exists. |

**Nothing in the nine videos contradicts any of these points.** Two are
confirmed outright (`Locked` exists; per-box handling of 31–33 is real), the
rest are unconfirmed but consistent. Before building against this section,
someone should open the help manual again and check it against a running
copy — or ask EZClaim support, who answer this exact kind of question.

---

## Coverage

**The channel has 66 videos. 46 were studied; 20 were skipped deliberately.**
Counted against a `yt-dlp` listing of the channel, so this is the real
denominator rather than an estimate.

Each studied video was downloaded at 720p, frame-sampled, and every sampled
frame was read; captions were taken wherever YouTube served them. The `.mp4` /
`.mkv` was deleted immediately after frame extraction. **Frames and captions
live in `~/ezclaim-study/frames/<video-id>/` on thunder-main and are
deliberately not in this repo** — they are EZClaim's copyrighted material.
Only this notes file is committed.

Sampling was by scene change, or a fixed interval where scene detection
under-samples (which it does badly on a screencast, where the screen barely
changes): 5 s normally, **15 s for anything over 30 minutes**.

YouTube served transient `403 Forbidden` and `429 Too Many Requests` on the
media URLs even when metadata resolved fine. The second pass needed a grabber
with backoff and **alternate player clients** (`grab2.sh`) to get past it;
`uEox7GQtBhI` failed outright on the first attempt and downloaded on a
fallback client.

### First pass — 37 videos
`DZ0spaFoFz4` `_UZktuXNBxc` `h8BdQO3FuPw` `oZBevrOFRwY` `QqvTxnAk2uE`
`7SeDsTtfBNU` `gO7UQeKlmFM` `puSJeow-pkk` `ciHa8ZgTTKE` `m85vv2jh148`
`N2hFJQDke_I` `qG699P9sC0o` `Y_glBgEkSHs` `vZb1Uzv7I7c` `i-7SoiBCpjk`
`uqRGjzNM-KE` `-JrFNkPqilw` `u-TuvmCVj-M` `erCHIBu51xw` `PsLZgSmi_qs`
`p4sCfOq7ftc` `h-EzAeOTDlQ` `5aJQBFSmkbU` `2ZgChe2rNnE` `CN2twFAShj0`
`N9QcUnB5kkY` `sTZilSPX-Fc` `b1AJePNYbcs` `hfhR0DsWxaY` `7Sl9bwm3CxU`
`JX5Esi1Vzp0` `5mj4eSiGSv0` `B2WenGr6fcQ` `Q6ytCiouF4I` `sEgz49YE1lI`
`QiiFx0hCFMU` `ikUIM2AVURQ`

*(An earlier version of this section said "all 38". It was 37 — counted
against the frame directories, which are ground truth.)*

`ikUIM2AVURQ` ("Working with Grids in EZClaim Premier") was the most useful
video of the first pass: the complete nineteen-item column-header menu (§2),
the per-grid bulk row actions (§9j2), the per-user-vs-company-wide rule,
custom fields (§7), and the rest of the conditional-formatting submenu (§9i).
Captured at **8.0.600**, older than the 8.0.665–8.0.670 seen elsewhere, and
nothing in it contradicts the newer captures — **the grids are the stable part
of EZClaim's look.**

### Second pass — 9 videos
These nine were passed over the first time as marketing or sales material. All
nine do show the program on screen, and **three of them are among the most
valuable in the whole set.**

| id | title | length | what it gave |
|---|---|---|---|
| `uEox7GQtBhI` | Understanding the Auto Posting System Within EZClaim | 80 min | ★ the definitive 835 source — §5, §5b, and most of §9c/§9d |
| `ctXeB-wct-A` | Understanding EDI Reports in EZClaim | 19 min | ★ §9b2, §9b3 — the 999 decode, Rejections tab, Claims Not Found |
| `tJsKQEAoRw4` | EZClaim Features That Assist Billing Services Suppliers | 37 min | ★ §1c company files, §1d users, §1e Rule Library |
| `D5CVTNTdCHw` | Benefits of the EZClaim Portal | 11 min | §9o, and the fullest report inventory anywhere |
| `TDIWTgfUJ2g` | Why Upgrade From EZClaim "Advanced" to "Premier"? | 5 min | the only capture of EZClaim Advanced 10 (§11) |
| `-vHuSb1e9iU` | How to Drill Down in Reports in EZClaim | 48 s | report drill-down; the printed `Claim List` layout |
| `Iv8z-duJ_OI` | Downloading Reports in EZClaim | 29 s | ★ `Download Reports` — proves reports are downloadable data |
| `Uu2b0eS6iQo` | Overview of EZClaim Premier [2016] | 2.5 min | 8.0.553 — dates the caramel chrome to March 2016 |
| `XBFxco5x5Ek` | Updating to EZClaim Premier | 2 min | installer, company-file naming, concurrent-user licensing |

**No captions were served for `D5CVTNTdCHw`, `TDIWTgfUJ2g`, `-vHuSb1e9iU`,
`Iv8z-duJ_OI`, `Uu2b0eS6iQo` or `XBFxco5x5Ek`** — those six are read from
frames only, which is worth knowing if a quoted line from them ever looks thin.

The lesson from the second pass: **"it's a sales video" was a bad filter.**
The 80-minute auto-posting webinar was skipped as a webinar recording and
turned out to be the single richest capture in the study. The 29-second
`Downloading Reports` clip was skipped as trivial and settled the most
important architectural question in the notes.

### The 20 skipped, by id — and why

**These are intentionally skipped because they do not show the program.**
Verified by title and duration against the channel listing; none is a
tutorial.

*Company / brand / podcast (6):*
| id | title |
|---|---|
| `nJsU1tkm4fk` | Modernizing Medical Billing Payments Podcast (31 min) |
| `fnNvYWnMwE0` | Using Video to Shape Your Brand's Message and Mentor Your Clients (38 min) |
| `VidEqHVeIYs` | Protect Your Medical Practice Against Rapid Change (17 min) |
| `oa7bFqYN1ds` | Getting Started with the EZClaim Team |
| `8HIlKBHsfFg` | EZClaim Onboarding Process Overview |
| `yCxRx5ExSFo` | Flexibility and Adaptability Sets EZClaim Apart |

*Testimonials and support-culture spots (8):*
| id | title |
|---|---|
| `WkGGtxZB3vA` | Observations of EZClaim by a Medical Biller |
| `uYRTwf_Xv9o` | Customers are First at EZClaim |
| `Mb6z0SNOf3I` | EZClaim's Keys to Customer Service |
| `mpP_eTvk4Pw` | EZClaim is a 'Support Company' First |
| `ctPBYTyDPFE` | EZClaim is "A support company that sells software." |
| `mBIUmNIYqmQ` | Clients Discuss EZClaim Support Experiences |
| `BY1N7B1EEEs` | Firsthand Experiences on the Ease and Flexibility of EZClaim |
| `8ck_OgbkPI4` | Connecting EZClaim to TriZetto Provider Solutions (6 min) |

*Third-party EHR / service integrations (6):*
| id | title |
|---|---|
| `N-COk_N-G6I` | How to Transfer Claims from Nexus Clinical Into EZClaim |
| `CDszuTd8uRk` | How to Send Electronic Statements to BillFlash from EZClaim |
| `lPkcKwKpYsI` | Transferring BestNotes Data into EZClaim |
| `54ZL5-npTZ8` | EZClaim Interface to QuickEMR Tutorial |
| `1itD2kyJ4fg` | Amazing Charts EHR Integrated Into EZClaim |
| `iTlLKCv-KLc` | Practice Fusion EHR Integrated Into EZClaim |

**Two caveats on that classification, given how the second pass went:**

1. **`8ck_OgbkPI4` (Connecting EZClaim to TriZetto Provider Solutions, 6 min)
   is the one genuinely borderline case.** It is filed under testimonials above
   because the title reads like sales, but a six-minute "connecting" video
   almost certainly shows the **Connection Library** (§9m2) being filled in.
   If anyone wants one more video, watch that one.
2. The six EHR-integration clips are 66–113 seconds each and are about *other
   vendors'* software pushing data in. They would show an import screen at
   most, and the `Import` ribbon group (`Appointments`, `Pending Data`) is
   already recorded from `gO7UQeKlmFM`.

### Not covered by any video
- **The EZClaim Scheduling application.** It is a separate installed program
  (§11) and owns the `Appointment List`, `Appointment Status Summary` and
  `Daily Schedule by Resource` reports. Nothing on the channel shows it.
- **The `Printer Adjustment` dialog** under `Home` → `Print` — see the
  printing section above, which is help-manual sourced and unverified.
- **The `Locked` checkbox actually being ticked.** It is visible in three
  builds; no video ever uses it.
- **The Rule Library's rule *editor*.** `Edit Rules` is shown as a button;
  what is behind it is not.
