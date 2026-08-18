# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 CodeTonight SA
"""verify_kit.py — the INCEPTION kit verifies itself.

Reads manifest.json (the content-addressed manifest of every file in the kit),
recomputes every SHA-256, and stamps the kit VERIFIED or BROKEN. Pure stdlib,
no network, no runtime. The kit root is the sha256 of the canonical manifest —
tamper with the manifest or any tool file and the verdict flips.
"""
import hashlib
import json
import sys
from pathlib import Path

KIT_DIR = Path(__file__).resolve().parent
MANIFEST = KIT_DIR / "manifest.json"


def verify_kit() -> dict:
    if not MANIFEST.exists():
        return {"ok": False, "detail": "manifest.json missing — the kit cannot certify itself"}
    raw = MANIFEST.read_text(encoding="utf-8")
    manifest = json.loads(raw)
    if not isinstance(manifest, dict) or manifest.get("kind") != "grasp-inception-manifest":
        return {"ok": False, "detail": "manifest.json is not a grasp-inception-manifest"}
    stored_root = manifest.get("kit_root")
    recomputed_root = "sha256:" + hashlib.sha256(
        json.dumps({k: v for k, v in manifest.items() if k != "kit_root"},
                   sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    entries = manifest.get("entries", [])
    results = []
    for entry in entries:
        path = KIT_DIR / entry["path"]
        if not path.exists():
            results.append({"path": entry["path"], "ok": False, "detail": "missing"})
            continue
        data = path.read_bytes()
        ok = hashlib.sha256(data).hexdigest() == entry["sha256"] and len(data) == entry["size"]
        results.append({"path": entry["path"], "ok": ok,
                        "detail": "match" if ok else "HASH MISMATCH — file altered"})
    ok = recomputed_root == stored_root and all(r["ok"] for r in results)
    return {
        "ok": ok,
        "kit_root": stored_root,
        "root_matches": recomputed_root == stored_root,
        "tools": manifest.get("tool_count"),
        "files_checked": len(results),
        "files_broken": sum(1 for r in results if not r["ok"]),
        "broken": [r for r in results if not r["ok"]],
        "thesis": manifest.get("thesis"),
    }


def main() -> int:
    out = verify_kit()
    if "--json" in sys.argv:
        print(json.dumps(out, sort_keys=True))
        return 0 if out["ok"] else 1
    print("=" * 62)
    print("  INCEPTION KIT — self-verification")
    print("=" * 62)
    print("  thesis       :", out.get("thesis", "?"))
    print("  kit_root     :", out.get("kit_root", "?"))
    print("  root_matches :", out.get("root_matches"))
    print("  files        :", out.get("files_checked"), "checked,",
          out.get("files_broken"), "broken")
    for b in out.get("broken", []):
        print("   BROKEN:", b["path"], "-", b["detail"])
    if out["ok"]:
        print()
        print("  STAMP: VERIFIED — every file and the manifest itself recompute.")
        print("  The kit proves itself. Don't trust it - witness it.")
        return 0
    print()
    print("  STAMP: BROKEN — this kit has been altered.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
