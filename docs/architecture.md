# Architecture

How Tonone is structured and why.

## Overview

Tonone is a Claude Code plugin that installs 15 agents and 74 skills. Everything is prompt-based — agents are Markdown system prompts, skills are Markdown workflow definitions. No runtime code is required.

```
User runs /forge-audit
  → Claude Code loads the skill prompt from skills/forge-audit/SKILL.md
  → Claude Code loads the agent definition from agents/forge.md
  → The agent executes using Claude Code's tools (Bash, Read, Write, etc.)
```

## Directory Structure

```
tonone/
├── .claude-plugin/           ← Plugin metadata (what users install)
│   ├── plugin.json           ← Package name, version, author
│   └── marketplace.json      ← Registry of all installable plugins
│
├── agents/                   ← Agent definitions (loaded by Claude Code)
│   ├── apex.md
│   ├── forge.md
│   └── ...                   (15 files)
│
├── skills/                   ← Skill definitions (loaded by Claude Code)
│   ├── apex-plan/SKILL.md
│   ├── forge-audit/SKILL.md
│   └── ...                   (74 directories)
│
├── team/                     ← Source of truth for each agent
│   ├── forge/
│   │   ├── .claude-plugin/   ← Individual plugin manifest
│   │   ├── agents/           ← Agent definition (edit here)
│   │   ├── skills/           ← Skill definitions (edit here)
│   │   ├── hooks/            ← Lifecycle hooks (post-install)
│   │   ├── scripts/          ← Python package + venv setup
│   │   └── tests/            ← Test directory
│   ├── relay/
│   └── ...                   (15 directories)
│
├── templates/new-agent/      ← Scaffolding for new agents
├── docs/                     ← Contributor documentation
├── CLAUDE.md                 ← Development conventions
├── CONTRIBUTING.md           ← Contributor guide
└── README.md                 ← User-facing documentation
```

## Why Files Exist in Two Places

### Agents: `team/<agent>/agents/` and `agents/`

The `team/` directory is the **source of truth** — it's where you develop and edit. The root `agents/` directory is what Claude Code actually loads when the plugin is installed.

Why not just use one location? The plugin system needs agent definitions at the root level for discovery. But each agent's full context (skills, hooks, scripts, tests) lives together in `team/` for development ergonomics.

**Rule:** Edit in `team/<agent>/agents/`, copy to `agents/`.

### Skills: `team/<agent>/skills/` and `skills/`

Same pattern. Skills are authored in `team/<agent>/skills/` alongside their agent, then copied to the flat `skills/` directory at root.

The flat root structure exists because Claude Code's plugin system discovers skills from the install root. Nested paths under `team/` wouldn't be found.

**Rule:** Edit in `team/<agent>/skills/`, copy to `skills/`.

## Plugin System

### plugin.json

Every plugin level has a `plugin.json`:

```json
{
  "name": "tonone",
  "version": "0.2.0",
  "description": "...",
  "author": { "name": "tonone-ai", "url": "https://tonone.ai" },
  "repository": "https://github.com/tonone-ai/tonone",
  "license": "MIT",
  "keywords": ["agents", "engineering-team"]
}
```

- **Root** (`.claude-plugin/plugin.json`) — The main package. Installing `tonone` gets everything.
- **Team** (`team/<agent>/.claude-plugin/plugin.json`) — Individual agent packages. These exist for standalone installs but most users install the root bundle.

### marketplace.json

The marketplace registry (`.claude-plugin/marketplace.json`) lists all installable plugins:

```json
{
  "name": "tonone-ai",
  "owner": { "name": "tonone-ai", "url": "https://tonone.ai" },
  "plugins": [
    {
      "name": "tonone",
      "source": "./",
      "tags": ["bundle", "full-team"]
    },
    {
      "name": "forge-infra",
      "source": "./team/forge",
      "category": "infrastructure",
      "tags": ["infrastructure", "cloud"]
    }
  ]
}
```

The `source` field points to the directory containing the plugin's `.claude-plugin/plugin.json`.

### Install Flow

```
/plugin marketplace add tonone-ai/tonone     ← registers the marketplace
/plugin install tonone@tonone-ai              ← installs root bundle (all 15 agents)
/plugin install forge-infra@tonone-ai         ← or install one agent
```

## Agent Model

```
                    ┌─────────┐
                    │  Apex   │  model: opus
                    │ (Lead)  │  tools: + Agent
                    └────┬────┘
                         │ dispatches
        ┌────────┬───────┼───────┬────────┐
        ▼        ▼       ▼       ▼        ▼
    ┌───────┐┌───────┐┌──────┐┌───────┐┌──────┐
    │ Forge ││ Spine ││ Flux ││Warden ││ ...  │  model: sonnet
    │       ││       ││      ││       ││      │  tools: standard
    └───────┘└───────┘└──────┘└───────┘└──────┘
       14 specialists
```

- **Apex** uses `opus` and the `Agent` tool to coordinate specialists
- **Specialists** use `sonnet` and the standard tool set (Bash, Read, Glob, Grep, Write)
- Users can invoke any agent directly via skills, or go through Apex for orchestrated workflows

## Hooks

Each agent has a `hooks/hooks.json` that runs `setup.sh` on post-install:

```json
{
  "hooks": [
    {
      "event": "post_install",
      "command": "bash scripts/setup.sh"
    }
  ]
}
```

The setup script creates a Python virtual environment. This exists for future use — the Python scaffolding is ready for agents that need local analysis tools, but current agents work entirely through Claude Code's built-in tools.

## Scripts (Future)

Each agent has a Python package in `team/<agent>/scripts/`:

```
scripts/
├── <agent>_agent/
│   ├── __init__.py
│   └── runner.py       ← scaffold (NotImplementedError)
├── pyproject.toml
└── setup.sh
```

This is scaffolding for future backing implementations. If an agent needs local computation (e.g., parsing ASTs, running static analysis, processing large datasets), the Python package is where that logic would live. Today, all agents work purely through prompts.
