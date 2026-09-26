import pytest

from tests.conftest import FakeMCP, make_runner
from vps_docker_mcp.database import _psql, register


def test_psql_builds_docker_exec():
    cmd = _psql("pgcontainer", "pguser", "mydb", "SELECT 1;")
    assert "docker exec" in cmd
    assert "pgcontainer" in cmd
    assert "pguser" in cmd
    assert "mydb" in cmd
    assert "SELECT 1;" in cmd


@pytest.mark.asyncio
async def test_postgres_backup_database_command():
    mcp = FakeMCP()
    runner = make_runner("Saved: /tmp/pg_backups/mydb_20260101_000000.dump")
    register(mcp, runner)
    await mcp.tools["postgres_backup_database"](database="mydb")
    cmd = runner.call_args[0][0]
    assert "pg_dump" in cmd
    assert "mydb" in cmd


@pytest.mark.asyncio
async def test_postgres_backup_database_invalid_name():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    with pytest.raises(ValueError):
        await mcp.tools["postgres_backup_database"](database="-bad")


@pytest.mark.asyncio
async def test_postgres_backup_all_command():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["postgres_backup_all"]()
    cmd = runner.call_args[0][0]
    assert "pg_dumpall" in cmd
    assert "gzip" in cmd


@pytest.mark.asyncio
async def test_postgres_list_backups_command():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["postgres_list_backups"]()
    cmd = runner.call_args[0][0]
    assert "ls -lht" in cmd


@pytest.mark.asyncio
async def test_postgres_download_backup_rejects_relative():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    with pytest.raises(ValueError):
        await mcp.tools["postgres_download_backup"](remote_path="relative/path")


@pytest.mark.asyncio
async def test_postgres_download_backup_rejects_dotdot():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    with pytest.raises(ValueError):
        await mcp.tools["postgres_download_backup"](remote_path="/safe/../evil")


@pytest.mark.asyncio
async def test_postgres_download_backup_rejects_directory():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    with pytest.raises(ValueError):
        await mcp.tools["postgres_download_backup"](remote_path="/tmp/pg_backups/")


@pytest.mark.asyncio
async def test_postgres_download_backup_calls_sftp(tmp_path, monkeypatch):
    from unittest.mock import AsyncMock

    sftp_mock = AsyncMock()
    monkeypatch.setattr("vps_docker_mcp.database.sftp_get", sftp_mock)
    monkeypatch.setattr("os.path.getsize", lambda _: 1024 * 1024 * 5)

    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    result = await mcp.tools["postgres_download_backup"](
        remote_path="/tmp/pg_backups/mydb.dump",
        local_dir=str(tmp_path),
    )
    sftp_mock.assert_awaited_once()
    assert "mydb.dump" in result
    assert "5.0 MB" in result


@pytest.mark.asyncio
async def test_postgres_stats_without_database():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["postgres_stats"]()
    cmd = runner.call_args[0][0]
    assert "pg_stat_database" in cmd
    assert "pg_stat_activity" in cmd


@pytest.mark.asyncio
async def test_postgres_stats_with_database_adds_table_query():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["postgres_stats"](database="mydb")
    cmd = runner.call_args[0][0]
    assert "pg_stat_user_tables" in cmd
    assert "mydb" in cmd
