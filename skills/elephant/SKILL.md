---
name: elephant
description: Persistent memory commands. /elephant save <text> — write entry. /elephant save !! <text> — write important entry. /elephant show — print memory. /elephant compact — compress old entries. /elephant takeover [N] — seed memory from git history (cold start bootstrap).
allowed-tools: Read, Write, Edit, Bash
version: 1.1.0
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

### `/elephant takeover [N]`

Bootstrap memory from git history. Solves cold-start: empty memory → no recall. Seeds backdated entries from real commit history.

Default N = 60 commits. User can pass a number: `/elephant takeover 100`.

Steps:

1. Check if `.elephant/memory.md` exists. If it does and has entries, print warning:
   `⚠ memory already seeded (N entries). re-run to append git history below existing entries.`
   Then continue (don't abort — append git entries below existing).

2. Run: `git log --format="%ci|||%s|||%H" -N` via Bash.
   - `%ci` = ISO 8601 date: `2026-04-12 13:58:23 +0000`
   - `%s` = subject line
   - `%H` = full hash (used only to detect merge commits)

   If git fails (not a git repo): print `not a git repo. nothing to seed.` and stop.

   Skip bare upstream sync commits: lines where subject matches `^Merge branch '.+' of https?://` — these are `git pull` noise with no content value.

3. For each remaining commit line, parse:
   - **Timestamp**: take first 16 chars of `%ci` → `YYYY-MM-DD HH:MM`
   - **Subject**: caveman-compress (drop a/an/the/just/really/basically/actually/simply, max 100 chars)
   - **Important?**: mark `[!!]` if subject matches any of:
     - starts with `feat`, `fix`, `breaking`, `release`, `deploy`, `revert`
     - contains `Merge pull request` or `Merge branch`
     - conventional commit with `!` (e.g. `feat!:`, `fix!:`)
     - subject contains `(#` (PR reference = likely significant)

4. Format entries (newest first, matching git log default order):
   ```
   [!!] 2026-04-12 13:58 : feat: elephant memory system
   2026-04-12 12:00 : fix typo in output kit
   ```

5. Write to `.elephant/memory.md`:
   - If file didn't exist: create dir + file, write all entries.
   - If file existed: prepend nothing new to existing entries; instead append git entries BELOW (so existing human entries stay at top).
   - Use a temp file + rename for atomicity.

6. For each entry, also append to `~/.claude/elephant/memory.md` (repo-prefixed):
   ```
   [!!] 2026-04-12 13:58 : tonone : feat: elephant memory system
   ```
   Append only entries not already present (match on timestamp + text).

7. Report:
   ```
   seeded N entries (YYYY-MM-DD → YYYY-MM-DD) — M marked [!!]
   tip: run /elephant compact to merge old routine entries
   ```
