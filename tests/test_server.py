#!/usr/bin/env python3
"""unittest suite for the INCEPTION daemon (server.py).

Run either of:
    python3 -m unittest discover -s tests -v
    python3 tests/test_server.py
"""
import filecmp
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server  # noqa: E402


def _trees_equal(a, b):
    """True when two directory trees have identical contents (byte-for-byte)."""
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files:
        return False
    for sub in cmp.common_dirs:
        if not _trees_equal(os.path.join(a, sub), os.path.join(b, sub)):
            return False
    return True


class TestServer(unittest.TestCase):
    def setUp(self):
        self.out_root = tempfile.mkdtemp(prefix="inception-test-")
        self.srv = server.make_server("127.0.0.1", 0, self.out_root)
        self.thread = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.srv.server_address[:2]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.thread.join(timeout=5)
        shutil.rmtree(self.out_root, ignore_errors=True)

    # ---- helpers -----------------------------------------------------------

    def _request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=15)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            resp = conn.getresponse()
            data = resp.read()
            return resp.status, dict(resp.getheaders()), data
        finally:
            conn.close()

    def _get(self, path):
        return self._request("GET", path)

    def _post_json(self, path, obj):
        body = json.dumps(obj).encode("utf-8")
        return self._request("POST", path, body=body,
                             headers={"Content-Type": "application/json"})

    def _get_json(self, path):
        status, _headers, data = self._get(path)
        return status, json.loads(data.decode("utf-8"))

    def _post_json_obj(self, path, obj):
        status, _headers, data = self._post_json(path, obj)
        return status, json.loads(data.decode("utf-8"))

    # ---- API: health + verify ---------------------------------------------

    def test_health(self):
        status, headers, data = self._get("/api/health")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        payload = json.loads(data.decode("utf-8"))
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["name"], "inception")
        self.assertEqual(payload["version"], "1.0")
        self.assertTrue(payload["kit_root"].startswith("sha256:"))
        self.assertEqual(payload["out_root"], self.out_root)
        self.assertGreaterEqual(payload["uptime_s"], 0.0)

    def test_verify(self):
        status, payload = self._get_json("/api/verify")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(payload["files_checked"], 30)
        self.assertEqual(payload["files_broken"], 0)
        self.assertEqual(payload["stamp"], "VERIFIED")

    # ---- API: plant --------------------------------------------------------

    def test_plant_valid(self):
        domain = "meeting quotes: verify quotes verbatim"
        status, payload = self._post_json_obj("/api/plant", {"domain": domain})
        self.assertEqual(status, 200)
        for key in ("seed", "hyp_hash", "genesis_file", "tool", "root"):
            self.assertRegex(payload[key], r"^[0-9a-f]{64}$", key)
        self.assertEqual(payload["domain"], domain)
        self.assertTrue(payload["planted"])
        self.assertTrue(payload["hypothesis"])
        self.assertTrue(payload["falsifier"])

    def test_plant_idempotent(self):
        domain = "idempotency check: same domain twice"
        status1, payload1 = self._post_json_obj("/api/plant", {"domain": domain})
        self.assertEqual(status1, 200)
        slug = payload1["slug"]
        dir1 = os.path.join(self.out_root, slug)
        self.assertTrue(os.path.isdir(dir1))

        backup_root = tempfile.mkdtemp(prefix="inception-backup-")
        backup = os.path.join(backup_root, slug)
        shutil.copytree(dir1, backup)
        try:
            status2, payload2 = self._post_json_obj("/api/plant", {"domain": domain})
            self.assertEqual(status2, 200)
            for key in ("slug", "domain", "archetype", "deadline", "seed",
                        "hypothesis_id", "hypothesis", "falsifier", "hyp_hash",
                        "genesis_file", "tool", "tool_name", "root"):
                self.assertEqual(payload1[key], payload2[key], key)
            self.assertTrue(_trees_equal(dir1, backup))
        finally:
            shutil.rmtree(backup_root, ignore_errors=True)

    def test_plant_deadline_and_archetype(self):
        domain = "password hygiene for team accounts"
        status, payload = self._post_json_obj("/api/plant", {
            "domain": domain,
            "deadline": "2030-06-15",
            "archetype": "passgrade",
        })
        self.assertEqual(status, 200)
        self.assertEqual(payload["deadline"], "2030-06-15")
        self.assertEqual(payload["archetype"], "passgrade")
        self.assertEqual(payload["tool_name"], "passgrade.py")
        # the forced archetype must land on disk too
        card = os.path.join(self.out_root, payload["slug"], "planted.card")
        with open(card, encoding="utf-8") as fh:
            self.assertIn("archetype: passgrade", fh.read())

    def test_plant_missing_domain(self):
        status, payload = self._post_json_obj("/api/plant", {})
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "Domain is required.")

    def test_plant_bad_archetype(self):
        status, payload = self._post_json_obj("/api/plant", {
            "domain": "anything", "archetype": "bogus"})
        self.assertEqual(status, 400)

    def test_plant_bad_deadline(self):
        status, payload = self._post_json_obj("/api/plant", {
            "domain": "anything", "deadline": "06/15/2030"})
        self.assertEqual(status, 400)

    def test_plant_body_too_large(self):
        big = {"domain": "x" * 200, "padding": "y" * (64 * 1024)}
        body = json.dumps(big).encode("utf-8")
        status, _headers, data = self._request(
            "POST", "/api/plant", body=body,
            headers={"Content-Type": "application/json"})
        self.assertEqual(status, 413)
        self.assertIn(b"error", data)

    # ---- API: list ---------------------------------------------------------

    def test_list_includes_planted(self):
        domain = "urban farming observations"
        status, payload = self._post_json_obj("/api/plant", {"domain": domain})
        self.assertEqual(status, 200)
        slug = payload["slug"]
        status, lst = self._get_json("/api/list")
        self.assertEqual(status, 200)
        self.assertIsInstance(lst, list)
        self.assertIn(slug, [item.get("slug") for item in lst])

    def test_list_sorted_by_deadline(self):
        self._post_json_obj("/api/plant", {"domain": "zzz late", "deadline": "2099-01-01"})
        self._post_json_obj("/api/plant", {"domain": "aaa early", "deadline": "2001-01-01"})
        _status, lst = self._get_json("/api/list")
        deadlines = [item["deadline"] for item in lst]
        self.assertEqual(deadlines, sorted(deadlines))

    # ---- routing / methods -------------------------------------------------

    def test_unknown_api_404(self):
        status, payload = self._get_json("/api/nope")
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "Not found.")

    def test_wrong_method_405(self):
        status, headers, data = self._post_json("/api/health", {})
        self.assertEqual(status, 405)
        self.assertEqual(headers.get("Allow"), "GET")
        self.assertEqual(json.loads(data.decode("utf-8"))["error"], "Method not allowed.")

    def test_root_fallback(self):
        status, headers, data = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn(b"INCEPTION", data)

    # ---- static files + traversal safety -----------------------------------

    def test_static_receipt_html(self):
        status, headers, data = self._get("/receipt/receipt.html")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn(b"<", data)

    def test_nope_404(self):
        status, _headers, _data = self._get("/nope.html")
        self.assertEqual(status, 404)

    def test_traversal_rejected(self):
        for path in ("/../manifest.json",
                     "/%2e%2e/manifest.json",
                     "/receipt/../../manifest.json"):
            status, _headers, data = self._get(path)
            self.assertIn(status, (403, 404), path)
            self.assertNotIn(b"grasp-inception-manifest", data, path)
            self.assertNotIn(b"kit_root", data, path)


if __name__ == "__main__":
    unittest.main()
