# Agent Authoring Guide

How to create a new agent for the Tonone team.

## What is an Agent?

An agent is a Markdown file with YAML frontmatter that defines a Claude Code subagent. The frontmatter configures the agent (name, tools, model). The body is a system prompt that defines its personality, scope, and workflow.

Agents don't run code directly — they work through Claude Code's tools (Bash, Read, Write, etc.).

## File Location

Agent definitions exist in two places:

```
agents/<agent>.md                    ← root (what gets loaded)
team/<agent>/agents/<agent>.md       ← source (where you edit)
```

Keep both in sync. The root copy is canonical for the plugin system.

## Frontmatter

```yaml
---
name: agent-name
description: One-line role summary — domain keywords
tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
model: sonnet
---
```

| Field         | Required | Values             | Notes                                              |
| ------------- | -------- | ------------------ | -------------------------------------------------- |
| `name`        | Yes      | kebab-case         | Matches the filename without `.md`                 |
| `description` | Yes      | One line           | Role + domain keywords                             |
| `tools`       | Yes      | Array of strings   | Which Claude Code tools the agent can use          |
| `model`       | Yes      | `sonnet` or `opus` | Use `sonnet` for specialists, `opus` only for lead |

### Tools

Standard specialist toolkit:

```yaml
tools:
  - Bash # Run shell commands
  - Read # Read files
  - Glob # Find files by pattern
  - Grep # Search file contents
  - Write # Create/overwrite files
```

Only Apex (the lead) gets the `Agent` tool to dispatch other agents. Don't add it to specialists.

### Model Selection

- **`sonnet`** — All specialists. Fast, cost-efficient, excellent for focused domain work.
- **`opus`** — Lead agent only. Needed for orchestration, scoping, and multi-agent coordination.

## Prompt Structure

The body of the agent definition follows this pattern:

```markdown
You are [Name] — the [role] on the Tonone team. [One sentence about mindset.]

## Scope

**Owns:** [comma-separated list of what this agent is responsible for]

**Does not own:** [what belongs to other agents — prevents scope creep]

## Platform Fluency

[List of tools, frameworks, and services this agent should know]

## Mindset

[2-3 bullets about how this agent thinks and approaches problems]

## Workflow

[Default workflow when given a task]

## Key Rules

[Hard constraints — what the agent must always or never do]

## Anti-Patterns

[Common mistakes this agent should avoid]
```

### Identity Line

Start with a strong identity statement:

```markdown
You are Forge — the infrastructure engineer on the Tonone team.
You think in systems, networks, and resource graphs.
```

This isn't flavor text — it shapes how the model interprets ambiguous requests.

### Scope Boundaries

Explicitly state what the agent does NOT own:

```markdown
**Does not own:** application code (Spine), CI/CD pipelines (Relay),
database schema (Flux), security policies (Warden)
```

This prevents agents from wandering into each other's domains.

### Platform Fluency

List specific technologies, not categories:

```markdown
## Platform Fluency

- **Cloud:** GCP (Cloud Run, GKE, Cloud SQL), AWS (ECS, RDS, Lambda), Azure (AKS, CosmosDB)
- **IaC:** Terraform, Pulumi, CloudFormation, CDK
- **Networking:** VPCs, DNS (Route53, Cloud DNS), load balancers, CDN (Cloudflare, CloudFront)
```

### Key Rules

These are the hard constraints that prevent bad output:

```markdown
## Key Rules

- Never generate tutorial-grade code — production-ready only
- Always detect existing infrastructure before proposing new resources
- Include cost estimates for any new infrastructure
- If a decision has cost implications over $50/month, flag it and ask
```

## Creating an Agent Step by Step

1. **Pick a name** — Follow the [naming guide](naming-guide.md). One word, 1-2 syllables, evocative.

2. **Copy the template:**

   ```bash
   cp -r templates/new-agent/ team/<agent-name>/
   ```

3. **Replace placeholders** in all files:
   - `AGENT_NAME` → Display name (e.g., `Forge`)
   - `AGENT_SLUG` → Kebab-case (e.g., `forge`)
   - `AGENT_DESCRIPTION` → One-line role summary
   - `TEAM_LABEL` → Role label (e.g., `Infrastructure`)

4. **Write the agent definition** in `team/<agent>/agents/<agent>.md`:
   - Start with identity and scope
   - Add platform fluency specific to the domain
   - Define key rules and anti-patterns
   - Study existing agents (e.g., `agents/forge.md`) for tone and depth

5. **Write 3-5 skills** in `team/<agent>/skills/`:
   - One build skill, one review/audit skill, one recon skill minimum
   - See the [skill guide](skill-guide.md) for format

6. **Copy to root directories:**

   ```bash
   cp team/<agent>/agents/<agent>.md agents/
   cp -r team/<agent>/skills/* skills/
   ```

7. **Update plugin.json** in `team/<agent>/.claude-plugin/plugin.json`

8. **Add marketplace entry** in `.claude-plugin/marketplace.json` — add a new object to the `plugins` array:

   ```json
   {
     "name": "<agent>-<domain>",
     "description": "...",
     "version": "0.1.0",
     "source": "./team/<agent>",
     "author": { "name": "tonone-ai", "url": "https://tonone.ai" },
     "category": "<domain>",
     "tags": ["relevant", "tags"]
   }
   ```

9. **Test** by installing locally and running each skill against a real project.

## Common Mistakes

- **Too broad scope**: An agent that owns "backend and frontend" — split it
- **No scope boundaries**: Without "does not own", agents overlap and conflict
- **Generic platform fluency**: "Knows about cloud" — list specific services
- **Missing anti-patterns**: Without these, the agent repeats common domain mistakes
- **Using `opus` for a specialist**: Reserve opus for the lead — it costs more and specialists don't need orchestration capabilities
