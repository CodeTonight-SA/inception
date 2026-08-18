/* verify_core.js - GRASP cite.verify arithmetic, reimplemented in plain JS.
 * Mirrors grasp/cite_verify.py (HAPPI/1.3 cite.verify). Deterministic ladder:
 *   exact substring -> whitespace + typographic-tolerant ("fuzzy") -> not_found.
 * Normalisation is length-preserving, so offsets index the ORIGINAL source.
 * Conservative ES5 so it runs identically in browsers, Node and JXA.
 * SPDX-License-Identifier: AGPL-3.0-only  (mirror of CodeTonight SA reference)
 */
(function (global) {
  'use strict';

  /* ---- typographic fold (length-preserving, mirrors _CV_TYPO) ---- */
  var TYPO = {};
  TYPO[0x2010] = '-'; TYPO[0x2011] = '-'; TYPO[0x2012] = '-'; TYPO[0x2013] = '-';
  TYPO[0x2014] = '-'; TYPO[0x2015] = '-';
  TYPO[0x2018] = "'"; TYPO[0x2019] = "'"; TYPO[0x201B] = "'";
  TYPO[0x201C] = '"'; TYPO[0x201D] = '"'; TYPO[0x201F] = '"';
  TYPO[0x00A0] = ' '; TYPO[0x2007] = ' '; TYPO[0x2009] = ' '; TYPO[0x202F] = ' ';

  function typoFold(s) {
    var out = '', i, c, r;
    for (i = 0; i < s.length; i++) {
      c = s.charCodeAt(i);
      r = TYPO[c];
      out += (r === undefined) ? s.charAt(i) : r;
    }
    return out;
  }

  function escapeRegExp(s) {
    var out = '', i, c;
    for (i = 0; i < s.length; i++) {
      c = s.charAt(i);
      out += ('^$\\.*+?()[]{}|'.indexOf(c) !== -1) ? '\\' + c : c;
    }
    return out;
  }

  /* ---- verify ladder: returns {status, start, end} ---- */
  function verify(quote, sourceText) {
    var q = (quote == null ? '' : String(quote)).trim();
    if (q === '') return { status: 'not_found', start: -1, end: -1 };
    var idx = sourceText.indexOf(q);
    if (idx !== -1) return { status: 'verified', start: idx, end: idx + q.length };
    var toks = typoFold(q).split(/\s+/).filter(function (t) { return t.length > 0; });
    if (toks.length === 0) return { status: 'not_found', start: -1, end: -1 };
    var re = new RegExp(toks.map(escapeRegExp).join('\\s+'));
    var m = re.exec(typoFold(sourceText));
    if (m) return { status: 'fuzzy', start: m.index, end: m.index + m[0].length };
    return { status: 'not_found', start: -1, end: -1 };
  }

  /* ---- canonical JSON: matches python json.dumps(sort_keys=True,
   *      separators=(',',':'), ensure_ascii=True) on str/bool/null/int/array/obj ---- */
  function escStr(s) {
    var j = JSON.stringify(s);
    var out = '', i, c, hex;
    for (i = 0; i < j.length; i++) {
      c = j.charCodeAt(i);
      if (c > 0x7f) {
        hex = c.toString(16);
        while (hex.length < 4) hex = '0' + hex;
        out += '\\u' + hex;
      } else {
        out += j.charAt(i);
      }
    }
    return out;
  }

  function canonical(obj) {
    var t = typeof obj;
    if (obj === null) return 'null';
    if (t === 'string') return escStr(obj);
    if (t === 'boolean') return obj ? 'true' : 'false';
    if (t === 'number') {
      if (isFinite(obj) && Math.floor(obj) === obj) return String(obj);
      return 'null'; /* floats are rejected by the generator; keep parity strict */
    }
    if (Array.isArray(obj)) {
      var a = [], i;
      for (i = 0; i < obj.length; i++) a.push(canonical(obj[i]));
      return '[' + a.join(',') + ']';
    }
    if (t === 'object') {
      var keys = Object.keys(obj).sort();
      var p = [], k;
      for (k = 0; k < keys.length; k++) p.push(escStr(keys[k]) + ':' + canonical(obj[keys[k]]));
      return '{' + p.join(',') + '}';
    }
    return 'null';
  }

  /* ---- sha-256 (pure JS; input: UTF-8 bytes) ---- */
  function utf8Bytes(str) {
    var bytes = [], i, c;
    for (i = 0; i < str.length; i++) {
      c = str.charCodeAt(i);
      if (c < 0x80) bytes.push(c);
      else if (c < 0x800) bytes.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f));
      else if (c >= 0xd800 && c <= 0xdbff && i + 1 < str.length) {
        var c2 = str.charCodeAt(i + 1);
        if (c2 >= 0xdc00 && c2 <= 0xdfff) {
          var cp = 0x10000 + ((c - 0xd800) << 10) + (c2 - 0xdc00);
          bytes.push(0xf0 | (cp >> 18), 0x80 | ((cp >> 12) & 0x3f),
                     0x80 | ((cp >> 6) & 0x3f), 0x80 | (cp & 0x3f));
          i++;
        } else bytes.push(0xef, 0xbf, 0xbd);
      } else if (c >= 0xdc00 && c <= 0xdfff) bytes.push(0xef, 0xbf, 0xbd);
      else bytes.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f));
    }
    return bytes;
  }

  var sha256 = (function () {
    var K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
      0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
      0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
      0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
      0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
      0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
      0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
      0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
    function rotr(x, n) { return (x >>> n) | (x << (32 - n)); }
    return function (bytes) {
      var l = bytes.length;
      var bitlenHi = Math.floor((l * 8) / 0x100000000);
      var bitlenLo = (l * 8) >>> 0;
      var paddedLen = (((l + 9 + 63) >> 6) << 6);
      var buf = new Uint8Array(paddedLen);
      buf.set(bytes);
      buf[l] = 0x80;
      var dv = new DataView(buf.buffer);
      dv.setUint32(paddedLen - 8, bitlenHi);
      dv.setUint32(paddedLen - 4, bitlenLo);
      var h0 = 0x6a09e667, h1 = 0xbb67ae85, h2 = 0x3c6ef372, h3 = 0xa54ff53a,
          h4 = 0x510e527f, h5 = 0x9b05688c, h6 = 0x1f83d9ab, h7 = 0x5be0cd19;
      var w = new Int32Array(64);
      var off, i;
      for (off = 0; off < paddedLen; off += 64) {
        for (i = 0; i < 16; i++) w[i] = dv.getInt32(off + i * 4);
        for (i = 16; i < 64; i++) {
          var s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
          var s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
          w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
        }
        var a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, h = h7;
        for (i = 0; i < 64; i++) {
          var S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
          var ch = (e & f) ^ (~e & g);
          var t1 = (h + S1 + ch + K[i] + w[i]) | 0;
          var S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
          var maj = (a & b) ^ (a & c) ^ (b & c);
          var t2 = (S0 + maj) | 0;
          h = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
        }
        h0 = (h0 + a) | 0; h1 = (h1 + b) | 0; h2 = (h2 + c) | 0; h3 = (h3 + d) | 0;
        h4 = (h4 + e) | 0; h5 = (h5 + f) | 0; h6 = (h6 + g) | 0; h7 = (h7 + h) | 0;
      }
      function hex32(n) { n = n >>> 0; var s = n.toString(16); while (s.length < 8) s = '0' + s; return s; }
      return hex32(h0) + hex32(h1) + hex32(h2) + hex32(h3) +
             hex32(h4) + hex32(h5) + hex32(h6) + hex32(h7);
    };
  })();

  function sha256Hex(str) { return sha256(utf8Bytes(str)); }

  /* ---- provenance record, mirrors cite_verify.process() ---- */
  function verifyAll(data) {
    var sources = data.sources || [];
    var citations = data.citations || [];
    var byId = {}, srcMeta = {}, i;
    for (i = 0; i < sources.length; i++) {
      byId[sources[i].id] = sources[i].text;
      srcMeta[sources[i].id] = { sha256: sha256Hex(sources[i].text), chars: sources[i].text.length };
    }
    var tally = { verified: 0, fuzzy: 0, not_found: 0 };
    var results = [], j;
    for (j = 0; j < citations.length; j++) {
      var c = citations[j];
      var src = byId[c.source_id];
      var v = (src === undefined)
        ? { status: 'not_found', start: -1, end: -1 }
        : verify(c.quote, src);
      tally[v.status] = (tally[v.status] || 0) + 1;
      results.push({ id: c.id, source_id: c.source_id, status: v.status, start: v.start, end: v.end });
    }
    var grounded = tally.verified + tally.fuzzy;
    var g = Math.round((grounded / Math.max(citations.length, 1)) * 1000) / 1000;
    return { sources: srcMeta, citations: results, tally: tally, grounding_rate: g };
  }

  function fingerprint(data) { return sha256Hex(canonical(data)); }

  var CITE = {
    typoFold: typoFold,
    verify: verify,
    canonical: canonical,
    sha256Hex: sha256Hex,
    utf8Bytes: utf8Bytes,
    verifyAll: verifyAll,
    fingerprint: fingerprint,
    LADDER: 'exact substring -> whitespace+typographic-tolerant ("fuzzy") -> not_found'
  };

  global.CITE = CITE;
  if (typeof module !== 'undefined' && module.exports) module.exports = CITE;
})(typeof globalThis !== 'undefined' ? globalThis : this);
