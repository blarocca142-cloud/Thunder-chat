"""Thunder-Engine: cheap CPU safety router. Stdlib only, no deps.

Enforces exactly one rule, deterministically, in code Blayne controls -
independent of whatever a given model's own alignment does or doesn't do:
never allow sexual/romantic content involving minors. Nothing else is
gated here; that's the model's job, per Blayne's explicit policy.

This is a keyword/pattern backstop, not a full classifier - it catches
obvious cases and is meant as defense-in-depth alongside the model's own
system-prompt instruction, not a replacement for it.
"""
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 9002

AGE_TERMS = r"(minor|child|kid|little girl|little boy|underage|toddler|infant|\b[0-9]|1[0-7]\s*(yo|yr|year))"
SEXUAL_TERMS = r"(sex|sexual|nude|naked|porn|erotic|molest|rape|fuck|blowjob|masturbat)"

PATTERN = re.compile(AGE_TERMS + r".{0,60}" + SEXUAL_TERMS + r"|" + SEXUAL_TERMS + r".{0,60}" + AGE_TERMS, re.IGNORECASE)


def check(message: str) -> dict:
    if PATTERN.search(message or ""):
        return {"allow": False, "reason": "blocked: sexual content involving minors is never allowed"}
    return {"allow": True, "reason": ""}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok"})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/check":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})
        return self._send(200, check(body.get("message", "")))

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Thunder-Engine safety router listening on :{PORT}")
    server.serve_forever()
