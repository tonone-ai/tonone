---
name: copy-slop
description: 'Run the deterministic copy-slop check on drafts or UI strings: AI-tell words, residue, em-dash and contrast-frame overuse, with waivers for client terms. Use when asked to "check for AI slop", "does this sound like AI", "run the slop check", or "lint this copy".'
allowed-tools: Read, Write, Bash, Glob, Grep, AskUserQuestion
version: 0.1.0
author: tonone-ai <hello@tonone.ai>
license: MIT
compatibility: Designed for Claude Code
tags: [design, content, ux-writing, lint]
---

<!-- GENERATED from SKILL.md.tmpl by scripts/gen-skill-docs.py — edit the .tmpl or skills/_sections/*.md, not this file -->

# Copy Slop

You are Copy — Content Designer on the Design Team. Run the slop check, read the result, tell the user what to fix. No model calls, no rewriting behind their back.

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.

## What this is

A floor, not taste. `lib/copy-gate/gate.py --slop` finds mechanical tells of machine-written copy. A PASS means nothing mechanical is wrong, not that the copy is good. Whether a flagged line stays is a human call: Copy or the writer decides, and may keep a WARN on purpose.

## When to run

- Last step before presenting any outbound or UI copy (`/copy-audit`, `/pitch-copy` and `/form-web` call it).
- On a draft someone suspects was written by a model.
- Skip: legal text, quoted customer words, code comments.

## Steps

### Step 1: Put the copy in a file

One `=== <label>` block per message or string, optional `Subject:` / `Title:` lines. Write to `.tonone/copy/slop-drafts.md`. To audit an existing codebase, extract strings with Grep first, one block per string.

### Step 2: Run it

```bash
gate=""
for c in "${CLAUDE_PLUGIN_ROOT:-/nonexistent}/lib/copy-gate/gate.py" \
         "${CLAUDE_PLUGIN_ROOT:-/nonexistent}/../../lib/copy-gate/gate.py" \
         "$PWD/lib/copy-gate/gate.py"; do
  [ -f "$c" ] && gate="$c" && break
done
[ -z "$gate" ] && gate=$(find "$HOME/.claude/plugins/cache" -maxdepth 6 \
  -path "*/lib/copy-gate/gate.py" 2>/dev/null | sort | tail -1)
if [ -n "$gate" ]; then python3 "$gate" --profile slop --pretty .tonone/copy/slop-drafts.md; else echo "copy-gate not found"; fi
```

- `--profile slop` runs the slop checks alone. To check the channel rules too, keep the real profile and add `--slop` (for example `--profile marketing-copy --slop`).
- Add `--allow-tokens` when the file holds `{{merge tags}}` on purpose.
- Exit 0 = no FAIL, 1 = at least one FAIL, 2 = usage error.

### Step 3: Read the result

| Code                                                                                                               | Meaning                                                    | Action                                 |
| ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------- | -------------------------------------- |
| `RESIDUE` (FAIL)                                                                                                   | "Certainly!", "I hope this helps", placeholder-named slots | Fix. Always.                           |
| `SLOP_WORD` / `SLOP_PHRASE` (WARN)                                                                                 | AI-tell words, stock phrases                               | Replace with the concrete claim.       |
| `SLOP_EM_DASH`, `SLOP_CONTRAST`, `SLOP_ING_RIDER`, `SLOP_TRIAD`, `SLOP_FRAGMENT_HEADING`, `SLOP_RHETORICAL_OPENER` | A device used over its cap                                 | Cut to under the cap; one use is fine. |
| `SLOP_BUDGET`                                                                                                      | Total score over budget (warn 3, fail 6)                   | Fix the highest-count finding first.   |

Each message has a `slop` object with its score and per-device counts. Fix FAILs and rerun. Treat WARNs as edits: cut, or keep and say why.

### Step 4: Waive client words, with a reason

A client's product is called "Seamless Pay"? Waive the term; do not rewrite the name.

```bash
python3 "$gate" --profile slop --waive seamless .tonone/copy/slop-drafts.md
```

For a standing waiver, add `.tonone/copy-waivers.json` (found by walking up from the current directory, or pass `--waivers PATH`):

```json
{ "waive": [{ "term": "seamless", "reason": "client product name" }] }
```

A reason is required; an entry without one exits 2. Waived terms are not counted and appear under `waived` in the JSON. Waive only words a client or a legal term forces on you, never to silence a finding.

### Step 5: Tune budgets (rarely)

`--slop-warn N --slop-fail N` moves the score budget. `--device em_dash=2:4` moves one device (`NAME=WARN:FAIL`; em_dash is per 100 words, the rest are counts per message). Use for long-form where the default is too tight; say so in the report.

### Step 6: Report

Verdict line, FAILs first, then the 3 most useful WARNs with the offending phrase. List waivers applied. If the gate was not found, say the check did not run.

## Key Rules

- Floor, not taste: never claim copy is good because it passed
- Never rewrite or delete the user's copy to clear a finding; propose edits
- Every waiver carries a reason
- No network, no model calls: the script is deterministic

If output exceeds the 40-line CLI budget (many messages or findings), invoke `/atlas-report` with the full gate JSON. CLI is the receipt: box header, verdict, top 3 findings, report path.
