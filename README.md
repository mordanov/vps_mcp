# VPS Docker MCP — Advanced

MCP server for Claude Code that provides safe VPS diagnostics and Docker/Docker Compose management over SSH.

## Architecture

```text
Claude Code
    |
    | MCP / stdio
    v
Local Python MCP server
    |
    | SSH / AsyncSSH
    v
VPS
    |
    +-- systemd
    +-- Docker
    +-- Docker Compose
```

The MCP server runs locally. Nothing needs to listen on the VPS.

### Module layout

```text
src/vps_docker_mcp/
├── server.py          # MCP instance, wires modules together
├── ssh.py             # SSH config, run_ssh/run_many helpers
├── docker.py          # Docker and Docker Compose tools
└── infrastructure.py  # VPS diagnostics tools
```

## Security model

This project intentionally does **not** expose arbitrary shell execution.

There is no:

```text
ssh(command)
execute(command)
bash(command)
```

Instead, every operation is a predefined MCP tool.

Arguments such as container and service names are validated with a restrictive allow-list pattern and shell-quoted before being inserted into commands.

SSH host key checking is enabled through `VPS_KNOWN_HOSTS`.

Use a dedicated non-root SSH account, e.g. `deploy`, with Docker access.

## Requirements

- Python 3.11+
- `uv`
- SSH access
- Docker on VPS
- Docker Compose v2 if Compose tools are used
- `deploy` user with permission to run Docker

## Installation

```bash
uv sync
```

Configure:

```bash
cp .env.example .env
```

Example:

```env
VPS_HOST=YOUR_VPS_IP
VPS_PORT=22
VPS_USER=deploy
VPS_SSH_KEY=~/.ssh/vps_mcp
VPS_KNOWN_HOSTS=~/.ssh/known_hosts
DOCKER_COMPOSE_DIR=/opt/news-bot
MAX_OUTPUT_CHARS=20000
```

Test SSH independently:

```bash
ssh -i ~/.ssh/vps_mcp deploy@YOUR_VPS_IP docker ps
```

Test MCP:

```bash
uv run vps-docker-mcp
```

It will wait for MCP stdio input. That is expected.

## Claude Code configuration

Copy `.mcp.json.example` to the project-level `.mcp.json` used by Claude Code and replace the absolute path.

Example:

```json
{
  "mcpServers": {
    "vps-docker": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "/home/me/projects/vps-docker-mcp-advanced",
        "run",
        "vps-docker-mcp"
      ]
    }
  }
}
```

Then start/restart Claude Code and inspect MCP status with:

```text
/mcp
```

Depending on the Claude Code version, MCP servers can also be managed with the Claude Code CLI.

## Tool groups

### VPS diagnostics

- `system_info`
- `disk_usage`
- `top_processes`
- `network_info`
- `systemd_failed`
- `journal_errors`
- `diagnose_vps`

### Docker read-only

- `docker_ps`
- `docker_logs`
- `docker_inspect`
- `docker_stats`
- `docker_health`
- `docker_images`
- `docker_volumes`
- `docker_networks`
- `docker_disk_usage`

### Docker mutations

- `docker_restart`
- `docker_start`
- `docker_stop`

### Docker Compose

Read-only:

- `docker_compose_ps`
- `docker_compose_config`
- `docker_compose_logs`

Mutating:

- `docker_compose_restart`
- `docker_compose_pull`
- `docker_compose_up`

### Restricted diagnostics

`diagnostic_command` only permits a fixed list:

- pwd
- whoami
- date
- df
- free
- uptime
- docker_version
- docker_info

It does not accept arbitrary shell syntax.

## Example Claude Code requests

```text
Check the VPS health.
```

Claude can use:

```text
diagnose_vps
```

For a broken container:

```text
Find out why news-bot is unhealthy.
```

A useful diagnostic sequence is:

```text
docker_health
docker_ps
docker_logs
docker_stats
docker_inspect
```

For a general resource problem:

```text
Check whether the VPS is running out of RAM or disk space.
```

Claude can inspect:

```text
system_info
disk_usage
top_processes
docker_stats
docker_disk_usage
```

Then:

```text
Restart news-bot if the diagnosis indicates that a restart is appropriate.
```

The restart operation is a separate mutating tool.

## Important production recommendation

Keep Claude Code's own permission/approval mechanism enabled for mutating operations.

The MCP server intentionally labels mutating tools in their descriptions, but MCP itself should not be treated as an authorization boundary.

For a production VPS, do not add arbitrary shell execution unless you deliberately accept the risk.

## Future improvements

Good next additions would be:

- application-specific health checks
- Docker container restart-loop detection
- OOM detection
- disk growth detection
- systemd service restart tools
- configurable allow-list of Compose projects
- audit logging
- command execution timeouts per tool
- separate read-only and write SSH credentials
