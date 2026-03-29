# Atlas Output System — Design Spec

**Date:** 2026-03-29
**Status:** Approved
**Scope:** Output Kit (shared CLI design system) + 3 new Atlas skills (`atlas-report`, `atlas-changelog`, `atlas-present`)

---

## Problem

Agent CLI output is walls of unstructured text. No shared formatting. No progressive disclosure — pages of content dumped into a terminal. Reports that need breathing room have nowhere to go. No changelog history. No way to present big releases to non-technical stakeholders.

## Solution

Atlas becomes the **output architect** for the entire team. Four deliverables:

1. **Output Kit** — shared CLI design system all agents follow
2. **`atlas-report`** — renders full findings as styled HTML in browser
3. **`atlas-changelog`** — maintains per-repo + per-agent technical change logs
4. **`atlas-present`** — generates HTML presentation pages + Obsidian Canvas for big releases

---

## 0. Workspace Model

The entire system assumes a **mono-workspace** layout. Users are guided to:

1. Create a main folder (itself a git repo) as their workspace root
2. Clone all project repos inside it as sub-repos
3. Open Claude Code from the main folder

```
~/workspace/                  ← main folder (git repo, user opens CLI here)
├── .reports/                 ← HTML reports from all agents
├── .presentations/           ← HTML presentations + Canvas files
├── .changelog/CHANGELOG.md   ← big-picture cross-repo changelog
├── api-service/              ← sub-repo
│   └── .changelog/CHANGELOG.md  ← per-repo changelog
├── web-app/                  ← sub-repo
│   └── .changelog/CHANGELOG.md  ← per-repo changelog
├── infra/                    ← sub-repo
│   └── .changelog/CHANGELOG.md  ← per-repo changelog
└── ...
```

### Routing

Apex orchestrates from the main folder. When a task arrives, Apex analyzes scope and assigns agents to specific repo(s). Each agent receives the target repo path as context.

### Where artifacts live

| Artifact               | Location                                           | Committed to        |
| ---------------------- | -------------------------------------------------- | ------------------- |
| Per-repo changelog     | `{repo}/.changelog/CHANGELOG.md`                   | Sub-repo            |
| Per-repo reports       | `{repo}/.reports/{agent}-{skill}-{timestamp}.html` | Sub-repo            |
| Per-agent activity log | `team/{agent}/.activity.md`                        | Tonone plugin repo  |
| Cross-repo changelog   | `.changelog/CHANGELOG.md` (main folder)            | Main workspace repo |
| Presentations          | `.presentations/{date}-{title}/` (main folder)     | Main workspace repo |
| Obsidian Canvas        | `.presentations/{date}-{title}/{title}.canvas`     | Main workspace repo |

### User guidance

README and onboarding docs should recommend:

- Main folder as git repo for workspace-level history
- Sub-repos gitignored from main (they have their own git)
- `.reports/` and `.presentations/` committed to main repo so they're versioned and shareable

---

## 1. Output Kit (CLI Design System)

Shared file at `docs/output-kit.md`. Every agent skill references it for formatting rules.

### Core Rules

- **Max 40 lines** of terminal output. Summarize and offer `atlas-report` for full view.
- **No emoji.** Use box-drawing characters and unicode indicators.
- **Tables:** Box-drawing characters (`┌─┬─┐`), max 4 columns, truncate cells at 30 chars.

### CLI Skeleton

Every agent output follows this structure:

```
╭─ AGENT NAME ── skill-name ──────────────────╮

  ## One-line verdict

  ### Key Findings (3-5 bullets max)
  - ■ CRITICAL — Finding description
  - ▲ WARNING — Finding description
  - ● INFO — Finding description

  ### Metrics (if applicable)
  ┌──────────┬───────┬────────┐
  │ Metric   │ Value │ Status │
  └──────────┴───────┴────────┘

  ### Next Steps (2-3 max)
  → Action one
  → Action two

╰─ Full report: atlas-report ─────────────────╯
```

### Unified Severity System

| Indicator    | Meaning   | When to use                                       |
| ------------ | --------- | ------------------------------------------------- |
| `■ CRITICAL` | Fix now   | Security holes, data loss risk, broken production |
| `▲ WARNING`  | Fix soon  | Performance issues, tech debt with timeline       |
| `● INFO`     | Awareness | Observations, suggestions, no urgency             |

