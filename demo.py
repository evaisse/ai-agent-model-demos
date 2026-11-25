#!/usr/bin/env python3
"""AI agent HTML demo generator: wizard + subcommands. Stdlib only."""
import argparse
import http.server
import json
import os
import subprocess
import sys
from pathlib import Path

from demolib import agents as agents_mod
from demolib import openrouter
from demolib.docker import build_image, docker_ready, image_exists
from demolib.export_check import check_tree
from demolib.index import build_index
from demolib.runner import PAGES, ROOT, VAR, create_prompt, execute, list_prompts, pages_base, slugify
from demolib.anonymize import default_secrets

EFFORTS = ["default", "minimal", "low", "medium", "high"]


def load_dotenv(path=ROOT / ".env"):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def models(refresh=False):
    return openrouter.tool_models(openrouter.load_models(VAR / "models.json", refresh=refresh))


def ask(question, default=None):
    suffix = f" [{default}]" if default else ""
    answer = input(f"{question}{suffix}: ").strip()
    return answer or default


def choose(title, items, label):
    print(f"\n{title}")
    for i, item in enumerate(items, 1):
        print(f"  {i:>2}. {label(item)}")
    while True:
        raw = ask("Number", "1")
        if raw.isdigit() and 1 <= int(raw) <= len(items):
            return items[int(raw) - 1]
        print("Invalid choice.")


def choose_model(all_models):
    while True:
        term = ask("\nSearch model (e.g. 'claude sonnet', 'qwen coder')", "")
        found = openrouter.search(all_models, term)[:20]
        if not found:
            print("No match.")
            continue
        return choose(f"{len(found)} tool-capable models", found,
                      lambda m: f"{m['id']:<50} {openrouter.format_price(m)}")


def yes(question, default=False):
    raw = ask(f"{question} (y/n)", "y" if default else "n").lower()
    return raw.startswith("y")


def ensure_image(agent):
    ok, info = docker_ready()
    if not ok:
        sys.exit(f"✖ {info}")
    if not image_exists(agent["image"]):
        print(f"Building {agent['image']}…")
        if not build_image(ROOT, agent):
            sys.exit("✖ docker build failed")


def require_key():
    if not os.environ.get("OPENROUTER_API_KEY"):
        sys.exit("✖ OPENROUTER_API_KEY is not set (env or .env)")


def run_tests():
    return subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=ROOT).returncode == 0


