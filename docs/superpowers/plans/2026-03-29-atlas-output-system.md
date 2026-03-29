# Atlas Output System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Atlas the output architect — shared CLI design system for all agents, browser HTML reports, three-layer changelogs, and release presentations.

**Architecture:** A shared output kit (`docs/output-kit.md`) that all 50 skills reference for CLI formatting. Three new Atlas skills handle escalation to browser (report), change tracking (changelog), and stakeholder communication (present). A PostToolUse hook automates changelog entries.

**Tech Stack:** Markdown (skills), HTML/CSS/JS (reports and presentations), Mermaid (diagrams), JSON Canvas (Obsidian companion)

---

### Task 1: Create the Output Kit

The foundation — the shared CLI design system document.

**Files:**

- Create: `docs/output-kit.md`

- [ ] **Step 1: Create the output kit document**

````markdown
# Output Kit — CLI Design System

Shared formatting rules for all tonone agent output. Every skill references this document.

## The 40-Line Rule

CLI output must not exceed 40 lines. If your findings need more space, summarize in the terminal and point to `/atlas-report` for the full browser view.

## CLI Skeleton

Every agent output follows this structure:

\```
╭─ AGENT NAME ── skill-name ──────────────────╮

## One-line verdict

### Key Findings (3-5 bullets max)

- ■ CRITICAL — Finding description
- ▲ WARNING — Finding description
- ● INFO — Finding description

### Metrics (if applicable)

┌──────────┬───────┬────────┐
│ Metric │ Value │ Status │
└──────────┴───────┴────────┘

### Next Steps (2-3 max)

→ Action one
→ Action two

╰─ Full report: /atlas-report ────────────────╯
\```

Adapt the skeleton to the skill's domain. Not every section is required — omit Metrics if there are none, omit Next Steps if the work is complete. But always include the box header, verdict, and findings.

## Severity Indicators

Use these consistently across all output. Never invent new indicators.

| Indicator    | Meaning   | When to use                                       |
| ------------ | --------- | ------------------------------------------------- |
| `■ CRITICAL` | Fix now   | Security holes, data loss risk, broken production |
| `▲ WARNING`  | Fix soon  | Performance issues, tech debt with timeline       |
| `● INFO`     | Awareness | Observations, suggestions, no urgency             |

## Tables

Use box-drawing characters for tables:

\```
┌──────────────┬───────────┬──────────┬────────┐
│ Column │ Column │ Column │ Column │
├──────────────┼───────────┼──────────┼────────┤
│ Value │ Value │ Value │ Value │
└──────────────┴───────────┴──────────┴────────┘
\```

Rules:

- Max 4 columns
- Truncate cell values at 30 characters with `…`
- Right-align numbers, left-align text

## Formatting Rules

- **No emoji.** Use box-drawing characters and unicode indicators (`■ ▲ ● → ─ │ ╭ ╮ ╰ ╯`).
- **No walls of text.** Bullet points, not paragraphs.
- **No raw data dumps.** Summarize, then offer the full report.
- **Bold for labels** in key-value output: `**Files:** 4 modified`
- **Code formatting** for paths, commands, and identifiers: \`src/api/auth.py\`

## Progressive Disclosure

When findings exceed the 40-line budget:

1. Show the summary in CLI (verdict + top findings + next steps)
2. End with: `Full report: /atlas-report`
3. The user runs `/atlas-report` to get the complete findings in a styled HTML page

## Skill Integration

Add this line to the output/present/summarize step of every skill:

\```
Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators.
\```

Skills keep their domain-specific content (what findings to show, what tables make sense) but follow the kit for formatting.
````

- [ ] **Step 2: Verify the document renders correctly**

Run: `cat docs/output-kit.md | head -20`
Expected: Clean markdown with proper headings

- [ ] **Step 3: Commit**

```bash
git add docs/output-kit.md
git commit -m "docs: add output kit — shared CLI design system for all agents"
```

---

### Task 2: Create `atlas-report` Skill

Browser HTML reports for when CLI isn't enough.

**Files:**

- Create: `team/atlas/skills/atlas-report/SKILL.md`
- Create: `skills/atlas-report/SKILL.md` (root copy)

- [ ] **Step 1: Create the skill file**

Write to `team/atlas/skills/atlas-report/SKILL.md`:

````markdown
---
name: atlas-report
description: Render agent findings as a styled HTML report in the browser. Use when asked for "full report", "detailed report", "show in browser", or when CLI output exceeds the 40-line budget.
---

# Generate Browser Report

You are Atlas — the knowledge engineer on the Engineering Team. You render structured findings as polished HTML reports.

## Steps

### Step 0: Gather Context

Determine what to report on:

- **From conversation** — if an agent just ran a skill, use its findings
- **From recent output** — if the user says "report on that", look at the most recent agent output in the conversation
- **From files** — if pointed at a specific changelog or audit result, read it

Identify:

- Which agent produced the findings
- Which skill was used
- What repo/service was analyzed
- The timestamp

### Step 1: Structure the Findings

Organize the raw findings into these sections (include only what applies):

1. **Header** — agent name, skill, timestamp, target repo/service
2. **Executive Summary** — 3-5 bullets, the "so what"
3. **Findings** — full findings with severity (`■ CRITICAL`, `▲ WARNING`, `● INFO`), evidence (file paths, code snippets), and fix
4. **Metrics** — tables, comparisons, scores
5. **Diagrams** — Mermaid architecture/flow diagrams if system relationships matter
6. **Timeline** — chronological events for audits or incidents
7. **Actions** — prioritized next steps

### Step 2: Generate the HTML Report

Create a single self-contained HTML file. The file must have:

- **Zero external dependencies** — all CSS and JS inline
- **Dark theme by default** with a light mode toggle button (top-right)
- **Sticky navigation sidebar** (left) with links to each section
- **Color-coded severity cards:**
  - `■ CRITICAL` → red background (`#dc2626` on dark, `#fef2f2` on light)
  - `▲ WARNING` → amber background (`#d97706` on dark, `#fffbeb` on light)
  - `● INFO` → blue background (`#2563eb` on dark, `#eff6ff` on light)