### Progressive Disclosure

CLI shows the summary. Detail lives in browser reports. Agents must not dump full findings into the terminal — summarize, then point to `/atlas-report`.

### Integration

Each agent skill's output section gets one line added:

```markdown
Follow the CLI output format defined in `docs/output-kit.md`.
```

Skills keep domain-specific output content (what findings to show, what tables) but delegate formatting rules to the kit.

---

## 2. `atlas-report` — Browser Reports

Full HTML reports for when CLI output isn't enough.

### Trigger

- User runs `/atlas-report`
- Agent suggests it when findings exceed the 40-line CLI budget

### Output

Single self-contained HTML file. Saved to the **target repo's** `.reports/` directory (`{repo}/.reports/{agent}-{skill}-{timestamp}.html`) so it's committed alongside the code it describes. Opens in default browser.

### HTML Design

- **Single file, zero dependencies** — inline CSS, no external assets
- **Dark theme** default with light toggle
- **Sticky nav sidebar** — jump between sections
- **Color-coded severity cards** — same `■ ▲ ●` system from CLI
- **Collapsible detail sections** — expand for code blocks, raw data, full findings
- **Mermaid diagrams** rendered inline via embedded Mermaid JS
- **Copy buttons** on code blocks and commands
- **Print-friendly** — `@media print` stylesheet for PDF export

### Report Template Sections

| Section  | Purpose                                    | When to include                  |
| -------- | ------------------------------------------ | -------------------------------- |
| Header   | Agent, skill, timestamp, target            | Always                           |
| Summary  | Executive summary, 3-5 bullets             | Always                           |
| Findings | Full findings with severity, evidence, fix | When there are findings          |
| Metrics  | Tables, inline SVG charts, comparisons     | When quantitative data exists    |
| Diagrams | Mermaid architecture/flow diagrams         | When system relationships matter |
| Timeline | Chronological event sequence               | For audits, incidents            |
| Actions  | Prioritized next steps with owners         | Always                           |

Not every report uses every section — template adapts to what the skill produced.

---

## 3. `atlas-changelog` — Technical Change Logs

Two layers for internal engineering audience.

### Per-Repo Changelog

Lives at `{repo}/.changelog/CHANGELOG.md` inside the target sub-repo. Committed to that repo's git history.

**Entry format:**

```markdown
## 2026-03-29

### spine — API endpoint authentication added

- Added JWT middleware to `/api/users` and `/api/orders`
- Rate limiting configured: 100 req/min per token
- Migration: `migrations/024_add_auth_tokens.sql`

### forge — Infrastructure scaled

- Redis cluster: 1 node → 3 nodes (eu-west-1)
- Reason: cache hit rate dropped below 80%
```

**Rules:**

- Date headers, agent name, one-line title, 2-4 bullet details
- Link to files changed when relevant
- No prose — scannable, grep-friendly
- Most recent entries at top

### Per-Agent Activity Log

Lives at `team/{agent}/.activity.md`. Tracks what this agent did across all repos/sessions.

**Entry format:**

```markdown
## 2026-03-29 01:15 — tonone/api-service

**Action:** API authentication hardened
**Skill:** spine-api
**Files:** 4 modified, 1 created
**Verdict:** ■ 2 critical findings fixed, ▲ 1 warning deferred
```

**Rules:**

- Timestamp + target repo
- What was done, which skill, scope of changes
- Links back to repo changelog entry
- Auto-pruned: keep last 90 days, archive older entries

### Cross-Repo Changelog (Big Picture)

Lives at `.changelog/CHANGELOG.md` in the **main workspace folder**. Aggregates significant events across all sub-repos. This is the "what happened to our systems" view.

**Entry format:**

```markdown
## 2026-03-29

### api-service

- spine — API authentication hardened (JWT middleware, rate limiting)
- warden — Security audit passed, 0 critical findings

### infra

- forge — Redis scaled to 3 nodes (eu-west-1)
- vigil — Alerting configured for new Redis cluster
```

**Rules:**

- Grouped by repo, then by agent
- One-line summaries only — detail lives in per-repo changelogs
- Updated whenever a per-repo changelog is updated
- Most recent at top

