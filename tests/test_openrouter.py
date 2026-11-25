import json
import tempfile
import time
import unittest
from pathlib import Path

from demolib.openrouter import format_price, load_models, search, tool_models

MODELS = [
    {"id": "a/tooly", "name": "Tooly", "supported_parameters": ["tools", "reasoning"],
     "pricing": {"prompt": "0.000001", "completion": "0.000002"}},
    {"id": "b/plain", "name": "Plain", "supported_parameters": ["temperature"], "pricing": {}},
    {"id": "c/other", "name": "Other Tool", "supported_parameters": ["tools"], "pricing": {}},
]


class OpenRouterTest(unittest.TestCase):
    def test_tool_models(self):
        self.assertEqual([m["id"] for m in tool_models(MODELS)], ["a/tooly", "c/other"])

    def test_search(self):
        self.assertEqual([m["id"] for m in search(MODELS, "TOOL")], ["a/tooly", "c/other"])
        self.assertEqual(len(search(MODELS, "")), 3)

    def test_format_price(self):
        self.assertEqual(format_price(MODELS[0]), "$1.00/$2.00 per M")
        self.assertEqual(format_price(MODELS[1]), "n/a")

    def test_cache_used_when_fresh(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "models.json"
            cache.write_text(json.dumps({"fetched_at": time.time(), "data": MODELS}))
            got = load_models(cache, fetch=lambda: self.fail("should not fetch"))
            self.assertEqual(len(got), 3)

    def test_cache_refreshed_when_stale(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "models.json"
            cache.write_text(json.dumps({"fetched_at": 0, "data": []}))
            got = load_models(cache, fetch=lambda: MODELS[:1])
            self.assertEqual(len(got), 1)
            self.assertEqual(len(json.loads(cache.read_text())["data"]), 1)

    def test_stale_cache_used_when_fetch_fails(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "models.json"
            cache.write_text(json.dumps({"fetched_at": 0, "data": MODELS}))

            def boom():
                raise OSError("offline")
            self.assertEqual(len(load_models(cache, fetch=boom)), 3)


if __name__ == "__main__":
    unittest.main()
