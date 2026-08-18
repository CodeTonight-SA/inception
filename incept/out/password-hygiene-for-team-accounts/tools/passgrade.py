#!/usr/bin/env python3
"""passgrade — offline password-strength grader (stdlib).

Planted by INCEPTION.
domain:    password hygiene for team accounts
seed:      b437b5e89f1ca774dfb1677d8cbbbb9b2ef463f94224e0644ef9cc0d2afb8425
genesis:   085877795c6ed329d880c12490999afcb57eeccee06ee7bc67622b10a0e1f73c   (hypothesis SHA-256)
deadline:  2026-01-31

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

SEED_SHA256 = "b437b5e89f1ca774dfb1677d8cbbbb9b2ef463f94224e0644ef9cc0d2afb8425"
GENESIS_SHA256 = "085877795c6ed329d880c12490999afcb57eeccee06ee7bc67622b10a0e1f73c"
GENESIS_FILE_SHA256 = "9739b8420a63402ecd569bb846e043d449482e818e420f9bef4013ac752d63d1"

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
