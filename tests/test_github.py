import pytest

from tests.conftest import FakeMCP, make_runner
from vps_docker_mcp.github import _repo, _run_id, _workflow, register


def test_repo_valid():
    assert _repo("owner/repo") == "owner/repo"


def test_repo_with_dots_and_dashes():
    assert _repo("my-org/my.repo") == "my-org/my.repo"


def test_repo_invalid_no_slash():
    with pytest.raises(ValueError):
        _repo("noslash")


def test_repo_invalid_leading_dash():
    with pytest.raises(ValueError):
        _repo("-bad/repo")


def test_repo_empty_no_default(monkeypatch):
    monkeypatch.setattr("vps_docker_mcp.github.GITHUB_REPO", "")
    with pytest.raises(ValueError):
        _repo("")


def test_repo_empty_falls_back_to_default(monkeypatch):
    monkeypatch.setattr("vps_docker_mcp.github.GITHUB_REPO", "default/repo")
    assert _repo("") == "default/repo"


def test_run_id_valid():
    assert _run_id("12345678") == "12345678"


def test_run_id_leading_whitespace():
    assert _run_id("  99  ") == "99"


def test_run_id_invalid_letters():
    with pytest.raises(ValueError):
        _run_id("abc")


def test_run_id_invalid_empty():
    with pytest.raises(ValueError):
        _run_id("")


def test_workflow_valid():
    assert _workflow("ci.yml") == "ci.yml"
    assert _workflow("Deploy Production") == "Deploy Production"


def test_workflow_invalid_leading_dash():
    with pytest.raises(ValueError):
        _workflow("-bad")


# ---------- tool command assertions ----------


@pytest.mark.asyncio
async def test_gh_workflow_list_command():
    mcp = FakeMCP()
    runner = make_runner("workflows")
    register(mcp, runner)
    result = await mcp.tools["gh_workflow_list"](repo="owner/repo")
    assert result == "workflows"
    cmd = runner.call_args[0][0]
    assert "gh workflow list" in cmd
    assert "owner/repo" in cmd


@pytest.mark.asyncio
async def test_gh_run_list_clamps_limit():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["gh_run_list"](repo="owner/repo", limit=999)
    cmd = runner.call_args[0][0]
    assert "--limit 100" in cmd


@pytest.mark.asyncio
async def test_gh_run_list_invalid_status():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    with pytest.raises(ValueError):
        await mcp.tools["gh_run_list"](repo="owner/repo", status="invalid")


@pytest.mark.asyncio
async def test_gh_run_view_requires_run_id():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    with pytest.raises(ValueError):
        await mcp.tools["gh_run_view"](repo="owner/repo", run_id="")


@pytest.mark.asyncio
async def test_gh_run_logs_failed_only():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["gh_run_logs"](repo="owner/repo", run_id="123", failed_only=True)
    cmd = runner.call_args[0][0]
    assert "--log-failed" in cmd or "--log --failed" in cmd or "--log-failed" in cmd


@pytest.mark.asyncio
async def test_gh_diagnose_last_run_includes_summary_and_logs():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["gh_diagnose_last_run"](repo="owner/repo")
    cmd = runner.call_args[0][0]
    assert "LAST RUN SUMMARY" in cmd
    assert "FAILED STEP LOGS" in cmd
    assert "--status failure" not in cmd  # difference from gh_diagnose_failure


@pytest.mark.asyncio
async def test_gh_diagnose_failure_filters_by_status():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["gh_diagnose_failure"](repo="owner/repo")
    cmd = runner.call_args[0][0]
    assert "--status failure" in cmd


@pytest.mark.asyncio
async def test_gh_run_cancel_command():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["gh_run_cancel"](repo="owner/repo", run_id="42")
    cmd = runner.call_args[0][0]
    assert "gh run cancel" in cmd
    assert "42" in cmd


@pytest.mark.asyncio
async def test_gh_run_rerun_failed_only_flag():
    mcp = FakeMCP()
    runner = make_runner()
    register(mcp, runner)
    await mcp.tools["gh_run_rerun"](repo="owner/repo", run_id="42", failed_only=True)
    cmd = runner.call_args[0][0]
    assert "--failed" in cmd
