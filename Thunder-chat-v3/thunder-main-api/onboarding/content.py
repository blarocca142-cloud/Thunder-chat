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
    "NF4": "A different 4-bit format that our card does support, unlike fp8. It "
           "is what makes video generation possible here at all.",
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

# Each chapter gets its own accent and a one-line promise for the contents grid.
# The colour is not decoration: on a deck this long the fastest way to know where
# you are is that the room changed colour, and it means a glance at the progress
# rail tells you how much of a chapter is left.
# Chosen for a light background. The first set was picked against near-black and
# they were pastel - on paper they washed out to nothing, which was part of why
# the deck read as dated. These are deep enough to carry text and a highlight.
SECTION_META = {
    "Start here":         {"accent": "#C2410C", "blurb": "What this is, in ninety seconds"},
    "The machines":       {"accent": "#1D4ED8", "blurb": "Six towers, and which one matters"},
    "Thunder":            {"accent": "#B45309", "blurb": "The assistant, and how it remembers"},
    "Odris":              {"accent": "#047857", "blurb": "The watchman that cannot be silenced"},
    "The call organizer": {"accent": "#7C3AED", "blurb": "Phone logs to a usable sheet"},
    "Claims":             {"accent": "#0E7490", "blurb": "The money, and how it is protected"},
    "Security":           {"accent": "#BE123C", "blurb": "Honest grade, weak spots included"},
    "Pictures and video": {"accent": "#A21CAF", "blurb": "The part that demos itself"},
    "Where this goes":    {"accent": "#A16207", "blurb": "The business and the real roadmap"},
    "Working here":       {"accent": "#334155", "blurb": "How we actually work"},
}

# Layouts. A deck where every slide is a bulleted list reads as a document
# someone forgot to finish, and that was the honest complaint about the first
# version of this. Numbers get to be numbers.
#
#   cover   the opening slide, oversized
#   bullets the default
#   stats   a `stats` list rendered as big figures, with `short`/`detail` beneath
LAYOUTS = {"cover", "bullets", "stats"}

