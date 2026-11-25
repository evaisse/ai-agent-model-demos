import re
import subprocess

IMAGE = "ai-agent-demos-shell:latest"
MCP_SERVERS = ["playwright", "context7"]

AGENTS = {
    "opencode": {
        "id": "opencode",
        "label": "opencode (OpenRouter)",
        "image": IMAGE,
        "dockerfile": "docker/Dockerfile",
        "context": "docker",
        "mcp_servers": MCP_SERVERS,
    },
}


def parse_version(text):
    m = re.search(r"\d+\.\d+\.\d+[\w.\-]*", text or "")
    return m.group(0) if m else "unknown"


def agent_version(agent):
    try:
        out = subprocess.run(["docker", "run", "--rm", agent["image"], "--version"],
                             capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return parse_version(out.stdout)