- **Collapsible detail sections** — `<details><summary>` for code blocks, raw data, verbose evidence
- **Mermaid diagrams** — include Mermaid JS CDN (`https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js`) and render `<pre class="mermaid">` blocks
- **Copy buttons** on all `<code>` and `<pre>` blocks (JS clipboard API)
- **Print stylesheet** — `@media print` that hides the sidebar, removes dark theme, expands all collapsed sections
- **Responsive** — readable on mobile (sidebar collapses to hamburger)

CSS design tokens:

```css
:root {
  --bg: #0f172a;
  --bg-card: #1e293b;
  --text: #e2e8f0;
  --text-muted: #94a3b8;
  --border: #334155;
  --accent: #3b82f6;
  --critical: #dc2626;
  --warning: #d97706;
  --info: #2563eb;
  --success: #16a34a;
  --font-mono: "JetBrains Mono", "Fira Code", monospace;
  --font-sans: "Inter", system-ui, sans-serif;
}

[data-theme="light"] {
  --bg: #ffffff;
  --bg-card: #f8fafc;
  --text: #1e293b;
  --text-muted: #64748b;
  --border: #e2e8f0;
}
```
````

HTML structure:

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{Agent} — {Skill} Report</title>
    <style>
      /* all CSS inline */
    </style>
  </head>
  <body>
    <nav class="sidebar"><!-- section links --></nav>
    <main>
      <header><!-- agent, skill, timestamp, target --></header>
      <section id="summary"><!-- executive summary --></section>
      <section id="findings"><!-- severity cards --></section>
      <section id="metrics"><!-- tables, charts --></section>
      <section id="diagrams"><!-- mermaid blocks --></section>
      <section id="timeline"><!-- chronological events --></section>
      <section id="actions"><!-- prioritized next steps --></section>
    </main>
    <script>
      /* theme toggle, copy buttons, mermaid init */
    </script>
  </body>
