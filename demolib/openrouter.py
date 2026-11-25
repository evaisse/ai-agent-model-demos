import http.client
import json
import time
import urllib.request
from pathlib import Path

MODELS_URL = "https://openrouter.ai/api/v1/models"
MAX_AGE_S = 24 * 3600


def fetch_models(timeout=30, attempts=3):
    req = urllib.request.Request(MODELS_URL, headers={"User-Agent": "ai-agent-model-demos"})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read()).get("data", [])
        except (OSError, http.client.HTTPException, json.JSONDecodeError):
            if attempt == attempts:
                raise
            time.sleep(attempt)


def load_models(cache_path, fetch=fetch_models, max_age=MAX_AGE_S, refresh=False):
    cache_path = Path(cache_path)
    cached = None
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        if not refresh and time.time() - cached.get("fetched_at", 0) < max_age:
            return cached["data"]
    try:
        data = fetch()
    except Exception:
        if cached:
            return cached["data"]
        raise
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"fetched_at": time.time(), "data": data}))
    return data


def tool_models(models):
    return [m for m in models if "tools" in (m.get("supported_parameters") or [])]


def supports_reasoning(model):
    params = model.get("supported_parameters") or []
    return "reasoning" in params or "include_reasoning" in params


def search(models, term):
    term = (term or "").lower().strip()
    if not term:
        return list(models)
    words = term.split()
    return [m for m in models
            if all(w in f"{m.get('id', '')} {m.get('name', '')}".lower() for w in words)]


def format_price(model):
    pricing = model.get("pricing") or {}
    try:
        prompt = float(pricing["prompt"]) * 1e6
        completion = float(pricing["completion"]) * 1e6
    except (KeyError, TypeError, ValueError):
        return "n/a"
    return f"${prompt:.2f}/${completion:.2f} per M"


def find(models, model_id):
    return next((m for m in models if m.get("id") == model_id), None)
