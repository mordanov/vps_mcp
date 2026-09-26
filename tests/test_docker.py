import pytest

from tests.conftest import FakeMCP, make_runner
from vps_docker_mcp.docker import _optional_service_arg, register


def test_optional_service_arg_empty():
    assert _optional_service_arg("") == ""


def test_optional_service_arg_valid():
    result = _optional_service_arg("web")
    assert "web" in result
    assert result.startswith(" ")


def test_optional_service_arg_invalid():
    with pytest.raises(ValueError):
        _optional_service_arg("bad;cmd")


@pytest.mark.asyncio
async def test_docker_ps_default():
    mcp = FakeMCP()
    runner = make_runner("containers")
    register(mcp, runner)
    result = await mcp.tools["docker_ps"]()
    assert result == "containers"
    cmd = runner.call_args[0][0]
    assert "docker ps" in cmd
    assert "--all" not in cmd


@pytest.mark.asyncio
async def test_docker_ps_all():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["docker_ps"](all_containers=True)
    cmd = runner.call_args[0][0]
    assert "--all" in cmd


@pytest.mark.asyncio
async def test_docker_logs_clamps_tail():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["docker_logs"](container="web", tail=99999)
    cmd = runner.call_args[0][0]
    assert "--tail 2000" in cmd


@pytest.mark.asyncio
async def test_docker_logs_invalid_container():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    with pytest.raises(ValueError):
        await mcp.tools["docker_logs"](container="-bad")


@pytest.mark.asyncio
async def test_docker_inspect_command():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["docker_inspect"](container="myapp")
    cmd = runner.call_args[0][0]
    assert "docker inspect" in cmd
    assert "myapp" in cmd


@pytest.mark.asyncio
async def test_docker_restart_validates_name():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    with pytest.raises(ValueError):
        await mcp.tools["docker_restart"](container="bad name!")


@pytest.mark.asyncio
async def test_docker_prune_images_flag():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["docker_prune_images"](all_unused=True)
    cmd = runner.call_args[0][0]
    assert "--all" in cmd


@pytest.mark.asyncio
async def test_docker_compose_ps_requires_dir():
    mcp = FakeMCP()
    runner = make_runner()
    # DOCKER_COMPOSE_DIR defaults to empty string in test env
    import vps_docker_mcp.docker as docker_mod

    original = docker_mod.DOCKER_COMPOSE_DIR
    docker_mod.DOCKER_COMPOSE_DIR = ""
    try:
        register(mcp, runner)
        with pytest.raises(ValueError):
            await mcp.tools["docker_compose_ps"]()
    finally:
        docker_mod.DOCKER_COMPOSE_DIR = original


@pytest.mark.asyncio
async def test_docker_compose_logs_clamps_tail(monkeypatch):
    import vps_docker_mcp.docker as docker_mod

    monkeypatch.setattr(docker_mod, "DOCKER_COMPOSE_DIR", "/app")
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["docker_compose_logs"](tail=99999)
    cmd = runner.call_args[0][0]
    assert "--tail 2000" in cmd
