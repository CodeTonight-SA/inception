#!/usr/bin/env python3
"""journal — signed observation journal for urban farming observations (stdlib).

Planted by INCEPTION.
domain:    urban farming observations
seed:      f4aa509e6392c6d75e95ee55da4f0d325873187d41ce73c664e61fb59e0258cf
genesis:   71fbf7afa2cd17159975a2a90f689ee02b456a8c6c244e24f48d6a4ac1375019   (hypothesis SHA-256)
deadline:  2026-03-14

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

SEED_SHA256 = "f4aa509e6392c6d75e95ee55da4f0d325873187d41ce73c664e61fb59e0258cf"
GENESIS_SHA256 = "71fbf7afa2cd17159975a2a90f689ee02b456a8c6c244e24f48d6a4ac1375019"
GENESIS_FILE_SHA256 = "1d346b27f40f3355034e90fb5cc06f72666f51cbdfe8de6aa4ae055fad17b4a5"
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
