import getpass
import os
import re
import socket

DROP_KEYS = {"directory", "cwd", "env", "environment", "projectID", "worktree", "root", "home", "location", "native"}
ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "example.net", "anthropic.com")

PATTERNS = [
    (re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}"), "<redacted-key>"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), "<redacted-key>"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "<redacted-token>"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]{8,}"), r"\1<redacted>"),
    (re.compile(r"(/Users|/home)/[^/\s\"'<>]+"), "~"),
    (re.compile(r"/root\b"), "~"),
    (re.compile(r"(/private)?/(tmp|var/folders)/[^\s\"'<>]*"), "<tmp>"),
    (re.compile(r"/workspace/?"), "./"),
]
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@([A-Za-z0-9\-]+\.)+[A-Za-z]{2,}")


def default_secrets():
    values = [os.environ.get(k) for k in ("OPENROUTER_API_KEY", "CONTEXT7_API_KEY")]
    return [v for v in values if v and len(v) >= 8]


def _identity_terms():
    terms = []
    for fn in (getpass.getuser, socket.gethostname):
        try:
            value = fn()
        except Exception:
            continue
        if value and len(value) >= 4 and value not in ("root", "node", "agent", "runner"):
            terms.append(value)
    return terms


def _email(match):
    text = match.group(0)
    if text.lower().endswith(ALLOWED_EMAIL_DOMAINS):
        return text
    return "<redacted-email>"


def scrub(text, secrets=(), identity=()):
    for secret in secrets:
        if secret:
            text = text.replace(secret, "<redacted-secret>")
    for regex, repl in PATTERNS:
        text = regex.sub(repl, text)
    text = EMAIL.sub(_email, text)
    for term in identity:
        text = re.sub(re.escape(term), "<redacted>", text, flags=re.IGNORECASE)
    return text


def anonymize(obj, secrets=None, identity=None):
    secrets = list(secrets or []) + default_secrets()
    identity = _identity_terms() if identity is None else identity

    def walk(value):
        if isinstance(value, str):
            return scrub(value, secrets, identity)
        if isinstance(value, list):
            return [walk(v) for v in value]
        if isinstance(value, dict):
            return {k: walk(v) for k, v in value.items() if k not in DROP_KEYS}
        return value

    return walk(obj)
