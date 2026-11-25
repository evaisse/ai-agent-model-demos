import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from demolib import runner
from demolib.export_check import check_tree

FIX = Path(__file__).parent / "fixtures"


class PublishRunTest(unittest.TestCase):
    def test_publish_simulated_run(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", {"PAGES_BASE": "/repo/"}):
            tmp = Path(tmp)
            work = tmp / "work"
            (work / "workspace").mkdir(parents=True)
            (work / "workspace" / "index.html").write_text("<html><head></head><body>/Users/alice/x</body></html>")
            (work / "workspace" / "opencode.json").write_text("{}")
            dest = tmp / "pages" / "demos" / "2026-11-25--ttt--x_y-default--opencode-2.3.2"
            export = json.loads((FIX / "export.json").read_text())
            meta = runner.publish(dest, work, {"date": "2026-11-25", "scenario": "ttt", "model": "x/y",
                                               "effort": "default", "agent": "opencode", "agent_version": "2.3.2",
                                               "status": "success", "mcp_servers": ["playwright", "context7"],
                                               "errors": []}, "prompt", export, [], 12.5, None)
            names = sorted(p.name for p in dest.iterdir())
            self.assertEqual(names, ["index.html", "meta.json", "prompt.md", "report.html", "session.json"])
            self.assertIn(f'<base href="/repo/demos/{dest.name}/">', (dest / "index.html").read_text())
            self.assertEqual(meta["stats"]["api_calls"], 2)
            self.assertEqual(check_tree(tmp / "pages"), [])

    def test_prompts_library(self):
        ids = [p["id"] for p in runner.list_prompts()]
        self.assertIn("tic-tac-toe", ids)
        meta, body = runner.parse_prompt("---\ntitle: T\n---\n\nHello")
        self.assertEqual((meta, body), ({"title": "T"}, "Hello"))


if __name__ == "__main__":
    unittest.main()


class CreatePromptTest(unittest.TestCase):
    def test_create_prompt(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(runner, "PROMPTS", Path(tmp)):
            path = runner.create_prompt("my-scene", "My scene", "Build a thing.\n")
            self.assertEqual(path.read_text(), "---\ntitle: My scene\n---\n\nBuild a thing.\n")
            self.assertEqual([p["id"] for p in runner.list_prompts()], ["my-scene"])
            with self.assertRaises(ValueError):
                runner.create_prompt("my-scene", "dup", "x")

    def test_create_prompt_validation(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(runner, "PROMPTS", Path(tmp)):
            for bad in ("Bad Id", "../x", "", "a/b"):
                with self.assertRaises(ValueError):
                    runner.create_prompt(bad, "t", "body")
            with self.assertRaises(ValueError):
                runner.create_prompt("ok", "t", "   ")

    def test_slugify(self):
        self.assertEqual(runner.slugify("  Cool 3D Spinner!! "), "cool-3d-spinner")
