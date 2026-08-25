from collections.abc import Awaitable, Callable

from mcp.server.fastmcp import FastMCP

from .config import DOCKER_COMPOSE_DIR
from .utils import clamp, q, validate_name

Runner = Callable[[str, int], Awaitable[str]]


def _require_compose_dir() -> str:
    if not DOCKER_COMPOSE_DIR:
        raise ValueError("DOCKER_COMPOSE_DIR is not configured")
    return DOCKER_COMPOSE_DIR


def _optional_service_arg(service: str) -> str:
    if not service:
        return ""
    validate_name(service, "service")
    return f" {q(service)}"


def register(mcp: FastMCP, run: Runner) -> None:
    # -------------------------------------------------------------------------
    # Read-only
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def docker_ps(all_containers: bool = False) -> str:
        """List Docker containers. Set all_containers=true to include stopped containers."""
        return await run(
            "docker ps --all --format "
            "'table {{.Names}}\\t{{.Status}}\\t{{.Image}}\\t{{.Ports}}'"
            if all_containers
            else
            "docker ps --format "
            "'table {{.Names}}\\t{{.Status}}\\t{{.Image}}\\t{{.Ports}}'",
            60,
        )

    @mcp.tool()
    async def docker_logs(container: str, tail: int = 100) -> str:
        """Show recent logs from a Docker container."""
        validate_name(container, "container")
        return await run(
            f"docker logs --tail {clamp(tail, 1, 2000)} {q(container)} 2>&1",
            120,
        )

    @mcp.tool()
    async def docker_inspect(container: str) -> str:
        """Inspect a Docker container."""
        validate_name(container, "container")
        return await run(f"docker inspect {q(container)}", 90)

    @mcp.tool()
    async def docker_stats() -> str:
        """Show current CPU, memory, network and block I/O usage of containers."""
        return await run(
            "docker stats --no-stream "
            "--format 'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}\\t{{.MemPerc}}\\t{{.NetIO}}\\t{{.BlockIO}}'",
            90,
        )

    @mcp.tool()
    async def docker_health(container: str) -> str:
        """Show container state, restart count and health status."""
        validate_name(container, "container")
        command = (
            "docker inspect --format "
            "'Name={{.Name}} Status={{.State.Status}} "
            "Running={{.State.Running}} ExitCode={{.State.ExitCode}} "
            "RestartCount={{.RestartCount}} "
            "Started={{.State.StartedAt}} Finished={{.State.FinishedAt}} "
            "Health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "
            + q(container)
        )
        return await run(command, 60)

    @mcp.tool()
    async def docker_images() -> str:
        """List Docker images."""
        return await run(
            "docker images --format "
            "'table {{.Repository}}\\t{{.Tag}}\\t{{.ID}}\\t{{.CreatedSince}}\\t{{.Size}}'",
            60,
        )

    @mcp.tool()
    async def docker_volumes() -> str:
        """List Docker volumes."""
        return await run("docker volume ls", 60)

    @mcp.tool()
    async def docker_networks() -> str:
        """List Docker networks."""
        return await run("docker network ls", 60)

    @mcp.tool()
    async def docker_disk_usage() -> str:
        """Show Docker disk usage."""
        return await run("docker system df", 60)

    # -------------------------------------------------------------------------
    # Mutating
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def docker_restart(container: str) -> str:
        """Restart a Docker container. This changes server state."""
        validate_name(container, "container")
        return await run(f"docker restart {q(container)}", 60)

    @mcp.tool()
    async def docker_start(container: str) -> str:
        """Start a Docker container. This changes server state."""
        validate_name(container, "container")
        return await run(f"docker start {q(container)}", 60)

    @mcp.tool()
    async def docker_stop(container: str) -> str:
        """Stop a Docker container. This changes server state."""
        validate_name(container, "container")
        return await run(f"docker stop {q(container)}", 60)

    @mcp.tool()
    async def docker_prune_images(all_unused: bool = False) -> str:
        """Remove unused Docker images to free disk space. This changes server state.

        By default removes only dangling images (untagged and not referenced by any container).
        Set all_unused=true to also remove images that exist but are not used by any container.
        """
        flag = " --all" if all_unused else ""
        return await run(f"docker image prune --force{flag}", 120)

    # -------------------------------------------------------------------------
    # Compose
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def docker_compose_ps() -> str:
        """Show Docker Compose services."""
        directory = _require_compose_dir()
        return await run(f"cd {q(directory)} && docker compose ps", 90)

    @mcp.tool()
    async def docker_compose_config() -> str:
        """Render and validate the Docker Compose configuration."""
        directory = _require_compose_dir()
        return await run(f"cd {q(directory)} && docker compose config", 90)

    @mcp.tool()
    async def docker_compose_logs(service: str = "", tail: int = 100) -> str:
        """Show Docker Compose logs, optionally for one service."""
        directory = _require_compose_dir()
        service_arg = _optional_service_arg(service)
        return await run(
            f"cd {q(directory)} && docker compose logs --tail {clamp(tail, 1, 2000)}{service_arg}",
            120,
        )

    @mcp.tool()
    async def docker_compose_restart(service: str = "") -> str:
        """Restart Docker Compose services. This changes server state."""
        directory = _require_compose_dir()
        service_arg = _optional_service_arg(service)
        return await run(
            f"cd {q(directory)} && docker compose restart{service_arg}",
            120,
        )

    @mcp.tool()
    async def docker_compose_pull() -> str:
        """Pull Docker Compose images. This changes local Docker image state."""
        directory = _require_compose_dir()
        return await run(f"cd {q(directory)} && docker compose pull", 600)

    @mcp.tool()
    async def docker_compose_up() -> str:
        """Start/update the Docker Compose stack with detached mode. This changes server state."""
        directory = _require_compose_dir()
        return await run(f"cd {q(directory)} && docker compose up -d", 600)