</html>
```

### Step 3: Save and Open

Determine the target location:

- If agent worked on a specific repo: save to `{repo}/.reports/{agent}-{skill}-{YYYY-MM-DD-HHmm}.html`
- If cross-repo or workspace-level: save to `.reports/{agent}-{skill}-{YYYY-MM-DD-HHmm}.html` in the working directory

Create the `.reports/` directory if it doesn't exist.

Open the file in the default browser:

```bash
open .reports/{filename}.html  # macOS
xdg-open .reports/{filename}.html  # Linux
```

### Step 4: Present CLI Summary

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators.

```
╭─ ATLAS ── atlas-report ─────────────────────╮

  ## Report generated

  **Source:** {agent} / {skill}
  **Target:** {repo or service}
  **Saved to:** {path}
  **Opened in:** default browser

  ### Report Contents
  - {N} findings ({critical} critical, {warning} warnings)
  - {N} action items
  - {diagrams/metrics if included}

╰─────────────────────────────────────────────╯
```

## Key Rules

- The HTML file must be completely self-contained — openable offline except for Mermaid CDN
- Never truncate findings in the HTML report — this is where the full detail lives
- Severity colors must match the output kit's indicator system
- If Mermaid CDN is unavailable, render diagram source as formatted code blocks (graceful degradation)
- Do not generate empty sections — omit sections that have no content

````

- [ ] **Step 2: Copy to root skills directory**

```bash
mkdir -p skills/atlas-report
cp team/atlas/skills/atlas-report/SKILL.md skills/atlas-report/SKILL.md
````

- [ ] **Step 3: Verify both copies match**

```bash
diff team/atlas/skills/atlas-report/SKILL.md skills/atlas-report/SKILL.md
```

Expected: no output (files are identical)

- [ ] **Step 4: Commit**

```bash
git add team/atlas/skills/atlas-report/SKILL.md skills/atlas-report/SKILL.md
git commit -m "feat(atlas): add atlas-report skill — browser HTML reports"
```

---

### Task 3: Create `atlas-changelog` Skill

Three-layer changelog management.

**Files:**

- Create: `team/atlas/skills/atlas-changelog/SKILL.md`
- Create: `skills/atlas-changelog/SKILL.md` (root copy)

- [ ] **Step 1: Create the skill file**

Write to `team/atlas/skills/atlas-changelog/SKILL.md`:

````markdown
---
name: atlas-changelog
description: Maintain per-repo and cross-repo changelogs — append structured entries after agent work. Use when asked to "log this change", "update changelog", "what changed", or "change history".
---

# Manage Changelogs

You are Atlas — the knowledge engineer on the Engineering Team. You maintain the team's change history across repos.

## Steps

### Step 0: Detect Workspace

Determine the workspace layout:

- Check if current directory contains sub-repos (directories with `.git/` inside)
- Check for existing `.changelog/` directories
- Identify the main workspace root vs individual repo directories

Map the workspace:

- **Main workspace folder** — the directory the user opened Claude Code in
- **Sub-repos** — git repositories inside the workspace folder
- **Current target** — which repo(s) the current work applies to

### Step 1: Determine What Changed

Gather change information from one of these sources (in priority order):

1. **From conversation** — if an agent just finished work, extract: agent name, skill used, what was done, files changed, severity of findings
2. **From git** — if asked to catch up, read `git log --oneline -20` in the target repo to find recent changes
3. **From user** — if told "log this", ask what happened if not obvious from context

Required fields for a changelog entry:

- **Agent** — which agent did the work
- **Action** — one-line title (imperative mood: "Add authentication", not "Added authentication")
- **Details** — 2-4 bullet points: what specifically changed
- **Files** — key files modified (not exhaustive, just the important ones)
- **Severity** — if audit/review: findings summary using `■ ▲ ●` indicators

### Step 2: Write Per-Repo Changelog

Append to `{repo}/.changelog/CHANGELOG.md`. Create the file and directory if they don't exist.

