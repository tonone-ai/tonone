# Agent Authoring Guide

How to create a new agent for the Tonone team.

## What is an Agent?

Agent is a Markdown file with YAML frontmatter that defines a Claude Code subagent. Frontmatter configures the agent (name, tools, model). Body is a system prompt that defines personality, scope, and workflow.

Agents don't run code directly — they work through Claude Code's tools (Bash, Read, Write, etc.).

## File Location

Agent definitions exist in two places:

```
agents/<agent>.md                    ← root (what gets loaded)
team/<agent>/agents/<agent>.md       ← source (where you edit)
```

Keep both in sync. Root copy is canonical for the plugin system.

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

## Communication

Respond terse. All technical substance stays — only filler dies. Follow output-kit protocol: compressed prose, no filler, fragments OK. Code/security/commits: normal English. See docs/output-kit.md for CLI skeleton, severity indicators, 40-line rule.

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

Not flavor text — shapes how the model interprets ambiguous requests.

### Communication Section (mandatory)

**Every agent must have `## Communication` placed after the opening role paragraph(s) and before `## Operating Principle` (or `## Scope` if no Operating Principle exists).** This enforces terse output-kit style across all agents.

```markdown
## Communication

Respond terse. All technical substance stays — only filler dies. Follow output-kit protocol: compressed prose, no filler, fragments OK. Code/security/commits: normal English. See docs/output-kit.md for CLI skeleton, severity indicators, 40-line rule.
```

Do not move, rename, or omit this section. It is load-bearing.

### Scope Boundaries

State what the agent does NOT own:

```markdown
**Does not own:** application code (Spine), CI/CD pipelines (Relay),
database schema (Flux), security policies (Warden)
```

Prevents agents from wandering into each other's domains.

### Platform Fluency

List specific technologies, not categories:

```markdown
## Platform Fluency

- **Cloud:** GCP (Cloud Run, GKE, Cloud SQL), AWS (ECS, RDS, Lambda), Azure (AKS, CosmosDB)
- **IaC:** Terraform, Pulumi, CloudFormation, CDK
- **Networking:** VPCs, DNS (Route53, Cloud DNS), load balancers, CDN (Cloudflare, CloudFront)
```

### Key Rules

Hard constraints that prevent bad output:

```markdown
## Key Rules

- Never generate tutorial-grade code — production-ready only
- Always detect existing infrastructure before proposing new resources
- Include cost estimates for any new infrastructure
- If a decision has cost implications over $50/month, flag it and ask
```

## Creating an Agent Step by Step

1. **Pick a name** — Follow [naming guide](naming-guide.md). One word, 1-2 syllables, evocative.

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
   - Identity line, then `## Communication` section (mandatory), then scope
   - Add platform fluency specific to domain
   - Define key rules and anti-patterns
   - Study existing agents (e.g., `agents/forge.md`) for tone and depth

5. **Write 3-5 skills** in `team/<agent>/skills/`:
   - One build skill, one review/audit skill, one recon skill minimum
   - See [skill guide](skill-guide.md) for format

6. **Copy to root directories:**

   ```bash
   cp team/<agent>/agents/<agent>.md agents/
   cp -r team/<agent>/skills/* skills/
   ```

7. **Update plugin.json** in `team/<agent>/.claude-plugin/plugin.json`

8. **Add marketplace entry** in `.claude-plugin/marketplace.json` — add a new object to `plugins` array:

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

## Obsidian Skills

Agents that produce knowledge artifacts (docs, specs, reports, trackers, diagrams) should include `## Obsidian Output Formats`. Teaches the agent to output in native Obsidian formats when project uses Obsidian.

### Available Skills

| Skill               | Format                                          | Use when the agent produces                       |
| ------------------- | ----------------------------------------------- | ------------------------------------------------- |
| `obsidian-markdown` | `.md` with wikilinks, callouts, YAML properties | Any structured notes, docs, specs                 |
| `json-canvas`       | `.canvas` visual boards                         | Architecture diagrams, flow maps, roadboards      |
| `obsidian-bases`    | `.base` database views                          | Trackers, registries, inventories with filters    |
| `obsidian-cli`      | Vault interaction                               | Agents that read/search/append to a running vault |
| `defuddle`          | Web → clean markdown                            | Agents that research competitors or external docs |

