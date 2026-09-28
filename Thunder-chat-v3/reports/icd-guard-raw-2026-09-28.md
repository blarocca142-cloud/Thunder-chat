# ICD guard — raw capture, 2026-09-28

Three identical requests to `POST localhost:8080/chat/stream` on thunder-main,
read-only (no restart, no deploy). Captured as raw ndjson, one line per frame,
exactly as received.

- Prompt, all three runs: `what does ICD-10 code Z9Q.47 mean?`
- Body sent: `{"message":"what does ICD-10 code Z9Q.47 mean?"}`
- Model per `/status`: `thunder-gptoss:latest`
- Run times (EDT): 17:14:35, 17:14:54, 17:15:14
- Wall clock: run 1 2.5s, run 2 3.0s, run 3 11.5s

Note on timestamps: `journalctl` on Main prints in **EDT**, not UTC — verified
against `date` in the same minute. The UTC-vs-local trap applies to the app's
own logs, not to the journal output below.

## Run 1 — raw ndjson

```
{"delta": "[checking the official code list: Z9Q.47]\n"}
{"delta": "\n\n(Stopped: the model kept drifting out of English. Ask again.)"}
{"delta": "I looked into this but could not put together an answer I can stand behind. Ask me again, or narrow the question."}
{"done": true}
```

Joined:

```
[checking the official code list: Z9Q.47]


(Stopped: the model kept drifting out of English. Ask again.)I looked into this but could not put together an answer I can stand behind. Ask me again, or narrow the question.
```

## Run 2 — raw ndjson

```
{"delta": "[checking the official code list: Z9Q.47]\n"}
{"delta": "\n\n(Stopped: the model kept drifting out of English. Ask again.)"}
{"delta": "I looked into this but could not put together an answer I can stand behind. Ask me again, or narrow the question."}
{"done": true}
```

Joined:

```
[checking the official code list: Z9Q.47]


(Stopped: the model kept drifting out of English. Ask again.)I looked into this but could not put together an answer I can stand behind. Ask me again, or narrow the question.
```

## Run 3 — raw ndjson

```
{"delta": "[checking the official code list: Z90.47]\n"}
{"delta": "[searching the web: ICD-10 Z90.47]\n"}
{"delta": "\n\n(Stopped: the model kept drifting out of English. Ask again.)"}
{"delta": "I looked into this but could not put together an answer I can stand behind. Ask me again, or narrow the question."}
{"done": true}
```

Joined:

```
[checking the official code list: Z90.47]
[searching the web: ICD-10 Z90.47]


(Stopped: the model kept drifting out of English. Ask again.)I looked into this but could not put together an answer I can stand behind. Ask me again, or narrow the question.
```

## What the three runs show

No run produced an answer about the code. All three ended on the same two
frames: the language-drift stop, then the refusal. Nothing invented a meaning
for `Z9Q.47` and reached the screen, which is the behaviour the guard is there
for.

Two things are not consistent across runs, and both are about the code that got
looked up rather than about the refusal.

**1. Run 3 checked a different code than the one asked about.** Runs 1 and 2
echo `Z9Q.47` — the string in the prompt. Run 3 echoes `Z90.47`, with the `Q`
replaced by a `0`, and then web-searched that rewritten code. The substitution
is not announced anywhere in the stream; a reader sees a lookup of a code they
never typed. Same prompt, same model, three runs, two different codes checked.

**2. `Z90.47` is not a valid code either.** Checked against
`thunder-claims/codes/icd10cm_2026.txt` (74,719 codes, stored undotted):

| code | in list | as prefix of any code |
|---|---|---|
| `Z9Q47` | no | 0 |
| `Z9047` | no | 0 |

The real `Z904` family is `Z90410`, `Z90411`, `Z9049` — nothing under `Z9047`.
So run 3 rewrote an invalid code into a second invalid code and passed that to
web search rather than stopping at the list check.

I did not trace the guard code to find where the substitution happens, so the
cause is open — whether the model emitted `Z90.47` itself or something
normalised it downstream is not established by this capture.

What this run does **not** show: that the gate rejects invalid codes at the list
check. In run 3 the lookup proceeded to web search after the list check on a
code the list does not contain. The refusal that ended all three runs came from
the language-drift stop, which is a different mechanism.

## journalctl -u thunder-main --since -30min (tail, polling noise removed)

`GET /job/next` lines from 10.168.168.11 (thunder-cache, every 15s) are dropped
below; they made up most of the output and say nothing about these requests.

