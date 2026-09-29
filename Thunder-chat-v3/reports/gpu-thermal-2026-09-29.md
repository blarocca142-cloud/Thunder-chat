# The "GPU heating issue" of 2026-09-29

Investigated 2026-09-29 ~12:30 EDT, read-only. Nothing was changed: no power
limit, no fan curve, no clocks, no service restarted. All times below are
**EDT** (Main's local time). The alert file stores UTC — 09:02 UTC is 05:02 EDT.

## The short answer

**It was not the GPU, and it was not an overheat.**

The alert that fired said *"thunder-main: Package temperature up 17.0C on its
own 305-sample normal of 40C"*. `Package id 0` is the **CPU** package sensor
(`coretemp`), read from hwmon. It has nothing to do with the RTX 3090.

The CPU touched **57°C** at the 04:13 poll, against a 100°C limit — 43°C of
headroom. It was flagged only because it was 17°C above its own mostly-idle
median, and the trend check fires at +12°C. It fired **once**, was back to 41°C
an hour later, and has since resolved itself. thunder-main's health score is
100/100 right now.

The GPU logged **no error of any kind**: no Xid, no NVRM message, no reboot, and
the hardware thermal brake has **never** engaged.

## What the numbers actually were

### CPU package temperature, hourly, around the event

Source: `health_history.jsonl` on Odris, 316 samples for thunder-main spanning
2026-09-16 → now.

| time (EDT) | package °C | |
|---|---|---|
| 09-29 01:13 | 42 | |
| 09-29 02:13 | 41 | |
| 09-29 03:13 | 41 | |
| **09-29 04:13** | **57** | **the alert** |
| 09-29 05:13 | 41 | back to normal, one hour later |
| 09-29 06:13 | 42 | |
| 09-29 12:14 | 39 | |

All-time for this machine: **min 34, median 40, max 71**. So 57°C is not even
this CPU's record — it has been 14°C hotter at some earlier point without
anything being wrong.

For an i7-4790, TJmax is 100°C. At 57°C the chip had 43°C of margin and was
nowhere near throttling.

### The alert, exactly as stored

    headline  thunder-main: Package temperature up 17.0C on its own
              305-sample normal of 40C
    severity  critical
    first_seen 2026-09-29T09:02:48Z   = 05:02:48 EDT
    last_seen  2026-09-29T09:02:48Z   = same (seen_count 1)
    resolved_at 2026-09-29T15:07:31Z  = 11:07:31 EDT

`seen_count: 1` — it was true for a single poll and never again.

### Why "critical" overstates it

Two different checks exist in `odris_health.py`. Only one fired.

- The **absolute** checks — `headroom < 20` and `headroom < 5` against the
  100°C limit — **did not fire**. Not close.
- The **relative** trend check fired: `delta >= 12` over the machine's own
  median. 57 − 40 = 17.

The trend check is the right idea (a CPU that always idled at 55°C is fine; the
same CPU at 55°C after a year at 40°C is a dust problem) and its own docstring
already warns about this exact failure mode:

> Idle-to-busy variation within one afternoon is not a trend; a month of
> afternoons is.

The guard it added for that was a **time** span (`MIN_BASELINE_HOURS = 24`), not
a **load** guard. The baseline is a median over 305 samples of a machine that is
idle ~99% of the time, so the median is an *idle* number. Any genuinely busy
hour is therefore ~17°C above "normal" by construction, and gets reported as
critical. That is what happened.

## What caused the CPU to warm up

Sustained model loading between **03:50 and 04:20 EDT** — the model-origin audit
session, not the 3am consolidate job.

`sar` for the window:

| time (EDT) | %user | %system | disk tps | bytes read/s |
|---|---|---|---|---|
| 03:40 | 1.17 | 0.38 | 1.5 | 0.5 KB/s |
| **03:50** | **26.79** | 2.21 | 610 | **248 MB/s** |
| **04:00** | 15.34 | 4.41 | 491 | **232 MB/s** |
| **04:10** | 15.33 | 1.03 | **1004** | **259 MB/s** |
| 04:20 | 7.24 | 0.51 | 544 | 138 MB/s |
| 04:30 | 1.38 | 0.44 | 1.6 | negligible |

And the matching model loads in the ollama journal:

    03:43:56  load  27cd6c43…  25 layers   (Mistral Small 24B)
    03:46:53  load  102a747c…  41 layers
    03:50:59  load  27cd6c43…  25 layers   (again)
    04:01:12  load  970aa74c…  13 layers   (nomic-embed-text)

Four full model loads in eighteen minutes. Each one reads 11–17 GB of GGUF off
the SSDs and pushes it over PCIe, which is a **disk and CPU** job. Note the CPU
never exceeded ~27% of eight threads — this was not even a heavy CPU load, just
a much busier hour than the 1% idle that set the baseline.

The 04:13 temperature poll landed squarely in the middle of it.

### The drives were fine, and the smartd lines are misleading

smartd logged what looks alarming:

    03:34:56  /dev/sda  Airflow_Temperature_Cel changed from 64 to 73

Attribute 190 on these drives is reported **normalised**, where `normalised =
100 − actual°C`. Read raw right now:

| drive | normalised | actual |
|---|---|---|
| sda | 071 | **29°C** |
| sdb | 072 | **28°C** |
| sdc | 073 | **27°C** |
| sdd | 071 | **29°C** |

So "64 → 73" means the drive went from 36°C to **27°C** — it *cooled*. The one
real warming step was sda at 04:04 (73 → 58, i.e. 27°C → 42°C), during the
model-load burst, and it was back to 28°C by 04:34. Worst-ever for sda is 53°C.
Nothing here is a problem; don't read those journal lines as temperatures.

## The GPU itself

### No errors, at all

- `journalctl -k` and `journalctl --since today` for NVRM / Xid / thermal /
  throttle / "fallen off the bus": **zero matches**.
- No reboots. Uptime is **5 days 17 hours**, unbroken since 2026-09-23 19:04.
- **HW Thermal Slowdown: 0 µs.** This is the 95°C emergency brake. It has never
  engaged in this boot.
- **HW Power Brake: 0 µs.**

### Current state (idle)

    GPU temp             36°C        (43°C with the model resident)
    Fan                  0%          (zero-RPM idle; 30% at 43°C)
    Power                15.6 W      of a 420 W limit
    P-state              P8
    Shutdown / Slowdown / Max-operating   98 / 95 / 93 °C
    Target temperature   83°C
    Power limit          420 W default, 420 W current, 100–450 W range

Nothing has been altered — the card is at its stock 420 W default.

### How hard the card actually works

From Odris's GPU odometer, since 2026-09-20:

| | |
|---|---|
| powered hours | 228.96 h |
| **hours actually generating** | **3.00 h** |
| energy | 5.34 kWh |

**A 1.3% duty cycle.** This card spends almost all of its life idle at 15 W.
That is the single most important number here: it is not a thermally stressed
part.

### The one loose end: SW thermal slowdown

Being straight about this, because it is the only GPU reading that is not
clean.

    SW Thermal Slowdown counter   2,515,847,828 µs  = 2,516 s ≈ 42 min
    SW Power Capping counter    484,380,376,563 µs  = 484,380 s ≈ 5.6 days

The power-capping counter ≈ uptime, which confirms these counters are **since
driver load**, i.e. the last 5d17h. So the card has logged ~42 minutes of
*software* thermal slowdown in that time.

That sounds worse than it is, and it cannot be pinned down:

- Yesterday's bench (`deploy-2026-09-28.md`) recorded throttle reason `0x24` =
  SwPowerCap + SwThermalSlowdown at a peak core temp of **61°C**. A core at 61°C
  is not thermally throttling by any normal reading, so the bit is being set for
  something other than core temperature.
- The most likely candidate is **GDDR6X memory junction temperature**. On a
  3090 the memory sits on the back of the PCB and typically runs 20–30°C above
  core, throttling around 105–110°C. At 61°C core, junction could plausibly be
  85–95°C.
- **We cannot measure it.** `temperature.memory` reports `N/A` on driver
  610.57.04, which is normal for GeForce cards.
- It may also simply be a driver quirk in this counter; NVML's SW-slowdown
  reporting on consumer cards is not reliable.

**What is certain:** the *hardware* thermal protection never triggered, and the
highest core temperature ever recorded on this card in the repo is **61°C**,
measured on the old 24B model which drew more power than the current one.

## The real problem found: GPU temperature is not being recorded

This is the finding worth acting on.

`health_history.jsonl` stores these keys for thunder-main, and only these:

    acpitz/temp1_input, acpitz/temp2_input,
    coretemp/Core 0..3, coretemp/Package id 0

**There is no GPU entry.** `odris_health.py` *reads* the card's temperature
every poll and puts it in the readings, but it is never persisted into the
history, so:

- there is **no GPU temperature trend check** — the trend machinery that
  flagged the CPU does not run on the card at all;
- the only GPU thermal rule is absolute, `celsius >= limit - 5` with `limit`
  defaulting to 90, so **it fires at 85°C or not at all**;
- that single check runs on an **hourly** poll against a card that is busy
  **1.3% of the time**.

The odds of that catching a real thermal event are close to zero. If the 3090
*had* cooked itself this morning, nothing in the fleet would have noticed. The
CPU got a critical alert for being 17°C warm; the GPU would have got silence.

## Recommendations

### 1. Do not set a power limit. (Nothing to fix)

The evidence does not support it: hardware thermal protection has never
engaged, the highest core temp on record is 61°C, and the card is idle 98.7% of
the time. Capping power now would be solving a problem that has not been shown
to exist.

If you want the headroom anyway for peace of mind, the cost is genuinely small —
LLM decode is memory-bandwidth-bound, not compute-bound, so the 3090 is not
using most of that 420 W during chat. `nvidia-smi -pl 280` would typically cost
somewhere around **3–7% of tok/s** (i.e. ~190 → ~180). That is an estimate, not
a measurement on this box; `thunder-tune/bench.py` would settle it in a couple
of minutes.

The systemd oneshot to make it survive a reboot already exists as a recipe in
`thunder-tune/tune.sh` (the `thunder-gpu.service` block) — persistence mode plus
`-pl`, with an `ExecStop` that restores `power.default_limit`. It does not need
to be written from scratch.

### 2. Record GPU temperature into the history, and trend it

The gap above. Add the nvidia card's temperature to the slimmed `temps` dict
that gets written to `health_history.jsonl`, then run the same `trend()` check
on it that the CPU package already gets. Without this there is no way to answer
"was the GPU hot this morning" — which is exactly the question that was asked
today and could not be answered from data.

An hourly poll will still miss short bursts. Sampling the card's temperature
during generation — `app.py` already shells out to `nvidia-smi` on the `/status`
path — would give real coverage for the 1.3% of the time that matters.

### 3. Make the CPU trend check load-aware, so this alert stops crying wolf

It fired "critical" on one sample, for a completely normal busy hour. Any of
these would fix it without losing the dust/paste signal it is there for:

- require **2+ consecutive** samples over threshold before alerting
  (`seen_count: 1` should not be critical);
- compare like with like — record CPU load alongside the temperature and
  compare a busy sample against the busy baseline;
- or use a **high percentile** (p90) of history as the baseline instead of the
  median, so the reference is not an idle number.

### 4. Dust and paste: worth doing, but on schedule, not urgently

No evidence of degraded cooling. The CPU returns to 39–42°C at idle, the same
as its 305-sample median, which is what a *clean* cooler looks like — a dust
problem shows up as the **idle** baseline drifting upward, and it has not.
Case airflow is fine too: the drives sit at 27–29°C.

Since you have thermal paste on hand, the reasonable version is: next time the
machine is open anyway, blow out the heatsinks and the 3090's fins. On a 3090
specifically, **thermal pads on the memory** are the part that ages and matters
— but opening the card voids nothing at this point and risks more than it
gains while there is no measured problem. Wait for recommendation 2 to produce
real data first.

## One-line summary

A single hourly sample caught the **CPU** at 57°C (of a 100°C limit) during
thirty minutes of model loading at 04:00 EDT, and a baseline-relative alert
called it critical because the machine is normally idle at 40°C. The GPU was
never in trouble and never logged an error. The actual defect is that **nobody
is watching the GPU's temperature at all**.
