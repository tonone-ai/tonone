# Elephant Standalone Repo — Design Spec

**Date:** 2026-04-12  
**Status:** Approved  
**Scope:** Extract `elephant` skill from tonone, publish as standalone viral Claude Code plugin

---

## Problem

Claude Code has no persistent memory between sessions. The `elephant` skill in tonone solves this locally, but it's buried inside a 23-agent monorepo. Most Claude Code users will never find it.

---

## Goal

Ship `elephant` as a standalone GitHub repo that is easy to discover, install in one command, and share. Target: GitHub stars, HN/X virality.

---

## Repository Structure

```
elephant/
├── .claude-plugin/
│   └── plugin.json          ← plugin manifest
├── skills/
│   └── elephant/
│       └── SKILL.md         ← skill (extracted from tonone, standalone-adapted)
├── docs/
│   └── index.html           ← GitHub Pages landing page
├── README.md
├── install.sh               ← curl | bash convenience installer
├── CONTRIBUTING.md
└── LICENSE                  ← MIT
```

**Plugin ID:** `elephant`  
**Skill trigger:** `/elephant`  
**GitHub Pages:** enabled on `main` branch `/docs` folder

---

## Install Mechanisms

**Plugin registry (primary):**
```bash
claude plugins install github:<owner>/elephant
```

**Curl fallback:**
```bash
curl -fsSL https://raw.githubusercontent.com/<owner>/elephant/main/install.sh | bash
```

`install.sh` copies `skills/elephant/SKILL.md` and `.claude-plugin/plugin.json` into `~/.claude/plugins/elephant/`.

---

## Skill Content

Direct extraction from `tonone/skills/elephant/SKILL.md` (v1.1.0, MIT).  
Frontmatter updated: remove tonone-specific `author` coupling, bump as standalone.  

No logic changes. Four commands (save has two variants) unchanged:

| Command | Action |
|---|---|
| `/elephant save <text>` | Write routine memory entry |
| `/elephant save !! <text>` | Write important entry (never compressed) |
| `/elephant show` | Print full memory file |
| `/elephant compact` | Merge routine entries older than 7 days |
| `/elephant takeover [N]` | Bootstrap from git history (cold start) |

Memory files:
- Local: `.elephant/memory.md`
- Global: `~/.claude/elephant/memory.md`

---

## Landing Page (`docs/index.html`)

**Platform:** GitHub Pages, static HTML + CSS, no JS framework, no build step.

**Vibe:** Fun, personality-first, 🐘 emoji as logo. Bold colors — deep forest green bg, cream text, amber `[!!]` highlights.

**Hero:**
```
"Consider the elephant. Legend has it its memory
 is so robust it never forgets."
                              — Gavin Belson

Claude Code forgets. Elephant doesn't.

[Install — 1 command]
```

**Sections:**
1. Hero — quote + tagline + install CTA
2. Terminal demo block — static code block showing `/elephant takeover` output (demo GIF slot reserved: `<!-- demo.gif coming soon -->`)
3. Commands grid — 4 commands with one-line descriptions
4. "No cloud. No config. Just a file." — three-bullet value prop
5. Footer — MIT · GitHub link · tonone credit

---

## README

**Structure:**
```
🐘 elephant

"Consider the elephant. Legend has it its memory
 is so robust it never forgets." — Gavin Belson

Claude Code forgets everything between sessions. Elephant fixes that.

[badges]

## Install
## Commands  
## How it works
## Contributing
```

**Badges:** version, license (MIT), platform (Claude Code)

**Demo GIF:** slot reserved with placeholder comment. Owner records and drops in.

---

## Launch Kit

**Social copy (X/Twitter thread):**

> "Consider the elephant. Legend has it its memory is so robust it never forgets." — Gavin Belson
>
> Claude Code forgets. So I built elephant.
>
> 4 commands. Local file. No cloud. Seeds itself from your git history in one shot.
>
> `/elephant takeover` — done.
>
> 🐘 github.com/<owner>/elephant

**Launch targets:** X/Twitter, Hacker News (Show HN), r/ClaudeAI, r/singularity

---

## Out of Scope

- No multi-AI support (Claude Code only)
- No web backend, database, or auth
- No memory syncing across machines (local file only)
- No GUI
- Demo GIF: owner records post-ship

---

## License

MIT — same as tonone source.
