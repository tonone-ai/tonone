# Elephant Memory System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-capture agent work, commits, and skill runs into persistent memory files; surface a smart recall block on session start; support manual entry and compression via `/elephant` skill.

**Architecture:** Two JS hooks handle read (SessionStart recall) and write (PostToolUse capture). Entries live in `.elephant/memory.md` (local, git-ignored) and `~/.claude/elephant/memory.md` (global). A SKILL.md handles manual commands. Plugin.json wires everything together.

**Tech Stack:** Node.js (no deps beyond stdlib), Claude Code plugin hooks, SKILL.md frontmatter

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `hooks/elephant-recall.js` | Create | SessionStart hook — reads both memory files, outputs recall block |
| `hooks/elephant-writer.js` | Create | PostToolUse hook — compresses and prepends entries to both files |
| `skills/elephant/SKILL.md` | Create | Skill for manual `/elephant` commands |
| `.elephant/.gitignore` | Create | Ignore `memory.md` (per-machine) |
| `.claude-plugin/plugin.json` | Modify | Wire new hooks into SessionStart + PostToolUse |

---

### Task 1: `.elephant/.gitignore`

**Files:**
- Create: `.elephant/.gitignore`

- [ ] **Step 1: Create the gitignore**

```
memory.md
```

- [ ] **Step 2: Verify git ignores it**

```bash
mkdir -p .elephant && touch .elephant/memory.md
git check-ignore -v .elephant/memory.md
```
Expected: `.elephant/.gitignore:1:memory.md   .elephant/memory.md`

- [ ] **Step 3: Commit**

```bash
git add .elephant/.gitignore
git commit -m "feat(elephant): add .elephant dir with gitignore for local memory"
```

---

### Task 2: `hooks/elephant-writer.js`

**Files:**
- Create: `hooks/elephant-writer.js`

PostToolUse hook. Reads stdin JSON, extracts a caveman-compressed description, prepends an entry to both local and global memory files. Filters: Agent (always), Bash (only git commit), Skill (always).

- [ ] **Step 1: Create the hook**

```js
#!/usr/bin/env node
// elephant-writer — PostToolUse hook
// Auto-captures agent completions, git commits, and skill runs to memory files.

"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");

const PLUGIN_ROOT =
  process.env.CLAUDE_PLUGIN_ROOT || path.join(__dirname, "..");
const LOCAL_DIR = path.join(PLUGIN_ROOT, ".elephant");
const LOCAL_MEM = path.join(LOCAL_DIR, "memory.md");
const GLOBAL_DIR = path.join(os.homedir(), ".claude", "elephant");
const GLOBAL_MEM = path.join(GLOBAL_DIR, "memory.md");

// Detect repo name from PLUGIN_ROOT
function repoName() {
  return path.basename(PLUGIN_ROOT);
}

// Caveman compression — drop filler, shorten, truncate to ~100 chars
function compress(text) {
  if (!text) return "";
  const drop = /\b(a|an|the|just|really|basically|actually|simply|successfully|I've|I'll|we've|we'll|it's been)\b/gi;
  const shorten = [
    [/\bimplemented\b/gi, "built"],
    [/\bcompleted\b/gi, "done"],
    [/\bcreated\b/gi, "create"],
    [/\bgenerated\b/gi, "gen"],
    [/\bfunctions?\b/gi, "fn"],
  ];
  let out = text.replace(drop, "").replace(/\s{2,}/g, " ").trim();
  for (const [re, rep] of shorten) out = out.replace(re, rep);
  return out.slice(0, 100).trim();
}

// Format timestamp as YYYY-MM-DD HH:MM
function ts() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Prepend a line to a file (create file + dirs if needed)
function prepend(filePath, line) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  let existing = "";
  try {
    existing = fs.readFileSync(filePath, "utf8");
  } catch {}
  const tmp = filePath + ".tmp." + process.pid;
  fs.writeFileSync(tmp, line + "\n" + existing);
  fs.renameSync(tmp, filePath);
}

// Main
let raw = "";
const timeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (c) => (raw += c));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    const data = JSON.parse(raw);
    const tool = data.tool_name || "";
    const inp = data.tool_input || {};
    const out = data.tool_output || {};

    let desc = null;

    if (tool === "Agent") {
      // Only capture completions (not starts)
      const isStart = Boolean(out.agentId) && !out.output;
      if (isStart) process.exit(0);
      desc = inp.description || inp.prompt?.slice(0, 60) || "agent run";
      desc = compress(desc);
    } else if (tool === "Bash") {
      const cmd = inp.command || "";
      if (!cmd.includes("git commit")) process.exit(0);
      // Extract -m message if present
      const mMatch = cmd.match(/-m\s+["']([^"']{1,80})/);
      desc = mMatch ? `commit: ${mMatch[1]}` : `commit: ${compress(cmd.slice(0, 80))}`;
    } else if (tool === "Skill") {
      const skillName = inp.skill || "unknown";
      const args = inp.args ? ` ${inp.args.slice(0, 40)}` : "";
      desc = `ran /${skillName}${args}`;
    } else {
      process.exit(0);
    }

    if (!desc) process.exit(0);

    const stamp = ts();
    const localLine = `${stamp} : ${desc}`;
    const repo = repoName();
    const globalLine = `${stamp} : ${repo} : ${desc}`;

    prepend(LOCAL_MEM, localLine);
    prepend(GLOBAL_MEM, globalLine);
  } catch {
    // Silent fail
  }
});
```

