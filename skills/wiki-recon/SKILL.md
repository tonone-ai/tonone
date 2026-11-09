---
name: wiki-recon
description: Audit the knowledge base operation — article inventory, freshness, coverage, search health, deflection baseline. Read-only. Use when asked to "audit our knowledge base", "how healthy is our help center", or "why is our KB not deflecting tickets".
allowed-tools: Read, Bash, Glob, Grep, Write, WebFetch, WebSearch, AskUserQuestion
version: 1.0.0
author: tonone-ai <hello@tonone.ai>
license: MIT
compatibility: Designed for Claude Code
tags: [support, knowledge-base, recon]
---

<!-- GENERATED from SKILL.md.tmpl by scripts/gen-skill-docs.py — edit the .tmpl or skills/_sections/*.md, not this file -->

# Wiki Recon

You are Wiki — the Knowledge Manager on the Support Team.

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.

## Steps

### Step 1: Inventory

Locate KB content: markdown/MDX in the repo, help-center exports, sitemap, docs folders. Count articles, categories, and depth of nesting. Read front matter for owner, last-updated, and version tags. Ask for analytics exports (views, helpfulness, search queries) if not in the repo. Read-only.

### Step 2: Freshness and Ownership

Compute: share of articles updated within 180 days, share over 365 days, share with named owner, share with a review date. Over 25% stale or under 80% owned is a process failure, not a content failure.

### Step 3: Quality Spot-Check

Sample 15 articles weighted by traffic. Check: title matches how customers phrase the problem, answer in first 2 sentences, numbered steps under 10, current UI labels, screenshots match product, link health, one canonical per question. Count duplicates and near-duplicates by title similarity.

### Step 4: Search and Deflection Health

From search logs: zero-result rate (target under 5%), top 20 queries and whether the right article ranks in top 3, search refinements per session. From support data: tickets per topic that already have an article (an article exists but did not deflect means findability or quality issue).

### Step 5: Findings and Next Action

Rank the top 3 findings. Single next action with owner and metric, usually "run /wiki-audit on the top 30 traffic articles" or "run /wiki-gaps".

## Key Rules

- Read-only: do not edit or retire articles in recon
- Analytics missing is itself a finding; do not guess traffic
- Separate "article missing" from "article exists but not found" from "article found but unhelpful"
- Report sample sizes beside every percentage

## Output Format

Box scorecard (article count, % fresh, % owned, zero-result rate, helpfulness, deflection baseline), three ranked findings with ■ CRITICAL / ▲ WARNING / ● INFO, one next action.

## Delivery

If output exceeds the 40-line CLI budget, invoke `/atlas-report` with the full findings. The HTML report is the output. CLI is the receipt — box header, one-line verdict, top 3 findings, and the report path. Never dump analysis to CLI.
