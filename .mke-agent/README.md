# MKE Agent Control Plane

This branch is intentionally separate from product lineage.

Purpose:
1. ChatGPT writes one trusted task into .mke-agent/task.json and a prompt file.
2. A local Windows runner polls this branch using normal git fetch/pull.
3. The runner creates an isolated git worktree at the exact task base SHA.
4. Antigravity CLI runs headlessly and edits only the task worktree.
5. The runner enforces allowed-path scope, runs baseline and final full regression tests, commits and pushes only a passing task branch.
6. The runner updates task.json to READY_FOR_AUDIT and immediately invokes the local OpenAI auditor.
7. The auditor re-fetches the exact remote head, checks ancestry/scope/frontend freezes, independently reruns the full test suite, and sends bounded evidence to the OpenAI Responses API using strict Structured Outputs.
8. The orchestrator atomically records ACCEPT/REMEDIATE history and queues a bounded remediation or the next pre-approved task.

Event delivery is at-least-once and state mutation is idempotent. The event key is derived from task id, attempt, status and candidate SHA. Decisions are cached locally before mutation, control updates use compare-and-swap checks, and a crash or push race is safe to retry. The hourly ChatGPT automation is a watchdog only.

Trust model:
- Antigravity never receives permission to push product branches directly.
- The runner owns commit/push after scope and regression gates pass.
- No force push.
- No main/default-branch product delivery.
- Frontend changes are forbidden unless a future task explicitly allows them.
- raw agent output is evidence only, never audit authority.
- CAS output remains an untrusted candidate; MKE verification alone grants mathematical trust.
- The API auditor cannot invent the next product scope. ACCEPT advances only to an entry already present in `queue.json`.
- REMEDIATE keeps the original allowed paths and freezes. After three task attempts, status becomes `OWNER_REQUIRED`.

## Secrets

The auditor accepts an OpenAI API key from either:

1. `OPENAI_API_KEY` in the runner environment (also suitable for a GitHub Actions secret), or
2. the default Windows per-user DPAPI store at `%LOCALAPPDATA%\MKE\secrets\openai_api_key.dpapi`.

The key is never committed or written to audit history. `configure-secrets.ps1` creates the DPAPI file and restricts its ACL to the current Windows user.

## Queue contract

`.mke-agent/queue.json` contains coordinator-approved task definitions. A pending task uses the same fields as `task.json`; `base_sha` may be `$ACCEPTED_COMMIT`. On ACCEPT the first pending item is marked QUEUED and becomes the active READY task. An empty queue leaves the accepted task in `ACCEPTED`, which is fail-closed and prevents the model from broadening product scope.

## One-time setup / upgrade

From PowerShell on the runner machine:

```powershell
cd "D:\Math Knowledge Engine"
git fetch origin automation/mke-agent-loop
git show origin/automation/mke-agent-loop:.mke-agent/install.ps1 | powershell -NoProfile -ExecutionPolicy Bypass -Command -
```

If neither an environment key nor the DPAPI file exists, the installer asks once for the OpenAI API key. API billing is separate from ChatGPT. Re-running the installer upgrades the existing control worktree and scheduled task without asking for the key again.

The only one-time local setup is running install.ps1. Antigravity CLI may require one interactive sign-in if its cached credentials are not already available.
