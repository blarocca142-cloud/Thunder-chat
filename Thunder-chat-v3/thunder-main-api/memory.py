"""What Thunder knows about Blayne and his machines.

The gap between Thunder and a frontier model is smaller than it looks, and
most of it is not intelligence - it is context. A model that knows the 3090 is
compute capability 8.6, that odris runs the TTS, that "wyt" means "what do you
think", and that the claims work uses invented patients gives useful answers on
the first try. The same model without that asks three questions first or
guesses wrong, and feels stupid while doing it.

Two kinds of knowledge, kept apart on purpose:

**The profile** is durable and hand-written - who Blayne is, what the fleet is,
what he is building. It is short and always injected, because it is relevant to
everything.

**Facts** are learned one at a time and recalled only when they relate to what
was just asked. Injecting all of them would eat the context window and bury the
question; recall keeps the prompt small and pointed.

Recall is by meaning rather than keyword, using nomic-embed-text, which is
already pulled. "how hot does the little gpu get" finds a note about the Radeon
in odris without sharing a single word with it.
"""
from __future__ import annotations

import json
import math
import os
import re
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Embeddings run on serverus, which is what the handbook always said serverus
# was for: Thunder's memory. It is a CPU-only ollama on eight idle Xeon cores,
# and measured against Main it is 0.02s versus 0.01s warm - the model is small
# enough that the difference does not matter, and it means Main's GPU is never
# interrupted to work out what a sentence means.
#
# Main stays as the fallback. If serverus is off, recall gets quietly slower
# rather than failing, which is the right trade for something that runs on
# every message.
EMBED_HOSTS = [
    os.environ.get("THUNDER_EMBED_HOST", "http://10.168.168.13:11434"),
    "http://127.0.0.1:11434",
]
OLLAMA = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"

