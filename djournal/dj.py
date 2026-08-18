#!/usr/bin/env python3
"""
dj — Decision Journal: prove what you decided.

A personal, append-only journal of consequential decisions. Every entry records
what / why / when / falsification-condition, is content-addressed (sha256), and
is cryptographically sealed into a chain: each record links to the digest of the
one before it, and the seal covers the whole canonical body. A journal cannot
lie about itself — not to its owner, not to a witness.

Sealing — honest about which:
  * ed25519      asymmetric signature, used when the 'cryptography' package is
                 installed (verify.key is public; seal.key stays private)
  * hmac-sha256  pure-stdlib symmetric MAC, the fallback used when cryptography
                 is absent (the same key seals and verifies — a secret shared
                 with a witness, never a public key)

Zero dependencies beyond the Python standard library.

Commands:
  dj init [--name X] [--path P] [--force-hmac]   create a journal
  dj log "WHAT" [--why W] [--when D] [--falsify F]   seal a decision (append-only)
  dj ls                                            list entries
  dj proof [ID]                                    print a shareable proof line
  dj verify                                        verify the whole journal + receipt card
  dj bundle [--out F]                              export a portable witness bundle
  dj check FILE                                    verify a received bundle
  dj info                                          journal details

Built for the GRIP/GRASP proof-layer family: signed decision records with
signable provenance, "don't trust it — witness it".
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

VERSION = "1.0.0"
GENESIS = "GENESIS"
SEAL_ED25519 = "ed25519"
SEAL_HMAC = "hmac-sha256"

# --- cryptography availability (used only when present) ---------------------
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    HAVE_ED25519 = True
except Exception:  # pragma: no cover - depends on machine
    HAVE_ED25519 = False


# --- small helpers -----------------------------------------------------------
def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def use_color(args):
    return sys.stdout.isatty() and not args.no_color and "NO_COLOR" not in os.environ


def color(s, code, on):
    return f"\x1b[{code}m{s}\x1b[0m" if on else s


def alg_desc(alg):
    if alg == SEAL_ED25519:
        return "ed25519 (asymmetric signature)"
    return "hmac-sha256 (symmetric MAC — stdlib)"


def short_digest(d):
    d = str(d)
    if len(d) <= 12:
        return d
    return d[:7] + d[7:19] + "…" + d[-4:]


# --- crypto primitives --------------------------------------------------------
def make_keys(alg):
    if alg == SEAL_ED25519:
        priv = Ed25519PrivateKey.generate()
        return priv, priv.public_key()
    return secrets.token_bytes(32), None  # hmac: one symmetric key


def seal(alg, key, msg):
    """Return base64 signature/MAC over msg."""
    if alg == SEAL_ED25519:
        return base64.b64encode(key.sign(msg)).decode("ascii")
    return base64.b64encode(hmac.new(key, msg, hashlib.sha256).digest()).decode("ascii")


def unseal_ok(alg, vkey, msg, sig_b64):
    try:
        sig = base64.b64decode(sig_b64)
        if alg == SEAL_ED25519:
            vkey.verify(sig, msg)
            return True
        expected = hmac.new(vkey, msg, hashlib.sha256).digest()
        return hmac.compare_digest(expected, sig)
    except Exception:
        return False


def _require_ed25519():
    if not HAVE_ED25519:
        die("this journal uses ed25519 but the 'cryptography' package is not installed")


def write_keys(jdir, alg, seal_key, verify_key):
    if alg == SEAL_ED25519:
        _require_ed25519()
        priv_pem = seal_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        pub_pem = verify_key.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        _write(jdir / "seal.key", priv_pem, private=True)
        _write(jdir / "verify.key", pub_pem, private=False)
    else:
        b64 = base64.b64encode(seal_key).decode("ascii") + "\n"
        _write(jdir / "seal.key", b64.encode(), private=True)
        _write(jdir / "verify.key", b64.encode(), private=False)


def load_seal_key(jdir, alg):
    raw = (jdir / "seal.key").read_bytes()
    if alg == SEAL_ED25519:
        _require_ed25519()
        return serialization.load_pem_private_key(raw, password=None)
    return base64.b64decode(raw.strip())


def load_verify_key(jdir, alg):
    raw = (jdir / "verify.key").read_bytes()
    if alg == SEAL_ED25519:
        _require_ed25519()
        return serialization.load_pem_public_key(raw)
    return base64.b64decode(raw.strip())


def parse_verify_key(alg, text):
    if alg == SEAL_ED25519:
        _require_ed25519()
        return serialization.load_pem_public_key(text.encode("ascii"))
    return base64.b64decode(text.strip())


def _write(path, data, private=False):
    path.write_bytes(data)
    os.chmod(path, 0o600 if private else 0o644)


# --- journal storage -----------------------------------------------------------
def meta_path(jdir):
    return jdir / "meta.json"


def load_meta(jdir):
    try:
        return json.loads(meta_path(jdir).read_text())
    except FileNotFoundError:
        die(f"no journal at {jdir} — run:  dj init --path {jdir}")
    except json.JSONDecodeError as ex:
        die(f"meta.json at {jdir} is corrupt: {ex}")


def save_meta(jdir, meta):
    _write(meta_path(jdir), (json.dumps(meta, indent=2, sort_keys=True) + "\n").encode())


def load_entries(jdir):
    p = jdir / "journal.jsonl"
    if not p.exists():
        return []
    out = []
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except Exception as ex:
            out.append({"__broken__": True, "__line__": n, "error": str(ex)})
    return out


# --- entry arithmetic -----------------------------------------------------------
def canonical(entry):
    """Deterministic bytes a record seals. 'seal' and 'digest' are derived, never sealed."""
    d = {k: v for k, v in entry.items() if k not in ("seal", "digest")}
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_digest(entry):
    return "sha256:" + hashlib.sha256(canonical(entry)).hexdigest()


# --- verification core -----------------------------------------------------------
def verify_chain(meta, entries, vkey):
    alg = meta["seal_alg"]
    rows = []
    prev_expected = GENESIS
    last_digest = None
    for e in entries:
        if e.get("__broken__"):
            rows.append({"id": f"line {e['__line__']}", "ok": False,
                         "why": f"unparseable line: {e.get('error')}", "digest": None})
            prev_expected = "<unparseable>"
            continue
        ok, why = True, []
        try:
            canon = canonical(e)
            dg = "sha256:" + hashlib.sha256(canon).hexdigest()
        except Exception as ex:
            ok, why, dg = False, [f"cannot canonicalise: {ex}"], None
        if ok:
            if e.get("digest") != dg:
                ok = False
                why.append(f"digest mismatch (content changed: stored {short_digest(e.get('digest'))} ≠ recomputed {short_digest(dg)})")
            if e.get("prev") != prev_expected:
                ok = False
                why.append(f"broken chain link (prev {short_digest(e.get('prev'))} ≠ expected {short_digest(prev_expected)})")
            if not unseal_ok(alg, vkey, canon, e.get("seal", "")):
                ok = False
                why.append("seal invalid")
            last_digest = dg
            prev_expected = dg
        rows.append({"id": e.get("id", "?"), "ok": ok, "why": "; ".join(why), "digest": e.get("digest")})
    head_ok = last_digest is not None and last_digest == meta.get("head")
    links_ok = sum(1 for r in rows if r["ok"])
    return rows, head_ok, links_ok, last_digest


# --- receipt card ---------------------------------------------------------------
def render_card(meta, rows, head_ok, links_ok, use_col):
    W = 66
    G = lambda s: color(s, "32", use_col)
    R = lambda s: color(s, "31", use_col)
    C = lambda s: color(s, "36", use_col)
    B = lambda s: color(s, "1", use_col)

    def pad(s):
        return s + " " * (W - len(s))

    def line(s=""):
        return "│" + pad(s) + "│"

    def rule():
        return "├" + "─" * W + "┤"

    def center(s):
        l = (W - len(s)) // 2
        return "│" + " " * l + s + " " * (W - len(s) - l) + "│"

    ok_all = head_ok and links_ok == len(rows) and len(rows) > 0
    ok_count = links_ok
    out = ["┌" + "─" * W + "┐", center(B(" DECISION JOURNAL · VERIFICATION RECEIPT ")), rule()]
    out.append(line(f"  journal   {C(meta['id'])}"))
    out.append(line(f"  name      {meta.get('name', '')}"))
    out.append(line(f"  seal      {alg_desc(meta['seal_alg'])}"))
    out.append(line(f"  entries   {len(rows)}"))
    out.append(rule())
    for r in rows:
        mark = G("✓") if r["ok"] else R("✗")
        dg = short_digest(r["digest"]) if r.get("digest") else "—"
        out.append(line(f"  {r['id']:<11} {mark}  digest {dg}"))
    out.append(rule())
    chain_word = G("intact") if links_ok == len(rows) else R("BROKEN")
    head_word = G("matches") if head_ok else R("mismatch")
    out.append(line(f"  chain     {links_ok}/{len(rows)} links {chain_word} · head {head_word} meta"))
    out.append(line(f"  seals     {ok_count}/{len(rows)} valid"))
    out.append(line(""))
    if ok_all:
        out.append(line(f"  verdict   {G('✅ VERIFIED — this journal has not lied')}"))
    else:
        out.append(line(f"  verdict   {R('✗ TAMPER DETECTED — the chain does not lie for you')}"))
        first_bad = next((r for r in rows if not r["ok"]), None)
        if first_bad is not None and first_bad["why"]:
            out.append(line(f"  at        {first_bad['id']} · {first_bad['why'][:W - 22]}"))
    out.append("└" + "─" * W + "┘")
    return "\n".join(out)


# --- commands -------------------------------------------------------------------
def cmd_init(a):
    jdir = Path(a.path)
    if jdir.exists() and meta_path(jdir).exists():
        die(f"{jdir} is already a journal — run:  dj verify --path {jdir}")
    jdir.mkdir(parents=True, exist_ok=True)
    alg = SEAL_HMAC if (a.force_hmac or not HAVE_ED25519) else SEAL_ED25519
    seal_key, verify_key = make_keys(alg)
    meta = {
        "v": 1,
        "id": "JRN-" + secrets.token_hex(4).upper(),
        "name": a.name,
        "created": utcnow(),
        "seal_alg": alg,
        "head": None,
        "count": 0,
    }
    write_keys(jdir, alg, seal_key, verify_key)
    save_meta(jdir, meta)
    (jdir / "journal.jsonl").touch()
    print(f"✓ journal created  {meta['id']}  ·  {meta['name']}")
    print(f"  seal      {alg_desc(alg)}")
    print(f"  path      {jdir}")
    print(f"  keys      seal.key (private — never share) · verify.key (public)")
    print()
    print("  next:  dj log 'what I decided' --why '...' --falsify '...'")


def cmd_log(a):
    jdir = Path(a.path)
    meta = load_meta(jdir)
    alg = meta["seal_alg"]
    what = a.what.strip()
    if not what:
        die("what did you decide?  dj log '<decision>' --why '...' --falsify '...'")
    entry = {
        "v": 1,
        "id": "D-%04d" % (meta["count"] + 1),
        "ts": utcnow(),
        "when": a.when or utcnow()[:10],
        "what": what,
        "why": a.why.strip(),
        "falsify": a.falsify.strip(),
        "prev": meta["head"] if meta["head"] else GENESIS,
        "nonce": secrets.token_hex(8),
    }
    canon = canonical(entry)
    entry["digest"] = content_digest(entry)
    entry["seal"] = seal(alg, load_seal_key(jdir, alg), canon)
    with open(jdir / "journal.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    meta["head"] = entry["digest"]
    meta["count"] += 1
    save_meta(jdir, meta)
    print(f"✓ sealed {entry['id']} · {short_digest(entry['digest'])} · {alg_desc(alg)}")
    if not (entry["why"] and entry["falsify"]):
        print("  tip: an unfalsifiable decision is a hope — add --why and --falsify")


def cmd_ls(a):
    jdir = Path(a.path)
    meta = load_meta(jdir)
    entries = load_entries(jdir)
    print(f"{meta['id']} · {meta['name']} · {len(entries)} entries · seal {alg_desc(meta['seal_alg'])}")
    print()
    for e in entries:
        if e.get("__broken__"):
            print(f"  line {e['__line__']:<6}  ✗ unparseable: {e.get('error')}")
            continue
        what = e.get("what", "")[:60]
        print(f"  {e.get('id','?'):<9} {e.get('when',''):<11} {what:<60}  {short_digest(e.get('digest','?'))}")


def cmd_proof(a):
    jdir = Path(a.path)
    meta = load_meta(jdir)
    if not meta["head"]:
        die("journal is empty — log a decision first")
    line = f"DJ-PROOF v1 · journal {meta['id']} · seal {meta['seal_alg']} · head {meta['head']}"
    if a.id:
        entries = [e for e in load_entries(jdir) if not e.get("__broken__")]
        match = [e for e in entries if e.get("id") == a.id]
        if not match:
            die(f"no entry {a.id}")
        line += f" · record {a.id} · digest {match[0]['digest']}"
    print(line)
    print("verify: dj verify --path <journal>   (any holder of the journal)", file=sys.stderr)


def cmd_verify(a):
    jdir = Path(a.path)
    meta = load_meta(jdir)
    entries = load_entries(jdir)
    if not entries:
        die("journal is empty — nothing to verify")
    vkey = load_verify_key(jdir, meta["seal_alg"])
    rows, head_ok, links_ok, _ = verify_chain(meta, entries, vkey)
    print(render_card(meta, rows, head_ok, links_ok, use_color(a)))
    print("(exit 0 = verified · 1 = tampered or broken)", file=sys.stderr)
    sys.exit(0 if (head_ok and links_ok == len(rows)) else 1)


def cmd_bundle(a):
    jdir = Path(a.path)
    meta = load_meta(jdir)
    entries = load_entries(jdir)
    if not entries:
        die("journal is empty — nothing to bundle")
    vkey_raw = (jdir / "verify.key").read_text().strip()
    bundle = {
        "v": 1,
        "journal_id": meta["id"],
        "name": meta.get("name"),
        "seal_alg": meta["seal_alg"],
        "verify_key": vkey_raw,
        "head": meta["head"],
        "entries": entries,
    }
    out = Path(a.out) if a.out else Path(f"{meta['id']}.bundle.json")
    out.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n")
    print(f"✓ bundle written to {out}  ({out.stat().st_size} bytes)")
    print(f"  hand this file to any witness — they run:  dj check {out}")
    print("  (contains verify key + entries + seals only; the sealing key stays home)")


def cmd_check(a):
    p = Path(a.file)
    try:
        bundle = json.loads(p.read_text(encoding="utf-8"))
    except Exception as ex:
        die(f"cannot read bundle {p}: {ex}")
    meta = {
        "id": bundle.get("journal_id", "?"),
        "name": bundle.get("name", ""),
        "seal_alg": bundle.get("seal_alg"),
        "head": bundle.get("head"),
    }
    entries = bundle.get("entries", [])
    if not entries:
        die(f"bundle {p} contains no entries")
    vkey = parse_verify_key(meta["seal_alg"], bundle["verify_key"])
    rows, head_ok, links_ok, _ = verify_chain(meta, entries, vkey)
    print(f"witness-checking bundle {p}")
    print(render_card(meta, rows, head_ok, links_ok, use_color(a)))
    print("(exit 0 = verified · 1 = tampered or broken)", file=sys.stderr)
    sys.exit(0 if (head_ok and links_ok == len(rows)) else 1)


def cmd_info(a):
    jdir = Path(a.path)
    meta = load_meta(jdir)
    entries = load_entries(jdir)
    print(f"journal   {meta['id']}")
    print(f"name      {meta['name']}")
    print(f"created   {meta['created']}")
    print(f"seal      {alg_desc(meta['seal_alg'])}")
    print(f"entries   {meta['count']} recorded (file holds {len(entries)} lines)")
    print(f"head      {meta['head']}")
    print(f"path      {jdir}")
    print(f"keys      seal.key (private) · verify.key (public)")


# --- main ------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="dj",
        description="Decision Journal — prove what you decided. Signed, append-only, "
                    "witness-verifiable decision records (GRASP).",
    )
    ap.add_argument("--path", default=".djournal", help="journal directory (default: ./.djournal)")
    ap.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    ap.add_argument("--version", action="version", version=f"dj {VERSION}")

    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="create a journal")
    p.add_argument("--name", default="Untitled journal")
    p.add_argument("--force-hmac", action="store_true",
                   help="use stdlib hmac-sha256 even if cryptography is installed")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("log", help="seal a decision (append-only)")
    p.add_argument("what", help="the decision — what you decided")
    p.add_argument("--why", default="", help="the reasoning behind it")
    p.add_argument("--when", default=None, help="decision date (default: today)")
    p.add_argument("--falsify", default="", help="the condition that would prove it wrong")
    p.set_defaults(fn=cmd_log)

    sub.add_parser("ls", help="list entries").set_defaults(fn=cmd_ls)

    p = sub.add_parser("proof", help="print a shareable proof line")
    p.add_argument("id", nargs="?", default=None, help="record id (e.g. D-0003)")
    p.set_defaults(fn=cmd_proof)

    sub.add_parser("verify", help="verify the whole journal + receipt card").set_defaults(fn=cmd_verify)

    p = sub.add_parser("bundle", help="export a portable witness bundle")
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_bundle)

    p = sub.add_parser("check", help="verify a received bundle")
    p.add_argument("file")
    p.set_defaults(fn=cmd_check)

    sub.add_parser("info", help="journal details").set_defaults(fn=cmd_info)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
