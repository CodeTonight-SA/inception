#!/usr/bin/env node
/*
 * crosscheck.js — headless replay of the HAPPIverse Passport's own verifier.
 *
 * Reads a generated passport.html, extracts the EXACT core JavaScript and the
 * EXACT embedded JSON that the browser runs, executes them in node, and prints
 * the same verdict the page's "Live Verify" button would render.
 *
 * This is the cross-language determinism check: the stored hashes were computed
 * by Python (hashlib) in the generator; if the page's own JS recomputes them to
 * the identical hex, the browser arithmetic and the Python arithmetic agree
 * byte-for-byte.
 *
 * Usage:  node crosscheck.js <passport.html>
 */
"use strict";
const fs = require("fs");

const file = process.argv[2] || "passport.html";
const html = fs.readFileSync(file, "utf8");

// --- extract embedded data -------------------------------------------------
const mData = html.match(/<script type="application\/json" id="passport-data">([\s\S]*?)<\/script>/);
if (!mData) { console.error("no embedded passport data found in " + file); process.exit(2); }
const DATA = JSON.parse(mData[1]);

// --- extract the shipped core JS (the exact code the browser executes) -----
const mCore = html.match(/\/\*PASSPORT_CORE_START\*\/([\s\S]*?)\/\*PASSPORT_CORE_END\*\//);
if (!mCore) { console.error("no core block found in " + file); process.exit(2); }
const core = new Function(mCore[1] + "; return {sha256Hex, leafDigest, merkleRootHex, verifyChain, verifyCitations, verifyPassport};")();

// --- independent SHA-256 (node crypto) as a third arbiter -------------------
const crypto = require("crypto");
const sh = (s) => crypto.createHash("sha256").update(s, "utf8").digest("hex");

// --- run the page's own verifier -------------------------------------------
const v = core.verifyPassport(DATA);
const chain = v.chain;

let fail = 0, pass = 0;
const line = (ok, txt) => { (ok ? pass++ : fail++); console.log((ok ? "  OK  " : "  FAIL") + "  " + txt); };

console.log("═".repeat(72));
console.log("  CROSSCHECK  [" + file + "]  — shipped JS core vs shipped data, run in node");
console.log("═".repeat(72));
console.log("  " + DATA.agent.name + " · session " + DATA.session.id);
console.log("  chain " + DATA.chain.length + " entries · stored root " + DATA.integrity.root.slice(0, 20) + "…");

chain.per.forEach((p, i) => {
  // third-arbiter: node crypto over the same canonical leaf
  const canonical = [p.kind, p.id, p.ts, p.body, p.prev].join("\x1f");
  const cryptoLeaf = sh(canonical);
  line(p.contentOk, "content " + p.id + "  js=" + p.recomputed.slice(0, 16) + "…  crypto=" + cryptoLeaf.slice(0, 16) + "…  " +
      (p.contentOk && p.recomputed === cryptoLeaf ? "JS == crypto == stored" : "MISMATCH"));
  line(p.linkOk, "link   " + p.id + "  prev→ " + (p.prev === "GENESIS" ? "GENESIS" : p.prev.slice(0, 16) + "…") +
      (p.linkOk ? "" : "  (does not match authentic predecessor)"));
});

// root: page JS recompute vs node crypto over the same merkle leaves
const leafHashes = chain.per.map(p => p.recomputed);
let level = leafHashes.slice();
while (level.length > 1) {
  if (level.length % 2 === 1) level.push(level[level.length - 1]);
  const next = [];
  for (let i = 0; i < level.length; i += 2) next.push(sh(level[i] + level[i + 1]));
  level = next;
}
const cryptoRoot = level[0];
line(v.rootOk && chain.recomputedRoot === cryptoRoot,
     "root   stored " + DATA.integrity.root.slice(0, 16) + "…  js=" + chain.recomputedRoot.slice(0, 16) + "…  crypto=" + cryptoRoot.slice(0, 16) + "…");

v.cites.forEach(c => {
  const src = DATA.citations.sources.find(s => s.id === c.source_id);
  const present = (src ? src.text : "").includes(c.quote);
  line(c.ok && present, "cite   " + c.id + " → " + c.source_id + "  “" + c.quote.slice(0, 44) + "…”  " + (c.ok ? "VERIFIED (verbatim substring)" : "NOT_FOUND"));
});

console.log("─".repeat(72));
if (v.pass && fail === 0) {
  console.log("  VERDICT: PASS — " + pass + "/" + (pass + fail) + " checks. Every content address, chain link,");
  console.log("  the Merkle root, and every citation verify. JS == Python == node:crypto.");
  console.log("  (This is the exact verdict the page's Live Verify button renders.)");
  process.exitCode = 0;
} else {
  console.log("  VERDICT: FAIL — " + fail + " integrity failure(s). This document has been altered:");
  v.failures.forEach(f => console.log("     ✗ " + f));
  console.log("  (This is the exact verdict the page's Live Verify button renders.)");
  process.exitCode = 1;
}
console.log("═".repeat(72));
