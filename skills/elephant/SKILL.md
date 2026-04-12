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

1. Get current timestamp: run `date "+%Y-%m-%d %H:%M"` via Bash
2. Compress text: drop a/an/the/just/really/basically/actually/simply, max 100 chars
3. Format line: `YYYY-MM-DD HH:MM : <compressed text>`
4. Prepend to `.elephant/memory.md` (create dir + file if needed)
5. Prepend `YYYY-MM-DD HH:MM : <repo> : <compressed text>` to `~/.claude/elephant/memory.md`
6. Confirm: output `saved: <line>`

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
5. Write compacted file back (use a temp file + rename for atomicity)
6. Do same for `~/.claude/elephant/memory.md` (filter to this repo's entries only when compacting)
7. Report: `compacted N entries into M lines`
