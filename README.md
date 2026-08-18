# INCEPTION — the witness stack for AI

**One thesis, five tools, zero install.** When an AI makes a claim, how does a human check it without trusting anyone? Each tool answers with the same mechanism: *string arithmetic, not judgement* — a file that verifies itself.

The kit certifies itself: every file's SHA-256 is recorded in `manifest.json`, and `verify_kit.py` recomputes them all (pure stdlib, no network). Tamper with one byte and the kit stamps itself **BROKEN**.

## The five tools

| Tool | What it is | The delightful moment |
|---|---|---|
| [`receipt/`](receipt) | The AI Receipt — a thermal-paper receipt for any AI claim; citations verified in-browser with offsets, green VERIFIED / red NOT-FOUND | Edit one character of the claim set and the receipt stamps **INTEGRITY FAILED** — the barcode IS the fingerprint |
| [`passport/`](passport) | HAPPIverse Passport — one HTML file renders an AI session's papers; LIVE VERIFY re-runs the whole audit in the page's own JavaScript | Identity papers that prove themselves: edit one word and the page stamps itself **ALTERED** in red, naming which record broke |
| [`quotecop/`](quotecop) | Cite-Cop — the anti-hallucination button: one command answers whether a quote actually exists in its source | The verdict card is the product: green with character offsets, or an undeniable red NOT-FOUND |
| [`incept/`](incept) | INCEPTION — the idea-seed: a domain in, a signed falsifiable genesis hypothesis + a working scaffolded tool out | Run it twice: byte-identical. Append one line: **chain TAMPERED** |
| [`djournal/`](djournal) | Decision Journal — prove what you decided: append-only sealed entries | One flipped byte flips the card from VERIFIED to **TAMPER DETECTED** |

## The thesis (full-converge)

Marks (watermarks, C2PA) answer *"did an AI touch this?"* — in-band, probabilistic, provider-detected. These tools answer *"can a skeptic check what it claimed?"* — out-of-band, deterministic, checkable by anyone with a browser or a terminal. The differentiator is GRASP's moat made consumer-grade: **don't trust it — witness it.**

## Verify the kit

```bash
python3 verify_kit.py          # recompute every hash in manifest.json
python3 verify_kit.py --json   # machine-readable
```

The full narrative, demo transcripts, and provenance live in [INCEPTION.md](INCEPTION.md).

## Licence

AGPL-3.0-only — see [LICENSE](LICENSE).

*Incepted 2026-08-18 by an overnight AFK session: V>> with assistance of DeepSeek V4 Pro (deepseek-v4-pro), alongside the GRASP Ed25519/ML-DSA-65 signing upgrade ([github.com/CodeTonight-SA/grasp](https://github.com/CodeTonight-SA/grasp)).*
