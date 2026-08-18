#!/usr/bin/env python3
"""dj demo helper: flip exactly ONE byte inside journal.jsonl to prove tamper-evidence.

Usage: python3 demo_tamper.py <journal.jsonl>
Flipped byte is inside D-0002's "what" field ('OpenTimestamps' -> 'NpenTimestamps'),
so the JSON stays valid — only the content changes.
"""
import pathlib
import sys


def main():
    p = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "demo/.djournal/journal.jsonl")
    data = bytearray(p.read_bytes())
    lines = data.split(b"\n")
    ln = lines[1]  # entry D-0002
    i = ln.find(b"OpenTimestamps")
    if i == -1:
        sys.exit(f"tamper target 'OpenTimestamps' not found in line 2 of {p}")
    orig = ln[i]
    ln[i] = orig ^ 1  # 0x4F 'O' -> 0x4E 'N' — exactly one byte
    lines[1] = ln
    p.write_bytes(b"\n".join(lines))
    print(f"tamper applied: one byte flipped in D-0002 (0x{orig:02x} -> 0x{ln[i]:02x} at 'OpenTimestamps')")


if __name__ == "__main__":
    main()
