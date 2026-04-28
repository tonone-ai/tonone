# Elephant Standalone Repo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a standalone `elephant` Claude Code plugin repo with full launch kit — plugin manifest, skill file, install script, README, and GitHub Pages landing page.

**Architecture:** New git repo at `~/repos/elephant/`. Plugin-structured layout (`.claude-plugin/` + `skills/elephant/`). GitHub Pages served from `docs/`. No build step — pure static files.

**Tech Stack:** Bash (install.sh), Markdown (README, SKILL.md), JSON (plugin.json), HTML/CSS (landing page, no frameworks)

---

### Task 1: Init repo + scaffold directories

**Files:**

- Create: `~/repos/elephant/` (git repo)
- Create: `~/repos/elephant/.claude-plugin/`
- Create: `~/repos/elephant/skills/elephant/`
- Create: `~/repos/elephant/docs/`

- [ ] **Step 1: Create repo directory and init git**

```bash
mkdir -p ~/repos/elephant
cd ~/repos/elephant
git init
```

Expected output: `Initialized empty Git repository in ~/repos/elephant/.git/`

- [ ] **Step 2: Create directory structure**

```bash
mkdir -p .claude-plugin skills/elephant docs
```

- [ ] **Step 3: Create .gitignore**

Create `~/repos/elephant/.gitignore`:

```
.DS_Store
*.swp
```

- [ ] **Step 4: Verify structure**

```bash
find . -not -path './.git/*' | sort
```

Expected:

```
.
./.gitignore
./.claude-plugin
./docs
./skills
./skills/elephant
```

---

### Task 2: LICENSE

**Files:**

- Create: `~/repos/elephant/LICENSE`

- [ ] **Step 1: Write MIT license**

Create `~/repos/elephant/LICENSE`:

```
MIT License

Copyright (c) 2026 tonone-ai

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore LICENSE
git commit -m "chore: init repo"
```

---

### Task 3: Plugin manifest

**Files:**

- Create: `~/repos/elephant/.claude-plugin/plugin.json`

- [ ] **Step 1: Write plugin manifest**

Create `~/repos/elephant/.claude-plugin/plugin.json`:

```json
{
  "name": "elephant",
  "version": "1.1.0",
  "description": "Persistent memory for Claude Code. Never forget a session.",
  "skills": [
    {
      "name": "elephant",
      "path": "../skills/elephant/SKILL.md",
      "trigger": "/elephant"
    }
  ],
  "author": "tonone-ai <hello@tonone.ai>",
  "license": "MIT",
  "homepage": "https://github.com/tonone-ai/elephant"
}
```

- [ ] **Step 2: Validate JSON**

```bash
cat .claude-plugin/plugin.json | python3 -m json.tool > /dev/null && echo "valid JSON"
```

Expected: `valid JSON`

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "feat: add plugin manifest"
```

---

### Task 4: Skill file

**Files:**

- Create: `~/repos/elephant/skills/elephant/SKILL.md`

- [ ] **Step 1: Write skill file**

Create `~/repos/elephant/skills/elephant/SKILL.md`:

````markdown
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
````

- [ ] **Step 2: Verify file exists and has content**

```bash
wc -l skills/elephant/SKILL.md
```

Expected: `115 skills/elephant/SKILL.md` (approximately)

- [ ] **Step 3: Commit**

```bash
git add skills/elephant/SKILL.md
git commit -m "feat: add elephant skill v1.1.0"
```

---

### Task 5: Install script

**Files:**

- Create: `~/repos/elephant/install.sh`

- [ ] **Step 1: Write install script**

Create `~/repos/elephant/install.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

PLUGIN_DIR="${HOME}/.claude/plugins/elephant"
REPO="https://raw.githubusercontent.com/tonone-ai/elephant/main"

echo "🐘 installing elephant..."

mkdir -p "${PLUGIN_DIR}/.claude-plugin"
mkdir -p "${PLUGIN_DIR}/skills/elephant"

curl -fsSL "${REPO}/.claude-plugin/plugin.json" -o "${PLUGIN_DIR}/.claude-plugin/plugin.json"
curl -fsSL "${REPO}/skills/elephant/SKILL.md"   -o "${PLUGIN_DIR}/skills/elephant/SKILL.md"