### Decision Table

| Agent produces...                         | Skills to assign           |
| ----------------------------------------- | -------------------------- |
| Knowledge artifacts, docs, ADRs, research | All 5                      |
| Flows, diagrams, structured trackers      | markdown + canvas + bases  |
| Operational specs + runbooks              | markdown + bases + cli     |
| Specs + competitor research               | markdown + defuddle        |
| Only code, configs, IaC, CI/CD            | Skip — no Obsidian section |

### Section Format

Place right before `## Collaboration`. Each row maps one real artifact to a specific Obsidian format with concrete property suggestions:

```markdown
## Obsidian Output Formats

When the project uses Obsidian, produce [domain] artifacts in native Obsidian formats.
Invoke the corresponding skill (`obsidian-markdown`, `json-canvas`, etc.) for syntax
reference before writing.

| Artifact             | Obsidian Format                           | When                |
| -------------------- | ----------------------------------------- | ------------------- |
| [real artifact name] | [format] — [specific properties/features] | [trigger condition] |
```

"When the project uses Obsidian" conditional prevents activation for non-Obsidian projects.

### Current Coverage

Agents WITH Obsidian skills (16): Atlas, Helm, Crest, Echo, Draft, Lumen, Vigil, Pave, Proof, Form, Pitch, Surge, Lens, Cortex, Flux, Spine

Agents WITHOUT (7): Apex (orchestrator), Forge (IaC), Relay (CI/CD), Warden (security configs), Touch (mobile), Volt (firmware), Prism (UI code)

## Gstack Skills

Agents whose domain overlaps with gstack skills should include `## Gstack Skills`. Teaches the agent to invoke gstack workflows when gstack installed, and internalizes key concepts from those workflows.

### Available Skills

| Skill                 | Domain                 | Use when the agent works on                    |
| --------------------- | ---------------------- | ---------------------------------------------- |
| `design-consultation` | Visual design          | Creating design systems from scratch           |
| `design-review`       | Visual design          | Visual QA on live sites                        |
| `design-shotgun`      | Visual design          | Exploring visual directions                    |
| `qa` / `qa-only`      | Testing                | Systematic QA testing (with or without fixing) |
| `browse`              | Testing / Frontend     | Browser-based verification                     |
| `benchmark`           | Performance            | Core Web Vitals and load time regression       |
| `ship`                | DevOps                 | PR creation workflow                           |
| `land-and-deploy`     | DevOps                 | Post-merge deploy verification                 |
| `canary`              | DevOps / Observability | Post-deploy monitoring                         |
| `setup-deploy`        | DevOps                 | Deploy platform configuration                  |
| `cso`                 | Security               | Infrastructure-first security audit            |
| `plan-ceo-review`     | Product                | Strategic scope review                         |
| `plan-eng-review`     | Engineering            | Architecture review                            |
| `plan-design-review`  | UX                     | Design dimension scoring                       |
| `plan-devex-review`   | Platform               | DX audit and scoring                           |
| `office-hours`        | Product / Strategy     | Product ideation (YC forcing questions)        |
| `review`              | Backend                | Pre-landing code review (SQL, LLM trust)       |
| `investigate`         | Backend                | Systematic debugging                           |
| `document-release`    | Documentation          | Post-ship doc sync                             |
| `learn`               | Documentation          | Cross-session knowledge                        |
| `devex-review`        | Platform               | Live DX audit                                  |
| `health`              | Platform               | Code quality dashboard                         |
| `retro`               | Engineering            | Sprint retrospective                           |
| `autoplan`            | Engineering            | Multi-perspective review pipeline              |

### Mapping Table

