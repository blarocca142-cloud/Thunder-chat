"""Two views of one deck, so the presenter notes never reach the television.

This is the whole architectural reason the deck is not a single page. Casting
from Android mirrors a browser tab: whatever is in the tab is on the TV. So any
design where the notes live in the same view as the slide - hidden panel,
collapsed drawer, small text, doesn't matter - puts the notes on the screen the
moment they are useful.

    /deck            the audience view. Cast this one. Slide only.
    /deck/presenter  the phone. Same slide, plus notes, glossary and contents.
    /deck/state      the shared position, so moving one moves the other.

The presenter drives; the audience view polls. Polling rather than a websocket
because the whole thing has to survive a phone locking, a tab being backgrounded
on a Chromecast, and wifi hiccuping mid-sentence - a poll recovers from all
three by itself, and a socket needs reconnect logic to do the same job.

Two implementation notes worth keeping:

**The templates are raw strings and never f-strings.** CSS and JS are full of
braces, and an f-string would try to read them as fields. Substitution is done
with .replace() on explicit placeholders instead.

**No backslash escapes in the JavaScript.** A `\\n` written in an ordinary
triple-quoted Python string becomes a real newline before the browser ever sees
it, which breaks the JS string it was sitting in, which breaks the parse, which
silently kills every script on the page. That exact bug cost an evening on the
Odris dashboard.
"""
from __future__ import annotations

import json
import threading

from . import content

# The position both views agree on. In memory on purpose: a talk is a session,
# and a deck that reopens on slide 14 tomorrow because that is where it was left
# is a worse default than reopening at the start.
_state = {"slide": 0, "detail": False, "rev": 0}
_lock = threading.Lock()


def get_state() -> dict:
    with _lock:
        return dict(_state)


def set_state(slide: int | None = None, detail: bool | None = None) -> dict:
    """`rev` increments on every change so the audience view can tell a real
    move from a poll that happened to land between two identical answers."""
    with _lock:
        if slide is not None:
            _state["slide"] = max(0, min(int(slide), len(content.SLIDES) - 1))
        if detail is not None:
            _state["detail"] = bool(detail)
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
    if audience:
        slides = [{"section": s["section"], "title": s["title"],
                   "short": s["short"], "detail": s["detail"]}
                  for s in content.SLIDES]
        data = {"slides": slides, "glossary": {},
                "sections": content.sections_with_slides()}
    else:
        data = {"slides": content.SLIDES, "glossary": content.GLOSSARY,
                "sections": content.sections_with_slides()}
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


# --------------------------------------------------------------------- styling
# Thunder's palette, because the deck is a demo of Thunder and should look like
# it. Sizes are set for a television across a room, not a laptop at arm's length.
_CSS = r"""
:root {
  --slate-top:#2C3340; --slate-mid:#1E232B; --slate-deep:#16191F;
  --surface:#252A33; --ink:#EDE8DF; --mute:#9A948A;
  --gold:#C4A35A; --gold-soft:#B8924A; --live:#8FCB9B; --crit:#D9534F;
}
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
html,body { margin:0; height:100%; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
body {
  background:linear-gradient(180deg,var(--slate-top) 0%,var(--slate-mid) 38%,var(--slate-deep) 100%);
  color:var(--ink); overflow:hidden;
}
.bloom {
  position:fixed; left:50%; top:18%; width:120vmin; height:120vmin;
  transform:translate(-50%,-50%); pointer-events:none;
  background:radial-gradient(circle,rgba(196,163,90,.16) 0%,rgba(196,163,90,.05) 45%,transparent 70%);
}
.wrap { position:relative; height:100%; display:flex; flex-direction:column; }
.eyebrow { color:var(--gold); text-transform:uppercase; letter-spacing:.16em; font-weight:600; }
h1 { margin:0; line-height:1.1; font-weight:700; }
ul { margin:0; padding:0; list-style:none; }
li { display:flex; gap:.7em; align-items:flex-start; }
li .dot { color:var(--gold); flex:none; }
.count { color:var(--mute); }
.fade { animation:fade .35s ease; }
@keyframes fade { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:none; } }
button { font:inherit; color:inherit; background:none; border:none; cursor:pointer; }
.term { color:var(--gold); border-bottom:1px dotted var(--gold-soft); cursor:pointer; }
"""