Format:

```markdown
## {YYYY-MM-DD}

### {agent} — {action title}

- {detail bullet}
- {detail bullet}
- {detail bullet}
```
````

Rules:

- If today's date header already exists, append under it
- If today's date header doesn't exist, add it at the top of the file (most recent first)
- Agent name is lowercase
- Action title is imperative, concise
- Detail bullets reference file paths in backticks when relevant
- No prose — scannable, grep-friendly

### Step 3: Write Cross-Repo Changelog

If in a multi-repo workspace, also append to `{workspace}/.changelog/CHANGELOG.md` (the main folder).

Format:

```markdown
## {YYYY-MM-DD}

### {repo-name}

- {agent} — {action title one-liner}
```

Rules:

- Group by repo name under each date
- One-line summaries only — detail lives in per-repo changelogs
- If today's date header exists, append under it
- If repo subheader exists under today's date, append to it

### Step 4: Write Per-Agent Activity Log

Append to `team/{agent}/.activity.md` in the tonone plugin directory.

Format:

```markdown
## {YYYY-MM-DD HH:MM} — {repo-name}

**Action:** {what was done}
**Skill:** {skill-name}
**Files:** {N} modified, {N} created
**Verdict:** {severity summary or "Complete"}
```

Rules:

- Timestamp includes time (HH:MM, 24h format)
- Repo name is the directory name, not full path
- Create the `.activity.md` file if it doesn't exist

### Step 5: Present CLI Summary

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators.

```
╭─ ATLAS ── atlas-changelog ──────────────────╮

  ## Changelog updated

  ### Entries Written
  → {repo}/.changelog/CHANGELOG.md
  → .changelog/CHANGELOG.md (workspace)
  → team/{agent}/.activity.md

  ### Entry
  **{agent}** — {action title}
  {2-4 detail bullets}

╰─────────────────────────────────────────────╯
```

## Key Rules

- Never overwrite existing changelog content — always append
- Date headers are `## YYYY-MM-DD` — no other format
- Per-repo changelog has full details; cross-repo has one-liners only
- If the agent activity log exceeds 500 lines, archive entries older than 90 days to `team/{agent}/.activity-archive.md`
- Changelog entries are committed with the work they describe (same commit or immediately after)
- If you can't determine what changed, ask — don't guess

````

- [ ] **Step 2: Copy to root skills directory**

