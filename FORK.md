# Afreetoid Hermes WebUI Fork

This is Afreetoid's fork of `nesquena/hermes-webui`. Git history and this prod-only file define the current customization and deployment contract.

## Topology

- `upstream/master`: vendor truth; fetch-only locally.
- `origin/master`: clean fork branch; must exactly equal `upstream/master` before replay.
- `origin/prod`: published customized deployment.
- local `prod`: live checkout tracking verified `origin/prod`.

The external `afreetoid/fork-sync-automation` repository normally synchronizes clean `origin/master`, but every update must first force freshness: manually dispatch that Action or perform the equivalent safe merge-upstream/non-force fast-forward, fetch both remotes again, and prove equality. Scheduled sync is not freshness proof.

Do not use WebUI **Update Now** as the deployment workflow. It does not replay, validate, publish, or preserve this keeper stack.

## Current snapshot

- Clean base: `f6265cc96293bc9ae16ab8d8e3d8bc2dc76d231f`
- Clean describe: `exp-v0.52.94`
- Behavior stack head: `292a3cf616cb9644f1a992ae5ed0ad6c33b2c110`
- Pre-update live head/tree: `88783ecd3e10224e535deec69e995f3e42573691` / `4c7ac1d3487293f04b33ff5e1fc6b84ebde3b5e7`
- Recovery branch/tag: `backup/pre-update-webui-20260717T131311Z` / `pre-update-webui-20260717T131311Z`

## Active behavior keepers

Keep these commits separate and replay them chronologically.

### 1. Compare update checks with vendor branches

Commit: `6a465fd570b67cdb79701b1c459e0c5522f4c179`

Makes Settings update checks fetch and compare WebUI against `upstream/master` and Agent against `upstream/main`, while preserving the existing update/apply behavior.

Files: `api/updates.py`, `tests/test_fork_update_checks.py`, `tests/test_update_channels.py`, `tests/test_updates.py`.

### 2. Fail closed on vendor-check errors

Commit: `292a3cf616cb9644f1a992ae5ed0ad6c33b2c110`

Returns an unknown/stale result rather than false “up to date” when fetch/ref/comparison fails, while sanitizing diagnostics before display.

Files: `api/updates.py`, `tests/test_fork_update_checks.py`.

Aggregate behavior delta before this documentation commit: 4 files, 283 insertions, 55 deletions.

## Validated update procedure

1. Confirm clean live `prod`, controller/listener state, `/health`, and zero active streams/runs.
2. Force a fresh clean-fork sync, fetch both remotes, and prove `origin/master == upstream/master`.
3. Record live HEAD/tree and create a recovery branch plus annotated tag.
4. Build from exact `origin/master` in a disposable worktree.
5. Replay active keepers separately; preserve current upstream behavior and drop any fully superseded keeper.
6. Regenerate this file as a separate documentation commit.
7. Run `git diff --check`, compile and Ruff changed Python, focused update tests, the full suite through `./scripts/test.sh`, and direct read-only vendor checks with isolated state.
8. Recheck upstream freshness, then publish candidate to `origin/prod` with `--force-with-lease` against the observed old remote head.
9. Read back remote SHA/tree/graph before moving local `prod` to it.
10. Confirm zero active work, restart through `ctl.sh`, and verify controller ownership, listener, `/health`, login, startup threads, and fresh errors.
11. Remove disposable worktrees only after remote/live/runtime verification. Retain recovery refs until explicitly pruned.

## Validation for this replay

Passed:

- `git diff --check`
- compileall and Ruff on all changed Python files
- focused update-check selection: 104 passed
- direct vendor checks resolved `upstream/master` and `upstream/main` without errors

Full-suite candidate run: 13,107 passed, 115 skipped, 1 xfailed, 2 xpassed, 34 subtests passed, with one failure in `tests/test_issue4685_post_compression_context_metering.py::test_post_compression_estimate_uses_compressor_budget_counter_without_metadata_estimators`. The identical failure reproduced on pristine clean `origin/master` (13,100 passed, 115 skipped, 1 xfailed, 2 xpassed, 34 subtests passed). It is an upstream order-dependent import-state baseline issue outside the keeper files, not a keeper regression.

## Safety

- Never push to `upstream` or place keepers on clean `master`.
- Never print `.env`, auth, token, cookie, process-environment, or other secret values.
- Never squash behavior keepers.
- Publish and verify remote `prod` before live cutover.
- Do not restart WebUI while active streams/runs exist.
- `/Users/afreetoid/repo-docs` is frozen historical evidence and must not receive current logs or replay artifacts.