# ------------------------------------------------------------- audience view
_AUDIENCE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Thunder</title>
<style>__CSS__
.wrap { padding:6vh 7vw; justify-content:center; }
.eyebrow { font-size:1.6vw; margin-bottom:2.2vh; }
h1 { font-size:5.0vw; margin-bottom:4vh; }
ul { display:flex; flex-direction:column; gap:2.2vh; }
li { font-size:2.5vw; line-height:1.35; }
.foot { position:absolute; left:7vw; right:7vw; bottom:3vh; display:flex; justify-content:space-between; font-size:1.3vw; }
.detailed h1 { font-size:4.0vw; margin-bottom:3vh; }
.detailed li { font-size:1.85vw; line-height:1.4; }
.detailed ul { gap:1.6vh; }
.offline { color:var(--crit); }
/* A phone held up as a second screen still gets something readable. */
@media (max-aspect-ratio:1/1) {
  .eyebrow { font-size:3.4vw; } h1 { font-size:8vw; } li { font-size:4.4vw; }
  .detailed h1 { font-size:6.5vw; } .detailed li { font-size:3.6vw; }
  .foot { font-size:3vw; }
}
</style></head>
<body>
<div class="bloom"></div>
<div class="wrap" id="wrap">
  <div class="eyebrow" id="section"></div>
  <h1 id="title"></h1>
  <ul id="body"></ul>
  <div class="foot">
    <span class="count" id="count"></span>
    <span class="count" id="brand">Made by Thunder &middot; running on our own hardware</span>
  </div>
</div>
<script>
const DATA = __PAYLOAD__;
let rev = -1, failures = 0;

function render(st) {
  const s = DATA.slides[st.slide];
  if (!s) return;
  document.getElementById('wrap').className = 'wrap' + (st.detail ? ' detailed' : '');
  document.getElementById('section').textContent = s.section;
  document.getElementById('title').textContent = s.title;
  const body = document.getElementById('body');
  body.innerHTML = '';
  (st.detail ? s.detail : s.short).forEach(function (line) {
    const li = document.createElement('li');
    const dot = document.createElement('span');
    dot.className = 'dot'; dot.textContent = '▸';
    const txt = document.createElement('span');
    txt.textContent = line;
    li.appendChild(dot); li.appendChild(txt);
    body.appendChild(li);
  });
  document.getElementById('count').textContent =
    (st.slide + 1) + ' / ' + DATA.slides.length;
  const w = document.getElementById('wrap');
  w.classList.remove('fade'); void w.offsetWidth; w.classList.add('fade');
}

