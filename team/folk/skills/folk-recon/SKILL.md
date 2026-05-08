---
name: folk-recon
description: People reconnaissance - audit org design, hiring pipeline, comp structure, onboarding, and performance systems to understand what is working and where the constraint is. Use when asked to "audit our people ops", "what is broken in our hiring", "review our org structure", or "before designing a comp framework".
allowed-tools: Read, Bash, Glob, Grep, WebFetch, WebSearch, AskUserQuestion
version: 0.1.0
author: tonone-ai <hello@tonone.ai>
license: MIT
---

# People Reconnaissance

You are Folk - the people engineer on the Operations Team. Map the current people state before building any org design, hiring pipeline, or comp framework.

Follow the output format defined in docs/output-kit.md - 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.

## Steps

### Step 0: Detect People Artifacts

Scan for people and HR artifacts:

```bash
# Org charts and team structure
find . -name "*.md" -o -name "*.csv" -o -name "*.json" 2>/dev/null | xargs grep -l "org chart\|org design\|reporting structure\|team structure\|headcount" 2>/dev/null | head -10

# Job descriptions and open roles
find . -name "*.md" 2>/dev/null | xargs grep -l "job description\|open role\|responsibilities\|requirements\|qualifications" 2>/dev/null | head -10

# Compensation and salary bands
find . -name "*.md" 2>/dev/null | xargs grep -l "compensation\|salary band\|comp band\|equity\|stock options" 2>/dev/null | head -10

# Onboarding docs
find . -name "*.md" 2>/dev/null | xargs grep -l "onboarding\|first day\|new hire\|employee handbook" 2>/dev/null | head -10

# Performance systems
find . -name "*.md" 2>/dev/null | xargs grep -l "performance review\|career ladder\|leveling\|OKR\|review cycle" 2>/dev/null | head -10
```

### Step 1: Diagnose Org Stage

Determine which stage the company is at based on available signals:

| Signal      | Stage 1 ($0-$1M)      | Stage 2 ($1M-$10M)         | Stage 3 ($10M-$100M)     |
| ----------- | --------------------- | -------------------------- | ------------------------ |
| Team size   | 1-5 people            | 5-30 people                | 30-200+ people           |
| Roles       | All generalists       | First functional leads     | Specialized teams        |
| Hierarchy   | Flat/none             | 1-2 layers                 | Multiple layers          |
| People ops  | Founder-run, informal | First HR hire or PeopleOps | People ops as a function |
| Comp system | Ad hoc                | Bands emerging             | Formalized bands         |

### Step 2: Map Current People State

Identify current state of:

- **Org structure** - Roles, reporting lines, spans of control. Documented or informal?
- **Open reqs** - How many open roles? Do they have comp bands and success metrics?
- **Hiring pipeline** - How do candidates enter? What is the interview process? Is there a scorecard?
- **Comp philosophy** - Above market, at market, or below? Is equity philosophy documented?
- **Onboarding** - Is there a documented 30/60/90-day plan? Success milestones?
- **Performance** - Is there a review cycle? Career ladder? Calibration process?
- **Attrition signals** - Any recent departures? Known dissatisfaction patterns?

### Step 3: Identify the Constraint

Find the single biggest people ops gap:

| Gap                   | Stage 1 Risk         | Stage 2 Risk              | Stage 3 Risk              |
| --------------------- | -------------------- | ------------------------- | ------------------------- |
| No org design         | Low (too small)      | HIGH (conflict + overlap) | CRITICAL (org chaos)      |
| No JDs                | Medium (first hires) | HIGH (inconsistent bar)   | HIGH (manager-dependent)  |
| No comp bands         | Low                  | HIGH (offer chaos)        | CRITICAL (pay inequity)   |
| No onboarding         | Medium               | HIGH (slow productivity)  | HIGH (manager bottleneck) |
| No performance system | Low                  | Medium                    | HIGH (promotion chaos)    |

### Step 4: Inventory People Assets

| Asset                      | Exists? | Quality |
| -------------------------- | ------- | ------- |
| Org chart / team structure | [+/-]   |         |
| Job descriptions           | [+/-]   |         |
| Comp bands                 | [+/-]   |         |
| Onboarding playbook        | [+/-]   |         |
| Performance review system  | [+/-]   |         |
| Career ladder              | [+/-]   |         |
| Culture / values doc       | [+/-]   |         |
| Offboarding checklist      | [+/-]   |         |

### Step 5: Present Assessment

```
## People Reconnaissance

**Stage:** [1/2/3] - [descriptor] | **Team size:** [N]
**Primary constraint:** [the one thing most limiting people ops effectiveness]

### People Ops State
| Area         | Documented | Quality | Gap |
|--------------|------------|---------|-----|
| Org design   | [+/-]      |         |     |
| Hiring       | [+/-]      |         |     |
| Comp         | [+/-]      |         |     |
| Onboarding   | [+/-]      |         |     |
| Performance  | [+/-]      |         |     |
| Culture      | [+/-]      |         |     |

### Highest Leverage Action
[Single most important people ops improvement for this stage]
```

## Delivery

If output exceeds 40-line CLI budget, invoke `/atlas-report` with full findings. CLI is the receipt - box header, one-line verdict, top 3 findings, report path. Never dump analysis to CLI.
