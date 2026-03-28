# Contributing to Tonone

Thanks for your interest in contributing. This guide covers the main ways to help.

## Getting Started

```bash
git clone https://github.com/tonone-ai/tonone.git
cd tonone
```

No build step required — Tonone is a Claude Code plugin made of Markdown agent definitions and skill prompts.

To test your changes, install your local clone in Claude Code:

```bash
/plugin install /path/to/your/clone
```

## Documentation

Before diving in, read the docs that cover what you're working on:

| Doc                                  | Covers                                                    |
| ------------------------------------ | --------------------------------------------------------- |
| [Architecture](docs/architecture.md) | How the plugin system works, why files are where they are |
| [Skill Guide](docs/skill-guide.md)   | How to write and improve skills                           |
| [Agent Guide](docs/agent-guide.md)   | How to create a new agent                                 |
| [Naming Guide](docs/naming-guide.md) | How to name a new agent                                   |

## Ways to Contribute

### Improve an existing skill

Skills live in `team/<agent>/skills/<skill-name>/SKILL.md` (source) and `skills/<skill-name>/SKILL.md` (root). Edit the source, copy to root. See the [skill guide](docs/skill-guide.md) for format and best practices.

Good improvements:

- Sharper workflow steps
- Better anti-pattern lists
- More precise platform detection logic
- Clearer output format specifications

### Propose a new agent

Open an issue using the **New Agent Proposal** template. Include:

- Agent name (see [naming guide](docs/naming-guide.md))
- Domain it covers
- Why existing agents don't cover it
- 3-5 skills it would have

### Add a new agent

Follow the step-by-step process in the [agent guide](docs/agent-guide.md). The short version:

1. Copy `templates/new-agent/` to `team/<agent-name>/`
2. Replace all placeholders
3. Write the agent definition and 3-5 skills
4. Copy agent and skills to root directories
5. Add marketplace entry in `.claude-plugin/marketplace.json`

### Fix bugs or improve documentation

Standard PR workflow — fork, branch, fix, PR.

## Testing Your Changes

There's no automated test suite for skills yet. Test manually:

1. **Install locally:**

   ```bash
   /plugin install /path/to/your/clone
   ```

2. **Run the skill** against a real codebase — not a toy project.

3. **Verify:**
   - Environment detection works (try at least 2 different stacks)
   - Output matches the format promised in the skill
   - The agent doesn't hallucinate tools, packages, or APIs
   - Anti-patterns listed in Key Rules are actually avoided

4. **Check file sync** — if you edited files in `team/`, make sure the root copies (`agents/`, `skills/`) match.

## Conventions

- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `docs:`, `chore:`
- **Agent names:** Single word, 1-2 syllables, evocative of the domain
- **Skill names:** `/<agent>-<action>` (e.g., `/forge-audit`)
- **Branches:** `feat/description`, `fix/description`, `docs/description`

## Pull Request Guidelines

- Keep PRs focused — one agent or one skill improvement per PR
- Include a clear description of what changed and why
- Skill changes should be tested against at least one real codebase
- Make sure root copies are in sync with `team/` sources

## Code of Conduct

Be respectful, constructive, and collaborative. We're building tools that help engineers — bring that same energy to the community.

## Questions?

Open a [discussion](https://github.com/tonone-ai/tonone/discussions) or file an issue.
