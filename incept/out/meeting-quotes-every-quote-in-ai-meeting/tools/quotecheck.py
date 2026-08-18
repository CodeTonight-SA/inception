#!/usr/bin/env python3
"""quotecheck — verbatim quote verification (GRASP cite.verify floor, stdlib).

Planted by INCEPTION.
domain:    meeting quotes: every quote in AI meeting notes must exist verbatim in the transcript
seed:      5e0280c2f673a21572bcfb2261f53202214590c19d2b8cb1b1f63d9ef69e71db
genesis:   a36de6c2f3eb719b95378ed3c4b32d72127b5613c93b3a055cc3ec802e8729ae   (hypothesis SHA-256)
deadline:  2026-03-23

A quote VERIFIES only if it appears verbatim inside the corpus text — string
arithmetic, not judgement. A fabricated quote renders not_found and can never
pass. Don't trust it — witness it.

Usage:
  quotecheck.py [corpus.txt] [quotes.txt] [--relax] [--strict] [--chain]
    corpus.txt   source text (default: embedded demo corpus)
    quotes.txt   one quote per line (default: embedded demo quotes)
    --relax      ignore whitespace differences before matching
    --strict     exit 1 if any quote is not_found (build-gate)
    --chain      print this tool's provenance chain and exit
"""
import argparse
import hashlib
import sys

CORPUS = "\n".join(['Aisha: We should ship Cedar by end of quarter, no excuses.', 'Ben: The staging build broke again on CI this morning.', 'Chen: I asked twice for the billing spec and got nothing back.', 'Dana: If the demo fails on Friday, we delay the launch.', 'Eli: Our users keep complaining about billing loading time.', 'Aisha: Can we move the sync meeting to Thursday at ten?', 'Ben: The budget for Cedar is locked; no new hires.', 'Chen: I can fix the billing bug in a day, tops.', 'Dana: Nobody read the billing doc I sent last week.', 'Eli: Ship the staging version first, then polish.'])

# (quote, provenance) — GENUINE | FABRICATED | PROVIDED
DEMO_QUOTES = [('We should ship Cedar by end of quarter, no excuses.', 'GENUINE'), ('no new hires', 'GENUINE'), ('If the demo fails on Friday, we cancel the launch.', 'FABRICATED'), ('We have no plans to raise prices this quarter.', 'FABRICATED')]

SEED_SHA256 = "5e0280c2f673a21572bcfb2261f53202214590c19d2b8cb1b1f63d9ef69e71db"
GENESIS_SHA256 = "a36de6c2f3eb719b95378ed3c4b32d72127b5613c93b3a055cc3ec802e8729ae"
GENESIS_FILE_SHA256 = "35dc56fe46a34920983776d25d5d28ebb769364839428896a7cdddddb56e721f"


def sha256(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def verify_quote(quote, corpus, relax):
    if relax:
        return " ".join(quote.split()) in " ".join(corpus.split())
    return quote in corpus


def load_quotes(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            q = raw.rstrip("\n")
            if q.strip():
                out.append((q, "PROVIDED"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="verbatim quote verification")
    ap.add_argument("corpus", nargs="?", help="corpus file (default: embedded demo)")
    ap.add_argument("quotes", nargs="?", help="quotes file, one per line (default: embedded demo)")
    ap.add_argument("--relax", action="store_true", help="ignore whitespace differences")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any quote is not_found")
    ap.add_argument("--chain", action="store_true", help="print provenance chain and exit")
    args = ap.parse_args(argv)

    if args.chain:
        print("quotecheck provenance chain (SHA-256)")
        print(f"  seed (idea)         {SEED_SHA256}")
        print(f"  genesis hypothesis  {GENESIS_SHA256}")
        print(f"  genesis.md (file)   {GENESIS_FILE_SHA256}")
        with open(__file__, "rb") as fh:
            own = sha256(fh.read())
        print(f"  this tool (file)    {own}")
        root = sha256(sha256(SEED_SHA256 + GENESIS_FILE_SHA256) + own)
        print(f"  root (planted card) {root}")
        return 0

    corpus = CORPUS
    src = "embedded demo corpus"
    if args.corpus:
        with open(args.corpus, encoding="utf-8") as fh:
            corpus = fh.read()
        src = args.corpus

    quotes = DEMO_QUOTES
    if args.quotes:
        quotes = load_quotes(args.quotes)

    print("QUOTECHECK · verbatim quote verification")
    print(f"corpus: {src} · {len(corpus)} bytes · {len(quotes)} quote(s)")
    print("─" * 62)
    verified = 0
    for text, prov in quotes:
        ok = verify_quote(text, corpus, args.relax)
        if ok:
            verified += 1
        mark = "[ OK ] verified  " if ok else "[ !! ] not_found "
        print(f"{mark} {prov:<10} {text!r}")
    rate = (verified / len(quotes)) if quotes else 0.0
    print("─" * 62)
    print(f"grounding rate: {verified}/{len(quotes)} = {rate:.3f}")
    if args.strict and verified < len(quotes):
        print("[strict] one or more quotes NOT FOUND — this gate cannot pass")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
