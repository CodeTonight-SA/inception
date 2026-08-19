#!/usr/bin/env python3
"""journal — signed observation journal for the grip-sovereign moat: GRIP convergent RSI with guardrails and Banach idempotency, HAL harness abstraction with sovereign multi-LLM councils, HAPPI ai-as-a-syscall 1.3 with IDR and memory-chain provenance, GRASP tamper-evident permanent decision storage — don't trust the AI, witness it (stdlib).

Planted by INCEPTION.
domain:    the grip-sovereign moat: GRIP convergent RSI with guardrails and Banach idempotency, HAL harness abstraction with sovereign multi-LLM councils, HAPPI ai-as-a-syscall 1.3 with IDR and memory-chain provenance, GRASP tamper-evident permanent decision storage — don't trust the AI, witness it
seed:      f3f3ade8376cf80c1c5691de1e220107b97cdbe8153f524c263de01fe8485f47
genesis:   5a7c4372b40d6794967ac46203d0bc3e5da2987335f28bb3f750b89446646500   (hypothesis SHA-256)
deadline:  2026-01-19

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

SEED_SHA256 = "f3f3ade8376cf80c1c5691de1e220107b97cdbe8153f524c263de01fe8485f47"
GENESIS_SHA256 = "5a7c4372b40d6794967ac46203d0bc3e5da2987335f28bb3f750b89446646500"
GENESIS_FILE_SHA256 = "da2bafb7dfe7dedf36e44b0ec4bf0a49ac397913dbf134597806097844c34002"
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