- [ ] **Step 2: Make executable**

```bash
chmod +x hooks/elephant-writer.js
```

- [ ] **Step 3: Smoke-test Agent capture**

```bash
echo '{"tool_name":"Agent","tool_input":{"description":"spine build auth API"},"tool_output":{"output":"done"}}' \
  | node hooks/elephant-writer.js
cat .elephant/memory.md
```
Expected: one line like `2026-04-12 HH:MM : spine build auth API`

- [ ] **Step 4: Smoke-test Bash / git commit capture**

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m \"feat: add JWT auth middleware\""},"tool_output":{}}' \
  | node hooks/elephant-writer.js
cat .elephant/memory.md
```
Expected: new first line like `2026-04-12 HH:MM : commit: feat: add JWT auth middleware`

- [ ] **Step 5: Smoke-test Bash non-commit is ignored**

```bash
BEFORE=$(wc -l < .elephant/memory.md)
echo '{"tool_name":"Bash","tool_input":{"command":"ls -la"},"tool_output":{}}' \
  | node hooks/elephant-writer.js
AFTER=$(wc -l < .elephant/memory.md)
[ "$BEFORE" = "$AFTER" ] && echo "PASS: non-commit ignored" || echo "FAIL"
```

- [ ] **Step 6: Smoke-test Skill capture**

```bash
echo '{"tool_name":"Skill","tool_input":{"skill":"ship","args":""},"tool_output":{}}' \
  | node hooks/elephant-writer.js
cat .elephant/memory.md
```
Expected: new first line like `2026-04-12 HH:MM : ran /ship`

- [ ] **Step 7: Verify global file updated**

```bash
cat ~/.claude/elephant/memory.md
```
Expected: matching entry with `tonone :` prefix.

- [ ] **Step 8: Verify Agent start is ignored (no duplicate)**

```bash
BEFORE=$(wc -l < .elephant/memory.md)
echo '{"tool_name":"Agent","tool_input":{"description":"some agent"},"tool_output":{"agentId":"abc123"}}' \
  | node hooks/elephant-writer.js
AFTER=$(wc -l < .elephant/memory.md)
[ "$BEFORE" = "$AFTER" ] && echo "PASS: start ignored" || echo "FAIL"
```

- [ ] **Step 9: Commit**

```bash
git add hooks/elephant-writer.js
git commit -m "feat(elephant): add writer hook — auto-captures agent completions, commits, skill runs"
```

---

### Task 3: `hooks/elephant-recall.js`

**Files:**
- Create: `hooks/elephant-recall.js`

SessionStart hook. Reads both memory files. Filters entries by age. Renders a box-drawing recall block to stdout. Exits silently if both files are empty or missing.

- [ ] **Step 1: Create the hook**

```js
#!/usr/bin/env node
// elephant-recall — SessionStart hook
// Reads local + global memory, renders a smart recall block.

"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");

const PLUGIN_ROOT =
  process.env.CLAUDE_PLUGIN_ROOT || path.join(__dirname, "..");
const LOCAL_MEM = path.join(PLUGIN_ROOT, ".elephant", "memory.md");
const GLOBAL_MEM = path.join(os.homedir(), ".claude", "elephant", "memory.md");
const REPO = path.basename(PLUGIN_ROOT);

// Parse a memory file into entry objects
// Line format: `[!!]? YYYY-MM-DD HH:MM : [repo :] text`
function parseFile(filePath, isGlobal) {
  try {
    const lines = fs.readFileSync(filePath, "utf8").split("\n").filter(Boolean);
    return lines.map((line) => {
      const important = line.startsWith("[!!]");
      const body = important ? line.slice(4).trim() : line.trim();
      // Extract timestamp
      const tsMatch = body.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2})/);
      const tsStr = tsMatch ? tsMatch[1] : null;
      const date = tsStr ? new Date(tsStr) : null;
      const rest = tsStr ? body.slice(tsStr.length).replace(/^\s*:\s*/, "") : body;

      let repo = null;
      let text = rest;
      if (isGlobal) {
        // `repo : text`
        const repoMatch = rest.match(/^([^:]+?)\s*:\s*(.+)$/);
        if (repoMatch) {
          repo = repoMatch[1].trim();
          text = repoMatch[2].trim();
        }
      }

      return { important, tsStr, date, repo, text, raw: line };
    });
  } catch {
    return [];
  }
}

