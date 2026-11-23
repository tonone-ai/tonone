# Tonone Roadmap

Tonone is an open-source Claude Code plugin: specialist agents and workflow skills across 15 teams. Install the full roster, the lean `tonone-core` engineering team, or just the skills.

Last updated: 2026-11-23. Current release: see [CHANGELOG.md](CHANGELOG.md).

## Shipped

- 15 teams, 140 agents, 573 skills, all in the main plugin.
- Apex depth-tier planning (XS to XXL) with specialist assignments and token and cost estimates.
- `/apex-profile` scopes the roster to the project; `tonone-core` is the lean 15-agent engineering install.
- Skills-only install via `npx skills add`, a read-only `tonone-mcp` server, and Codex support through `AGENTS.md`.
- Opt-in safety and memory: `/apex-guard`, `/apex-decisions`, `/tonone-doctor`, plus the separate `elephant` plugin.
- Design toolchain: `/form-lint`, `/form-brief`, `/form-direction`, `/prism-variants`.

## Next

**Adoption**

- [ ] Lean install first: `tonone-core` and `/apex-profile` are the front door, the 37k-token full roster is opt-in.
- [ ] Vertical presets with one-line installs and site landing pages (SaaS founder, agency, data team, hardware, security review).
- [ ] Shareable `/apex-plan` output (tiers, specialists, cost) as a page.

**Credibility**

- [ ] Before/after evals on flagship skills (`/apex-plan`, `/warden-audit`, `/forge-recon`), published with method and raw results.
- [ ] Skill quality scoring in CI (frontmatter, workflow steps, output format).
- [ ] Resubmit to curated lists once the evals are public.

**Reliability**

- [ ] Fix agent routing gaps (wrong agent picked for a task).

## Not now

- More agents. The roster is broad enough; new agents raise startup context cost. New ones need an open issue showing demand.
- Hosted or paid tiers inside this repo. This repo stays MIT and local-first.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and `docs/skill-guide.md`. Open an issue before proposing a new agent.
