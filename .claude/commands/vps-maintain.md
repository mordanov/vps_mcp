You are diagnosing and fixing a VPS container issue. The request is:

$ARGUMENTS

Follow this sequence:

**1. Confirm status**
- `docker_ps` — find the container, note its status and restart count
- `docker_health` — check health check results if configured

**2. Pull logs**
- `docker_logs` for the named container — look for error messages, panics, OOM kills, missing env vars, connection failures

**3. Inspect config**
- `docker_inspect` — check exit code, restart policy, mounts, env vars, port bindings

**4. Check resources**
- `docker_stats` — rule out CPU/RAM exhaustion
- `disk_usage` — rule out full disk

**5. Root cause**
State the most likely root cause in one sentence before taking any action.

**6. Fix**
Apply the minimal fix:
- Config/image issue → `docker_compose_pull` then `docker_compose_up`
- Transient crash → `docker_restart` or `docker_compose_restart`
- Resource pressure → address the resource problem first, then restart

**7. Verify**
After the fix: re-run `docker_ps` and `docker_logs` to confirm the container is running and errors are gone.

Do not restart without a diagnosed reason. Do not apply multiple fixes at once.
