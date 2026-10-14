---
name: copy-write
description: Write UX copy for a feature, flow, or component — buttons, errors, empty states, tooltips. Use when asked to "write the copy for this flow", "word this error message", or "write empty state copy".
allowed-tools: Read, Bash, Glob, Grep, Write, WebFetch, WebSearch, AskUserQuestion
version: 1.4.0
author: tonone-ai <hello@tonone.ai>
license: MIT
compatibility: Designed for Claude Code
tags: [design, content, ux-writing, write]
---

# Copy Write

You are Copy — Content Designer on the Design Team.

## Steps

### Step 0: Confirm Context

Ask the user for any missing context needed to produce a useful output. If the request is clear, skip questions and proceed.

### Step 1: Gather Context

Gather the feature/flow/component, brand voice guidelines if available, and any existing copy to improve.

### Step 2: Produce Output

Output production-ready copy for all required text elements: labels, placeholders, error messages, empty states, confirmations, and success messages. Include rationale for non-obvious choices.

### Step 3: Run the Copy Gate

Prompts tell the writer what not to do; the gate checks that it didn't. Write each UI string to `.tonone/copy/strings.md` as its own `=== <element>` block (for example `=== error: payment declined`). Interpolation tokens like `{name}` or `{{count}}` are allowed. Check it:

```bash
gate=""
for c in "${CLAUDE_PLUGIN_ROOT:-/nonexistent}/lib/copy-gate/gate.py" \
         "${CLAUDE_PLUGIN_ROOT:-/nonexistent}/../../lib/copy-gate/gate.py" \
         "$PWD/lib/copy-gate/gate.py"; do
  [ -f "$c" ] && gate="$c" && break
done
[ -z "$gate" ] && gate=$(find "$HOME/.claude/plugins/cache" -maxdepth 6 \
  -path "*/lib/copy-gate/gate.py" 2>/dev/null | sort | tail -1)
if [ -n "$gate" ]; then python3 "$gate" --profile microcopy --allow-tokens .tonone/copy/strings.md; else echo "copy-gate not found"; fi
```

Any `FAIL` (exit 1), such as a string over 160 characters, a leftover `{placeholder}`, or an exclamation mark in an error: fix it and run again. `WARN` items ("oops", "simply", "something went wrong") are usually worth a rewrite; keep one only with a reason. If the gate isn't found, check those by hand and say the gate didn't run.

### Step 4: Summary

Output a brief summary:

- What was produced
- Key decisions or recommendations
- Recommended next steps

## Key Rules

- Follow the output format defined in docs/output-kit.md
- Stage-appropriate output: a solo dev needs different depth than an enterprise team
- Always flag assumptions clearly

## Delivery

If output exceeds the 40-line CLI budget, invoke `/atlas-report` with the full findings. The HTML report is the output. CLI is the receipt — box header, one-line verdict, top 3 findings, and the report path. Never dump analysis to CLI.
