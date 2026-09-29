# Jellyfin on thunder-cache

Home theatre for the house. Free, local, no account, no cloud. Installed
2026-09-29 on **thunder-cache (10.168.168.11)** — the idle i5-3470 — deliberately
*not* on Main (the 3090 belongs to chat, and Main will hold claims data) and not
on Odris (4GB Radeon, and it is the only box with internet).

**Open it at <http://10.168.168.11:8096>.**

## What was installed, and why this way

thunder-cache has **no internet** and `blayne-cache` has **no passwordless
sudo** there, so the apt repo was not an option. Instead:

- Jellyfin **12.1.0** — the official portable amd64 tarball
  (`jellyfin_12.1-amd64.tar.gz`). It is a self-contained .NET build, so no
  `dotnet` runtime is needed, and the web UI is bundled.
- **jellyfin-ffmpeg 7.1.4-3**, the `resolute` build (thunder-cache is Ubuntu
  26.04 "Resolute Raccoon", so the distro build matches exactly). Unpacked from
  the `.deb` with `dpkg-deb -x` — no root required.

Both were downloaded on **Main** (which does have internet) and `scp`'d over.
Everything lives under `~/jellyfin` on thunder-cache and is owned by
`blayne-cache`. Nothing was installed system-wide; **no root was used at any
point.**

```
~/jellyfin/jellyfin          the server binary
~/jellyfin/bin/ffmpeg        wrapper (see below)
~/jellyfin/bin/ffprobe       wrapper
~/jellyfin/ffmpeg/           unpacked jellyfin-ffmpeg
~/jellyfin/{data,cache,config,log}/
~/media/{Movies,TV,Music}    where the films go
```

Install footprint is ~445MB.

### The ffmpeg wrappers

`jellyfin-ffmpeg` ships its own shared libraries and, unpacked outside its
packaged location, cannot find them — it dies with `error while loading shared
libraries: libavdevice.so.61`. `~/jellyfin/bin/ffmpeg` is a two-line shell
wrapper that sets `LD_LIBRARY_PATH` and execs the real binary. The service
points `--ffmpeg` at the wrapper. `ffprobe` is wrapped the same way because
Jellyfin looks for it next to whatever `--ffmpeg` names.

## Running it

It is a **systemd user service**, `~/.config/systemd/user/jellyfin.service`
(a copy is checked in next to this README). Lingering is enabled for
`blayne-cache`, so it starts at boot and keeps running with nobody logged in.

`loginctl enable-linger` worked **without sudo** — polkit allowed the user to
set linger on themselves. Worth knowing; it is the thing that usually forces a
root password on this kind of install.

```bash
ssh thunder-cache
systemctl --user status  jellyfin
systemctl --user restart jellyfin
systemctl --user stop    jellyfin
journalctl --user -u jellyfin -f     # logs; also ~/jellyfin/log/
```

`Restart=always` with `RestartSec=5`. Verified: `kill -9` on the main PID and
the server was back and answering `Healthy` about 25s later.

### Verified working

- `curl http://10.168.168.11:8096/health` from Main → `Healthy`
- `/System/Info/Public` → `"Version":"12.1.0"`, `"ServerName":"thunder-cache"`
- `/web/index.html` → HTTP 200
- survives `kill -9` (`NRestarts=1`, new PID, healthy again)

The **first-run wizard was deliberately left undone** (`StartupWizardCompleted:
false`) so Blayne creates the admin account and picks his own password.

## Network

Listens on **8096**, LAN only. No remote access, no port forwarding, no UPnP,
no Jellyfin relay or cloud account — none of that was set up and none of it
should be. `ufw` and `nftables` are both inactive on thunder-cache, so no
firewall rule was needed; if one is ever turned on, allow 8096 from
`10.168.168.0/24` only.

The server logs some `System.Net.Http` exceptions at startup. That is it
failing to reach the **online plugin catalogue** — thunder-cache has no
internet. Harmless, and arguably the correct posture for this box.

## Adding movies

Copy files into `~/media/Movies`, `~/media/TV`, or `~/media/Music` on
thunder-cache, then hit **Scan All Libraries** in the Jellyfin dashboard.

From a PC or laptop:

```bash
scp "Some Movie (1999).mkv" thunder-cache:~/media/Movies/
scp -r "Some Show/" thunder-cache:~/media/TV/
```

From a USB drive plugged into thunder-cache: mount it and `cp` across.

Naming matters for artwork and metadata lookup — Jellyfin matches on it:

```
~/media/Movies/Heat (1995)/Heat (1995).mkv
~/media/TV/The Wire/Season 01/The Wire - S01E01.mkv
```

Metadata fetching needs internet, which thunder-cache does not have, so
expect artwork to come up blank. Good filenames still give clean titles,
seasons and episodes.

## Hardware limits — read before blaming the software

thunder-cache is an **i5-3470 (Ivy Bridge, 4 cores, no hyperthreading)** with
Intel HD 2500 graphics, 22GB RAM.

- **Direct play is the goal.** If the TV or phone app can decode the file as-is,
  thunder-cache just streams bytes off the disk and the CPU barely moves. This
  works fine for 4K and HEVC. Prefer clients that direct-play — the official
  apps on a modern TV, Fire Stick, Shield, or phone usually do.
- **Hardware transcoding is currently unavailable.** Ivy Bridge QuickSync can
  only ever do **H.264** (no HEVC, no AV1, no 4K) — but right now it is off
  entirely, because `/dev/dri/renderD128` is `root:render` and `blayne-cache`
  is not in the `render` group. That needs one root command (below).
- **Software transcoding works but is slow.** Four Ivy Bridge cores will
  manage roughly one 1080p H.264 transcode. Two people transcoding at once
  will stutter. 4K transcoding on this CPU is not realistic — 4K needs to
  direct-play.

### To enable hardware transcoding (needs the root password)

On thunder-cache:

```bash
sudo usermod -aG render blayne-cache
sudo loginctl terminate-user blayne-cache   # or just reboot
```

Then in the Jellyfin dashboard → Playback → Transcoding, set hardware
acceleration to **VAAPI**, device `/dev/dri/renderD128`, and tick **H.264
only**. Leave HEVC and VP9 unticked; Ivy Bridge cannot do them and ticking
them produces green frames or failures rather than an honest error.

Check it took with:

```bash
~/jellyfin/bin/ffmpeg -init_hw_device vaapi=va:/dev/dri/renderD128 \
  -f lavfi -i testsrc=size=320x240:rate=1:duration=1 -f null -
```

Right now that prints `No VA display found for device /dev/dri/renderD128`,
which is the permission problem and not a driver problem.

## Disk

One 477GB SSD (`/dev/sda`), **426GB free** after the install. Home and media
are on it. Rough capacity:

| Quality | Per film | Films in 426GB |
|---|---|---|
| 1080p, well encoded | 4–8GB | ~60–100 |
| 4K HDR remux | 40–80GB | ~6–10 |

There is only one drive and **there is no backup of it**. Ripped discs can be
re-ripped; anything irreplaceable does not belong solely here.

## If more space is needed

The board has spare SATA ports. A 4TB SATA SSD or a 4TB 3.5" drive is the
obvious add, under $100 at the time of writing. Mount it and either move
`~/media` onto it or add the new path as a second library folder in Jellyfin —
libraries can span multiple directories, so nothing has to be shuffled.