```
Sep 28 17:02:24 thunder-main systemd[1]: thunder-main.service: Consumed 21.211s CPU time over 1h 22min 36.527s wall clock time, 86.7M memory peak, 5.3M memory swap peak.
Sep 28 17:02:24 thunder-main systemd[1]: Started thunder-main.service - Thunder Main API.
Sep 28 17:02:24 thunder-main python3[117932]: INFO:     Started server process [117932]
Sep 28 17:02:24 thunder-main python3[117932]: INFO:     Waiting for application startup.
Sep 28 17:02:24 thunder-main python3[117932]: INFO:     Application startup complete.
Sep 28 17:02:24 thunder-main python3[117932]: INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
Sep 28 17:02:28 thunder-main python3[117932]: INFO:     127.0.0.1:33650 - "GET /status HTTP/1.1" 200 OK
Sep 28 17:02:36 thunder-main python3[117932]: INFO:     10.168.168.4:56926 - "GET /status HTTP/1.1" 200 OK
Sep 28 17:02:52 thunder-main python3[117932]: INFO:     10.168.168.4:50040 - "GET /status HTTP/1.1" 200 OK
Sep 28 17:03:00 thunder-main python3[117932]: INFO:     127.0.0.1:55764 - "GET /status HTTP/1.1" 200 OK
Sep 28 17:03:07 thunder-main python3[117932]: INFO:     10.168.168.4:59330 - "GET /status HTTP/1.1" 200 OK
Sep 28 17:03:22 thunder-main python3[117932]: INFO:     10.168.168.4:52062 - "GET /status HTTP/1.1" 200 OK
Sep 28 17:03:37 thunder-main python3[117932]: INFO:     10.168.168.4:52030 - "GET /status HTTP/1.1" 200 OK
Sep 28 17:03:43 thunder-main python3[117932]: INFO:     127.0.0.1:59612 - "POST /chat/stream HTTP/1.1" 200 OK
Sep 28 17:03:45 thunder-main python3[117932]: INFO:     127.0.0.1:59614 - "POST /chat/stream HTTP/1.1" 200 OK
Sep 28 17:03:47 thunder-main python3[117932]: INFO:     127.0.0.1:59622 - "POST /chat/stream HTTP/1.1" 200 OK
Sep 28 17:03:52 thunder-main python3[117932]: INFO:     10.168.168.4:41466 - "GET /status HTTP/1.1" 200 OK
Sep 28 17:04:06 thunder-main python3[117932]: INFO:     10.168.168.4:59622 - "GET /code HTTP/1.1" 200 OK
Sep 28 17:04:07 thunder-main python3[117932]: INFO:     10.168.168.4:59622 - "GET /status HTTP/1.1" 200 OK
Sep 28 17:10:43 thunder-main systemd[1]: Stopping thunder-main.service - Thunder Main API...
Sep 28 17:10:43 thunder-main python3[117932]: INFO:     Shutting down
Sep 28 17:10:43 thunder-main python3[117932]: INFO:     Waiting for application shutdown.
Sep 28 17:10:43 thunder-main python3[117932]: INFO:     Application shutdown complete.
Sep 28 17:10:43 thunder-main python3[117932]: INFO:     Finished server process [117932]
Sep 28 17:10:43 thunder-main systemd[1]: thunder-main.service: Deactivated successfully.
Sep 28 17:10:43 thunder-main systemd[1]: Stopped thunder-main.service - Thunder Main API.
Sep 28 17:10:43 thunder-main systemd[1]: thunder-main.service: Consumed 3.107s CPU time over 8min 19.162s wall clock time, 91.7M memory peak.
Sep 28 17:10:43 thunder-main systemd[1]: Started thunder-main.service - Thunder Main API.
Sep 28 17:10:43 thunder-main python3[118350]: INFO:     Started server process [118350]
Sep 28 17:10:43 thunder-main python3[118350]: INFO:     Waiting for application startup.
Sep 28 17:10:43 thunder-main python3[118350]: INFO:     Application startup complete.
Sep 28 17:10:43 thunder-main python3[118350]: INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
Sep 28 17:11:19 thunder-main python3[118350]: INFO:     127.0.0.1:43162 - "POST /chat/stream HTTP/1.1" 200 OK
Sep 28 17:11:22 thunder-main python3[118350]: INFO:     127.0.0.1:43166 - "POST /chat/stream HTTP/1.1" 200 OK
Sep 28 17:11:24 thunder-main python3[118350]: INFO:     127.0.0.1:43180 - "POST /chat/stream HTTP/1.1" 200 OK
Sep 28 17:11:29 thunder-main python3[118350]: INFO:     127.0.0.1:51914 - "POST /chat/stream HTTP/1.1" 200 OK
Sep 28 17:14:16 thunder-main python3[118350]: INFO:     127.0.0.1:52088 - "GET /status HTTP/1.1" 200 OK
Sep 28 17:14:35 thunder-main python3[118350]: INFO:     127.0.0.1:60060 - "POST /chat/stream HTTP/1.1" 200 OK
Sep 28 17:14:54 thunder-main python3[118350]: INFO:     127.0.0.1:45430 - "POST /chat/stream HTTP/1.1" 200 OK
Sep 28 17:15:14 thunder-main python3[118350]: INFO:     127.0.0.1:51292 - "POST /chat/stream HTTP/1.1" 200 OK
```

The last three `POST /chat/stream` lines are the three runs above. The journal
carries no detail about the guard itself — it is uvicorn access logging only,
so the stream frames are the only record of what the code check did.

Two things in this window were **not** mine, flagged so they aren't misread as
part of the test:

- The service **restarted at 17:10:43**, about four minutes before the first
  run. This capture was read-only; I issued no restart and no deploy. The
  restart's origin is unaccounted for.
- The four `POST /chat/stream` at 17:11:19–17:11:29, and the three at
  17:03:43–17:03:47, predate my runs and came from someone or something else on
  loopback.
