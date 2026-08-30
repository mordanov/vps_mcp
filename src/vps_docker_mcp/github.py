import re
from collections.abc import Awaitable, Callable

from mcp.server.fastmcp import FastMCP

from .config import GITHUB_REPO
from .utils import clamp, q

Runner = Callable[[str, int], Awaitable[str]]

_REPO_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}/[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$")
_RUN_ID_RE = re.compile(r"^\d{1,20}$")
_WORKFLOW_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 _.-]{0,127}$")


def _repo(repo: str) -> str:
    """Resolve and validate repo, falling back to GITHUB_REPO env var."""
    r = repo.strip() or GITHUB_REPO
    if not r:
        raise ValueError("repo is required (or set GITHUB_REPO in .env)")
    if not _REPO_RE.fullmatch(r):
        raise ValueError(f"Invalid repo: {r!r}. Expected owner/repo format.")
    return r


def _run_id(run_id: str) -> str:
    if not _RUN_ID_RE.fullmatch(run_id.strip()):
        raise ValueError(f"Invalid run_id: {run_id!r}. Must be numeric.")
    return run_id.strip()


def _workflow(workflow: str) -> str:
    if not _WORKFLOW_RE.fullmatch(workflow):
        raise ValueError(f"Invalid workflow: {workflow!r}")
    return workflow


def register(mcp: FastMCP, run: Runner) -> None:
    # -------------------------------------------------------------------------
    # Read-only
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def gh_workflow_list(repo: str = "") -> str:
        """List GitHub Actions workflows for a repository.

        repo: owner/repo (e.g. acme/api). Falls back to GITHUB_REPO env var.
        """
        return await run(f"gh workflow list --repo {q(_repo(repo))}", 60)

    @mcp.tool()
    async def gh_run_list(
        repo: str = "",
        workflow: str = "",
        limit: int = 20,
        status: str = "",
    ) -> str:
        """List recent GitHub Actions workflow runs.

        repo:     owner/repo. Falls back to GITHUB_REPO env var.
        workflow: filter by workflow filename or name (optional).
        limit:    number of runs to return (1-100, default 20).
        status:   filter by status: queued, in_progress, completed, failure, success,
                  cancelled, skipped, waiting (optional).
        """
        r = _repo(repo)
        args = f"--repo {q(r)} --limit {clamp(limit, 1, 100)}"
        if workflow:
            args += f" --workflow {q(_workflow(workflow))}"
        valid_statuses = {
            "queued", "in_progress", "completed", "failure",
            "success", "cancelled", "skipped", "waiting",
        }
        if status:
            if status not in valid_statuses:
                raise ValueError(f"Invalid status {status!r}. Choose from: {', '.join(sorted(valid_statuses))}")
            args += f" --status {q(status)}"
        return await run(f"gh run list {args}", 60)

    @mcp.tool()
    async def gh_run_view(repo: str = "", run_id: str = "") -> str:
        """Show summary and job status for a GitHub Actions workflow run.

        repo:   owner/repo. Falls back to GITHUB_REPO env var.
        run_id: numeric run ID (from gh_run_list).
        """
        r = _repo(repo)
        if not run_id.strip():
            raise ValueError("run_id is required")
        return await run(
            f"gh run view {q(_run_id(run_id))} --repo {q(r)}",
            60,
        )

    @mcp.tool()
    async def gh_run_logs(
        repo: str = "",
        run_id: str = "",
        failed_only: bool = False,
    ) -> str:
        """Fetch logs for a GitHub Actions workflow run.

        repo:        owner/repo. Falls back to GITHUB_REPO env var.
        run_id:      numeric run ID (from gh_run_list).
        failed_only: set true to return only failed step logs (much shorter).
        """
        r = _repo(repo)
        if not run_id.strip():
            raise ValueError("run_id is required")
        flag = " --failed" if failed_only else ""
        return await run(
            f"gh run view {q(_run_id(run_id))} --repo {q(r)} --log{flag}",
            120,
        )

    @mcp.tool()
    async def gh_job_logs(
        repo: str = "",
        job_id: str = "",
    ) -> str:
        """Fetch logs for a single job within a GitHub Actions run.

        Use gh_run_view to find job IDs listed under a run.
        repo:   owner/repo. Falls back to GITHUB_REPO env var.
        job_id: numeric job ID.
        """
        r = _repo(repo)
        if not job_id.strip():
            raise ValueError("job_id is required")
        if not _RUN_ID_RE.fullmatch(job_id.strip()):
            raise ValueError(f"Invalid job_id: {job_id!r}. Must be numeric.")
        return await run(
            f"gh run view --job {q(job_id.strip())} --repo {q(r)} --log",
            120,
        )

    @mcp.tool()
    async def gh_diagnose_failure(
        repo: str = "",
        workflow: str = "",
    ) -> str:
        """Find the latest failed GitHub Actions run and show its error logs.

        Combines finding the most recent failure with fetching the failed-step
        logs in a single call — useful for quickly understanding why a build broke.

        repo:     owner/repo. Falls back to GITHUB_REPO env var.
        workflow: narrow to a specific workflow filename or name (optional).
        """
        r = _repo(repo)
        workflow_flag = f" --workflow {q(_workflow(workflow))}" if workflow else ""
        command = f"""
set -e
run_id=$(gh run list --repo {q(r)}{workflow_flag} --status failure --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null)
if [ -z "$run_id" ] || [ "$run_id" = "null" ]; then
  echo "No failed runs found."
  exit 0
fi
echo "===== FAILED RUN SUMMARY ====="
gh run view "$run_id" --repo {q(r)}
echo ""
echo "===== FAILED STEP LOGS ====="
gh run view "$run_id" --repo {q(r)} --log-failed
"""
        return await run(command, 120)

    # -------------------------------------------------------------------------
    # Mutating
    # -------------------------------------------------------------------------

    @mcp.tool()
    async def gh_run_cancel(repo: str = "", run_id: str = "") -> str:
        """Cancel an in-progress GitHub Actions workflow run. This changes remote state.

        repo:   owner/repo. Falls back to GITHUB_REPO env var.
        run_id: numeric run ID (from gh_run_list).
        """
        r = _repo(repo)
        if not run_id.strip():
            raise ValueError("run_id is required")
        return await run(
            f"gh run cancel {q(_run_id(run_id))} --repo {q(r)}",
            60,
        )

    @mcp.tool()
    async def gh_run_rerun(
        repo: str = "",
        run_id: str = "",
        failed_only: bool = False,
    ) -> str:
        """Re-run a GitHub Actions workflow run. This changes remote state.

        repo:        owner/repo. Falls back to GITHUB_REPO env var.
        run_id:      numeric run ID (from gh_run_list).
        failed_only: set true to re-run only failed jobs.
        """
        r = _repo(repo)
        if not run_id.strip():
            raise ValueError("run_id is required")
        flag = " --failed" if failed_only else ""
        return await run(
            f"gh run rerun {q(_run_id(run_id))} --repo {q(r)}{flag}",
            120,
        )