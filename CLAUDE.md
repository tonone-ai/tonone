# Engineering Team

Elite engineering team as Claude Code agents. 1 lead + 12 specialists. Simplicity is king. Scalability is best friend.

## The Team

| Agent | Hat | Owns |
|-------|-----|------|
| **Apex** | Engineering Lead | Orchestrates the team, scopes work, controls depth and budget |
| **Forge** | Infrastructure | Cloud services, networking, IaC, cost optimization |
| **Relay** | DevOps | CI/CD, deployments, GitOps, developer experience |
| **Spine** | Backend | APIs, system design, performance, distributed systems |
| **Flux** | Data | Databases, migrations, pipelines, data modeling |
| **Warden** | Security | IAM, secrets, compliance, threat modeling |
| **Vigil** | Observability + Reliability | Monitoring, alerting, SRE, incident response, SLOs |
| **Prism** | Frontend/DX | UI, internal tools, developer portals |
| **Cortex** | ML/AI | Model training, MLOps, feature engineering, LLM integration |
| **Touch** | Mobile | Native iOS/Android, cross-platform, app stores |
| **Volt** | Embedded/IoT | Firmware, microcontrollers, edge computing, protocols |
| **Atlas** | Knowledge Engineering | Architecture docs, ADRs, API specs, system diagrams |
| **Lens** | Data Analytics & BI | Dashboards, metrics design, reporting, data storytelling |

## Structure

```
eng-team/
├── .claude-plugin/         ← root plugin (installs Apex as entry point)
├── agents/                 ← root-level Apex agent definition
│   └── apex.md
├── skills/                 ← root-level Apex skills
│   ├── apex-plan/
│   ├── apex-review/
│   ├── apex-status/
│   └── apex-takeover/
├── marketplace.json        ← plugin marketplace registry
├── team/                   ← all specialists (each is a self-contained plugin)
│   ├── forge/
│   │   ├── .claude-plugin/ ← plugin manifest
│   │   ├── agents/         ← agent definition
│   │   ├── skills/         ← slash commands
│   │   ├── hooks/          ← lifecycle hooks
│   │   ├── scripts/        ← Python source + venv
│   │   └── tests/
│   ├── relay/
│   ├── spine/
│   ├── flux/
│   ├── warden/
│   ├── vigil/
│   ├── prism/
│   ├── cortex/
│   ├── touch/
│   ├── volt/
│   ├── atlas/
│   └── lens/
├── docs/                   ← naming guide, design docs
├── src/engteam/            ← marketplace CLI (pip path)
└── templates/new-agent/    ← scaffolding for new agents
```

## Adding a New Agent

1. Copy `templates/new-agent/` to `team/<agent-name>/`
2. Replace placeholders in plugin.json, agent def, skills
3. Implement analyzers in `scripts/<module>/`
4. Add entry to `marketplace.json`
5. See `docs/naming-guide.md` for naming conventions
6. Agent must expose: `<package>` CLI command

## Conventions

- Agent names: single word, 1-2 syllables, evocative of the domain (see `docs/naming-guide.md`)
- Skills: `/{agentname}-{action}` (e.g., `/cloudrun-dashboard`)
- PyPI: `{agentname}-agent` (e.g., `forge-agent`)
- Each agent is self-contained with own pyproject.toml, tests, hooks

## Development

```bash
# Marketplace CLI
cd eng-team && uv sync && uv run engteam list

# Individual agent (plugin layout)
cd team/forge/scripts && bash setup.sh
.venv/bin/python -m pytest ../tests/
```
