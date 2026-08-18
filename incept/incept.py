#!/usr/bin/env python3
"""incept.py — INCEPTION · the idea-seed generator (GRASP-flavoured, stdlib only).

Give it any domain (one line). It:
  (a) emits a SIGNED genesis hypothesis — a falsifiable, deadline-bound
      prediction about that domain — written to genesis.md with its SHA-256;
  (b) scaffolds a WORKING micro-tool for that domain (stdlib, runnable, real);
  (c) prints a PLANTED CARD showing the seed -> hypothesis -> tool hash chain.

Everything is content-addressed: seed = SHA-256(domain), and every
artifact downstream is derived from that seed — re-running on the same domain
reproduces the identical seed, hypothesis text, tool bytes and hashes.
Determinism is load-bearing: same seed, same everything.

GRASP family — reimplemented stdlib arithmetic (predecessor hash-chaining +
the verbatim-quote floor). Don't trust it — witness it.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import random
import re
import sys
import textwrap
from datetime import date, timedelta

VERSION = "incept/1.0"
EPOCH = date(2026, 1, 1)          # deterministic hypothesis dates only — no wall clock
ARCHETYPES = ("quotecheck", "passgrade", "journal")

DESCRIBE = {
    "quotecheck": "verbatim quote verification — fabricated quotes can never pass",
    "passgrade":  "offline password-strength grader — deterministic scores",
    "journal":    "signed observation journal — chained, replayable provenance",
}
TOOL_NAME = {"quotecheck": "quotecheck.py", "passgrade": "passgrade.py", "journal": "journal.py"}

# ------------------------------------------------------------------ helpers

def sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def slugify(domain: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", domain.strip().lower()).strip("-")
    return s[:40] or "domain"


def seed_hash(domain: str) -> str:
    """The content address of the idea: stable for a given domain. The
    deadline is a hypothesis parameter, not part of the seed — so the seed
    is identical whether the deadline is auto-derived or user-supplied."""
    canon = f"{VERSION}|{domain.strip().lower()}"
    return sha256(canon)


def seeded_rng(seed: str, salt: str) -> random.Random:
    return random.Random(int(sha256(seed + "|" + salt), 16))


def deterministic_deadline(seed: str) -> str:
    rng = seeded_rng(seed, "deadline")
    offset = 14 + rng.randrange(77)                      # 14..90 days past EPOCH
    return (EPOCH + timedelta(days=offset)).isoformat()


def pick_archetype(domain: str) -> str:
    d = domain.strip().lower()
    if any(k in d for k in ("quote", "quotes", "transcript", "meeting", "summary", "notes")):
        return "quotecheck"
    if any(k in d for k in ("password", "passwords", "passphrase", "credential", "secret", "auth")):
        return "passgrade"
    return "journal"                                     # always-domain-appropriate fallback


# ------------------------------------------------------------------ hypotheses

def build_hypothesis(domain: str, archetype: str, deadline: str, rng: random.Random):
    if archetype == "quotecheck":
        vehicle = rng.choice(("a weekly digest", "an executive summary", "the release notes"))
        claim = rng.choice(("quoted", "circulated", "attributed"))
        text = (
            f"By {deadline}, at least one quote claimed to come from this domain "
            f"({domain}) — {claim} in {vehicle} — will fail verbatim verification "
            f"against its source text: words that were never spoken, rendered "
            f"not_found by string arithmetic."
        )
        falsifier = (
            "A single quote, attributed to the corpus, that is not verbatim present "
            "in the corpus text. The check is substring arithmetic, not judgement — "
            "run quotecheck.py and watch it render not_found."
        )
    elif archetype == "passgrade":
        text = (
            f"By {deadline}, at least one password in active use for this domain "
            f"({domain}) will score below 40/100 under passgrade's deterministic "
            f"rubric — and at least one entry from the embedded common-passwords "
            f"list will be rated WEAK, never STRONG."
        )
        falsifier = (
            "A password rated STRONG that a deterministic re-run of passgrade "
            "rates WEAK. The rubric is fixed arithmetic, so the rating is replayable."
        )
    else:  # journal
        text = (
            f"By {deadline}, at least one observation recorded in this domain's "
            f"journal ({domain}) will be superseded or contradicted by a later "
            f"entry — and the signed prev-hash chain will prove both entries were "
            f"recorded in that order, or the chain breaks."
        )
        falsifier = (
            "Two journal entries whose chain cannot be replayed: entry N+1 whose "
            "prev hash does not equal the hash of entry N. The chain is arithmetic, "
            "so a broken link is evidence of tampering."
        )
    return text, falsifier


# ------------------------------------------------------------------ tool builders

def build_quotecheck_corpus(rng: random.Random):
    speakers = ["Aisha", "Ben", "Chen", "Dana", "Eli"]
    proj = rng.choice(["Aurora", "Beacon", "Cedar", "Drift", "Ember"])
    adj = rng.choice(["nightly", "weekly", "morning", "staging"])
    noun = rng.choice(["payments", "dashboard", "signup", "search", "billing"])
    return [
        f"{speakers[0]}: We should ship {proj} by end of quarter, no excuses.",
        f"{speakers[1]}: The {adj} build broke again on CI this morning.",
        f"{speakers[2]}: I asked twice for the {noun} spec and got nothing back.",
        f"{speakers[3]}: If the demo fails on Friday, we delay the launch.",
        f"{speakers[4]}: Our users keep complaining about {noun} loading time.",
        f"{speakers[0]}: Can we move the sync meeting to Thursday at ten?",
        f"{speakers[1]}: The budget for {proj} is locked; no new hires.",
        f"{speakers[2]}: I can fix the {noun} bug in a day, tops.",
        f"{speakers[3]}: Nobody read the {noun} doc I sent last week.",
        f"{speakers[4]}: Ship the {adj} version first, then polish.",
    ]


def build_quotecheck_quotes(lines: list):
    def spoken(i):
        return lines[i].split(": ", 1)[1]
    return [
        (spoken(0), "GENUINE"),
        ("no new hires", "GENUINE"),
        (spoken(3).replace("delay the launch", "cancel the launch"), "FABRICATED"),
        ("We have no plans to raise prices this quarter.", "FABRICATED"),
    ]


TOOL_QUOTECHECK = r'''#!/usr/bin/env python3
"""quotecheck — verbatim quote verification (GRASP cite.verify floor, stdlib).