function main() {
  const now = new Date();
  const todayStr = now.toISOString().slice(0, 10);
  const cutoff7 = new Date(now - 7 * 24 * 60 * 60 * 1000);

  // Local entries (this repo)
  const local = parseFile(LOCAL_MEM, false);

  // Global entries (other repos only)
  const global = parseFile(GLOBAL_MEM, true).filter(
    (e) => e.repo && e.repo !== REPO
  );

  if (local.length === 0 && global.length === 0) {
    console.log(
      "🐘 ELEPHANT RECALL\n└ nothing yet. use /elephant save to start remembering."
    );
    return;
  }

  const lines = [];

  // Local: today in full, last 7 days in full (cap 10), older only [!!]
  const today = local.filter((e) => e.tsStr?.startsWith(todayStr));
  const week = local.filter(
    (e) => !e.tsStr?.startsWith(todayStr) && e.date && e.date >= cutoff7
  );
  const older = local.filter(
    (e) => e.date && e.date < cutoff7 && e.important
  );

  for (const e of today) lines.push(`${e.important ? "[!!] " : ""}${e.tsStr} : ${e.text}`);
  for (const e of week.slice(0, 10 - today.length)) lines.push(`${e.important ? "[!!] " : ""}${e.tsStr} : ${e.text}`);
  for (const e of older) lines.push(`[!!] ${e.tsStr} : ${e.text}`);

  // Other repos: last 3 entries
  const otherEntries = global.slice(0, 3);
  if (otherEntries.length > 0) {
    lines.push("── other repos ──");
    for (const e of otherEntries) {
      const dateShort = e.tsStr ? e.tsStr.slice(5, 10) : "??-??";
      lines.push(`${e.repo} : ${e.text} (${dateShort})`);
    }
  }

  // Cap at 15 lines
  const capped = lines.slice(0, 15);

  // Footer stats
  const total = local.length;
  const important = local.filter((e) => e.important).length;
  const oldest = local.length
    ? local[local.length - 1].tsStr?.slice(0, 10) || "?"
    : "?";

  // Render
  const body = capped.map((l, i) => {
    const prefix = i === capped.length - 1 && otherEntries.length === 0 ? "└" : "├";
    return `${prefix} ${l}`;
  });

  console.log("🐘 ELEPHANT RECALL");
  for (const l of body) console.log(l);
  console.log(
    `└ ${total} entries total │ ${important} important │ oldest: ${oldest}`
  );
}

main();
```

- [ ] **Step 2: Make executable**

```bash
chmod +x hooks/elephant-recall.js
```

- [ ] **Step 3: Test with data in memory file**

```bash
node hooks/elephant-recall.js
```
Expected: box-drawing output showing entries from Task 2 smoke tests.

- [ ] **Step 4: Test empty state**

```bash
mv .elephant/memory.md .elephant/memory.md.bak 2>/dev/null || true
mv ~/.claude/elephant/memory.md ~/.claude/elephant/memory.md.bak 2>/dev/null || true
node hooks/elephant-recall.js
```
Expected:
```
🐘 ELEPHANT RECALL
└ nothing yet. use /elephant save to start remembering.
```

- [ ] **Step 5: Restore memory files**

```bash
mv .elephant/memory.md.bak .elephant/memory.md 2>/dev/null || true
mv ~/.claude/elephant/memory.md.bak ~/.claude/elephant/memory.md 2>/dev/null || true
```

- [ ] **Step 6: Commit**

```bash
git add hooks/elephant-recall.js
git commit -m "feat(elephant): add recall hook — startup summary of local + global memory"
```

---

### Task 4: `skills/elephant/SKILL.md`

**Files:**
- Create: `skills/elephant/SKILL.md`

Manual skill for `/elephant save`, `/elephant show`, `/elephant compact`.

- [ ] **Step 1: Create the skill**

```markdown
---
name: elephant
description: Persistent memory commands. /elephant save <text> — write entry. /elephant save !! <text> — write important entry. /elephant show — print memory. /elephant compact — compress old entries.
allowed-tools: Read, Write, Edit, Bash
version: 1.0.0
author: tonone-ai <hello@tonone.ai>
license: MIT
---

# Elephant — Manual Memory Commands

