import asyncio
import os

import asyncssh

from .config import (
    MAX_OUTPUT_CHARS,
    VPS_HOST,
    VPS_KNOWN_HOSTS,
    VPS_PORT,
    VPS_SSH_KEY,
    VPS_USER,
)
from .utils import limit_output


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
        return limit_output(f"ERROR (exit {result.exit_status}): {text}", MAX_OUTPUT_CHARS)

    return limit_output(stdout or "(no output)", MAX_OUTPUT_CHARS)


async def run_many(commands: list[tuple[str, str]], timeout: int = 90) -> str:
    parts = []
    for title, command in commands:
        parts.append(f"===== {title} =====")
        parts.append(await run_ssh(command, timeout=timeout))
    return "\n".join(parts)
