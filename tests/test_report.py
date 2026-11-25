import json
import unittest
from pathlib import Path

from demolib.anonymize import anonymize
from demolib.report import render_report
from demolib.session import compute_stats

FIX = Path(__file__).parent / "fixtures"


class ReportTest(unittest.TestCase):
    def test_render_report(self):
        export = anonymize(json.loads((FIX / "export.json").read_text()))
        meta = {"dir": "d", "scenario": "ttt", "model": "x/y", "effort": "default", "agent": "opencode",
                "agent_version": "2.3.2", "status": "success", "date": "2026-11-25",
                "stats": compute_stats(export, wall_s=30)}
        html = render_report(meta, export, prompt="Build <it>")
        self.assertIn("context7_resolve-library-id", html)
        self.assertIn("playwright_browser_navigate", html)
        self.assertIn("Build &lt;it&gt;", html)
        self.assertIn('href="index.html"', html)
        self.assertIn('href="session.json"', html)
        self.assertIn("<caption", html)
        self.assertNotIn("sk-or-v1-", html)


if __name__ == "__main__":
    unittest.main()
