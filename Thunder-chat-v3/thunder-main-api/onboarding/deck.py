"""Two views of one deck, so the presenter notes never reach the television.

This is the whole architectural reason the deck is not a single page. Casting
from Android mirrors a browser tab: whatever is in the tab is on the TV. So any
design where the notes live in the same view as the slide - hidden panel,
collapsed drawer, small text, doesn't matter - puts the notes on the screen the
moment they are useful.

    /deck            the audience view. Cast this one. Slide only, no controls.
    /deck/presenter  the phone. Same slide, plus notes, contents and definitions.
    /deck/state      the shared position, so moving one moves the other.

The presenter drives; the audience view polls. Polling rather than a websocket
because the whole thing has to survive a phone locking, a tab being backgrounded
on a Chromecast, and wifi hiccuping mid-sentence - a poll recovers from all
three by itself, and a socket needs reconnect logic to do the same job.

**The audience view has no buttons on purpose.** Worth knowing before adding
any: opening /deck expecting controls and finding none is a confusing first
experience, so the cover explains itself and points at the presenter URL. The
controls are absent because a television is not a thing you tap.

Three implementation notes, each of which has already cost an evening somewhere:

**The templates are raw strings and never f-strings.** CSS and JS are full of
braces, and an f-string would try to read them as fields. Substitution is done
with .replace() on explicit placeholders instead.

**No backslash escapes in the JavaScript.** A `\\n` written in an ordinary
triple-quoted Python string becomes a real newline before the browser ever sees
it, which breaks the JS string it was sitting in, which breaks the parse, which
silently kills every script on the page. That exact bug cost an evening on the
Odris dashboard.

**No external resources.** No CDN, no web font, no analytics. Partly because a
deck that needs the internet to render is a strange advertisement for a system
whose whole pitch is that it does not, and partly because the room it gets shown
in may not have working wifi.
"""
from __future__ import annotations

import json
import threading

from . import content

# The position both views agree on. In memory on purpose: a talk is a session,
# and a deck that reopens on slide 14 tomorrow because that is where it was left
# is a worse default than reopening at the cover.
#
# `started` is what makes the opening choice possible - until the presenter picks
# short or detailed, both screens show the cover, so the television displays
# something deliberate instead of slide one of twenty-three.
_state = {"slide": 0, "detail": False, "started": False, "rev": 0}
_lock = threading.Lock()


def get_state() -> dict:
    with _lock:
        return dict(_state)


def set_state(slide: int | None = None, detail: bool | None = None,
              started: bool | None = None) -> dict:
    """`rev` increments on every change so the audience view can tell a real
    move from a poll that happened to land between two identical answers."""
    with _lock:
        if slide is not None:
            _state["slide"] = max(0, min(int(slide), len(content.SLIDES) - 1))
        if detail is not None:
            _state["detail"] = bool(detail)
        if started is not None:
            _state["started"] = bool(started)
        _state["rev"] += 1
        return dict(_state)


def _payload(audience: bool = False) -> str:
    """Slides as JSON for the page.

    The audience build has the notes and the glossary removed outright, not
    merely left unrendered. Both views started from the same payload, which put
    every presenter note in the cast page's source - invisible on the television
    but one careless change away from being on it, and readable by anyone who
    views source on the device doing the casting. A note that cannot be rendered
    because it was never sent is the only version of this that stays true.

    `</` is broken up because a closing tag inside an inline <script> ends the
    script element no matter that it sits inside a JSON string.
    """
    def slim(s: dict) -> dict:
        keep = ("section", "title", "short", "detail", "layout", "stats")
        return {k: s[k] for k in keep if k in s}

    if audience:
        data = {"slides": [slim(s) for s in content.SLIDES], "glossary": {},
                "sections": content.sections_with_slides()}
    else:
        data = {"slides": content.SLIDES, "glossary": content.GLOSSARY,
                "sections": content.sections_with_slides()}
    data["accents"] = {name: content.accent_for(name) for name in content.SECTIONS}
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


