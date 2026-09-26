import pytest

from tests.conftest import FakeMCP, make_runner
from vps_docker_mcp.infrastructure import ALLOWED_EXEC, register


def test_allowed_exec_contains_safe_commands():
    assert "whoami" in ALLOWED_EXEC
    assert "df" in ALLOWED_EXEC
    assert "uptime" in ALLOWED_EXEC


def test_allowed_exec_values_are_safe():
    for key, cmd in ALLOWED_EXEC.items():
        assert "rm" not in cmd
        assert ">" not in cmd
        assert "|" not in cmd


@pytest.mark.asyncio
async def test_diagnostic_command_allowed():
    mcp = FakeMCP()
    runner = make_runner("root")
    register(mcp, runner)
    await mcp.tools["diagnostic_command"](command="whoami")
    assert runner.call_args[0][0] == "whoami"


@pytest.mark.asyncio
async def test_diagnostic_command_blocked():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    with pytest.raises(ValueError):
        await mcp.tools["diagnostic_command"](command="rm -rf /")


@pytest.mark.asyncio
async def test_top_processes_clamps_limit():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["top_processes"](limit=9999)
    cmd = runner.call_args[0][0]
    assert "head -n 51" in cmd  # clamp(9999, 5, 50) + 1


@pytest.mark.asyncio
async def test_top_processes_min_clamp():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["top_processes"](limit=1)
    cmd = runner.call_args[0][0]
    assert "head -n 6" in cmd  # clamp(1, 5, 50) + 1


@pytest.mark.asyncio
async def test_journal_errors_clamps_hours():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["journal_errors"](hours=999, lines=10)
    cmd = runner.call_args[0][0]
    assert "72 hours ago" in cmd


@pytest.mark.asyncio
async def test_disk_large_files_clamp():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["disk_large_files"](path="/", min_mb=999999, limit=999)
    cmd = runner.call_args[0][0]
    assert "+10240M" in cmd
    assert "head -100" in cmd


@pytest.mark.asyncio
async def test_system_info_runs():
    mcp = FakeMCP()
    runner = make_runner("info")
    register(mcp, runner)
    result = await mcp.tools["system_info"]()
    assert result == "info"
    assert runner.called


@pytest.mark.asyncio
async def test_diagnose_vps_calls_run_multiple_times():
    mcp = FakeMCP()
    runner = make_runner("ok")
    register(mcp, runner)
    result = await mcp.tools["diagnose_vps"]()
    assert runner.call_count >= 7
    assert "SYSTEM" in result
    assert "DOCKER" in result
