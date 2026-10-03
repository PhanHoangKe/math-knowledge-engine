# MKE Agent Control Plane

This branch is intentionally separate from product lineage.

Purpose:
1. ChatGPT writes one trusted task into .mke-agent/task.json and a prompt file.
2. A local Windows runner polls this branch using normal git fetch/pull.
3. The runner creates an isolated git worktree at the exact task base SHA.
4. Antigravity CLI runs headlessly and edits only the task worktree.
5. The runner enforces allowed-path scope, runs baseline and final full regression tests, commits and pushes only a passing task branch.
6. The runner updates task.json to READY_FOR_AUDIT.
7. ChatGPT independently audits the remote commit and either accepts it or queues a remediation/next task.

Trust model:
- Antigravity never receives permission to push product branches directly.
- The runner owns commit/push after scope and regression gates pass.
- No force push.
- No main/default-branch product delivery.
- Frontend changes are forbidden unless a future task explicitly allows them.
- raw agent output is evidence only, never audit authority.

The only one-time local setup is running install.ps1. Antigravity CLI may require one interactive sign-in if its cached credentials are not already available.