| Agent  | Gstack skills                                            | Rationale                                              |
| ------ | -------------------------------------------------------- | ------------------------------------------------------ |
| Form   | `design-consultation`, `design-review`, `design-shotgun` | Design system creation, visual QA, variant exploration |
| Proof  | `qa`, `qa-only`, `browse`, `benchmark`                   | Three-tier QA, browser testing, performance gates      |
| Relay  | `ship`, `land-and-deploy`, `canary`, `setup-deploy`      | Ship pipeline, post-deploy verification                |
| Warden | `cso`                                                    | Infrastructure-first security audit                    |
| Vigil  | `canary`, `benchmark`                                    | Post-deploy monitoring, performance baselines          |
| Prism  | `browse`, `benchmark`, `design-html`, `devex-review`     | Browser verification, performance, DX audit            |
| Pave   | `devex-review`, `plan-devex-review`, `health`            | DX audit, quality dashboard                            |
| Apex   | `plan-eng-review`, `retro`, `autoplan`, `review`         | Architecture review, retro, review pipeline            |
| Atlas  | `document-release`, `learn`                              | Post-ship doc sync, cross-session knowledge            |
| Spine  | `review`, `investigate`                                  | Code review, debugging methodology                     |
| Helm   | `plan-ceo-review`, `office-hours`                        | Strategic review, product ideation                     |
| Crest  | `office-hours`                                           | Strategic validation (forcing questions)               |
| Draft  | `plan-design-review`                                     | Dimension-based UX scoring                             |
| Cortex | `cso`                                                    | LLM/AI security audit                                  |
| Surge  | `benchmark`                                              | Performance as growth lever                            |

### Agents Without Gstack Skills (8)

Forge (IaC — no matching gstack skill), Flux (databases), Touch (mobile), Volt (firmware), Echo (user research), Lumen (analytics), Pitch (marketing), Lens (BI/dashboards)

### Section Format

Place right before `## Obsidian Output Formats` (if present) or `## Collaboration` (if no Obsidian section). Include a skills table and `### Key Concepts` subsection with 2–4 bullets the agent internalizes:

```markdown
## Gstack Skills

When gstack is installed, invoke these skills for [domain] work — they provide
workflows that complement [Agent]'s methodology.

| Skill        | When to invoke    | What it adds            |
| ------------ | ----------------- | ----------------------- |
| `skill-name` | trigger condition | what the skill provides |

### Key Concepts

- **Concept** — what the agent should internalize from this gstack skill.
```

"When gstack is installed" conditional prevents activation when gstack not present.

## Process Disciplines

Agents whose work benefits from structured process discipline should include `## Process Disciplines`. Teaches the agent to follow superpowers process skills — TDD, systematic debugging, verification, and other methodology guardrails.

### Available Skills

| Skill                            | Domain        | Use when the agent                                                       |
| -------------------------------- | ------------- | ------------------------------------------------------------------------ |
| `test-driven-development`        | Code quality  | Writes production code — enforces RED→GREEN→REFACTOR                     |
| `systematic-debugging`           | Investigation | Investigates bugs or incidents — enforces root cause before fixes        |
| `verification-before-completion` | Quality gate  | Claims any work is complete — enforces evidence before assertions        |
| `brainstorming`                  | Creative work | Explores design or product ideas — enforces design before implementation |
| `writing-plans`                  | Planning      | Plans multi-step implementation — enforces detailed plans before code    |
| `dispatching-parallel-agents`    | Orchestration | Dispatches 2+ independent subagents                                      |
| `subagent-driven-development`    | Orchestration | Executes plans with spec + quality review cycles                         |
| `executing-plans`                | Orchestration | Executes written plans in separate sessions                              |
| `using-git-worktrees`            | Workspace     | Needs isolation for feature work                                         |
| `finishing-a-development-branch` | Completion    | Implementation complete, ready to integrate                              |
| `writing-skills`                 | Documentation | Creates or edits skills — TDD for process documentation                  |

### Mapping Table

