from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vps_docker_mcp.ssh import run_ssh, sftp_get


def _make_ssh_mock(stdout="output", stderr="", exit_status=0):
    mock_result = MagicMock()
    mock_result.stdout = stdout
    mock_result.stderr = stderr
    mock_result.exit_status = exit_status

    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=mock_result)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_connect = MagicMock(return_value=mock_conn)
    return mock_connect, mock_conn


@pytest.mark.asyncio
async def test_run_ssh_success():
    mock_connect, mock_conn = _make_ssh_mock(stdout="hello")
    with patch("vps_docker_mcp.ssh.asyncssh.connect", mock_connect):
        result = await run_ssh("echo hello", timeout=10)
    assert result == "hello"
    mock_conn.run.assert_awaited_once_with("echo hello", check=False)


@pytest.mark.asyncio
async def test_run_ssh_uses_config_credentials():
    mock_connect, _ = _make_ssh_mock()
    with patch("vps_docker_mcp.ssh.asyncssh.connect", mock_connect):
        await run_ssh("ls", timeout=10)
    call_kwargs = mock_connect.call_args
    assert call_kwargs is not None
    assert "username" in call_kwargs.kwargs or len(call_kwargs.args) >= 2


@pytest.mark.asyncio
async def test_run_ssh_nonzero_exit_returns_error():
    mock_connect, _ = _make_ssh_mock(stderr="permission denied", exit_status=1)
    with patch("vps_docker_mcp.ssh.asyncssh.connect", mock_connect):
        result = await run_ssh("ls /root", timeout=10)
    assert "ERROR" in result
    assert "permission denied" in result


@pytest.mark.asyncio
async def test_run_ssh_nonzero_exit_falls_back_to_stdout():
    mock_connect, _ = _make_ssh_mock(stdout="stdout msg", stderr="", exit_status=1)
    with patch("vps_docker_mcp.ssh.asyncssh.connect", mock_connect):
        result = await run_ssh("bad", timeout=10)
    assert "ERROR" in result
    assert "stdout msg" in result


@pytest.mark.asyncio
async def test_run_ssh_empty_output():
    mock_connect, _ = _make_ssh_mock(stdout="", stderr="", exit_status=0)
    with patch("vps_docker_mcp.ssh.asyncssh.connect", mock_connect):
        result = await run_ssh("true", timeout=10)
    assert result == "(no output)"


@pytest.mark.asyncio
async def test_run_ssh_truncates_long_output():
    long_output = "x" * 100_000
    mock_connect, _ = _make_ssh_mock(stdout=long_output)
    with patch("vps_docker_mcp.ssh.asyncssh.connect", mock_connect):
        result = await run_ssh("big", timeout=10)
    assert len(result) < len(long_output)
    assert "truncated" in result.lower()


@pytest.mark.asyncio
async def test_sftp_get_calls_sftp_client(tmp_path):
    mock_sftp = AsyncMock()
    mock_sftp.__aenter__ = AsyncMock(return_value=mock_sftp)
    mock_sftp.__aexit__ = AsyncMock(return_value=False)

    mock_conn = AsyncMock()
    mock_conn.start_sftp_client = MagicMock(return_value=mock_sftp)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_connect = MagicMock(return_value=mock_conn)

    local = str(tmp_path / "file.dump")
    with patch("vps_docker_mcp.ssh.asyncssh.connect", mock_connect):
        await sftp_get("/remote/file.dump", local)

    mock_sftp.get.assert_awaited_once_with("/remote/file.dump", local)