def commit_run(meta):
    paths = [f"pages/demos/{meta['dir']}", "pages/index.html", "pages/stats.json"]
    msg = f"feat(demos): add {meta['scenario']} by {meta['model']} ({meta['agent']} {meta['agent_version']}, {meta['effort']})"
    subprocess.run(["git", "add", "--", *paths], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", msg, "--", *paths], cwd=ROOT, check=True)


def print_summary(meta):
    s = meta["stats"]
    print(f"\n{meta['status'].upper()}  {meta['dir']}")
    print(f"  time {s['duration_s']}s · {s['tokens_per_s']} tok/s · ${s['cost_usd']:.4f} · "
          f"{s['api_calls']} API calls · {s['tool_calls_total']} tool calls {s['mcp_calls']}")
    print(f"  demo   pages/demos/{meta['dir']}/index.html\n  report pages/demos/{meta['dir']}/report.html")


def finish(meta, interactive, commit):
    build_index(PAGES)
    print_summary(meta)
    problems = check_tree(PAGES, secrets=default_secrets())
    if problems:
        print("✖ export check failed:\n  " + "\n  ".join(problems))
        return 1
    if not run_tests():
        print("✖ tests failed, not committing")
        return 1
    if commit or (interactive and yes("Commit this demo?", True)):
        commit_run(meta)
    return 0


def do_run(args, interactive=False):
    require_key()
    agent = agents_mod.AGENTS[args.agent]
    ensure_image(agent)
    model = openrouter.find(models(), args.model) or {}
    if not model:
        print(f"⚠ {args.model} not in tool-capable OpenRouter models")
    meta = execute(args.scenario, args.model, args.effort, args.agent, args.timeout,
                   pricing=model.get("pricing"), force=args.force,
                   confirm_overwrite=(lambda n: yes(f"{n} exists, overwrite?")) if interactive else None)
    return finish(meta, interactive, args.commit)


NEW_PROMPT = {"id": None, "title": "+ New scenario…"}


def read_multiline(message):
    print(f"{message} (finish with a line containing only '.', or Ctrl-D)")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == ".":
            break
        lines.append(line)
    return "\n".join(lines)


def add_prompt_interactive(title=None, scenario_id=None, body=None):
    title = title or ask("Title")
    scenario_id = scenario_id or ask("Scenario id", slugify(title or ""))
    body = body if body is not None else read_multiline("Prompt")
    try:
        path = create_prompt(scenario_id, title or scenario_id, body)
    except ValueError as exc:
        sys.exit(f"✖ {exc}")
    print(f"✔ created {path.relative_to(ROOT)}")
    return scenario_id


def cmd_add_prompt(args):
    body = None
    if args.file == "-":
        body = sys.stdin.read()
    elif args.file:
        body = Path(args.file).read_text()
    add_prompt_interactive(args.title, args.id, body)


def cmd_wizard(args):
    require_key()
    scenario = choose("Scenario (prompts/)", list_prompts() + [NEW_PROMPT],
                      lambda p: f"{p['id']:<24} {p['title']}" if p["id"] else p["title"])
    if scenario is NEW_PROMPT:
        new_id = add_prompt_interactive()
        scenario = next(p for p in list_prompts() if p["id"] == new_id)
    model = choose_model(models())
    efforts = EFFORTS if openrouter.supports_reasoning(model) else ["default"]
    effort = choose("Reasoning effort", efforts, str) if len(efforts) > 1 else "default"
    agent = choose("Coding agent", list(agents_mod.AGENTS.values()), lambda a: a["label"])
    timeout = int(ask("Timeout seconds", str(args.timeout)))
    print(f"\n{scenario['id']} · {model['id']} · {effort} · {agent['id']} · MCP {agent['mcp_servers']} · {timeout}s")
    if not yes("Launch?", True):
        return 0
    ns = argparse.Namespace(scenario=scenario["id"], model=model["id"], effort=effort, agent=agent["id"],
                            timeout=timeout, force=False, commit=False)
    return do_run(ns, interactive=True)


def cmd_models(args):
    for m in openrouter.search(models(args.refresh), args.search or ""):
        flag = "R" if openrouter.supports_reasoning(m) else " "
        print(f"{flag} {m['id']:<55} {openrouter.format_price(m)}")


def cmd_agents(args):
    for a in agents_mod.AGENTS.values():
        print(f"{a['id']:<12} {a['label']:<28} image={a['image']} mcp={','.join(a['mcp_servers'])}")


def cmd_prompts(args):
    for p in list_prompts():
        print(f"{p['id']:<24} {p['title']}")


def cmd_index(args):
    stats = build_index(PAGES)
    print(f"index: {stats['totals']['runs']} runs → pages/index.html, pages/stats.json")


def cmd_check(args):
    problems = check_tree(PAGES, secrets=default_secrets())
    print("\n".join(problems) if problems else "export check: OK")
    return 1 if problems else 0


def cmd_docker_build(args):
    ok, info = docker_ready()
    if not ok:
        sys.exit(f"✖ {info}")
    return 0 if build_image(ROOT, agents_mod.AGENTS[args.agent], args.no_cache) else 1


def cmd_serve(args):
    base = pages_base()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path):
            if path.startswith(base):
                path = "/" + path[len(base):]
            return super().translate_path(path)

    handler = lambda *a, **k: Handler(*a, directory=str(PAGES), **k)
    print(f"Serving pages/ at http://127.0.0.1:{args.port}{base}")
    http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler).serve_forever()


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd")
    w = sub.add_parser("wizard", help="interactive demo generation (default)")
    w.add_argument("--timeout", type=int, default=900)
    w.set_defaults(fn=cmd_wizard)
    r = sub.add_parser("run", help="non-interactive demo generation")
    r.add_argument("--scenario", required=True, choices=[x["id"] for x in list_prompts()])
    r.add_argument("--model", required=True, help="OpenRouter model id")
    r.add_argument("--effort", default="default", choices=EFFORTS)
    r.add_argument("--agent", default="opencode", choices=list(agents_mod.AGENTS))
    r.add_argument("--timeout", type=int, default=900)
    r.add_argument("--force", action="store_true", help="overwrite an existing run directory")
    r.add_argument("--commit", action="store_true", help="git commit the run when checks pass")
    r.set_defaults(fn=lambda a: do_run(a))
    m = sub.add_parser("models", help="list tool-capable OpenRouter models")
    m.add_argument("search", nargs="?")
    m.add_argument("--refresh", action="store_true")
    m.set_defaults(fn=cmd_models)
    sub.add_parser("agents", help="list coding agents").set_defaults(fn=cmd_agents)
    sub.add_parser("prompts", help="list scenarios in prompts/").set_defaults(fn=cmd_prompts)
    ap = sub.add_parser("add-prompt", help="add a scenario to prompts/ (asks for missing fields)")
    ap.add_argument("--id", help="scenario id, lowercase-kebab-case (default: from title)")
    ap.add_argument("--title")
    ap.add_argument("--file", help="read the prompt body from a file, or '-' for stdin")
    ap.set_defaults(fn=cmd_add_prompt)
    sub.add_parser("index", help="rebuild pages/index.html and stats.json").set_defaults(fn=cmd_index)
    sub.add_parser("check-export", help="scan pages/ for secrets and forbidden files").set_defaults(fn=cmd_check)
    b = sub.add_parser("docker-build", help="build the agent shell image")
    b.add_argument("--agent", default="opencode", choices=list(agents_mod.AGENTS))
    b.add_argument("--no-cache", action="store_true")
    b.set_defaults(fn=cmd_docker_build)
    s = sub.add_parser("serve", help="preview pages/ locally under the GitHub Pages base path")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(fn=cmd_serve)
    return p


def main(argv=None):
    load_dotenv()
    args = parser().parse_args(argv)
    if not args.cmd:
        args = parser().parse_args(["wizard", *(argv or [])])
    try:
        return args.fn(args) or 0
    except KeyboardInterrupt:
        print("\nAborted.")
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
