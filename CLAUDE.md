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
tonone/
├── .claude-plugin/         ← root plugin (installs full team)
├── agents/                 ← all agent definitions (Apex + 12 specialists)
│   ├── apex.md
│   ├── forge.md
│   ├── relay.md
│   └── ...
├── skills/                 ← root-level Apex skills
│   ├── apex-plan/
│   ├── apex-review/
│   ├── apex-status/
│   └── apex-takeover/
├── team/                   ← specialist source (scripts, skills, hooks, tests)
│   ├── forge/
│   │   ├── .claude-plugin/ ← plugin manifest
│   │   ├── agents/         ← agent definition (canonical copy)
│   │   ├── skills/         ← slash commands
│   │   ├── hooks/          ← lifecycle hooks
│   │   ├── scripts/        ← Python source + venv
│   │   └── tests/
│   ├── relay/
│   ├── spine/
│   └── ...
├── docs/                   ← naming guide, design docs
└── templates/new-agent/    ← scaffolding for new agents
```

## Adding a New Agent

1. Copy `templates/new-agent/` to `team/<agent-name>/`
2. Replace placeholders in plugin.json, agent def, skills
3. Implement analyzers in `scripts/<module>/`
4. Copy agent def to root `agents/` directory
5. See `docs/naming-guide.md` for naming conventions
6. Agent must expose skills via its plugin manifest

## Conventions

- Agent names: single word, 1-2 syllables, evocative of the domain (see `docs/naming-guide.md`)
- Skills: `/{agentname}-{action}` (e.g., `/cloudrun-dashboard`)
- Each agent is self-contained with own pyproject.toml, tests, hooks

## Development

```bash
# Individual agent (plugin layout)
cd team/forge/scripts && bash setup.sh
.venv/bin/python -m pytest ../tests/
```
