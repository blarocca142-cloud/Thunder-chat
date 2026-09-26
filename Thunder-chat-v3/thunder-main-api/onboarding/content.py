"""The onboarding deck's words. Structure here, rendering in deck.py.

Written to be shown on a TV while Blayne talks over it, so every slide carries
four separate things:

- `short`   what goes on the screen by default. Fewer words than feels natural.
            A slide is a caption for the person talking, not the talk.
- `detail`  the same slide with the depth added, one button away. Both are
            meant to be accurate; the short one is not a teaser.
- `notes`   presenter-only, and genuinely only - it renders on /deck/presenter
            and never on /deck, because casting mirrors a tab and anything in
            the audience view is on the television.
- `terms`   words on the slide that can be tapped for a definition, so "what is
            the test vault" gets answered in ten seconds with the real answer.

Facts here are the measured ones from CLAUDE.md and the commit history, not
estimates. If a number is in this file it was observed on this hardware. Two
things are deliberately stated plainly and must stay that way: no real patient
data has ever touched the claims work, and the encryption is not compliance -
the remaining gap is paperwork. A deck that oversells either one would be the
single most expensive mistake in it.
"""

# Tapped words. Kept in one place so the same term means the same thing on
# every slide, and so Blayne can be asked about any of them cold.
GLOSSARY = {
    "Ollama": "The program that actually runs a language model on a machine you "
              "own. Point it at a model file, it answers questions. Thunder talks "
              "to Ollama instead of to a company's API, which is the whole reason "
              "nothing leaves the house.",
    "quantised": "A model shrunk so it fits. The full model stores each number in "
                 "16 bits; Q4 stores it in about 4. You lose a little accuracy and "
                 "gain the ability to run a 24-billion-parameter model on one "
                 "graphics card instead of four.",
    "Q4_K_M": "The specific recipe used to shrink Thunder. Roughly a quarter of "
              "the original size, and the setting most people land on because it "
              "keeps the most quality per gigabyte saved.",
    "abliterated": "A model with its refusal behaviour removed. Thunder will "
                   "engage with a question rather than declining it. Worth being "
                   "clear-eyed about: that is a capability choice, and it means "
                   "the guardrails have to live in our code, not in the model.",
    "tok/s": "Tokens per second - roughly three-quarters of a word per token. "
             "It is reading speed. 55 tok/s is faster than you can read; 1.8 is "
             "about a word every two seconds.",
    "VRAM": "Memory on the graphics card itself. Different from system RAM and "
            "much faster. It is the hard ceiling on what a GPU can run, and ours "
            "is 24 GB.",
    "envelope encryption": "Every record gets its own key, and those keys are "
                           "themselves encrypted by one master key. Stealing one "
                           "record's key gets you one record. Rotating the master "
                           "key does not mean re-encrypting everything.",
    "AES-256-GCM": "The encryption standard banks and governments use, in the "
                   "mode that also detects tampering. If someone edits the "
                   "ciphertext, decryption fails loudly instead of quietly "
                   "returning wrong data.",
    "blind index": "A way to search encrypted data without decrypting it. We "
                   "store a fingerprint of the value instead of the value. Worth "
                   "knowing the honest limit: it tells you two records hold the "
                   "same value, so it leaks equality even though it never leaks "
                   "the value itself.",
    "test vault": "34 automated checks against our own claims storage, and most "
                  "of them are attacks rather than tests. They tamper with "
                  "ciphertext, move a record to where another one was, use the "
                  "wrong key, use a weak passphrase, and edit a backup archive. "
                  "All 34 pass. It runs in seconds, so it runs after every change.",
    "honeyfile": "A file that exists only to be opened by someone who should not "
                 "be there. Nothing real ever reads it, so any access is a signal. "
                 "Ours are named like things worth stealing and sit where a "
                 "snooper would look.",
    "canary": "The watcher behind the honeyfiles. It reports the instant one is "
              "touched. It is detection, not protection - it cannot stop a break-in, "
              "it tells you about it now instead of in six months.",
    "OCR": "Optical character recognition - turning a picture of a page into text. "
           "The first step on every scanned claim, and the step that fails most, "
           "usually on a crooked or dark scan.",
    "ICD-10": "The standard code for a diagnosis. One wrong character is a "
              "different condition, which is why our validation checks them "
              "mechanically instead of trusting the model.",
    "BAA": "Business Associate Agreement. The contract a company has to sign "
           "before it may legally handle patient data on your behalf. Cloud AI "
           "providers mostly will not sign one for a small practice - which is "
           "exactly the gap Thunder walks into, because it never sends the data "
           "anywhere.",
    "HIPAA": "The US law governing patient health information. It has a technical "
             "half (encryption, access control, audit logs) and a paperwork half "
             "(risk analysis, written policies, training, contracts). We have "
             "built the technical half. The paperwork half is not code.",
    "PHI": "Protected Health Information - anything that identifies a patient. "
           "Name, date of birth, record number. The thing all of this exists to "
           "protect.",
    "fp8": "An 8-bit number format that makes newer cards much faster. Our 3090 "
           "cannot do it at all - it needs compute capability 8.9 and the 3090 is "
           "8.6. This is not a setting we forgot to turn on; the silicon lacks it.",
    "NF4": "A different 4-bit format that our card *can* do. It is what makes "
           "video generation possible here at all.",
    "LoRA": "A small add-on trained on top of a big model to teach it one thing. "
            "Cheap to train, easy to swap. The realistic route to a model that is "
            "genuinely ours: not training a giant from scratch, but teaching an "
            "open one our specific job.",
    "swap": "Using disk space as overflow memory. Normally slow. Ours is striped "
            "across three SSDs and measured at 1.55 GB/s, which is twelve times "
            "faster than pulling memory from another machine over the network.",
    "RPC backend": "A way to split one model across several machines so their "
                   "memory pools together. We tested it properly. It works, and "
                   "it costs about thirty times the speed.",
    "diffusion": "How image and video models work - start with noise, clean it up "
                 "step by step. Unlike chat models, it cannot be split across "
                 "machines, which is why extra towers never help video.",
    "systemd": "What starts and restarts our services on boot. Everything is set "
               "to Restart=always, so a crashed service is back in about three "
               "seconds without anyone noticing.",
    "bearer token": "A secret string sent with every request to prove who you "
                    "are. Simpler than a login for machine-to-machine talk, and "
                    "what Thunder's API uses when auth is switched on.",
}

