# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 CodeTonight SA
"""citecop — deterministic citation verification engine. Zero dependencies.

The arithmetic twin of GRASP's cite.verify (HAPPI happi/1.3, reference
implementation at grasp/cite_verify.py): the same deterministic ladder —
exact substring -> whitespace/typographic/case-tolerant -> not_found — so a
fabricated quote can NEVER verify. String arithmetic, not judgement.

Scope honesty: this proves a quote is **verbatim in the supplied source
text**. It does not prove the source is authentic, and it does not prove the
quote supports the claim it is attached to.

Offsets returned index the ORIGINAL source text verbatim: every
normalisation applied is length-preserving (single char -> single char), so a
match found in normalised text maps 1:1 back to the raw source.
"""
from __future__ import annotations

import hashlib
import re

__all__ = ["verify", "verify_batch", "source_fingerprint"]

_WS = re.compile(r"\s+")

# Length-preserving typographic normalisation (single char -> single char):
# en/em dashes -> hyphen, curly quotes -> straight, non-breaking spaces -> space.
_TYPO = {
    0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-", 0x2014: "-", 0x2015: "-",
    0x2018: "'", 0x2019: "'", 0x201B: "'",
    0x201C: '"', 0x201D: '"', 0x201F: '"',
    0x00A0: " ", 0x2007: " ", 0x2009: " ", 0x202F: " ",
}

RUNG_EXACT = "exact"
RUNG_WS = "tolerant-whitespace"
RUNG_CASE = "tolerant-case"


def _typo(s: str) -> str:
    return s.translate(_TYPO)


def source_fingerprint(text: str) -> dict:
    """sha256 + char count of the supplied source text."""
    return {
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "chars": len(text),
    }


def _token_pattern(quote: str):
    """Whitespace-run-flexible regex for an already-normalised quote.

    Each token is escaped; tokens are joined with the pattern r"\\s+" so any
    run of whitespace in the source (spaces, tabs, newlines) matches a single
    space in the quote. The match's offsets are valid in the source because
    normalisation is length-preserving.
    """
    toks = [re.escape(t) for t in _WS.split(quote) if t]
    if not toks:
        return None
    return re.compile(r"\s+".join(toks))


def verify(quote: str, source_text: str) -> dict:
    """Run the ladder for one (quote, source) pair.

    Returns {status, rung, start, end}:
      status  "verified" | "not_found"
      rung    "exact" | "tolerant-whitespace" | "tolerant-case" | None
      start/end  character offsets into the ORIGINAL source, or -1/-1.
    """
    q = (quote or "").strip()
    if not q or not source_text:
        return {"status": "not_found", "rung": None, "start": -1, "end": -1}

    # Rung 1 — exact verbatim substring in the raw source.
    idx = source_text.find(q)
    if idx != -1:
        return {"status": "verified", "rung": RUNG_EXACT,
                "start": idx, "end": idx + len(q)}

    # Normalise (length-preserving) for the tolerant rungs.
    qn = _typo(q)
    sn = _typo(source_text)

    # Rung 2 — whitespace runs + typographic punctuation flexible.
    pat = _token_pattern(qn)
    if pat is not None:
        m = pat.search(sn)
        if m:
            return {"status": "verified", "rung": RUNG_WS,
                    "start": m.start(), "end": m.end()}

    # Rung 3 — case-insensitive on top. Only when case-folding preserves
    # length, so offsets keep indexing the original source verbatim.
    ql = qn.lower()
    sl = sn.lower()
    if len(ql) == len(qn) and len(sl) == len(sn):
        patl = _token_pattern(ql)
        if patl is not None:
            m = patl.search(sl)
            if m:
                return {"status": "verified", "rung": RUNG_CASE,
                        "start": m.start(), "end": m.end()}

    return {"status": "not_found", "rung": None, "start": -1, "end": -1}


def verify_batch(quotes, source_text: str) -> dict:
    """Verify many quotes against one source; tally + grounding rate.

    Record shape mirrors GRASP's provenance record (per-source sha256+chars,
    per-citation status+offsets, tally, grounding_rate).
    """
    results = []
    for q in quotes:
        verdict = verify(q, source_text)
        results.append({"quote": q, **verdict})
    grounded = sum(1 for r in results if r["status"] == "verified")
    return {
        "source": source_fingerprint(source_text),
        "citations": results,
        "tally": {"verified": grounded, "not_found": len(results) - grounded},
        "grounding_rate": round(grounded / len(results), 3) if results else 0.0,
    }