# --------------------------------------------------------------------- styling
# Shared by both views. The chapter accent arrives as --accent, set from JS on
# every slide change, so one stylesheet recolours the whole room.
_CSS = r"""
:root {
  --bg0:#0A0C10; --bg1:#12161D; --bg2:#1A1F28;
  --ink:#F2EEE6; --ink-dim:#A8A399; --ink-faint:#6E6A63;
  --accent:#C4A35A;
  --glass:rgba(255,255,255,.045);
  --edge:rgba(255,255,255,.09);
  --good:#7FD69B; --bad:#FF8A7A;
}
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
html,body { margin:0; height:100%; }
body {
  background:var(--bg0);
  color:var(--ink);
  overflow:hidden;
  font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-feature-settings:"kern" 1,"liga" 1,"cv11" 1;
  -webkit-font-smoothing:antialiased;
}

/* Slow-drifting colour field. Three soft blobs, one of them the chapter accent,
   so changing chapter visibly changes the light in the room. */
.bg { position:fixed; inset:-25%; pointer-events:none; filter:blur(70px); opacity:.6; }
.bg i {
  position:absolute; display:block; border-radius:50%;
  width:60vmax; height:60vmax; mix-blend-mode:screen;
}
.bg i:nth-child(1) {
  background:radial-gradient(circle,var(--accent) 0%,transparent 62%);
  top:-14%; left:-8%; animation:drift1 26s ease-in-out infinite alternate;
}
.bg i:nth-child(2) {
  background:radial-gradient(circle,#2F6FB8 0%,transparent 62%);
  bottom:-20%; right:-10%; animation:drift2 32s ease-in-out infinite alternate;
}
.bg i:nth-child(3) {
  background:radial-gradient(circle,#6B4E9B 0%,transparent 66%);
  top:28%; right:18%; animation:drift3 38s ease-in-out infinite alternate;
  opacity:.65;
}
@keyframes drift1 { to { transform:translate3d(9vw,7vh,0) scale(1.14); } }
@keyframes drift2 { to { transform:translate3d(-11vw,-6vh,0) scale(1.1); } }
@keyframes drift3 { to { transform:translate3d(6vw,-9vh,0) scale(.9); } }

/* Grain. Keeps large flat gradients from banding on a television, which is the
   single thing that made the first version look cheap. */
.grain {
  position:fixed; inset:0; pointer-events:none; opacity:.028; z-index:2;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='120' height='120' filter='url(%23n)'/%3E%3C/svg%3E");
}

@media (prefers-reduced-motion:reduce) {
  .bg i { animation:none; }
  .fx { animation:none !important; }
}

.rail { position:fixed; top:0; left:0; right:0; height:3px; z-index:6; background:rgba(255,255,255,.06); }
.rail b { display:block; height:100%; background:var(--accent); transition:width .45s cubic-bezier(.4,0,.2,1); box-shadow:0 0 14px var(--accent); }

.wrap { position:relative; z-index:3; height:100%; display:flex; flex-direction:column; }

.chapter { display:flex; align-items:center; gap:.7em; color:var(--accent); font-weight:650; letter-spacing:.14em; text-transform:uppercase; }
.chapter s { text-decoration:none; opacity:.5; font-variant-numeric:tabular-nums; }
.chapter em { font-style:normal; width:2.2em; height:1px; background:currentColor; opacity:.45; }

h1 { margin:0; font-weight:760; letter-spacing:-.022em; line-height:1.04; text-wrap:balance; }
.sub { color:var(--ink-dim); font-weight:400; }

ul { margin:0; padding:0; list-style:none; display:flex; flex-direction:column; }
li { display:flex; gap:.75em; align-items:flex-start; color:var(--ink); }
li > s {
  flex:none; text-decoration:none; color:var(--accent); font-variant-numeric:tabular-nums;
  opacity:.85; font-weight:700;
}

/* Numbers get to be numbers. */
.stats { display:flex; flex-wrap:wrap; }
.stat { flex:1 1 0; min-width:6em; border-left:2px solid var(--edge); }
.stat.good { border-left-color:var(--good); }
.stat.bad { border-left-color:var(--bad); }
.stat b { display:block; font-weight:780; letter-spacing:-.03em; line-height:1; font-variant-numeric:tabular-nums; }
.stat u { display:block; text-decoration:none; color:var(--ink-faint); font-weight:600; }
.stat span { display:block; color:var(--ink-dim); }

.fx { animation:rise .5s cubic-bezier(.16,1,.3,1) both; }
@keyframes rise { from { opacity:0; transform:translateY(14px); } to { opacity:1; transform:none; } }

.card { background:var(--glass); border:1px solid var(--edge); border-radius:16px; backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); }
button { font:inherit; color:inherit; background:none; border:none; cursor:pointer; }
.term { color:var(--accent); border-bottom:1px dashed color-mix(in srgb,var(--accent) 60%,transparent); cursor:pointer; }
.mono { font-variant-numeric:tabular-nums; }
"""


