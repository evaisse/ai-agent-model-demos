#!/usr/bin/env bash
# Runs one opencode session in /workspace and writes logs to /out.
# Env: MODEL (OpenRouter id), EFFORT, TIMEOUT, TITLE, OPENROUTER_API_KEY, CONTEXT7_API_KEY.
set -uo pipefail

if [ "${1:-}" = "--version" ]; then
  opencode --version
  exit 0
fi
if [ "${1:-}" != "" ]; then
  exec "$@"
fi

model="openrouter/${MODEL:?MODEL is required}"
effort_args=()
if [ -n "${EFFORT:-}" ] && [ "${EFFORT}" != "default" ]; then
  if opencode run --help 2>&1 | grep -q -- '--variant'; then
    effort_args=(--variant "${EFFORT}")
  else
    model="${model}#${EFFORT}"
  fi
fi

cd /workspace
git init -q 2>/dev/null || true
opencode --version > /out/agent-version.txt 2>/dev/null
date +%s%3N > /out/started-ms

timeout --signal=TERM --kill-after=15 "${TIMEOUT:-900}" \
  opencode run --auto --format json --model "${model}" "${effort_args[@]}" --title "${TITLE:-demo}" \
  "$(cat /out/prompt.md)" > /out/events.jsonl 2> /out/stderr.log
echo $? > /out/exit-code
date +%s%3N > /out/ended-ms

sid="$(grep -o '"sessionID":"[^"]*"' /out/events.jsonl | head -n1 | cut -d'"' -f4)"
if [ -n "${sid}" ]; then
  for cmd in "session export" "export"; do
    # shellcheck disable=SC2086
    opencode ${cmd} "${sid}" > /out/export.json 2>> /out/stderr.log
    if head -c 1 /out/export.json | grep -q '{'; then break; fi
    rm -f /out/export.json
  done
fi
exit 0
