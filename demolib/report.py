import json

from .html import esc, fmt_cost, fmt_num, page, table
from .session import normalize_export

MAX_IO = 4000


def _clip(value, limit=MAX_IO):
    if not isinstance(value, str):
        value = json.dumps(value, indent=2, ensure_ascii=False)
    if len(value) > limit:
        return value[:limit] + f"\n… [{len(value) - limit} chars truncated]"
    return value


def _ms(t, start):
    return f"+{(t - start) / 1000:.1f}s" if t and start else ""


def _part(p, start):
    kind = p.get("type")
    if kind == "text" and p.get("text"):
        return f"<pre>{esc(_clip(p['text'], 20000))}</pre>"
    if kind == "reasoning" and p.get("text"):
        return f"<details><summary>Reasoning</summary><pre>{esc(_clip(p['text'], 20000))}</pre></details>"
    if kind == "tool":
        st = p.get("state") or {}
        t = st.get("time") or {}
        dur = f"{(t['end'] - t['start']) / 1000:.2f}s" if t.get("start") and t.get("end") else ""
        status = st.get("status", "?")
        cls = "err" if status == "error" else "ok"
        out = st.get("error") if status == "error" else st.get("output")
        return (f"<details><summary><code>{esc(p.get('tool'))}</code> "
                f'<span class="{cls}">{esc(status)}</span> <span class="muted">{esc(dur)} {_ms(t.get("start"), start)}</span>'
                f"</summary><h3>Input</h3><pre>{esc(_clip(st.get('input')))}</pre>"
                f"<h3>Output</h3><pre>{esc(_clip(out or ''))}</pre></details>")
    if kind == "step-finish":
        tok = p.get("tokens") or {}
        return (f'<p class="muted">step: in {fmt_num(tok.get("input"))} · out {fmt_num(tok.get("output"))} · '
                f'reasoning {fmt_num(tok.get("reasoning"))} · {fmt_cost(p.get("cost"))}</p>')
    return ""


def _timeline(export):
    export = normalize_export(export)
    messages = (export or {}).get("messages", [])
    start = ((export or {}).get("info", {}).get("time") or {}).get("created")
    items = []
    for msg in messages:
        info = msg.get("info", {})
        role = info.get("role", "?")
        t = info.get("time") or {}
        head = f"<strong>{esc(role)}</strong>"
        if info.get("modelID"):
            head += f' <code>{esc(info.get("modelID"))}</code>'
        if t.get("created") and t.get("completed"):
            head += f' <span class="muted">{(t["completed"] - t["created"]) / 1000:.1f}s</span>'
        head += f' <span class="muted">{_ms(t.get("created"), start)}</span>'
        parts = "".join(_part(p, start) for p in msg.get("parts", []))
        items.append(f'<li class="{esc(role)}">{head}{parts}</li>')
    return f'<ol class="timeline">{"".join(items)}</ol>' if items else "<p>No session export available.</p>"


def render_report(meta, export, prompt=""):
    s = meta.get("stats", {})
    tok = s.get("tokens", {})
    title = f"{meta.get('scenario')} · {meta.get('model')} · {meta.get('agent')} {meta.get('agent_version')}"
    kv = [
        ("Date", meta.get("date")), ("Scenario", meta.get("scenario")), ("Model", meta.get("model")),
        ("Effort", meta.get("effort")), ("Agent", f"{meta.get('agent')} {meta.get('agent_version')}"),
        ("MCP servers", ", ".join(meta.get("mcp_servers", []))), ("Status", meta.get("status")),
        ("Duration", f"{fmt_num(s.get('duration_s'))} s (generation {fmt_num(s.get('generation_s'))} s, tools {fmt_num(s.get('tool_time_s'))} s)"),
        ("Tokens/s", fmt_num(s.get("tokens_per_s"))), ("Time to first token", f"{fmt_num(s.get('ttft_s'), 2)} s"),
        ("Tokens", f"in {fmt_num(tok.get('input'))} · out {fmt_num(tok.get('output'))} · reasoning {fmt_num(tok.get('reasoning'))} · cache read {fmt_num(tok.get('cache_read'))}"),
        ("Cost", fmt_cost(s.get("cost_usd"))), ("API calls", s.get("api_calls")),
        ("Tool calls", f"{s.get('tool_calls_total', 0)} ({s.get('tool_errors', 0)} errors)"),
    ]
    errors = meta.get("errors") or []
    tool_rows = [[f"<code>{esc(k)}</code>", v] for k, v in (s.get("tool_calls") or {}).items()]
    body = [
        f"<header><h1>{esc(title)}</h1>",
        '<nav aria-label="Run"><ul><li><a href="../../index.html">All demos</a></li><li><a href="index.html">Open demo</a></li>'
        '<li><a href="session.json">Session export (JSON)</a></li><li><a href="meta.json">meta.json</a></li></ul></nav></header><main>',
        '<section aria-labelledby="sum-h"><h2 id="sum-h">Summary</h2><dl class="kv">',
        "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in kv), "</dl>",
        "".join(f'<p class="err">{esc(e)}</p>' for e in errors), "</section>",
        '<section aria-labelledby="tools-h"><h2 id="tools-h">Tools</h2>',
        table("Tool calls by name", ["Tool", "Calls"], tool_rows, numeric=(1,)) if tool_rows else "<p>No tool calls.</p>",
        "</section>",
        f'<section aria-labelledby="prompt-h"><h2 id="prompt-h">Prompt</h2><pre>{esc(prompt)}</pre></section>',
        f'<section aria-labelledby="tl-h"><h2 id="tl-h">Session timeline</h2>{_timeline(export)}</section></main>',
    ]
    return page(f"Report · {title}", "\n".join(body))