# ------------------------------------------------------------- audience view
_AUDIENCE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Thunder</title>
<style>__CSS__
.wrap { padding:clamp(28px,5vh,70px) clamp(30px,6vw,110px) clamp(60px,8vh,90px); justify-content:center; }
.chapter { font-size:clamp(11px,1.15vw,17px); margin-bottom:clamp(14px,2.4vh,30px); }
h1 { font-size:clamp(30px,4.6vw,86px); }
.slide h1 { margin-bottom:clamp(20px,3.4vh,44px); }
ul { gap:clamp(12px,2.1vh,26px); margin-top:clamp(6px,1vh,14px); }
li { font-size:clamp(17px,2.25vw,40px); line-height:1.32; }
li > s { font-size:.62em; padding-top:.36em; }
.detailed h1 { font-size:clamp(25px,3.5vw,64px); }
.detailed li { font-size:clamp(14px,1.62vw,29px); line-height:1.4; }
.detailed ul { gap:clamp(9px,1.5vh,18px); }

.stats { gap:clamp(16px,2.6vw,48px); margin-bottom:clamp(20px,3vh,40px); }
.stat { padding-left:clamp(12px,1.4vw,24px); }
.stat b { font-size:clamp(34px,5.6vw,104px); }
.stat u { font-size:clamp(11px,1.15vw,19px); margin-top:.35em; }
.stat span { font-size:clamp(12px,1.25vw,21px); margin-top:.5em; line-height:1.3; }
.detailed .stat b { font-size:clamp(26px,3.8vw,68px); }

/* The opening frame. Deliberately unlike the slides: it is a title card, and it
   is what sits on the television while the room settles. */
.cover { display:flex; flex-direction:column; justify-content:center; height:100%; }
.mark { display:flex; align-items:center; gap:.8em; color:var(--accent); font-weight:700; letter-spacing:.34em; text-transform:uppercase; font-size:clamp(10px,1.05vw,15px); margin-bottom:clamp(20px,3.4vh,42px); }
.mark i { display:block; width:clamp(7px,.7vw,11px); height:clamp(7px,.7vw,11px); border-radius:50%; background:var(--accent); box-shadow:0 0 18px var(--accent); animation:pulse 2.6s ease-in-out infinite; }
@keyframes pulse { 50% { opacity:.35; transform:scale(.82); } }
.cover h1 { font-size:clamp(34px,6.4vw,124px); max-width:19em; }
.cover .sub { font-size:clamp(15px,1.85vw,32px); margin-top:clamp(16px,2.6vh,34px); max-width:30em; line-height:1.45; }
.cover .hint { margin-top:clamp(26px,4.4vh,56px); color:var(--ink-faint); font-size:clamp(11px,1.15vw,18px); display:flex; align-items:center; gap:.7em; }
.cover .hint b { color:var(--ink-dim); font-weight:600; }

.foot { position:absolute; left:clamp(30px,6vw,110px); right:clamp(30px,6vw,110px); bottom:clamp(20px,3vh,38px); display:flex; justify-content:space-between; align-items:baseline; font-size:clamp(10px,1.05vw,16px); color:var(--ink-faint); z-index:4; }
.foot .now { color:var(--ink-dim); }
.offline { color:var(--bad); }

/* A phone or tablet held up as a second screen. */
@media (max-aspect-ratio:1/1) {
  h1 { font-size:clamp(28px,7.4vw,58px); }
  .cover h1 { font-size:clamp(32px,9vw,68px); }
  li { font-size:clamp(16px,4.3vw,30px); }
  .detailed li { font-size:clamp(13px,3.5vw,24px); }
  .chapter { font-size:clamp(10px,2.7vw,15px); }
  .stat b { font-size:clamp(28px,9vw,56px); }
  .stats { gap:18px; }
  .foot { font-size:clamp(10px,2.6vw,14px); }
}
</style></head>
<body>
<div class="bg"><i></i><i></i><i></i></div>
<div class="grain"></div>
<div class="rail"><b id="rail" style="width:0"></b></div>
<div class="wrap" id="wrap"><div id="stage"></div></div>
<div class="foot">
  <span class="now" id="count"></span>
  <span id="brand">Made by Thunder &middot; running on our own hardware</span>
