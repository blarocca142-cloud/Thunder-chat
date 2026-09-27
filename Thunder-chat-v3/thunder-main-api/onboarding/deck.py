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
# Light, warm and confident. The first version was near-black with pastel
# accents, and the verdict was "dark", "underground" and "mid 2000s" - which was
# fair. Dark decks read as either a code editor or a nightclub, and this one has
# to read as a company. Paper background, deep ink, one strong chapter colour.
#
# The chapter accent arrives as --accent, set from JS on every slide change, so a
# single stylesheet recolours the wash, the rail, the numerals, the highlights
# and the dots together.
_CSS = r"""
:root {
  --paper:#FBF9F5; --paper-2:#F4F1EA; --card:#FFFFFF;
  --ink:#14161A; --ink-2:#4A5058; --ink-3:#8A9099;
  --line:#E4DFD5;
  --accent:#C2410C;
  --good:#047857; --bad:#BE123C;
  --shadow:0 1px 2px rgba(20,22,26,.04),0 8px 24px rgba(20,22,26,.06);
  --shadow-lg:0 2px 4px rgba(20,22,26,.04),0 18px 48px rgba(20,22,26,.09);
}
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
html,body { margin:0; height:100%; }
body {
  background:var(--paper);
  color:var(--ink);
  overflow:hidden;
  font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-feature-settings:"kern" 1,"liga" 1,"ss01" 1;
  -webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility;
}

/* A soft wash of the chapter colour, not a gradient you notice. Two very light
   tints high and low, so the page has depth without looking like a background
   image from a template. */
.bg { position:fixed; inset:0; pointer-events:none; overflow:hidden; }
.bg i {
  position:absolute; display:block; border-radius:50%; filter:blur(90px);
  width:70vmax; height:70vmax; opacity:.13;
  transition:background .8s ease;
}
.bg i:nth-child(1) { background:var(--accent); top:-32%; right:-18%; }
.bg i:nth-child(2) { background:var(--accent); bottom:-40%; left:-24%; opacity:.07; }

.rail { position:fixed; top:0; left:0; right:0; height:3px; z-index:6; background:var(--line); }
.rail b { display:block; height:100%; background:var(--accent); transition:width .5s cubic-bezier(.4,0,.2,1); }

.wrap { position:relative; z-index:3; height:100%; display:flex; flex-direction:column; }

/* Chapter line: a short accent rule, the number, the name. */
.chapter { display:flex; align-items:center; gap:.85em; color:var(--accent); font-weight:700; letter-spacing:.11em; text-transform:uppercase; }
.chapter em { display:block; height:2px; background:var(--accent); border-radius:2px; font-style:normal; flex:none; }
.chapter s { text-decoration:none; font-variant-numeric:tabular-nums; opacity:.55; }

h1 { margin:0; font-weight:800; letter-spacing:-.028em; line-height:1.02; color:var(--ink); text-wrap:balance; }
.sub { color:var(--ink-2); font-weight:400; }

ul { margin:0; padding:0; list-style:none; display:flex; flex-direction:column; }
li { display:flex; gap:.8em; align-items:flex-start; color:var(--ink-2); }
li > s { flex:none; text-decoration:none; color:var(--accent); font-variant-numeric:tabular-nums; font-weight:800; opacity:.5; }

/* The highlight. A marker-pen wash of the chapter colour, and the ink goes to
   full black inside it - this is the phrase the room should remember. */
mark {
  background:color-mix(in srgb,var(--accent) 15%,transparent);
  color:var(--ink); font-weight:680;
  padding:.04em .2em; margin:0 -.04em; border-radius:.2em;
  -webkit-box-decoration-break:clone; box-decoration-break:clone;
}

/* Numbers get to be numbers. */
.stats { display:flex; flex-wrap:wrap; }
.stat { flex:1 1 0; min-width:5.5em; }
.stat b { display:block; font-weight:800; letter-spacing:-.04em; line-height:.95; font-variant-numeric:tabular-nums; color:var(--ink); }
.stat.good b { color:var(--good); }
.stat.bad b { color:var(--bad); }
.stat u { display:block; text-decoration:none; color:var(--ink-3); font-weight:700; text-transform:uppercase; letter-spacing:.09em; }
.stat span { display:block; color:var(--ink-2); }
.stat hr { border:0; height:3px; border-radius:3px; background:var(--line); margin:0 0 .7em; width:2.4em; }
.stat.good hr { background:var(--good); }
.stat.bad hr { background:var(--bad); }

.fx { animation:rise .55s cubic-bezier(.16,1,.3,1) both; }
@keyframes rise { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:none; } }
@media (prefers-reduced-motion:reduce) { .fx { animation:none !important; } }

button { font:inherit; color:inherit; background:none; border:none; cursor:pointer; }
.mono { font-variant-numeric:tabular-nums; }
"""


