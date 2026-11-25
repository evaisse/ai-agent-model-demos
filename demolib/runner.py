import json
import os
import re
import shutil
import subprocess
import time
from datetime import date
from pathlib import Path

from . import agents as agents_mod
from .anonymize import anonymize, default_secrets, scrub
from .docker import run_agent
from .html import esc, page
from .publish import copy_artifacts, inject_base, run_dir_name
from .report import render_report
from .session import compute_stats, parse_events

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
PAGES = ROOT / "pages"
VAR = ROOT / "var"
TEXT_EXT = {".html", ".css", ".js", ".mjs", ".json", ".svg"}

OUTPUT_RULES = """

---
Output requirements (harness):
- Write the final result as a self-contained `index.html` in the current working directory.
- Use only relative URLs for local assets; CDN dependencies are allowed.
- You may use the Playwright MCP tools to open and check your page, and Context7 for library docs.
"""


def list_prompts():
    out = []
    for path in sorted(PROMPTS.glob("*.md")):
        meta, _ = parse_prompt(path.read_text())
        out.append({"id": path.stem, "title": meta.get("title", path.stem), "path": path})
    return out


def parse_prompt(text):
    meta = {}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        text = text[m.end():]
    return meta, text.strip()


def pages_base():
    if os.environ.get("PAGES_BASE"):
        base = os.environ["PAGES_BASE"]
        return base if base.endswith("/") else base + "/"
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, cwd=ROOT).stdout
        name = url.strip().rstrip("/").removesuffix(".git").rsplit("/", 1)[-1]
        if name and not name.endswith(".github.io"):
            return f"/{name}/"
    except OSError:
        pass
    return "/"


def _read(path, default=""):
    return path.read_text(errors="ignore") if path.exists() else default


def _status(exit_code, has_index, docker_rc):
    if docker_rc not in (0, None) or exit_code is None:
        return "runtime_error"
    if exit_code == 124:
        return "timeout"
    if exit_code != 0:
        return "agent_error"
    return "success" if has_index else "no_artifact"


def execute(scenario_id, model, effort="default", agent_id="opencode", timeout=900, pricing=None,
            force=False, confirm_overwrite=None, log=print):
    agent = agents_mod.AGENTS[agent_id]
    meta_p, prompt = parse_prompt((PROMPTS / f"{scenario_id}.md").read_text())
    version = agents_mod.agent_version(agent)
    today = date.today().isoformat()
    name = run_dir_name(today, scenario_id, model, effort, agent_id, version)
    dest = PAGES / "demos" / name
    if dest.exists() and not force:
        if not (confirm_overwrite and confirm_overwrite(name)):
            raise SystemExit(f"Run directory already exists: {name} (use --force)")
    work = VAR / "runs" / name
    shutil.rmtree(work, ignore_errors=True)
    (work / "workspace").mkdir(parents=True)
    (work / "out").mkdir(parents=True)
    (work / "out" / "prompt.md").write_text(prompt + OUTPUT_RULES)

    log(f"▶ {name}")
    started = time.time()
    rc = run_agent(agent, work / "workspace", work / "out", model, effort, timeout, name)
    wall = time.time() - started
    out = work / "out"
    exit_raw = _read(out / "exit-code").strip()
    exit_code = int(exit_raw) if exit_raw.isdigit() else None
    events = parse_events(_read(out / "events.jsonl").splitlines())
    export = None
    if (out / "export.json").exists():
        try:
            export = json.loads(_read(out / "export.json"))
        except json.JSONDecodeError:
            export = None
    has_index = (work / "workspace" / "index.html").exists()
    status = _status(exit_code, has_index, rc)
    errors = []
    if status != "success":
        errors.append(f"status={status} docker_rc={rc} exit_code={exit_code}")
        tail = _read(out / "stderr.log")[-2000:].strip()
        if tail:
            errors.append(tail)
    return publish(dest, work, {
        "date": today, "scenario": scenario_id, "scenario_title": meta_p.get("title", scenario_id),
        "model": model, "effort": effort, "agent": agent_id, "agent_version": version,
        "mcp_servers": agent["mcp_servers"], "status": status, "timeout_s": timeout,
        "errors": errors,
    }, prompt, export, events, wall, pricing)


def publish(dest, work, meta, prompt, export, events, wall, pricing):
    secrets = default_secrets()
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    copied = copy_artifacts(work / "workspace", dest)
    for rel in copied:
        p = dest / rel
        if p.suffix.lower() in TEXT_EXT:
            p.write_text(scrub(p.read_text(errors="ignore"), secrets))
    href = f"{pages_base()}demos/{dest.name}/"
    index = dest / "index.html"
    if index.exists():
        index.write_text(inject_base(index.read_text(errors="ignore"), href))
    else:
        index.write_text(page("No demo produced", f'<h1>No index.html produced</h1><p>Status: {esc(meta["status"])}. '
                                                   f'<a href="report.html">Read the session report</a>.</p>'))
    if not export and events:
        from .session import export_from_events
        export = export_from_events(events)
    clean_export = anonymize(export or {}, secrets)
    meta = anonymize(meta, secrets)
    meta["dir"] = dest.name
    meta["artifacts"] = copied
    meta["stats"] = compute_stats(clean_export, wall_s=wall, pricing=pricing)
    (dest / "session.json").write_text(json.dumps(clean_export, indent=1, ensure_ascii=False) + "\n")
    (dest / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    (dest / "prompt.md").write_text(prompt + "\n")
    (dest / "report.html").write_text(render_report(meta, clean_export, prompt))
    return meta
