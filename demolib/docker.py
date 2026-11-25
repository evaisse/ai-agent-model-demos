import os
import shutil
import subprocess
from pathlib import Path

PASSTHROUGH_ENV = ("OPENROUTER_API_KEY", "CONTEXT7_API_KEY")


def docker_ready():
    if not shutil.which("docker"):
        return False, "docker CLI not found"
    res = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True)
    if res.returncode != 0:
        return False, "Docker daemon not reachable (start Docker Desktop)"
    return True, res.stdout.strip()


def image_exists(image):
    return subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode == 0


def build_image(root, agent, no_cache=False):
    cmd = ["docker", "build", "-t", agent["image"], "-f", str(Path(root, agent["dockerfile"]))]
    if no_cache:
        cmd.append("--no-cache")
    cmd.append(str(Path(root, agent["context"])))
    return subprocess.run(cmd).returncode == 0


def run_agent(agent, workspace, out_dir, model, effort, timeout, title):
    """Run the agent container. Secrets are passed by name only (`-e VAR`), never in argv values."""
    env = dict(os.environ, MODEL=model, EFFORT=effort, TIMEOUT=str(timeout), TITLE=title)
    cmd = ["docker", "run", "--rm", "--init", "--shm-size=1g",
           "-v", f"{Path(workspace).resolve()}:/workspace", "-v", f"{Path(out_dir).resolve()}:/out",
           "-e", "MODEL", "-e", "EFFORT", "-e", "TIMEOUT", "-e", "TITLE"]
    for name in PASSTHROUGH_ENV:
        if os.environ.get(name):
            cmd += ["-e", name]
    cmd.append(agent["image"])
    try:
        return subprocess.run(cmd, env=env, timeout=timeout + 120).returncode
    except subprocess.TimeoutExpired:
        return 124