# ------------------------------------------------------------- audience view
_AUDIENCE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#FBF9F5">
<title>Thunder</title>
<style>__CSS__
.wrap { padding:clamp(30px,5.5vh,72px) clamp(34px,6.5vw,120px) clamp(72px,10vh,110px); justify-content:center; }

/* The chapter number, oversized and almost invisible behind the slide. Gives the
   page a focal depth that a flat list of bullets never has. */
.ghost {
  position:absolute; top:clamp(10px,2vh,40px); right:clamp(26px,4vw,74px);
  font-size:clamp(90px,17vw,320px); font-weight:800; line-height:.8;
  color:var(--accent); opacity:.07; letter-spacing:-.05em;
  font-variant-numeric:tabular-nums; pointer-events:none; user-select:none;
}

.chapter { font-size:clamp(11px,1.15vw,17px); margin-bottom:clamp(14px,2.4vh,30px); }
.chapter em { width:clamp(22px,2.6vw,48px); }
h1 { font-size:clamp(31px,4.7vw,88px); }
.slide h1 { margin-bottom:clamp(20px,3.4vh,46px); }
ul { gap:clamp(13px,2.2vh,28px); }
li { font-size:clamp(17px,2.3vw,41px); line-height:1.3; }
li > s { font-size:.58em; padding-top:.34em; }
.detailed h1 { font-size:clamp(25px,3.5vw,64px); }
.detailed li { font-size:clamp(14px,1.62vw,29px); line-height:1.42; }
.detailed ul { gap:clamp(9px,1.5vh,19px); }

.stats { gap:clamp(18px,3vw,54px); margin-bottom:clamp(22px,3.4vh,44px); }
.stat b { font-size:clamp(36px,5.8vw,108px); }
.stat u { font-size:clamp(9px,.92vw,15px); margin-top:.6em; }
.stat span { font-size:clamp(12px,1.22vw,21px); margin-top:.45em; line-height:1.3; }
.detailed .stat b { font-size:clamp(27px,3.9vw,70px); }

/* Title card. */
.cover { display:flex; flex-direction:column; justify-content:center; height:100%; }
.mark { display:flex; align-items:center; gap:.7em; color:var(--accent); font-weight:800; letter-spacing:.3em; text-transform:uppercase; font-size:clamp(10px,1.05vw,16px); margin-bottom:clamp(22px,3.6vh,46px); }
.mark i { display:block; width:clamp(8px,.8vw,13px); height:clamp(8px,.8vw,13px); border-radius:50%; background:var(--accent); animation:pulse 2.8s ease-in-out infinite; }
@keyframes pulse { 50% { opacity:.3; transform:scale(.8); } }
.cover h1 { font-size:clamp(36px,6.6vw,128px); max-width:18em; }
.cover .sub { font-size:clamp(15px,1.9vw,33px); margin-top:clamp(18px,2.8vh,36px); max-width:28em; line-height:1.42; }
.cover .hint { margin-top:clamp(28px,4.6vh,60px); color:var(--ink-3); font-size:clamp(11px,1.15vw,18px); }
.cover .hint b { color:var(--accent); font-weight:700; }

