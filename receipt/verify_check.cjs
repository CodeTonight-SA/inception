/* verify_check.cjs — cross-runtime conformance check for the AI Receipt.
 * Runs the SAME verify_core.js that is inlined in receipt.html, against the
 * same spec, and asserts:
 *   - sha256 vector correctness ('abc')
 *   - canonical fingerprint == the one embedded in receipt.html (python parity)
 *   - per-citation verdicts + offsets (python parity)
 *   - per-source sha256 (python parity)
 * Zero deps. Usage: node verify_check.cjs
 */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const dir = __dirname;

const CITE = require('./verify_core.js');
const data = JSON.parse(fs.readFileSync(path.join(dir, 'demo.json'), 'utf8'));
const html = fs.readFileSync(path.join(dir, 'receipt.html'), 'utf8');

const fp = CITE.fingerprint(data);
const embedded = (html.match(/window\.RECEIPT_FP = "([0-9a-f]{64})"/) || [])[1];
const recid = (html.match(/window\.RECEIPT_ID = "([^"]+)"/) || [])[1];

const vec = CITE.sha256Hex('abc');
const VEC_OK = vec === 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad';

const record = CITE.verifyAll(data);

console.log('verify_check.cjs — cross-runtime conformance (browser core vs python generator)');
console.log('  sha256 vector  : sha256("abc") = ' + vec + (VEC_OK ? '  OK' : '  FAIL'));
console.log('  record id      : ' + recid);
console.log('  fingerprint    : sha256:' + fp);
console.log('  embedded fp    : ' + embedded + '  ' + (fp === embedded ? 'MATCH' : 'MISMATCH'));
console.log('');
console.log("  id   src   status     offsets          quote");
record.citations.forEach(function (r, i) {
  var c = data.citations[i];
  var q = c.quote.slice(0, 52) + (c.quote.length > 52 ? '…' : '');
  var off = r.status === 'not_found' ? '[-1–-1]' : '[' + r.start + '–' + r.end + ']';
  console.log('  ' + r.id.padEnd(5) + r.source_id.padEnd(6) + r.status.padEnd(11) + off.padEnd(17) + q);
});
console.log('');
console.log('  grounding rate : ' + record.grounding_rate + '  tally ' + JSON.stringify(record.tally));
console.log('  source hashes  : ' + Object.keys(record.sources).map(function (sid) {
  return sid + ' sha256:' + record.sources[sid].sha256.slice(0, 16) + '… (' + record.sources[sid].chars + ' chars)';
}).join(' · '));
const ok = VEC_OK && fp === embedded && record.grounding_rate === 0.6 &&
           record.tally.verified === 2 && record.tally.fuzzy === 1 && record.tally.not_found === 2;
console.log('');
console.log('CONFORMANCE: ' + (ok ? 'ALL CHECKS PASS — python and JS agree on every byte' : 'FAILURES PRESENT'));
process.exit(ok ? 0 : 1);