Manage the elephant memory system. Local file: `.elephant/memory.md`. Global file: `~/.claude/elephant/memory.md`.

## Entry Format

```
[!!]? YYYY-MM-DD HH:MM : text
```

`[!!]` = important (never compressed). No prefix = routine (eligible for compression after 7 days).

All text caveman-compressed: drop articles (a/an/the), filler (just/really/basically/actually), fragments OK, short synonyms.

## Commands

Parse the args provided to this skill invocation:

### `/elephant save <text>`

Write a routine entry.

1. Get current timestamp: `date "+%Y-%m-%d %H:%M"`
2. Format line: `YYYY-MM-DD HH:MM : <compressed text>`
3. Prepend to `.elephant/memory.md` (create dir + file if needed)
4. Prepend `YYYY-MM-DD HH:MM : <repo> : <compressed text>` to `~/.claude/elephant/memory.md`
5. Confirm: `saved: <line>`

Compress text: drop a/an/the/just/really/basically/actually/simply, fragments OK, max 100 chars.

Repo name = last component of current working directory path.

### `/elephant save !! <text>`

Same as above but prefix line with `[!!] `.

### `/elephant show`

Read `.elephant/memory.md` and print full contents verbatim.

If file missing: print `nothing yet.`

### `/elephant compact`

Compress old routine entries (older than 7 days, no `[!!]` prefix).

1. Read `.elephant/memory.md`
2. Group non-`[!!]` entries older than 7 days by date (YYYY-MM-DD)
3. Per day: merge all entries → single line: `YYYY-MM-DD : <entry1 text> + <entry2 text> + ...`
4. Keep `[!!]` entries and entries ≤ 7 days old untouched
5. Write compacted file back
6. Do same for `~/.claude/elephant/memory.md` (filter to this repo's entries only)
7. Report: `compacted N entries into M lines`
```

- [ ] **Step 2: Verify skill discovered**

```bash
ls skills/elephant/
```
Expected: `SKILL.md`

- [ ] **Step 3: Commit**

```bash
git add skills/elephant/SKILL.md
git commit -m "feat(elephant): add /elephant skill — save, show, compact commands"
```

---

### Task 5: Wire hooks into `plugin.json`

**Files:**
- Modify: `.claude-plugin/plugin.json`

Add `elephant-recall.js` to SessionStart. Add `elephant-writer.js` to PostToolUse for Agent, Bash, and Skill matchers.

- [ ] **Step 1: Update plugin.json**

Replace the hooks section with:

```json
"hooks": {
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/install-statusline.sh\""
        },
        {
          "type": "command",
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/elephant-recall.js\"",
          "timeout": 5
        },
        {
          "type": "command",
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-update-check.js\"",
          "timeout": 8
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
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-agent-tracker.js\"",
          "timeout": 5
        },
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
    },
    {
      "matcher": "ExitPlanMode",
      "hooks": [
        {
          "type": "command",
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-worktree-create.js\"",
          "timeout": 10
        }
      ]
    }
  ],
  "PreToolUse": [
    {
      "matcher": "Edit|Write|NotebookEdit",
      "hooks": [
        {
          "type": "command",
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-worktree-gate.js\"",
          "timeout": 5
        }
      ]
    }
  ],
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-notify.js\"",
          "timeout": 5
        }
      ]
    }
  ],
  "Notification": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-notify.js\"",
          "timeout": 5
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: Validate JSON**

```bash
node -e "JSON.parse(require('fs').readFileSync('.claude-plugin/plugin.json','utf8')); console.log('valid')"
```
Expected: `valid`

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "feat(elephant): wire recall + writer hooks into plugin.json"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| Auto-capture Agent completions | Task 2 |
| Auto-capture git commits | Task 2 |
| Auto-capture Skill runs | Task 2 |
| Prepend to local `.elephant/memory.md` | Task 2 |
| Prepend to global `~/.claude/elephant/memory.md` | Task 2 |
| Caveman compression in writer | Task 2 |
| SessionStart recall block | Task 3 |
| Today / 7-day / older filter logic | Task 3 |
| Other repos from global (last 3) | Task 3 |
| 15-line cap | Task 3 |
| Empty state message | Task 3 |
| Footer counts | Task 3 |
| `/elephant save` | Task 4 |
| `/elephant save !!` | Task 4 |
| `/elephant show` | Task 4 |
| `/elephant compact` | Task 4 |
| `.elephant/.gitignore` | Task 1 |
| Hook registration in plugin.json | Task 5 |
| `[!!]` never compress | Task 4 |

**Gaps:** None found.

**Placeholder scan:** No TBD, TODO, or vague steps found.

**Type consistency:** No shared types across tasks — pure JS + markdown.
