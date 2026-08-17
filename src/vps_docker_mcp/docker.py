from mcp.server.fastmcp import FastMCP

from .ssh import DOCKER_COMPOSE_DIR, q, run_ssh, validate_name


def require_compose_dir() -> str:
    if not DOCKER_COMPOSE_DIR:
        raise ValueError("DOCKER_COMPOSE_DIR is not configured")
    return DOCKER_COMPOSE_DIR


def validate_service(service: str) -> str:
    return validate_name(service, "service")


def register(mcp: FastMCP) -> None:
    # -------------------------------------------------------------------------
    # Read-only
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def docker_ps(all_containers: bool = False) -> str:
        """List Docker containers. Set all_containers=true to include stopped containers."""
        return await run_ssh(
            "docker ps --all --format "
            "'table {{.Names}}\\t{{.Status}}\\t{{.Image}}\\t{{.Ports}}'"
            if all_containers
            else
            "docker ps --format "
            "'table {{.Names}}\\t{{.Status}}\\t{{.Image}}\\t{{.Ports}}'"
        )

    @mcp.tool()
    async def docker_logs(container: str, tail: int = 100) -> str:
        """Show recent logs from a Docker container."""
        validate_name(container, "container")
        tail = max(1, min(int(tail), 2000))
        return await run_ssh(
            f"docker logs --tail {tail} {q(container)} 2>&1",
            timeout=120,
        )

    @mcp.tool()
    async def docker_inspect(container: str) -> str:
        """Inspect a Docker container."""
        validate_name(container, "container")
        return await run_ssh(
            f"docker inspect {q(container)}",
            timeout=90,
        )

    @mcp.tool()
    async def docker_stats() -> str:
        """Show current CPU, memory, network and block I/O usage of containers."""
        return await run_ssh(
            "docker stats --no-stream "
            "--format 'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}\\t{{.MemPerc}}\\t{{.NetIO}}\\t{{.BlockIO}}'",
            timeout=90,
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
        return await run_ssh(command)

    @mcp.tool()
    async def docker_images() -> str:
        """List Docker images."""
        return await run_ssh(
            "docker images --format "
            "'table {{.Repository}}\\t{{.Tag}}\\t{{.ID}}\\t{{.CreatedSince}}\\t{{.Size}}'"
        )

    @mcp.tool()
    async def docker_volumes() -> str:
        """List Docker volumes."""
        return await run_ssh("docker volume ls")

    @mcp.tool()
    async def docker_networks() -> str:
        """List Docker networks."""
        return await run_ssh("docker network ls")

    @mcp.tool()
    async def docker_disk_usage() -> str:
        """Show Docker disk usage."""
        return await run_ssh("docker system df")

    # -------------------------------------------------------------------------
    # Mutating
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def docker_restart(container: str) -> str:
        """Restart a Docker container. This changes server state."""
        validate_name(container, "container")
        return await run_ssh(f"docker restart {q(container)}")

    @mcp.tool()
    async def docker_start(container: str) -> str:
        """Start a Docker container. This changes server state."""
        validate_name(container, "container")
        return await run_ssh(f"docker start {q(container)}")

    @mcp.tool()
    async def docker_stop(container: str) -> str:
        """Stop a Docker container. This changes server state."""
        validate_name(container, "container")
        return await run_ssh(f"docker stop {q(container)}")

    # -------------------------------------------------------------------------
    # Compose
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def docker_compose_ps() -> str:
        """Show Docker Compose services."""
        directory = require_compose_dir()
        return await run_ssh(
            f"cd {q(directory)} && docker compose ps",
            timeout=90,
        )

    @mcp.tool()
    async def docker_compose_config() -> str:
        """Render and validate the Docker Compose configuration."""
        directory = require_compose_dir()
        return await run_ssh(
            f"cd {q(directory)} && docker compose config",
            timeout=90,
        )

    @mcp.tool()
    async def docker_compose_logs(service: str = "", tail: int = 100) -> str:
        """Show Docker Compose logs, optionally for one service."""
        directory = require_compose_dir()
        tail = max(1, min(int(tail), 2000))
        service_arg = ""
        if service:
            validate_service(service)
            service_arg = f" {q(service)}"
        return await run_ssh(
            f"cd {q(directory)} && docker compose logs --tail {tail}{service_arg}",
            timeout=120,
        )

    @mcp.tool()
    async def docker_compose_restart(service: str = "") -> str:
        """Restart Docker Compose services. This changes server state."""
        directory = require_compose_dir()
        service_arg = ""
        if service:
            validate_service(service)
            service_arg = f" {q(service)}"
        return await run_ssh(
            f"cd {q(directory)} && docker compose restart{service_arg}",
            timeout=120,
        )

    @mcp.tool()
    async def docker_compose_pull() -> str:
        """Pull Docker Compose images. This changes local Docker image state."""
        directory = require_compose_dir()
        return await run_ssh(
            f"cd {q(directory)} && docker compose pull",
            timeout=600,
        )

    @mcp.tool()
    async def docker_compose_up() -> str:
        """Start/update the Docker Compose stack with detached mode. This changes server state."""
        directory = require_compose_dir()
        return await run_ssh(
            f"cd {q(directory)} && docker compose up -d",
            timeout=600,
        )