async function poll() {
  try {
    const r = await fetch('/deck/state', { cache: 'no-store' });
    const st = await r.json();
    failures = 0;
    document.getElementById('brand').classList.remove('offline');
    if (st.rev !== rev) { rev = st.rev; render(st); }
  } catch (e) {
    // Say so on the third miss, not the first: one dropped poll on wifi is
    // normal and a warning that flickers is worse than no warning.
    if (++failures >= 3) {
      document.getElementById('brand').classList.add('offline');
      document.getElementById('brand').textContent = 'Lost the presenter - still on slide ' + (rev >= 0 ? '' : '?');
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
<title>Thunder &middot; presenter</title>
<style>__CSS__
.wrap { padding:0; }
.bar { display:flex; align-items:center; gap:10px; padding:12px 14px; background:rgba(0,0,0,.25); }
.bar .who { font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--gold); font-weight:700; }
.bar .sp { flex:1; }
.chip { background:var(--surface); border-radius:999px; padding:7px 13px; font-size:12px; color:var(--mute); }
.chip.on { background:var(--gold); color:#16191F; font-weight:700; }
.scroll { flex:1; overflow-y:auto; padding:16px 16px 120px; }
.slidecard { background:var(--surface); border-radius:16px; padding:16px; }
.slidecard .eyebrow { font-size:10px; margin-bottom:8px; }
.slidecard h1 { font-size:21px; margin-bottom:12px; }
.slidecard li { font-size:14px; line-height:1.45; margin-bottom:9px; }
.label { color:var(--gold); font-size:11px; letter-spacing:.14em; text-transform:uppercase; font-weight:700; margin:20px 0 8px; }
.notes { background:rgba(196,163,90,.10); border-left:3px solid var(--gold); border-radius:0 12px 12px 0; padding:14px; font-size:15px; line-height:1.55; }
.next { color:var(--mute); font-size:13px; }
.nav { position:fixed; left:0; right:0; bottom:0; display:flex; gap:10px; padding:12px 14px calc(12px + env(safe-area-inset-bottom)); background:rgba(22,25,31,.96); border-top:1px solid #3A414D; }
.nav button { flex:1; background:var(--surface); border-radius:12px; padding:15px 0; font-size:15px; font-weight:600; }
.nav button.primary { background:var(--gold); color:#16191F; }
.nav button:disabled { opacity:.35; }
.sheet { position:fixed; inset:0; background:rgba(0,0,0,.62); display:none; align-items:flex-end; z-index:10; }
.sheet.open { display:flex; }
.sheetbody { background:var(--slate-mid); width:100%; max-height:76vh; overflow-y:auto; border-radius:18px 18px 0 0; padding:18px 18px calc(18px + env(safe-area-inset-bottom)); }
.sheetbody h2 { margin:0 0 10px; font-size:17px; color:var(--gold); }
.sheetbody p { font-size:15px; line-height:1.55; margin:0; }
.toc button { display:block; width:100%; text-align:left; padding:13px 10px; border-bottom:1px solid #333A45; font-size:15px; }
.toc button .n { color:var(--mute); font-size:12px; }
.toc button.cur { color:var(--gold); font-weight:700; }
</style></head>
<body>
<div class="wrap">
  <div class="bar">
    <span class="who">Presenter</span>
    <span class="sp"></span>
    <button class="chip" id="autoBtn">Auto</button>
    <button class="chip" id="speakBtn">Read</button>
    <button class="chip" id="detailBtn">Detail</button>
    <button class="chip" id="tocBtn">Contents</button>
  </div>
  <div class="scroll" id="scroll">
    <div class="slidecard">
      <div class="eyebrow" id="section"></div>
      <h1 id="title"></h1>
      <ul id="body"></ul>
    </div>
    <div class="label">Only you can see this</div>
    <div class="notes" id="notes"></div>
    <div class="label">Tap for a definition</div>
    <div id="terms" class="next"></div>
    <div class="label">Coming up</div>
    <div class="next" id="next"></div>
  </div>
  <div class="nav">
    <button id="prev">&larr; Back</button>
    <button id="next-btn" class="primary">Next &rarr;</button>
  </div>
</div>

<div class="sheet" id="sheet"><div class="sheetbody">
  <h2 id="sheetTitle"></h2>
  <p id="sheetText"></p>
</div></div>

<div class="sheet" id="toc"><div class="sheetbody toc" id="tocList"></div></div>

<script>
const DATA = __PAYLOAD__;
let st = { slide: 0, detail: false };

function post(patch) {
  Object.assign(st, patch);
  render();
  fetch('/deck/state', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slide: st.slide, detail: st.detail })
  }).catch(function () { /* the view is already right; the TV catches up */ });
}

function go(delta) {
  const n = st.slide + delta;
  if (n < 0 || n >= DATA.slides.length) return;
  // Moving by hand cuts the narration off. In auto mode the move IS the
  // narration advancing, so leave it alone there.
  if (!auto) stopSpeaking();
  post({ slide: n });
}

function openSheet(title, text) {
  document.getElementById('sheetTitle').textContent = title;
  document.getElementById('sheetText').textContent = text;
  document.getElementById('sheet').classList.add('open');
}

function render() {
  const s = DATA.slides[st.slide];
  document.getElementById('section').textContent =
    s.section + '  ·  ' + (st.slide + 1) + ' of ' + DATA.slides.length;
  document.getElementById('title').textContent = s.title;

  const body = document.getElementById('body');
  body.innerHTML = '';
  (st.detail ? s.detail : s.short).forEach(function (line) {
    const li = document.createElement('li');
    const d = document.createElement('span'); d.className = 'dot'; d.textContent = '▸';
    const t = document.createElement('span'); t.textContent = line;
    li.appendChild(d); li.appendChild(t); body.appendChild(li);
  });

  document.getElementById('notes').textContent = s.notes;

  const terms = document.getElementById('terms');
  terms.innerHTML = '';
  if (!s.terms || !s.terms.length) {
    terms.textContent = 'Nothing to define on this one.';
  } else {
    s.terms.forEach(function (name, i) {
      if (i) terms.appendChild(document.createTextNode('   '));
      const b = document.createElement('span');
      b.className = 'term'; b.textContent = name;
      b.onclick = function () { openSheet(name, DATA.glossary[name] || ''); };
      terms.appendChild(b);
    });
  }

  const nxt = DATA.slides[st.slide + 1];
  document.getElementById('next').textContent = nxt ? nxt.title : 'Last slide.';
  document.getElementById('detailBtn').className = 'chip' + (st.detail ? ' on' : '');
  document.getElementById('prev').disabled = st.slide === 0;
  document.getElementById('next-btn').disabled = st.slide === DATA.slides.length - 1;
  document.getElementById('scroll').scrollTop = 0;
}

// Thunder reading the slide aloud. One <audio> reused for every slide, because
// twenty-three of them would each hold a decoder open on a phone.
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
    // No narration generated for this slide yet, or the phone refused to play
    // without a gesture. Either way, say so instead of looking broken.
    document.getElementById('speakBtn').className = 'chip';
    openSheet('No narration', 'This slide has not been narrated yet. Run ' +
      'python3 -m onboarding.narrate on Main to generate it.');
  });
}