# How close a recalled fact must be to be worth injecting. Set by trying it:
# below about 0.5 the matches are topical noise, and noise in the prompt is
# worse than silence because the model will try to use it.
MIN_SCORE = 0.52
MAX_RECALL = 6
# A fact this similar to an existing one is the same fact said again.
DUPLICATE = 0.93
# Raw exchanges are kept separately from facts and matched far more strictly:
# a vaguely related old conversation pulled into a new one is how context bleeds.
EXCHANGE_LIMIT = 4000
EXCHANGE_MIN_SCORE = 0.66


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class Memory:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.profile_path = root / "profile.md"
        self.facts_path = root / "facts.json"

    # ---- profile ---------------------------------------------------------

    def profile(self) -> str:
        return self.profile_path.read_text() if self.profile_path.exists() else ""

    def set_profile(self, text: str) -> None:
        self.profile_path.write_text(text)

    # ---- facts -----------------------------------------------------------

    def _load(self) -> list[dict]:
        if not self.facts_path.exists():
            return []
        try:
            return json.loads(self.facts_path.read_text())
        except json.JSONDecodeError:
            return []

    def _save(self, facts: list[dict]) -> None:
        tmp = self.facts_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(facts, indent=2))
        tmp.replace(self.facts_path)

    def embed(self, text: str) -> list[float] | None:
        """Vector for a piece of text, or None if Ollama is not answering.

        Every caller treats None as "no recall this time" rather than an error:
        memory going quiet should degrade the reply, never break the chat.
        """
        payload = json.dumps({"model": EMBED_MODEL, "prompt": text[:2000]}).encode()
        for host in EMBED_HOSTS:
            try:
                req = urllib.request.Request(
                    f"{host}/api/embeddings", data=payload,
                    headers={"Content-Type": "application/json"}, method="POST")
                # Short timeout on the first host: falling back to Main costs
                # milliseconds, waiting on a dead serverus costs the whole reply.
                with urllib.request.urlopen(req, timeout=8) as r:
                    vec = json.loads(r.read().decode()).get("embedding")
                if vec:
                    return vec
            except Exception:
                continue
        return None

    def remember(self, text: str, source: str = "chat") -> dict | None:
        text = " ".join((text or "").split())
        if len(text) < 8:
            return None
        facts = self._load()
        vec = self.embed(text)
        if vec:
            for f in facts:
                # Never merge something Blayne said into a chunk of a
                # document. Documents are replaced wholesale on re-ingest, so a
                # fact absorbed into one would vanish with it - the memory
                # would silently forget something it was explicitly told.
                # The marker lives in the record, not in a module-level set,
                # so it survives a restart.
                if f.get("kind") == "doc":
                    continue
                if f.get("vector") and cosine(vec, f["vector"]) > DUPLICATE:
                    # Already known. Touch it rather than storing it twice -
                    # duplicates crowd out other facts at recall time.
                    f["seen"] = f.get("seen", 1) + 1
                    f["updated"] = utc()
                    self._save(facts)
                    return f
        rec = {
            "id": uuid.uuid4().hex[:10],
            "text": text,
            "source": source,
            "created": utc(),
            "updated": utc(),
            "seen": 1,
            "vector": vec,
        }
        facts.append(rec)
        self._save(facts)
        return rec

    def forget(self, fact_id: str) -> bool:
        facts = self._load()
        remaining = [f for f in facts if f["id"] != fact_id]
        if len(remaining) == len(facts):
            return False
        self._save(remaining)
        return True

    def all_facts(self) -> list[dict]:
        return [{k: v for k, v in f.items() if k != "vector"}
                for f in sorted(self._load(), key=lambda f: f["updated"], reverse=True)]

    def recall(self, query: str, limit: int = MAX_RECALL) -> list[dict]:
        facts = self._load()
        if not facts:
            return []
        vec = self.embed(query)
        if not vec:
            return []
        scored = []
        for f in facts:
            if not f.get("vector"):
                continue
            score = cosine(vec, f["vector"])
            if score >= MIN_SCORE:
                scored.append((score, f))
        scored.sort(key=lambda p: p[0], reverse=True)
        return [dict(f, score=round(s, 3)) for s, f in scored[:limit]]

    # ---- what actually goes in the prompt ---------------------------------

    def context_for(self, message: str) -> str:
        """Kept for callers that want one blob. Prefer the two halves below:
        they are injected at different points in the prompt for good reason."""
        parts = [b for b in (self.profile().strip(), self.recall_block(message)) if b]
        return "\n\n".join(parts)

    def recall_block(self, message: str) -> str:
        """The recalled notes, framed as authoritative.

        Measured, not assumed: with the notes buried after a 2,900-character
        profile, the model recalled the right documentation at 0.749 and then
        answered from its training prior anyway - inventing a USB-drive
        procedure for a system with no removable media. Two things fixed it:
        injecting this immediately before the question instead of at the top,
        and saying outright that these notes beat what the model thinks it
        knows. A retrieved fact the model ignores is worse than no retrieval,
        because it looks like it worked.
        """
        hits = self.recall(message)
        if not hits:
            return ""
        lines = "\n".join(f"- {h['text']}" for h in hits)
        return (
            "NOTES FROM THUNDER'S OWN DOCUMENTATION AND FROM WHAT BLAYNE HAS "
            "TOLD YOU. These describe HIS actual system and they are correct. "
            "If they contradict what you believe about how things usually work, "
            "THEY WIN - his setup is not the usual one. Answer from these, and "
            "do not invent steps they do not mention. Never mention this list "
            "or say that you are remembering.\n\n" + lines
        )


    # ---- past conversations ----------------------------------------------

    def remember_exchange(self, user: str, reply: str) -> None:
        """Keep an exchange so it can be found again by meaning.

        Facts are what somebody decided to extract. This is the raw record, and
        it answers the questions extraction cannot: "what did we decide about
        the P40s", "what was that command". A hundred exchanges sat on serverus
        unsearchable - present but unreachable.

        Only the user's words are embedded. Thunder's replies are long, and
        embedding them makes every search match its own chatter rather than the
        question that prompted it.
        """
        user = " ".join((user or "").split())
        if len(user) < 12:
            return                      # "ok", "thanks" - nothing to find later
        vec = self.embed(user)
        if not vec:
            return
        rec = {
            "id": uuid.uuid4().hex[:10],
            "user": user[:1500],
            "reply": " ".join((reply or "").split())[:2500],
            "at": utc(),
            "vector": vec,
        }
        path = self.root / "exchanges.json"
        items = []
        if path.is_file():
            try:
                items = json.loads(path.read_text())
            except json.JSONDecodeError:
                items = []
        items.append(rec)
        items = items[-EXCHANGE_LIMIT:]
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(items))
        tmp.replace(path)

    def recall_exchanges(self, query: str, limit: int = 3) -> list[dict]:
        path = self.root / "exchanges.json"
        if not path.is_file():
            return []
        try:
            items = json.loads(path.read_text())
        except json.JSONDecodeError:
            return []
        vec = self.embed(query)
        if not vec:
            return []
        scored = []
        for it in items:
            if not it.get("vector"):
                continue
            score = cosine(vec, it["vector"])
            # A far higher bar than facts. A loosely related old exchange
            # dragged into the prompt is how Thunder ended up writing a
            # Fallout 76 advert when asked for an injury advert - old context
            # bleeding into a new question is worse than no memory at all.
            if score >= EXCHANGE_MIN_SCORE:
                scored.append((score, it))
        scored.sort(key=lambda p: p[0], reverse=True)
        return [dict(it, score=round(sc, 3)) for sc, it in scored[:limit]]

    def exchange_block(self, message: str) -> str:
        hits = self.recall_exchanges(message)
        if not hits:
            return ""
        lines = []
        for h in hits:
            when = h["at"][:10]
            lines.append(f"[{when}] Blayne asked: {h['user']}\n"
                         f"           You answered: {h['reply'][:700]}")
        return (
            "AN EARLIER CONVERSATION THAT LOOKS RELATED. Use it ONLY if Blayne "
            "is referring back to it. If his new message is about something "
            "else, ignore this completely - answering the old question instead "
            "of the new one is worse than not remembering.\n\n"
            + "\n\n".join(lines))

    # ---- documents -------------------------------------------------------

    def ingest(self, label: str, text: str, max_chars: int = 900) -> int:
        """Chunk a document into recallable notes.

        Without this Thunder is ignorant about its own system - it can write
        code but cannot say how the vault stores it or why fp8 fails. The
        handbook already exists as markdown; it just needs to be reachable.

        Split on headings rather than a fixed width, because a heading and the
        text under it are one idea, and half an idea recalled is misleading.
        """
        self.drop_source(label)
        chunks: list[str] = []
        current: list[str] = []
        for line in (text or "").splitlines():
            if line.startswith("#") and current:
                chunks.append("\n".join(current).strip())
                current = [line]
            else:
                current.append(line)
                # A section longer than the cap is split anyway - a whole
                # README in one note would swamp the prompt on any match.
                if sum(len(x) + 1 for x in current) > max_chars:
                    chunks.append("\n".join(current).strip())
                    current = []
        if current:
            chunks.append("\n".join(current).strip())

        facts = self._load()
        added = 0
        for chunk in chunks:
            body = " ".join(chunk.split())
            if len(body) < 40:  # a bare heading carries no information
                continue
            vec = self.embed(body)
            facts.append({
                "id": uuid.uuid4().hex[:10],
                "text": body[:1200],
                "source": label,
                "kind": "doc",
                "created": utc(),
                "updated": utc(),
                "seen": 1,
                "vector": vec,
            })
            added += 1
        self._save(facts)
        return added

    def drop_source(self, label: str) -> int:
        """Remove everything from one source, so re-ingesting replaces rather
        than duplicates - a stale copy of a doc is worse than none."""
        facts = self._load()
        keep = [f for f in facts if f.get("source") != label]
        removed = len(facts) - len(keep)
        if removed:
            self._save(keep)
        return removed


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