</div>
<script>
const DATA = __PAYLOAD__;
let rev = -1, failures = 0;

function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

function bullets(lines) {
  return '<ul>' + lines.map(function (line, i) {
    return '<li class="fx" style="animation-delay:' + (90 + i * 75) + 'ms">' +
           '<s>' + String(i + 1).padStart(2, '0') + '</s><span>' + esc(line) + '</span></li>';
  }).join('') + '</ul>';
}

function statsBlock(stats) {
  return '<div class="stats">' + stats.map(function (s, i) {
    return '<div class="stat ' + (s.tone || '') + ' fx" style="animation-delay:' + (90 + i * 95) + 'ms">' +
           '<b>' + esc(s.value) + '</b>' +
           (s.unit ? '<u>' + esc(s.unit) + '</u>' : '<u>&nbsp;</u>') +
           '<span>' + esc(s.label) + '</span></div>';
  }).join('') + '</div>';
}

function cover() {
  const s = DATA.slides[0];
  return '<div class="cover">' +
    '<div class="mark fx"><i></i><span>Thunder</span></div>' +
    '<h1 class="fx" style="animation-delay:80ms">' + esc(s.title) + '</h1>' +
    '<div class="sub fx" style="animation-delay:180ms">Six computers in a house, running our own AI. ' +
      'Nothing we do leaves the building.</div>' +
    '<div class="hint fx" style="animation-delay:300ms">Waiting for the presenter to pick ' +
      '<b>&nbsp;Quick tour&nbsp;</b> or <b>&nbsp;Full detail</b></div>' +
    '</div>';
}

function render(st) {
  const stage = document.getElementById('stage');
  const wrap = document.getElementById('wrap');

  if (!st.started) {
    document.documentElement.style.setProperty('--accent', DATA.accents[DATA.slides[0].section]);
    wrap.className = 'wrap';
    stage.innerHTML = cover();
    document.getElementById('count').textContent = '';
    document.getElementById('rail').style.width = '0';
    return;
  }

  const s = DATA.slides[st.slide];
  if (!s) return;
  const sec = DATA.sections.find(function (x) { return x.name === s.section; }) || {};
  document.documentElement.style.setProperty('--accent', DATA.accents[s.section] || '#C4A35A');
  wrap.className = 'wrap' + (st.detail ? ' detailed' : '');

  const lines = st.detail ? s.detail : s.short;
  const head = '<div class="chapter fx"><s>' + String(sec.number || 1).padStart(2, '0') +
               '</s><em></em><span>' + esc(s.section) + '</span></div>' +
               '<h1 class="fx" style="animation-delay:60ms">' + esc(s.title) + '</h1>';

  stage.innerHTML = '<div class="slide">' + head +
    ((s.layout === 'stats' && s.stats) ? statsBlock(s.stats) : '') +
    bullets(lines) + '</div>';

  document.getElementById('count').textContent =
    esc(s.section) + '  —  ' + (st.slide + 1) + ' of ' + DATA.slides.length;
  document.getElementById('rail').style.width =
    ((st.slide + 1) / DATA.slides.length * 100) + '%';
}

