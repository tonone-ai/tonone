# Changelog

All notable changes to this project will be documented in this file.

## [0.4.1] — 2026-04-03

### Fixed

- **Browser-first reporting** — all substantial agent reports (takeover, plan, review) now open as HTML in the browser automatically; no analysis is dumped to CLI
- **`atlas-report`** — opens browser immediately without prompting for confirmation
- **`apex-takeover`** — Phase 3 CLI output reduced to a 6-line receipt; all findings route to HTML report
- **`apex-plan`** — report path updated to `.agent-logs/reports/`; CLI receipt format tightened
- **`apex-review`** — CLI verdict only (READY TO SHIP / DO NOT SHIP + risk counts); full findings in HTML
- **`output-kit`** — added Browser-First Reporting section as canonical team rule; report storage path standardized to `.agent-logs/reports/`

## [0.4.0] — 2026-03-29

### Added

- **Output Kit** — shared CLI design system for all agents (`docs/output-kit.md`)
- **`atlas-report`** — render agent findings as styled HTML reports in the browser
- **`atlas-changelog`** — three-layer changelog management (per-repo, cross-repo, per-agent)
- **`atlas-present`** — release presentations as HTML pages + Obsidian Canvas
- **Changelog hook** — automatic changelog entries when agents complete work
- **Workspace model** — documentation for multi-repo workspace layout

### Changed

- All agent skills now reference the output kit for consistent CLI formatting
- Atlas agent scope expanded to include output architecture
- Atlas plugin version bumped to 0.2.0

## [0.3.0] - 2026-03-29

### Added

- **Proof** agent — QA & testing engineer (test strategy, E2E suites, API testing, test audits, testing recon)
- **Pave** agent — platform engineer (golden path templates, dev environments, service catalogs, DX audits, platform recon)
- 10 new skills: proof-strategy, proof-e2e, proof-api, proof-audit, proof-recon, pave-golden, pave-env, pave-catalog, pave-audit, pave-recon
- Contributor documentation: architecture overview, skill authoring guide, agent authoring guide
- CONTRIBUTING.md, CHANGELOG.md, GitHub issue/PR templates
- Real SECURITY.md replacing placeholder

### Changed

- Team roster: 1 lead + 14 specialists (was 12), 74 skills (was 64)
- TODOS.md rewritten as full project roadmap

## [0.2.0] - 2026-03-28

### Changed

- Flattened all 64 skills to root plugin for single-install discoverability
- Bundled all 13 agents in root plugin — one install gets everything
- Refined tagline to "Simple by default. Scalable by design."
- Added "Why This Exists" philosophy section to README

### Removed

- Legacy pip CLI — plugin system is the sole install path
- Legacy Cloud Run agent from Forge (infrastructure generalist now)

## [0.1.0] - 2026-03-16

### Added

- Initial release with 13 agents and 64 skills
- Plugin-based architecture with marketplace registration
- Agent template for scaffolding new team members
- Naming guide for consistent agent identity
- Apex lead agent with orchestration and S/M/L scoping
- 12 specialist agents: Forge, Relay, Spine, Flux, Warden, Vigil, Prism, Cortex, Touch, Volt, Atlas, Lens