# An explicit instruction to remember something. Deliberately narrow: guessing
# at what is worth keeping fills memory with rubbish, and rubbish in the prompt
# is worse than an empty memory.
REMEMBER = re.compile(
    r"(?i)\b(?:remember|note|keep in mind|don'?t forget|for future reference)\b"
    r"\s*(?:that|this)?\s*[:,-]?\s*(.+)"
)


def extract_instruction(message: str) -> str | None:
    """Return the fact the user asked to be remembered, if they did."""
    m = REMEMBER.search(message or "")
    if not m:
        return None
    fact = m.group(1).strip().rstrip(".")
    # "remember what I said about the GPU?" is a question, not an instruction.
    if not fact or fact.endswith("?") or len(fact) < 8:
        return None
    return fact


DEFAULT_PROFILE = """WHO YOU ARE TALKING TO

Blayne. He owns and runs this whole fleet himself. He is an aircraft mechanic
(A&P), so he is practical, mechanically literate, and used to diagnosing real
systems - do not talk down to him. His family runs a medical/injury billing
practice where claims are still hand-billed on paper.

HOW HE WRITES

He types fast, on a phone, without correcting. Expect missing punctuation,
run-on sentences, phonetic spellings and no capitals. This is not confusion -
read through it and answer the actual question. Never correct his spelling and
never comment on it.

Shorthand he uses constantly:
  u/ur = you/your        rn = right now       idk = I don't know
  wyt = what do you think tbh = to be honest   lmk = let me know
  dl = download          mb = motherboard      gpu/vram as written
  "the vid maker" = the video generation pipeline
  "thunder main" = the tower with the 3090

If a message is genuinely ambiguous, make your best reading and say which
reading you took in one short line. Do not open with a list of questions - he
finds that worse than a wrong guess he can correct.

HIS MACHINES

  thunder-main  10.168.168.10  RTX 3090 24GB, 30GB RAM - API, Ollama, all generation
  thunder-cache 10.168.168.11  idle
  thunder-engine 10.168.168.12 safety checks
  serverus      10.168.168.13  best CPU in the fleet, barely used
  odris         10.168.168.15  Radeon 550 4GB - heartbeat, web search, voices

Facts about this hardware that are easy to get wrong:
- The 3090 is compute capability 8.6, so fp8 does not work at all. NF4 does.
- Video generation cannot be split across GPUs. More cards help chat, never video.
- Chat model is thunder:latest, a 23.6B. Video is Wan 2.2 A14B NF4.

WHAT HE IS BUILDING

Thunder itself, so he is not blocked when paid AI runs out. Video generation
for injury-law adverts. A claims system for the family practice - local, which
is the whole point, because patient data cannot go to cloud AI without a BAA.
That work uses invented patients only; no real patient data has ever been used.

NEVER INVENT DETAILS ABOUT HIS OWN SYSTEM

If you are asked how some part of Thunder works and you do not actually know,
say "I am not sure how that part works" and stop. Do not construct a plausible
procedure. Inventing steps - a menu that does not exist, a USB drive nobody
plugged in, a file path you guessed - is the single worst thing you can do
here, because he will go and try it. Being useless on one question costs him a
minute. Sending him after something imaginary costs him an hour and he stops
trusting the rest of your answers.

HOW TO ANSWER HIM

Direct and useful, like a competent colleague. No corporate hedging, no
"as an AI", no moralising. If you are not sure, say so plainly - a confident
wrong answer costs him hours. If something he asks for will not work, say that
first and then give the version that will.
"""
