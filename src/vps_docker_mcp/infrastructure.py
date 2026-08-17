from mcp.server.fastmcp import FastMCP

from .ssh import q, run_ssh, run_many, validate_name

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


def register(mcp: FastMCP) -> None:
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
        return await run_ssh(command)

    @mcp.tool()
    async def disk_usage() -> str:
        """Show filesystem space and inode usage."""
        command = r"""
printf '%s\n' '=== FILESYSTEM SPACE ==='
df -hT
printf '%s\n' '=== INODES ==='
df -ih
"""
        return await run_ssh(command)

    @mcp.tool()
    async def top_processes(limit: int = 15) -> str:
        """Show processes consuming the most CPU and memory."""
        limit = max(5, min(int(limit), 50))
        return await run_ssh(
            f"ps -eo pid,ppid,user,%cpu,%mem,rss,stat,etime,comm "
            f"--sort=-%cpu | head -n {limit + 1}"
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
        return await run_ssh(command)

    @mcp.tool()
    async def systemd_failed() -> str:
        """Show failed systemd services."""
        return await run_ssh(
            "systemctl --failed --no-pager 2>/dev/null || true"
        )

    @mcp.tool()
    async def journal_errors(hours: int = 6, lines: int = 100) -> str:
        """Show recent system journal errors."""
        hours = max(1, min(int(hours), 72))
        lines = max(10, min(int(lines), 500))
        return await run_ssh(
            "journalctl --since "
            + q(f"{hours} hours ago")
            + f" -p err..alert -n {lines} --no-pager 2>/dev/null || true",
            timeout=90,
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
        return await run_many(commands, timeout=120)

    @mcp.tool()
    async def diagnostic_command(command: str) -> str:
        """Run one of a small predefined set of read-only diagnostic commands."""
        if command not in ALLOWED_EXEC:
            allowed = ", ".join(sorted(ALLOWED_EXEC))
            raise ValueError(f"Command not allowed. Available: {allowed}")
        return await run_ssh(ALLOWED_EXEC[command], timeout=90)