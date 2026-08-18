# GRASP · AI Receipt — /inception/receipt

A single self-contained HTML file that turns any AI claim (with cited sources)
into a gorgeous receipt that **verifies itself in the browser**. The cite.verify
floor — deterministic string arithmetic, not judgement — is reimplemented in
plain JS inside the file: every citation is stamped **green VERIFIED (with
character offsets)** or **red NOT-FOUND**, and the whole claim set is
content-addressed by a SHA-256 fingerprint that the receipt recomputes live.

> Don't trust it — witness it. Open one file. No install. No network. No trust.

## Files

| file | what it is |
|---|---|
| `receipt_gen.py` | stdlib generator: claim spec JSON → `receipt.html` (deterministic: same spec ⇒ same bytes) |
| `demo.json` | demo claim set: Bitcoin whitepaper + UDHR Art. 1 — 3 real citations, 2 deliberately fabricated |
| `receipt.html` | **the deliverable** — generated, opens in any browser, self-verifies |
| `verify_core.js` | the cite.verify arithmetic (exact substring → typographic-tolerant → not_found), single source of truth, inlined into every receipt |
| `verify_check.cjs` | cross-runtime conformance: Python generator vs in-browser JS vs reference `grasp.cite_verify` — all three agree byte-for-byte |
| `receipt.png` | headless-Chrome render (visual proof) |
| `pixaudit.py` | stdlib PNG decoder used to machine-audit the render |

## Use

    python3 receipt_gen.py demo.json -o receipt.html        # build
    open receipt.html                                       # verify in-browser
    node verify_check.cjs                                   # cross-runtime proof
    python3 receipt_gen.py spec.json --strict               # fail on any not_found

## The arithmetic (mirror of grasp/cite_verify.py · HAPPI 1.3 cite.verify)

1. exact substring match → `verified` (offsets into the source)
2. whitespace + typographic fold (curly quotes, en/em dashes, NBSP) → `fuzzy` (also grounded)
3. otherwise → `not_found` — a fabricated quote can never pass, in any language, in any runtime.

## What a skeptic can verify

- **The red is real**: `c3` / `c5` are invented sentences; grep the sources in the
  receipt — they are not there — and watch them stamp NOT-FOUND.
- **The green is real**: offsets [404–505] and [0–63] point at the verbatim
  sentences inside the embedded sources.
- **It is content-addressed**: edit one character of the embedded claim set and
  the integrity banner flips to INTEGRITY FAILED (recomputed hash shown).
- **Three runtimes agree**: `node verify_check.cjs` reproduces the fingerprint
  and every verdict that Python printed — and `grasp.cite_verify.process`
  returns the identical record.

Provenance: built overnight by an autonomous GRIP agent (deepseek-v4-flash) in
the AFK inception session, mirroring the reference implementation at
`~/CodeTonight/grasp/grasp/cite_verify.py` (AGPL-3.0).
