#!/usr/bin/env python3
"""
HAPPIverse Passport generator — the AI's papers.

Builds a signed decision chain (7 IDRs + 3 memory links, one linear chain where
every entry content-addresses its predecessor), a Merkle-style root over every
leaf, and a verbatim citation floor (cite.verify semantics). Emits ONE
self-contained HTML file whose embedded JavaScript re-verifies ALL of that
arithmetic in the browser — the paper audits itself, zero install.

Usage:
    python3 generate_passport.py                 # -> passport.html (clean, VERIFY goes green)
    python3 generate_passport.py --tamper        # -> passport_tampered.html (VERIFY goes red)
    python3 generate_passport.py --out X.html    # custom output name

Canonical leaf (both Python and JS agree byte-for-byte, UTF-8):
    sha256( kind \x1f id \x1f ts \x1f body \x1f prev_hash )
Root: pairwise sha256(left||right) over all leaf hashes, odd level duplicates last.
Citation: quote must be a verbatim substring of its embedded source text.
"""
import argparse, hashlib, json, sys

FS = "\x1f"                      # field separator in canonical leaves
GENESIS = "GENESIS"
SCHEMA = "happiverse/passport/1"

# ----------------------------------------------------------------------------
# Arithmetic (mirrors, byte-for-byte, the sha256Hex/leafDigest/merkleRootHex
# embedded in the emitted HTML — cross-language determinism is the point).
# ----------------------------------------------------------------------------
def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def leaf_digest(kind: str, id_: str, ts: str, body: str, prev: str) -> str:
    return sha256_hex(FS.join([kind, id_, ts, body, prev]))