/* Position, as chapter-grouped ticks. Twenty-three dots in ten groups tells you
   where you are and how much of this chapter is left, which a "4 / 23" cannot. */
.dots { position:absolute; left:clamp(34px,6.5vw,120px); bottom:clamp(30px,4.4vh,54px); display:flex; align-items:center; gap:clamp(7px,.75vw,13px); }
.dots .grp { display:flex; gap:clamp(3px,.3vw,5px); }
.dots span { display:block; width:clamp(5px,.5vw,9px); height:clamp(5px,.5vw,9px); border-radius:99px; background:var(--line); transition:all .4s ease; }
.dots span.past { background:var(--ink-3); opacity:.5; }
.dots span.cur { background:var(--accent); width:clamp(17px,1.7vw,30px); }

.foot { position:absolute; right:clamp(34px,6.5vw,120px); bottom:clamp(28px,4.2vh,52px); text-align:right; font-size:clamp(10px,1.02vw,16px); color:var(--ink-3); z-index:4; }
.foot .now { color:var(--ink-2); font-weight:650; display:block; }
.offline { color:var(--bad); }

@media (max-aspect-ratio:1/1) {
  h1 { font-size:clamp(28px,7.6vw,58px); }
  .cover h1 { font-size:clamp(33px,9.2vw,70px); }
  li { font-size:clamp(16px,4.4vw,30px); }
  .detailed li { font-size:clamp(13px,3.6vw,24px); }
  .chapter { font-size:clamp(10px,2.7vw,15px); }
  .stat b { font-size:clamp(30px,9.4vw,58px); }
  .stats { gap:20px; }
  .ghost { font-size:26vw; }
  .foot { font-size:clamp(10px,2.6vw,14px); }
}
</style></head>
<body>
<div class="bg"><i></i><i></i></div>
<div class="rail"><b id="rail" style="width:0"></b></div>
<div class="wrap" id="wrap"><div id="stage"></div></div>
<div class="dots" id="dots"></div>
<div class="foot">
  <span class="now" id="count"></span>
  <span id="brand">Made by Thunder &middot; our own hardware</span>
</div>
<script>
const DATA = __PAYLOAD__;
let rev = -1, failures = 0;

function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

/* *phrase* becomes a highlighted phrase. content.py validates that the markers
   pair up, so an odd one cannot reach here and highlight the rest of the line. */
function rich(text) {
  const parts = String(text).split('*');
  let out = '';
  for (let i = 0; i < parts.length; i++) {
    out += (i % 2) ? '<mark>' + esc(parts[i]) + '</mark>' : esc(parts[i]);
  }
  return out;
}

function bullets(lines) {
  return '<ul>' + lines.map(function (line, i) {
    return '<li class="fx" style="animation-delay:' + (110 + i * 80) + 'ms">' +
           '<s>' + String(i + 1).padStart(2, '0') + '</s><span>' + rich(line) + '</span></li>';
  }).join('') + '</ul>';
}

function statsBlock(stats) {
  return '<div class="stats">' + stats.map(function (s, i) {
    return '<div class="stat ' + (s.tone || '') + ' fx" style="animation-delay:' + (110 + i * 100) + 'ms">' +
           '<hr><b>' + esc(s.value) + '</b>' +
           (s.unit ? '<u>' + esc(s.unit) + '</u>' : '<u>&nbsp;</u>') +
           '<span>' + esc(s.label) + '</span></div>';
  }).join('') + '</div>';
}

function dots(slide, started) {
  const box = document.getElementById('dots');
  if (!started) { box.innerHTML = ''; return; }
  box.innerHTML = DATA.sections.map(function (sec) {
    let g = '';
    for (let i = sec.first; i < sec.first + sec.count; i++) {
      g += '<span class="' + (i === slide ? 'cur' : (i < slide ? 'past' : '')) + '"></span>';
    }
    return '<span class="grp">' + g + '</span>';
  }).join('');
}

