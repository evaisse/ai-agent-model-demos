import os
import tempfile
import unittest
from pathlib import Path

from demolib.export_check import check_tree

PAGES = Path(__file__).resolve().parent.parent / "pages"


class ExportCheckFixtureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, content):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def test_clean_tree(self):
        self.write("index.html", "<html>hello demo@example.com</html>")
        self.write("demos/a/meta.json", "{}")
        self.assertEqual(check_tree(self.root), [])

    def test_detects_secrets(self):
        self.write("a.html", "key=sk-or-v1-0123456789abcdef0123456789")
        self.write("b.json", '"Authorization": "Bearer abcdefghijklmnopqrst"')
        self.write("c.js", "const t='ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123'")
        self.write("d.txt", "value my-own-secret-123")
        problems = check_tree(self.root, secrets=["my-own-secret-123"])
        self.assertEqual(len(problems), 4, problems)

    def test_detects_local_paths_and_emails(self):
        self.write("a.html", "see /Users/alice/x")
        self.write("b.html", "contact john@corp.io")
        self.assertEqual(len(check_tree(self.root)), 2)

    def test_detects_forbidden_files(self):
        self.write(".env", "X=1")
        self.write("demos/a/opencode.json", "{}")
        self.write("demos/a/node_modules/x.js", "")
        self.write("demos/a/run.sh", "")
        self.assertEqual(len(check_tree(self.root)), 4)

    def test_size_limit(self):
        self.write("big.html", "x" * 50)
        self.assertEqual(len(check_tree(self.root, max_bytes=10)), 1)


class PagesExportTest(unittest.TestCase):
    def test_pages_directory_is_safe_to_publish(self):
        secrets = [os.environ[k] for k in ("OPENROUTER_API_KEY", "CONTEXT7_API_KEY") if os.environ.get(k)]
        problems = check_tree(PAGES, secrets=secrets)
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