### Changelog Hook

A PostToolUse hook on Atlas triggers when a skill produces output matching the CLI skeleton format (the `╭─ AGENT NAME ── skill-name` header). The hook extracts structured data from the output:

- Agent name and skill name (from the header)
- Target repo (from working directory)
- Verdict and findings summary (from the Key Findings section)

Atlas formats and appends to all three changelogs automatically:

1. Per-repo changelog (`{repo}/.changelog/CHANGELOG.md`)
2. Cross-repo changelog (main workspace `.changelog/CHANGELOG.md`)
3. Per-agent activity log (`team/{agent}/.activity.md`)

Agents don't write changelog entries directly — the output kit's structured format makes the output machine-parseable.

---

## 4. `atlas-present` — Release Presentations

For big moments: new products, system takeovers, major migrations. Non-technical audience.

### Trigger

Manual only — user runs `/atlas-present` with scope (PR, milestone, date range, or freeform description). Presentations are intentional, not auto-generated.

### Two Outputs

Both saved to the **main workspace folder** at `.presentations/{date}-{title}/`:

1. **HTML presentation page** — `index.html`, primary delivery
2. **Obsidian Canvas** — `{title}.canvas`, visual companion

These are committed to the main workspace repo so they're versioned and shareable across the team.

### HTML Presentation Design

**Format:** Single scrollable page with section snapping — like a Stripe or Linear changelog page. Not slides.

**Tone:** Outcome-focused. "What can you do now that you couldn't before." No implementation details unless they serve the narrative.

**Sections:**

| Section       | Content                                                |
| ------------- | ------------------------------------------------------ |
| Hero          | Big title, one-sentence summary, date                  |
| The Problem   | What was broken/missing (before state)                 |
| What We Built | Key capabilities as feature cards with icons           |
| How It Works  | Simplified architecture diagram (Mermaid)              |
| Before/After  | Side-by-side metrics, screenshots, workflow comparison |
| Impact        | Numbers: speed, cost, reliability improvements         |
| What's Next   | Roadmap teaser, 2-3 upcoming items                     |
| Team          | Which agents/people contributed                        |

**Visual style:**

- Clean, lots of whitespace, large typography
- Brand-neutral — works for any company
- Inline SVG icons for feature cards
- Mermaid diagrams simplified, no technical jargon
- Self-contained HTML file (same as reports)

### Obsidian Canvas Companion

Generated alongside the HTML. Shows the system map.

**Layout:**

- Central node: product/feature name
- Connected nodes: components, services, data flows
- Color-coded: green = new, blue = modified, gray = unchanged
- Group nodes for logical clusters (frontend, backend, data, infra)

**Source data:** Atlas reads git history, changelogs, and existing docs to build the narrative.

---

## 5. Integration Plan

### What changes per agent

| Target                   | Change                                               |
| ------------------------ | ---------------------------------------------------- |
| All 14 specialist skills | Add `docs/output-kit.md` reference to output section |
| Atlas agent definition   | Updated scope to include output architecture         |
| Atlas skills (3 new)     | `atlas-report`, `atlas-changelog`, `atlas-present`   |
| Root plugin manifest     | Register 3 new Atlas skills                          |
| Atlas plugin hooks       | PostToolUse hook for changelog automation            |

### What does NOT change

- Agent definitions (scope boundaries, personality)
- Agent skill logic (what they analyze, how they work)
- Team directory structure
- Existing skill triggers and workflows

### File inventory

New files:

- `docs/output-kit.md` — shared CLI design system
- `team/atlas/skills/atlas-report/` — browser report skill
- `team/atlas/skills/atlas-changelog/` — changelog skill
- `team/atlas/skills/atlas-present/` — presentation skill
- `team/atlas/hooks/changelog-hook.md` — PostToolUse hook for auto-logging
- `skills/atlas-report/` — root copy for discovery
- `skills/atlas-changelog/` — root copy for discovery
- `skills/atlas-present/` — root copy for discovery

Modified files:

- All specialist skill output sections (add output-kit reference)
- `team/atlas/.claude-plugin/plugin.json` — register new skills
- `.claude-plugin/plugin.json` — register new skills in root manifest
- `agents/atlas.md` — updated scope