echo "✓ installed to ${PLUGIN_DIR}"
echo ""
echo "restart Claude Code, then try:"
echo "  /elephant takeover"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x install.sh
```

- [ ] **Step 3: Smoke test (dry run — check syntax only)**

```bash
bash -n install.sh && echo "syntax ok"
```

Expected: `syntax ok`

- [ ] **Step 4: Commit**

```bash
git add install.sh
git commit -m "feat: add curl install script"
```

---

### Task 6: CONTRIBUTING.md

**Files:**

- Create: `~/repos/elephant/CONTRIBUTING.md`

- [ ] **Step 1: Write contributing guide**

Create `~/repos/elephant/CONTRIBUTING.md`:

```markdown
# Contributing

elephant is a single-skill Claude Code plugin. Contributions welcome.

## What's here

- `skills/elephant/SKILL.md` — the skill. All logic lives here.
- `.claude-plugin/plugin.json` — plugin manifest.
- `install.sh` — curl installer.
- `docs/index.html` — GitHub Pages landing page.

## How to contribute

1. Fork the repo
2. Make your change
3. Test it: install locally with `bash install.sh` (update REPO var to point to local files, or copy manually to `~/.claude/plugins/elephant/`)
4. Open a PR with a clear description of what changed and why

## Skill changes

The skill is plain Markdown. Edit `skills/elephant/SKILL.md` directly.
Test by running the commands in Claude Code after installing locally.

## What we won't merge

- Dependencies (no npm, pip, brew requirements)
- Cloud sync or remote storage
- Breaking changes to `.elephant/memory.md` format without a migration path
```

- [ ] **Step 2: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: add contributing guide"
```

---

### Task 7: README

**Files:**

- Create: `~/repos/elephant/README.md`

- [ ] **Step 1: Write README**

Create `~/repos/elephant/README.md`:

````markdown
# 🐘 elephant

> "Consider the elephant. Legend has it its memory is so robust it never forgets."
> — Gavin Belson

Claude Code forgets everything between sessions. Elephant fixes that.