function cover() {
  const s = DATA.slides[0];
  return '<div class="cover">' +
    '<div class="mark fx"><i></i><span>Thunder</span></div>' +
    '<h1 class="fx" style="animation-delay:90ms">' + esc(s.title) + '</h1>' +
    '<div class="sub fx" style="animation-delay:200ms">Six computers in a house, running our own AI. ' +
      'Nothing we do leaves the building.</div>' +
    '<div class="hint fx" style="animation-delay:320ms">Choose <b>Quick tour</b> or <b>Full detail</b> to begin</div>' +
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
    dots(0, false);
    return;
  }

  const s = DATA.slides[st.slide];
  if (!s) return;
  const sec = DATA.sections.find(function (x) { return x.name === s.section; }) || {};
  document.documentElement.style.setProperty('--accent', DATA.accents[s.section] || '#C2410C');
  wrap.className = 'wrap' + (st.detail ? ' detailed' : '');

  const n = String(sec.number || 1).padStart(2, '0');
  stage.innerHTML =
    '<div class="ghost">' + n + '</div>' +
    '<div class="slide">' +
      '<div class="chapter fx"><em></em><s>' + n + '</s><span>' + esc(s.section) + '</span></div>' +
      '<h1 class="fx" style="animation-delay:70ms">' + rich(s.title) + '</h1>' +
      ((s.layout === 'stats' && s.stats) ? statsBlock(s.stats) : '') +
      bullets(st.detail ? s.detail : s.short) +
    '</div>';

  document.getElementById('count').textContent = (st.slide + 1) + ' / ' + DATA.slides.length;
  document.getElementById('rail').style.width =
    ((st.slide + 1) / DATA.slides.length * 100) + '%';
  dots(st.slide, true);
}

