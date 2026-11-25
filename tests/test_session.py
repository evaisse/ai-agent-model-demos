import json
import unittest
from pathlib import Path

from demolib.session import compute_stats, session_id_from_events

FIX = Path(__file__).parent / "fixtures"


class SessionStatsTest(unittest.TestCase):
    def setUp(self):
        self.export = json.loads((FIX / "export.json").read_text())

    def test_tokens_and_cost(self):
        s = compute_stats(self.export, wall_s=30)
        self.assertEqual(s["tokens"]["input"], 3000)
        self.assertEqual(s["tokens"]["output"], 500)
        self.assertEqual(s["tokens"]["reasoning"], 50)
        self.assertEqual(s["tokens"]["cache_read"], 300)
        self.assertAlmostEqual(s["cost_usd"], 0.03)
        self.assertEqual(s["api_calls"], 2)
        self.assertEqual(s["duration_s"], 30)

    def test_tokens_per_second_uses_generation_time(self):
        s = compute_stats(self.export, wall_s=30)
        self.assertAlmostEqual(s["generation_s"], 10.0)
        self.assertAlmostEqual(s["tokens_per_s"], 55.0)

    def test_tool_calls(self):
        s = compute_stats(self.export)
        self.assertEqual(s["tool_calls_total"], 3)
        self.assertEqual(s["tool_calls"]["write"], 1)
        self.assertEqual(s["tool_calls"]["playwright_browser_navigate"], 1)
        self.assertEqual(s["mcp_calls"], {"context7": 1, "playwright": 1})
        self.assertEqual(s["tool_errors"], 1)

    def test_cost_fallback_on_pricing(self):
        for m in self.export["messages"]:
            m["info"].pop("cost", None)
            for p in m["parts"]:
                p.pop("cost", None)
        s = compute_stats(self.export, pricing={"prompt": "0.000001", "completion": "0.00001"})
        self.assertAlmostEqual(s["cost_usd"], 3000 * 1e-6 + 550 * 1e-5)

    def test_empty_export(self):
        s = compute_stats(None, wall_s=5)
        self.assertEqual(s["api_calls"], 0)
        self.assertEqual(s["tokens_per_s"], 0)

    def test_session_id_from_events(self):
        lines = ['not json', json.dumps({"type": "step_start", "sessionID": "ses_42"})]
        self.assertEqual(session_id_from_events(lines), "ses_42")


if __name__ == "__main__":
    unittest.main()


class SessionV2Test(unittest.TestCase):
    def setUp(self):
        self.export = json.loads((FIX / "export_v2.json").read_text())

    def test_v2_stats(self):
        s = compute_stats(self.export, wall_s=60)
        self.assertEqual(s["api_calls"], 2)
        self.assertEqual(s["tokens"]["output"], 8518)
        self.assertEqual(s["tokens"]["reasoning"], 5502)
        self.assertAlmostEqual(s["cost_usd"], 0.0098858)
        self.assertEqual(s["tool_calls"], {"write": 1, "playwright_browser_navigate": 1})
        self.assertEqual(s["mcp_calls"], {"playwright": 1})
        self.assertEqual(s["tool_errors"], 1)
        self.assertAlmostEqual(s["ttft_s"], 2.21, places=2)
        self.assertGreater(s["tokens_per_s"], 0)

    def test_normalize_v2(self):
        from demolib.session import normalize_export
        n = normalize_export(self.export)
        roles = [m["info"]["role"] for m in n["messages"]]
        self.assertEqual(roles, ["user", "assistant", "assistant"])
        tool = next(p for p in n["messages"][1]["parts"] if p["type"] == "tool")
        self.assertEqual(tool["tool"], "write")
        self.assertIn("Created file", tool["state"]["output"])