```bash
mkdir -p skills/atlas-changelog
cp team/atlas/skills/atlas-changelog/SKILL.md skills/atlas-changelog/SKILL.md
````

- [ ] **Step 3: Verify both copies match**

```bash
diff team/atlas/skills/atlas-changelog/SKILL.md skills/atlas-changelog/SKILL.md
```

Expected: no output (files are identical)

- [ ] **Step 4: Commit**

```bash
git add team/atlas/skills/atlas-changelog/SKILL.md skills/atlas-changelog/SKILL.md
git commit -m "feat(atlas): add atlas-changelog skill — three-layer changelog management"
```

---

### Task 4: Create `atlas-present` Skill

Release presentations for non-technical stakeholders.

**Files:**

- Create: `team/atlas/skills/atlas-present/SKILL.md`
- Create: `skills/atlas-present/SKILL.md` (root copy)

- [ ] **Step 1: Create the skill file**

Write to `team/atlas/skills/atlas-present/SKILL.md`:

````markdown
---
name: atlas-present
description: Generate a polished HTML presentation page and Obsidian Canvas for big releases — new products, takeovers, major migrations. Non-technical audience. Use when asked to "present this", "release announcement", "show what we built", or "stakeholder update".
---

# Generate Release Presentation

You are Atlas — the knowledge engineer on the Engineering Team. You translate technical work into compelling narratives for non-technical stakeholders.

## Steps

### Step 0: Determine Scope

Understand what's being presented:

- **From user** — they'll describe the release, milestone, or event
- **From changelogs** — read `.changelog/CHANGELOG.md` files for the relevant date range
- **From git** — `git log --oneline --since={date}` across relevant repos
- **From PRs** — if given a PR number or milestone, read it

Identify:

- **Title** — the name of what was built/launched
- **Date range** — when this work happened
- **Repos involved** — which sub-repos were touched
- **Audience** — default is non-technical stakeholders

### Step 1: Build the Narrative

Structure the story for a non-technical audience. Every section answers a question a stakeholder would ask:

1. **Hero** — "What is this?" → Big title, one-sentence summary
2. **The Problem** — "Why did we do this?" → What was broken, missing, or painful
3. **What We Built** — "What can I do now?" → 3-5 feature cards, outcome-focused language
4. **How It Works** — "Is this reliable?" → Simplified architecture diagram, no jargon
5. **Before/After** — "Did it actually improve things?" → Side-by-side metrics, workflow comparison
6. **Impact** — "What are the numbers?" → Speed, cost, reliability improvements
7. **What's Next** — "What's coming?" → 2-3 upcoming items, roadmap teaser
8. **Team** — "Who did this?" → Credits for agents and people involved

Rules for non-technical writing:

- No acronyms without explanation
- No implementation details (no "added JWT middleware" — say "secured user login")
- Outcome language: "You can now X" not "We implemented Y"
- Numbers over adjectives: "3x faster" not "significantly improved"

### Step 2: Generate the HTML Presentation

Create a single scrollable HTML page. Not slides — a continuous page with section snapping.

Design requirements:

- **Single file, zero external dependencies** (except Mermaid CDN for diagrams)
- **Large typography** — hero title at 4rem, section headings at 2rem, body at 1.125rem
- **Generous whitespace** — sections separated by 6rem+ vertical space
- **Section snap scrolling** — `scroll-snap-type: y mandatory` on the container
- **Feature cards** — grid layout with inline SVG icons, subtle border, hover lift
- **Before/After** — two-column layout with divider line
- **Mermaid diagrams** — simplified, no technical jargon in labels
- **Brand-neutral colors** — works for any company

CSS design tokens:

```css
:root {
  --bg: #0a0a0a;
  --bg-card: #141414;
  --text: #fafafa;
  --text-muted: #a1a1aa;
  --border: #27272a;
  --accent: #3b82f6;
  --accent-soft: #1e3a5f;
  --success: #22c55e;
  --font-sans: "Inter", system-ui, -apple-system, sans-serif;
  --font-display: "Inter", system-ui, -apple-system, sans-serif;
}
```
````

HTML structure:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{Title} — Release Presentation</title>
    <style>
      /* all CSS inline */
    </style>
  </head>
  <body>
    <section class="hero">
      <h1>{Title}</h1>
      <p class="subtitle">{One-sentence summary}</p>
      <time>{Date}</time>
    </section>
    <section class="problem"><!-- The Problem --></section>
    <section class="built"><!-- What We Built — feature cards grid --></section>
    <section class="how"><!-- How It Works — Mermaid diagram --></section>
    <section class="compare"><!-- Before/After --></section>
    <section class="impact"><!-- Impact numbers --></section>
    <section class="next"><!-- What's Next --></section>
    <section class="team"><!-- Credits --></section>
    <script>
      /* Mermaid init, scroll behavior */
    </script>
  </body>
</html>
```

### Step 3: Generate Obsidian Canvas Companion

Create a JSON Canvas file (`.canvas`) alongside the HTML. This shows the system map for technical people who want to zoom into architecture.

Canvas structure:

- **Central node** (text, color: `"6"` purple) — the product/feature name with one-line description
- **Component nodes** arranged radially:
  - Green (`"4"`) for new components
  - Blue (`"6"`) for modified components
  - No color for unchanged components
- **Group nodes** for logical clusters: Frontend, Backend, Data, Infrastructure
- **Edges** between components showing data flow, labeled with connection type
- **Layout:** Central node at (0, 0), groups arranged in quadrants, nodes spaced 300px apart

JSON Canvas format:

