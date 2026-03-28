# TODOs

Audited 2026-03-28. Original items from v0.1.0 launch review (2026-03-16), updated after rebrand to tonone.ai and migration to plugin-based architecture (13 agents).

## P2 - Next Release

### Prerequisite checker

- **What:** Skill or script that verifies gcloud installed, authenticated, project set, Python version compatible.
- **Why:** Prevents wasted time when users hit "gcloud not found" on first run.
- **Effort:** S
- **Depends on:** Nothing

### Parallel fleet analysis

- **What:** Use `concurrent.futures.ThreadPoolExecutor` (5-10 workers) in `team/forge/scripts/cloudrun_agent/overview.py` for service analysis.
- **Why:** 50-service fleet = ~500 sequential API calls = 10+ min. Parallel = ~2 min.
- **Effort:** M
- **Depends on:** Progress indicator (shipped in v0.1.0)

## P3 - Future

### Snapshot retention / pruning

- **What:** Auto-prune old snapshots (keep last 30) in `team/forge/scripts/cloudrun_agent/history.py`. Add `prune_old_snapshots()` and expose via CLI flag.
- **Why:** `~/.cloudrun-agent/history/` grows unbounded over months.
- **Effort:** S

### Post-install smoke test

- **What:** After agent install, optionally verify prerequisites work and print a summary.
- **Why:** Turns "hope it works" into "confirmed working" on first install.
- **Effort:** S
- **Depends on:** Prerequisite checker (shared logic)

## Done / Obsolete

### ~~Pip CLI~~ (removed 2026-03-28)

- **Status:** REMOVED — plugin system is the sole install/discovery path now.
