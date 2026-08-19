#!/usr/bin/env python3
"""server.py - the INCEPTION daemon (Python 3 stdlib only, zero dependencies).

A self-certifying HTTP server for the INCEPTION "witness stack for AI". It:

  * serves the five tools' static files (receipt/, passport/, quotecop/,
    djournal/, incept/out/, assets/) under the repo root;
  * exposes a JSON API: /api/health, /api/verify, /api/plant, /api/list;
  * replays the deterministic incept plant sequence over HTTP - re-planting the
    same domain reproduces byte-identical artifacts and identical hashes.

No third-party imports, no network calls beyond its own HTTP handling, no CGI
or code execution. Static serving is path-traversal safe (realpath containment
plus rejection of any ".." segment).

Run:
    python3 server.py [--host 127.0.0.1] [--port 8377] [--out <path>]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import os
import re
import sys
import threading
import time
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ------------------------------------------------------------------ kit root

KIT_ROOT = os.path.dirname(os.path.abspath(__file__))
if KIT_ROOT not in sys.path:
    sys.path.insert(0, KIT_ROOT)

# namespace package (PEP 420): <repo>/incept has no __init__.py
from incept import incept as incept_mod  # noqa: E402

VERSION = "1.0"
SERVER_NAME = "inception"
MAX_BODY = 64 * 1024  # 64 KiB request-body cap

# Static roots served under the repo root (trailing slash = subtree).
STATIC_DIRS = ("receipt", "passport", "quotecop", "djournal", "assets", "incept/out")
STATIC_PREFIXES = tuple(d + "/" for d in STATIC_DIRS)

MIME_TEXT = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".json": "application/json",
    ".txt": "text/plain",
    ".md": "text/plain",
    ".card": "text/plain",
    ".py": "text/plain",
}
MIME_BINARY = {
    ".png": "image/png",
}

FALLBACK_INDEX = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>INCEPTION</title>
<style>
  body { background: #EAEAEA; color: #000; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; margin: 2.5rem; line-height: 1.5; }
  h1 { font-size: 1.25rem; border-bottom: 2px solid #000; padding-bottom: .4rem; }
  h2 { font-size: 1rem; margin-top: 1.5rem; }
  ul { list-style: none; padding-left: 0; }
  li { margin: .25rem 0; }
  code { background: #dcdcdc; padding: 0 .3rem; }
</style>
</head>
<body>
<h1>INCEPTION - witness stack for AI</h1>
<p>Five zero-install, self-verifying tools for AI provenance.</p>
<h2>Tools</h2>
<ul>
  <li><strong>receipt</strong> - tamper-evident receipts for generated artifacts</li>
  <li><strong>passport</strong> - provenance passports with cross-checking</li>
  <li><strong>quotecop</strong> - verbatim quote verification</li>
  <li><strong>djournal</strong> - signed, chained observation journal</li>
  <li><strong>incept</strong> - deterministic idea-seed generator</li>
</ul>
<h2>API</h2>
<ul>
  <li><code>GET /api/health</code> - liveness + kit/out roots</li>
  <li><code>GET /api/verify</code> - recompute every SHA-256 and stamp VERIFIED/BROKEN</li>
  <li><code>POST /api/plant</code> - plant a signed genesis hypothesis for a domain</li>
  <li><code>GET /api/list</code> - list planted cards, sorted by deadline</li>
</ul>
</body>
</html>
"""


# ------------------------------------------------------------------ handler

