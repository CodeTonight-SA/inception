#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 CodeTonight SA
"""quotecop — the anti-hallucination button.

ONE command that answers "did this quote actually exist in this source?"
deterministically. String arithmetic, not judgement — a fabricated quote can
never pass. Ladder: exact verbatim -> whitespace/typographic/case-tolerant ->
NOT-FOUND, with exact character offsets into the source and a grounding rate.

Usage:
  python3 quotecop.py --file doc.txt --quote "..." [--quote "..."]
  python3 quotecop.py --source "pasted source text" --quote "..."
  cat doc.txt | python3 quotecop.py --quote "..."
  python3 quotecop.py --file doc.txt --quotes-file quotes.txt
  python3 quotecop.py --file doc.txt --quote "..." --json

Options:
  --file PATH       source text file (one of --file / --source / piped stdin)
  --source TEXT     source text pasted inline
  --quote TEXT      the quoted claim (repeatable)
  --quotes-file F   read one quote per line from F
  --json            machine-readable provenance record (no cards)
  --color MODE      auto | always | never
  --no-gate         exit 0 even when a quote is NOT-FOUND
  --version         print version

Exit codes:
  0  every quote verified
  1  at least one quote NOT-FOUND  (the gate: never ship an unproven quote)
  2  usage / I/O error
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap

import citecop

__version__ = "1.0.0"
W = 76            # total card width, borders included
INNER = W - 4     # visible content width between the border pipes

RUNG_LABEL = {
    "exact": "exact",
    "tolerant-whitespace": "whitespace · typographic",
    "tolerant-case": "case-insensitive",
}


class Palette:
    """ANSI styling, honouring --color and the NO_COLOR convention."""

    def __init__(self, enabled: bool):
        self.en = enabled

    def paint(self, code, s):
        if not self.en or not s:
            return s
        return "\x1b[" + str(code) + "m" + s + "\x1b[0m"

    def green(self, s):   return self.paint(32, s)
    def red(self, s):     return self.paint(31, s)
    def bold(self, s):    return self.paint(1, s)
    def dim(self, s):     return self.paint(2, s)
    def cyan(self, s):    return self.paint(36, s)


def top_border():
    return "╭" + "─" * (W - 2) + "╮"


def bottom_border():
    return "╰" + "─" * (W - 2) + "╯"


def divider():
    return "├" + "─" * (W - 2) + "┤"


def row(pal, segs):
    """One card row from (text, ansi_code|None) segments; pads by visible width."""
    if isinstance(segs, str):
        segs = [(segs, None)]
    plain = "".join(t for t, _ in segs)
    styled = "".join(pal.paint(s, t) if s else t for t, s in segs)
    pad = max(0, INNER - len(plain))
    return "│ " + styled + " " * pad + " │"


def labelled(pal, label, text, style=None):
    """Label column (8 chars) + wrapped text rows."""
    chunks = []
    for para in text.split("\n"):
        chunks += textwrap.wrap(para, INNER - 8) or [""]
    if not chunks:
        chunks = [""]
    lines = [row(pal, [(label, 2), (chunks[0], style)])]
    for c in chunks[1:]:
        lines.append(row(pal, [("        ", None), (c, style)]))
    return lines


def display_quote(q):
    return " ".join(q.split())


def context_of(source, start, end, span=38):
    before = source[max(0, start - span):start]
    after = source[end:end + span]
    if start - span > 0:
        before = "…" + before.lstrip("\n")
    if end + span < len(source):
        after = after + "…"
    ctx = before + "⟪" + source[start:end] + "⟫" + after
    return ctx.rstrip("\n")


def banner(pal, src_name, sha, chars, n):
    lines = [top_border()]
    lines.append(row(pal, [("◆ CITECOP · the anti-hallucination button", 1)]))
    lines.append(row(pal, [("deterministic citation provenance — string arithmetic, not judgement", 2)]))
    lines.append(divider())
    lines.append(row(pal, [("source  ", 2), (src_name, None)]))
    lines.append(row(pal, [("sha256  ", 2), (sha, None)]))
    lines.append(row(pal, [("chars   ", 2), (str(chars), None), ("   ·   quotes to check: ", 2), (str(n), None)]))
    lines.append(bottom_border())
    return lines


def quote_card(pal, rec, src_name, src_chars, sha, source):
    lines = [top_border()]
    if rec["status"] == "verified":
        lines.append(row(pal, [("✔ VERIFIED", 32),
                               ("   ·   rung: ", None),
                               (RUNG_LABEL.get(rec["rung"], rec["rung"]), 1)]))
        lines.append(divider())
        lines += labelled(pal, "quote   ", display_quote(rec["quote"]))
        lines.append(row(pal, [("offsets ", 2),
                               ("chars " + str(rec["start"]) + "–" + str(rec["end"]) +
                                " of " + str(src_chars), None)]))
        lines += labelled(pal, "context ", context_of(source, rec["start"], rec["end"]))
    else:
        lines.append(row(pal, [("✘ NOT-FOUND", 31)]))
        lines.append(divider())
        lines += labelled(pal, "quote   ", display_quote(rec["quote"]))
        lines.append(row(pal, [("", None)]))
        lines.append(row(pal, [("— no rung of the ladder could anchor this string in the source —", 31)]))
        lines.append(row(pal, [("ladder  ", 2), ("exact → whitespace → typographic → case", None)]))
    lines.append(divider())
    lines.append(row(pal, [("source  ", 2), (src_name, None),
                           ("  ·  sha256 ", 2),
                           (sha[:12] + "…" + sha[-4:], None)]))
    lines.append(bottom_border())
    return lines


def summary_card(pal, tally, rate, gate_fired):
    bar = "█" * round(rate * 10) + "░" * (10 - round(rate * 10))
    lines = [top_border()]
    lines.append(row(pal, [("grounding", 2), ("  " + bar + "  ", None),
                           (str(rate), 1), ("  ·  " + str(tally["verified"]) + "/" +
                                            str(tally["verified"] + tally["not_found"]), None)]))
    lines.append(row(pal, [("tally    ", 2), ("verified ", None), (str(tally["verified"]), 32),
                           ("  ·  not_found ", None), (str(tally["not_found"]), 31)]))
    lines.append(divider())
    if gate_fired:
        lines.append(row(pal, [("✘ gate   ", 31),
                               ("EXIT 1 — unproven quote present. never ship an unproven quote.", None)]))
    else:
        lines.append(row(pal, [("✔ gate   ", 32),
                               ("EXIT 0 — every quote verified. ship it.", None)]))
    lines.append(bottom_border())
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="quotecop",
        description="The anti-hallucination button — did this quote actually exist in this source?",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--file", metavar="PATH", help="source text file")
    src.add_argument("--source", metavar="TEXT", help="source text pasted inline")
    ap.add_argument("--quote", action="append", metavar="TEXT", help="the quoted claim (repeatable)")
    ap.add_argument("--quotes-file", metavar="PATH", help="file with one quote per line")
    ap.add_argument("--json", action="store_true", help="machine-readable record, no cards")
    ap.add_argument("--color", choices=["auto", "always", "never"], default="auto")
    ap.add_argument("--no-gate", action="store_true", help="exit 0 even when a quote is NOT-FOUND")
    ap.add_argument("--version", action="version", version="quotecop " + __version__)
    args = ap.parse_args(argv)

    # ---- source text: --file | --source | piped stdin
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as fh:
                source = fh.read()
        except OSError as exc:
            print("quotecop: cannot read source file: " + str(exc), file=sys.stderr)
            return 2
        src_name = os.path.basename(args.file)
    elif args.source is not None:
        source = args.source
        src_name = "(pasted source)"
    elif not sys.stdin.isatty():
        source = sys.stdin.read()
        src_name = "(stdin)"
    else:
        print("quotecop: give a source with --file, --source, or piped stdin", file=sys.stderr)
        return 2

    # ---- quotes: --quote (repeatable) + --quotes-file
    quotes = list(args.quote or [])
    if args.quotes_file:
        try:
            with open(args.quotes_file, encoding="utf-8") as fh:
                for line in fh:
                    line = line.rstrip("\n").strip()
                    if line:
                        quotes.append(line)
        except OSError as exc:
            print("quotecop: cannot read quotes file: " + str(exc), file=sys.stderr)
            return 2
    if not quotes:
        print("quotecop: give at least one quote with --quote or --quotes-file", file=sys.stderr)
        return 2

    record = citecop.verify_batch(quotes, source)
    record["source"]["name"] = src_name

    if args.json:
        print(json.dumps(record, indent=2, ensure_ascii=False))
    else:
        mode = args.color
        if mode == "auto":
            mode = "always" if sys.stdout.isatty() and os.environ.get("NO_COLOR") is None else "never"
        pal = Palette(mode == "always")
        for line in banner(pal, src_name, record["source"]["sha256"],
                           record["source"]["chars"], len(quotes)):
            print(line)
        for rec in record["citations"]:
            for line in quote_card(pal, rec, src_name,
                                   record["source"]["chars"], record["source"]["sha256"], source):
                print(line)
        gate_fired = record["tally"]["not_found"] > 0
        for line in summary_card(pal, record["tally"], record["grounding_rate"], gate_fired):
            print(line)

    if record["tally"]["not_found"] > 0 and not args.no_gate:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