SLIDES = [
    # ---------------------------------------------------------------- Start here
    {
        "section": "Start here",
        "layout": "cover",
        "title": "A fully local AI stack, built for data that cannot leave the building",
        "short": [
            "Six commodity machines. *No external inference, no API keys.*",
            "Chat, generative media, and a medical claims pipeline.",
            "*Locality is the architecture*, not a deployment preference.",
        ],
        "detail": [
            "Six commodity x86 machines on a private network, running open-weight "
            "models locally. No hosted inference, no API keys, no third-party "
            "dependency in the data path.",
            "Three workloads on one stack: a conversational assistant, generative "
            "image and video, and a document-understanding pipeline for medical "
            "claims.",
            "The constraint driving all of it: protected health information cannot "
            "be sent to a hosted model without a signed business associate "
            "agreement, and providers will not extend one to a practice this size.",
            "Locality is therefore not a preference to be traded away for "
            "convenience. It is the property the system is designed around, and "
            "every decision that follows is downstream of it.",
        ],
        "notes": "Open here and stop talking. Let 'no external inference' sit in "
                 "the room before any hardware. It is the only slide that matters "
                 "if you get one. Dad knows IT, so he will start hunting for the "
                 "catch immediately - the catch is throughput and scale, and you "
                 "volunteer it yourself two slides from now rather than letting him "
                 "find it. Volunteering it is what buys credibility for everything "
                 "after.",
        "terms": ["BAA", "PHI"],
    },
    {
        "section": "Start here",
        "title": "System components",
        "short": [
            "*Thunder* - conversational assistant with retrieval and speech.",
            "*Odris* - independent monitoring and operations plane.",
            "*Call consolidation* - record linkage over telephony metadata.",
            "*Claims* - document understanding with mechanical adjudication.",
            "*Security* - encryption at rest, TLS, and intrusion detection.",
        ],
        "detail": [
            "Thunder - a 23.6-billion-parameter assistant with a three-tier "
            "retrieval system, nine synthesised voices, and an Android client.",
            "Odris - a separate monitoring plane on separate hardware, holding the "
            "fleet-wide health model and the operations dashboard.",
            "Call consolidation - record linkage and label normalisation over "
            "exported telephony metadata, producing an analyst-ready dataset.",
            "Claims - optical character recognition, field extraction, and "
            "deterministic validation. The pipeline submits nothing; it produces "
            "adjudicated output for human sign-off.",
            "Security - envelope encryption at rest, mutual TLS between nodes "
            "under a private certificate authority, audited access, and canary "
            "artifacts for intrusion detection.",
            "Each of these is deployed and running, not specified.",
        ],
        "notes": "This is the table of contents in disguise. If he wants one area, "
                 "jump there from Contents - the deck is built to be entered in the "
                 "middle. Do not rush the claims line; that one is the family's "
                 "actual money. Say 'the pipeline submits nothing' out loud here, "
                 "because it pre-empts every liability question he is about to ask.",
        "terms": [],
    },

    # -------------------------------------------------------------- The machines
    {
        "section": "The machines",
        "title": "Fleet topology: one accelerator, five supporting nodes",
        "short": [
            "*thunder-main* - RTX 3090, 24 GB VRAM. All inference.",
            "*odris* - monitoring plane. 4 GB GPU, deliberately unused.",
            "*serverus* - Xeon E3-1230 v5. Conversation store.",
            "*thunder-engine* - classification. *thunder-cache* - batch capacity.",
            "*One accelerator does the compute.* The rest provide durability.",
        ],
        "detail": [
            "thunder-main (.10) - RTX 3090, 24 GB VRAM, 30 GB system memory. All "
            "language and diffusion inference executes here.",
            "odris (.15) - Radeon 550, 4 GB. Too small to host a model, which is "
            "appropriate: its workload is observation, and it runs on CPU.",
            "serverus (.13) - Xeon E3-1230 v5, the strongest CPU in the fleet. "
            "Holds the conversation store. Substantially under-utilised.",
            "thunder-engine (.12) - binary safety classification.",
            "thunder-cache (.11) - spare capacity, reserved for overnight batch.",
            "The honest description: a single accelerator performs the computation, "
            "and five machines provide availability, observability and storage.",
        ],
        "notes": "He will ask why the six are not pooled into one larger machine. "
                 "That is the next slide and you have measurements, so let him ask "
                 "it - answering a question he just raised lands far better than "
                 "pre-empting it. On cost: the towers are retired office desktops; "
                 "the 3090 is the only meaningful capital in the rack.",
        "terms": ["VRAM"],
    },
    {
        "section": "The machines",
        "layout": "stats",
        "title": "A negative result: distributed inference across heterogeneous nodes",
        "stats": [
            {"value": "55.5", "unit": "tok/s", "label": "Single 3090", "tone": "good"},
            {"value": "2.97", "unit": "tok/s", "label": "Adding serverus", "tone": "bad"},
            {"value": "1.80", "unit": "tok/s", "label": "Adding all three nodes", "tone": "bad"},
        ],
        "short": [
            "Identical model and prompt across three configurations.",
            "*Adding nodes reduced throughput by 40% against a single node.*",
            "Cause: per-token pipeline latency and layer placement on older silicon.",
            "Local memory ~12 GB/s against 0.125 GB/s over gigabit Ethernet.",
            "*Published against our own hypothesis, because we measured it.*",
        ],
        "detail": [
            "Method: llama.cpp RPC backend, identical 24B model, identical prompt, "
            "three configurations measured end to end.",
            "Single 3090 in isolation: 55.5 tokens per second. Adding serverus: "
            "2.97. Adding all three supporting nodes: 1.80.",
            "Adding the two weakest nodes degraded throughput by roughly 40% "
            "relative to using one node alone.",
            "The mechanism is not mysterious. Every token traverses the full "
            "pipeline, so aggregate throughput converges on the slowest member and "
            "degrades as the topology grows. Local memory bandwidth is roughly 12 "
            "GB/s; gigabit Ethernet is 0.125 GB/s.",
            "The conclusion generalises: one machine with sufficient memory "
            "outperforms several machines with pooled memory by more than an order "
            "of magnitude.",
            "Retained use: at 1.80 tokens per second the configuration still "
            "produces roughly 50,000 tokens over an eight-hour window, which suits "
            "asynchronous batch work where no one is waiting.",
        ],
        "notes": "This is the slide that earns his trust, so do not hurry it. He is "
                 "the kind of engineer who will respect that we tested the "
                 "appealing idea and published a result against ourselves. If he "
                 "pushes on whether it was wasted, the retained use is real - the "
                 "overnight batch worker wants exactly this. Slow is acceptable "
                 "when nobody is waiting.",
        "terms": ["tok/s", "RPC backend"],
    },
    {
        "section": "The machines",
        "title": "Working inside hard constraints: memory, precision, bandwidth",
        "short": [
            "Main's board caps at *32 GB*. No upgrade path exists.",
            "Overflow goes to three striped SSDs: *1.55 GB/s measured*.",
            "*Twelve times the bandwidth* of borrowing from another node.",
            "The 3090 is compute capability 8.6, so *fp8 is absent, not disabled*.",
            "Every constraint is documented rather than rediscovered.",
        ],
        "detail": [
            "thunder-main is a Lenovo ThinkCentre with four populated DIMM slots. "
            "32 GB is the board maximum and there is no upgrade path.",
            "Overflow is handled with 32 GB of swap on each of three SSDs at equal "
            "priority, so the kernel stripes across all three. Measured at 1.55 "
            "GB/s - roughly twelve times the bandwidth available from another node "
            "over gigabit Ethernet.",
            "The 3090 is compute capability 8.6. fp8 requires 8.9, so the format "
            "is absent from the silicon rather than disabled in software. NF4 "
            "quantisation is supported and is what makes video generation feasible.",
            "One allocator setting is load-bearing for 720p and above: without "
            "expandable segments, generation exhausts memory rather than running "
            "slowly.",
            "All of this is recorded in an engineering handbook. The expensive way "
            "to hold this knowledge is to derive it twice.",
        ],
        "notes": "Move briskly unless he bites - this is the most technical slide "
                 "in the deck. The point to land is cultural rather than technical: "
                 "every hard-won constraint is written down, which is what makes a "
                 "second engineer productive in a day instead of a month. That is "
                 "also the honest answer to 'could you actually hire into this'.",
        "terms": ["swap", "fp8", "NF4", "VRAM"],
    },

    # ------------------------------------------------------------------ Thunder
    {
        "section": "Thunder",
        "layout": "stats",
        "title": "Thunder: a 23.6B model serving interactively on one consumer GPU",
        "stats": [
            {"value": "23.6B", "unit": "parameters", "label": "Q4_K_M quantisation", "tone": "good"},
            {"value": "55", "unit": "tok/s", "label": "Above reading speed", "tone": "good"},
            {"value": "0", "unit": "external calls", "label": "Nothing leaves the network", "tone": "good"},
        ],
        "short": [
            "23.6B parameters quantised to *roughly a quarter* of full precision.",
            "Open Mistral base with a custom system prompt.",
            "Android client, nine voices, generative media, code retention.",
            "*No API key exists anywhere in this system.*",
        ],
        "detail": [
            "23.6 billion parameters at Q4_K_M, which fits 24 GB of VRAM and "
            "serves at approximately 55 tokens per second - above sustained human "
            "reading speed.",
            "Built on an open Mistral base with a custom system prompt, tuned for "
            "direct technical answers rather than hedged assistant register.",
            "Surfaces: an Android client, nine synthesised voices, image and video "
            "generation, and durable storage for generated code.",
            "There is no API key in this system. Loss of internet connectivity does "
            "not degrade it, and no external pricing or terms change can affect it.",
        ],
        "notes": "Be direct if he asks how it compares to a frontier model: a 24B "
                 "is genuinely weaker on multi-step reasoning and long context, and "
                 "claiming otherwise gets found out in five minutes of him using "
                 "it. Where it wins is the axis that matters here - it is ours, it "
                 "is private, it is free to operate, and it has our domain context. "
                 "Frame it as a specialist, never as a smaller frontier model.",
        "terms": ["quantised", "Q4_K_M", "abliterated", "tok/s", "Ollama"],
    },
    {
        "section": "Thunder",
        "title": "Retrieval architecture: profile, semantic facts, documents",
        "short": [
            "A always-resident profile: domain, hardware, operator context.",
            "Facts retrieved by *semantic similarity*, only when relevant.",
            "Documents chunked on headings and indexed.",
            "*Most of the gap to a frontier model is context, not reasoning.*",
        ],
        "detail": [
            "Three tiers. An always-resident profile carrying operator context, "
            "fleet topology, and the hardware facts most often gotten wrong. This "
            "is empirically the single largest lever on answer quality.",
            "Facts retrieved by embedding similarity rather than keyword match, and "
            "injected only when relevant to the query.",
            "Documents - the engineering handbook and the security notes - chunked "
            "on heading boundaries and indexed for retrieval.",
            "Two findings worth carrying away. Retrieval succeeding is not "
            "retrieval being used: passages recalled at 0.749 similarity were "
            "ignored in favour of the model's prior until they were repositioned "
            "immediately before the user turn and labelled authoritative.",
            "And never re-ingest model output. An early configuration learned one "
            "of the model's own fabricated file paths as a durable fact.",
        ],
        "notes": "The second finding is the important one and it is worth "
                 "delivering slowly, because it separates a system that improves "
                 "from one that decays. A model writing its own beliefs into its "
                 "own long-term store compounds: one confident error becomes "
                 "permanent context for every subsequent answer, and afterwards "
                 "there is no way to determine which facts were ever grounded. If "
                 "he has run data systems he will recognise this instantly.",
        "terms": [],
    },
    {
        "section": "Thunder",
        "title": "Human-in-the-loop memory writes, and why autonomy was rejected",
        "short": [
            "A nightly job reads *operator turns only* - never model output.",
            "*It proposes. It does not commit.*",
            "Contradictory proposals are flagged against each other.",
            "A human approves or rejects. *Always.*",
        ],
        "detail": [
            "A scheduled job processes the previous day's conversations, reading "
            "only the operator's turns and never the model's own responses.",
            "Its output is a set of candidate facts held in a review queue. It has "
            "no write path to durable memory.",
            "Where two candidates conflict, both are flagged against each other "
            "rather than one being silently selected. At least one is wrong, and "
            "that is an operator decision.",
            "Nothing enters long-term memory without explicit approval. This is an "
            "invariant, not a configuration flag, and it is documented as such so "
            "that it is not later optimised away.",
        ],
        "notes": "If he asks why not let it learn autonomously - that is precisely "
                 "the failure mode. Unsupervised self-write sounds like progress "
                 "and produces a system nobody can audit within months, with no way "
                 "to separate grounded facts from fabricated ones. The review queue "
                 "is the reason this can be handed to an employee at all. Connect "
                 "it to claims: the model proposes, a deterministic check decides.",
        "terms": [],
    },

    # -------------------------------------------------------------------- Odris
    {
        "section": "Odris",
        "title": "Observability under compromise",
        "short": [
            "*The watcher must not be controllable by the watched.*",
            "Separate host, separate prompt, separate context.",
            "Reaches into Main through a *single forced read-only command*.",
            "If Main is compromised, its warnings remain trustworthy.",
        ],
        "detail": [
            "Odris is not the assistant in another role. It has its own system "
            "prompt and its own context - live machine telemetry rather than "
            "conversation history.",
            "The governing principle: the watcher must not be controllable by the "
            "watched. Any alarm the monitored host can suppress is not an alarm.",
            "Implementation: Odris holds a key into Main restricted to one forced "
            "command with no interactive shell. Full compromise of Main does not "
            "grant use of that key for anything other than the single read.",
            "It runs on the weakest machine in the fleet, because observation does "
            "not require an accelerator.",
            "This is the same separation principle behind an off-host log "
            "collector, applied at the scale we actually operate at.",
        ],
        "notes": "Be proud of this one - it is genuinely correct security design "
                 "and the same reasoning behind a write-only log server in any "
                 "serious environment. The restricted key is the detail worth "
                 "naming explicitly, because it is the part that holds even under "
                 "total compromise of the monitored host.",
        "terms": ["systemd"],
    },
    {
        "section": "Odris",
        "title": "Incident report: a correct alert with no path to the operator",
        "short": [
            "The phone reported a degraded drive on serverus. *The finding was real.*",
            "Opening the client showed nothing. The assistant had no knowledge of it.",
            "*Three independent defects*, none of them the detection logic.",
            "Alerts now persist, surface, and are available to both assistants.",
        ],
        "detail": [
            "Observed: a notification reporting 6.4 years of power-on time on the "
            "boot device of serverus. Opening the client displayed nothing, and "
            "querying the assistant about it returned no knowledge of the finding.",
            "The detection was correct. The drive is 6.4 years old and carries "
            "both /boot and root.",
            "Three independent defects. The digest was recomputed per request and "
            "discarded, so no record survived to be opened. No view in the client "
            "had ever rendered it. And the finding was never placed in the "
            "assistant's context, so its ignorance was accurate.",
            "Resolved: findings now persist with first-observed and "
            "still-present state, the notification resolves to the finding, and "
            "both assistants receive current telemetry before answering.",
            "The general lesson: a monitoring system is only as good as its "
            "delivery path, and delivery is the part that is never tested.",
        ],
        "notes": "Tell this as a narrative, because it is the most honest slide in "
                 "the deck and the honesty is what you are actually selling. It "
                 "demonstrates that the system caught a real fault, that we "
                 "diagnosed why reporting failed, and that the fix was three fixes "
                 "rather than one guess. If he has ever carried a pager, 'the "
                 "monitoring was right and the dashboard was empty' will land hard. "
                 "It also demos live - open the Odris tab.",
        "terms": [],
    },

    # ------------------------------------------------- The call organizer
    {
        "section": "The call organizer",
        "title": "Record linkage and label normalisation over telephony metadata",
        "short": [
            "Exported call logs in, *analyst-ready dataset out*.",
            "Automated filtering of unsolicited and machine-originated traffic.",
            "*Caller-ID label normalisation* - carrier placeholders are not names.",
            "One engine, two front ends: browser and desktop.",
        ],
        "detail": [
            "Input is an exported call log. Output is a structured dataset "
            "organised for human analysis rather than for the carrier's own "
            "reporting format.",
            "Unsolicited and machine-originated traffic is filtered on pattern and "
            "repetition characteristics.",
            "Caller-ID labels require normalisation before the data is usable. "
            "Real-world fields contain the number repeated inside its own label, "
            "and carrier placeholders such as 'Wireless Caller', 'Unknown' and "
            "'Unavailable'. None are names, and all of them contaminate a name "
            "column if nothing removes them.",
            "Two front ends over one processing engine - a browser interface and a "
            "desktop application - so the implementations cannot diverge.",
            "It is the smallest component here and the most immediately useful, "
            "which is a common outcome.",
        ],
        "notes": "He can evaluate this one instantly because he has seen the raw "
                 "data, so consider demoing it live - it is fast and unglamorous "
                 "and that is the point. Mention the discipline: the repository "
                 "excludes call data, spreadsheets and contact lists by policy, "
                 "because those carry real numbers and real names. Code is "
                 "shareable; the data never leaves.",
        "terms": [],
    },

    # ------------------------------------------------------------------- Claims
    {
        "section": "Claims",
        "title": "Document understanding with mechanical adjudication",
        "short": [
            "Scan, extract, then *validate deterministically*.",
            "*The pipeline submits nothing.* Output is adjudicated for sign-off.",
            "It has already caught *the model corrupting a diagnosis code*.",
            "Current practice is manual preparation on paper.",
        ],
        "detail": [
            "Pipeline: scan, optical character recognition, field extraction, then "
            "deterministic validation of every field - check digits, code format "
            "conformance, date feasibility.",
            "Validation failures are blocked. Repaired or incomplete records enter "
            "a review queue for a human. Nothing is transmitted automatically at "
            "any point.",
            "The validation layer has already justified itself: it detected the "
            "model corrupting an ICD-10 diagnosis code and omitting the billing "
            "provider entirely. The model was confidently wrong, and the "
            "deterministic check was indifferent to its confidence.",
            "That is the governing design principle for the whole pipeline. The "
            "model proposes; arithmetic adjudicates.",
            "The current process is manual preparation on paper, with records held "
            "in third-party cloud storage.",
        ],
        "notes": "The ICD-10 detection is the single most persuasive fact in this "
                 "deck for a family business, so give it room. It demonstrates that "
                 "we do not trust our own model and that we built the component "
                 "that checks it. Nobody selling him an AI claims product will tell "
                 "him a story about their model being wrong. 'The pipeline submits "
                 "nothing' answers every liability question - say it first.",
        "terms": ["OCR", "ICD-10"],
    },
    {
        "section": "Claims",
        "layout": "stats",
        "title": "Encryption at rest: envelope keys, searchable ciphertext, audited access",
        "stats": [
            {"value": "AES-256", "unit": "GCM", "label": "Per-record data keys", "tone": "good"},
            {"value": "34/34", "unit": "adversarial", "label": "Test suite passing", "tone": "good"},
            {"value": "0", "unit": "records", "label": "Real PHI to date", "tone": "neutral"},
        ],
        "short": [
            "Per-record data keys under a *single wrapped master key*.",
            "Authenticated encryption, so *tampering fails loudly*.",
            "Searchable without decryption via deterministic indexes.",
            "*34 adversarial tests*, all passing, run on every change.",
        ],
        "detail": [
            "Every record is encrypted under its own data key; those keys are "
            "wrapped by a single master key. Compromise of one record's key does "
            "not extend to any other, and master-key rotation does not require "
            "re-encrypting the corpus.",
            "AES-256-GCM provides authenticated encryption, so modified ciphertext "
            "fails decryption rather than silently yielding incorrect plaintext.",
            "Records are searchable without decryption using deterministic "
            "indexes over field values.",
            "Every access is written to an audit log. Backups are separately "
            "encrypted under their own passphrase.",
            "The test suite is 34 checks, predominantly adversarial: ciphertext "
            "tampering, record relocation, incorrect keys, weak passphrases, and "
            "modified backup archives. All pass, and the suite runs in seconds, so "
            "it runs on every change.",
        ],
        "notes": "State both limitations yourself before he finds them, because an "
                 "engineer who spots an unstated limitation stops believing the "
                 "rest of the deck. One: encryption at rest provides no protection "
                 "against an adversary with root on a running host - the keys are "
                 "resident by definition. Two: deterministic indexes leak equality, "
                 "so they reveal that two records share a value. Both are in our "
                 "own documentation. Saying them aloud is what makes 34 passing "
                 "tests credible.",
        "terms": ["envelope encryption", "AES-256-GCM", "blind index", "test vault", "PHI"],
    },
    {
        "section": "Claims",
        "title": "Scope and limitations",
        "short": [
            "*All development and testing has used synthetic records.*",
            "Technical safeguards are implemented and individually verified.",
            "*Cryptography is not compliance.*",
            "Risk analysis, policy, training, agreements. *Not engineering work.*",
        ],
        "detail": [
            "All development and testing to date has used synthetic patient "
            "records. No protected health information has entered any component, "
            "and that remains the case until a deliberate decision changes it.",
            "The technical safeguards are implemented and each was verified rather "
            "than assumed: encryption at rest, encrypted backups, authentication, "
            "transport security between nodes, audit logging, intrusion detection.",
            "None of that constitutes compliance. The HIPAA Security Rule has an "
            "administrative half - documented risk analysis, written policy, "
            "workforce training, and executed agreements with every party handling "
            "the data.",
            "That half is not engineering work and cannot be produced by a model. "
            "It is the genuine remaining prerequisite before a single real record "
            "is processed.",
            "Stating this precisely is not modesty. It is the difference between a "
            "defensible position and a liability.",
        ],
        "notes": "Do not soften this slide, and do not let enthusiasm in the room "
                 "soften it either. If he leaves believing we are compliant because "
                 "the cryptography is sound, that is actively dangerous for the "
                 "family. The correct framing: we have completed the expensive half "
                 "that most small practices never manage, and the remainder is "
                 "documentation and decisions a person has to own. If he wants a "
                 "role, that half is genuinely well suited to someone with IT "
                 "background who can write policy.",
        "terms": ["HIPAA", "BAA", "PHI"],
    },

    # ------------------------------------------------------------------ Security
    {
        "section": "Security",
        "title": "Canary artifacts: high-signal intrusion detection",
        "short": [
            "Decoy files placed where an intruder would look.",
            "*Nothing legitimate reads them, so any access is signal.*",
            "Access raises an alert immediately, to the log and the operator.",
            "*Detection, not prevention* - and the distinction is the value.",
        ],
        "detail": [
            "Files named to resemble high-value targets - patient exports, billing "
            "records, a backup private key - are placed where an intruder would "
            "look. All are synthetic.",
            "No legitimate process reads them, which makes any access a signal "
            "rather than an event requiring interpretation. This is the highest "
            "signal-to-noise detection available at this cost.",
            "Access triggers an immediate alert into the system journal and to the "
            "operator.",
            "The classification matters: this is detection, not prevention. It "
            "cannot stop an intrusion, and by the time one fires the adversary is "
            "already inside. What it provides is time-to-detection measured in "
            "seconds rather than months, which is the variable that determines how "
            "severe a breach becomes.",
        ],
        "notes": "There is a good incident here if he wants one. These fired at "
                 "03:12 and read as a genuine intrusion for about an hour. Root "
                 "cause was the operator's own recursive file search sweeping them "
                 "up - and the reason it initially read as an intrusion is that the "
                 "log records UTC, so 07:12 in the log was 03:12 locally. Two fixes "
                 "followed: the decoys moved outside any path a code search "
                 "traverses, and every timestamp shown to a person is converted "
                 "first. A false positive you can explain is worth more than a "
                 "system that stays quiet.",
        "terms": ["honeyfile", "canary"],
    },
    {
        "section": "Security",
        "title": "Threat model and current posture, including known gaps",
        "short": [
            "Strong: the claims vault, the operations dashboard, egress control.",
            "*Weak: the internal network is trusted more than it should be.*",
            "*Exactly one service on the fleet performs authentication.*",
            "Identified by auditing ourselves. *No compromise occurred.*",
        ],
        "detail": [
            "Genuinely strong: the claims vault and its adversarial test suite; the "
            "operations dashboard, which is the one service enforcing "
            "authentication; and firewall-level egress control preventing the "
            "inference processes from reaching the internet at all.",
            "Genuinely weak, stated plainly: the fleet largely trusts any host "
            "already on the internal network. Across six machines and roughly a "
            "dozen services, exactly one performs authentication.",
            "That is a defensible posture for a residential network and an "
            "indefensible one for protected health information, which is the "
            "honest reason it appears in this deck.",
            "The remediation is not exotic - per-service authentication, which is "
            "largely plumbing. The plan is an adversarial test suite against our "
            "own network, built the way the vault suite was, so that posture "
            "becomes a number that can be re-measured after every change rather "
            "than a subjective assessment.",
            "This was identified by auditing ourselves. Nothing was compromised.",
        ],
        "notes": "Including this slide is the entire point of the deck, and if you "
                 "remember one presenter note make it this one. Anyone can present "
                 "a system as finished. Presenting the weak spot with the "
                 "remediation already specified is what a professional operation "
                 "looks like, and it is the reason he should believe the strong "
                 "slides. If he wants to contribute somewhere real, this is the "
                 "most useful door in the deck - methodical, testable work that "
                 "suits IT experience.",
        "terms": ["bearer token", "test vault"],
    },
    {
        "section": "Security",
        "title": "Model provenance as a supply-chain risk",
        "short": [
            "For clinical workloads, *provenance is a security property*.",
            "Egress is blocked at the firewall, so *local weights cannot exfiltrate*.",
            "*The residual risk is behavioural, not network* - and untestable by firewall.",
            "Mitigation: the model is never the authority. Validation is.",
        ],
        "detail": [
            "For anything touching claims, model provenance is a security question "
            "rather than a preference. The requirement is domestic origin and, "
            "ideally, published training data and methodology.",
            "The commonly-cited risk - a model exfiltrating data - is already "
            "mitigated here. The inference processes are blocked from the internet "
            "at the firewall, so locally-executed weights have no path out. That "
            "is enforced, not assumed.",
            "The residual risk from foreign weights is subtler and is not "
            "addressed by network controls at all: a model trained to behave "
            "incorrectly on specific inputs. No firewall detects that.",
            "The mitigation is the one already in production: the model is never "
            "the authority. Deterministic validation adjudicates, and it has "
            "already caught a diagnosis code the model was confident about.",
            "For completeness: the current chat model derives from a French open "
            "base, not a Chinese one.",
        ],
        "notes": "There is a real distinction to draw if he engages. Some "
                 "open-weight models are domestic but weights-only - you receive "
                 "the artefact and cannot audit what produced it. A smaller set "
                 "publishes training data and code, which is the only case where "
                 "'ours' is verifiable rather than trusted. That is the category to "
                 "prefer for the clinical role. Also worth saying: this slide "
                 "defends against a threat nobody has aimed at us, which is the "
                 "correct time to build the defence.",
        "terms": ["abliterated", "LoRA"],
    },

    # ------------------------------------------------- Pictures and video
    {
        "section": "Pictures and video",
        "layout": "stats",
        "title": "Generative media on consumer hardware: measured throughput",
        "stats": [
            {"value": "4", "unit": "minutes", "label": "5s at 480p", "tone": "good"},
            {"value": "8", "unit": "minutes", "label": "5s at 720p", "tone": "neutral"},
            {"value": "22", "unit": "minutes", "label": "5s at 1080p", "tone": "neutral"},
        ],
        "short": [
            "Stills in seconds. Editing conditioned on natural language.",
            "Video from text, at *four denoising steps*.",
            "Duration limits enforced server-side - *VRAM, not patience*.",
            "*Diffusion does not shard*, so additional nodes cannot help.",
        ],
        "detail": [
            "Still image generation completes in seconds, with a separate model "
            "for editing an existing image conditioned on a natural-language "
            "instruction.",
            "Text-to-video at four denoising steps. Measured on this hardware: "
            "five seconds of output takes approximately four minutes at 480p, "
            "eight at 720p, and twenty-two at 1080p.",
            "Portrait and landscape are both supported. Duration limits are "
            "enforced server-side because the binding constraint is VRAM "
            "exhaustion rather than degraded throughput.",
            "Entirely local: no upload, no subscription, no watermarking, and no "
            "external terms governing what may be generated.",
            "Unlike autoregressive inference, diffusion does not shard across "
            "hosts, so additional nodes cannot reduce these times. Only a larger "
            "accelerator can.",
        ],
        "notes": "Demonstrate rather than describe - this is the most immediately "
                 "impressive component and needs no explanation. Start a 480p clip "
                 "early and let it complete while you talk through other slides. Be "
                 "straight that this is four-step generation on a consumer card: "
                 "the achievement is that it runs here at zero marginal cost, not "
                 "that it competes with a studio.",
        "terms": ["diffusion", "NF4", "VRAM"],
    },
    {
        "section": "Pictures and video",
        "title": "This presentation was produced by the system it describes",
        "short": [
            "Narrated by the local speech model. Illustrated on the same GPU.",
            "*No hosted AI service was involved at any point.*",
            "*The artefact is the demonstration*, not a description of one.",
        ],
        "detail": [
            "The narration is synthesised locally by the speech model running on "
            "this hardware. Generated imagery comes from the same GPU. Portions of "
            "the copy were drafted by the local model and edited by a person.",
            "No hosted AI service was involved in producing this presentation.",
            "Which is the claim worth making twice: the artefact explaining the "
            "system was produced by the system. If it can generate its own "
            "onboarding material, the assertion that it can read a claims form is "
            "a demonstration rather than a promise.",
        ],
        "notes": "Be slightly theatrical here - play the narration for one slide "
                 "rather than explaining that narration exists. Be honest about the "
                 "division of labour if asked: technical accuracy was human-written, "
                 "because being wrong about our own system in front of him is worse "
                 "than being impressive, and the voice and imagery are genuinely "
                 "the local models.",
        "terms": [],
    },

    # ------------------------------------------------------- Where this goes
    {
        "section": "Where this goes",
        "title": "Deployment context: locality as a structural advantage",
        "short": [
            "The practice prepares claims manually and pays for cloud storage.",
            "Hosted AI requires an agreement *providers will not extend at this size*.",
            "*A local system needs no such agreement.*",
            "First the internal deployment. Only then anything external.",
        ],
        "detail": [
            "The immediate opportunity is internal: claims are prepared manually on "
            "paper, and records are held in third-party cloud storage at ongoing "
            "cost.",
            "A hosted model cannot lawfully process their patient data without a "
            "business associate agreement, and providers will not extend one to a "
            "practice of this size.",
            "A local system requires no such agreement, because the data does not "
            "leave the premises. This is a structural advantage rather than a "
            "commercial claim - it follows from the architecture, and a competitor "
            "with a hosted product cannot replicate it without becoming local.",
            "Sequencing matters. The internal deployment comes first, with real "
            "records and real accountability. Anything external depends on having "
            "done it once, properly.",
        ],
        "notes": "This is where he can see himself, so slow down and leave silence. "
                 "He is closer to the practice than to the code, and the "
                 "administrative half of compliance - policy, training, risk "
                 "analysis, executing agreements - is genuinely the critical path "
                 "and genuinely suits someone with IT background who can write. "
                 "That is not an invented role to include him; it is the actual "
                 "blocker.",
        "terms": ["BAA", "HIPAA"],
    },
    {
        "section": "Where this goes",
        "title": "Toward a domain-specific model: what is reachable",
        "short": [
            "*Frontier pre-training is not reachable.* Nine figures and a datacentre.",
            "*Domain adaptation of an open base is* - on the GPU already here.",
            "A narrow specialist can outperform a general model *on one task*.",
            "*The advantage is proprietary data*, not compute.",
        ],
        "detail": [
            "The honest position first: pre-training a frontier model requires "
            "expenditure in the hundreds of millions and tens of thousands of "
            "specialised accelerators. That is not a budget constraint to overcome; "
            "it is a different category of undertaking.",
            "What is reachable on this hardware: continued training of an open "
            "domestic base on our own domain - our forms, our payers, our denial "
            "patterns.",
            "That produces a specialist. On a narrow, high-repetition task with "
            "rigorous validation around it, a well-adapted small model can "
            "outperform a general frontier model, because the general model is "
            "optimising for breadth.",
            "The durable advantage is not compute. It is a proprietary corpus "
            "nobody else holds.",
            "So the objective restated precisely: not a general assistant of our "
            "own, but the strongest claims-adjudication model in existence, trained "
            "on the only copy of the relevant material.",
        ],
        "notes": "He has raised this repeatedly and it matters to him, so do not "
                 "flatten it into 'impossible' - flatten it into 'not by that "
                 "route, by this one'. The reframe is real rather than "
                 "consolation: a narrow specialist beating a generalist on one task "
                 "is how small teams actually win, and it is achievable on the card "
                 "already in the rack. No timeline on this slide deliberately. It "
                 "is a direction, not a commitment.",
        "terms": ["LoRA", "tok/s"],
    },
    {
        "section": "Where this goes",
        "title": "Roadmap, ordered by dependency",
        "short": [
            "Per-service authentication across the fleet. *The known gap.*",
            "An adversarial test suite against our own network.",
            "Asynchronous batch processing overnight, reviewed in the morning.",
            "Then domain adaptation, once there is reviewed data to train on.",
        ],
        "detail": [
            "Per-service authentication across the fleet. Unglamorous plumbing, and "
            "the largest gap we have identified in our own posture.",
            "An adversarial test suite aimed at our own network, constructed the "
            "way the vault suite was - predominantly attacks, re-runnable, "
            "producing a measurement rather than an assessment.",
            "Asynchronous batch processing: queue work overnight, let the "
            "distributed configuration process it, and have drafts and exceptions "
            "waiting in the morning. This is the one workload where 1.80 tokens per "
            "second is entirely adequate, because no one is waiting on it.",
            "Then domain adaptation, once sufficient reviewed real data exists to "
            "train on honestly.",
            "Deliberately excluded: anything external before the internal claims "
            "deployment works end to end.",
        ],
        "notes": "Ordered by dependency rather than by interest, and that is worth "
                 "pointing out - it is the difference between a roadmap and a "
                 "wishlist. If he wants to take something on, the top two items are "
                 "the most delegable work in the system: both methodical, both "
                 "testable, and neither requires understanding how a transformer "
                 "works.",
        "terms": [],
    },

    # ------------------------------------------------------------ Working here
    {
        "section": "Working here",
        "title": "Engineering practices",
        "short": [
            "*Build it rather than describe it.*",
            "*Verify before claiming.* Check the log, the endpoint, the artefact.",
            "Document anything learned the hard way, immediately.",
            "One change at a time, completed. *State the weakness aloud.*",
        ],
        "detail": [
            "Build rather than describe. Hours have been lost discussing features "
            "that did not yet exist. If it can be built in the time required to "
            "explain it, build it.",
            "Verify before claiming. Asserting a root cause before confirming it "
            "has cost real credibility here. Check the log, check the endpoint, "
            "check the installed artefact - then state it.",
            "Document anything learned the hard way, immediately. The handbook "
            "exists so that no constraint is paid for twice, and it is why a second "
            "engineer becomes productive in a day rather than a month.",
            "One change at a time, completed, before the next. Five partially "
            "implemented features have no value.",
            "State the weakness aloud. Every slide in this deck that concedes a "
            "limitation made the remainder more credible.",
        ],
        "notes": "Close on this rather than on technology, because it is what makes "
                 "the rest repeatable and it is what you are actually asking him to "
                 "join. Then hand him something small and real - the authentication "
                 "work or the network test suite - because nobody understands a "
                 "system by being shown it. Ask what he wants to examine first and "
                 "let the answer decide where you go next.",
        "terms": [],
    },
]