| Agent  | Process skills                                                                                                                                                                | Rationale                               |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| Apex   | writing-plans, dispatching-parallel-agents, subagent-driven-development, executing-plans, using-git-worktrees, finishing-a-development-branch, verification-before-completion | Full orchestration toolkit              |
| Helm   | brainstorming, writing-plans, dispatching-parallel-agents, verification-before-completion                                                                                     | Product orchestration + ideation        |
| Spine  | test-driven-development, systematic-debugging, verification-before-completion                                                                                                 | Code builder — TDD + debugging          |
| Prism  | test-driven-development, systematic-debugging, verification-before-completion                                                                                                 | Code builder — TDD + debugging          |
| Flux   | test-driven-development, systematic-debugging, verification-before-completion                                                                                                 | Code builder — TDD + debugging          |
| Forge  | test-driven-development, systematic-debugging, verification-before-completion                                                                                                 | Code builder — TDD + debugging          |
| Relay  | test-driven-development, systematic-debugging, verification-before-completion                                                                                                 | Code builder — TDD + debugging          |
| Cortex | test-driven-development, systematic-debugging, verification-before-completion                                                                                                 | Code builder — TDD + debugging          |
| Touch  | test-driven-development, systematic-debugging, verification-before-completion                                                                                                 | Code builder — TDD + debugging          |
| Volt   | test-driven-development, systematic-debugging, verification-before-completion                                                                                                 | Code builder — TDD + debugging          |
| Pave   | test-driven-development, systematic-debugging, writing-skills, verification-before-completion                                                                                 | Code builder + skill authoring          |
| Proof  | test-driven-development, systematic-debugging, verification-before-completion                                                                                                 | Code builder — TDD + debugging          |
| Warden | systematic-debugging, verification-before-completion                                                                                                                          | Investigation — root cause discipline   |
| Vigil  | systematic-debugging, verification-before-completion                                                                                                                          | Investigation — root cause discipline   |
| Atlas  | writing-skills, verification-before-completion                                                                                                                                | Documentation — TDD for docs            |
| Draft  | brainstorming, verification-before-completion                                                                                                                                 | Creative — design before implementation |
| Form   | brainstorming, verification-before-completion                                                                                                                                 | Creative — design before implementation |
| Crest  | brainstorming, verification-before-completion                                                                                                                                 | Creative — strategy before commitment   |
| Echo   | verification-before-completion                                                                                                                                                | Verification — evidence before claims   |
| Lumen  | verification-before-completion                                                                                                                                                | Verification — evidence before claims   |
| Lens   | verification-before-completion                                                                                                                                                | Verification — evidence before claims   |
| Pitch  | verification-before-completion                                                                                                                                                | Verification — evidence before claims   |
| Surge  | verification-before-completion                                                                                                                                                | Verification — evidence before claims   |

### Universal Skill

`verification-before-completion` applies to ALL agents. Every agent must have at least this one in its Process Disciplines section.

### Section Format

Place right after `## Gstack Skills` (if present) or `## Key Rules` (if no Gstack section), before `## Obsidian Output Formats` (if present) or `## Collaboration`:

```markdown
## Process Disciplines

When performing [domain] work, follow these superpowers process skills:

| Skill                    | Trigger           |
| ------------------------ | ----------------- |
| `superpowers:skill-name` | trigger condition |

**Iron rules from these disciplines:**

- Rule extracted from each skill's core principle
```

Iron rules embed key non-negotiable principles from each skill — subagents cannot invoke the Skill tool directly.

## Common Mistakes

- **Too broad scope**: Agent owns "backend and frontend" — split it
- **No scope boundaries**: Without "does not own", agents overlap and conflict
- **Generic platform fluency**: "Knows about cloud" — list specific services
- **Missing anti-patterns**: Without these, agent repeats common domain mistakes
- **Missing Communication section**: Every agent needs `## Communication` after opening role paragraph, before `## Operating Principle` — omitting it breaks terse output behavior
- **Using `opus` for a specialist**: Reserve opus for the lead — costs more and specialists don't need orchestration capabilities