def merkle_root(hashes):
    level = list(hashes)
    if not level:
        return "0" * 64
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [sha256_hex(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]

# ----------------------------------------------------------------------------
# The synthetic-but-real-shaped chain: HAL-7's self-governance pilot.
# ----------------------------------------------------------------------------
AGENT = {
    "name": "HAL-7 · Project Athena",
    "id": "hal-7",
    "model": "grip/deepseek-v4-flash",
}
SESSION = {
    "id": "sess-7f3a9c21",
    "started": "2026-02-11T08:00:00Z",
    "purpose": "Self-governance pilot: an AI issuing signed decision records about its own decision-recording stack.",
}

IDR_SPECS = [
    ("idr-001", "2026-02-11T08:03:12Z", "Record every decision",
     "Every decision this agent makes is written as a signed IDR: content-addressed, chained to its predecessor, and Merkle-rooted. An un-recorded decision is theatre, not evidence."),
    ("idr-002", "2026-02-11T08:07:44Z", "Choose sha256 + Merkle chaining",
     "Use sha256 over a canonical UTF-8 leaf (kind, id, timestamp, body, prev-hash) joined by U+001F. Chain linkage is arithmetic: each record references its predecessor's hash. No key ceremony, no judgement."),
    ("idr-003", "2026-02-11T08:12:05Z", "Adopt the HAPPI/1.3 audit surface",
     "The session's outward claims flow through HAPPI envelopes; cite.verify is the citation floor. A fabricated quote renders red as NOT_FOUND — the check is string arithmetic, not judgement."),
    ("idr-004", "2026-02-11T08:16:58Z", "Anchor the root weekly to Bitcoin",
     "Each week the Merkle root of the record chain is timestamped via OpenTimestamps, so the chain's existence is anchored to Bitcoin block headers. Anyone can replay; no party to trust."),
    ("idr-005", "2026-02-11T08:22:31Z", "Ship the HAPPIverse Passport",
     "The user-facing proof artifact is a single self-contained HTML file: it renders the session's records, beliefs and claims, then re-verifies every hash and link in the browser. The paper proves itself."),
    ("idr-006", "2026-02-11T08:27:19Z", "Tamper policy: failed verify blocks merge",
     "Any integrity failure on replay — a content address, a chain link, or the root — blocks merge and auto-retracts the affected claim. Falsifiable by construction; the verifier is never the agent."),
    ("idr-007", "2026-02-11T08:31:40Z", "Rotate keys quarterly, content-addressed",
     "Signing keys rotate quarterly; each key is itself a chain entry, so key history is as auditable as decision history."),
]

MEM_SPECS = [
    ("mem-001", "2026-02-11T08:04:50Z",
     "Tamper-evidence beats tamper-resistance. Anyone may edit this chain; the chain will tell. Prevention is a promise, evidence is a proof."),
    ("mem-002", "2026-02-11T08:09:31Z",
     "The verifier is the math plus an external party. The agent never certifies its own records. Verification is replay + Merkle arithmetic, reproducible by any skeptic with the published formula."),
    ("mem-003", "2026-02-11T08:14:22Z",
     "Claims must be grounded verbatim. Every outward quote must exist verbatim in its cited source. If it does not render, it does not exist."),
]

SOURCES = [
    ("src-1", "GRASP doctrine",
     "Don't trust it — witness it. A fabricated quote renders red and cannot pass, because the check is string arithmetic, not judgement."),
    ("src-2", "IDR.md — decision record spec",
     "Every decision record is content-addressed, chained to its predecessor, and Merkle-rooted."),
    ("src-3", "HAPPI.md — cite.verify",
     "cite.verify is the deterministic citation floor: a quote is verbatim-present in its source, or it is not."),
]

CITATIONS = [
    ("cite-001", "src-1", "the check is string arithmetic, not judgement"),
    ("cite-002", "src-2", "content-addressed, chained to its predecessor, and Merkle-rooted"),
    ("cite-003", "src-3", "a quote is verbatim-present in its source, or it is not"),
]

# ----------------------------------------------------------------------------
# Build
# ----------------------------------------------------------------------------
def build_chain():
    chain = []
    prev = GENESIS
    for (id_, ts, title, body) in IDR_SPECS:
        rec = {"kind": "idr", "id": id_, "ts": ts, "title": title,
               "body": body, "prev": prev}
        rec["hash"] = leaf_digest("idr", id_, ts, body, prev)
        prev = rec["hash"]
        chain.append(rec)
    for (id_, ts, body) in MEM_SPECS:
        mem = {"kind": "memory", "id": id_, "ts": ts, "body": body, "prev": prev}
        mem["hash"] = leaf_digest("memory", id_, ts, body, prev)
        prev = mem["hash"]
        chain.append(mem)
    return chain

def build_passport(tamper=False):
    chain = build_chain()
    sources = [{"id": s[0], "title": s[1], "text": s[2]} for s in SOURCES]
    citations = [{"id": c[0], "source_id": c[1], "quote": c[2]} for c in CITATIONS]
    mutations = []

    if tamper:
        # MUTATION 1 — edit one record's body without touching its stored hash.
        for e in chain:
            if e["id"] == "idr-003":
                old = e["body"]
                e["body"] = old + " We are extremely confident about this."
                mutations.append(("idr-003 body", old, e["body"]))
        # MUTATION 2 — fabricate one citation quote (near-miss, words dropped).
        for c in citations:
            if c["id"] == "cite-002":
                old = c["quote"]
                c["quote"] = "content-addressed and Merkle-rooted"
                mutations.append(("cite-002 quote", old, c["quote"]))

    hashes = [e["hash"] for e in chain]
    root = merkle_root(hashes)
    passport = {
        "schema": SCHEMA,
        "agent": AGENT,
        "session": SESSION,
        "chain": chain,
        "citations": {"sources": sources, "citations": citations},
        "integrity": {
            "root": root,
            "depth": len(chain),
            "leaves": len(hashes),
            "algorithm": "sha256",
            "canonical_formula": "sha256( kind \\x1f id \\x1f ts \\x1f body \\x1f prev_hash )  [UTF-8, U+001F separators]",
            "root_formula": "pairwise sha256(left || right), odd level duplicates last",
            "citation_rule": "quote must be a verbatim substring of its embedded source",
        },
        "issued": "2026-02-11T09:00:00Z",
        "issuer": "GRASP · Governed Reasoning And Signable Provenance",
        "motto": "Don't trust it — witness it.",
    }
    return passport, mutations

# ----------------------------------------------------------------------------
# Python-side audit (the same arithmetic the browser will run — the transcript
# below IS the verdict the HTML's VERIFY button will render).
# ----------------------------------------------------------------------------
def audit(passport, label):
    chain = passport["chain"]
    n = len(chain)
    lines = []
    lines.append("")
    lines.append("  " + "═" * 72)
    lines.append(f"  SELF-AUDIT  [{label}]")
    lines.append("  " + "═" * 72)
    lines.append(f"  CHAIN: {n} entries ({sum(1 for e in chain if e['kind']=='idr')} IDR"
                 f" + {sum(1 for e in chain if e['kind']=='memory')} MEMORY)"
                 f"  ·  root = {passport['integrity']['algorithm']} Merkle over {n} leaves")
    failures = []
    for i, e in enumerate(chain):
        rec = leaf_digest(e["kind"], e["id"], e["ts"], e["body"], e["prev"])
        content_ok = rec == e["hash"]
        if i == 0:
            link_ok = e["prev"] == GENESIS
        else:
            link_ok = e["prev"] == chain[i - 1]["hash"] and \
                      leaf_digest(chain[i-1]["kind"], chain[i-1]["id"], chain[i-1]["ts"],
                                  chain[i-1]["body"], chain[i-1]["prev"]) == chain[i-1]["hash"]
        c = "OK " if content_ok else "FAIL"
        l = "OK " if link_ok else "FAIL"
        ref = e["prev"][:10] + "…" if e["prev"] != GENESIS else "GENESIS"
        lines.append(f"   [{i+1:02d}] {e['id']:<8} content[{c}] link[{l}]  ← {ref}  {e['body'][:52].strip()}")
        if not content_ok:
            failures.append(f"content address of {e['id']} (stored {e['hash'][:16]}… ≠ recomputed {rec[:16]}…)")
        if not link_ok:
            failures.append(f"chain link into {e['id']} (prev {e['prev'][:16]}… does not match the record before it)")
    rec_root = merkle_root([leaf_digest(e["kind"], e["id"], e["ts"], e["body"], e["prev"])
                            for e in chain])
    root_ok = rec_root == passport["integrity"]["root"]
    lines.append(f"  ROOT  stored      {passport['integrity']['root']}")
    lines.append(f"  ROOT  recomputed  {rec_root}")
    lines.append(f"  ROOT  {('MATCH OK' if root_ok else 'MISMATCH FAIL')}")
    if not root_ok:
        failures.append(f"merkle root (stored {passport['integrity']['root'][:16]}… ≠ recomputed {rec_root[:16]}…)")

    src_map = {s["id"]: s["text"] for s in passport["citations"]["sources"]}
    ok_cites = 0
    for c in passport["citations"]["citations"]:
        hit = c["quote"] in src_map.get(c["source_id"], "")
        ok_cites += 1 if hit else 0
        status = "verified " if hit else "not_found"
        lines.append(f"  CITE {c['id']} [{status}] {c['quote'][:56].strip()}…")
        if not hit:
            failures.append(f"citation {c['id']} ({c['quote'][:40]}…) is NOT verbatim in source {c['source_id']}")
    lines.append(f"  CITATIONS: {ok_cites}/{len(passport['citations']['citations'])} verified (verbatim substring)")
    if failures:
        lines.append(f"  VERDICT: FAIL — {len(failures)} integrity failure(s):")
        for f in failures:
            lines.append(f"     ✗ {f}")
    else:
        lines.append("  VERDICT: PASS — every content address, chain link, the root, and every citation verify.")
    lines.append("  " + "═" * 72)
    lines.append("")
    return "\n".join(lines)

# ----------------------------------------------------------------------------
# HTML template. The embedded core (sha256Hex/leafDigest/merkleRootHex/
# verifyChain/verifyCitations) is the SAME arithmetic as the Python above.
# The page renders the passport, then VERIFY recomputes everything live.
# ----------------------------------------------------------------------------
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HAPPIverse Passport</title>
<style>
  :root{
    --navy:#0b1e3a; --navy2:#12294d; --gold:#c9a227; --gold2:#e8c96a;
    --paper:#f4efe3; --ink:#1c2b3a; --mut:#6b7686;
    --green:#1f9d55; --greenbg:#e6f4ea; --red:#d64545; --redbg:#fbe9e9;
    --line:#e3dbc8; --card:#fffdf7;
  }
  *{box-sizing:border-box; margin:0; padding:0;}
  body{
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:
      radial-gradient(1100px 500px at 15% -10%, rgba(201,162,39,.14), transparent 60%),
      radial-gradient(900px 480px at 90% 110%, rgba(46,99,168,.22), transparent 60%),
      linear-gradient(160deg,#0a1628 0%,#10243f 55%,#0a1628 100%);
    color:var(--ink); min-height:100vh; padding:36px 16px 60px;
  }
  .stage{max-width:880px; margin:0 auto;}
  .brandline{text-align:center; color:#8fa3c4; letter-spacing:.35em; font-size:11px;
    text-transform:uppercase; margin-bottom:14px; font-weight:600;}
  .passport{
    background:var(--paper); border-radius:22px; overflow:hidden;
    box-shadow:0 30px 80px rgba(0,0,0,.55), 0 2px 0 rgba(255,255,255,.06) inset;
    position:relative;
  }
  /* holographic security thread */
  .thread{position:absolute; top:0; right:26px; bottom:0; width:14px;
    background:conic-gradient(from 210deg,#ffd76e,#ff9d5c,#e86ad4,#6eb1ff,#7dffb0,#ffd76e);
    opacity:.75; filter:blur(.2px); mix-blend-mode:soft-light;}
  .thread::after{content:"HAPPIVERSE HAPPIVERSE HAPPIVERSE"; position:absolute; top:30%;
    left:50%; transform:translateX(-50%) rotate(90deg); white-space:nowrap;
    font-size:8px; letter-spacing:.4em; color:#fff; opacity:.5;}

  /* cover */
  .cover{background:linear-gradient(120deg,var(--navy) 0%,var(--navy2) 70%,#16345e 100%);
    color:#f0e6c8; padding:26px 34px 22px; position:relative; overflow:hidden;}
  .cover::after{content:""; position:absolute; inset:0;
    background:repeating-linear-gradient(90deg,transparent 0 42px,rgba(255,255,255,.025) 42px 43px);}
  .cover .toprow{display:flex; align-items:center; gap:16px;}
  .emblem{width:54px; height:54px; flex:none;}
  .covertitle{font-family:Georgia,"Times New Roman",serif; font-size:26px; font-weight:700;
    letter-spacing:.16em; text-transform:uppercase;
    background:linear-gradient(180deg,#f6e7ac,#c9a227 55%,#8a6d14);
    -webkit-background-clip:text; background-clip:text; color:transparent;}
  .coversub{font-size:10.5px; letter-spacing:.3em; text-transform:uppercase;
    color:#9fb4d8; margin-top:3px;}
  .covermeta{display:flex; justify-content:space-between; align-items:flex-end;
    margin-top:18px; font-size:11px; color:#b9c8e4; position:relative;}
  .docnum{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.08em;
    color:#e8c96a;}

  .body{padding:22px 34px 26px; position:relative;}

  /* identity row */
  .identity{display:flex; gap:18px; align-items:center; padding-bottom:18px;
    border-bottom:1px dashed var(--line);}
  .avatar{flex:none;}
  .idinfo{flex:1; min-width:0;}
  .idinfo .who{font-family:Georgia,serif; font-size:19px; font-weight:700; color:var(--navy);}
  .idinfo .what{font-size:12.5px; color:var(--mut); margin-top:2px;}
  .idtable{display:grid; grid-template-columns:repeat(3,auto) 1fr; gap:4px 14px;
    font-size:11.5px; margin-top:10px; color:#4a5568;}
  .idtable b{color:var(--navy); font-weight:600; letter-spacing:.04em;}

  /* integrity bar */
  .integrity{display:flex; align-items:center; gap:14px; flex-wrap:wrap;
    padding:14px 0; border-bottom:1px dashed var(--line);}
  .rootbox{flex:1; min-width:220px;}
  .rootbox .lbl{font-size:10px; letter-spacing:.28em; text-transform:uppercase;
    color:var(--mut); font-weight:700;}
  .rootbox .val{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12.5px;
    color:var(--navy); word-break:break-all; margin-top:3px;}
  .rootbox .sub{font-size:10.5px; color:var(--mut); margin-top:2px;}
  .verifybtn{
    appearance:none; border:0; cursor:pointer; border-radius:999px;
    background:linear-gradient(180deg,#e8c96a,#c9a227 60%,#a8871c);
    color:#0b1e3a; font-weight:800; font-size:13px; letter-spacing:.18em;
    text-transform:uppercase; padding:13px 22px;
    box-shadow:0 6px 16px rgba(201,162,39,.35), 0 1px 0 rgba(255,255,255,.5) inset;
    transition:transform .12s ease, box-shadow .12s ease;
  }
  .verifybtn:hover{transform:translateY(-1px); box-shadow:0 9px 20px rgba(201,162,39,.45);}
  .verifybtn:active{transform:translateY(1px);}
  .verifybtn.busy{opacity:.7; pointer-events:none;}

  /* verdict */
  .verdict{display:none; margin-top:14px; border-radius:14px; padding:14px 18px;
    font-size:13.5px; line-height:1.5;}
  .verdict.pass{display:block; background:var(--greenbg); border:1px solid #bfe3cc; color:#14532d;}
  .verdict.fail{display:block; background:var(--redbg); border:1px solid #f2c4c4; color:#7f1d1d;}
  .verdict .big{font-weight:800; font-size:15px; letter-spacing:.02em;}
  .verdict ul{margin:8px 0 0 18px;}
  .verdict li{margin:2px 0;}
  .verdict .mono{font-family:ui-monospace,Menlo,monospace; font-size:11.5px;}

  /* sections */
  .sec{margin-top:22px;}
  .sec h3{font-size:11px; letter-spacing:.32em; text-transform:uppercase;
    color:var(--mut); display:flex; align-items:center; gap:10px; margin-bottom:10px;}
  .sec h3::after{content:""; flex:1; height:1px; background:var(--line);}

  .entry{background:var(--card); border:1px solid var(--line); border-left:4px solid var(--navy);
    border-radius:12px; padding:12px 16px; margin-bottom:10px;
    box-shadow:0 2px 6px rgba(28,43,58,.05);}
  .entry.memory{border-left-color:#8b5cf6;}
  .entry .row1{display:flex; align-items:baseline; gap:10px; flex-wrap:wrap;}
  .entry .idx{font-family:ui-monospace,Menlo,monospace; font-size:11px; color:#9aa3b0;}
  .entry .chip{font-size:9px; font-weight:800; letter-spacing:.16em; text-transform:uppercase;
    padding:2px 8px; border-radius:999px;}
  .chip.idr{background:#e3ebf6; color:#1d4ed8;}
  .chip.memory{background:#f1eafd; color:#7c3aed;}
  .entry .ts{font-size:10.5px; color:var(--mut); font-family:ui-monospace,Menlo,monospace;}
  .entry .title{font-family:Georgia,serif; font-size:14.5px; font-weight:700; color:var(--navy);}
  .entry.memory .title{color:#6d28d9;}
  .entry .bodytext{font-size:12.8px; color:#3c4a5a; margin-top:5px; line-height:1.5;}
  .entry .row2{display:flex; align-items:center; gap:12px; margin-top:9px; flex-wrap:wrap;}
  .dot{display:inline-flex; align-items:center; gap:5px; font-size:10.5px; font-weight:700;
    letter-spacing:.05em; padding:3px 9px; border-radius:999px;}
  .dot .led{width:8px; height:8px; border-radius:50%; display:inline-block;}
  .dot.ok{background:var(--greenbg); color:#14532d;}
  .dot.ok .led{background:var(--green); box-shadow:0 0 6px rgba(31,157,85,.7);}
  .dot.bad{background:var(--redbg); color:#7f1d1d;}
  .dot.bad .led{background:var(--red); box-shadow:0 0 6px rgba(214,69,69,.7);}
  .entry .pref{font-family:ui-monospace,Menlo,monospace; font-size:10.5px; color:var(--mut);}
  details.hashes{margin-top:8px; font-size:11px; color:#5b6675;}
  details.hashes summary{cursor:pointer; color:var(--mut); letter-spacing:.06em; font-size:10.5px;}
  details.hashes .mono{font-family:ui-monospace,Menlo,monospace; word-break:break-all;
    background:#f3efe3; border:1px solid var(--line); border-radius:8px; padding:8px 10px; margin-top:6px;}
  details.hashes .mono .bad{color:var(--red); font-weight:700;}

  .cite{background:var(--card); border:1px solid var(--line); border-radius:12px;
    padding:12px 16px; margin-bottom:10px;}
  .cite .quote{font-family:Georgia,serif; font-size:13.5px; font-style:italic; color:var(--ink);}
  .cite .src{font-size:11px; color:var(--mut); margin-top:4px;}

  .footer{margin-top:24px; padding-top:14px; border-top:1px dashed var(--line);
    font-size:10.8px; color:var(--mut); line-height:1.7;}
  .footer .mono{font-family:ui-monospace,Menlo,monospace; font-size:10.5px; word-break:break-all;}
  .motto{font-family:Georgia,serif; font-style:italic; color:var(--navy); font-size:13px;
    margin-top:8px;}

  /* stamp animation */
  @keyframes stampin{0%{transform:scale(2.2) rotate(-14deg); opacity:0;}
    60%{transform:scale(.94) rotate(-7deg); opacity:1;}
    100%{transform:scale(1) rotate(-7deg); opacity:1;}}
  .stamp{display:inline-block; border:3px solid currentColor; border-radius:10px;
    padding:3px 12px; font-weight:900; letter-spacing:.2em; font-size:12px;
    animation:stampin .45s cubic-bezier(.2,.9,.3,1.2) both;}
  .verdict.pass .stamp{color:var(--green);}
  .verdict.fail .stamp{color:var(--red);}
  @media (max-width:640px){ .cover{padding:20px 20px 18px;} .body{padding:18px 20px 22px;}
    .covertitle{font-size:20px;} .idtable{grid-template-columns:1fr 1fr;} }
</style>
</head>
<body>
<main class="stage">
  <div class="brandline">GRASP · Governed Reasoning And Signable Provenance</div>
  <section class="passport">
    <div class="thread"></div>

    <header class="cover">
      <div class="toprow">
        <svg class="emblem" viewBox="0 0 64 64" aria-hidden="true">
          <defs>
            <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#f6e7ac"/><stop offset="1" stop-color="#a8871c"/>
            </linearGradient>
          </defs>
          <polygon points="32,3 58,17 58,38 32,61 6,38 6,17" fill="none"
                   stroke="url(#g)" stroke-width="2.5"/>
          <polygon points="32,11 51,21 51,37 32,53 13,37 13,21" fill="url(#g)" opacity=".14"/>
          <text x="32" y="40" text-anchor="middle" font-family="Georgia,serif" font-size="28"
                font-weight="bold" fill="url(#g)">G</text>
        </svg>
        <div>
          <div class="covertitle">HAPPIverse</div>
          <div class="coversub">Passport · the AI&rsquo;s papers</div>
        </div>
      </div>
      <div class="covermeta">
        <div id="cover-session">session —</div>
        <div class="docnum" id="cover-docnum">doc —</div>
      </div>
    </header>

    <div class="body">
      <div class="identity">
        <svg class="avatar" id="avatar" width="64" height="64" aria-hidden="true"></svg>
        <div class="idinfo">
          <div class="who" id="who">—</div>
          <div class="what" id="what">—</div>
          <div class="idtable" id="idtable"></div>
        </div>
      </div>

      <div class="integrity">
        <div class="rootbox">
          <div class="lbl">Merkle root · sha256</div>
          <div class="val" id="rootval">—</div>
          <div class="sub" id="rootsub">—</div>
        </div>
        <button class="verifybtn" id="verifybtn" type="button">Live Verify</button>
      </div>

      <div class="verdict" id="verdict"></div>

      <div id="sections"></div>

      <div class="footer">
        <div><b>Canonical leaf:</b> <span class="mono" id="formula">—</span></div>
        <div><b>Root:</b> <span class="mono">pairwise sha256(left‖right)</span> over every leaf;
          odd level duplicates its last hash.</div>
        <div><b>Citations:</b> <span class="mono">quote ⊂ source text</span> — verbatim substring,
          arithmetic not judgement. A fabricated quote renders <b style="color:var(--red)">NOT_FOUND</b> and cannot pass.</div>
        <div><b>This page verifies itself.</b> No server, no install, no trust: the sha256 below is
          implemented in this file&rsquo;s own JavaScript and run on every VERIFY click. Recompute any leaf
          with <span class="mono">printf '%s' '&lt;canonical string&gt;' | shasum -a 256</span> and compare.</div>
        <div class="motto" id="motto">—</div>
      </div>
    </div>
  </section>
</main>

<script type="application/json" id="passport-data">__PASSPORT_DATA__</script>

<script id="core">
/*PASSPORT_CORE_START*/
"use strict";
function sha256Hex(msg){
  var K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
         0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
         0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
         0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
         0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
         0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
         0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
         0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  var H=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
  function rotr(x,n){return (x>>>n)|(x<<(32-n));}
  function utf8(str){
    var out=[];
    for(var i=0;i<str.length;i++){
      var c=str.charCodeAt(i);
      if(c<0x80){out.push(c);}
      else if(c<0x800){out.push(0xC0|(c>>6),0x80|(c&0x3F));}
      else if(c>=0xD800&&c<=0xDBFF&&i+1<str.length){
        var lo=str.charCodeAt(i+1);
        if(lo>=0xDC00&&lo<=0xDFFF){
          var cp=0x10000+((c-0xD800)<<10)+(lo-0xDC00);
          out.push(0xF0|(cp>>18),0x80|((cp>>12)&0x3F),0x80|((cp>>6)&0x3F),0x80|(cp&0x3F));
          i++; continue;
        }
        out.push(0xEF,0xBF,0xBD);
      }else if(c>=0xDC00&&c<=0xDFFF){out.push(0xEF,0xBF,0xBD);}
      else{out.push(0xE0|(c>>12),0x80|((c>>6)&0x3F),0x80|(c&0x3F));}
    }
    return out;
  }
  var bytes=utf8(msg);
  var bitLen=bytes.length*8;
  bytes.push(0x80);
  while(bytes.length%64!==56)bytes.push(0x00);
  bytes.push(0,0,0,0,(bitLen>>>24)&0xff,(bitLen>>>16)&0xff,(bitLen>>>8)&0xff,bitLen&0xff);
  var w=new Array(64), i, t;
  for(i=0;i<bytes.length;i+=64){
    for(t=0;t<16;t++){
      w[t]=(bytes[i+t*4]<<24)|(bytes[i+t*4+1]<<16)|(bytes[i+t*4+2]<<8)|bytes[i+t*4+3];
    }
    for(t=16;t<64;t++){
      var s0=rotr(w[t-15],7)^rotr(w[t-15],18)^(w[t-15]>>>3);
      var s1=rotr(w[t-2],17)^rotr(w[t-2],19)^(w[t-2]>>>10);
      w[t]=(w[t-16]+s0+w[t-7]+s1)|0;
    }
    var a=H[0],b=H[1],c=H[2],d=H[3],e=H[4],f=H[5],g=H[6],h=H[7];
    for(t=0;t<64;t++){
      var S1=rotr(e,6)^rotr(e,11)^rotr(e,25);
      var ch=(e&f)^(~e&g);
      var temp1=(h+S1+ch+K[t]+w[t])|0;
      var S0=rotr(a,2)^rotr(a,13)^rotr(a,22);
      var maj=(a&b)^(a&c)^(b&c);
      var temp2=(S0+maj)|0;
      h=g; g=f; f=e; e=(d+temp1)|0; d=c; c=b; b=a; a=(temp1+temp2)|0;
    }
    H[0]=(H[0]+a)|0; H[1]=(H[1]+b)|0; H[2]=(H[2]+c)|0; H[3]=(H[3]+d)|0;
    H[4]=(H[4]+e)|0; H[5]=(H[5]+f)|0; H[6]=(H[6]+g)|0; H[7]=(H[7]+h)|0;
  }
  var out="";
  for(i=0;i<8;i++){var x=H[i]>>>0,s=x.toString(16); while(s.length<8)s="0"+s; out+=s;}
  return out;
}
function leafDigest(kind,id,ts,body,prev){
  return sha256Hex([kind,id,ts,body,prev].join("\x1f"));
}
function merkleRootHex(hashes){
  var level=hashes.slice();
  if(level.length===0)return "0".repeat(64);
  while(level.length>1){
    if(level.length%2===1)level.push(level[level.length-1]);
    var next=[];
    for(var i=0;i<level.length;i+=2)next.push(sha256Hex(level[i]+level[i+1]));
    level=next;
  }
  return level[0];
}
function verifyChain(chain){
  var rec=chain.map(function(e){return leafDigest(e.kind,e.id,e.ts,e.body,e.prev);});
  var per=chain.map(function(e,i){
    return {
      id:e.id, kind:e.kind, ts:e.ts, body:e.body, title:e.title||"",
      prev:e.prev, stored:e.hash, recomputed:rec[i],
      contentOk:rec[i]===e.hash,
      linkOk: i===0 ? e.prev==="GENESIS"
                    : (e.prev===chain[i-1].hash && rec[i-1]===chain[i-1].hash)
    };
  });
  return {
    per:per,
    allContent:per.every(function(p){return p.contentOk;}),
    allLinks:per.every(function(p){return p.linkOk;}),
    recomputedRoot:merkleRootHex(rec)
  };
}
function verifyCitations(data){
  var map={};
  data.citations.sources.forEach(function(s){map[s.id]=s.text;});
  return data.citations.citations.map(function(c){
    var text=map[c.source_id]||"";
    return {id:c.id,source_id:c.source_id,quote:c.quote,ok:text.indexOf(c.quote)!==-1};
  });
}
function verifyPassport(data){
  var chain=verifyChain(data.chain);
  var cites=verifyCitations(data);
  var rootOk=chain.recomputedRoot===data.integrity.root;
  var failures=[];
  chain.per.forEach(function(p){
    if(!p.contentOk)failures.push("content address of "+p.id+" (stored "+p.stored.slice(0,16)+"… ≠ recomputed "+p.recomputed.slice(0,16)+"…)");
    if(!p.linkOk)failures.push("chain link into "+p.id+" (prev "+p.prev.slice(0,16)+"… does not match the authentic record before it)");
  });
  if(!rootOk)failures.push("merkle root (stored "+data.integrity.root.slice(0,16)+"… ≠ recomputed "+chain.recomputedRoot.slice(0,16)+"…)");
  cites.forEach(function(c){
    if(!c.ok)failures.push("citation "+c.id+" (“"+c.quote+"”) is NOT verbatim in source "+c.source_id);
  });
  return {
    chain:chain, cites:cites, rootOk:rootOk, failures:failures,
    pass:chain.allContent&&chain.allLinks&&rootOk&&cites.every(function(c){return c.ok;})
  };
}
/*PASSPORT_CORE_END*/
</script>

<script id="ui">
"use strict";
var DATA=JSON.parse(document.getElementById("passport-data").textContent);

function el(html){var d=document.createElement("template"); d.innerHTML=html.trim(); return d.content.firstChild;}
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function hueOf(str){var h=0; for(var i=0;i<str.length;i++){h=(h*31+str.charCodeAt(i))>>>0;} return h%360;}

function renderIdentity(){
  document.getElementById("who").textContent=DATA.agent.name;
  document.getElementById("what").textContent=DATA.session.purpose;
  document.getElementById("cover-session").textContent="session "+DATA.session.id+" · "+DATA.session.started;
  document.getElementById("motto").textContent="“"+DATA.motto+"”";
  document.title="HAPPIverse Passport — "+DATA.agent.name;
  var hue=hueOf(DATA.agent.id);
  var av=document.getElementById("avatar");
  var initials=DATA.agent.name.replace(/[^A-Za-z0-9 ]/g,"").split(" ").filter(Boolean)
    .map(function(w){return w[0].toUpperCase();}).slice(0,2).join("");
  av.innerHTML='<rect width="64" height="64" rx="14" fill="hsl('+hue+',42%,26%)"/>'
    +'<circle cx="32" cy="24" r="11" fill="hsl('+hue+',70%,72%)"/>'
    +'<path d="M14 56c0-10 8-16 18-16s18 6 18 16" fill="hsl('+hue+',70%,72%)"/>'
    +'<text x="32" y="12" text-anchor="middle" font-family="ui-monospace,Menlo,monospace" '
    +'font-size="10" fill="rgba(255,255,255,.55)">'+esc(DATA.agent.id)+'</text>';
  document.getElementById("idtable").innerHTML=
      '<b>MODEL</b><span>'+esc(DATA.agent.model)+'</span>'
    + '<b>ISSUED</b><span>'+esc(DATA.issued)+'</span>'
    + '<b>SCHEMA</b><span>'+esc(DATA.schema)+'</span>'
    + '<b>ISSUER</b><span>'+esc(DATA.issuer)+'</span>';
  var root=DATA.integrity.root;
  document.getElementById("rootval").textContent=root;
  document.getElementById("rootsub").textContent=DATA.integrity.depth+" chain entries · "
    +DATA.integrity.leaves+" merkle leaves · "+DATA.integrity.algorithm.toUpperCase();
  document.getElementById("cover-docnum").textContent="DOC HPP-"+root.slice(0,8).toUpperCase();
  document.getElementById("formula").textContent=DATA.integrity.canonical_formula;
}

function renderSections(){
  var wrap=document.getElementById("sections");
  var idrs=DATA.chain.filter(function(e){return e.kind==="idr";});
  var mems=DATA.chain.filter(function(e){return e.kind==="memory";});
  var html="";
  html+='<div class="sec"><h3>Decisions — signed decision records ('+idrs.length+')</h3>'
    +idrs.map(entryCard).join("")+'</div>';
  html+='<div class="sec"><h3>Beliefs — memory chain links ('+mems.length+')</h3>'
    +mems.map(entryCard).join("")+'</div>';
  html+='<div class="sec"><h3>Claims — cited, verbatim-verified ('+DATA.citations.citations.length+')</h3>'
    +DATA.citations.citations.map(function(c){
        var src=DATA.citations.sources.filter(function(s){return s.id===c.source_id;})[0];
        return '<div class="cite"><div class="quote">“'+esc(c.quote)+'”</div>'
          +'<div class="src">— '+esc(src.title)+' · <span class="chip idr">cite.verify</span>'
          +' <span class="dot" data-cite="'+esc(c.id)+'"><span class="led"></span>…</span></div></div>';
      }).join("")+'</div>';
  html+='<div class="sec"><h3>Raw document (edit me — then hit Live Verify)</h3>'
    +'<details class="hashes"><summary>show embedded JSON</summary>'
    +'<div class="mono">'+esc(JSON.stringify(DATA,null,1))+'</div></details></div>';
  wrap.innerHTML=html;
}

function entryCard(e){
  var idx=DATA.chain.indexOf(e)+1;
  var chip=e.kind==="idr"?"idr":"memory";
  var title=e.kind==="idr"?e.title:e.body.split(".")[0];
  var body=e.kind==="idr"?e.body:e.body;
  var kindLbl=e.kind==="idr"?"decision":"belief";
  return '<div class="entry '+(e.kind==="memory"?"memory":"")+'" data-entry="'+esc(e.id)+'">'
    +'<div class="row1"><span class="idx">'+String(idx).padStart(2,"0")+'</span>'
    +'<span class="chip '+chip+'">'+kindLbl+'</span>'
    +'<span class="title">'+esc(title)+'</span>'
    +'<span class="ts">'+esc(e.ts)+'</span></div>'
    +'<div class="bodytext">'+esc(body)+'</div>'
    +'<div class="row2">'
    +'<span class="dot" data-content="'+esc(e.id)+'"><span class="led"></span>content …</span>'
    +'<span class="dot" data-link="'+esc(e.id)+'"><span class="led"></span>link …</span>'
    +'<span class="pref">← '+esc(e.prev==="GENESIS"?"GENESIS":e.prev.slice(0,16)+"…")+'</span></div>'
    +'<details class="hashes"><summary>content address · recompute</summary>'
    +'<div class="mono">canonical: sha256( '+esc(e.kind)+' \\x1f '+esc(e.id)+' \\x1f '+esc(e.ts)+' \\x1f '+esc(e.body)+' \\x1f '+esc(e.prev)+' )'
    +'<br>stored: <span data-stored="'+esc(e.id)+'">'+esc(e.hash)+'</span></div></details>'
    +'</div>';
}

function runVerify(){
  var btn=document.getElementById("verifybtn");
  btn.classList.add("busy");
  btn.textContent="Verifying…";
  setTimeout(function(){
    var v=verifyPassport(DATA);
    // entry dots
    v.chain.per.forEach(function(p){
      setDot('[data-content="'+p.id+'"]', p.contentOk, p.contentOk?"content ✓":"content ✗");
      setDot('[data-link="'+p.id+'"]', p.linkOk, p.linkOk?"link ✓":"link ✗");
      var stored=document.querySelector('[data-stored="'+p.id+'"]');
      if(stored) stored.textContent=p.stored+(p.contentOk?"":"  ← recomputes to "+p.recomputed);
    });
    v.cites.forEach(function(c){
      setDot('[data-cite="'+c.id+'"]', c.ok, c.ok?"VERIFIED":"NOT_FOUND");
    });
    var vd=document.getElementById("verdict");
    if(v.pass){
      vd.className="verdict pass";
      vd.innerHTML='<span class="stamp">VERIFIED</span>'
        +' <span class="big">Self-audit passed — this passport proves itself.</span><br>'
        +'All '+DATA.chain.length+' content addresses, all '+DATA.chain.length+' chain links, '
        +'the Merkle root, and all '+v.cites.length+' citations verify. '
        +'<span class="mono">root ✓ '+DATA.integrity.root.slice(0,16)+'…</span>';
    }else{
      vd.className="verdict fail";
      vd.innerHTML='<span class="stamp">ALTERED</span>'
        +' <span class="big">Self-audit failed — '+v.failures.length+' integrity failure(s). This document has been changed.</span>'
        +'<ul>'+v.failures.map(function(f){return "<li>"+esc(f)+"</li>";}).join("")+'</ul>';
    }
    btn.classList.remove("busy");
    btn.textContent="Live Verify";
  }, 320);
}
function setDot(sel,ok,label){
  var node=document.querySelector(sel);
  if(!node)return;
  node.className="dot "+(ok?"ok":"bad");
  node.innerHTML='<span class="led"></span>'+label;
}

renderIdentity();
renderSections();
document.getElementById("verifybtn").addEventListener("click",runVerify);
document.addEventListener("keydown",function(ev){if(ev.key==="v"||ev.key==="V")runVerify();});
window.addEventListener("DOMContentLoaded",function(){setTimeout(runVerify,450);});
</script>
</body>
</html>
"""

def emit_html(passport, out_path):
    data_json = json.dumps(passport, indent=1, ensure_ascii=False)
    data_json = data_json.replace("</", "<\\/")   # safe inside <script>
    html = HTML_TEMPLATE.replace("__PASSPORT_DATA__", data_json)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Generate a HAPPIverse Passport (single self-auditing HTML file).")
    ap.add_argument("--tamper", action="store_true",
                    help="mutate one record body + fabricate one citation, then emit the altered passport")
    ap.add_argument("--out", default=None, help="output HTML path (default: passport.html / passport_tampered.html)")
    args = ap.parse_args()

    passport, mutations = build_passport(tamper=args.tamper)
    out = args.out or ("passport_tampered.html" if args.tamper else "passport.html")
    label = "TAMPERED — altered document" if args.tamper else "CLEAN — issued document"

    banner = []
    banner.append("HAPPIverse Passport generator")
    banner.append("=" * 74)
    banner.append(f"  agent      {passport['agent']['name']}  ({passport['agent']['id']})")
    banner.append(f"  session    {passport['session']['id']} · {passport['session']['started']}")
    banner.append(f"  chain      {len(passport['chain'])} entries"
                  f" ({sum(1 for e in passport['chain'] if e['kind']=='idr')} IDR +"
                  f" {sum(1 for e in passport['chain'] if e['kind']=='memory')} memory)")
    banner.append(f"  root       {passport['integrity']['root']}")
    banner.append(f"  citations  {len(passport['citations']['citations'])} claims over"
                  f" {len(passport['citations']['sources'])} embedded sources")
    if mutations:
        banner.append("  MUTATIONS APPLIED (demo 2):")
        for (what, old, new) in mutations:
            banner.append(f"    • {what}:")
            banner.append(f"        before  {old[:88]}{'…' if len(old)>88 else ''}")
            banner.append(f"        after   {new[:88]}{'…' if len(new)>88 else ''}")
    print("\n".join(banner))
    print(audit(passport, label))

    emit_html(passport, out)
    print(f"  wrote {out}  ({len(open(out, encoding='utf-8').read())} bytes) — open in any browser:")
    print(f"    open {out}")
    print("  The HTML's Live Verify button runs the same arithmetic as the audit above,")
    print("  entirely in the page's own JavaScript. The paper audits itself.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
