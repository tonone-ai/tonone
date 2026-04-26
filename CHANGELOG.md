# Changelog

All notable changes to this project will be documented in this file.

## [0.9.3] — 2026-04-26

### Added

- **`/draft-proto`** — hi-fi interactive HTML prototype skill for Draft. Takes wireframes to the next level: single-file React+Babel HTML, device-framed (iOS), real images from Wikimedia/Unsplash, state-driven navigation, Playwright-verified before delivery. Fills the gap between `/draft-wireframe` (lo-fi) and `/prism-ui` (production code).
- **`/form-direction`** — design direction advisor for Form. Generates 3 differentiated visual directions from 5 design schools (Information Architecture, Motion Poetry, Minimalism, Experimental Avant-garde, Eastern Philosophy), each with a parallel HTML demo. Richer than `/form-style`: produces actual visual demos for selection, not just text recommendations.
- **`/form-animate`** — motion design skill for Form. HTML animation to Playwright render to MP4/GIF export with BGM. Includes brand asset protocol, anti-AI-slop guardrails (no CSS silhouettes, no blue-purple gradient defaults), and narrative structure (hook, build, resolve, hold).
- **`/form-critique`** — 5-dimension expert design critique for Form. Scores coherence, visual hierarchy, execution craft, functionality, and innovation 0-10 with ASCII radar chart and Keep/Fix/Quick Wins punch list. Distinct from `/form-audit` (technical QA): evaluates design as a craft object.
- **`form-palette` and `form-style`** registered in Form plugin.json (previously existed but untracked).

### Changed

- Draft agent definition updated with `## Draft Skills` routing table referencing `/draft-wireframe` vs `/draft-proto` decision logic.
- Form agent definition updated with `## Form Skills` routing table for all 6 specialized workflows.

## [0.9.2] — 2026-04-26

### Added

- **23 agent entry-point skills** — each agent now has a root `/apex`, `/helm`, `/forge`, etc. skill that accepts any task description and routes internally to the right sub-skill. Users no longer need to know which sub-skill to call; they hand the task to the agent and the agent decides. Brings total skill count to 161.

## [0.9.1] — 2026-04-26

### Fixed

- Fix `tonone-onboard` skill compliance — quoted YAML description (colon broke parse), added Step 2/3 workflow headers, exempted from prefix/output-kit/atlas-report checks via new `SPECIAL_SKILLS` set

### Changed

- README reframed around founder vision — "Founder + Tonone = whole company" thesis, roadmap table with sales/CS/finance/ops phases, skill count corrected to 138
- Add `launch/` folder — HN post and X thread drafts for public launch prep

## [0.9.0] — 2026-04-17

### Removed