# Ordered. Each section becomes a chapter in the contents.
SECTIONS = [
    "Start here",
    "The machines",
    "Thunder",
    "Odris",
    "The call organizer",
    "Claims",
    "Security",
    "Pictures and video",
    "Where this goes",
    "Working here",
]

SLIDES = [
    # ---------------------------------------------------------------- Start here
    {
        "section": "Start here",
        "title": "You are looking at a private AI company",
        "short": [
            "Six computers in a house, running our own AI.",
            "Nothing we do leaves the building.",
            "That last sentence is the entire business.",
        ],
        "detail": [
            "Six computers in a house, running our own AI - chat, images, video, "
            "and a claims pipeline for the family practice.",
            "Nothing is rented. No OpenAI, no Google, no API bill, no company "
            "holding the off switch.",
            "That is not a hobbyist's preference. Patient data cannot go into "
            "cloud AI without a signed contract most providers will not give a "
            "small practice. We do not need one, because the data never leaves "
            "the room it was scanned in.",
            "Everything after this slide is detail on how that is actually true.",
        ],
        "notes": "Open here and stop. Let the room sit with 'nothing leaves the "
                 "building' before any hardware talk - it is the only slide that "
                 "matters if you only get one. Dad knows IT, so he will "
                 "immediately wonder about the catch. The catch is speed and "
                 "scale, and you are going to volunteer that yourself on the "
                 "fleet slide rather than let him find it. Volunteering it is "
                 "what buys credibility for the rest.",
        "terms": ["BAA", "PHI"],
    },
    {
        "section": "Start here",
        "title": "What is actually built, in one list",
        "short": [
            "Thunder - the assistant. Chat, voice, images, video.",
            "Odris - the watchman. Reports what is breaking.",
            "The call organizer - turns phone logs into a clean sheet.",
            "Claims - scan a form, check it, flag it for a human.",
            "The security layer wrapped around all of it.",
        ],
        "detail": [
            "Thunder - the assistant. A 24-billion-parameter model on our own "
            "graphics card, with memory, a voice, and an Android app.",
            "Odris - the watchman. A separate assistant on a separate machine "
            "whose only job is watching the other five and telling us what needs "
            "a person.",
            "The call organizer - takes exported phone logs and produces a "
            "spreadsheet a human can act on, with the robocalls stripped out.",
            "Claims - scan a paper form, read it, check it mechanically, and hand "
            "anything doubtful to a person. It does not submit anything.",
            "Security - encryption at rest, TLS between machines, decoy files "
            "that scream when touched, and an audit trail.",
            "Each of these is a working thing you can open, not a plan.",
        ],
        "notes": "This is the contents page in disguise. If he only wants one "
                 "area, jump there from the menu - the deck is built to be "
                 "skipped around in. The claims line is the one he will care "
                 "about most because it is the family's actual money, so do not "
                 "rush past it. Note 'it does not submit anything' out loud; "
                 "that single design choice is why nobody can get in trouble.",
        "terms": [],
    },

    # -------------------------------------------------------------- The machines
    {
        "section": "The machines",
        "title": "Six towers, and only one that matters",
        "short": [
            "thunder-main - RTX 3090, 24 GB. This one does the work.",
            "odris - watches the other five.",
            "serverus - best processor in the house, holds memory.",
            "thunder-engine - safety checks. thunder-cache - spare.",
            "One card does the thinking. The rest are support.",
        ],
        "detail": [
            "thunder-main (.10) - RTX 3090 with 24 GB of VRAM, 30 GB of system "
            "RAM. Chat, images and video all happen here.",
            "odris (.15) - a Radeon 550 with 4 GB. Too small to run a model, "
            "which is fine: its job is watching the others and it does that on "
            "the processor.",
            "serverus (.13) - a Xeon E3-1230 v5, the best CPU in the fleet. "
            "Stores conversation memory. Barely breaks a sweat.",
            "thunder-engine (.12) - answers yes/no safety questions.",
            "thunder-cache (.11) - spare capacity, and the overnight batch box.",
            "The honest shape of it: one graphics card does the thinking and five "
            "machines make it dependable.",
        ],
        "notes": "He will ask why not pool all six into one big machine. That is "
                 "the next slide and you have the measurements, so let him ask - "
                 "answering a question he just raised lands better than "
                 "pre-empting it. If he asks about cost, the towers are old "
                 "office desktops; the 3090 is the only real money in the rack.",
        "terms": ["VRAM"],
    },
    {
        "section": "The machines",
        "title": "We tried pooling them. It got 30x slower.",
        "short": [
            "One 3090 alone: 55.5 tok/s.",
            "3090 + serverus: 2.97.",
            "All four together: 1.80.",
            "Adding machines made it slower than one machine.",
            "We know because we measured it, not because we guessed.",
        ],
        "detail": [
            "Same model, same prompt, measured three ways:",
            "3090 alone - 55.5 tokens per second. Faster than you can read.",
            "3090 plus serverus - 2.97. 3090 plus all three helpers - 1.80.",
            "Adding the two weakest machines made the whole thing 40% slower "
            "than using one machine on its own.",
            "The reason is plumbing: every token walks the whole chain, so the "
            "fleet runs at the speed of its slowest member and gets worse as it "
            "grows. Local memory moves at about 12 GB/s; the network moves at "
            "0.125.",
            "This is why 'just add more old towers' is not our growth plan, and "
            "why we can say that with numbers instead of opinion.",
        ],
        "notes": "This is the slide that earns his trust, so do not hurry it. It "
                 "is the shape of engineer he is - he will respect that we tested "
                 "the appealing idea and published the result against ourselves. "
                 "If he pushes, the fallback is real: 1.8 tok/s is still ~50,000 "
                 "tokens over an eight-hour night, which is exactly what the "
                 "overnight batch worker wants. Slow is fine when nobody is "
                 "waiting.",
        "terms": ["tok/s", "RPC backend"],
    },
    {
        "section": "The machines",
        "title": "The tricks that make old hardware work",
        "short": [
            "Main's board maxes at 32 GB of RAM. That ceiling is real.",
            "So we borrow memory from three SSDs instead - 1.55 GB/s.",
            "Twelve times faster than borrowing from another machine.",
            "The 3090 cannot do fp8. We use NF4, which it can.",
            "Constraints are documented so nobody rediscovers them.",
        ],
        "detail": [
            "Main is a Lenovo ThinkCentre with four DIMM slots, all full. 32 GB "
            "is the board's hard ceiling and there is no upgrade path.",
            "Instead we put 32 GB of swap on each of three SSDs at equal "
            "priority, so the kernel spreads across all three: measured at 1.55 "
            "GB/s. Gigabit ethernet is 0.125 GB/s, so the disks in this machine "
            "beat any other machine on the network by twelve times.",
            "The 3090 is compute capability 8.6, so fp8 simply does not exist on "
            "it - not disabled, absent. NF4 works, and that is what runs video.",
            "Video's memory allocator needs one specific setting or it runs out "
            "of memory at 720p. That setting is the difference between working "
            "and not.",
            "All of this is written down in the handbook, because the expensive "
            "version of knowing it is finding out twice.",
        ],
        "notes": "Good slide to speed up on unless he bites - it is the most "
                 "technical one in the deck. The point to land is cultural, not "
                 "technical: every hard-won fact is written down so nobody pays "
                 "for it twice. That is the thing that makes a team of more than "
                 "one person possible, and it is why hiring is realistic.",
        "terms": ["swap", "fp8", "NF4", "VRAM"],
    },

    # ------------------------------------------------------------------ Thunder
    {
        "section": "Thunder",
        "title": "Thunder is ours, running on our card",
        "short": [
            "24 billion parameters, on the 3090, at 55 tok/s.",
            "Talks like a person, not a corporate chatbot.",
            "Android app, voice, images, video, code.",
            "No API key. No bill. No outage that is not ours.",
        ],
        "detail": [
            "A 23.6-billion-parameter model, quantised to about a quarter of its "
            "full size so it fits in 24 GB, answering at 55 tokens per second.",
            "Built on an open Mistral base with our own system prompt - so it is "
            "direct and useful rather than hedging like a customer service bot.",
            "It has an Android app, nine voices, image and video generation, and "
            "a place to keep code it writes.",
            "There is no API key anywhere in this system. If the internet goes "
            "down, Thunder keeps working. If a company changes its pricing or "
            "its terms, nothing here changes.",
        ],
        "notes": "Be straight if he asks how it compares to ChatGPT: a 24B is "
                 "genuinely weaker at hard reasoning and long chains, and "
                 "pretending otherwise gets found out in five minutes of him "
                 "using it. Where it wins is the part that actually matters here "
                 "- it is ours, it is private, it is free to run, and it knows "
                 "our business because we gave it our context. Frame it as a "
                 "specialist, not a smaller ChatGPT.",
        "terms": ["quantised", "Q4_K_M", "abliterated", "tok/s", "Ollama"],
    },
    {
        "section": "Thunder",
        "title": "Why Thunder knows things - the memory",
        "short": [
            "A profile that is always loaded: who we are, what the hardware is.",
            "Facts recalled by meaning, only when relevant.",
            "Documents - the handbooks - searchable.",
            "Most of the gap to a big model is context, not brains.",
        ],
        "detail": [
            "Three layers. A profile always in front of it - who Blayne is, the "
            "fleet, the hardware facts that are easy to get wrong. That single "
            "thing is the biggest lever on answer quality in the whole system.",
            "Facts, recalled by meaning rather than keyword, and only when they "
            "are relevant to what was asked.",
            "Documents - the handbook and the technical notes - chunked and "
            "searchable.",
            "Two lessons learned the hard way. Retrieval working is not "
            "retrieval being used: notes were found correctly and then ignored "
            "until they were moved to sit immediately before the question and "
            "labelled as authoritative.",
            "And never let it read its own answers back. An early version "
            "learned one of Thunder's own invented file paths as a fact.",
        ],
        "notes": "The second lesson is the important one and it is worth saying "
                 "slowly, because it is the difference between a system that "
                 "improves and one that rots. An AI that writes its own beliefs "
                 "into its own memory compounds errors - one confident mistake "
                 "becomes permanent context for every answer after it, and later "
                 "there is no way to tell which facts were ever real. Which is "
                 "why nothing enters memory without a human approving it. If he "
                 "has managed data systems he will recognise this instantly.",
        "terms": [],
    },
    {
        "section": "Thunder",
        "title": "Nothing writes to memory unreviewed",
        "short": [
            "At 3am, Thunder reads back only what Blayne said. Never itself.",
            "It proposes. It does not save.",
            "Contradictions get flagged against each other, not silently picked.",
            "A human approves or rejects. Always.",
        ],
        "detail": [
            "A job runs nightly and reads the day's conversations - only "
            "Blayne's messages, never Thunder's own replies.",
            "It produces proposals: 'this looks worth remembering'. They sit in "
            "a queue.",
            "If two proposals contradict each other, both get flagged against "
            "each other rather than one being quietly chosen. At least one is "
            "wrong and a person should decide which.",
            "Nothing enters long-term memory until approved. This is a rule, not "
            "a setting, and it is written into the handbook as a thing not to "
            "'improve'.",
        ],
        "notes": "If he asks why not just let it learn automatically - that is "
                 "the exact trap. Unsupervised self-learning sounds like progress "
                 "and is actually how you get a system nobody can trust in six "
                 "months, with no way to audit which facts were real. The review "
                 "queue is the whole reason we can hand this to an employee. "
                 "Good place to mention this is the same principle as claims: the "
                 "model proposes, a human or a mechanical check decides.",
        "terms": [],
    },

    # -------------------------------------------------------------------- Odris
    {
        "section": "Odris",
        "title": "Odris watches, and cannot be silenced by what it watches",
        "short": [
            "A separate assistant on a separate machine.",
            "Its job: node health, hardware, alerts, errors.",
            "Different from Thunder on purpose.",
            "The rule: the watcher must not be controllable by the watched.",
        ],
        "detail": [
            "Odris is not Thunder wearing a hat. Its own instructions, its own "
            "context - live machine readings instead of chat history.",
            "It watches the other five machines, reads their hardware health, "
            "and tells us what needs a person.",
            "The architectural rule behind it: the watcher must not be "
            "controllable by the watched. If Main is compromised, anything Main "
            "can switch off is worthless as a warning.",
            "So Odris reaches into Main through a key that can run exactly one "
            "read-only command and nothing else.",
            "It runs on the weakest machine in the house, because watching does "
            "not need a graphics card.",
        ],
        "notes": "This is the slide to be proud of and it is genuinely good "
                 "security design - the same principle behind a separate logging "
                 "server in any serious shop. The restricted key is the detail "
                 "worth naming: even if someone owns Main completely, they cannot "
                 "use that key to do anything but the one read.",
        "terms": ["systemd"],
    },
    {
        "section": "Odris",
        "title": "The bug that proves why this matters",
        "short": [
            "The phone warned about serverus. Opening the app showed nothing.",
            "The warning was real. There was just no screen for it.",
            "Three separate causes. All three now fixed.",
            "Alerts have a history. Both AIs can explain them.",
        ],
        "detail": [
            "The phone sent a notification about serverus's boot drive. Opening "
            "the app showed nothing, and asking Thunder about it got a blank "
            "look. It felt like the system was making things up.",
            "It was not. The warning was correct - a drive with 6.4 years of "
            "runtime carrying the boot partition.",
            "Three causes. The daily summary was computed fresh each time and "
            "thrown away, so nothing survived to be opened. No screen in the app "
            "had ever displayed it. And the chat model was never told, so it "
            "genuinely did not know.",
            "Now: alerts persist with a first-seen, whether they are still true, "
            "and what to do. A tapped notification opens onto the finding. And "
            "both Thunder and Odris are given the live readings before they "
            "answer.",
        ],
        "notes": "Tell this one as a story, because it is the most honest slide "
                 "in the deck and honesty is what you are actually selling. It "
                 "shows the system caught a real problem, shows we found out why "
                 "the reporting was broken, and shows the fix was three fixes "
                 "rather than one guess. If he has ever been on call, 'the "
                 "monitoring was right and the dashboard was empty' will land "
                 "hard. It is also a live demo: open the Fleet tab.",
        "terms": [],
    },

    # ------------------------------------------------- The call organizer
    {
        "section": "The call organizer",
        "title": "Phone logs in, a sheet a human can use out",
        "short": [
            "Export the call log. Get back a clean spreadsheet.",
            "Robocalls and junk filtered out.",
            "Caller ID cleaned up - 'Wireless Caller' is not a name.",
            "Runs as a web page or a desktop app.",
        ],
        "detail": [
            "Point it at an exported phone log and it produces a spreadsheet "
            "organised the way a person actually wants to read it.",
            "It strips the junk - robocalls, spam patterns, the repeat numbers "
            "that are not people.",
            "It cleans the caller ID labels, which are a mess in real data: a "
            "number repeated inside its own name field, 'Wireless Caller', "
            "'Unknown', 'Unavailable'. None of those are names and all of them "
            "end up in the name column if nothing removes them.",
            "Two front ends over one engine: a web page in the browser, and a "
            "desktop app. Same code doing the work, so they cannot drift apart.",
            "It is the smallest thing here and the most immediately useful, "
            "which is usually how it goes.",
        ],
        "notes": "This is the one he can judge instantly because he has seen the "
                 "raw data, so consider demoing it live - it is fast and "
                 "unglamorous and that is the point. Worth mentioning the "
                 "discipline: the repository has a rule that no call data, no "
                 "spreadsheet, no contact list is ever committed alongside the "
                 "code, because those hold real numbers and real names. The code "
                 "is shareable; the data never leaves.",
        "terms": [],
    },

    # ------------------------------------------------------------------- Claims
    {
        "section": "Claims",
        "title": "Our version of the claims software",
        "short": [
            "Scan a form. Read it. Check it. Flag anything doubtful.",
            "It submits nothing. Ever. A person decides.",
            "It already caught the AI corrupting a diagnosis code.",
            "The practice bills on paper, by hand, today.",
        ],
        "detail": [
            "The pipeline: scan a paper form, read the text off it, pull out the "
            "fields, then check every field mechanically - check digits, code "
            "formats, impossible dates.",
            "Anything that fails is blocked. Anything repaired or missing goes "
            "to a review queue for a person. Nothing is ever submitted "
            "automatically.",
            "The validation has already earned itself: it caught the model "
            "corrupting an ICD-10 diagnosis code and dropping the billing "
            "provider entirely. The model was confidently wrong and the "
            "mechanical check did not care how confident it was.",
            "That is the whole design principle. The AI proposes, arithmetic "
            "decides.",
            "Today the practice does this by hand on paper and pays a cloud "
            "provider for storage.",
        ],
        "notes": "The ICD-10 catch is the single most persuasive fact in this "
                 "entire deck for a family business, so give it room. It proves "
                 "we do not trust our own AI, and that we built the thing that "
                 "checks it. Anyone selling him an AI claims product will not "
                 "tell him a story about their model being wrong. Also: 'it "
                 "submits nothing' is the answer to every liability question he "
                 "is about to raise, so say it before he asks.",
        "terms": ["OCR", "ICD-10"],
    },
    {
        "section": "Claims",
        "title": "Where the patient data actually sits",
        "short": [
            "Every record encrypted with its own key.",
            "Searchable without being decrypted.",
            "Every access logged. Keys can be rotated.",
            "34 attacks run against it. All 34 pass.",
        ],
        "detail": [
            "Each record is encrypted with its own key, and those keys are "
            "encrypted by one master key. Compromising one record does not give "
            "you the next one, and rotating the master does not mean "
            "re-encrypting everything.",
            "The cipher is AES-256-GCM, which also detects tampering - an edited "
            "record fails loudly rather than quietly decrypting to something "
            "wrong.",
            "Records can be searched without being decrypted, using stored "
            "fingerprints rather than values.",
            "Every access is written to an audit log. Backups are encrypted with "
            "a passphrase of their own.",
            "The test suite is 34 checks and most of them are attacks: tamper "
            "with the ciphertext, move a record to another record's slot, use "
            "the wrong key, use a weak passphrase, edit a backup archive. All 34 "
            "pass, and it runs in seconds, so it runs after every change.",
        ],
        "notes": "Two honest limits, and state them yourself before he finds "
                 "them, because an engineer who spots an unstated limit stops "
                 "believing the rest. One: encryption at rest does nothing "
                 "against an attacker who already has administrator access on a "
                 "running machine - the keys are in memory by definition. Two: "
                 "the searchable fingerprint leaks equality; it can tell you two "
                 "records hold the same value. Both are written in our own "
                 "documentation. Saying them out loud is what makes the 34 "
                 "passing tests believable.",
        "terms": ["envelope encryption", "AES-256-GCM", "blind index", "test vault", "PHI"],
    },
    {
        "section": "Claims",
        "title": "Two things we will not overstate",
        "short": [
            "No real patient data has ever touched this. Synthetic only.",
            "Good encryption is not compliance.",
            "The technical safeguards are built. The paperwork is not.",
            "Risk analysis, written policies, training, contracts. Not code.",
        ],
        "detail": [
            "Everything built so far has been tested on invented patients. No "
            "real protected health information has been through any of it, and "
            "that stays true until there is a deliberate decision to change it.",
            "The technical safeguards are genuinely done, and each was verified "
            "rather than assumed: encryption at rest, encrypted backups, "
            "authentication, TLS between machines, audit logging, intrusion "
            "detection.",
            "None of that is compliance. HIPAA has a paperwork half - a written "
            "risk analysis, written policies, workforce training, signed "
            "agreements with anyone who touches the data.",
            "That half is not code and cannot be written by an AI. It is the "
            "real remaining work before a single real patient record moves.",
            "Saying this clearly is not modesty. It is the difference between a "
            "system you can defend and a lawsuit.",
        ],
        "notes": "Do not soften this slide, and do not let enthusiasm in the room "
                 "soften it either. If Dad comes away thinking we are compliant "
                 "because the crypto is good, that is actively dangerous for the "
                 "family. The right framing: we have done the expensive half that "
                 "most small practices never manage, and the remaining half is "
                 "forms and decisions that a person has to own. If he wants a job "
                 "in this, that half is a genuinely great one for someone who "
                 "knows IT and can write policy.",
        "terms": ["HIPAA", "BAA", "PHI"],
    },

    # ------------------------------------------------------------------ Security
    {
        "section": "Security",
        "title": "Decoy files that scream",
        "short": [
            "Files that exist only to be opened by the wrong person.",
            "Named like things worth stealing.",
            "Touch one and the phone knows immediately.",
            "Detection, not protection - and that distinction matters.",
        ],
        "detail": [
            "Scattered where a snooper would look are files named like the "
            "crown jewels - patient exports, billing records, a backup SSH key. "
            "All fake.",
            "Nothing legitimate ever reads them, so any access at all is a "
            "signal rather than something to interpret.",
            "Touch one and an alert fires instantly, into the system log and "
            "onto the phone.",
            "Be precise about what this is: detection, not protection. It cannot "
            "stop a break-in. By the time one fires, someone is already inside. "
            "What it buys is finding out now instead of in six months, which is "
            "the difference that actually decides how bad a breach becomes.",
        ],
        "notes": "There is a good war story here if he wants one. These fired at "
                 "3am and it looked like a real intrusion for about an hour. It "
                 "turned out to be Blayne's own file search sweeping them up - "
                 "and the reason it read as an intrusion at first was a timezone "
                 "mistake, because the log records UTC and 07:12 in the log was "
                 "03:12 in the kitchen. Two fixes came out of it: the decoys "
                 "moved somewhere a code search will not touch, and every "
                 "timestamp shown to a person is now converted to local time "
                 "first. A false alarm you understand is worth more than a quiet "
                 "system.",
        "terms": ["honeyfile", "canary"],
    },
    {
        "section": "Security",
        "title": "The honest grade, including what is weak",
        "short": [
            "Strong: the claims vault, the Odris dashboard, the egress lockdown.",
            "Weak: the network is trusted more than it should be.",
            "Only one service on the fleet asks for a password.",
            "We know because we went looking, not because it broke.",
        ],
        "detail": [
            "What is genuinely strong: the claims encryption and its 34 attack "
            "tests; the Odris dashboard, which is the one service that properly "
            "authenticates; and the network lockdown that stops the AI processes "
            "reaching the internet at all.",
            "What is weak, stated plainly: the fleet largely trusts anything "
            "already on the home network. Of all the services running across six "
            "machines, exactly one asks for a password.",
            "That is a reasonable posture for a house and not a reasonable one "
            "for patient data, which is the honest reason it is on this slide.",
            "The fix is not exotic - authentication on each service, which is "
            "mostly plumbing. The plan is to build a test suite that attacks our "
            "own network the way the vault tests attack the vault, so 'is our "
            "security good' becomes a number we can re-run after every change "
            "instead of a feeling.",
            "We found this by auditing ourselves. Nothing was breached.",
        ],
        "notes": "Including this slide is the point of the deck, and if you only "
                 "remember one presenter note, make it this one. Anyone can "
                 "present a system as finished. Showing the weak spot, with the "
                 "fix already specified, is what a professional shop looks like - "
                 "and it is the reason he should believe the strong slides. If he "
                 "wants to contribute somewhere real, this is the most useful "
                 "door in the whole deck: it is exactly the kind of methodical "
                 "work someone with IT experience is good at.",
        "terms": ["bearer token", "test vault"],
    },
    {
        "section": "Security",
        "title": "The model itself is a supply chain",
        "short": [
            "For medical work, the model must be one we can trust completely.",
            "Not Chinese-made. Preferably fully open about its training.",
            "Locked-down network means local weights cannot phone home.",
            "The real risk is behaviour, not networking. Validation covers it.",
        ],
        "detail": [
            "For anything touching claims, where the model came from is a "
            "security question, not a preference. The requirement is American-"
            "made and, ideally, fully open about what it was trained on.",
            "The fear people have - a model 'phoning home' - is already handled "
            "here. The AI processes are blocked from the internet at the firewall, "
            "so weights running locally cannot send anything anywhere. That is "
            "enforced, not hoped.",
            "The real risk from foreign weights is subtler: a model trained to "
            "behave badly on specific inputs. Networking controls do nothing "
            "about that.",
            "Which is why the answer is the same one that already works - the "
            "model never gets to be the authority. Mechanical validation "
            "decides, and it caught a bad diagnosis code the model was confident "
            "about.",
            "Worth knowing: the current chat model is built on a French open "
            "base, not a Chinese one.",
        ],
        "notes": "There is a real distinction to draw if he is interested. Some "
                 "models are American but weights-only - you get the finished "
                 "model and cannot audit what went into it. A smaller set "
                 "publishes the training data and the code too, which is the only "
                 "case where 'ours' means something you can actually verify "
                 "rather than trust. That is the category to prefer for the "
                 "claims role. Also worth saying: this is a slide about "
                 "defending against a threat nobody has aimed at us yet, which "
                 "is the right time to build the defence.",
        "terms": ["abliterated", "LoRA"],
    },

    # ------------------------------------------------- Pictures and video
    {
        "section": "Pictures and video",
        "title": "It makes pictures and video too",
        "short": [
            "Images in seconds. Editing by description.",
            "Video from a sentence - 5 seconds at 480p in about 4 minutes.",
            "1080p exists and costs about 22 minutes.",
            "All on our card. No subscription, no watermark, no upload.",
        ],
        "detail": [
            "Images generate in seconds, and there is a separate model for "
            "editing an existing picture by describing the change.",
            "Video generates from a written prompt. Measured on our card: five "
            "seconds at 480p takes about four minutes, at 720p about eight, and "
            "at 1080p about twenty-two.",
            "Portrait works as well as landscape, and length limits are enforced "
            "by the server because the card runs out of memory rather than "
            "slowing down.",
            "All of it local. Nothing uploaded, no subscription, no watermark, no "
            "terms of service deciding what we may generate.",
            "Video cannot be split across machines - unlike chat, the maths does "
            "not divide - so more towers will never make this faster. Only a "
            "better card will.",
        ],
        "notes": "Demo this rather than describing it; it is the most immediately "
                 "impressive thing in the house and it does not need explaining. "
                 "Start a 480p clip early and let it finish while you talk "
                 "through other slides. Be straight that it is not Hollywood - "
                 "it is four-step generation on a consumer card, and the "
                 "achievement is that it runs here at all for free rather than "
                 "that it beats a studio.",
        "terms": ["diffusion", "NF4", "VRAM"],
    },
    {
        "section": "Pictures and video",
        "title": "This deck was made by Thunder",
        "short": [
            "Written, illustrated and narrated on our own hardware.",
            "No cloud AI touched it.",
            "Which makes it the demo, not a slideshow about the demo.",
        ],
        "detail": [
            "The artwork on these slides was generated on our 3090. The narration "
            "is Thunder's own voice. Some of the copy was drafted by Thunder and "
            "edited by a person.",
            "Nothing in this presentation went through a cloud AI service.",
            "Which is the point worth making twice: the thing explaining the "
            "system is itself produced by the system. If it can build its own "
            "onboarding deck, the claim that it can read a claims form is not a "
            "promise.",
        ],
        "notes": "Good place to be a little theatrical - play the narration for "
                 "one slide rather than explaining that narration exists. Be "
                 "honest about the division of labour if he asks: the technical "
                 "accuracy was written by a person because being wrong about our "
                 "own system in front of him would be worse than being "
                 "impressive, and the art and voice are genuinely Thunder's.",
        "terms": [],
    },

    # ------------------------------------------------------- Where this goes
    {
        "section": "Where this goes",
        "title": "The business, honestly",
        "short": [
            "The family practice bills by hand and pays for cloud storage.",
            "Thunder is local, so it needs no patient-data contract.",
            "That is a real moat, not a pitch.",
            "First: replace the hand-billing. Then look outward.",
        ],
        "detail": [
            "The immediate opportunity is in the family: claims are billed by "
            "hand on paper, and the practice pays a cloud provider to store "
            "records.",
            "A cloud AI cannot legally handle patient data for them without a "
            "signed agreement most providers will not offer a practice this "
            "size. Thunder does not need one, because the data never leaves the "
            "building.",
            "That is a genuine structural advantage rather than a sales line - "
            "it comes from the architecture, and a competitor with a cloud "
            "product cannot copy it without becoming local too.",
            "The order matters: make the family's billing work first, with real "
            "records and real accountability. Everything outward-facing depends "
            "on having done it once, properly.",
        ],
        "notes": "This is where he can see himself, so slow down and leave "
                 "silence. He is closer to the practice than to the code, and "
                 "the paperwork half of compliance - policies, training, risk "
                 "analysis, chasing agreements - is genuinely the critical path "
                 "and genuinely suits someone with IT experience who can write. "
                 "That is not a made-up job to include him; it is the actual "
                 "blocker.",
        "terms": ["BAA", "HIPAA"],
    },
    {
        "section": "Where this goes",
        "title": "Our own model - the real version of that goal",
        "short": [
            "Training a frontier model from scratch is not reachable. Straight up.",
            "Teaching an open model our specific job is reachable.",
            "A specialist can beat a giant generalist at one narrow task.",
            "Nobody else has our data. That is the actual advantage.",
        ],
        "detail": [
            "The honest version first: training a frontier model from scratch "
            "costs upwards of a hundred million dollars and tens of thousands of "
            "specialised chips. That is not a budget problem to solve, it is a "
            "different sport.",
            "What is reachable on the hardware in this house: taking an open "
            "American model and training it further on our own domain - our "
            "forms, our payers, our denial patterns.",
            "That produces a specialist. And on one narrow, high-repetition job "
            "with good validation around it, a well-tuned small model genuinely "
            "beats a giant generalist, because the giant is trying to be good at "
            "everything.",
            "The advantage is not compute, it is data nobody else has.",
            "So the goal stands, restated accurately: not 'our own ChatGPT', but "
            "the best claims model in existence, because it was trained on the "
            "only copy of the right material.",
        ],
        "notes": "Blayne has asked for this repeatedly and it matters to him, so "
                 "do not flatten it into 'impossible' - flatten it into 'not that "
                 "way, this way'. The reframe is real, not a consolation: a "
                 "narrow specialist outperforming a generalist on one task is "
                 "how small teams actually win, and it is achievable on the card "
                 "already in the rack. Timeline is deliberately not on this slide. "
                 "It is a direction, not a date.",
        "terms": ["LoRA", "tok/s"],
    },
    {
        "section": "Where this goes",
        "title": "What is next, in order",
        "short": [
            "Authentication on every service. The known weak spot.",
            "A test suite that attacks our own network.",
            "The overnight worker: queue at night, review in the morning.",
            "Then the claims fine-tune.",
        ],
        "detail": [
            "Authentication on every service across the fleet. Unglamorous "
            "plumbing, and the single biggest gap we know about.",
            "A security test suite aimed at our own network, built the way the "
            "vault tests were - mostly attacks, re-runnable, producing a number "
            "rather than an opinion.",
            "The overnight worker: queue up work at night, let the slow "
            "distributed setup grind through it, and have drafts and flags "
            "waiting in the morning. This is the one job where 1.8 tokens per "
            "second is genuinely fine, because nobody is sitting there.",
            "Then the claims fine-tune, once there is enough reviewed real data "
            "to train on honestly.",
            "Deliberately not on this list: anything outward-facing before the "
            "family's billing works end to end.",
        ],
        "notes": "Ordered by dependency rather than excitement, and that is worth "
                 "pointing out - it is the difference between a roadmap and a "
                 "wishlist. If he wants to pick something up, the top two are the "
                 "most delegable work in the entire system: both are methodical, "
                 "both are testable, and neither requires knowing how a model "
                 "works.",
        "terms": [],
    },

    # ------------------------------------------------------------ Working here
    {
        "section": "Working here",
        "title": "How we actually work",
        "short": [
            "Build it, do not describe it.",
            "Verify before claiming. Check the log, check the endpoint.",
            "Write down anything learned the hard way.",
            "Baby steps. One thing at a time.",
        ],
        "detail": [
            "Build it, do not describe it. Hours have been lost to discussing "
            "features that did not exist yet. If it can be built in the time it "
            "takes to explain it, build it.",
            "Verify before claiming. 'Found the bug' before confirming it cost "
            "real trust once. Check the log, check the endpoint, check the "
            "installed app - then say it.",
            "Write down anything learned the hard way, immediately. The handbook "
            "exists so nobody pays twice for the same lesson, and it is why a "
            "second person can be useful here in a day rather than a month.",
            "One thing at a time, finished, before the next. Five half-built "
            "features are worth nothing.",
            "Say the weak part out loud. Every slide in this deck that admits a "
            "limit made the rest more believable.",
        ],
        "notes": "Close on this rather than on technology, because it is what "
                 "makes the rest repeatable and it is what you are actually "
                 "asking him to join. Then hand him something small and real - "
                 "the authentication work or the security test suite - because "
                 "nobody understands a system by being shown it. Ask what he "
                 "wants to poke at first and let the answer decide where you go "
                 "next.",
        "terms": [],
    },
]


