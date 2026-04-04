# Tonone Roadmap

Tonone is an open source Claude Code plugin that gives you a team of specialized AI agents. This roadmap covers agent capabilities, plugin quality, and community growth.

Current version: **v0.4.1**
Agents: **15** (Apex orchestrator + 14 specialists)
Skills: **77**

---

## Now — Stability and Quality (v0.5)

The foundation is built. Next focus is making it solid enough for contributors to extend.

**Agent Quality**

- [ ] Audit all 77 skill definitions for accuracy and completeness
- [ ] Standardize skill frontmatter (name, description, trigger conditions)
- [ ] Remove redundant or overlapping skills between agents

**Plugin Reliability**

- [ ] Add CI — smoke test that all skills load and parse correctly
- [ ] Lint skill YAML/Markdown on every push
- [ ] Fix any remaining agent routing gaps (wrong agent gets invoked)

**Documentation**

- [ ] Each agent: clear description of what it does and when to use it
- [ ] Getting started guide — from zero to first agent invoked
- [ ] Contribution guide — how to add or improve a skill

**Release: v0.5.0**

---

## Next — Extended Agent Coverage (v0.6 → v1.0)

Expand the specialist roster and deepen existing agents.

**New Agent Domains**

- [ ] Evaluate: data privacy / compliance agent (GDPR, CCPA review)
- [ ] Evaluate: incident postmortem agent (structured RCA + timeline)
- [ ] Evaluate: cost optimization agent (cloud spend analysis)

**Deeper Existing Agents**

- [ ] Warden: expand beyond IAM — S3 policies, network security groups, secrets detection
- [ ] Vigil: add SLO burn rate analysis and multi-window alerting patterns
- [ ] Flux: add migration plan generation with rollback steps
- [ ] Cortex: add evaluation framework generation (not just prompt writing)

**Skills API**

- [ ] Document the skill format so external contributors can add skills
- [ ] Skill validation tool — run locally before submitting a PR

**Release: v1.0.0** — Stable, documented, community-ready.

---

## Later — Community and Ecosystem

**Community**

- [ ] Skills marketplace — community-submitted skills, rated by usage
- [ ] "Specialist of the month" highlight in README
- [ ] Discord server for agent discussions and support

**Integrations**

- [ ] GitHub Actions skill — run agents as part of CI pipelines
- [ ] VS Code extension (if Anthropic supports it)
- [ ] MCP server mode — expose agents via Model Context Protocol

**Plugin Distribution**

- [ ] Anthropic Claude Code marketplace listing (when available)
- [ ] `npm install -g tonone` for non-Claude Code environments

---

## What We're Not Building

To stay focused:

- No web UI in this repo (that's tonone.ai — separate)
- No database, auth, or payment logic (plugin stays stateless)
- No agent that requires proprietary APIs — everything runs with a Claude API key

---

## Contributing

See [CLAUDE.md](CLAUDE.md) for how skills are structured.
Each agent lives in `agents/`. Each skill is a Markdown file in `skills/`.

Open an issue before building a new agent — we want to make sure it fits the system.