```json
{
  "nodes": [
    {
      "id": "center",
      "type": "text",
      "x": 0,
      "y": 0,
      "width": 400,
      "height": 200,
      "text": "# {Title}\n{summary}",
      "color": "6"
    },
    {
      "id": "group-frontend",
      "type": "group",
      "x": -600,
      "y": -500,
      "width": 500,
      "height": 400,
      "label": "Frontend"
    },
    {
      "id": "comp-1",
      "type": "text",
      "x": -550,
      "y": -400,
      "width": 200,
      "height": 100,
      "text": "**{Component}**\n{description}",
      "color": "4"
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "fromNode": "comp-1",
      "toNode": "center",
      "fromSide": "right",
      "toSide": "left",
      "label": "REST API"
    }
  ]
}
```

### Step 4: Save and Open

Save both files to the main workspace folder:

```
.presentations/{YYYY-MM-DD}-{kebab-title}/
├── index.html          ← the presentation
└── {kebab-title}.canvas  ← Obsidian Canvas companion
```

Create the directory if it doesn't exist.

Open the HTML in the default browser:

```bash
open .presentations/{dir}/index.html
```

### Step 5: Present CLI Summary

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators.

```
╭─ ATLAS ── atlas-present ────────────────────╮

  ## Presentation generated

  **Title:** {title}
  **Scope:** {date range or milestone}
  **Repos:** {list of repos involved}

  ### Deliverables
  → .presentations/{dir}/index.html (opened in browser)
  → .presentations/{dir}/{title}.canvas (Obsidian)

  ### Sections
  - Hero, Problem, What We Built ({N} features)
  - How It Works (architecture diagram)
  - Before/After, Impact, What's Next, Team

╰─────────────────────────────────────────────╯
```

## Key Rules

- Write for non-technical stakeholders — no jargon, no implementation details
- Outcome language always: "You can now X" not "We added Y"
- Numbers over adjectives: "3x faster" not "much faster"
- The HTML must be completely self-contained and openable offline (except Mermaid CDN)
- Canvas nodes must have meaningful descriptions, not just component names
- If there's no meaningful Before/After data, omit that section rather than fabricating numbers
- Presentations are manual — never auto-generate without the user asking

````

- [ ] **Step 2: Copy to root skills directory**

```bash
mkdir -p skills/atlas-present
cp team/atlas/skills/atlas-present/SKILL.md skills/atlas-present/SKILL.md
````

- [ ] **Step 3: Verify both copies match**

```bash
diff team/atlas/skills/atlas-present/SKILL.md skills/atlas-present/SKILL.md
```

Expected: no output (files are identical)

- [ ] **Step 4: Commit**

```bash
git add team/atlas/skills/atlas-present/SKILL.md skills/atlas-present/SKILL.md
git commit -m "feat(atlas): add atlas-present skill — release presentations with HTML + Canvas"
```

---

### Task 5: Create Changelog PostToolUse Hook

Automate changelog entries when agents complete work.

**Files:**

- Modify: `team/atlas/hooks/hooks.json`
- Create: `team/atlas/hooks/changelog-hook.md`

- [ ] **Step 1: Create the hook prompt**

Write to `team/atlas/hooks/changelog-hook.md`:

```markdown
# Changelog Hook

When an agent skill completes and produces output matching the CLI skeleton format (the `╭─ AGENT NAME ── skill-name` header), extract structured data and update changelogs.

## Detection

Look for output containing:

- `╭─` followed by an agent name and skill name
- Severity indicators: `■ CRITICAL`, `▲ WARNING`, `● INFO`
- A structured findings section

If the output does not match this pattern, do nothing.

## Extraction

From the CLI skeleton output, extract:

- **Agent name** — from the `╭─ AGENT NAME` header
- **Skill name** — from the `── skill-name` part of the header
- **Target repo** — from the current working directory
- **Verdict** — the one-line verdict
- **Findings summary** — count of critical/warning/info items
- **Key actions** — from the Next Steps section

## Action

Run `/atlas-changelog` with the extracted data to update all three changelog layers:

