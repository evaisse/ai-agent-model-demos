import tempfile
import unittest
from pathlib import Path

from demolib.publish import copy_artifacts, inject_base, run_dir_name


class PublishTest(unittest.TestCase):
    def test_run_dir_name(self):
        name = run_dir_name("2026-11-25", "tic-tac-toe", "anthropic/claude-sonnet-4.5", "high", "opencode", "2.3.2")
        self.assertEqual(name, "2026-11-25--tic-tac-toe--anthropic_claude-sonnet-4.5-high--opencode-2.3.2")

    def test_run_dir_name_sanitizes(self):
        name = run_dir_name("2026-11-25", "x", "a/b:free", "default", "opencode", "v2.3.2")
        self.assertEqual(name, "2026-11-25--x--a_b_free-default--opencode-2.3.2")

    def test_inject_base_in_head(self):
        out = inject_base("<html><head><title>t</title></head></html>", "/r/demos/a/")
        self.assertIn('<head>\n<base href="/r/demos/a/">', out)

    def test_inject_base_replaces_existing(self):
        out = inject_base('<html><head><base href="/old/"></head></html>', "/new/")
        self.assertIn('<base href="/new/">', out)
        self.assertNotIn("/old/", out)

    def test_inject_base_without_head(self):
        out = inject_base("<div>hi</div>", "/b/")
        self.assertTrue(out.startswith('<base href="/b/">'))

    def test_copy_artifacts_allowlist(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as dst:
            s = Path(src)
            for rel in ("index.html", "app.js", "img/a.png", "opencode.json", ".env", "run.sh",
                        "node_modules/x.js", ".git/HEAD", "PROMPT.md", "AGENTS.md"):
                (s / rel).parent.mkdir(parents=True, exist_ok=True)
                (s / rel).write_text("x")
            copied = copy_artifacts(s, Path(dst))
            self.assertEqual(sorted(copied), ["app.js", "img/a.png", "index.html"])


if __name__ == "__main__":
    unittest.main()
