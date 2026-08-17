import asyncio
import os
import re
import shlex

import asyncssh
from dotenv import load_dotenv

load_dotenv()

VPS_HOST = os.environ["VPS_HOST"]
VPS_PORT = int(os.getenv("VPS_PORT", "22"))
VPS_USER = os.environ["VPS_USER"]
VPS_SSH_KEY = os.path.expanduser(os.environ["VPS_SSH_KEY"])
VPS_KNOWN_HOSTS = os.getenv("VPS_KNOWN_HOSTS", "").strip()
DOCKER_COMPOSE_DIR = os.getenv("DOCKER_COMPOSE_DIR", "").strip()
MAX_OUTPUT_CHARS = int(os.getenv("MAX_OUTPUT_CHARS", "20000"))

NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")


def q(value: str) -> str:
    return shlex.quote(value)


def validate_name(value: str, label: str = "name") -> str:
    if not NAME_RE.fullmatch(value):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value


def limit_output(output: str) -> str:
    if len(output) <= MAX_OUTPUT_CHARS:
        return output
    return output[:MAX_OUTPUT_CHARS] + (
        f"\n\n[Output truncated at {MAX_OUTPUT_CHARS} characters]"
    )


async def run_ssh(command: str, timeout: int = 60) -> str:
    known_hosts = (
        None if not VPS_KNOWN_HOSTS
        else os.path.expanduser(VPS_KNOWN_HOSTS)
    )

    async with asyncssh.connect(
        VPS_HOST,
        port=VPS_PORT,
        username=VPS_USER,
        client_keys=[VPS_SSH_KEY],
        known_hosts=known_hosts,
    ) as conn:
        result = await asyncio.wait_for(
            conn.run(command, check=False),
            timeout=timeout,
        )

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.exit_status != 0:
        text = stderr or stdout or "command failed"
        return limit_output(
            f"ERROR (exit {result.exit_status}): {text}"
        )

    return limit_output(stdout or "(no output)")


async def run_many(commands: list[tuple[str, str]], timeout: int = 90) -> str:
    parts = []
    for title, command in commands:
        parts.append(f"===== {title} =====")
        parts.append(await run_ssh(command, timeout=timeout))
    return "\n".join(parts)