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

Sample row: `SAMPLE, PATI… | 1005 | GENERAL GR… | $10.00 | $30.00 |
BLUE CROSS | 10/30/2016 | Please Pay within …`

Footer: `Shown: 4. Checked: 4.` then `$60.00` and `$355.00`. (`DZ0spaFoFz4`)

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
