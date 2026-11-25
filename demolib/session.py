import json
from collections import Counter

MCP_SERVERS = ("playwright", "context7")


def parse_events(lines):
    events = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def session_id_from_events(lines):
    for event in parse_events(lines):
        sid = event.get("sessionID") or (event.get("part") or {}).get("sessionID")
        if sid:
            return sid
    return None


def export_from_events(events):
    """Rebuild a minimal export when `session export` is unavailable."""
    messages = {}
    for event in events:
        part = event.get("part")
        if not isinstance(part, dict):
            continue
        mid = part.get("messageID", "m")
        msg = messages.setdefault(mid, {"info": {"id": mid, "role": "assistant"}, "parts": []})
        msg["parts"].append(part)
    return {"info": {}, "messages": list(messages.values())}


def _v2_part(c):
    kind = c.get("type")
    if kind != "tool":
        return {"type": kind, "text": c.get("text", "")}
    state = c.get("state") or {}
    t = c.get("time") or {}
    output = "\n".join(x.get("text", "") for x in state.get("content") or [] if isinstance(x, dict))
    return {"type": "tool", "tool": c.get("name", "?"), "callID": c.get("id"),
            "state": {"status": state.get("status"), "input": state.get("input"), "output": output,
                      "error": state.get("error"), "time": {"start": t.get("created"), "end": t.get("completed")}}}


def normalize_export(export):
    """Return the v1 shape ({info, parts}) for both opencode v1 and v2 exports."""
    messages = (export or {}).get("messages", [])
    if not messages or "info" in messages[0]:
        return export or {}
    out = []
    for m in messages:
        role = m.get("type")
        if role not in ("user", "assistant"):
            continue
        info = {"id": m.get("id"), "role": role, "time": m.get("time") or {}}
        if role == "assistant":
            info.update(modelID=(m.get("model") or {}).get("id"), cost=m.get("cost", 0), tokens=m.get("tokens") or {})
            parts = [_v2_part(c) for c in m.get("content") or []]
        else:
            parts = [{"type": "text", "text": m.get("text", "")}]
        out.append({"info": info, "parts": parts})
    return {"info": {"time": (export.get("info") or {}).get("time") or {}}, "messages": out}


def _tokens(src):
    src = src or {}
    cache = src.get("cache") or {}
    return {
        "input": src.get("input", 0) or 0,
        "output": src.get("output", 0) or 0,
        "reasoning": src.get("reasoning", 0) or 0,
        "cache_read": cache.get("read", 0) or 0,
        "cache_write": cache.get("write", 0) or 0,
    }


def _add(acc, tok):
    for k, v in tok.items():
        acc[k] = acc.get(k, 0) + v


def compute_stats(export, events=None, wall_s=None, pricing=None):
    if not export and events:
        export = export_from_events(events)
    messages = normalize_export(export).get("messages", [])
    ttft = None
    tokens = {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0}
    cost = 0.0
    api_calls = 0
    gen_ms = 0
    tools = Counter()
    mcp = Counter()
    tool_errors = 0
    tool_ms = 0
    for msg in messages:
        info = msg.get("info", {})
        if info.get("role") != "assistant":
            continue
        parts = msg.get("parts", [])
        finishes = [p for p in parts if p.get("type") == "step-finish"]
        if finishes:
            api_calls += len(finishes)
            for p in finishes:
                _add(tokens, _tokens(p.get("tokens")))
                cost += p.get("cost", 0) or 0
        else:
            api_calls += 1
            _add(tokens, _tokens(info.get("tokens")))
            cost += info.get("cost", 0) or 0
        t = info.get("time") or {}
        if t.get("created") and t.get("completed"):
            gen_ms += t["completed"] - t["created"]
        if ttft is None and t.get("created") and t.get("firstToken"):
            ttft = (t["firstToken"] - t["created"]) / 1000
        for p in parts:
            if p.get("type") != "tool":
                continue
            name = p.get("tool", "?")
            tools[name] += 1
            server = name.split("_", 1)[0]
            if server in MCP_SERVERS:
                mcp[server] += 1
            state = p.get("state") or {}
            if state.get("status") == "error":
                tool_errors += 1
            st = state.get("time") or {}
            if st.get("start") and st.get("end"):
                tool_ms += st["end"] - st["start"]
    if not cost and pricing:
        prompt = float(pricing.get("prompt") or 0)
        completion = float(pricing.get("completion") or 0)
        cost = tokens["input"] * prompt + (tokens["output"] + tokens["reasoning"]) * completion
    gen_s = gen_ms / 1000
    out_tokens = tokens["output"] + tokens["reasoning"]
    return {
        "duration_s": round(wall_s, 2) if wall_s is not None else round(gen_s, 2),
        "generation_s": round(gen_s, 2),
        "ttft_s": round(ttft, 2) if ttft is not None else None,
        "tool_time_s": round(tool_ms / 1000, 2),
        "tokens": tokens,
        "tokens_per_s": round(out_tokens / gen_s, 2) if gen_s else 0,
        "cost_usd": round(cost, 8),
        "api_calls": api_calls,
        "tool_calls_total": sum(tools.values()),
        "tool_calls": dict(tools.most_common()),
        "mcp_calls": dict(sorted(mcp.items())),
        "tool_errors": tool_errors,
    }
