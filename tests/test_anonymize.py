import json
import unittest
from pathlib import Path

from demolib.anonymize import anonymize

FIX = Path(__file__).parent / "fixtures"


class AnonymizeTest(unittest.TestCase):
    def test_scrubs_secrets_paths_emails(self):
        data = json.loads((FIX / "export.json").read_text())
        out = json.dumps(anonymize(data, secrets=["supersecretvalue"]))
        self.assertNotIn("sk-or-v1-", out)
        self.assertNotIn("/Users/alice", out)
        self.assertNotIn("/home/bob", out)
        self.assertNotIn("me@corp.io", out)
        self.assertNotIn("/workspace", out)

    def test_explicit_secret_and_tokens(self):
        text = "a supersecretvalue b Bearer abcdefghijklmnop ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
        out = anonymize(text, secrets=["supersecretvalue"])
        for needle in ("supersecretvalue", "abcdefghijklmnop", "ghp_"):
            self.assertNotIn(needle, out)

    def test_keeps_example_emails_and_structure(self):
        out = anonymize({"a": ["mail demo@example.com", 3, None]})
        self.assertEqual(out, {"a": ["mail demo@example.com", 3, None]})

    def test_drops_sensitive_keys(self):
        out = anonymize({"info": {"directory": "/x", "env": {"A": "1"}, "title": "t"}})
        self.assertEqual(out, {"info": {"title": "t"}})


if __name__ == "__main__":
    unittest.main()