1. Per-repo changelog
2. Cross-repo changelog (if in multi-repo workspace)
3. Per-agent activity log
```

- [ ] **Step 2: Update hooks.json to register the hook**

Read the current `team/atlas/hooks/hooks.json` and add the changelog hook. The updated file should be:

```json
{
  "hooks": [
    {
      "event": "post_install",
      "command": "bash scripts/setup.sh",
      "description": "Set up Python environment for analyzers"
    },
    {
      "event": "PostToolUse",
      "tool": "Agent",
      "description": "Auto-update changelogs when an agent skill completes work",
      "prompt": "Check if the agent output contains a CLI skeleton header (╭─ AGENT NAME ── skill-name). If it does, run /atlas-changelog to log the change. If it doesn't match, do nothing."
    }
  ]
}
```

- [ ] **Step 3: Commit**

```bash
git add team/atlas/hooks/hooks.json team/atlas/hooks/changelog-hook.md
git commit -m "feat(atlas): add PostToolUse hook for automatic changelog entries"
```

---

### Task 6: Update Atlas Agent Definition

Expand Atlas's scope to include output architecture.

**Files:**

- Modify: `agents/atlas.md`
- Modify: `team/atlas/agents/atlas.md`

- [ ] **Step 1: Update the root agent definition**

In `agents/atlas.md`, add to the **Scope > Owns** list (after "changelog and migration guides"):

```
output formatting standards (output kit), browser report generation, release presentations, cross-repo changelogs
```

And add to **Scope > Also covers**:

```
CLI output design system, HTML report rendering, presentation generation for non-technical stakeholders, Obsidian Canvas generation
```

Add a new section after **Anti-Patterns You Call Out**:

```markdown
## Output Architecture

Atlas owns the team's output design system:

