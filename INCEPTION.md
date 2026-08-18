# INCEPTION — the witness stack for AI

**One thesis, five tools, zero install.**

Every tool in this kit is a different answer to the same question: *when an AI
makes a claim, how does a human check it without trusting anyone?* The answer is
always the same — string arithmetic, not judgement; a file that verifies itself;
no account, no network, no runtime.

The kit certifies itself: every file's SHA-256 is recorded in manifest.json, and
verify_kit.py recomputes all of them. Tamper with one byte of one tool and the
kit stamps itself BROKEN. The kit practices what the tools preach.

## The five tools

| # | Tool | One line | The delightful moment |
|---|------|----------|----------------------|
| 1 | receipt/ | The AI Receipt — a thermal-paper receipt for any AI claim. Every citation verified in-browser, green VERIFIED with offsets, red NOT-FOUND. | Edit one character of the claim set and the receipt stamps INTEGRITY FAILED — the barcode IS the fingerprint. |
| 2 | passport/ | HAPPIverse Passport — the AI's papers. One HTML file renders a passport card and LIVE VERIFY re-runs the whole audit in the page's own JavaScript. | Identity papers that prove themselves: edit one word and the page stamps itself ALTERED in red, naming which record broke. |
| 3 | quotecop/ | Cite-Cop — the anti-hallucination button. One command: did this quote actually exist in this source? | The verdict card is the product: green with character offsets, or an undeniable red NOT-FOUND. |
| 4 | incept/ | INCEPTION — the idea-seed. Give it a domain, it plants a signed, falsifiable genesis hypothesis and a working tool, all content-addressed. | Determinism proven: two runs are byte-identical; append one line and the chain reads TAMPERED. |
| 5 | djournal/ | Decision Journal — prove what you decided. Append-only, sealed entries; tamper a byte and verification breaks. | Your journal cannot lie about itself. |

## Converged thesis (full-converge, depth 11)

All five converge on GRASP's moat made consumer-grade: **out-of-band, deterministic,
self-verifying witnesses**. Marks (watermarks, C2PA) answer "did an AI touch this?" —
in-band, probabilistic, provider-detected. These tools answer "can a skeptic check
what it claimed?" — out-of-band, deterministic, checkable by anyone with a browser
or a terminal. The differentiator is the same one that powers the GRASP proof layer:
*don't trust it — witness it* — now in a form a human can hold.

## Verify the kit

    python3 verify_kit.py        # recompute every hash in manifest.json
    python3 verify_kit.py --json # machine-readable

The verifier is arithmetic: Python stdlib only, no network. The kit root is the
SHA-256 of the canonical manifest — printed on every verify run.

*Incepted 2026-08-18 by an overnight AFK session: V>> with assistance of DeepSeek
V4 Pro (deepseek-v4-pro), building alongside the GRASP Ed25519/ML-DSA-65 upgrade.*
