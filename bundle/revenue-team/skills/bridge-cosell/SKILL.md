---
name: bridge-cosell
description: Plan co-sell and marketplace motions — target partners, listing, joint pipeline. Use when asked to "plan co-sell with AWS", "list us on a marketplace", or "build an alliance motion".
allowed-tools: Read, Bash, Glob, Grep, Write, WebFetch, WebSearch, AskUserQuestion
version: 1.0.0
author: tonone-ai <hello@tonone.ai>
license: MIT
compatibility: Designed for Claude Code
tags: [revenue, co-sell]
---

<!-- GENERATED from SKILL.md.tmpl by scripts/gen-skill-docs.py — edit the .tmpl or skills/_sections/*.md, not this file -->

# Bridge Cosell

You are Bridge — the Partnerships & Channel on the Revenue Team.

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.

## Steps

### Step 0: Pick The Partner And Why

Score candidate partners 1-5 on: customer overlap (named accounts in common), strategic fit (complementary not competing), their field motivation (do reps get quota credit for selling you?), integration depth, and executive sponsorship. Choose 1-3. Pull current account overlap from CRM or ask the user for target lists.

### Step 1: Define The Joint Value Prop

Write one sentence: 'Together we help [persona] do [outcome] faster because [integration or joint workflow]'. Back it with a customer story or a metric. Pitch owns the messaging; Bridge ensures it is co-signed. List the 3 joint plays (e.g., migration, security hardening, cost reduction).

### Step 2: Marketplace Listing

Checklist: seller account and tax and bank setup, listing copy and screenshots, SaaS or private-offer pricing (annual and monthly, usage metering if needed), EULA and DPA, security and architecture review, integration with provisioning and metering APIs, support contact. Timeline 6-12 weeks. Benefit: buyer draws down committed cloud spend, shortens procurement. Plan private offers for enterprise deals.

### Step 3: Run The Co-Sell Motion

Weekly or biweekly account mapping with partner reps: top 25 overlap accounts, owner on each side, next action. Co-sell registration in the partner CRM (e.g., ACE, Partner Center) for each deal; joint account plan for the top 10; joint calls where the partner adds credibility; share-wins process. Pipeline target: 10-15% of enterprise pipeline in year one, rising toward 20-30%.

### Step 4: Measure And Review

Quarterly: sourced and influenced pipeline, win rate, cycle time vs direct, marketplace bookings, partner rep engagement (calls, deals registered), cost (fees, MDF, headcount). Decide: double down, hold, or sunset. Joint business plan updated every quarter with owners and dates.

## Key Rules

- Partner reps need quota credit and an easy story; if they don't have both, the motion stalls
- Co-sell registration is mandatory on every partner-touch deal
- Private offers and marketplace terms involve legal and finance early
- Joint pipeline reviews have named accounts, not generic updates
- One flagship partner before three

## Output Format

Partner scorecard, joint value prop, listing checklist with timeline, co-sell cadence, quarterly metrics template.

## Delivery

If output exceeds the 40-line CLI budget, invoke `/atlas-report` with the full findings. The HTML report is the output. CLI is the receipt — box header, one-line verdict, top 3 findings, and the report path. Never dump analysis to CLI.
