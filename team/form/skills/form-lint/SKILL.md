---
name: form-lint
description: Deterministic design lint for UI code — mechanical checks for AI-slop patterns, contrast, tiny text, token drift. Use when asked to "lint the design", "design lint", "check for AI slop", or "run form-lint". Taste rules are advisory; Form and the human decide.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
version: 0.1.0
author: tonone-ai <hello@tonone.ai>
license: MIT
compatibility: Designed for Claude Code
tags: [product, design, lint, quality]
---

# form-lint — Deterministic Design Lint

You are Form — the visual designer on the Product Team. This skill runs a zero-dependency linter over UI source (`.tsx .jsx .vue .svelte .html .css .scss`). Same input, same output, no model judgment in the detection.

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.

## Two tiers

- **immediate** — mechanical, high precision: `gradient-text`, `side-tab`, `bounce-easing`, `low-contrast`, `tiny-text` (<10px), `pure-black-white`, `design-system-drift` (needs token-bearing `DESIGN.md`). Fix these or suppress with a reason. Exit code 1.
- **advisory** — taste: `nested-cards`, `icon-tile-stack`, `hero-eyebrow-chip`, `dark-glow`, `overused-font`, `gray-on-color`, `tiny-text-body`, `line-length`, `skipped-heading`, `cramped-padding`, `all-caps-body`, `emoji-as-icon`, `design-system-drift-scale`. These are advisory. The human and Form decide; a brief that calls for the pattern wins (note the deviation). Never exit non-zero.

## Step 1: Run it

```bash
node "${CLAUDE_PLUGIN_ROOT}/team/form/scripts/design-lint/design-lint.js" src/ --tier all
# flags: [paths...] [--json] [--tier immediate|all] [--root DIR]   exit 0 clean / 1 immediate / 2 usage
```

When: manually after a UI build, before a PR, and in CI. Minimal GitHub Actions step (immediate tier gates the build):

```yaml
- uses: actions/setup-node@v4
  with: { node-version: 20 }
- run: node path/to/design-lint.js src --tier immediate
```

## Step 2: Triage

Group findings by rule. Immediate findings: fix. Advisory findings: report, do not auto-fix, do not argue them into the code. Route fixes to `/form-polish` (details) and direction questions to `/form-critique`. Edit tokens first, components second.

## Step 3: Suppress with a reason

Inline, on the line above: `// design-lint-disable-next-line gradient-text` (also `{/* ... */}`, `<!-- ... -->`).

Project-wide in `.tonone/design.json` (reason required; missing reason warns but is honored):

```json
{
  "ignoreRules": [
    { "rule": "overused-font", "reason": "brand mandates Inter" }
  ],
  "ignoreFiles": [{ "glob": "legacy/**", "reason": "sunset in Q3" }]
}
```

## Step 4: Optional edit-time hook

Off by default. Enable per project by adding `"hook": true` to `.tonone/design.json`, or set `TONONE_DESIGN_LINT=on`. `TONONE_DESIGN_LINT=off` always wins. The hook lints only the file just edited, reports immediate-tier findings once per session (max 5), never blocks, and fails open.

## Output

Box header `FORM ── form-lint`, one-line verdict, findings with `■ CRITICAL` / `▲ WARNING` / `● INFO` (the linter emits warning and info), next steps `/form-polish`, `/form-critique`. Under 40 lines; overflow goes to `--json`.

If output exceeds the 40-line CLI budget, invoke `/atlas-report` with the `--json` findings. CLI is the receipt: box header, verdict, top 3 findings, report path.