class Handler(BaseHTTPRequestHandler):
    """JSON API + path-traversal-safe static file serving."""

    server_version = SERVER_NAME
    sys_version = ""

    def log_version_string(self):
        """Plain identifier - never a version banner."""
        return SERVER_NAME

    def version_string(self):
        # Controls the "Server:" response header; no BaseHTTP/Python banner.
        return SERVER_NAME

    # ---- request logging (time, method, path, status, duration ms) ---------

    def setup(self):
        super().setup()
        self._start_time = time.time()

    def log_request(self, code="-", size="-"):
        if isinstance(code, int):
            code_str = str(code)
        elif hasattr(code, "value"):
            code_str = str(code.value)
        else:
            code_str = str(code)
        duration_ms = (time.time() - self._start_time) * 1000.0
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"{ts} {self.command} {self.path} {code_str} {duration_ms:.1f}ms",
              flush=True)

    # ---- low-level response helpers ----------------------------------------

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code, message):
        self._json(code, {"error": message})

    def _method_not_allowed(self, allowed):
        body = json.dumps({"error": "Method not allowed."}).encode("utf-8")
        self.send_response(405)
        self.send_header("Allow", ", ".join(allowed))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, code, ctype, data):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ---- routing -----------------------------------------------------------

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def _route(self, method):
        try:
            path = urllib.parse.urlsplit(self.path).path
            if path == "/":
                if method != "GET":
                    self._method_not_allowed(["GET"])
                else:
                    self._handle_index()
            elif path == "/api/health":
                if method != "GET":
                    self._method_not_allowed(["GET"])
                else:
                    self._handle_health()
            elif path == "/api/verify":
                if method != "GET":
                    self._method_not_allowed(["GET"])
                else:
                    self._handle_verify()
            elif path == "/api/plant":
                if method != "POST":
                    self._method_not_allowed(["POST"])
                else:
                    self._handle_plant()
            elif path == "/api/list":
                if method != "GET":
                    self._method_not_allowed(["GET"])
                else:
                    self._handle_list()
            elif path.startswith("/api/"):
                self._error(404, "Not found.")
            else:
                if method != "GET":
                    self._method_not_allowed(["GET"])
                else:
                    self._handle_static(path)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            traceback.print_exc()
            try:
                self._error(500, "Internal server error.")
            except Exception:
                pass

    # ---- endpoints ---------------------------------------------------------

    def _handle_index(self):
        index = os.path.join(self.server.kit_root, "index.html")
        if os.path.isfile(index):
            self._serve_file(index)
        else:
            self._send_bytes(200, "text/html; charset=utf-8",
                             FALLBACK_INDEX.encode("utf-8"))

    def _handle_health(self):
        self._json(200, {
            "status": "ok",
            "name": "inception",
            "version": VERSION,
            "kit_root": self.server.kit_root_hash,
            "out_root": str(self.server.out_root),
            "uptime_s": round(time.time() - self.server.start_time, 3),
        })

    def _handle_verify(self):
        spec = importlib.util.spec_from_file_location(
            "verify_kit", os.path.join(self.server.kit_root, "verify_kit.py"))
        vk = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vk)
        r = vk.verify_kit()
        self._json(200, {
            "ok": bool(r.get("ok")),
            "kit_root": r.get("kit_root"),
            "root_matches": r.get("root_matches"),
            "files_checked": r.get("files_checked", 0),
            "files_broken": r.get("files_broken", 0),
            "broken": r.get("broken", []),
            "stamp": "VERIFIED" if r.get("ok") else "BROKEN",
        })

    def _handle_plant(self):
        length_header = self.headers.get("Content-Length")
        if length_header is not None:
            try:
                n = int(length_header)
            except ValueError:
                self._error(400, "Bad Content-Length.")
                return
            if n < 0:
                self._error(400, "Bad Content-Length.")
                return
        else:
            n = 0
        if n > MAX_BODY:
            self._error(413, "Request body exceeds 64 KiB.")
            return

        raw = b""
        while len(raw) < n:
            chunk = self.rfile.read(n - len(raw))
            if not chunk:
                break
            raw += chunk

        try:
            data = json.loads(raw.decode("utf-8") if raw else "{}")
        except Exception:
            self._error(400, "Invalid JSON body.")
            return
        if not isinstance(data, dict):
            self._error(400, "JSON body must be an object.")
            return

        domain = data.get("domain")
        if not isinstance(domain, str) or not domain.strip():
            self._error(400, "Domain is required.")
            return
        domain = domain.strip()
        if len(domain) > 1000:
            self._error(400, "Domain must be at most 1000 characters.")
            return

        deadline = data.get("deadline")
        if deadline is not None:
            if not isinstance(deadline, str) or                     not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", deadline):
                self._error(400, "Deadline must be YYYY-MM-DD.")
                return
            try:
                _dt.date.fromisoformat(deadline)
            except ValueError:
                self._error(400, "Deadline must be a valid date (YYYY-MM-DD).")
                return

        archetype = data.get("archetype")
        if archetype is not None and archetype not in incept_mod.ARCHETYPES:
            self._error(400, "Archetype must be one of: quotecheck, passgrade, journal.")
            return

        with self.server.plant_lock:
            result = self._plant(domain, deadline, archetype)
        self._json(200, result)

    def _plant(self, domain, deadline_override, archetype_arg):
        """The exact deterministic plant sequence (mirrors incept.main)."""
        out_root = self.server.out_root
        seed = incept_mod.seed_hash(domain)
        deadline = deadline_override or incept_mod.deterministic_deadline(seed)
        archetype = archetype_arg or incept_mod.pick_archetype(domain)
        hyp_text, falsifier = incept_mod.build_hypothesis(
            domain, archetype, deadline, incept_mod.seeded_rng(seed, "hypothesis"))
        hyp_hash = incept_mod.sha256(hyp_text)
        genesis_text = incept_mod.render_genesis(
            domain, archetype, seed, deadline, hyp_hash, hyp_text)
        genesis_file = incept_mod.sha256(genesis_text)
        tool_source, tool_name = incept_mod.build_tool(
            archetype, domain, seed, hyp_hash, deadline, genesis_file,
            incept_mod.seeded_rng(seed, "tool:" + archetype))
        tool_hash = incept_mod.sha256(tool_source)
        root = incept_mod.sha256(incept_mod.sha256(seed + genesis_file) + tool_hash)
        slug = incept_mod.slugify(domain)

        out_dir = os.path.join(out_root, slug)
        tools_dir = os.path.join(out_dir, "tools")
        os.makedirs(tools_dir, exist_ok=True)
        card_text = incept_mod.render_card_file(
            slug, domain, archetype, deadline, seed, hyp_hash, genesis_file,
            tool_hash, root)
        with open(os.path.join(out_dir, "genesis.md"), "w", encoding="utf-8") as fh:
            fh.write(genesis_text)
        with open(os.path.join(out_dir, "planted.card"), "w", encoding="utf-8") as fh:
            fh.write(card_text)
        with open(os.path.join(tools_dir, tool_name), "w", encoding="utf-8") as fh:
            fh.write(tool_source)

        return {
            "slug": slug,
            "domain": domain,
            "archetype": archetype,
            "deadline": deadline,
            "seed": seed,
            "hypothesis_id": "H-" + hyp_hash[:8],
            "hypothesis": hyp_text,
            "falsifier": falsifier,
            "hyp_hash": hyp_hash,
            "genesis_file": genesis_file,
            "tool": tool_hash,
            "tool_name": tool_name,
            "root": root,
            "planted": True,
            "replay": "plant the same domain again — byte-identical",
        }

    CARD_KEYS = ("slug", "domain", "archetype", "deadline", "seed",
                 "hypothesis", "genesis_file", "tool", "root")

    def _handle_list(self):
        items = []
        out_root = self.server.out_root
        if os.path.isdir(out_root):
            for name in sorted(os.listdir(out_root)):
                d = os.path.join(out_root, name)
                if not os.path.isdir(d):
                    continue
                card = os.path.join(d, "planted.card")
                if not os.path.isfile(card):
                    continue
                parsed = self._parse_card(card)
                if parsed is not None:
                    items.append(parsed)
        items.sort(key=lambda x: (x.get("deadline", ""), x.get("slug", "")))
        self._json(200, items)

    @classmethod
    def _parse_card(cls, path):
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            return None
        fields = {}
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            if key not in cls.CARD_KEYS:
                continue
            fields[key] = value.strip()
        for k in cls.CARD_KEYS:
            if not fields.get(k):
                return None
        return fields

    # ---- static file serving ----------------------------------------------

    def _handle_static(self, raw_path):
        path = urllib.parse.unquote(raw_path)
        if chr(0) in path or chr(92) in path:
            self._error(403, "Forbidden.")
            return
        rel = path.lstrip("/")
        segments = rel.split("/")
        if ".." in segments:
            self._error(403, "Forbidden.")
            return
        if not self._allowed(rel):
            self._error(404, "Not found.")
            return

        kit_real = os.path.realpath(self.server.kit_root)
        target = os.path.realpath(os.path.join(self.server.kit_root, rel))
        if target != kit_real and not target.startswith(kit_real + os.sep):
            self._error(403, "Forbidden.")
            return

        if os.path.isdir(target):
            index = os.path.join(target, "index.html")
            if os.path.isfile(index):
                target = index
            else:
                self._error(403, "Forbidden.")
                return
        if not os.path.isfile(target):
            self._error(404, "Not found.")
            return
        self._serve_file(target)

    @staticmethod
    def _allowed(rel):
        if rel in STATIC_DIRS:
            return True
        for prefix in STATIC_PREFIXES:
            if rel.startswith(prefix):
                return True
        return False

    def _serve_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in MIME_TEXT:
            ctype = MIME_TEXT[ext] + "; charset=utf-8"
        elif ext in MIME_BINARY:
            ctype = MIME_BINARY[ext]
        else:
            ctype = "application/octet-stream"
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            self._error(404, "Not found.")
            return
        self._send_bytes(200, ctype, data)


