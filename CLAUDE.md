# Engineering Team

Monorepo for the Engineering Team agent marketplace - Claude Code agents that act as specialized engineers.

## Structure

```
eng-team/
├── marketplace.json        ← plugin marketplace registry
├── cloud-architecture/     ← team: Cloud Architecture
│   └── cloud-run-specialist/   ← plugin (self-contained)
│       ├── .claude-plugin/     ← plugin manifest
│       ├── agents/             ← agent definitions
│       ├── skills/             ← slash commands
│       ├── hooks/              ← lifecycle hooks
│       ├── scripts/            ← Python source + venv
│       └── tests/
├── src/engteam/            ← marketplace CLI (pip path)
└── templates/new-agent/    ← scaffolding for new agents
```

## Adding a New Agent

1. Copy `templates/new-agent/` to `<team>/<agent-name>/`
2. Replace placeholders in plugin.json, agent def, skills
3. Implement analyzers in `scripts/<module>/`
4. Add entry to `marketplace.json`
5. Add entry to `src/engteam/registry.py` (for pip path)
6. Agent must expose: `<package>` CLI command

## Conventions

- Teams: `cloud-architecture`, `security`, `devops`, `data`
- Agents: `{focus}-specialist` or `{role}` (e.g., `cloud-run-specialist`, `iam-auditor`)
- Skills: `/{shortname}-{action}` (e.g., `/cloudrun-dashboard`)
- PyPI: `{shortname}-agent` (e.g., `cloudrun-agent`)
- Each agent is self-contained with own pyproject.toml, tests, .claude/

## Development

```bash
# Marketplace CLI
cd eng-team && uv sync && uv run engteam list

# Individual agent (plugin layout)
cd cloud-architecture/cloud-run-specialist/scripts && bash setup.sh
.venv/bin/python -m pytest ../tests/
```
