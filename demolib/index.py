import json
from datetime import datetime, timezone
from pathlib import Path

from .html import esc, fmt_cost, fmt_num, page, table


def collect_runs(pages_dir):
    runs = []
    for meta in sorted(Path(pages_dir, "demos").glob("*/meta.json")):
        data = json.loads(meta.read_text())
        data["dir"] = meta.parent.name
        runs.append(data)
    runs.sort(key=lambda r: (r.get("date", ""), r["dir"]), reverse=True)
    return runs


def aggregate(runs, key):
    groups = {}
    for run in runs:
        groups.setdefault(run.get(key, "?"), []).append(run)
    out = []
    for k, items in groups.items():
        stats = [r.get("stats", {}) for r in items]
        ok = [r for r in items if r.get("status") == "success"]
        n = len(items)
        out.append({
            "key": k,
            "runs": n,
            "success": len(ok),
            "total_cost_usd": round(sum(s.get("cost_usd", 0) for s in stats), 6),
            "avg_cost_usd": round(sum(s.get("cost_usd", 0) for s in stats) / n, 6),
            "avg_duration_s": round(sum(s.get("duration_s", 0) for s in stats) / n, 2),
            "avg_tokens_per_s": round(sum(s.get("tokens_per_s", 0) for s in stats) / n, 2),
            "avg_tool_calls": round(sum(s.get("tool_calls_total", 0) for s in stats) / n, 2),
        })
    out.sort(key=lambda a: (-a["runs"], a["key"]))
    return out


def _run_row(r):
    s = r.get("stats", {})
    base = f"demos/{r['dir']}/"
    status = r.get("status", "?")
    cls = "ok" if status == "success" else "err"
    return [
        esc(r.get("date")), esc(r.get("scenario")), f"<code>{esc(r.get('model'))}</code>", esc(r.get("effort")),
        esc(f"{r.get('agent')} {r.get('agent_version')}"), f'<span class="{cls}">{esc(status)}</span>',
        fmt_num(s.get("duration_s")), fmt_num(s.get("tokens_per_s")), fmt_num((s.get("tokens") or {}).get("output")),
        fmt_cost(s.get("cost_usd")), fmt_num(s.get("tool_calls_total")),
        f'<a href="{esc(base)}index.html">Demo<span class="sr"> {esc(r["dir"])}</span></a> · '
        f'<a href="{esc(base)}report.html">Report<span class="sr"> {esc(r["dir"])}</span></a>',
    ]


def _agg_rows(agg):
    return [[esc(a["key"]), a["runs"], a["success"], fmt_num(a["avg_duration_s"]), fmt_num(a["avg_tokens_per_s"]),
             fmt_cost(a["avg_cost_usd"]), fmt_cost(a["total_cost_usd"]), fmt_num(a["avg_tool_calls"])] for a in agg]


def render_index(runs, by_model, by_scenario, totals):
    agg_headers = ["Key", "Runs", "OK", "Avg s", "Avg tok/s", "Avg cost", "Total cost", "Avg tools"]
    num = range(1, 8)
    body = [
        "<style>.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}</style>",
        "<header><h1>AI agent model demos</h1>",
        f'<p class="muted">{totals["runs"]} runs · {totals["scenarios"]} scenarios · {totals["models"]} models · '
        f'total cost {fmt_cost(totals["cost_usd"])} · <a href="stats.json">stats.json</a></p>',
        '<nav aria-label="Sections"><ul><li><a href="#runs">Runs</a></li><li><a href="#models">By model</a></li>'
        '<li><a href="#scenarios">By scenario</a></li></ul></nav></header><main>',
        '<section id="runs" aria-labelledby="runs-h"><h2 id="runs-h">Runs</h2>',
        table("All runs, newest first",
              ["Date", "Scenario", "Model", "Effort", "Agent", "Status", "Time s", "Tok/s", "Out tok", "Cost", "Tools", "Links"],
              [_run_row(r) for r in runs], numeric=(6, 7, 8, 9, 10)) if runs else "<p>No runs yet.</p>",
        "</section>",
        '<section id="models" aria-labelledby="models-h"><h2 id="models-h">By model</h2>',
        table("Aggregated stats per model", agg_headers, _agg_rows(by_model), numeric=num), "</section>",
        '<section id="scenarios" aria-labelledby="scen-h"><h2 id="scen-h">By scenario</h2>',
        table("Aggregated stats per scenario", agg_headers, _agg_rows(by_scenario), numeric=num), "</section>",
        "</main>",
    ]
    return page("AI agent model demos", "\n".join(body))


def build_index(pages_dir):
    pages_dir = Path(pages_dir)
    runs = collect_runs(pages_dir)
    by_model = aggregate(runs, "model")
    by_scenario = aggregate(runs, "scenario")
    totals = {
        "runs": len(runs),
        "scenarios": len(by_scenario),
        "models": len(by_model),
        "cost_usd": round(sum(r.get("stats", {}).get("cost_usd", 0) for r in runs), 6),
    }
    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "totals": totals,
        "by_model": by_model,
        "by_scenario": by_scenario,
        "runs": [{k: r.get(k) for k in ("dir", "date", "scenario", "model", "effort", "agent",
                                         "agent_version", "status", "stats")} for r in runs],
    }
    (pages_dir / "stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    (pages_dir / "index.html").write_text(render_index(runs, by_model, by_scenario, totals))
    return stats
