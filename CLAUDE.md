# Engineering Team

Elite engineering team as Claude Code agents. 1 lead + 14 specialists. Simple by default. Scalable by design.

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
| **Proof** | QA & Testing | Test strategy, E2E suites, integration testing, flaky triage |
| **Pave** | Platform Engineering | Developer experience, golden paths, service catalogs |

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
- Skills: `/{agentname}-{action}` (e.g., `/forge-audit`)
- Each agent is self-contained with own pyproject.toml, tests, hooks
- All agent CLI output follows the output kit (`docs/output-kit.md`): 40-line max, box-drawing skeleton, unified severity indicators

## Development

```bash
# Individual agent (plugin layout)
cd team/forge/scripts && bash setup.sh
.venv/bin/python -m pytest ../tests/
```

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
