"""Odris web gateway: the ONLY thing in the Thunder stack allowed to touch
the real internet, and only for this one narrow job. Main's Ollama process
is firewalled off the internet entirely (see net-lockdown/); when Thunder
needs to look something up (game info, current facts, whatever it doesn't
know), it asks Odris over the internal LAN, and Odris does the actual
outbound fetch. Stdlib only, no deps, no API key required.
"""
import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 9004
UA = "Mozilla/5.0 (compatible; ThunderOdrisSearch/1.0)"


class ResultParser(HTMLParser):
    """Pulls result titles + snippets out of DuckDuckGo lite's results page."""

    def __init__(self):
        super().__init__()
        self.results = []
        self._in_title = False
        self._in_snippet = False
        self._cur_title = ""
        self._cur_href = ""
        self._cur_snippet = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        cls = attrs.get("class", "")
        if tag == "a" and cls == "result-link":
            self._in_title = True
            self._cur_href = attrs.get("href", "")
        if tag == "td" and cls == "result-snippet":
            self._in_snippet = True

    def handle_endtag(self, tag):
        if tag == "a" and self._in_title:
            self._in_title = False
            if self._cur_title:
                self.results.append({"title": self._cur_title.strip(), "snippet": "", "url": self._cur_href})
            self._cur_title = ""
        if tag == "td" and self._in_snippet:
            self._in_snippet = False
            if self.results:
                self.results[-1]["snippet"] = self._cur_snippet.strip()
            self._cur_snippet = ""

    def handle_data(self, data):
        if self._in_title:
            self._cur_title += data
        if self._in_snippet:
            self._cur_snippet += data


def web_search(query: str, max_results: int = 5) -> list[dict]:
    data = urllib.parse.urlencode({"q": query}).encode()
    req = urllib.request.Request(
        "https://lite.duckduckgo.com/lite/",
        data=data,
        headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        html = r.read().decode("utf-8", errors="ignore")
    parser = ResultParser()
    parser.feed(html)
    # dedupe titles that got double-counted, keep order
    seen = set()
    out = []
    for item in parser.results:
        if item["title"] and item["title"] not in seen:
            seen.add(item["title"])
            out.append(item)
    return out[:max_results]


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
        if self.path != "/websearch":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})
        query = (body.get("query") or "").strip()
        if not query:
            return self._send(400, {"error": "missing query"})
        try:
            results = web_search(query, body.get("max_results", 5))
            return self._send(200, {"query": query, "results": results})
        except Exception as e:
            return self._send(502, {"error": str(e)})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Odris web gateway listening on :{PORT}")
    server.serve_forever()