Planted by INCEPTION.
domain:    @@DOMAIN@@
seed:      @@SEED@@
genesis:   @@GENESIS@@   (hypothesis SHA-256)
deadline:  @@DEADLINE@@

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

CORPUS = "\n".join(@@CORPUS@@)

# (quote, provenance) — GENUINE | FABRICATED | PROVIDED
DEMO_QUOTES = @@QUOTES@@

SEED_SHA256 = "@@SEED@@"
GENESIS_SHA256 = "@@GENESIS@@"
GENESIS_FILE_SHA256 = "@@GENESIS_FILE@@"


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
'''


TOOL_PASSGRADE = r'''#!/usr/bin/env python3
"""passgrade — offline password-strength grader (stdlib).

Planted by INCEPTION.
domain:    @@DOMAIN@@
seed:      @@SEED@@
genesis:   @@GENESIS@@   (hypothesis SHA-256)
deadline:  @@DEADLINE@@

Scores a password 0-100 with deterministic arithmetic: length, character-class
breadth, and membership in the embedded common-password list. Same password,
same score, every machine, forever. No judgement calls.
Don't trust it — witness it.

Usage:
  passgrade.py --check 'hunter2'
  passgrade.py --chain
"""
import argparse
import hashlib
import math
import re
import string
import sys

SEED_SHA256 = "@@SEED@@"
GENESIS_SHA256 = "@@GENESIS@@"
GENESIS_FILE_SHA256 = "@@GENESIS_FILE@@"

COMMON = [
    "password", "123456", "123456789", "qwerty", "abc123", "monkey",
    "dragon", "letmein", "trustno1", "admin", "welcome", "login",
    "princess", "sunshine", "master", "shadow", "iloveyou", "111111",
    "654321", "passw0rd",
]

