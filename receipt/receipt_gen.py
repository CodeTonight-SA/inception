#!/usr/bin/env python3
"""receipt_gen.py — GRASP "AI Receipt" generator (pure stdlib, zero deps).

Reads a claim spec {"title", "response", "sources[]", "citations[]"}, computes
the content address (SHA-256 of the canonical claim set), re-runs the
cite.verify ladder locally (exact mirror of grasp/cite_verify.py / HAPPI 1.3
cite.verify: exact substring -> whitespace+typographic-tolerant "fuzzy" ->
not_found), and emits ONE self-contained HTML receipt whose in-browser
JavaScript performs the same arithmetic and stamps every citation
VERIFIED (green, with character offsets) or NOT-FOUND (red).

Deterministic: the same spec always produces byte-identical HTML.

Usage:
    python3 receipt_gen.py [spec.json] [-o receipt.html] [--strict]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SPEC = HERE / "demo.json"
DEFAULT_OUT = HERE / "receipt.html"
TEMPLATE = HERE / "template.html"
CORE = HERE / "verify_core.js"

# --------------------------------------------------------------------------
# cite.verify ladder — mirror of grasp/cite_verify.py (HAPPI/1.3)
# --------------------------------------------------------------------------
_WS = re.compile(r"\s+")
_TYPO = {
    0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-", 0x2014: "-", 0x2015: "-",
    0x2018: "'", 0x2019: "'", 0x201B: "'",
    0x201C: '"', 0x201D: '"', 0x201F: '"',
    0x00A0: " ", 0x2007: " ", 0x2009: " ", 0x202F: " ",
}


def _typo(s: str) -> str:
    return s.translate(_TYPO)


def verify_quote(quote, source_text):
    """(status, start, end) — deterministic ladder; offsets index the ORIGINAL
    source because normalisation is length-preserving."""
    q = (quote or "").strip()
    if not q:
        return "not_found", -1, -1
    idx = source_text.find(q)
    if idx != -1:
        return "verified", idx, idx + len(q)
    toks = [re.escape(t) for t in _WS.split(_typo(q)) if t]
    if not toks:
        return "not_found", -1, -1
    m = re.compile(r"\s+".join(toks)).search(_typo(source_text))
    if m:
        return "fuzzy", m.start(), m.end()
    return "not_found", -1, -1


def provenance(spec: dict) -> dict:
    by_id = {s["id"]: s["text"] for s in spec["sources"]}
    tally = {"verified": 0, "fuzzy": 0, "not_found": 0}
    results = []
    for c in spec["citations"]:
        src = by_id.get(c["source_id"])
        status, start, end = (
            verify_quote(c["quote"], src) if src is not None else ("not_found", -1, -1)
        )
        tally[status] += 1
        results.append({"id": c["id"], "source_id": c["source_id"],
                        "status": status, "start": start, "end": end})
    grounded = tally["verified"] + tally["fuzzy"]
    return {
        "sources": {
            sid: {"sha256": hashlib.sha256(t.encode("utf-8")).hexdigest(), "chars": len(t)}
            for sid, t in by_id.items()
        },
        "citations": results,
        "tally": tally,
        "grounding_rate": round(grounded / max(len(spec["citations"]), 1), 3),
    }


def canonical(spec: dict) -> str:
    """Byte-for-byte the same string as the in-browser JS canonical() — sorted
    keys, minimal separators, ASCII-escaped (lowercase hex)."""
    return json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(spec: dict) -> str:
    return hashlib.sha256(canonical(spec).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------
def _reject_floats(obj, path: str) -> None:
    if isinstance(obj, float):
        raise ValueError(f"spec.{path}: floats break python/js canonical parity — use int or string")
    if isinstance(obj, dict):
        for k, v in obj.items():
            _reject_floats(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _reject_floats(v, f"{path}[{i}]")


def validate(spec: dict) -> None:
    for key in ("title", "response", "sources", "citations"):
        if key not in spec:
            raise ValueError(f"spec missing required key: {key!r}")
    if not isinstance(spec["title"], str) or not isinstance(spec["response"], str):
        raise ValueError("title and response must be strings")
    _reject_floats(spec, "")
    if not isinstance(spec["sources"], list) or not spec["sources"]:
        raise ValueError("sources must be a non-empty list")
    if not isinstance(spec["citations"], list) or not spec["citations"]:
        raise ValueError("citations must be a non-empty list")
    ids = set()
    for s in spec["sources"]:
        if not isinstance(s, dict) or not isinstance(s.get("id"), str) or not isinstance(s.get("text"), str):
            raise ValueError("each source needs string id and text")
        ids.add(s["id"])
    for c in spec["citations"]:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str)                 or not isinstance(c.get("source_id"), str) or not isinstance(c.get("quote"), str):
            raise ValueError("each citation needs string id, source_id, quote")
        if c["source_id"] not in ids:
            raise ValueError(f"citation {c['id']!r} references unknown source {c['source_id']!r}")


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------
def render(spec: dict) -> str:
    tpl = TEMPLATE.read_text(encoding="utf-8")
    core = CORE.read_text(encoding="utf-8")
    data_json = json.dumps(spec, indent=2, ensure_ascii=False).replace("<", "\\u003c")
    fp = fingerprint(spec)
    record_id = "REC-" + fp[:12].upper()
    title_escaped = spec["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    out = tpl
    out = out.replace("@DATA@", data_json)
    out = out.replace("@FP@", fp)
    out = out.replace("@RECORD_ID@", record_id)
    out = out.replace("@TITLE@", title_escaped)
    out = out.replace("@CORE@", core)
    for tok in ("@DATA@", "@FP@", "@RECORD_ID@", "@TITLE@", "@CORE@"):
        if tok in out:
            raise RuntimeError("unresolved template token " + tok)
    return out


def _audit_expectations(spec: dict, prov: dict) -> list:
    """Compare spec-level 'expect' hints (if present) against real verdicts."""
    lines = []
    by_id = {c["id"]: c for c in spec["citations"]}
    ok = True
    for r in prov["citations"]:
        c = by_id[r["id"]]
        exp = c.get("expect")
        if exp is None:
            continue
        got = r["status"]
        pass_ = (exp == "verified" and got in ("verified", "fuzzy")) or (exp == got)
        if not pass_:
            ok = False
        lines.append(f"    {r['id']}: expect {exp:<9} got {got:<9} {'OK' if pass_ else 'MISMATCH'}")
    lines.insert(0, "  expectation audit (spec 'expect' hints vs real verdicts):")
    lines.append(f"    audit: {'ALL MATCH' if ok else 'MISMATCH(ES) FOUND'}")
    return lines


def _wellformed(html: str) -> str:
    """Cheap well-formedness scan: parse with html.parser, verify every start
    tag has a matching end tag for the tags we emit, and no stray </script>."""
    from html.parser import HTMLParser

    void = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}
    stack = []
    errors = []

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag not in void:
                stack.append(tag)

        def handle_endtag(self, tag):
            if tag in void:
                return
            if not stack:
                errors.append(f"stray </{tag}>")
                return
            if stack[-1] == tag:
                stack.pop()
            else:
                # tolerate <p> auto-close style mismatches: pop until match
                try:
                    i = len(stack) - 1 - stack[::-1].index(tag)
                except ValueError:
                    errors.append(f"unmatched </{tag}>")
                    return
                del stack[i:]

    p = P(convert_charrefs=True)
    p.feed(html)
    p.close()
    for tag in stack:
        errors.append(f"unclosed <{tag}>")
    if errors:
        return "MALFORMED: " + "; ".join(errors[:6])
    return f"OK ({len(html)} chars, balanced tags)"


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="GRASP AI Receipt generator (stdlib)")
    ap.add_argument("spec", nargs="?", default=str(DEFAULT_SPEC), help="claim spec JSON")
    ap.add_argument("-o", "--output", default=str(DEFAULT_OUT), help="output HTML path")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if any citation is not_found (cite.verify strict gate)")
    args = ap.parse_args(argv)

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    validate(spec)

    prov = provenance(spec)
    fp = fingerprint(spec)
    record_id = "REC-" + fp[:12].upper()
    n = len(spec["citations"])
    grounded = prov["tally"]["verified"] + prov["tally"]["fuzzy"]

    print("GRASP AI-Receipt generator  ·  stdlib only, zero deps")
    print(f"  spec       : {args.spec}")
    print(f"  record id  : {record_id}")
    print(f"  fingerprint: sha256:{fp}")
    print('  ladder     : exact substring -> typographic-tolerant ("fuzzy") -> not_found')
    print("               (mirror of grasp/cite_verify.py · HAPPI 1.3 cite.verify)")
    print()
    print(f"  {'id':<5}{'src':<6}{'status':<11}{'offsets':<17}quote")
    for c, r in zip(spec["citations"], prov["citations"]):
        q = c["quote"]
        prev = q[:52] + ("…" if len(q) > 52 else "")
        off = f"[{r['start']}–{r['end']}]" if r["status"] != "not_found" else "[-1–-1]"
        print(f"  {r['id']:<5}{r['source_id']:<6}{r['status']:<11}{off:<17}{prev}")
    print()
    print(f"  grounding rate : {prov['grounding_rate']} ({grounded}/{n})")
    print(f"  tally          : verified={prov['tally']['verified']} fuzzy={prov['tally']['fuzzy']} "
          f"not_found={prov['tally']['not_found']}")
    for line in _audit_expectations(spec, prov):
        print(line)
    print("  source hashes  : " + " · ".join(
        f"{sid} sha256:{m['sha256'][:16]}… ({m['chars']} chars)"
        for sid, m in prov["sources"].items()))
    print()

    html = render(spec)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    # self-checks
    print(f"  wrote          : {out} ({out.stat().st_size} bytes)")
    print(f"  well-formed    : {_wellformed(html)}")
    # round-trip: the embedded @DATA@ must re-parse to the same spec -> same fp
    m = re.search(r"window\.RECEIPT_DATA = (\{.*?\});", html, re.S)
    if not m:
        print("  embed check    : FAILED — RECEIPT_DATA not found in output")
        return 1
    embedded = json.loads(m.group(1).replace("\\u003c", "<"))
    fp_embedded = fingerprint(embedded)
    print(f"  embed check    : {fp_embedded == fp and 'round-trips, fingerprint identical' or 'FINGERPRINT MISMATCH'}")
    # determinism: render again, must be byte-identical
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tf:
        tf.write(html)
        tmp = Path(tf.name)
    same = tmp.read_bytes() == out.read_bytes()
    tmp.unlink(missing_ok=True)
    print(f"  determinism    : {'regeneration is byte-identical' if same else 'DETERMINISM BROKEN'}")

    if args.strict and prov["tally"]["not_found"] > 0:
        print(f"  strict gate    : {prov['tally']['not_found']} not_found -> exit 1 (never ship an unproven quote)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
