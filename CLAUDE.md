# Engineering Team

Monorepo for the Engineering Team agent marketplace — Claude Code agents that act as specialized engineers.

## Structure

```
eng-team/
├── src/engteam/           ← marketplace CLI (list, install, run, update)
├── cloud-architecture/     ← team: Cloud Architecture
│   └── cloud-run-specialist/   ← agent (self-contained Python package)
├── security/               ← team: Security (future)
├── devops/                 ← team: DevOps (future)
└── templates/new-agent/    ← scaffolding for new agents
```

## Adding a New Agent

1. Copy `templates/new-agent/` to `<team>/<agent-name>/`
2. Implement the agent (analyzers, tools, dashboard)
3. Add an entry to `src/engteam/registry.py`
4. Agent must expose: `<package> install` and `<package> analyze` CLI commands

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

# Individual agent
cd cloud-architecture/cloud-run-specialist && uv sync && uv run pytest
```