// Auto mode: Thunder presents itself. Useful for rehearsing, and the demo to
// leave running when Blayne is not in the room.
audio.onended = function () {
  document.getElementById('speakBtn').className = 'chip';
  if (auto && st.slide < DATA.slides.length - 1) {
    setTimeout(function () { if (auto) { go(1); speak(); } }, 1200);
  } else if (auto) {
    auto = false;
    document.getElementById('autoBtn').className = 'chip';
  }
};

document.getElementById('speakBtn').onclick = function () {
  if (!audio.paused && audio.src) stopSpeaking(); else speak();
};

document.getElementById('autoBtn').onclick = function () {
  auto = !auto;
  this.className = 'chip' + (auto ? ' on' : '');
  if (auto) speak(); else stopSpeaking();
};

document.getElementById('prev').onclick = function () { go(-1); };
document.getElementById('next-btn').onclick = function () { go(1); };
document.getElementById('detailBtn').onclick = function () { post({ detail: !st.detail }); };

document.getElementById('sheet').onclick = function () { this.classList.remove('open'); };
document.getElementById('toc').onclick = function (e) {
  if (e.target === this) this.classList.remove('open');
};

document.getElementById('tocBtn').onclick = function () {
  const list = document.getElementById('tocList');
  list.innerHTML = '';
  DATA.sections.forEach(function (sec) {
    const b = document.createElement('button');
    const cur = st.slide >= sec.first && st.slide < sec.first + sec.count;
    if (cur) b.className = 'cur';
    b.textContent = sec.name + '  ';
    const n = document.createElement('span');
    n.className = 'n'; n.textContent = sec.count + (sec.count === 1 ? ' slide' : ' slides');
    b.appendChild(n);
    b.onclick = function () {
      document.getElementById('toc').classList.remove('open');
      post({ slide: sec.first });
    };
    list.appendChild(b);
  });
  document.getElementById('toc').classList.add('open');
};

// Swipe left for the next cell, right to go back - on the whole page, because
// on a phone the thumb lands wherever it lands.
let x0 = null, y0 = null;
document.addEventListener('touchstart', function (e) {
  x0 = e.touches[0].clientX; y0 = e.touches[0].clientY;
}, { passive: true });
document.addEventListener('touchend', function (e) {
  if (x0 === null) return;
  const dx = e.changedTouches[0].clientX - x0;
  const dy = e.changedTouches[0].clientY - y0;
  // Horizontal has to clearly beat vertical, or scrolling the notes would
  // change slide halfway down a paragraph.
  if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.6) go(dx < 0 ? 1 : -1);
  x0 = null; y0 = null;
}, { passive: true });

// A keyboard, for rehearsing at the desk.
document.addEventListener('keydown', function (e) {
  if (e.key === 'ArrowRight' || e.key === ' ') go(1);
  if (e.key === 'ArrowLeft') go(-1);
  if (e.key === 'd') post({ detail: !st.detail });
});

// Adopt whatever position the deck is already on, so opening the presenter
// view mid-talk does not yank the television back to slide one.
fetch('/deck/state', { cache: 'no-store' })
  .then(function (r) { return r.json(); })
  .then(function (s) { st.slide = s.slide; st.detail = s.detail; render(); })
  .catch(render);
</script>
</body></html>
"""


def audience_html() -> str:
    return _AUDIENCE.replace("__CSS__", _CSS).replace(
        "__PAYLOAD__", _payload(audience=True))


def presenter_html() -> str:
    return _PRESENTER.replace("__CSS__", _CSS).replace("__PAYLOAD__", _payload())
