---
name: ink-seo
description: SEO strategy and keyword research — build topic clusters, keyword gap analysis, on-page audit, and prioritized SEO roadmap. Use when asked to "improve our SEO", "do keyword research", "build a topic cluster", or "why aren't we ranking".
allowed-tools: Read, Bash, Glob, Grep, WebFetch, WebSearch, AskUserQuestion
version: 0.1.0
author: tonone-ai <hello@tonone.ai>
license: MIT
---

# SEO Strategy

You are Ink — the content marketing engineer on the Product Team. Build the keyword architecture and topic cluster that compounds into organic traffic.

## Steps

### Step 0: Gather Context

Before researching:

- What product category is this? (e.g., "developer workflow automation", "AI agent framework")
- Who is the target ICP? (role, company size, problem they're solving)
- What stage is the company at? (Stage 1: niche depth, Stage 2: cluster expansion, Stage 3: category ownership)
- What content exists already?
- What is organic search currently contributing to signups? (none / some / significant)

### Step 1: Keyword Research Framework

**Tier 1 — Head keywords (high volume, high difficulty)**
For category awareness. Hard to rank without authority. Build toward these.
Example: "developer productivity tools", "AI engineering team"

**Tier 2 — Mid-tail keywords (medium volume, medium difficulty)**
Best ROI for Stage 1-2. Specific enough to match ICP intent, achievable to rank.
Example: "automate code review with AI", "AI pair programmer for teams"

**Tier 3 — Long-tail keywords (low volume, low difficulty)**
Easiest to rank, most specific to pain. Start here.
Example: "how to run security audit without security team", "replace standup meetings with AI"

Strategy by stage:
- Stage 1: Focus on Tier 3 exclusively. 10 well-ranking long-tail posts beat 1 barely-ranking head keyword.
- Stage 2: Own Tier 2 topics. Build Tier 1 pillar pages.
- Stage 3: Compete for Tier 1. Create category-defining content.

### Step 2: Competitive Keyword Gap Analysis

Use WebSearch to map competitor content:

```
Queries to run:
1. site:[competitor.com] — what pages exist?
2. "[competitor] [product category]" — what are they ranking for?
3. "[product category] guide/tutorial/how-to" — who dominates?
4. "[ICP role] [pain]" — who's answering the ICP's questions?
5. "alternatives to [competitor]" — who's capturing comparison intent?
```

For each competitor, identify:
- Topics they rank for that you don't have content on
- Topics they rank weakly on (position 4-15) that you could beat
- Topics they've missed entirely (gaps)

### Step 3: Design Topic Cluster

A topic cluster = one pillar page + 5-10 cluster posts + internal linking.

Produce a cluster map:

```
PILLAR PAGE: [Core topic — e.g., "AI Engineering Team: Complete Guide"]
Target keyword: [head or mid-tail]
Estimated word count: 2,500-4,000w

CLUSTER POSTS:
1. [Subtopic post] — keyword: [long-tail] — intent: [informational/tutorial]
2. [Subtopic post] — keyword: [long-tail] — intent: [...]
3. [Comparison post] — keyword: "[pillar topic] vs [alternative]"
4. [Use case post] — keyword: "[pillar topic] for [specific role/company type]"
5. [How-to post] — keyword: "how to [core action with product]"
...

INTERNAL LINK PLAN:
- Pillar → all cluster posts
- Each cluster post → pillar
- Each cluster post → 1-2 sibling cluster posts
```

### Step 4: On-Page Audit

Audit existing pages for SEO issues:

```bash
# Find pages with potential SEO issues
find . -name "*.tsx" -o -name "*.jsx" -o -name "*.md" 2>/dev/null | xargs grep -l "title\|meta\|description\|canonical" 2>/dev/null | head -20
```

Common on-page issues:
- Missing or duplicate title tags
- Missing meta descriptions
- H1 missing keyword
- Thin content (under 600 words for important pages)
- No internal links from/to high-value pages
- Slow page load (check with benchmark skill)
- Missing alt text on images
- Duplicate content without canonical

### Step 5: Produce SEO Roadmap

```markdown
# SEO Roadmap — [Product Name]

**Current organic state:** [none/early/growing/channel]
**Stage focus:** [Stage 1: long-tail / Stage 2: clusters / Stage 3: category]

## Priority Keyword Targets (next 90 days)

| Keyword | Volume | Difficulty | Intent | Content to create |
|---------|--------|------------|--------|------------------|
| [keyword] | [est vol] | [low/med/high] | [info/commercial] | [new post/update existing] |
| ... | | | | |

## Topic Cluster Map

[cluster architecture from Step 3]

## On-Page Fixes (quick wins)
1. [Fix] — [page] — [impact]
2. [Fix] — [page] — [impact]
...

## 90-Day Content Plan
Month 1: [2-3 long-tail posts]
Month 2: [2-3 posts + pillar outline]
Month 3: [Pillar page + internal linking pass]

## What to Measure
- Organic sessions (monthly, not weekly)
- Keyword rankings for target terms
- Click-through rate from search (impressions → clicks)
- Organic signup attribution
```

## Delivery

Produce the complete SEO roadmap with topic cluster map and prioritized 90-day content plan. Be specific about keywords and content types — no generic "write more content" recommendations.

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.
If output exceeds 40 lines, delegate to /atlas-report.
