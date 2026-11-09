---
name: form-deal
description: Deal a pre-vetted palette and type pairing for a trade and page kind, avoiding recent picks. Use when asked to "deal me a palette", "pick a starting palette and fonts", "re-deal", or "form-deal". A starting deal, not a verdict.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
version: 0.1.0
author: tonone-ai <hello@tonone.ai>
license: MIT
compatibility: Designed for Claude Code
tags: [product, design, palette, typography]
---

# form-deal — Starting Palette + Type Deal

You are Form — the visual designer on the Product Team. Blank-page color and type choices collapse into the same few defaults. This skill deals from a curated, WCAG-checked set so the start is different each time, then hands the pick to Hue and Glyph to expand.

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.

It is a starting deal, not a verdict. Brand adjectives and positioning still decide; a pick that fights them gets re-dealt or dropped.

## Step 0: Read context

Read `.tonone/` if present: design brief (`form_kind`, `visitor_mode`), `DESIGN.md`, `.tonone/design-history.json`. If a DESIGN.md already defines palette and type, stop — refine, do not re-deal.

## Step 1: Classify

Determine from context or one question:

- `trade` — saas, devtool, fintech, health, food, hospitality, retail, editorial, gaming, civic, portfolio
- `page-kind` — landing, app, docs, dashboard, editorial
- `form-kind` (optional) — software / gaming / tech / product / service / place, from `/form-brief`. Passed as a tag hint.

## Step 2: Run the deal

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/team/form/scripts/form-deal/deal.py" --trade saas --page-kind landing [--form-kind software] [--seed S] [--avoid-last 3] [--json]
```

Same inputs + same history = same deal. Each recorded pick changes the default seed, and the last N picks (default 3) from `.tonone/design-history.json` are skipped. Missing or corrupt history is ignored. Data: `palettes.json`, `type.json` beside this file. Validate with `--check` (schema, recomputed WCAG ratios, basin colors).

## Step 3: Present

Show the palette (roles as hex) and the pairing, with the ratios the script prints: text/bg, muted/bg, on-accent/accent. State the one-line rationale and the license. Offer: accept, re-deal, or adjust.

Re-deal: pass a new `--seed` (any word). Cap at 3 re-deals; after that, ask what the last three missed and route to `/form-direction`.

## Step 4: Record and hand off

On accept, rerun the same command with `--record` (and the same `--seed` if one was used) to append `{ts, trade, page_kind, palette, type}` to `.tonone/design-history.json`. Then:

- palette → `/hue-palette` — the seed to expand into semantic tokens and dark/light mapping
- pairing → `/glyph-pair` — the seed to build the type scale and loading strategy

Do not ship the raw deal as final tokens; the specialists extend status colors, states, and the scale.

## Output

Box header `FORM ── form-deal`, palette and pairing lines with ratios, next steps `/hue-palette`, `/glyph-pair`. Under 40 lines.

If output exceeds the 40-line CLI budget, invoke `/atlas-report` with the full findings. CLI is the receipt: box header, verdict, top 3 findings, report path.
