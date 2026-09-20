---
name: tonone-onboard
description: 'First-run onboarding — detect what kind of project this is, recommend a four-agent roster instead of all 100, and print the one-line install command. Use when asked "how do I use tonone", "which agents do I need", "what can tonone do", "show me around", or "first steps".'
allowed-tools: Bash, Read, AskUserQuestion
version: 0.9.0
author: tonone-ai <hello@tonone.ai>
license: MIT
compatibility: Designed for Claude Code
tags: [onboarding, getting-started, roster, recommendation]
---

# tonone-onboard

Cross-agent onboarding. Not tied to a single agent.

The default install registers every agent in every session. That is the wrong
default for almost every repository: most projects need four or five
specialists, and Apex reaches the rest on demand. This skill proposes the
roster that fits **this** repository and hands it to `/apex-profile` to write.

Follow the output format defined in docs/output-kit.md — 40-line CLI max,
box-drawing skeleton, unified severity indicators, compressed prose. This skill
should land in roughly a dozen lines. An onboarding message that scrolls is an
onboarding message nobody reads.

Always runs. Never checks the marker file — replay it as often as you like. To
re-show the SessionStart install banner, delete `~/.config/tonone/onboarded`.

## Steps

### Step 1: Detect the project shape

Run the shared detector. It is the same signal gathering and scoring the
SessionStart banner and the skill gate use, so all three agree by construction.

`CLAUDE_PLUGIN_ROOT` is **not** exported into the Bash tool's environment, so
the detector has to be located before it can be run. Paste this block verbatim —
it checks the plugin root when one is set, the repository checkout you are
standing in, then the installed plugin cache:

```bash
shape=""
for c in "${CLAUDE_PLUGIN_ROOT:-/nonexistent}/lib/signals/project-shape.js" \
         "${CLAUDE_PLUGIN_ROOT:-/nonexistent}/../../lib/signals/project-shape.js" \
         "$PWD/lib/signals/project-shape.js"; do
  [ -f "$c" ] && shape="$c" && break
done
if [ -z "$shape" ]; then
  found=$(find "$HOME/.claude/plugins/cache" -maxdepth 6 \
    -path "*/lib/signals/project-shape.js" 2>/dev/null | head -1)
  [ -n "$found" ] && shape="$found"
fi
if [ -n "$shape" ]; then
  node "$shape" --pretty --cwd "$PWD"
else
  echo '{"ok":false,"error":"detector not on disk","source":"default"}'
fi
```

Written this way the block exits 0 and prints one JSON object on every path,
under bash, zsh and sh alike. The detector's own CLI never exits non-zero
either; the `else` branch covers the one case it cannot, which is not being
installed at all. Read `ok` first — a `false` there means no detection
happened, so do not present the roster in it as a match.

The JSON object:

| Field          | Use                                                                   |
| -------------- | --------------------------------------------------------------------- |
| `label`, `why` | What it decided, and the one-line reason                              |
| `agents`       | The recommended roster, Apex always first                             |
| `bundles`      | Wider bundles in the same domain — a superset, never the roster       |
| `commands`     | `commands[0]` installs exactly the roster; the rest are bundles       |
| `evidence`     | The files and dependencies that drove the match                       |
| `source`       | `signals` deterministic, `jev`/`local` tie-broken, `default` no match |
| `alternate`    | The runner-up roster, or `null`                                       |

Do not re-derive any of this by hand and do not substitute your own roster.

If `ok` is `false` — the detector is not on disk, which happens when only a
single agent plugin is installed rather than the bundle — say so in one line
and hand off to `/apex-profile` with its **Preset** option, letting its curated
preset table pick the roster. Do not fall back to the full 100-agent team: an
undetected project is the case this skill exists for, not an exception to it.

### Step 2: Present the recommendation

One box, under 12 lines. Report `source` honestly — a `default` result means
nothing matched, not that the starter roster is right:

```
┌────────────────────────────────────────────────────────┐
│  tonone — recommended roster                           │
├────────────────────────────────────────────────────────┤
│  Detected   Frontend web app                           │
│  Evidence   next, next.config.js, react                │
│  Roster     apex, prism, form, draft, axe              │
│  Why        UI work, a design system, an a11y pass     │
└────────────────────────────────────────────────────────┘

claude plugin install apex@tonone-ai prism@tonone-ai form@tonone-ai \
  draft@tonone-ai axe@tonone-ai
```

Print `commands[0]` verbatim, below the box where it has room to wrap. Never
print a bundle command in its place: `design-team` installs ten design agents
and still misses Prism, so it is not the roster the box just promised.

Add one line only when it earns its place:

- `source` is `default` — ● INFO No strong signal; this is the generic starter roster.
- `alternate` is set — ● INFO Runner-up: `<alternate>`. Say `both` to install it too.
- `bundles` is non-empty — ● INFO Whole discipline instead: `commands[1]`.

### Step 3: Confirm (AskUserQuestion, single-select)

- **Install this roster** — the recommended agents, nothing else
- **Roster plus the runner-up** — offer only when `alternate` is set
- **Full team** — all 100 agents, the current default
- **Just show me around** — skip installation, go to Step 5

### Step 4: Hand off to apex-profile

`/apex-profile` owns agent roster configuration — it writes `enabledPlugins`
into `.claude/settings.json` or `.claude/settings.local.json`, merging rather
than overwriting, and it asks which of the two. Do not write either file here.

Invoke `/apex-profile` with the **Custom list** option and the `agents` array
from Step 1 as the list. This skill is the recommender; apex-profile is the
writer. If the user wants a different set, let apex-profile's own preset table
take over — do not negotiate the roster twice.

State plainly that plugin enablement is read at startup, so the change takes
effect in the **next** Claude Code session.

### Step 5: Orientation (only if asked)

Keep it to this block. The full agent table lives in `CLAUDE.md` and
`docs/agent-index.json`; do not reproduce 100 rows in the terminal.

```
/apex-takeover    hand any task to the team — Apex routes it
/apex-route       reach a specialist outside your roster, on demand
/apex-profile     change the installed roster later
/atlas-onboard    generate onboarding docs for this project
```

Mental model, in three lines:

- You talk to Apex. Apex picks the specialist. You never dispatch by name.
- A roster is what is installed. `/apex-route` still reaches all 100.
- Each session gets its own git worktree branch, so parallel sessions never
  collide, and a session that changed nothing removes its branch on close.

## Key Rules

- **Recommend, never install silently.** No plugin is installed and no settings
  file is written without an explicit confirmation in Step 3.
- **apex-profile writes the config.** This skill detects and proposes. Writing
  `enabledPlugins` in two places would produce two sources of truth.
- **Never invent a roster or a bundle.** Use exactly what the detector returns;
  its bundles are checked against `bundle/` by `tests/test_project_shape.js`.
- **Report the source.** `signals` is deterministic evidence. `local` is lexical
  overlap from the key-free scorer, not judgement. `default` means no match.
- **No credentials, ever.** The detector needs no key and no network. Never
  suggest setting one to improve the recommendation.
- **Stay short.** Steps 1-4 produce one box plus at most two extra lines.
- **Do not list all 100 agents.** That is the problem this skill exists to fix.

## Output Format

One box (the Step 2 skeleton), then the confirmation question, then a single
closing line naming what was written and when it takes effect:

```
Roster written to .claude/settings.local.json — active next session.
```

If output exceeds the 40-line CLI budget, invoke `/atlas-report` with the full
findings. The HTML report is the output; the CLI is the receipt — box header,
one-line verdict, and the report path.
