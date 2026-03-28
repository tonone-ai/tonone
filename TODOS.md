# Roadmap

Last updated: 2026-03-29

## v0.3.0 — Open Source Ready

### CONTRIBUTING.md

- **What:** Contributor guide covering setup, PR conventions, agent creation workflow, and skill authoring.
- **Why:** Essential for external contributors to understand how to add agents or improve existing skills.
- **Effort:** S
- **Status:** Done

### SECURITY.md

- **What:** Replace GitHub template with real vulnerability reporting process.
- **Why:** Current file has placeholder version numbers and no actual policy.
- **Effort:** S
- **Status:** Done

### CHANGELOG

- **What:** Retroactive changelog from git history, then maintain going forward.
- **Why:** Contributors and users need to understand what changed between versions.
- **Effort:** S
- **Status:** Done

### GitHub templates

- **What:** Issue templates (bug report, feature request, new agent proposal), PR template, and funding config.
- **Why:** Standardizes contributions and makes it easy for new contributors to participate.
- **Effort:** S
- **Status:** Done

### CI pipeline

- **What:** GitHub Actions workflow — lint (Trunk), validate plugin structure, test.
- **Why:** PRs need automated quality gates before merge. Currently all checks are manual.
- **Effort:** M
- **Status:** Todo

### Prerequisite checker

- **What:** Skill or hook that verifies dependencies (Python version, uv/pip) on install.
- **Why:** Prevents wasted time when users hit missing tool errors on first run.
- **Effort:** S
- **Status:** Todo

### Post-install smoke test

- **What:** After install, optionally verify agent loading and print a summary.
- **Why:** Turns "hope it works" into "confirmed working" on first install.
- **Effort:** S
- **Depends on:** Prerequisite checker

## v0.4.0 — Agent Quality

### Skill test harness

- **What:** Framework for testing skills with sample inputs and expected behavior patterns.
- **Why:** As skill count grows (64+), manual testing doesn't scale. Need automated regression.
- **Effort:** M

### Agent integration tests

- **What:** Tests that verify each agent loads, responds to basic prompts, and uses correct tools.
- **Why:** Ensures refactors don't silently break agent behavior.
- **Effort:** M

### Skill quality scoring

- **What:** Lint-like tool that scores skill definitions for completeness (frontmatter, workflow steps, anti-patterns, output format).
- **Why:** Maintains consistent quality as community contributes new skills.
- **Effort:** M

### Agent showcase / demos

- **What:** Recorded examples (asciicast or markdown) showing each agent handling a real task.
- **Why:** Contributors need to see what "good" looks like. Users need to see what's possible.
- **Effort:** L

## v0.5.0 — Ecosystem

### Plugin marketplace metadata

- **What:** Rich metadata (screenshots, categories, compatibility tags) for marketplace listing.
- **Why:** Better discovery when Claude Code plugin ecosystem grows.
- **Effort:** S

### Cross-agent memory

- **What:** Shared context mechanism so agents can pass findings to each other without Apex relaying everything.
- **Why:** System takeover and multi-agent workflows lose context in handoffs today.
- **Effort:** L

### Community agent template

- **What:** Interactive scaffolding (like `create-react-app` but for agents) that walks through naming, domain, skills.
- **Why:** Lowers the barrier for community contributions beyond the current manual template copy.
- **Effort:** M

### Agent composition API

- **What:** Declarative way to define multi-agent workflows (e.g., "run Warden audit, then Relay hardening, then Vigil instrumentation").
- **Why:** Currently only Apex can orchestrate. Users should be able to define custom pipelines.
- **Effort:** L

## Backlog — Ideas

- Documentation site (Astro/Starlight) with per-agent pages
- Agent performance benchmarks (token usage, task completion rates)
- Specialized sub-agents within teams (e.g., Forge could have Terraform vs Pulumi specialists)
- Localization of agent prompts for non-English teams
- VS Code extension for agent selection UI

## Done

### ~~v0.1.0~~ (2026-03-16)

- Initial release with 13 agents and 64 skills
- Plugin-based architecture
- Marketplace registration

### ~~v0.2.0~~ (2026-03-28)

- Removed legacy pip CLI
- Bundled all agents in root plugin for single install
- Flattened skills to root for discoverability
- Removed legacy Cloud Run agent from Forge
- Refined tagline and added "Why This Exists" section
