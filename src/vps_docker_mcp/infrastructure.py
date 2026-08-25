from collections.abc import Awaitable, Callable

from mcp.server.fastmcp import FastMCP

from .utils import clamp, q, validate_name

Runner = Callable[[str, int], Awaitable[str]]

ALLOWED_EXEC = {
    "pwd": "pwd",
    "whoami": "whoami",
    "date": "date",
    "df": "df -h",
    "free": "free -h",
    "uptime": "uptime",
    "docker_version": "docker version",
    "docker_info": "docker info",
}


async def _run_many(
    run: Runner,
    commands: list[tuple[str, str]],
    timeout: int = 90,
) -> str:
    parts = []
    for title, command in commands:
        parts.append(f"===== {title} =====")
        parts.append(await run(command, timeout))
    return "\n".join(parts)


def register(mcp: FastMCP, run: Runner) -> None:
    @mcp.tool()
    async def system_info() -> str:
        """Show VPS uptime, OS, CPU, memory, swap, load and kernel information."""
        command = r"""
set +e
printf '%s\n' '=== HOST ==='
hostname
printf '%s\n' '=== OS ==='
cat /etc/os-release 2>/dev/null | grep -E '^(PRETTY_NAME|VERSION_ID)='
printf '%s\n' '=== KERNEL ==='
uname -a
printf '%s\n' '=== UPTIME ==='
uptime
printf '%s\n' '=== LOAD ==='
cat /proc/loadavg
printf '%s\n' '=== CPU ==='
nproc
lscpu 2>/dev/null | grep -E '^(CPU\(s\)|Model name|Architecture):' | head -5
printf '%s\n' '=== MEMORY ==='
free -h
printf '%s\n' '=== SWAP ==='
swapon --show
"""
        return await run(command, 60)

    @mcp.tool()
    async def disk_usage() -> str:
        """Show filesystem space and inode usage."""
        command = r"""
printf '%s\n' '=== FILESYSTEM SPACE ==='
df -hT
printf '%s\n' '=== INODES ==='
df -ih
"""
        return await run(command, 60)

    @mcp.tool()
    async def top_processes(limit: int = 15) -> str:
        """Show processes consuming the most CPU and memory."""
        n = clamp(limit, 5, 50)
        return await run(
            f"ps -eo pid,ppid,user,%cpu,%mem,rss,stat,etime,comm "
            f"--sort=-%cpu | head -n {n + 1}",
            60,
        )

    @mcp.tool()
    async def network_info() -> str:
        """Show network interfaces, routes and listening TCP/UDP ports."""
        command = r"""
set +e
printf '%s\n' '=== INTERFACES ==='
ip -brief address 2>/dev/null || ip addr
printf '%s\n' '=== ROUTES ==='
ip route 2>/dev/null
printf '%s\n' '=== LISTENING PORTS ==='
ss -lntup 2>/dev/null || ss -lnt
"""
        return await run(command, 60)

    @mcp.tool()
    async def systemd_failed() -> str:
        """Show failed systemd services."""
        return await run("systemctl --failed --no-pager 2>/dev/null || true", 60)

    @mcp.tool()
    async def journal_errors(hours: int = 6, lines: int = 100) -> str:
        """Show recent system journal errors."""
        return await run(
            "journalctl --since "
            + q(f"{clamp(hours, 1, 72)} hours ago")
            + f" -p err..alert -n {clamp(lines, 10, 500)} --no-pager 2>/dev/null || true",
            90,
        )

    @mcp.tool()
    async def diagnose_vps() -> str:
        """Run a compact VPS health check covering resources, disk, systemd and Docker."""
        commands = [
            ("SYSTEM", "hostname; uptime; free -h"),
            ("DISK", "df -hT /; df -ih /"),
            ("TOP CPU", "ps -eo pid,%cpu,%mem,rss,stat,comm --sort=-%cpu | head -n 11"),
            ("SYSTEMD FAILED", "systemctl --failed --no-pager 2>/dev/null || true"),
            ("DOCKER", "docker info --format 'ServerVersion={{.ServerVersion}} Containers={{.Containers}} Running={{.ContainersRunning}} Images={{.Images}}' 2>&1"),
            ("DOCKER CONTAINERS", "docker ps -a --format 'table {{.Names}}\\t{{.Status}}\\t{{.Image}}'"),
            ("DOCKER DISK", "docker system df"),
        ]
        return await _run_many(run, commands, timeout=120)

    @mcp.tool()
    async def diagnostic_command(command: str) -> str:
        """Run one of a small predefined set of read-only diagnostic commands."""
        if command not in ALLOWED_EXEC:
            allowed = ", ".join(sorted(ALLOWED_EXEC))
            raise ValueError(f"Command not allowed. Available: {allowed}")
        return await run(ALLOWED_EXEC[command], 90)
