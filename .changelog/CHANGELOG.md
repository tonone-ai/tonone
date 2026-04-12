## 2026-04-12

### pave — Wire eager session worktrees, remove gate, update CLAUDE.md

- Replaced deferred `tonone-worktree-gate.js` + `tonone-worktree-create.js` with eager `tonone-worktree-session.js` — worktree created at `SessionStart`, not on first edit
- Human-readable branch names via `.claude/branch-slug` (e.g. `feat/auth-fixes` instead of UUID)
- Deleted 246 lines of gate/create hook code; `plugin.json` re-wired
- Files: `hooks/tonone-worktree-session.js`, `.claude-plugin/plugin.json`, `CLAUDE.md`

### surge — Add PR attribution for viral K-factor growth

- `hooks/tonone-pr-attribution.js` appends team credits block to every PR body
- Registered `session-tracker` and `pr-attribution` hooks in `plugin.json`
- Files: `hooks/tonone-pr-attribution.js`, `hooks/tonone-session-tracker.js`, `.claude-plugin/plugin.json`

### prism — Add shoutouts and statusline session goal (Line 4)

- Line 4 of 3-line statusline now displays session goal
- Shoutout rendering added alongside statusline update
- Files: `hooks/tonone-statusline.js`

### pave — Add elephant persistent memory system

- Writer hook auto-captures agent completions, commits, skill runs to `.elephant/`
- Recall hook surfaces startup summary from local + global memory
- `/elephant` skill: `save`, `show`, `compact`, `takeover` commands
- `takeover` cold-starts memory from git history for repos with no prior data
- Files: `hooks/tonone-elephant-writer.js`, `hooks/tonone-elephant-recall.js`, `skills/elephant.md`

### pave — Fix statusline resets_at Unix seconds parsing

- `resets_at` was parsed as milliseconds; corrected to seconds — fixes pace projection
- Files: `hooks/tonone-statusline.js`
