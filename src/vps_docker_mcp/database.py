import os
from collections.abc import Awaitable, Callable

from mcp.server.fastmcp import FastMCP

from .config import POSTGRES_BACKUP_DIR, POSTGRES_CONTAINER
from .ssh import sftp_get
from .utils import q, validate_name

Runner = Callable[[str, int], Awaitable[str]]

_DB_STATS_SQL = (
    "SELECT datname AS database, "
    "pg_size_pretty(pg_database_size(datname)) AS size, "
    "numbackends AS connections "
    "FROM pg_stat_database "
    "WHERE datistemplate = false "
    "ORDER BY pg_database_size(datname) DESC;"
)

_ACTIVITY_SQL = (
    "SELECT datname AS database, usename AS user, state, "
    "now() - query_start AS duration, left(query, 80) AS query "
    "FROM pg_stat_activity "
    "WHERE state IS NOT NULL "
    "ORDER BY duration DESC NULLS LAST "
    "LIMIT 20;"
)

_TABLE_STATS_SQL = (
    "SELECT schemaname AS schema, tablename AS table, "
    "pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size, "
    "n_live_tup AS live_rows, n_dead_tup AS dead_rows "
    "FROM pg_stat_user_tables "
    "ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC "
    "LIMIT 20;"
)


def _psql(container: str, database: str, sql: str) -> str:
    return (
        f"docker exec -u postgres {q(container)} "
        f"psql -U postgres -d {q(database)} -c {q(sql)}"
    )


def register(mcp: FastMCP, run: Runner) -> None:

    @mcp.tool()
    async def postgres_backup_database(
        database: str,
        container: str = POSTGRES_CONTAINER,
        backup_dir: str = POSTGRES_BACKUP_DIR,
    ) -> str:
        """Backup a single PostgreSQL database to a custom-format dump file.

        Creates <backup_dir>/<database>_YYYYMMDD_HHMMSS.dump on the server.
        Restore with: pg_restore -d <target_db> <file>
        """
        validate_name(container, "container")
        validate_name(database, "database")
        cmd = (
            f"set -e\n"
            f"mkdir -p {q(backup_dir)}\n"
            f"OUTFILE={q(backup_dir)}/{database}_$(date +%Y%m%d_%H%M%S).dump\n"
            f'docker exec -u postgres {q(container)} pg_dump -Fc {q(database)} > "$OUTFILE"\n'
            f'echo "Saved: $OUTFILE" && du -sh "$OUTFILE"'
        )
        return await run(cmd, 600)

    @mcp.tool()
    async def postgres_backup_all(
        container: str = POSTGRES_CONTAINER,
        backup_dir: str = POSTGRES_BACKUP_DIR,
    ) -> str:
        """Backup all PostgreSQL databases using pg_dumpall, compressed with gzip.

        Creates <backup_dir>/all_databases_YYYYMMDD_HHMMSS.sql.gz on the server.
        Restore with: gunzip -c <file> | psql -U postgres
        """
        validate_name(container, "container")
        cmd = (
            f"set -e\n"
            f"mkdir -p {q(backup_dir)}\n"
            f"OUTFILE={q(backup_dir)}/all_databases_$(date +%Y%m%d_%H%M%S).sql.gz\n"
            f"docker exec -u postgres {q(container)} pg_dumpall | gzip > \"$OUTFILE\"\n"
            f'echo "Saved: $OUTFILE" && du -sh "$OUTFILE"'
        )
        return await run(cmd, 900)

    @mcp.tool()
    async def postgres_list_backups(
        backup_dir: str = POSTGRES_BACKUP_DIR,
    ) -> str:
        """List PostgreSQL backup files on the server, newest first."""
        return await run(
            f"ls -lht {q(backup_dir)} 2>/dev/null || echo 'Directory empty or not found'",
            30,
        )

    @mcp.tool()
    async def postgres_download_backup(
        remote_path: str,
        local_dir: str = "~/Downloads",
    ) -> str:
        """Download a PostgreSQL backup file from the server to a local directory.

        remote_path must be an absolute path on the server (e.g. from postgres_list_backups).
        """
        if not remote_path.startswith("/") or ".." in remote_path.split("/"):
            raise ValueError("remote_path must be an absolute path with no '..' components")
        local_dir_expanded = os.path.expanduser(local_dir)
        os.makedirs(local_dir_expanded, exist_ok=True)
        filename = os.path.basename(remote_path)
        if not filename:
            raise ValueError("remote_path must point to a file, not a directory")
        local_path = os.path.join(local_dir_expanded, filename)
        await sftp_get(remote_path, local_path)
        size = os.path.getsize(local_path)
        return f"Downloaded: {local_path} ({size / 1024 / 1024:.1f} MB)"

    @mcp.tool()
    async def postgres_stats(
        container: str = POSTGRES_CONTAINER,
        database: str = "",
    ) -> str:
        """Show PostgreSQL statistics: database sizes, active queries, and optionally table stats.

        If database is specified, also shows the top 20 tables by size for that database.
        """
        validate_name(container, "container")
        cmds = [
            "echo '=== DATABASE SIZES AND CONNECTIONS ===' && "
            + _psql(container, "postgres", _DB_STATS_SQL),
            "echo '=== ACTIVE QUERIES ===' && "
            + _psql(container, "postgres", _ACTIVITY_SQL),
        ]
        if database:
            validate_name(database, "database")
            cmds.append(
                f"echo '=== TOP TABLES IN {database} ===' && "
                + _psql(container, database, _TABLE_STATS_SQL)
            )
        return await run(" && ".join(cmds), 60)
