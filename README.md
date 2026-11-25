# AI agent model demos

Generate HTML demos with an AI coding agent running in Docker, compare models, publish on GitHub Pages.

- Agent: [opencode](https://opencode.ai) v2 (official GitHub release binary, SHA256-checked; `OPENCODE_VERSION` build arg; registry in `demolib/agents.py`)
- Models: any tool-capable model from OpenRouter
- MCP set (always on): Playwright (headless Chromium) + Context7
- Scenarios: `prompts/<scenarioId>.md`

## Requirements

Python 3.10+, Docker, `OPENROUTER_API_KEY` (env or `.env`, see `.env.example`).

## Usage

```bash
make docker-build          # build ai-agent-demos-shell image
make wizard                # pick scenario, model, effort, agent → run → index → checks → commit
python3 demo.py run --scenario tic-tac-toe --model anthropic/claude-sonnet-5 --effort high --commit
python3 demo.py models "qwen coder"
python3 demo.py prompts
make test                  # unit tests + export safety check of pages/
make serve                 # preview at http://127.0.0.1:8000/<repo>/
```

## Output

`pages/demos/{YYYY-MM-DD}--{scenarioId}--{model}-{effort}--{agent}-{version}/`

| File | Content |
|------|---------|
| `index.html` | Demo produced by the agent, with `<base href>` for GitHub Pages |
| `report.html` | Session report: stats, tool calls, timeline |
| `session.json` | Anonymized `opencode session export` |
| `meta.json` | Run metadata and stats (time, tokens/s, tokens, cost, API calls, tool calls) |
| `prompt.md` | Prompt sent to the agent |

`pages/index.html` and `pages/stats.json` aggregate all runs (per model, per scenario).

## Adding a scenario

Add `prompts/<scenarioId>.md` with an optional `title` front matter.

## Safety

Secrets are passed to Docker by name only. Session exports and artifacts are anonymized
(keys, tokens, emails, local paths, user/host names). `tests/test_export_check.py` scans
`pages/` and fails on leaks or forbidden files; GitHub Actions runs it before deploying.