def sections_with_slides() -> list[dict]:
    """Contents: each section with the slide numbers it covers."""
    out: list[dict] = []
    for name in SECTIONS:
        idx = [i for i, s in enumerate(SLIDES) if s["section"] == name]
        if idx:
            out.append({"name": name, "first": idx[0], "count": len(idx)})
    return out


def validate() -> list[str]:
    """Catch the mistakes that only show up on a television.

    Every slide needs both depth levels and a presenter note, every tapped term
    needs a definition, and every section named in SECTIONS needs slides -
    otherwise the contents menu offers a chapter that goes nowhere.
    """
    problems = []
    for i, s in enumerate(SLIDES):
        where = f"slide {i} ({s.get('title', 'untitled')!r})"
        for field in ("section", "title", "short", "detail", "notes"):
            if not s.get(field):
                problems.append(f"{where}: missing {field}")
        if s.get("section") not in SECTIONS:
            problems.append(f"{where}: section {s.get('section')!r} not in SECTIONS")
        for t in s.get("terms", []):
            if t not in GLOSSARY:
                problems.append(f"{where}: term {t!r} has no glossary entry")
        if len(s.get("short", [])) > 6:
            problems.append(f"{where}: {len(s['short'])} short lines, max 6 on a TV")
    for name in SECTIONS:
        if not any(s["section"] == name for s in SLIDES):
            problems.append(f"section {name!r} has no slides")
    return problems
