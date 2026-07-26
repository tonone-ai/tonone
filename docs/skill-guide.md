# Skill Authoring Guide

How to write and improve skills for Tonone agents.

## What is a Skill?

A skill is a Markdown file (`SKILL.md`) that defines a slash command. When a user runs `/forge-audit`, Claude Code loads the skill's content as a system prompt and the agent follows its instructions.

Skills are pure prompts — no backing code required.

## File Location

Every skill exists in two places:

```
skills/<skill-name>/SKILL.md          ← root (what users install)
team/<agent>/skills/<skill-name>/SKILL.md  ← source (where you edit)
```

When adding or editing a skill, update the source in `team/<agent>/skills/` and copy to `skills/` at the root. Both must stay in sync.

## Format

```markdown
---
name: agent-action
description: One-line summary — what it does and when to use it. Use when asked to "X", "Y", or "Z".
---

# Skill Title

You are AgentName — the [role] on the Engineering Team.

## Steps

### Step 0: Detect Environment

[environment detection logic]

### Step 1: [First Action]

[what to do, what to look for, what to output]

### Step 2: [Second Action]

...

## Key Rules

- [constraints and anti-patterns]

## Output Format

[what the final output should look like]
```

## Frontmatter Fields

| Field           | Required | Format                                   | Example                                                                        |
| --------------- | -------- | ---------------------------------------- | ------------------------------------------------------------------------------ |
| `name`          | Yes      | kebab-case                               | `forge-audit`                                                                  |
| `description`   | Yes      | Single line with trigger phrases         | `Full security audit — ... Use when asked to "audit", "check vulnerabilities"` |
| `allowed-tools` | No       | Comma-separated tool list                | `Read, Bash, Glob, Grep, WebFetch, WebSearch, AskUserQuestion`                 |
| `version`       | No       | Semver                                   | `0.6.4`                                                                        |
| `author`        | No       | Name and contact                         | `tonone-ai <hello@tonone.ai>`                                                  |
| `license`       | No       | SPDX identifier                          | `MIT`                                                                          |
| `compatibility` | No       | Free text, marketplace-facing            | `Designed for Claude Code`                                                     |
| `tags`          | No       | YAML array, `[team, domain, ...]`, max 5 | `[engineering, infrastructure, cloud, audit]`                                  |

`name` and `description` are hand-authored per skill. `compatibility` and `tags` are backfilled
across all 613 `SKILL.md` files by `scripts/gen-skill-metadata.py` — idempotent, safe to re-run
after adding a new skill or agent. `tags` come from a per-agent domain table plus the skill's own
name suffix, so identical skills always get identical tags; see the script for the full agent → tag
mapping.

### Writing Good Descriptions

The description determines when Claude Code suggests the skill. Include:

- **What it does** in plain language
- **Trigger phrases** — quoted phrases users might say

```yaml
# Good — specific triggers, clear scope
description: Build infrastructure from scratch using IaC. Use when asked to "set up infra", "provision infrastructure", "create cloud resources", or "terraform for this".

# Bad — vague, no triggers
description: Helps with infrastructure tasks.
```

## Anatomy of a Good Skill

### Identity Line

Always start the body with who the agent is:

```markdown
You are Forge — the infrastructure engineer on the Tonone team.
```

This anchors the agent's persona and expertise.

### Step 0: Detect Environment

Most skills should start by scanning the project:

```markdown
### Step 0: Detect Environment

Scan the project to identify the stack:

- Check for `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`
- Read config files for framework, database, cloud provider
- Note existing patterns and conventions
```

This ensures the agent adapts to the user's stack rather than assuming one.

### Workflow Steps

Number your steps. Each step should:

- Have a clear action verb in the heading
- Explain what to look for, not just what to do
- Include example output formats (tables, code blocks) where helpful
- Be specific about tool usage (`grep`, `read`, `write`)

```markdown
### Step 1: Map All Routes

Find and read all route definitions. Build a complete endpoint map:

| Method | Path       | Auth | Handler             | Description |
| ------ | ---------- | ---- | ------------------- | ----------- |
| GET    | /api/users | JWT  | UserController.list | List users  |
```

### Key Rules

List constraints that prevent common mistakes:

```markdown
## Key Rules

- Never generate placeholder or example code — only production-ready output
- Detect the existing stack before suggesting anything
- If a decision requires user input, ask — don't assume
- Don't add dependencies without checking what's already installed
```

### Output Format

Define what the skill produces:

```markdown
## Output Format

Deliver a single Markdown report with:

1. Executive summary (3-5 bullets)
2. Findings table with severity ratings
3. Recommended actions, ordered by impact
```

## Skill Categories

Every agent typically has three types of skills:

| Type       | Pattern                        | Purpose                       | Example                         |
| ---------- | ------------------------------ | ----------------------------- | ------------------------------- |
| **Build**  | `agent-noun`                   | Create something from scratch | `/forge-infra`, `/spine-api`    |
| **Review** | `agent-audit` or `agent-check` | Audit existing systems        | `/warden-audit`, `/vigil-check` |
| **Recon**  | `agent-recon`                  | Survey a domain for takeover  | `/forge-recon`, `/spine-recon`  |

When adding a new skill, decide which category it falls into. Build skills are the most complex; recon skills are the most formulaic.

## Testing a Skill

1. Install your local clone:
   ```
   /plugin install /path/to/your/clone
   ```
2. Run the skill against a real codebase — not a toy project
3. Check that:
   - Environment detection works for at least 2 different stacks
   - Output format matches what the skill promises
   - The agent doesn't hallucinate tools or packages
   - Anti-patterns listed in Key Rules are actually avoided

## Common Mistakes

- **Too vague**: "Analyze the codebase" — specify what to look for
- **Too rigid**: Hardcoding file paths instead of detecting them
- **No output format**: The agent rambles instead of producing structured results
- **Missing Step 0**: Agent assumes a stack instead of detecting it
- **Over-long descriptions**: Keep frontmatter `description` to one line
