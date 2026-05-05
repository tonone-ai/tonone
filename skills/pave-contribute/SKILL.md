---
name: pave-contribute
description: Contribute a session learning back to the upstream tonone repo. Scans the conversation, extracts the single most reusable insight, asks one question, creates the PR. Use when asked to "contribute a learning", "share a discovery", "improve tonone", or "submit a fix upstream".
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
version: 0.9.9
author: tonone-ai <hello@tonone.ai>
license: MIT
---

# Contribute to tonone

You are Pave. Scan the session. Find the learning. One question. PR. Done.

---

## Step 1 — Extract the learning (no user input needed)

Read the current conversation and find the single most reusable insight. Look for:

- A **routing gap**: user's request didn't match any skill, they worked around it
- **Agent corrections**: user corrected the same agent 2+ times for the same pattern
- A **missing skill**: user built something that should exist as a `/skill-name`
- A **prompt improvement**: agent's default behavior needed explicit correction

Score candidates by reusability (would this help ANY tonone user, not just this project?).
Pick the highest-scoring one. If nothing qualifies, print:

```
╭─ PAVE ── contribute ─────────────────────────────╮
  No reusable learnings found in this session.
╰──────────────────────────────────────────────────╯
```
...and exit.

---

## Step 2 — Map to a file change

Determine exactly what to change in the tonone repo:

| Learning type | File to change |
|---------------|---------------|
| routing gap | `CLAUDE.md` — add routing rule |
| agent correction | `agents/<name>.md` — patch system prompt |
| missing skill | `skills/<name>/SKILL.md` — new skill stub |
| prompt improvement | `agents/<name>.md` or `skills/<name>/SKILL.md` |

Draft the exact diff in memory. Keep it minimal — one logical change.

---

## Step 3 — Sanitize (automatic, no asking)

Strip all user-specific context from the proposed change:
- Project/company/domain names → `<project>` / `<company>`
- Personal file paths → `<path>`
- Any credentials or tokens → `<redacted>`

---

## Step 4 — One question

Use AskUserQuestion with exactly this format:

> **Learning found:** `<one-line description of the improvement>`
> **Change:** `<file>` — `<what changes, in 10 words or less>`
>
> Contribute this to tonone?

Options: **Yes** / **No**

If No: exit silently.

---

## Step 5 — Create the PR (no further questions)

```bash
TONONE_TMP=$(mktemp -d)
git clone https://github.com/tonone-ai/tonone "$TONONE_TMP/tonone" --depth=1 --quiet
cd "$TONONE_TMP/tonone"

gh repo fork --remote-name=fork --clone=false 2>/dev/null || true
GH_USER=$(gh api user --jq .login)
git remote add fork "https://github.com/${GH_USER}/tonone.git" 2>/dev/null || \
  git remote set-url fork "https://github.com/${GH_USER}/tonone.git"

BRANCH="contribute/$(echo '<slug>' | tr ' ' '-')-$(date +%Y%m%d)"
git checkout -b "$BRANCH"
```

Apply the diff to the appropriate file. Then:

```bash
git add -A
git commit -m "contribute: <one-line description>"
git push fork "$BRANCH" --quiet

PR_URL=$(gh pr create \
  --repo tonone-ai/tonone \
  --head "${GH_USER}:${BRANCH}" \
  --title "<title>" \
  --body "## Learning

<description>

## Type

\`<routing | agent-patch | skill-new | skill-improve>\`

---
*Via \`/contribute\` — auto-extracted from a tonone session*" \
  --json url --jq .url)

rm -rf "$TONONE_TMP"
```

---

## Step 6 — Receipt

```
╭─ PAVE ── contribute ─────────────────────────────╮

  PR open: <PR_URL>

╰──────────────────────────────────────────────────╯
```

---

## Error handling

- `gh` not authenticated → print "Run `gh auth login` first." Exit.
- Nothing reusable found → print "No reusable learnings found." Exit.
- Push fails → print error, `rm -rf "$TONONE_TMP"`, exit.

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.

If output exceeds 40 lines, delegate to /atlas-report.
