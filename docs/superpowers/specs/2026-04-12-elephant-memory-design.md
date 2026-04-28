# Elephant — Persistent Memory System for tonone

## Overview

Persistent memory system. Auto-captures agent work, commits, skill runs. Manual entries for decisions. Caveman-compressed text. Startup recall block shows smart summary. Never deletes — compresses old routine entries.

## File Layout

```
# Local (per repo)
.elephant/
└── memory.md

# Global (cross-repo feed)
~/.claude/elephant/
└── memory.md
```

## Entry Format

**Local `memory.md`:**

```
[!!] 2026-04-12 14:30 : chose JWT over sessions — stateless API need
2026-04-12 14:45 : spine build auth API + 12 endpoints. tests pass.
2026-04-12 15:10 : relay deploy staging done.
2026-04-11 09:20 : proof write 42 tests. coverage 87%.
```

**Global `memory.md`:**

```
[!!] 2026-04-12 14:30 : tonone : chose JWT over sessions — stateless API need
2026-04-12 14:45 : tonone : spine build auth API + 12 endpoints. tests pass.
2026-04-12 16:00 : billing-app : fix webhook retry logic.
```

**Format rules:**

- Local: `[!!]? YYYY-MM-DD HH:MM : text`
- Global: `[!!]? YYYY-MM-DD HH:MM : repo : text`
- `[!!]` prefix = important, never compress
- No prefix = routine, eligible for compression
- All text in caveman-compressed style (drop articles, fragments OK, short synonyms)
- Newest entries on top

## Writing to Memory

### Auto-capture (hooks)

Hook script: `hooks/elephant-writer.js`

Triggers via PostToolUse hook on these events:

| Event           | Hook Matcher                | Example Entry                         |
| --------------- | --------------------------- | ------------------------------------- |
| Agent completes | `Agent`                     | `spine build auth API. 12 endpoints.` |
| Commit created  | `Bash` (matches git commit) | `commit: add JWT auth middleware`     |
| Skill finishes  | `Skill`                     | `ran /ship — PR #42 created`          |

**Hook flow:**

1. Read tool result from stdin JSON (same pattern as existing `tonone-agent-tracker.js`)
2. Compress description to caveman style (drop articles, truncate, short synonyms)
3. Prepend line to local `.elephant/memory.md`
4. Prepend line with repo name to global `~/.claude/elephant/memory.md`
5. Create directories if they don't exist

**Caveman compression in the hook (lightweight rules):**

- Drop: a, an, the, just, really, basically, actually, simply
- Drop: "I've", "I'll", "we've", "we'll", "it's been"
- Shorten: "implemented" → "build", "successfully" → drop, "completed" → "done"
- Truncate to ~100 chars max per entry
- Preserve: code refs, file paths, numbers, proper nouns

### Manual entries

Skill: `/elephant`

| Command                    | Action                        |
| -------------------------- | ----------------------------- |
| `/elephant save <text>`    | Write routine entry           |
| `/elephant save !! <text>` | Write important entry         |
| `/elephant show`           | Print current memory contents |
| `/elephant compact`        | Compress old routine entries  |

## Startup Recall

Hook script: `hooks/elephant-recall.js`

Runs on SessionStart. Reads both memory files, builds smart summary, outputs as hook additional context.

**Summary logic:**

- Today's entries — show in full
- Last 7 days — show in full, capped at 10 lines
- Older than 7 days — only show `[!!]` entries
- Other repos (from global) — last 3 entries max, one-liner each
- Total block capped at 15 lines max

**Output format:**

```
🐘 ELEPHANT RECALL
├ [!!] 2026-04-12 14:30 : chose JWT over sessions — stateless API need
├ 2026-04-12 14:45 : spine build auth API + 12 endpoints. tests pass.
├ 2026-04-12 15:10 : relay deploy staging done.
├ 2026-04-11 09:20 : proof write 42 tests. coverage 87%.
├ ── other repos ──
├ billing-app : fix webhook retry logic (04-12)
└ 6 entries total │ 2 important │ oldest: 2026-04-05
```

**Empty state:**

```
🐘 ELEPHANT RECALL
└ nothing yet. use /elephant save to start remembering.
```

**Style:** Box-drawing lines per tonone output-kit. Footer with counts.

## Compression (`/elephant compact`)

Merges old routine entries to save space:

- Entries older than 7 days without `[!!]` get merged
- Multiple entries from same day collapse into one line
- Example: 3 entries from 04-05 → `2026-04-05 : spine auth + proof 42 tests + relay staging deploy`
- `[!!]` entries never touched regardless of age
- Applies to both local and global memory files

## Hook Registration

Added to `.claude-plugin/plugin.json` hooks:

```json
{
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/elephant-recall.js\""
        }
      ]
    }
  ],
  "PostToolUse": [
    {
      "matcher": "Agent",
      "hooks": [
        {
          "type": "command",
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/elephant-writer.js\"",
          "timeout": 5
        }
      ]
    },
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/elephant-writer.js\"",
          "timeout": 5
        }
      ]
    },
    {
      "matcher": "Skill",
      "hooks": [
        {
          "type": "command",
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/elephant-writer.js\"",
          "timeout": 5
        }
      ]
    }
  ]
}
```

**Filtering logic inside `elephant-writer.js`:**

- `Agent` matcher: always capture. Extract description from agent result.
- `Bash` matcher: only capture if command contains `git commit`. Ignore all other Bash calls.
- `Skill` matcher: always capture. Extract skill name from tool input.

## Files to Create

| File                                         | Purpose                                                |
| -------------------------------------------- | ------------------------------------------------------ |
| `hooks/elephant-recall.js`                   | SessionStart hook — reads memory, renders recap block  |
| `hooks/elephant-writer.js`                   | PostToolUse hook — auto-captures entries to both files |
| `skills/elephant/SKILL.md`                   | Skill definition for manual commands                   |
| `skills/elephant/.claude-plugin/plugin.json` | Plugin manifest for the skill                          |
| `.elephant/.gitignore`                       | Ignore `memory.md` (local memory is per-machine)       |

## Integration with Existing Hooks

- `elephant-recall.js` runs alongside `install-statusline.sh` on SessionStart
- `elephant-writer.js` runs alongside `tonone-agent-tracker.js` on PostToolUse (Agent)
- No conflicts — each hook reads stdin independently, writes to different files
- Timeout of 5s per hook call (same as agent-tracker)

## Repo Detection for Global Memory

The writer hook determines repo name from:

1. `cwd` field in stdin JSON
2. Extract last path component (e.g., `/Users/f/repos/tn/tonone` → `tonone`)
3. Use as repo identifier in global memory entries
