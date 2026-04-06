# tonone — Engineering + Product Team

> **Primary platform:** Claude Code. This file provides Codex CLI compatibility.
> For Claude Code setup, see `CLAUDE.md`.

Two AI teams. 23 agents total. Engineering executes. Product decides what to build and why.

## Engineering Team — 15 agents

| Agent      | Hat                         | Owns                                                          |
| ---------- | --------------------------- | ------------------------------------------------------------- |
| **Apex**   | Engineering Lead            | Orchestrates the team, scopes work, controls depth and budget |
| **Forge**  | Infrastructure              | Cloud services, networking, IaC, cost optimization            |
| **Relay**  | DevOps                      | CI/CD, deployments, GitOps, developer experience              |
| **Spine**  | Backend                     | APIs, system design, performance, distributed systems         |
| **Flux**   | Data                        | Databases, migrations, pipelines, data modeling               |
| **Warden** | Security                    | IAM, secrets, compliance, threat modeling                     |
| **Vigil**  | Observability + Reliability | Monitoring, alerting, SRE, incident response, SLOs            |
| **Prism**  | Frontend/DX                 | UI, internal tools, developer portals                         |
| **Cortex** | ML/AI                       | Model training, MLOps, feature engineering, LLM integration   |
| **Touch**  | Mobile                      | Native iOS/Android, cross-platform, app stores                |
| **Volt**   | Embedded/IoT                | Firmware, microcontrollers, edge computing, protocols         |
| **Atlas**  | Knowledge Engineering       | Architecture docs, ADRs, API specs, system diagrams           |
| **Lens**   | Data Analytics & BI         | Dashboards, metrics design, reporting, data storytelling      |
| **Proof**  | QA & Testing                | Test strategy, E2E suites, integration testing, flaky triage  |
| **Pave**   | Platform Engineering        | Developer experience, golden paths, service catalogs          |

## Product Team — 8 agents

| Agent     | Hat               | Owns                                                            |
| --------- | ----------------- | --------------------------------------------------------------- |
| **Helm**  | Head of Product   | Orchestrates the product team, writes briefs, hands off to Apex |
| **Echo**  | User Research     | User interviews, personas, Jobs-to-Be-Done, feedback synthesis  |
| **Lumen** | Product Analytics | Metrics frameworks, funnel analysis, OKRs, A/B test design      |
| **Draft** | UX Design         | User flows, information architecture, wireframes                |
| **Form**  | Visual Design     | Brand identity, color systems, typography, design system        |
| **Crest** | Product Strategy  | Roadmap planning, prioritization, competitive analysis          |
| **Pitch** | Product Marketing | Positioning, messaging, value prop, GTM, launch copy            |
| **Surge** | Growth            | Acquisition channels, activation funnels, retention playbooks   |

## Helm↔Apex Interface

Helm hands off to Apex using a 6-field product brief schema. See `agents/apex.md` → `## Helm Handoff` for the full contract.

## Structure

```
tonone/
├── agents/           ← agent definitions (read these to embody an agent)
│   ├── apex.md
│   ├── forge.md
│   └── ...           (23 files)
├── skills/           ← skill workflows (read these to follow a skill)
│   ├── apex-plan/SKILL.md
│   ├── forge-audit/SKILL.md
│   └── ...           (125 directories)
├── team/             ← source of truth per agent (canonical skills, hooks, scripts)
├── docs/             ← naming guide, architecture, output kit
└── templates/        ← scaffolding for new agents
```

Note: `.claude-plugin/` directories are Claude Code-specific and can be ignored in Codex.

## Using Agents in Codex

Agents are plain Markdown system prompts in `agents/<name>.md`. To work with a specific agent:

1. Read the agent definition: `agents/<name>.md`
2. Adopt that agent's role, priorities, and output style for the session
3. Use Codex's standard tools (shell, file read/write) as the agent would

Example: to work as Forge, read `agents/forge.md` and respond as the infrastructure specialist.

## Using Skills in Codex

Skills are workflow documents in `skills/<skill-name>/SKILL.md`. They have no special invocation — just read and follow them:

1. Find the relevant skill: `skills/` lists all 125 workflows
2. Read the skill file to understand the steps
3. Execute the workflow using Codex's tools

Example: to run the forge audit workflow, read `skills/forge-audit/SKILL.md` and follow the steps.

To find the right skill for a task, check the skill frontmatter `description` field — it explains when to use each skill.

## Conventions

- Agent names: single word, 1-2 syllables, evocative of the domain
- Skills: `{agentname}-{action}` naming pattern (e.g., `forge-audit`, `spine-review`)
- All agent output follows the output kit (`docs/output-kit.md`): 40-line max, box-drawing skeleton, unified severity indicators
- Edit agent definitions in `team/<agent>/agents/`, not the root `agents/` copies

## Adding a New Agent

1. Copy `templates/new-agent/` to `team/<agent-name>/`
2. Replace placeholders in plugin.json, agent def, skills
3. Copy agent def to root `agents/` directory
4. See `docs/naming-guide.md` for naming conventions
