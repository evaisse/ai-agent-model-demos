import re
import shutil
from pathlib import Path

ARTIFACT_EXT = {".html", ".css", ".js", ".mjs", ".json", ".svg", ".png", ".jpg", ".jpeg", ".gif",
                ".webp", ".ico", ".woff", ".woff2", ".ttf", ".glb", ".gltf", ".mp3", ".ogg", ".wav"}
SKIP_NAMES = {"opencode.json", "package.json", "package-lock.json", "PROMPT.md", "AGENTS.md"}
SKIP_DIRS = {"node_modules", ".git", ".opencode", ".playwright-mcp"}


def _slug(value):
    return re.sub(r"[^A-Za-z0-9._\-]+", "_", value).strip("_")


def run_dir_name(date, scenario, model, effort, agent, version):
    version = version.lstrip("v")
    return f"{date}--{_slug(scenario)}--{_slug(model.replace('/', '_'))}-{_slug(effort)}--{_slug(agent)}-{_slug(version)}"


def inject_base(html, href):
    tag = f'<base href="{href}">'
    if re.search(r"<base\b[^>]*>", html, re.I):
        return re.sub(r"<base\b[^>]*>", tag, html, count=1, flags=re.I)
    m = re.search(r"<head\b[^>]*>", html, re.I)
    if m:
        return html[:m.end()] + "\n" + tag + html[m.end():]
    return tag + "\n" + html


def copy_artifacts(src, dst):
    src, dst = Path(src), Path(dst)
    copied = []
    for path in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = path.relative_to(src)
        if set(rel.parts) & SKIP_DIRS or any(part.startswith(".") for part in rel.parts):
            continue
        if path.name in SKIP_NAMES or path.suffix.lower() not in ARTIFACT_EXT:
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(rel.as_posix())
    return copied