async function poll() {
  try {
    const r = await fetch('/deck/state', { cache: 'no-store' });
    const st = await r.json();
    failures = 0;
    const brand = document.getElementById('brand');
    brand.classList.remove('offline');
    brand.textContent = 'Made by Thunder · running on our own hardware';
    if (st.rev !== rev) { rev = st.rev; render(st); }
  } catch (e) {
    // Say so on the third miss, not the first: one dropped poll on wifi is
    // normal, and a warning that flickers is worse than no warning.
    if (++failures >= 3) {
      const brand = document.getElementById('brand');
      brand.classList.add('offline');
      brand.textContent = 'Lost the presenter — slide is frozen';
    }
  }
  setTimeout(poll, 700);
}
poll();
</script>
</body></html>
"""


# ------------------------------------------------------------ presenter view
_PRESENTER = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#0A0C10">
<title>Thunder &middot; presenter</title>
<style>__CSS__
.bar { display:flex; align-items:center; gap:7px; padding:12px 14px 10px; }
.bar .who { font-size:10px; letter-spacing:.2em; text-transform:uppercase; color:var(--accent); font-weight:750; }
.bar .sp { flex:1; }
.chip { background:var(--glass); border:1px solid var(--edge); border-radius:999px; padding:8px 13px; font-size:12px; color:var(--ink-dim); font-weight:600; }
.chip.on { background:var(--accent); border-color:var(--accent); color:#0A0C10; }
.scroll { flex:1; overflow-y:auto; overscroll-behavior:contain; padding:4px 14px 122px; }

.slidecard { padding:16px; }
.slidecard .chapter { font-size:10px; margin-bottom:11px; }
.slidecard h1 { font-size:22px; margin-bottom:13px; }
.slidecard ul { gap:10px; }
.slidecard li { font-size:14px; line-height:1.45; }
.slidecard li > s { font-size:.72em; padding-top:.3em; }
.slidecard .stats { gap:12px; margin-bottom:14px; }
.slidecard .stat { padding-left:10px; min-width:4.6em; }
.slidecard .stat b { font-size:26px; }
.slidecard .stat u { font-size:9px; margin-top:.3em; }
.slidecard .stat span { font-size:11px; margin-top:.35em; line-height:1.25; }

.label { color:var(--accent); font-size:10px; letter-spacing:.2em; text-transform:uppercase; font-weight:750; margin:22px 0 9px; display:flex; align-items:center; gap:8px; }
.label em { flex:1; height:1px; background:var(--edge); font-style:normal; }
.notes { background:color-mix(in srgb,var(--accent) 9%,transparent); border:1px solid color-mix(in srgb,var(--accent) 26%,transparent); border-radius:14px; padding:15px; font-size:15px; line-height:1.58; color:var(--ink); }
.next { color:var(--ink-dim); font-size:13px; line-height:1.5; }
.termrow { display:flex; flex-wrap:wrap; gap:8px; }
.termrow .term { background:var(--glass); border:1px solid var(--edge); border-bottom-style:dashed; border-radius:9px; padding:7px 11px; font-size:13px; }

.nav { position:fixed; left:0; right:0; bottom:0; display:flex; gap:9px; padding:11px 14px calc(11px + env(safe-area-inset-bottom)); background:linear-gradient(to top,rgba(10,12,16,.99),rgba(10,12,16,.9)); border-top:1px solid var(--edge); z-index:8; }
.nav button { flex:1; background:var(--glass); border:1px solid var(--edge); border-radius:13px; padding:15px 0; font-size:15px; font-weight:650; }
.nav button.primary { background:var(--accent); border-color:var(--accent); color:#0A0C10; flex:1.7; }
.nav button:disabled { opacity:.3; }

.sheet { position:fixed; inset:0; background:rgba(6,8,11,.78); backdrop-filter:blur(7px); display:none; align-items:flex-end; z-index:20; }
.sheet.open { display:flex; animation:fadein .2s ease; }
@keyframes fadein { from { opacity:0; } }
.sheetbody { background:var(--bg1); border:1px solid var(--edge); border-bottom:0; width:100%; max-height:82vh; overflow-y:auto; border-radius:20px 20px 0 0; padding:20px 18px calc(22px + env(safe-area-inset-bottom)); animation:up .26s cubic-bezier(.16,1,.3,1); }
@keyframes up { from { transform:translateY(26px); } }
.sheetbody h2 { margin:0 0 10px; font-size:17px; color:var(--accent); letter-spacing:-.01em; }
.sheetbody p { font-size:15px; line-height:1.6; margin:0; color:var(--ink); }
.grip { width:36px; height:4px; border-radius:99px; background:var(--edge); margin:0 auto 16px; }

/* Contents. A grid of chapters, not a list of 23 slides - the complaint was
   being stuck swiping, and what fixes that is jumping to a chapter by name. */
.toc h2 { margin:0 0 4px; font-size:19px; color:var(--ink); }
.toc .note { color:var(--ink-faint); font-size:12px; margin-bottom:16px; }
.chap { display:flex; align-items:center; gap:13px; width:100%; text-align:left; padding:13px 12px; border-radius:13px; border:1px solid var(--edge); background:var(--glass); margin-bottom:9px; }
.chap.cur { border-color:var(--accent); background:color-mix(in srgb,var(--accent) 12%,transparent); }
.chap .n { font-size:12px; font-weight:750; font-variant-numeric:tabular-nums; width:22px; flex:none; opacity:.85; }
.chap .t { flex:1; }
.chap .t b { display:block; font-size:15px; font-weight:650; }
.chap .t span { display:block; font-size:12px; color:var(--ink-dim); margin-top:2px; line-height:1.35; }
.chap .c { font-size:11px; color:var(--ink-faint); flex:none; font-variant-numeric:tabular-nums; }

/* The opening choice. */
.start { padding:26px 18px 30px; }
.start .mark { display:flex; align-items:center; gap:.75em; color:var(--accent); font-weight:750; letter-spacing:.3em; text-transform:uppercase; font-size:10px; margin-bottom:18px; }
.start .mark i { width:8px; height:8px; border-radius:50%; background:var(--accent); box-shadow:0 0 14px var(--accent); }
.start h1 { font-size:27px; margin-bottom:12px; }
.start .sub { font-size:14px; line-height:1.55; margin-bottom:24px; }
.pick { display:flex; flex-direction:column; gap:11px; margin-bottom:8px; }
.pick button { text-align:left; padding:17px 16px; border-radius:15px; border:1px solid var(--edge); background:var(--glass); }
.pick button.hero { border-color:var(--accent); background:color-mix(in srgb,var(--accent) 13%,transparent); }
.pick b { display:block; font-size:16px; font-weight:700; margin-bottom:4px; }
.pick span { display:block; font-size:12.5px; color:var(--ink-dim); line-height:1.45; }
.pick .meta { color:var(--accent); font-weight:650; }
</style></head>
<body>
<div class="bg"><i></i><i></i><i></i></div>
<div class="grain"></div>
<div class="rail"><b id="rail" style="width:0"></b></div>

<div class="wrap">
  <div class="bar" id="bar">
    <span class="who">Presenter</span>
    <span class="sp"></span>
    <button class="chip" id="autoBtn">Auto</button>
    <button class="chip" id="speakBtn">Read</button>
    <button class="chip" id="detailBtn">Detail</button>
    <button class="chip" id="tocBtn">Contents</button>
  </div>
  <div class="scroll" id="scroll"></div>
  <div class="nav" id="nav">
    <button id="prev">&larr;</button>
    <button id="next-btn" class="primary">Next &rarr;</button>
  </div>
</div>

<div class="sheet" id="sheet"><div class="sheetbody">
  <div class="grip"></div>
  <h2 id="sheetTitle"></h2>
  <p id="sheetText"></p>
</div></div>

<div class="sheet" id="toc"><div class="sheetbody toc">
  <div class="grip"></div>
  <h2>Contents</h2>
  <div class="note" id="tocNote"></div>
  <div id="tocList"></div>
</div></div>

<script>
const DATA = __PAYLOAD__;
let st = { slide: 0, detail: false, started: false };

function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

function post(patch) {
  Object.assign(st, patch);
  render();
  fetch('/deck/state', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slide: st.slide, detail: st.detail, started: st.started })
  }).catch(function () { /* this view is already right; the TV catches up */ });
}

function go(delta) {
  const n = st.slide + delta;
  if (n < 0 || n >= DATA.slides.length) return;
  if (!auto) stopSpeaking();
  post({ slide: n });
}

function jump(i) {
  if (!auto) stopSpeaking();
  post({ slide: i, started: true });
}

function openSheet(title, text) {
  document.getElementById('sheetTitle').textContent = title;
  document.getElementById('sheetText').textContent = text;
  document.getElementById('sheet').classList.add('open');
}

/* ---------------------------------------------------------------- narration */
const audio = new Audio();
let auto = false;

function stopSpeaking() {
  audio.pause();
  audio.removeAttribute('src');
  document.getElementById('speakBtn').className = 'chip';
}

function speak() {
  audio.src = '/deck/audio/' + st.slide;
  audio.play().then(function () {
    document.getElementById('speakBtn').className = 'chip on';
  }).catch(function () {
    document.getElementById('speakBtn').className = 'chip';
    openSheet('No narration yet', 'This slide has not been narrated. Run ' +
      'python3 -m onboarding.narrate on Main to generate it.');
  });
}

audio.onended = function () {
  document.getElementById('speakBtn').className = 'chip';
  if (auto && st.slide < DATA.slides.length - 1) {
    setTimeout(function () { if (auto) { go(1); speak(); } }, 1100);
  } else if (auto) {
    auto = false;
    document.getElementById('autoBtn').className = 'chip';
  }
};

/* -------------------------------------------------------------------- views */
function startScreen() {
  return '<div class="start">' +
    '<div class="mark"><i></i><span>Thunder</span></div>' +
    '<h1>' + esc(DATA.slides[0].title) + '</h1>' +
    '<div class="sub">' + DATA.slides.length + ' slides across ' + DATA.sections.length +
      ' chapters. Pick how much detail goes on the television — you can ' +
      'switch at any point, and either way your notes stay on this screen.</div>' +
    '<div class="pick">' +
      '<button class="hero" onclick="begin(false)">' +
        '<b>Quick tour</b><span>The short version. A few lines a slide, big enough ' +
        'to read across a room. <span class="meta">Best if you are talking over it.</span></span></button>' +
      '<button onclick="begin(true)">' +
        '<b>Full detail</b><span>Every slide expanded with the depth behind it. ' +
        '<span class="meta">Best if someone is reading it themselves.</span></span></button>' +
      '<button onclick="document.getElementById(\'tocBtn\').click()">' +
        '<b>Jump to a chapter</b><span>Skip straight to claims, security, or ' +
        'wherever the question lands.</span></button>' +
    '</div></div>';
}

function bullets(lines) {
  return '<ul>' + lines.map(function (line, i) {
    return '<li><s>' + String(i + 1).padStart(2, '0') + '</s><span>' + esc(line) + '</span></li>';
  }).join('') + '</ul>';
}

function statsBlock(stats) {
  return '<div class="stats">' + stats.map(function (s) {
    return '<div class="stat ' + (s.tone || '') + '"><b>' + esc(s.value) + '</b>' +
           (s.unit ? '<u>' + esc(s.unit) + '</u>' : '<u>&nbsp;</u>') +
           '<span>' + esc(s.label) + '</span></div>';
  }).join('') + '</div>';
}

function render() {
  const bar = document.getElementById('bar');
  const nav = document.getElementById('nav');
  const scroll = document.getElementById('scroll');

  if (!st.started) {
    document.documentElement.style.setProperty('--accent', DATA.accents[DATA.slides[0].section]);
    // Only Contents is useful before starting; the rest would act on nothing.
    ['autoBtn', 'speakBtn', 'detailBtn'].forEach(function (id) {
      document.getElementById(id).style.display = 'none';
    });
    nav.style.display = 'none';
    document.getElementById('rail').style.width = '0';
    scroll.innerHTML = startScreen();
    scroll.style.paddingBottom = '30px';
    return;
  }

  ['autoBtn', 'speakBtn', 'detailBtn'].forEach(function (id) {
    document.getElementById(id).style.display = '';
  });
  nav.style.display = '';
  scroll.style.paddingBottom = '122px';

  const s = DATA.slides[st.slide];
  const sec = DATA.sections.find(function (x) { return x.name === s.section; }) || {};
  document.documentElement.style.setProperty('--accent', DATA.accents[s.section] || '#C4A35A');

  const terms = (s.terms && s.terms.length)
    ? '<div class="termrow">' + s.terms.map(function (n) {
        return '<button class="term" onclick="defn(this)" data-t="' + esc(n) + '">' + esc(n) + '</button>';
      }).join('') + '</div>'
    : '<div class="next">Nothing to define on this one.</div>';

  const nxt = DATA.slides[st.slide + 1];

  scroll.innerHTML =
    '<div class="card slidecard">' +
      '<div class="chapter"><s>' + String(sec.number || 1).padStart(2, '0') +
        '</s><em></em><span>' + esc(s.section) + '  ·  ' +
        (st.slide + 1) + '/' + DATA.slides.length + '</span></div>' +
      '<h1>' + esc(s.title) + '</h1>' +
      ((s.layout === 'stats' && s.stats) ? statsBlock(s.stats) : '') +
      bullets(st.detail ? s.detail : s.short) +
    '</div>' +
    '<div class="label">Only you can see this<em></em></div>' +
    '<div class="notes">' + esc(s.notes) + '</div>' +
    '<div class="label">Tap for a definition<em></em></div>' + terms +
    '<div class="label">Coming up<em></em></div>' +
    '<div class="next">' + (nxt ? esc(nxt.title) : 'Last slide.') + '</div>';

  document.getElementById('detailBtn').className = 'chip' + (st.detail ? ' on' : '');
  document.getElementById('prev').disabled = st.slide === 0;
  document.getElementById('next-btn').disabled = st.slide === DATA.slides.length - 1;
  document.getElementById('rail').style.width =
    ((st.slide + 1) / DATA.slides.length * 100) + '%';
  scroll.scrollTop = 0;
}

function begin(detail) { post({ started: true, detail: detail, slide: 0 }); }
function defn(el) { const n = el.getAttribute('data-t'); openSheet(n, DATA.glossary[n] || ''); }

/* ------------------------------------------------------------------ wiring */
document.getElementById('prev').onclick = function () { go(-1); };
document.getElementById('next-btn').onclick = function () { go(1); };
document.getElementById('detailBtn').onclick = function () { post({ detail: !st.detail }); };
document.getElementById('speakBtn').onclick = function () {
  if (!audio.paused && audio.src) stopSpeaking(); else speak();
};
document.getElementById('autoBtn').onclick = function () {
  auto = !auto;
  this.className = 'chip' + (auto ? ' on' : '');
  if (auto) { if (!st.started) post({ started: true }); speak(); } else stopSpeaking();
};

document.getElementById('sheet').onclick = function () { this.classList.remove('open'); };
document.getElementById('toc').onclick = function (e) {
  if (e.target === this) this.classList.remove('open');
};

document.getElementById('tocBtn').onclick = function () {
  const list = document.getElementById('tocList');
  document.getElementById('tocNote').textContent =
    DATA.slides.length + ' slides in ' + DATA.sections.length + ' chapters. Tap one to go straight there.';
  list.innerHTML = '';
  DATA.sections.forEach(function (sec) {
    const cur = st.started && st.slide >= sec.first && st.slide < sec.first + sec.count;
    const b = document.createElement('button');
    b.className = 'chap' + (cur ? ' cur' : '');
    b.style.setProperty('--accent', sec.accent);
    b.innerHTML = '<span class="n" style="color:' + sec.accent + '">' +
      String(sec.number).padStart(2, '0') + '</span>' +
      '<span class="t"><b>' + esc(sec.name) + '</b><span>' + esc(sec.blurb) + '</span></span>' +
      '<span class="c">' + sec.count + '</span>';
    b.onclick = function () {
      document.getElementById('toc').classList.remove('open');
      jump(sec.first);
    };
    list.appendChild(b);
  });
  document.getElementById('toc').classList.add('open');
};

// Swipe left for the next slide, right to go back - on the whole page, because
// on a phone the thumb lands wherever it lands.
let x0 = null, y0 = null;
document.addEventListener('touchstart', function (e) {
  x0 = e.touches[0].clientX; y0 = e.touches[0].clientY;
}, { passive: true });
document.addEventListener('touchend', function (e) {
  if (x0 === null || !st.started) return;
  if (document.querySelector('.sheet.open')) return;
  const dx = e.changedTouches[0].clientX - x0;
  const dy = e.changedTouches[0].clientY - y0;
  // Horizontal has to clearly beat vertical, or scrolling the notes would
  // change slide halfway down a paragraph.
  if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.6) go(dx < 0 ? 1 : -1);
  x0 = null; y0 = null;
}, { passive: true });

// A keyboard, for rehearsing at the desk.
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.sheet.open').forEach(function (s) { s.classList.remove('open'); });
    return;
  }
  if (e.key === 'ArrowRight' || e.key === ' ') go(1);
  if (e.key === 'ArrowLeft') go(-1);
  if (e.key === 'd') post({ detail: !st.detail });
  if (e.key === 't') document.getElementById('tocBtn').click();
});

// Adopt whatever position the deck is already on, so opening the presenter view
// mid-talk does not yank the television back to the cover.
fetch('/deck/state', { cache: 'no-store' })
  .then(function (r) { return r.json(); })
  .then(function (s) {
    st.slide = s.slide; st.detail = s.detail; st.started = s.started;
    render();
  })
  .catch(render);
</script>
</body></html>
"""


def audience_html() -> str:
    return _AUDIENCE.replace("__CSS__", _CSS).replace(
        "__PAYLOAD__", _payload(audience=True))


def presenter_html() -> str:
    return _PRESENTER.replace("__CSS__", _CSS).replace(
        "__PAYLOAD__", _payload())
