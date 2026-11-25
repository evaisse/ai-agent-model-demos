import re
from pathlib import Path

ALLOWED_EXT = {".html", ".css", ".js", ".mjs", ".json", ".md", ".txt", ".svg", ".png", ".jpg",
               ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".ttf", ".glb", ".gltf",
               ".mp3", ".ogg", ".wav", ".gitkeep"}
FORBIDDEN_NAMES = {"opencode.json", ".npmrc", "id_rsa", "credentials.json"}
FORBIDDEN_DIRS = {"node_modules", ".git", ".opencode"}
TEXT_EXT = {".html", ".css", ".js", ".mjs", ".json", ".md", ".txt", ".svg"}
ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "example.net")

RULES = [
    ("openrouter key", re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}")),
    ("api key", re.compile(r"\bsk-(?!or-)[A-Za-z0-9_\-]{20,}")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("bearer token", re.compile(r"Bearer\s+(?!<)[A-Za-z0-9._\-]{12,}")),
    ("local path", re.compile(r"(?<![\w.])/(Users|home)/[A-Za-z0-9._\-]+/")),
    ("local path", re.compile(r"(?<![\w.])/private/(tmp|var)/")),
]
EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@(?:[A-Za-z0-9\-]+\.)+[A-Za-z]{2,}\b")
MAX_BYTES = 5 * 1024 * 1024


def _file_problems(path, rel):
    parts = set(Path(rel).parts)
    if parts & FORBIDDEN_DIRS:
        return [f"{rel}: forbidden directory"]
    name = path.name
    if name.startswith(".env") or name in FORBIDDEN_NAMES:
        return [f"{rel}: forbidden file"]
    ext = path.suffix.lower() if path.suffix else name
    if ext not in ALLOWED_EXT:
        return [f"{rel}: extension not allowed"]
    return []


def check_tree(root, secrets=(), max_bytes=MAX_BYTES):
    root = Path(root)
    problems = []
    if not root.exists():
        return problems
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        found = _file_problems(path, rel)
        if found:
            problems.extend(found)
            continue
        if path.stat().st_size > max_bytes:
            problems.append(f"{rel}: larger than {max_bytes} bytes")
            continue
        if path.suffix.lower() not in TEXT_EXT:
            continue
        text = path.read_text(errors="ignore")
        for secret in secrets:
            if secret and secret in text:
                problems.append(f"{rel}: contains a configured secret value")
        for label, regex in RULES:
            if regex.search(text):
                problems.append(f"{rel}: {label}")
        for m in EMAIL.finditer(text):
            if not m.group(0).lower().endswith(ALLOWED_EMAIL_DOMAINS) and not _looks_like_package(m.group(0)):
                problems.append(f"{rel}: email address {m.group(0)}")
                break
    return problems


def _looks_like_package(text):
    domain = text.split("@", 1)[1]
    return bool(re.match(r"^\d", domain)) or domain.endswith((".js", ".min.js", ".css"))