_CLASSES = (string.ascii_lowercase, string.ascii_uppercase,
            string.digits, string.punctuation)


def sha256(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def grade(pw):
    if not pw:
        return 0, "EMPTY", 0.0
    union = {ch for ch in pw for cls in _CLASSES if ch in cls}
    entropy = len(pw) * math.log2(len(union)) if union else 0.0
    s = int(round(entropy))
    if pw in COMMON:
        s = min(s, 10)
    if len(set(pw)) == 1:
        s = min(s, 5)
    if re.fullmatch(r"\d+", pw):
        s = min(s, 15)
    if len(pw) < 8:
        s = min(s, 30)
    s = max(0, min(s, 100))
    verdict = "WEAK" if s < 40 else ("ACCEPTABLE" if s < 70 else "STRONG")
    return s, verdict, entropy


def main(argv=None):
    ap = argparse.ArgumentParser(description="offline password-strength grader")
    ap.add_argument("--check", metavar="PASSWORD", help="password to grade")
    ap.add_argument("--chain", action="store_true", help="print provenance chain and exit")
    args = ap.parse_args(argv)

    if args.chain:
        print("passgrade provenance chain (SHA-256)")
        print(f"  seed (idea)         {SEED_SHA256}")
        print(f"  genesis hypothesis  {GENESIS_SHA256}")
        print(f"  genesis.md (file)   {GENESIS_FILE_SHA256}")
        with open(__file__, "rb") as fh:
            own = sha256(fh.read())
        print(f"  this tool (file)    {own}")
        root = sha256(sha256(SEED_SHA256 + GENESIS_FILE_SHA256) + own)
        print(f"  root (planted card) {root}")
        return 0

    if not args.check:
        ap.error("pass a password with --check, or use --chain")

    score, verdict, entropy = grade(args.check)
    print("passgrade · offline strength grading")
    print(f"password   {args.check!r}")
    print(f"entropy    ~{entropy:.0f} bits")
    print(f"score      {score}/100")
    print(f"verdict    {verdict}")
    return 1 if verdict == "WEAK" else 0


if __name__ == "__main__":
    sys.exit(main())
'''


TOOL_JOURNAL = r'''#!/usr/bin/env python3
"""journal — signed observation journal for @@DOMAIN@@ (stdlib).

Planted by INCEPTION.
domain:    @@DOMAIN@@
seed:      @@SEED@@
genesis:   @@GENESIS@@   (hypothesis SHA-256)
deadline:  @@DEADLINE@@

Every entry is chained to the previous one by SHA-256, starting from the
genesis hypothesis hash. Replaying the chain proves entries were recorded in
the order they claim — a broken link is arithmetic evidence of tampering.
Don't trust it — witness it.

Usage:
  journal.py note "observation text"
  journal.py verify
  journal.py chain
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

SEED_SHA256 = "@@SEED@@"
GENESIS_SHA256 = "@@GENESIS@@"
GENESIS_FILE_SHA256 = "@@GENESIS_FILE@@"
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "journal.jsonl")


def sha256(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def head_hash():
    if not os.path.exists(DB):
        return GENESIS_SHA256
    with open(DB, "rb") as fh:
        return sha256(fh.read())


def main(argv=None):
    ap = argparse.ArgumentParser(description="signed observation journal")
    sub = ap.add_subparsers(dest="cmd", required=True)
    note = sub.add_parser("note", help="append a chained observation")
    note.add_argument("text", help="observation text")
    sub.add_parser("verify", help="replay the chain and check every link")
    sub.add_parser("chain", help="print anchor and current head")
    args = ap.parse_args(argv)

    if args.cmd == "chain":
        print("journal provenance chain (SHA-256)")
        print(f"  seed (idea)         {SEED_SHA256}")
        print(f"  genesis (anchor)    {GENESIS_SHA256}")
        print(f"  genesis.md (file)   {GENESIS_FILE_SHA256}")
        print(f"  head                {head_hash()}")
        return 0

    if args.cmd == "verify":
        if not os.path.exists(DB):
            print("journal empty — nothing to verify")
            return 0
        with open(DB, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        if not lines:
            print("journal empty — nothing to verify")
            return 0
        acc = b""
        for i, line in enumerate(lines, 1):
            try:
                entry = json.loads(line)
            except ValueError:
                print(f"  [!!] line {i}: not valid JSON — chain broken")
                return 1
            prev_expected = sha256(acc) if acc else GENESIS_SHA256
            if entry.get("prev") != prev_expected:
                print(f"  [!!] line {i}: prev hash mismatch — chain broken")
                print(f"        expected {prev_expected}")
                return 1
            acc += (line + "\n").encode("utf-8")
        print(f"  chain VERIFIED · {len(lines)} entry/entries · head {sha256(acc)}")
        return 0

    # cmd == note
    prev = head_hash()
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entry = {"prev": prev, "ts": ts, "note": args.text}
    line = json.dumps(entry, sort_keys=True, ensure_ascii=True)
    with open(DB, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print("  entry appended")
    print(f"    prev    {prev}")
    print(f"    sha256  {sha256(line)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def build_tool(archetype: str, domain: str, seed: str, hyp_hash: str, deadline: str,
               genesis_file: str, rng: random.Random):
    subs = {
        "@@DOMAIN@@": domain,
        "@@SEED@@": seed,
        "@@GENESIS@@": hyp_hash,
        "@@GENESIS_FILE@@": genesis_file,
        "@@DEADLINE@@": deadline,
    }
    if archetype == "quotecheck":
        lines = build_quotecheck_corpus(rng)
        subs["@@CORPUS@@"] = repr(lines)
        subs["@@QUOTES@@"] = repr(build_quotecheck_quotes(lines))
        source = TOOL_QUOTECHECK
    elif archetype == "passgrade":
        source = TOOL_PASSGRADE
    else:
        source = TOOL_JOURNAL
    for key, val in subs.items():
        source = source.replace(key, val)
    return source, TOOL_NAME[archetype]


# ------------------------------------------------------------------ rendering

def render_box(lines):
    w = max(len(l) for l in lines)
    out = ["┌" + "─" * (w + 4) + "┐"]
    for l in lines:
        out.append("│  " + l.ljust(w) + "  │")
    out.append("└" + "─" * (w + 4) + "┘")
    return "\n".join(out)


def field(label, value, width=64):
    """label + wrapped value, as single-line box rows."""
    wrapped = textwrap.wrap(value, width) or [""]
    rows = [f"{label:<11}{wrapped[0]}"]
    rows += [" " * 11 + l for l in wrapped[1:]]
    return rows


def render_hypothesis(domain, archetype, deadline, seed, hyp_text, falsifier, hyp_hash):
    lines = [f"GENESIS HYPOTHESIS · H-{hyp_hash[:8]}"]
    lines += field("domain:", domain, 66)
    lines += field("archetype:", archetype, 66)
    lines += field("deadline:", deadline, 66)
    lines += field("seed:", seed, 66)
    lines.append("")
    lines.append("hypothesis:")
    lines += ["  " + l for l in textwrap.wrap(hyp_text, 72)]
    lines.append("")
    fals = textwrap.wrap(falsifier, 70)
    lines.append("falsifier:  " + fals[0])
    lines += ["            " + l for l in fals[1:]]
    lines.append(f"SHA-256:    {hyp_hash}")
    return render_box(lines)


def render_card(domain, archetype, deadline, seed, hyp_hash, genesis_file, tool_hash,
                 root, tool_name, slug):
    lines = [f"INCEPTION · planted card · {slug}"]
    lines += field("domain:", domain, 60)
    lines += field("archetype:", archetype, 60)
    lines += field("deadline:", deadline, 60)
    lines.append("chain:       seed ⊂ genesis.md ⊂ tool   (GRASP hash chain)")
    lines.append("")
    lines.append(f"seed         {seed}")
    lines.append(f"hypothesis   {hyp_hash}   (body of genesis.md)")
    lines.append(f"genesis.md   {genesis_file}   (file bytes)")
    lines.append(f"tool         {tool_hash}   tools/{tool_name}")
    lines.append(f"root         {root}")
    lines.append("")
    lines.append("don't trust it — witness it")
    return render_box(lines)


def render_genesis(domain, archetype, seed, deadline, hyp_hash, hyp_text):
    return (
        "# GENESIS HYPOTHESIS\n"
        "\n"
        f"domain: {domain}\n"
        f"archetype: {archetype}\n"
        f"seed: {seed}\n"
        f"deadline: {deadline}\n"
        f"hypothesis id: H-{hyp_hash[:8]}\n"
        "\n"
        "<BEGIN BODY>\n"
        f"{hyp_text}\n"
        "<END BODY>\n"
        "\n"
        f"SHA-256 (body): {hyp_hash}\n"
    )


def render_card_file(slug, domain, archetype, deadline, seed, hyp_hash, genesis_file,
                      tool_hash, root):
    return (
        "INCEPTION planted card\n"
        f"slug: {slug}\n"
        f"domain: {domain}\n"
        f"archetype: {archetype}\n"
        f"deadline: {deadline}\n"
        f"seed: {seed}\n"
        f"hypothesis: {hyp_hash}\n"
        f"genesis_file: {genesis_file}\n"
        f"tool: {tool_hash}\n"
        f"root: {root}\n"
        "chain: seed < genesis.md < tool\n"
    )


# ------------------------------------------------------------------ verification

def verify_planted(domain, out_root, deadline_override):
    slug = slugify(domain)
    out_dir = os.path.join(out_root, slug)
    genesis_path = os.path.join(out_dir, "genesis.md")
    card_path = os.path.join(out_dir, "planted.card")
    if not (os.path.exists(genesis_path) and os.path.exists(card_path)):
        print(f"nothing planted for domain {domain!r} under {out_root}/ — "
              "run without --verify first")
        return 2

    genesis_bytes = open(genesis_path, "rb").read()
    genesis = genesis_bytes.decode("utf-8")
    card = open(card_path, encoding="utf-8").read()

    def file_get(text, key):
        for line in text.splitlines():
            if line.startswith(key + ":"):
                return line.split(":", 1)[1].strip()
        return None

    stored = {
        "domain": file_get(genesis, "domain"),
        "archetype": file_get(genesis, "archetype"),
        "deadline": deadline_override or file_get(genesis, "deadline"),
        "seed": file_get(genesis, "seed"),
        "hyp_hash": file_get(genesis, "SHA-256 (body)"),
    }
    card_seed = file_get(card, "seed")
    card_hyp = file_get(card, "hypothesis")
    card_genesis_file = file_get(card, "genesis_file")
    card_tool = file_get(card, "tool")
    card_root = file_get(card, "root")

    m = re.search(r"<BEGIN BODY>\n(.*)\n<END BODY>", genesis, re.S)
    if not m:
        print("genesis.md malformed — BODY markers missing")
        return 1
    body = m.group(1).rstrip("\n")

    print(f"verifying planted chain for {slug}")
    print(f"  deadline in effect: {stored['deadline']}")

    recomputed = {}
    recomputed["seed"] = seed_hash(domain)
    recomputed["hypothesis"] = sha256(body)
    recomputed["genesis_file"] = sha256(genesis_bytes)
    tool_path = os.path.join(out_dir, "tools", TOOL_NAME[stored["archetype"]])
    with open(tool_path, "rb") as fh:
        recomputed["tool"] = sha256(fh.read())
    recomputed["root"] = sha256(
        sha256(recomputed["seed"] + recomputed["genesis_file"]) + recomputed["tool"])

    checks = [
        ("seed",         recomputed["seed"],         card_seed,          True),
        ("hypothesis",   recomputed["hypothesis"],   card_hyp,           recomputed["hypothesis"] == stored["hyp_hash"]),
        ("genesis_file", recomputed["genesis_file"], card_genesis_file,  True),
        ("tool",         recomputed["tool"],         card_tool,          True),
        ("root",         recomputed["root"],         card_root,          True),
    ]
    ok = True
    for name, got, want, extra in checks:
        good = (got == want) and extra
        ok = ok and good
        print(f"  {name:<13} {'✓' if good else '✗'} {got}")
        if not good:
            print(f"                expected {want}")
    if ok:
        print("chain VERIFIED — every artifact matches the seed, byte for byte.")
        return 0
    print("chain TAMPERED — at least one artifact no longer matches its content address.")
    return 1


# ------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="incept.py",
        description="INCEPTION — idea-seed generator (GRASP-flavoured). "
                    "Give it any domain: it plants a signed genesis hypothesis, "
                    "scaffolds a working stdlib micro-tool, and prints a "
                    "content-addressed seed -> hypothesis -> tool chain.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("domain", nargs="?",
                    help="one-line domain, e.g. 'meeting quotes: verify quotes verbatim'")
    ap.add_argument("--deadline", default=None, metavar="YYYY-MM-DD",
                    help="hypothesis deadline (default: deterministic seeded date)")
    ap.add_argument("--archetype", choices=ARCHETYPES,
                    help=f"force a tool archetype ({', '.join(ARCHETYPES)})")
    ap.add_argument("--out", default="out", help="output root (default: ./out)")
    ap.add_argument("--check", action="store_true",
                    help="compute and print only — write nothing")
    ap.add_argument("--verify", action="store_true",
                    help="verify the planted chain for this domain")
    ap.add_argument("--list", action="store_true",
                    help="list available tool archetypes")
    args = ap.parse_args(argv)

    if args.list:
        print("available tool archetypes (all stdlib):")
        for name in ARCHETYPES:
            print(f"  {name:<11} {DESCRIBE[name]}")
        return 0

    if not args.domain:
        ap.error("a domain is required (or use --list)")

    if args.deadline and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.deadline):
        ap.error("--deadline must be YYYY-MM-DD")

    if args.verify:
        return verify_planted(args.domain, args.out, args.deadline)

    seed = seed_hash(args.domain)
    deadline = args.deadline or deterministic_deadline(seed)
    archetype = args.archetype or pick_archetype(args.domain)
    hyp_text, falsifier = build_hypothesis(
        args.domain, archetype, deadline, seeded_rng(seed, "hypothesis"))
    hyp_hash = sha256(hyp_text)
    genesis_text = render_genesis(args.domain, archetype, seed, deadline, hyp_hash, hyp_text)
    genesis_file = sha256(genesis_text)
    tool_source, tool_name = build_tool(
        archetype, args.domain, seed, hyp_hash, deadline, genesis_file,
        seeded_rng(seed, "tool:" + archetype))
    tool_hash = sha256(tool_source)
    root = sha256(sha256(seed + genesis_file) + tool_hash)
    slug = slugify(args.domain)

    print(render_hypothesis(args.domain, archetype, deadline, seed,
                            hyp_text, falsifier, hyp_hash))
    print()
    print(render_card(args.domain, archetype, deadline, seed,
                      hyp_hash, genesis_file, tool_hash, root, tool_name, slug))

    if args.check:
        print()
        print("dry run — nothing written. re-running on the same domain reproduces")
        print("the identical seed, hypothesis, tool bytes and hashes.")
        return 0

    out_dir = os.path.join(args.out, slug)
    tools_dir = os.path.join(out_dir, "tools")
    os.makedirs(tools_dir, exist_ok=True)
    card_text = render_card_file(slug, args.domain, archetype, deadline,
                                 seed, hyp_hash, genesis_file, tool_hash, root)
    with open(os.path.join(out_dir, "genesis.md"), "w", encoding="utf-8") as fh:
        fh.write(genesis_text)
    with open(os.path.join(out_dir, "planted.card"), "w", encoding="utf-8") as fh:
        fh.write(card_text)
    with open(os.path.join(tools_dir, tool_name), "w", encoding="utf-8") as fh:
        fh.write(tool_source)

    print()
    print(f"planted:  {out_dir}/")
    print(f"  genesis.md      {hyp_hash}")
    print(f"  planted.card    {root}")
    print(f"  tools/{tool_name}  {tool_hash}")
    print(f"verify:   python3 incept.py {args.domain!r} --verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