async function poll() {
  try {
    const r = await fetch('/deck/state', { cache: 'no-store' });
    const st = await r.json();
    failures = 0;
    const brand = document.getElementById('brand');
    brand.classList.remove('offline');
    brand.textContent = 'Made by Thunder · our own hardware';
    if (st.rev !== rev) { rev = st.rev; render(st); }
  } catch (e) {
    // Say so on the third miss, not the first: one dropped poll on wifi is
    // normal, and a warning that flickers is worse than no warning.
    if (++failures >= 3) {
      const brand = document.getElementById('brand');
      brand.classList.add('offline');
      brand.textContent = 'Lost the presenter';
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
<meta name="theme-color" content="#FBF9F5">
<title>Thunder &middot; presenter</title>
<style>__CSS__
.bar { display:flex; align-items:center; gap:6px; padding:12px 13px 10px; overflow-x:auto; scrollbar-width:none; }
.bar::-webkit-scrollbar { display:none; }
.bar .who { font-size:10px; letter-spacing:.18em; text-transform:uppercase; color:var(--accent); font-weight:800; flex:none; }
.bar .sp { flex:1; min-width:4px; }
.chip { background:var(--card); border:1px solid var(--line); border-radius:999px; padding:8px 13px; font-size:12px; color:var(--ink-2); font-weight:650; flex:none; box-shadow:var(--shadow); }
.chip.on { background:var(--accent); border-color:var(--accent); color:#fff; }
.scroll { flex:1; overflow-y:auto; overscroll-behavior:contain; padding:4px 13px 124px; }

.slidecard { background:var(--card); border:1px solid var(--line); border-radius:18px; padding:17px; box-shadow:var(--shadow); }
.slidecard .chapter { font-size:10px; margin-bottom:12px; }
.slidecard .chapter em { width:20px; }
.slidecard h1 { font-size:23px; margin-bottom:14px; }
.slidecard ul { gap:11px; }
.slidecard li { font-size:14px; line-height:1.45; }
.slidecard li > s { font-size:.7em; padding-top:.3em; }
.slidecard .stats { gap:14px; margin-bottom:15px; }
.slidecard .stat { min-width:4.4em; }
.slidecard .stat hr { width:1.6em; height:2px; margin-bottom:.5em; }
.slidecard .stat b { font-size:27px; }
.slidecard .stat u { font-size:8px; margin-top:.45em; }
.slidecard .stat span { font-size:11px; margin-top:.3em; line-height:1.25; }

.label { color:var(--accent); font-size:10px; letter-spacing:.18em; text-transform:uppercase; font-weight:800; margin:22px 0 9px; display:flex; align-items:center; gap:9px; }
.label em { flex:1; height:1px; background:var(--line); font-style:normal; }
.notes { background:var(--card); border:1px solid var(--line); border-left:3px solid var(--accent); border-radius:6px 16px 16px 6px; padding:15px; font-size:15px; line-height:1.58; color:var(--ink); box-shadow:var(--shadow); }
.next { color:var(--ink-2); font-size:13px; line-height:1.5; }
.termrow { display:flex; flex-wrap:wrap; gap:8px; }
.termrow button { background:var(--card); border:1px solid var(--line); border-bottom:2px solid var(--accent); border-radius:10px; padding:8px 12px; font-size:13px; color:var(--ink); font-weight:600; box-shadow:var(--shadow); }

.nav { position:fixed; left:0; right:0; bottom:0; display:flex; gap:9px; padding:11px 13px calc(11px + env(safe-area-inset-bottom)); background:linear-gradient(to top,var(--paper) 72%,rgba(251,249,245,.86)); border-top:1px solid var(--line); z-index:8; }
.nav button { flex:1; background:var(--card); border:1px solid var(--line); border-radius:14px; padding:15px 0; font-size:15px; font-weight:700; box-shadow:var(--shadow); }
.nav button.primary { background:var(--accent); border-color:var(--accent); color:#fff; flex:1.8; }
.nav button:disabled { opacity:.35; box-shadow:none; }

.sheet { position:fixed; inset:0; background:rgba(20,22,26,.4); backdrop-filter:blur(5px); display:none; align-items:flex-end; z-index:20; }
.sheet.open { display:flex; animation:fadein .2s ease; }
@keyframes fadein { from { opacity:0; } }
.sheetbody { background:var(--paper); border-top:1px solid var(--line); width:100%; max-height:84vh; overflow-y:auto; border-radius:22px 22px 0 0; padding:18px 16px calc(24px + env(safe-area-inset-bottom)); box-shadow:var(--shadow-lg); animation:up .28s cubic-bezier(.16,1,.3,1); }
@keyframes up { from { transform:translateY(28px); } }
.sheetbody h2 { margin:0 0 9px; font-size:19px; color:var(--ink); letter-spacing:-.015em; }
.sheetbody p { font-size:15px; line-height:1.6; margin:0; color:var(--ink-2); }
.grip { width:38px; height:4px; border-radius:99px; background:var(--line); margin:0 auto 16px; }
.note { color:var(--ink-3); font-size:12px; margin-bottom:15px; line-height:1.45; }

/* Contents: chapters, not 23 slides. */
.chap { display:flex; align-items:center; gap:13px; width:100%; text-align:left; padding:13px 13px; border-radius:14px; border:1px solid var(--line); background:var(--card); margin-bottom:9px; box-shadow:var(--shadow); }
.chap.cur { border-color:var(--accent); border-width:2px; }
.chap .n { font-size:13px; font-weight:800; font-variant-numeric:tabular-nums; width:23px; flex:none; }
.chap .t { flex:1; }
.chap .t b { display:block; font-size:15px; font-weight:700; color:var(--ink); }
.chap .t span { display:block; font-size:12px; color:var(--ink-3); margin-top:2px; line-height:1.35; }
.chap .c { font-size:11px; color:var(--ink-3); flex:none; font-variant-numeric:tabular-nums; }

/* Voice picker. */
.vrow { display:flex; align-items:center; gap:11px; width:100%; padding:12px 13px; border-radius:13px; border:1px solid var(--line); background:var(--card); margin-bottom:8px; box-shadow:var(--shadow); }
.vrow.cur { border-color:var(--accent); border-width:2px; }
.vrow .t { flex:1; text-align:left; }
.vrow .t b { display:block; font-size:15px; font-weight:700; color:var(--ink); }
.vrow .t span { display:block; font-size:12px; color:var(--ink-3); margin-top:2px; }
.vrow .play { flex:none; width:38px; height:38px; border-radius:50%; background:var(--accent); color:#fff; font-size:14px; font-weight:800; }
.vrow .use { flex:none; font-size:12px; font-weight:700; color:var(--accent); padding:8px 10px; }
.prog { height:6px; border-radius:99px; background:var(--line); overflow:hidden; margin:12px 0 4px; }
.prog b { display:block; height:100%; background:var(--accent); transition:width .3s ease; }

/* The opening choice. */
.start { padding:24px 16px 28px; }
.start .mark { display:flex; align-items:center; gap:.7em; color:var(--accent); font-weight:800; letter-spacing:.26em; text-transform:uppercase; font-size:10px; margin-bottom:18px; }
.start .mark i { width:9px; height:9px; border-radius:50%; background:var(--accent); }
.start h1 { font-size:28px; margin-bottom:12px; }
.start .sub { font-size:14px; line-height:1.55; margin-bottom:22px; }
.pick { display:flex; flex-direction:column; gap:10px; }
.pick button { text-align:left; padding:17px 16px; border-radius:16px; border:1px solid var(--line); background:var(--card); box-shadow:var(--shadow); }
.pick button.hero { border-color:var(--accent); border-width:2px; }
.pick b { display:block; font-size:16px; font-weight:750; margin-bottom:4px; color:var(--ink); }
.pick span { display:block; font-size:12.5px; color:var(--ink-2); line-height:1.45; }
.pick .meta { color:var(--accent); font-weight:700; }
</style></head>
<body>
<div class="bg"><i></i><i></i></div>
<div class="rail"><b id="rail" style="width:0"></b></div>

<div class="wrap">
  <div class="bar" id="bar">
    <span class="who">Presenter</span>
    <span class="sp"></span>
    <button class="chip" id="autoBtn">Auto</button>
    <button class="chip" id="speakBtn">Read</button>
    <button class="chip" id="voiceBtn">Voice</button>
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
  <div class="grip"></div><h2 id="sheetTitle"></h2><p id="sheetText"></p>
</div></div>

<div class="sheet" id="toc"><div class="sheetbody">
  <div class="grip"></div><h2>Contents</h2>
  <div class="note" id="tocNote"></div>
  <div id="tocList"></div>
</div></div>

<div class="sheet" id="voices"><div class="sheetbody">
  <div class="grip"></div><h2>Narrator</h2>
  <div class="note">Every voice reads the same line, so the seconds are pure pace.
    Tap the circle to hear it. "Use this" re-narrates all 23 slides on Main -
    about a minute.</div>
  <div id="voiceList"></div>
  <div id="voiceProg" style="display:none">
    <div class="prog"><b id="voiceBar" style="width:0"></b></div>
    <div class="note" id="voiceStatus"></div>
  </div>
</div></div>

<script>
const DATA = __PAYLOAD__;
let st = { slide: 0, detail: false, started: false };

function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

function rich(text) {
  const parts = String(text).split('*');
  let out = '';
  for (let i = 0; i < parts.length; i++) {
    out += (i % 2) ? '<mark>' + esc(parts[i]) + '</mark>' : esc(parts[i]);
  }
  return out;
}

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

function jump(i) { if (!auto) stopSpeaking(); post({ slide: i, started: true }); }

function openSheet(title, text) {
  document.getElementById('sheetTitle').textContent = title;
  document.getElementById('sheetText').textContent = text;
  document.getElementById('sheet').classList.add('open');
}
function closeSheets() {
  document.querySelectorAll('.sheet.open').forEach(function (s) { s.classList.remove('open'); });
}

/* ---------------------------------------------------------------- narration */
const audio = new Audio();
const sampler = new Audio();
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
    openSheet('No narration yet', 'This slide has not been narrated. Pick a ' +
      'voice under Voice, or run python3 -m onboarding.narrate on Main.');
  });
}

audio.onended = function () {
  document.getElementById('speakBtn').className = 'chip';
  if (auto && st.slide < DATA.slides.length - 1) {
    setTimeout(function () { if (auto) { go(1); speak(); } }, 1000);
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
      ' chapters. Pick how much detail goes on the television — you can switch ' +
      'at any point, and either way your notes stay on this screen.</div>' +
    '<div class="pick">' +
      '<button class="hero" onclick="begin(false)">' +
        '<b>Quick tour</b><span>The short version. A few lines a slide, big enough to ' +
        'read across a room. <span class="meta">Best if you are talking over it.</span></span></button>' +
      '<button onclick="begin(true)">' +
        '<b>Full detail</b><span>Every slide expanded with the depth behind it. ' +
        '<span class="meta">Best if someone is reading it themselves.</span></span></button>' +
      '<button onclick="document.getElementById(\'tocBtn\').click()">' +
        '<b>Jump to a chapter</b><span>Skip straight to claims, security, or wherever ' +
        'the question lands.</span></button>' +
    '</div></div>';
}

function bullets(lines) {
  return '<ul>' + lines.map(function (line, i) {
    return '<li><s>' + String(i + 1).padStart(2, '0') + '</s><span>' + rich(line) + '</span></li>';
  }).join('') + '</ul>';
}

function statsBlock(stats) {
  return '<div class="stats">' + stats.map(function (s) {
    return '<div class="stat ' + (s.tone || '') + '"><hr><b>' + esc(s.value) + '</b>' +
           (s.unit ? '<u>' + esc(s.unit) + '</u>' : '<u>&nbsp;</u>') +
           '<span>' + esc(s.label) + '</span></div>';
  }).join('') + '</div>';
}

function render() {
  const nav = document.getElementById('nav');
  const scroll = document.getElementById('scroll');
  const hideable = ['autoBtn', 'speakBtn', 'detailBtn'];

  if (!st.started) {
    document.documentElement.style.setProperty('--accent', DATA.accents[DATA.slides[0].section]);
    // Only Voice and Contents do anything before starting.
    hideable.forEach(function (id) { document.getElementById(id).style.display = 'none'; });
    nav.style.display = 'none';
    document.getElementById('rail').style.width = '0';
    scroll.innerHTML = startScreen();
    scroll.style.paddingBottom = '30px';
    return;
  }

  hideable.forEach(function (id) { document.getElementById(id).style.display = ''; });
  nav.style.display = '';
  scroll.style.paddingBottom = '124px';

  const s = DATA.slides[st.slide];
  const sec = DATA.sections.find(function (x) { return x.name === s.section; }) || {};
  document.documentElement.style.setProperty('--accent', DATA.accents[s.section] || '#C2410C');

  const terms = (s.terms && s.terms.length)
    ? '<div class="termrow">' + s.terms.map(function (n) {
        return '<button onclick="defn(this)" data-t="' + esc(n) + '">' + esc(n) + '</button>';
      }).join('') + '</div>'
    : '<div class="next">Nothing to define on this one.</div>';
  const nxt = DATA.slides[st.slide + 1];
  const n = String(sec.number || 1).padStart(2, '0');

  scroll.innerHTML =
    '<div class="slidecard">' +
      '<div class="chapter"><em></em><s>' + n + '</s><span>' + esc(s.section) +
        '  ·  ' + (st.slide + 1) + '/' + DATA.slides.length + '</span></div>' +
      '<h1>' + rich(s.title) + '</h1>' +
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
function defn(el) { const k = el.getAttribute('data-t'); openSheet(k, DATA.glossary[k] || ''); }

/* ---------------------------------------------------------- voice selection */
let voiceData = null;

function playSample(v) {
  sampler.pause();
  sampler.src = '/deck/voice-sample/' + v;
  sampler.play().catch(function () {
    openSheet('Could not play that', 'Main may still be synthesising the sample. Try again.');
  });
}

function useVoice(v) {
  fetch('/deck/narrate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ voice: v })
  }).then(function () {
    document.getElementById('voiceProg').style.display = '';
    pollNarrate();
  });
}

function pollNarrate() {
  fetch('/deck/narrate/status', { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (p) {
      const pct = p.total ? (p.done / p.total * 100) : 0;
      document.getElementById('voiceBar').style.width = pct + '%';
      document.getElementById('voiceStatus').textContent = p.error
        ? ('Failed: ' + p.error)
        : (p.running ? ('Narrating ' + p.done + ' of ' + p.total + ' in ' + p.voice + '…')
                     : (p.done ? ('Done — ' + p.done + ' slides in ' + p.voice + '.') : ''));
      if (p.running) setTimeout(pollNarrate, 1200);
      else if (!p.error) { voiceData = null; renderVoices(); }
    })
    .catch(function () { /* leave the last message up */ });
}

function renderVoices() {
  const list = document.getElementById('voiceList');
  if (!voiceData) {
    fetch('/deck/voices', { cache: 'no-store' })
      .then(function (r) { return r.json(); })
      .then(function (d) { voiceData = d; renderVoices(); });
    list.innerHTML = '<div class="note">Loading voices…</div>';
    return;
  }
  list.innerHTML = '';
  voiceData.choices.forEach(function (c) {
    const row = document.createElement('div');
    row.className = 'vrow' + (c.voice === voiceData.current ? ' cur' : '');
    row.innerHTML =
      '<button class="play">&#9654;</button>' +
      '<span class="t"><b>' + esc(c.name) + '</b><span>' + esc(c.note) + '</span></span>' +
      (c.voice === voiceData.current ? '<span class="use">in use</span>'
                                     : '<button class="use">Use this</button>');
    row.querySelector('.play').onclick = function () { playSample(c.voice); };
    const use = row.querySelector('button.use');
    if (use) use.onclick = function () { useVoice(c.voice); };
    list.appendChild(row);
  });
}

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
document.getElementById('voiceBtn').onclick = function () {
  renderVoices();
  document.getElementById('voices').classList.add('open');
};

document.getElementById('sheet').onclick = function () { this.classList.remove('open'); };
['toc', 'voices'].forEach(function (id) {
  document.getElementById(id).onclick = function (e) {
    if (e.target === this) this.classList.remove('open');
  };
});

document.getElementById('tocBtn').onclick = function () {
  const list = document.getElementById('tocList');
  document.getElementById('tocNote').textContent =
    DATA.slides.length + ' slides in ' + DATA.sections.length + ' chapters. Tap one to go straight there.';
  list.innerHTML = '';
  DATA.sections.forEach(function (sec) {
    const cur = st.started && st.slide >= sec.first && st.slide < sec.first + sec.count;
    const b = document.createElement('button');
    b.className = 'chap' + (cur ? ' cur' : '');
    b.style.borderColor = cur ? sec.accent : '';
    b.innerHTML = '<span class="n" style="color:' + sec.accent + '">' +
      String(sec.number).padStart(2, '0') + '</span>' +
      '<span class="t"><b>' + esc(sec.name) + '</b><span>' + esc(sec.blurb) + '</span></span>' +
      '<span class="c">' + sec.count + '</span>';
    b.onclick = function () { closeSheets(); jump(sec.first); };
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
  if (e.key === 'Escape') { closeSheets(); return; }
  if (e.key === 'ArrowRight' || e.key === ' ') go(1);
  if (e.key === 'ArrowLeft') go(-1);
  if (e.key === 'd') post({ detail: !st.detail });
  if (e.key === 't') document.getElementById('tocBtn').click();
  if (e.key === 'v') document.getElementById('voiceBtn').click();
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
