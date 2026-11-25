# AI Agent Information

Python (stdlib only) tool generating HTML demos with an AI coding agent (opencode) in Docker,
on OpenRouter models, with a fixed MCP set (Playwright + Context7). Output is published on GitHub Pages.

## Layout

- `demo.py` — CLI (argparse): `wizard` (default), `run`, `models`, `agents`, `prompts`, `add-prompt`, `index`, `check-export`, `docker-build`, `serve`
- `demolib/` — `openrouter` (models, 24h cache in `var/`), `agents` (registry), `docker`, `runner` (run + publish),
  `session` (stats), `anonymize`, `report` (report.html), `index` (pages/index.html + stats.json), `export_check`
- `docker/` — agent shell image (`Dockerfile`, `opencode.json` MCP config, `run-agent.sh`)
- `prompts/` — scenario library
- `pages/` — published site; `pages/demos/{date}--{scenario}--{model}-{effort}--{agent}-{version}/`
- `tests/` — unittest; `make test`

## Conventions

- TDD: add/adjust tests in `tests/` first; `make test` must pass before commit.
- Never write secrets to disk or argv; pass env vars by name to Docker.
- Anything under `pages/` is public: keep `export_check` rules strict.
- Conventional commits, no AI attribution lines.
- Files under 600 lines.