# ------------------------------------------------------------------ server

class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _read_kit_root(kit_root):
    try:
        with open(os.path.join(kit_root, "manifest.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
        return manifest.get("kit_root")
    except Exception:
        return None


def make_server(host="127.0.0.1", port=8377, out_root=None, kit_root=None):
    """Build a configured Server bound to (host, port). Port 0 = ephemeral."""
    if kit_root is None:
        kit_root = KIT_ROOT
    if out_root is None:
        out_root = os.path.join(kit_root, "incept", "out")
    out_root = os.path.abspath(out_root)
    os.makedirs(out_root, exist_ok=True)

    srv = Server((host, port), Handler)
    srv.kit_root = kit_root
    srv.out_root = out_root
    srv.start_time = time.time()
    srv.plant_lock = threading.Lock()
    srv.kit_root_hash = _read_kit_root(kit_root)
    return srv


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="server.py",
        description="INCEPTION daemon - self-certifying kit server (stdlib only).")
    ap.add_argument("--host", default="127.0.0.1",
                    help="bind host (default: 127.0.0.1)")
    ap.add_argument("--port", type=int, default=8377,
                    help="bind port (default: 8377)")
    ap.add_argument("--out", default=None,
                    help="plant output root (default: <repo>/incept/out)")
    args = ap.parse_args(argv)

    srv = make_server(args.host, args.port, args.out)
    host, port = srv.server_address[:2]
    print(f"inception daemon listening on {host}:{port} "
          f"- out_root={srv.out_root} kit_root={srv.kit_root}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("inception daemon stopped.", flush=True)
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
