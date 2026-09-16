"""OCR text -> structured claim fields, via the local model.

Ollama's format=json forces syntactically valid output, which is the difference
between this being usable and being a coin flip - a 24B model asked politely
for JSON will sometimes write prose instead.
"""
import json, sys, time, urllib.request

OLLAMA = "http://127.0.0.1:11434/api/chat"
MODEL = "thunder:latest"

SCHEMA_HINT = """Return ONLY a JSON object with exactly these keys:
{"patient_name":"","dob":"","sex":"","address":"","phone":"",
 "insurer":"","claim_number":"","date_of_injury":"","date_of_service":"",
 "referring_provider":"","referring_npi":"","treating_provider":"","treating_npi":"",
 "clinic_name":"","clinic_tax_id":"","clinic_npi":"",
 "accident_type":"","diagnoses":[{"code":"","description":""}],
 "procedures":[{"code":"","description":"","units":""}]}
Use "" for anything not present. Copy values exactly as written - do not
reformat dates, do not correct spellings, do not invent codes."""

def extract(text: str) -> dict:
    payload = json.dumps({
        "model": MODEL, "stream": False, "format": "json",
        "options": {"temperature": 0, "num_predict": 1600},
        "messages": [
            {"role": "system", "content":
             "You extract billing fields from scanned clinical documents. "
             "You never invent data. " + SCHEMA_HINT},
            {"role": "user", "content": f"Document text:\n\n{text}"},
        ],
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        body = json.loads(r.read().decode())
    return json.loads(body["message"]["content"])

if __name__ == "__main__":
    text = open(sys.argv[1]).read()
    t = time.time()
    data = extract(text)
    print(f"extracted in {time.time()-t:.1f}s\n")
    json.dump(data, open("claim.json", "w"), indent=2)
    print(json.dumps(data, indent=2)[:1400])
