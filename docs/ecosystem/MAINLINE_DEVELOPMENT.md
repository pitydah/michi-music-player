# Mainline development policy

Michi Music Player uses `main` as the only active development line. Long-lived
parallel development branches are not used for product work.

## Rules

1. Work from the current remote `main`; fetch before starting.
2. Keep changes small, independent and reversible.
3. Run focused tests before every commit.
4. Push a corrective commit, then verify CI for that exact SHA. A green run for
   an older SHA is not evidence for the new HEAD.
5. Do not accumulate incompatible sprints before testing.
6. Bind receipts and evidence to the code that was actually executed.
7. Never force-push or rewrite `main` history.
8. If a repository protection prevents the required workflow, stop and report
   the restriction instead of bypassing it.

Short-lived local branches or worktrees may be used to isolate a risky
experiment, but they must be integrated promptly and must not become a second
source of truth. `PHASE2_STATE.json` and the AP2 research freeze remain
authoritative for Audio Phase 2.