- **Output Kit** (`docs/output-kit.md`) — shared CLI formatting rules all agents follow: 40-line max, box-drawing skeleton, unified severity indicators
- **`/atlas-report`** — renders full findings as styled HTML in the browser when CLI isn't enough
- **`/atlas-changelog`** — maintains three-layer changelogs: per-repo, cross-repo, and per-agent activity logs
- **`/atlas-present`** — generates HTML presentation pages + Obsidian Canvas for major releases targeting non-technical stakeholders
```

- [ ] **Step 2: Copy updated definition to team directory**

```bash
cp agents/atlas.md team/atlas/agents/atlas.md
```

- [ ] **Step 3: Verify both copies match**

```bash
diff agents/atlas.md team/atlas/agents/atlas.md
```

Expected: no output

- [ ] **Step 4: Commit**

```bash
git add agents/atlas.md team/atlas/agents/atlas.md
git commit -m "feat(atlas): expand scope to include output architecture"
```

---

### Task 7: Update Plugin Manifests

Register the three new skills in both root and Atlas plugin manifests.

**Files:**

- Modify: `team/atlas/.claude-plugin/plugin.json`

- [ ] **Step 1: Update Atlas team plugin manifest**

The root plugin.json doesn't list individual skills (they're discovered by directory structure). But update the Atlas team plugin description to reflect expanded scope.

In `team/atlas/.claude-plugin/plugin.json`, update the description:

```json
{
  "name": "atlas-docs",
  "version": "0.2.0",
  "description": "Knowledge engineer — architecture docs, ADRs, API specs, system diagrams, onboarding, output formatting, browser reports, changelogs, release presentations",
  "author": {
    "name": "tonone-ai",
    "url": "https://tonone.ai"
  },
  "repository": "https://github.com/tonone-ai/tonone",
  "license": "MIT",
  "keywords": [
    "documentation",
    "architecture",
    "adrs",
    "api-specs",
    "diagrams",
    "knowledge",
    "reports",
    "changelogs",
    "presentations",
    "output-formatting"
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add team/atlas/.claude-plugin/plugin.json
git commit -m "chore(atlas): bump version and update plugin description for new skills"
```

---

### Task 8: Update All Existing Skills with Output Kit Reference

Add the output kit reference to all 50 skill files. This is the bulk update.

**Files:**

- Modify: All `SKILL.md` files in `team/*/skills/*/` and their root copies in `skills/*/`

- [ ] **Step 1: Identify all skill files that need updating**

```bash
find team/*/skills/*/SKILL.md -type f | sort
```

This gives the canonical list. Each file's output/present/summarize step gets one line added.

- [ ] **Step 2: Update each skill's output section**

For each skill file, find the last step (the output/present/summarize step) and add this line at the beginning of that step:

```
Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators.
```

The three new Atlas skills (atlas-report, atlas-changelog, atlas-present) already have this line — skip them.

Also skip skills that have no explicit output section (proof-api, proof-e2e, pave-golden) — add a new final step to these:

```markdown
### Step N: Present Summary

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators.

Summarize what was built/configured in the CLI skeleton format with key findings and next steps.
```

- [ ] **Step 3: Sync all team skills to root copies**

For each skill updated in `team/*/skills/*/SKILL.md`, copy to the matching `skills/*/SKILL.md`:

```bash
for team_skill in team/*/skills/*/SKILL.md; do
  skill_name=$(basename $(dirname "$team_skill"))
  cp "$team_skill" "skills/$skill_name/SKILL.md"
done
```

- [ ] **Step 4: Verify all copies are in sync**

```bash
for team_skill in team/*/skills/*/SKILL.md; do
  skill_name=$(basename $(dirname "$team_skill"))
  root_skill="skills/$skill_name/SKILL.md"
  if ! diff -q "$team_skill" "$root_skill" > /dev/null 2>&1; then
    echo "MISMATCH: $skill_name"
  fi
done
```

Expected: no output (all match)

- [ ] **Step 5: Commit**

```bash
git add team/*/skills/*/SKILL.md skills/*/SKILL.md
git commit -m "feat: add output kit reference to all 50 agent skills"
```

---

### Task 9: Update Documentation

Update README, CHANGELOG, CLAUDE.md, and other docs for the new capabilities.

**Files:**

- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Modify: `docs/naming-guide.md`

- [ ] **Step 1: Update README.md**

Add the three new Atlas skills to the Atlas row in the skills table. Add a new section about the Output Kit and workspace model under "Getting Started" or similar.

- [ ] **Step 2: Update CLAUDE.md**

Add a brief note about the output kit in the Conventions section:

```markdown
- All agent CLI output follows the output kit (`docs/output-kit.md`): 40-line max, box-drawing skeleton, unified severity indicators
```

- [ ] **Step 3: Update CHANGELOG.md**

Add a v0.4.0 entry:

```markdown
## [0.4.0] — 2026-03-29

### Added

- **Output Kit** — shared CLI design system for all agents (`docs/output-kit.md`)
- **`atlas-report`** — render agent findings as styled HTML reports in the browser
- **`atlas-changelog`** — three-layer changelog management (per-repo, cross-repo, per-agent)
- **`atlas-present`** — release presentations as HTML pages + Obsidian Canvas
- **Changelog hook** — automatic changelog entries when agents complete work
- **Workspace model** — documentation for multi-repo workspace layout

### Changed

- All 50 skills now reference the output kit for consistent CLI formatting
- Atlas agent scope expanded to include output architecture
- Atlas plugin version bumped to 0.2.0
```

- [ ] **Step 4: Update docs/architecture.md**

Add a section about the output system and workspace model.

- [ ] **Step 5: Update docs/naming-guide.md**

Add the three new Atlas skills to the skill roster.

- [ ] **Step 6: Bump root plugin version**

In `.claude-plugin/plugin.json`, bump version from `0.3.0` to `0.4.0`.

- [ ] **Step 7: Commit all documentation updates**

```bash
git add README.md CLAUDE.md CHANGELOG.md docs/architecture.md docs/naming-guide.md .claude-plugin/plugin.json
git commit -m "docs: update all documentation for v0.4.0 — Atlas Output System"
```
