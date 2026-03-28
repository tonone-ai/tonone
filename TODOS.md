# TODOs

Audited 2026-03-28. Original items from v0.1.0 launch review (2026-03-16), updated after rebrand to tonone.ai and migration to plugin-based architecture (13 agents).

## P2 - Next Release

### Prerequisite checker

- **What:** Skill or script that verifies gcloud installed, authenticated, project set, Python version compatible.
- **Why:** Prevents wasted time when users hit "gcloud not found" on first run.
- **Effort:** S
- **Depends on:** Nothing

## P3 - Future

### Post-install smoke test

- **What:** After agent install, optionally verify prerequisites work and print a summary.
- **Why:** Turns "hope it works" into "confirmed working" on first install.
- **Effort:** S
- **Depends on:** Prerequisite checker (shared logic)

## Done / Obsolete

### ~~Pip CLI~~ (removed 2026-03-28)

- **Status:** REMOVED — plugin system is the sole install/discovery path now.
