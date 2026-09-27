# Thunder's tools

Thunder decides for itself when to search, read a page, run code, open a file,
check memory or check the hardware. Every call is asked of **Odris** first.

    phone -> Main /chat/stream -> agent.py loop -> model asks for a tool
                                        |
                                        v
                        Odris :9007 (odris_gate.py): allowed? log it.
                          internet tools: Odris does the fetch itself
                          local tools:    Odris approves, Main runs them

| Tool | Runs on | What stops misuse |
|---|---|---|
| `web_search`, `fetch_url` | Odris | Refused if the text looks like patient data (SSN, DOB, member/claim IDs, NPI, ICD-10). `fetch_url` refuses LAN, loopback, link-local and cloud-metadata addresses, including via redirect. |
| `run_python` | Main | Own network namespace (`unshare -rn`) so it has **no network**, temp dir thrown away, 30s CPU, 2GB memory, 50MB files. |
| `read_file`, `write_file`, `list_files` | Main | Confined to `thunder-data/code` (the code workspace). `../` and absolute paths refused. |
| `memory_search`, `system_status` | Main | Read-only. |

Every decision is one JSON line in `~/thunder-gate/gate.log` on Odris.
**If Odris does not answer, every tool is refused** - fail closed.

## Checks on every reply (code, not prompt)

- **English only.** Any Chinese/Japanese/Korean character stops the stream
  before it is shown; the model is told why and continues from where it
  stopped. Three strikes and the reply is cut off with a note.
- **Thunder is Thunder.** "I am Qwen / made by Alibaba / OpenAI / ..." is
  caught the same way.
- **No invented links.** URLs not returned by a tool this turn (or typed by
  Blayne) get a `Check:` note under the reply.
- **No invented test runs.** "I ran / tested it" with no `run_python` this
  turn gets a `Check:` note.
- A pages-read footer lists what was actually opened.

`python3 test_tools.py` - 61 checks, mostly attacks. All passing.

## Deploy

**Odris** (user unit, no root - same as TTS):

    scp thunder-nodes/odris/odris_gate.py thunder-nodes/odris/odris_websearch.py odris:~/thunder-nodes/odris/
    scp thunder-nodes/odris/odris-gate.service odris:~/.config/systemd/user/
    ssh odris 'systemctl --user daemon-reload && systemctl --user enable --now odris-gate'
    curl -s http://10.168.168.15:9007/health

**Main**: the new code is `agent.py`, `tools.py` and changes in `app.py`.
Restart `thunder-main`. Settings (env):

| Var | Default | |
|---|---|---|
| `THUNDER_TOOLS` | `1` | `0` = old keyword-search path |
| `ODRIS_GATE_URL` | `http://10.168.168.15:9007` | |
| `THUNDER_NUM_CTX` | `16384` | raise with the new model |
| `THUNDER_NUM_PREDICT` | `4096` | reply length cap in tool mode |
| `THUNDER_TOOL_STEPS` | `10` | tool calls per reply |
| `THUNDER_THINK` | unset | `0`/`1` forces thinking off/on for models that have it |
| `THUNDER_STUDIO_PROMPT` | `0` | video/photo section of the prompt - shelved |

**Sandbox check on Main** - must print `NONET`:

    unshare -rn python3 -c "import socket;s=socket.socket();s.settimeout(2)
    try: s.connect(('1.1.1.1',53));print('NET')
    except OSError: print('NONET')"

If `unshare` fails with "Operation not permitted", Ubuntu's AppArmor is
blocking unprivileged user namespaces. One-time root fix:

    echo 'kernel.apparmor_restrict_unprivileged_userns=0' | sudo tee /etc/sysctl.d/60-thunder-userns.conf
    sudo sysctl --system

Until then `run_python` refuses to run rather than running with network.

## The model must support tools

A model without tool calling (Ollama answers "does not support tools") falls
back to the old path automatically. Import new models with a **minimal**
Modelfile - no `SYSTEM` block. `app.py` supplies the system prompt, and a second
one baked into the model competes with it.

## Medical never touches a Chinese model

Blayne's rule. Enforced three ways, by what a model *is*, not what it is called:

- **Chat**: a message that looks like a claim or chart (`tools.looks_medical`)
  is answered by `THUNDER_MEDICAL_MODEL` (default `thunder:latest`, Mistral),
  whatever `THUNDER_MODEL` is. The app shows a line saying so.
- **Context**: when the main model answers, earlier medical turns and recalled
  medical notes are stripped from its prompt, so it never sees them.
- **Claims pipeline**: `thunder-claims/extract.py` asks Ollama for the model's
  architecture and refuses Qwen, DeepSeek, GLM and the other Chinese families
  before reading a single page (`CLAIMS_MODEL`, default `thunder:latest`).
