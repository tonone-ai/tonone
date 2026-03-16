# TODOs

Deferred items from the v0.1.0 launch review (2026-03-16).

## P2 - Next Release (v0.2.0)

### `engteam doctor` - prerequisite checker

- **What:** CLI command that verifies gcloud installed, authenticated, project set, Python version compatible.
- **Why:** Prevents wasted time when users hit "gcloud not found" on first run.
- **Effort:** S
- **Depends on:** Nothing

### Parallel fleet analysis

- **What:** Use `concurrent.futures.ThreadPoolExecutor` (5-10 workers) for service analysis.
- **Why:** 50-service fleet = ~500 sequential API calls = 10+ min. Parallel = ~2 min.
- **Effort:** M
- **Depends on:** Progress indicator (shipped in v0.1.0)

### Dynamic agent registry via PyPI tags / entry_points

- **What:** Replace static `AGENTS` tuple with discovery mechanism. Agents self-register via `entry_points` in their pyproject.toml.
- **Why:** Enables community agents without marketplace PRs. Required when agent count > 5.
- **Effort:** L
- **Depends on:** At least 3 agents to justify the abstraction

## P3 - Future

### Snapshot retention / pruning

- **What:** Auto-prune old snapshots (keep last 30) or add `cloudrun-agent analyze --prune`.
- **Why:** `~/.cloudrun-agent/history/` grows unbounded over months.
- **Effort:** S

### Post-install smoke test

- **What:** After `cloudrun-agent install`, optionally verify gcloud works and print service count.
- **Why:** Turns "hope it works" into "confirmed working" on first install.
- **Effort:** S
- **Depends on:** `engteam doctor` (shared prerequisite logic)
