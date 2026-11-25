import json
import tempfile
import unittest
from pathlib import Path

from demolib.index import aggregate, build_index, collect_runs


def meta(scenario, model, cost, tps, status="success"):
    return {"dir": f"2026-11-25--{scenario}--{model.replace('/', '_')}-default--opencode-2.3.2",
            "date": "2026-11-25", "scenario": scenario, "model": model, "effort": "default",
            "agent": "opencode", "agent_version": "2.3.2", "status": status,
            "stats": {"duration_s": 10, "tokens_per_s": tps, "cost_usd": cost, "tool_calls_total": 2,
                      "tokens": {"input": 1, "output": 2, "reasoning": 0}}}


class IndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pages = Path(self.tmp.name)
        for m in (meta("ttt", "a/x", 0.1, 10), meta("ttt", "b/y", 0.3, 30), meta("rain", "a/x", 0.2, 20)):
            d = self.pages / "demos" / m["dir"]
            d.mkdir(parents=True)
            (d / "meta.json").write_text(json.dumps(m))

    def tearDown(self):
        self.tmp.cleanup()

    def test_collect_and_aggregate(self):
        runs = collect_runs(self.pages)
        self.assertEqual(len(runs), 3)
        agg = aggregate(runs, "model")
        ax = next(a for a in agg if a["key"] == "a/x")
        self.assertEqual(ax["runs"], 2)
        self.assertAlmostEqual(ax["total_cost_usd"], 0.3)
        self.assertAlmostEqual(ax["avg_tokens_per_s"], 15)

    def test_build_index_writes_files(self):
        build_index(self.pages)
        html = (self.pages / "index.html").read_text()
        stats = json.loads((self.pages / "stats.json").read_text())
        self.assertEqual(stats["totals"]["runs"], 3)
        self.assertIn('href="demos/2026-11-25--ttt--a_x-default--opencode-2.3.2/index.html"', html)
        self.assertIn('report.html"', html)
        self.assertIn("<caption", html)
        self.assertIn('lang="', html)


if __name__ == "__main__":
    unittest.main()