![version](https://img.shields.io/badge/version-1.1.0-green)
![license](https://img.shields.io/badge/license-MIT-green)
![platform](https://img.shields.io/badge/platform-Claude%20Code-blue)

<!-- demo.gif coming soon -->

---

## Install

**Plugin registry:**

```bash
claude plugins install github:tonone-ai/elephant
```
````

**Or curl:**

```bash
curl -fsSL https://raw.githubusercontent.com/tonone-ai/elephant/main/install.sh | bash
```

Restart Claude Code. Done.

---

## Commands

| Command                    | What it does                               |
| -------------------------- | ------------------------------------------ |
| `/elephant save <text>`    | Save a memory entry                        |
| `/elephant save !! <text>` | Save an important entry (never compressed) |
| `/elephant show`           | Print your memory                          |
| `/elephant compact`        | Merge old entries to save tokens           |
| `/elephant takeover [N]`   | Bootstrap from git history (cold start)    |

---

## How it works

Elephant writes to two files:

- **`.elephant/memory.md`** — local, project-specific
- **`~/.claude/elephant/memory.md`** — global, across all projects

Entries are caveman-compressed (articles and filler dropped) to minimize token usage.
Important entries (`[!!]`) are never compressed or deleted.

### Cold start

New project? No history? Run `/elephant takeover` — it reads your last 60 commits and seeds memory automatically. Important commits (`feat:`, `fix:`, PRs) get marked `[!!]`.

---

## Memory format

```
[!!] 2026-04-12 13:58 : feat: add stripe webhooks
2026-04-12 12:00 : fix null pointer in auth middleware
```

---

## License

MIT — see [LICENSE](LICENSE)

Made by [tonone-ai](https://github.com/tonone-ai)

````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with install, commands, format"
````

---

### Task 8: Landing page

**Files:**

- Create: `~/repos/elephant/docs/index.html`

- [ ] **Step 1: Write landing page**

Create `~/repos/elephant/docs/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>🐘 elephant — Claude Code memory</title>
    <meta
      name="description"
      content="Claude Code forgets. Elephant doesn't. Persistent memory for Claude Code sessions."
    />
    <style>
      *,
      *::before,
      *::after {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
      }

      :root {
        --bg: #0d1f0d;
        --bg2: #162416;
        --bg3: #1e321e;
        --cream: #f0ead6;
        --cream-dim: #9a9080;
        --green: #4ade80;
        --amber: #f59e0b;
        --border: #2a3d2a;
        --mono: "Courier New", Courier, monospace;
      }

      html {
        scroll-behavior: smooth;
      }

      body {
        background: var(--bg);
        color: var(--cream);
        font-family:
          system-ui,
          -apple-system,
          BlinkMacSystemFont,
          "Segoe UI",
          sans-serif;
        line-height: 1.6;
        min-height: 100vh;
      }

      /* ── NAV ── */
      nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.25rem 2rem;
        border-bottom: 1px solid var(--border);
        position: sticky;
        top: 0;
        background: var(--bg);
        z-index: 10;
      }
      .nav-brand {
        font-weight: 700;
        font-size: 1.1rem;
      }
      .nav-star {
        background: var(--bg3);
        border: 1px solid var(--border);
        color: var(--cream);
        padding: 0.4rem 1rem;
        border-radius: 6px;
        text-decoration: none;
        font-size: 0.875rem;
        transition: border-color 0.15s;
      }
      .nav-star:hover {
        border-color: var(--green);
        color: var(--green);
      }

      /* ── HERO ── */
      .hero {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 6rem 2rem 5rem;
        gap: 1.5rem;
      }
      .hero-emoji {
        font-size: 5rem;
        line-height: 1;
      }
      .hero-quote {
        font-style: italic;
        color: var(--cream-dim);
        font-size: 1rem;
        max-width: 420px;
        line-height: 1.7;
      }
      .hero-attribution {
        color: var(--cream-dim);
        font-size: 0.85rem;
        margin-top: -0.75rem;
      }
      .hero-headline {
        font-size: clamp(2rem, 5vw, 3.5rem);
        font-weight: 800;
        line-height: 1.15;
        letter-spacing: -0.02em;
      }
      .hero-headline .accent {
        color: var(--green);
      }
      .hero-sub {
        color: var(--cream-dim);
        font-size: 1.1rem;
        max-width: 380px;
      }
      .hero-install {
        background: var(--bg2);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 0.9rem 1.75rem;
        font-family: var(--mono);
        font-size: 0.95rem;
        color: var(--green);
        cursor: pointer;
        user-select: all;
        transition: border-color 0.15s;
      }
      .hero-install:hover {
        border-color: var(--green);
      }
      .hero-install-hint {
        color: var(--cream-dim);
        font-size: 0.8rem;
        margin-top: -0.75rem;
      }

      /* ── DEMO ── */
      .section {
        padding: 4rem 2rem;
        max-width: 700px;
        margin: 0 auto;
      }
      .section-label {
        color: var(--green);
        font-family: var(--mono);
        font-size: 0.8rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 1.25rem;
      }
      .terminal {
        background: var(--bg2);
        border: 1px solid var(--border);
        border-radius: 10px;
        overflow: hidden;
      }
      .terminal-bar {
        background: var(--bg3);
        padding: 0.6rem 1rem;
        display: flex;
        gap: 0.5rem;
        align-items: center;
        border-bottom: 1px solid var(--border);
      }
      .dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
      }
      .dot-r {
        background: #ff5f57;
      }
      .dot-y {
        background: #febc2e;
      }
      .dot-g {
        background: #28c840;
      }
      .terminal-body {
        padding: 1.25rem 1.5rem;
        font-family: var(--mono);
        font-size: 0.875rem;
        line-height: 1.8;
      }
      .t-prompt {
        color: var(--green);
      }
      .t-out {
        color: var(--cream-dim);
      }
      .t-important {
        color: var(--amber);
      }
      .t-tip {
        color: var(--cream-dim);
        font-style: italic;
      }

      /* ── COMMANDS ── */
      .commands-grid {
        display: grid;
        gap: 1rem;
      }
      .cmd-card {
        background: var(--bg2);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1rem 1.25rem;
      }
      .cmd-name {
        font-family: var(--mono);
        color: var(--green);
        font-size: 0.9rem;
        margin-bottom: 0.25rem;
      }
      .cmd-desc {
        color: var(--cream-dim);
        font-size: 0.875rem;
      }
      .cmd-badge {
        display: inline-block;
        background: var(--amber);
        color: var(--bg);
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.1rem 0.4rem;
        border-radius: 3px;
        margin-left: 0.5rem;
        vertical-align: middle;
      }

      /* ── VALUE PROPS ── */
      .props {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1.5rem;
      }
      .prop {
        text-align: center;
      }
      .prop-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
      }
      .prop-title {
        font-weight: 700;
        margin-bottom: 0.25rem;
      }
      .prop-desc {
        color: var(--cream-dim);
        font-size: 0.875rem;
      }

      /* ── FOOTER ── */
      footer {
        border-top: 1px solid var(--border);
        padding: 2rem;
        text-align: center;
        color: var(--cream-dim);
        font-size: 0.875rem;
      }
      footer a {
        color: var(--cream-dim);
        text-decoration: underline;
      }
      footer a:hover {
        color: var(--cream);
      }

      /* ── DIVIDER ── */
      .divider {
        border: none;
        border-top: 1px solid var(--border);
        margin: 0;
      }
    </style>
  </head>
  <body>
    <!-- NAV -->
    <nav>
      <span class="nav-brand">🐘 elephant</span>
      <a
        class="nav-star"
        href="https://github.com/tonone-ai/elephant"
        target="_blank"
        rel="noopener"
        >★ Star on GitHub</a
      >
    </nav>

    <!-- HERO -->
    <section class="hero">
      <div class="hero-emoji">🐘</div>
      <p class="hero-quote">
        "Consider the elephant. Legend has it its memory is so robust it never
        forgets."
      </p>
      <p class="hero-attribution">— Gavin Belson</p>
      <h1 class="hero-headline">
        Claude Code <span class="accent">forgets</span>.<br />Elephant doesn't.
      </h1>
      <p class="hero-sub">
        Persistent memory for Claude Code sessions. No cloud. No config. Just a
        file.
      </p>
      <code class="hero-install"
        >claude plugins install github:tonone-ai/elephant</code
      >
      <p class="hero-install-hint">
        or: <code>curl -fsSL …/install.sh | bash</code>
      </p>
    </section>

    <hr class="divider" />

    <!-- DEMO -->
    <div class="section">
      <p class="section-label">Cold start → memory in one shot</p>
      <div class="terminal">
        <div class="terminal-bar">
          <div class="dot dot-r"></div>
          <div class="dot dot-y"></div>
          <div class="dot dot-g"></div>
        </div>
        <div class="terminal-body">
          <div><span class="t-prompt">/elephant takeover</span></div>
          <div class="t-out">&nbsp;</div>
          <div class="t-important">
            [!!] 2026-04-11 09:14 : feat: add stripe webhook handler
          </div>
          <div class="t-important">
            [!!] 2026-04-10 16:32 : fix: null pointer in auth middleware
          </div>
          <div class="t-out">2026-04-09 11:05 : refactor user model</div>
          <div class="t-out">2026-04-08 14:22 : update env vars in staging</div>
          <div class="t-important">
            [!!] 2026-04-07 10:00 : feat: onboarding flow (#142)
          </div>
          <div class="t-out">…</div>
          <div class="t-out">&nbsp;</div>
          <div class="t-out">
            seeded 60 entries (2026-02-01 → 2026-04-11) — 18 marked [!!]
          </div>
          <div class="t-tip">
            tip: run /elephant compact to merge old routine entries
          </div>
        </div>
      </div>
    </div>

    <hr class="divider" />

    <!-- COMMANDS -->
    <div class="section">
      <p class="section-label">Commands</p>
      <div class="commands-grid">
        <div class="cmd-card">
          <div class="cmd-name">/elephant save &lt;text&gt;</div>
          <div class="cmd-desc">
            Write a memory entry to local + global files. Caveman-compressed to
            save tokens.
          </div>
        </div>
        <div class="cmd-card">
          <div class="cmd-name">
            /elephant save !! &lt;text&gt; <span class="cmd-badge">!!</span>
          </div>
          <div class="cmd-desc">
            Write an important entry. Never compressed, never deleted.
          </div>
        </div>
        <div class="cmd-card">
          <div class="cmd-name">/elephant show</div>
          <div class="cmd-desc">Print your full memory file verbatim.</div>
        </div>
        <div class="cmd-card">
          <div class="cmd-name">/elephant compact</div>
          <div class="cmd-desc">
            Merge routine entries older than 7 days into single lines. Keeps
            token count low.
          </div>
        </div>
        <div class="cmd-card">
          <div class="cmd-name">/elephant takeover [N]</div>
          <div class="cmd-desc">
            Bootstrap from git history. Seeds the last N commits (default 60).
            Marks important commits <span class="cmd-badge">!!</span>
          </div>
        </div>
      </div>
    </div>

    <hr class="divider" />

    <!-- VALUE PROPS -->
    <div class="section">
      <div class="props">
        <div class="prop">
          <div class="prop-icon">📁</div>
          <div class="prop-title">Just a file</div>
          <div class="prop-desc">
            Memory lives in <code>.elephant/memory.md</code>. Readable,
            editable, committable.
          </div>
        </div>
        <div class="prop">
          <div class="prop-icon">☁️</div>
          <div class="prop-title">No cloud</div>
          <div class="prop-desc">
            Nothing leaves your machine. No API keys beyond your Claude
            subscription.
          </div>
        </div>
        <div class="prop">
          <div class="prop-icon">🗜️</div>
          <div class="prop-title">Token-efficient</div>
          <div class="prop-desc">
            Caveman compression. Articles and filler dropped. Compact keeps
            history lean.
          </div>
        </div>
      </div>
    </div>

    <hr class="divider" />

    <!-- FOOTER -->
    <footer>
      <p>
        MIT license ·
        <a
          href="https://github.com/tonone-ai/elephant"
          target="_blank"
          rel="noopener"
          >GitHub</a
        >
        · made by
        <a href="https://github.com/tonone-ai" target="_blank" rel="noopener"
          >tonone-ai</a
        >
      </p>
    </footer>
  </body>
</html>
```

- [ ] **Step 2: Verify HTML is valid (basic check)**

```bash
python3 -c "
import html.parser, pathlib
class Check(html.parser.HTMLParser):
    pass
p = Check()
p.feed(pathlib.Path('docs/index.html').read_text())
print('HTML parsed ok')
"
```

Expected: `HTML parsed ok`

- [ ] **Step 3: Open in browser to visually verify**

```bash
open docs/index.html
```

Check: 🐘 emoji visible in hero, Gavin Belson quote renders, terminal demo block shows amber `[!!]` lines, command cards render, footer present.

- [ ] **Step 4: Commit**

```bash
git add docs/index.html
git commit -m "feat: add GitHub Pages landing page"
```

---

### Task 9: GitHub setup + publish

**Files:** None new — configuration steps only.

- [ ] **Step 1: Create GitHub repo**

Go to github.com/new. Name: `elephant`. Public. No auto-init (we have local git already).

- [ ] **Step 2: Push**

```bash
git remote add origin git@github.com:<owner>/elephant.git
git branch -M main
git push -u origin main
```

- [ ] **Step 3: Enable GitHub Pages**

GitHub repo → Settings → Pages → Source: `Deploy from branch` → Branch: `main` → Folder: `/docs` → Save.

Wait ~60 seconds. Visit `https://<owner>.github.io/elephant/` to confirm landing page is live.

- [ ] **Step 4: Update repo URLs**

In `.claude-plugin/plugin.json`, `install.sh`, and `README.md`, replace `tonone-ai` with actual owner if different. Commit and push.

```bash
git add .
git commit -m "chore: update repo URLs with actual owner"
git push
```

- [ ] **Step 5: Add repo topics on GitHub**

GitHub repo → About (gear icon) → Topics: `claude-code`, `claude`, `memory`, `ai`, `productivity`, `plugin`

- [ ] **Step 6: Confirm plugin install works**

In a new Claude Code session:

```bash
claude plugins install github:<owner>/elephant
```

Then in Claude Code: `/elephant show` → should print `nothing yet.`

Then: `/elephant takeover` → should seed from git history.

---

## Launch checklist

After all tasks complete:

- [ ] Landing page live at `https://<owner>.github.io/elephant/`
- [ ] `claude plugins install github:<owner>/elephant` works end-to-end
- [ ] `/elephant takeover` seeds memory correctly
- [ ] `/elephant save`, `/elephant show`, `/elephant compact` all work
- [ ] README has correct URLs and badge links

**Social copy ready to post (X/Twitter):**

> "Consider the elephant. Legend has it its memory is so robust it never forgets." — Gavin Belson
>
> Claude Code forgets. So I built elephant.
>
> 4 commands. Local file. No cloud. Seeds itself from your git history in one shot.
>
> `/elephant takeover` — done.
>
> 🐘 github.com/<owner>/elephant