def sections_with_slides() -> list[dict]:
    """Contents: each chapter with its accent, promise and slide range."""
    out: list[dict] = []
    for n, name in enumerate(SECTIONS, start=1):
        idx = [i for i, s in enumerate(SLIDES) if s["section"] == name]
        if not idx:
            continue
        meta = SECTION_META.get(name, {})
        out.append({
            "name": name,
            "number": n,
            "first": idx[0],
            "count": len(idx),
            "accent": meta.get("accent", "#C4A35A"),
            "blurb": meta.get("blurb", ""),
        })
    return out


def accent_for(section: str) -> str:
    return SECTION_META.get(section, {}).get("accent", "#C4A35A")


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
        # Highlight markers must pair up. An odd asterisk makes the renderer
        # highlight everything after it, which on a television is glaring and
        # is the kind of thing nobody notices until it is projected.
        for field in ("short", "detail"):
            for line in s.get(field, []):
                if line.count("*") % 2:
                    problems.append(
                        f"{where}: unbalanced * in {field}: {line[:48]!r}")
        layout = s.get("layout", "bullets")
        if layout not in LAYOUTS:
            problems.append(f"{where}: unknown layout {layout!r}")
        if layout == "stats":
            stats = s.get("stats") or []
            if not 2 <= len(stats) <= 4:
                problems.append(f"{where}: stats layout wants 2-4 figures, has {len(stats)}")
            for st in stats:
                if not st.get("value") or not st.get("label"):
                    problems.append(f"{where}: a stat is missing value or label")
        elif s.get("stats"):
            problems.append(f"{where}: has stats but layout is {layout!r}")
    for name in SECTIONS:
        if not any(s["section"] == name for s in SLIDES):
            problems.append(f"section {name!r} has no slides")
        if name not in SECTION_META:
            problems.append(f"section {name!r} has no accent/blurb in SECTION_META")
    for name in SECTION_META:
        if name not in SECTIONS:
            problems.append(f"SECTION_META has {name!r}, which is not a section")
    return problems
