# Fleet hardware health

Getting ahead of failures instead of finding out when something stops.

    node_probe.py    runs on each node, reads sensors, prints JSON
    odris_health.py  runs on Odris, collects and scores, serves :9007
    GET /fleet/health on Main proxies it for the phone

In the app: **Settings -> Fleet health**. Machines first, tap one for its
parts, tap a part for what was measured and what to do about it.

## Two rules

**Measured, or not assessable - never a guess.** Every component either shows
real readings with their limits, or says plainly that this hardware cannot
report on it. A page claiming "PSU 98%" from nothing is worse than an empty
one, because it gets believed. An uninspectable item is a finding, not a pass.

This caught itself during the build: Odris reported a healthy PSU on the
strength of `amdgpu/vddgfx` at 0.7V - a GPU core voltage being counted as a
power rail. Now the PSU on every board here honestly reports "not inspectable".

**Trends, not snapshots.** A CPU at 55C means nothing. A CPU at 55C that used
to sit at 40C under the same load means dust or dried paste, months before it
throttles. Every poll is kept and today is compared against that machine's own
median, not a number from a manual.

## What each part can actually tell us

| Part | Signal | On this fleet |
|---|---|---|
| CPU | package/core temps, core-to-core spread, throttle counts | all nodes |
| RAM | ECC corrected/uncorrectable per rank, DIMM temps | **serverus only** |
| Drives | SMART, filesystem, kernel I/O errors, SATA resets | no SMART yet |
| GPU | temps against limits, fans, VRAM ECC | main (3090), odris (Radeon) |
| Motherboard | PCIe AER errors, chipset temp, BIOS age, MCEs | all nodes |
| PSU | voltage rails | **none** - no sensor chips fitted |

A wide core-to-core spread means the cooler is sitting crooked or the paste
has dried. Throttle counts are not a prediction - the CPU already got too hot
and recorded it. PCIe corrected errors rising is a card working loose.

## The one thing worth fixing

**SMART is not installed, and it is the best failure warning drives give.**
Reallocated and pending sectors climb weeks before a disk dies. Without it,
problems are only visible once the filesystem is already erroring.

One-time, needs the root password, on each node:

    sudo apt install smartmontools
    echo "$USER ALL=(root) NOPASSWD: /usr/sbin/smartctl" | sudo tee /etc/sudoers.d/smartctl
    sudo chmod 440 /etc/sudoers.d/smartctl

Then change `run(["smartctl", ...])` in `node_probe.py` to prefix `sudo`.
Serverus has 8 drives with no visibility at all, which is where this matters
most.

## Security

Odris collects over SSH with a **forced-command key**: its entry in each
node's `authorized_keys` runs `node_probe.py` and nothing else, with
`restrict` (no shell, no pty, no forwarding). Odris is the only box with
internet access, so it must not double as a way into everything else.

Setting this up found an **unrestricted Odris key already on thunder-main**,
which has been removed.

The probe only reads. It takes no arguments, so there is nothing to inject.