- **Elephant memory bundled in tonone** — `hooks/elephant-recall.js`, `hooks/elephant-writer.js`, and the `skills/atlas-elephant/` skill are gone. Elephant is now a standalone plugin at [tonone-ai/elephant](https://github.com/tonone-ai/elephant); install it separately if you want persistent memory. This drops 4 hook entries from `.claude-plugin/plugin.json` (1× `SessionStart`, 3× `PostToolUse` on `Agent`/`Bash`/`Skill`).

### Changed

- **Onboarding tour** — `skills/tonone-onboard/` no longer advertises bundled elephant memory. Description, expert-path command list, mental-model section, and newcomer-path next-steps updated to reflect tonone's current scope (agents + skills + worktree sessions).

## [0.8.1] — 2026-04-13

### Changed

- **Lazy worktree creation** — sessions now start clean on `main` with no upfront worktree. The first `Edit`, `Write`, or `NotebookEdit` on main triggers a `PreToolUse` gate (`tonone-worktree-gate.js`) that blocks and asks Claude to create a properly-named branch. By the time the gate fires, Claude knows the task — so the slug is meaningful and no rename step is ever needed.

### Removed

- **Session-start auto-worktree** — `tonone-worktree-session.js` and its `session-YYYYMMDD-HHMMSS` branch naming removed. No more stale worktree branches accumulating per session.

## [0.7.1] — 2026-04-12

### Fixed

- **atlas-elephant skill** — renamed from `skills/elephant` to `skills/atlas-elephant` to satisfy 7 skill compliance checks: kebab-case naming, valid agent prefix (`atlas`), description trigger phrases, output-kit reference, atlas-report overflow clause, identity line, and structured workflow steps.

## [0.7.0] — 2026-04-12

### Added

- **Eager worktree sessions** — `hooks/tonone-worktree-session.js` fires on `SessionStart` and auto-creates a worktree immediately, before any edits. Replaces the deferred gate approach. `plugin.json` wired; old `tonone-worktree-create.js` and `tonone-worktree-gate.js` deleted.
- **Human-readable branch names** — `.claude/branch-slug` maps session IDs to short slugs (e.g. `feat/auth-fixes`) so worktree branches are readable at a glance instead of UUID-based.
- **PR attribution** — `hooks/tonone-pr-attribution.js` appends a "Built by Tonone team" credits block to every PR body, listing the agents involved. Boosts K-factor via team credit visibility. Registered in `plugin.json`.
- **Elephant memory** — persistent caveman-compressed memory system: `hooks/tonone-elephant-writer.js` auto-captures agent completions, commits, and skill runs; `hooks/tonone-elephant-recall.js` surfaces a startup summary. `/elephant` skill adds `save`, `show`, and `compact` commands.
- **Elephant takeover** — `/elephant takeover` cold-starts the memory system from git history, bootstrapping recall for repos with no prior elephant data.
- **Statusline session goal** — Line 4 of the 3-line statusline redesign now shows the session goal. Shoutouts added.

### Fixed

- **Statusline** — `resets_at` now parsed as Unix seconds (not milliseconds), fixing incorrect pace projection display.
- **Worktree session hook** — removed unused `fs` import.

## [0.6.9] — 2026-04-12

### Added

- **Update checker** — `hooks/tonone-update-check.js` runs at `SessionStart`, fetches the latest version from GitHub at most once per 24 h, and notifies via OS notification + stderr line when a newer version is available. Result is cached in `~/.config/tonone/update-cache.json`.

## [0.6.8] — 2026-04-12

### Added

- **Notification system** — `hooks/tonone-notify.js` fires a macOS notification (via `osascript`) when Claude finishes a turn (`Stop` hook) or needs your attention (`Notification` hook). Sound plays via `afplay` and is on by default. Configure in `~/.config/tonone/config.json` under the `notify` key (`sound: bool`, `soundFile: string`).

## [0.6.7] — 2026-04-12

### Added

- **Agent eval suite** — 25 new tests across `test_agent_compliance.py` (11 tests) and `test_skill_compliance.py` (14 tests) validating frontmatter schema, model selection, communication protocol, identity lines, severity indicators, emoji, naming conventions, output-kit contract, atlas-report overflow clause, and structured workflow steps
- **Drift tracking** — known severity and emoji violations tracked in explicit sets with companion tests that fail when drift is fixed but not removed from the allowlist
- **CI gate** — agent and skill compliance tests wired into the validate-structure job

### Fixed

- **12 skills missing output-kit contract** — added the standard output-kit reference line to draft-landing, draft-patterns, form-exam, form-palette, form-style, lens-chart, pitch-landing, prism-chart, prism-stack, proof-design, surge-landing, touch-ui (root + team copies)

## [0.6.6] — 2026-04-12

### Added

- **Communication Protocol** — rolled out to all 21 agents (apex, atlas, cortex, crest, draft, forge, form, helm, lens, lumen, pave, pitch, prism, proof, relay, spine, surge, touch, vigil, volt, warden) and agent template; upgrades output-kit Language Rules to a full Communication Protocol
- **Agent template** — new agents now include communication protocol by default

### Fixed

- **plugin.json hooks** — inlined hooks directly in root plugin manifest to fix install validation failure

### Changed

- **Agent docs** — compressed prose across all 21 updated agent definitions
- **Agent plugin versions** — bumped from 0.1.0 → 0.1.1 for all agents with communication protocol changes

## [0.6.5] — 2026-04-07

### Changed

- **README** — tagline sharpened to "One session. Two commands. Full team. Zero meetings."

### Fixed

- **test_structure.py** — updated naming assertion to match bare plugin name convention (no `tonone-` prefix) introduced in v0.6.4

## [0.6.4] — 2026-04-06

### Fixed

- **bundle manifests** — removed invalid `"agents"` and `"skills"` string fields from all three bundle plugin.json files; Claude Code auto-discovers these directories and the string format caused a validation error on install
- **README** — Quick Start now shows both CLI (`claude plugin`) and in-session (`/plugin`) installation pathways; code fences labelled with language identifiers

## [0.6.3] — 2026-04-06

### Fixed

- **plugin.json** — all four plugin manifests (root + 3 bundles) now declare `"agents"` and `"skills"` paths so agents like `/apex`, `/forge`, etc. are discoverable after installation

## [0.6.2] — 2026-04-06

### Added

- **AGENTS.md** — Codex CLI compatibility layer: team roster, directory guide, and instructions for using agents and skills without the Claude Code plugin system
- **README** — Codex CLI quick start section (clone, `codex`, invoke agents by reading markdown directly)
- **docs/architecture.md** — platform support table documenting Claude Code (primary) vs Codex CLI (secondary)

## [0.6.1] — 2026-04-06

### Changed

- **README** — updated tagline from "Engineering second to none" to "Engineering + product, second to none"; added full Product team table (8 agents); expanded skill list from 77 to all 125; updated intro copy to reflect both teams
- **ROADMAP** — bumped version to v0.6.0, skills count to 125; replaced "Complete Product Team" section (already shipped) with stability and community goals for v1.0
- **docs/architecture.md** — corrected agent and skill counts from 15/77 to 23/125
- **docs/agent-guide.md, docs/skill-guide.md** — updated identity line examples from "Engineering Team" to "Tonone team"
- **docs/naming-guide.md** — removed "(Sprint 1–3)" label from Product Team section
- **templates/new-agent** — updated agent and skill templates to use "Tonone team" instead of "Engineering Team TEAM_LABEL team"

## [0.6.0] — 2026-04-06

### Changed

- **All 23 agents upgraded with industry best practices** — every agent definition rebuilt with a founder mindset, execution-first workflows, and domain-specific professional standards. Agents now GET SHIT DONE instead of advising.
- **44 skills rewritten** across all agents — each skill now includes operating principles, competitive audits, minimum viable output gates, and explicit "done enough" criteria. No more consulting theater.
- **Form** — operating principle "positioning before pixels"; resource allocation (60-70% UI, 20-30% web, 10% other); MVB checklist; explicit skip/never-skip lists
- **form-brand** — 3-question positioning gate; competitive audit; shipability gate with 6-item checklist
- **form-logo** — ONE THING anchor; brief extraction gate; ship decision (recommendation, not options)
- **Echo** — Mom Test built into echo-interview; Four Forces + switch threshold in echo-jobs
- **Draft** — pattern audit before wireframes; done-enough gate in draft-wireframe; IA-before-jobs in draft-ia
- **Helm** — Infer/Ask/Decide protocol with labeled assumptions in helm-brief; 6-field handoff schema
- **Crest** — strategic anchor before roadmap; mandatory positioning call in crest-compete
- **Pitch** — Dunford positioning framework in pitch-position; writes actual copy in pitch-launch
- **Lumen** — North Star validity test in lumen-metrics; Step 0 "when NOT to test" in lumen-abtest
- **Surge** — single-diagnosis verdict in surge-retention; readiness check gate in surge-plg
- **Spine** — Stripe-quality API spec in spine-api; decision log required in spine-design
- **Flux** — normalization decision by stage in flux-schema; CONCURRENTLY caveat + SQL templates in flux-migrate
- **Prism** — real TypeScript + Tailwind in prism-component; spec-driven implementation in prism-ui
- **Cortex** — decision tree (prompt→RAG→tool→agent→fine-tune) in cortex-integrate; complete prompt package in cortex-prompt
- **Atlas** — real Mermaid C4 diagrams in atlas-map; minimum 2 alternatives + 1 acknowledged downside in atlas-adr
- **Proof** — risk map + "what NOT to test" in proof-strategy; Playwright config + auth fixture in proof-e2e
- **Relay** — ready-to-commit YAML + SHA-pinned actions in relay-pipeline; strategy decision table in relay-deploy
- **Forge** — stage fork (managed vs Terraform) in forge-infra; per-opportunity change blocks in forge-cost
- **Warden** — crown jewels first + accepted risks required in warden-threat; exact header values in warden-harden
- **Vigil** — OTel auto-instrumentation in vigil-instrument; "What NOT to alert on" step in vigil-alert
- **Pave** — friction audit first in pave-golden; size-based decision tree in pave-catalog
- **Apex** — reversible/irreversible lens in apex-plan; ship/no-ship verdict with file+line in apex-review
- **Lens** — decision + "so what?" audit in lens-dashboard; MISSING DATA section in lens-metrics
- **Touch** — platform decision in spec for touch-feature; full architecture + EAS Update OTA in touch-app
- **Volt** — HAL interfaces + RTOS decision in volt-firmware; A/B partitions + failure mode table in volt-ota

## [0.5.0] — 2026-04-06

### Added

- **Skill balancing initiative** — all 23 agents now meet the minimum 5-skill production threshold (up from 10 under-skilled agents)
- **Form agent** — expanded from 2 to 10 skills: form-audit, form-component, form-deck, form-email, form-mobile, form-social, form-tokens, form-web, plus rebuilt form-logo with a professional phase-gate workflow (research → strategy → 3 visual directions → refinement → delivery)
- **Wave 1 — Recon skills (8)**: apex-recon, crest-recon, draft-recon, echo-recon, helm-recon, lumen-recon, pitch-recon, surge-recon — systematic project-state reconnaissance before any agent action
- **Wave 2 — Bounded procedures (6)**: warden-threat (STRIDE threat modeling), volt-power (power budget analysis), helm-arbiter (scope arbitration), crest-okr (OKR design), lumen-abtest (A/B test design), lumen-instrument (analytics instrumentation)
- **Wave 3 — Analysis frameworks (8)**: crest-compete (competitive analysis), crest-narrative (strategic memos), echo-segment (user personas), echo-jobs (Jobs-to-Be-Done), echo-feedback (feedback synthesis), lumen-metrics (metrics framework), surge-experiment (growth experiments), surge-retention (retention playbooks)
- **Wave 4 — Creative output (7)**: draft-wireframe (text/Mermaid wireframes), draft-ia (information architecture), draft-review (usability audits), pitch-message (messaging frameworks), pitch-launch (GTM planning), pitch-copy (landing page copy), surge-plg (product-led growth strategy)
- **relay-ship skill** — Relay agent can now run full ship workflows
- **Root `skills/` directory** — 125 installable skills synced for use as individual Claude Code plugins; includes 19 previously-built skills that were never exposed (helm-brief, helm-handoff, helm-plan, crest-roadmap, draft-flow, echo-interview, lumen-funnel, pitch-position, surge-activation, and all 10 Form skills)

### Changed

- Form agent plugin manifest updated to register all 10 skills
- Relay agent plugin manifest updated with relay-ship skill

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

---

> Changelog maintained automatically by [🐘 elephant](https://github.com/tonone-ai/elephant) — keep your changelog up to date without the manual work.
