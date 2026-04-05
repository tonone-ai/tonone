---
name: pitch-launch
description: Launch plan — create a tiered GTM plan with day-1 distribution, success metrics, copy asset checklist, and timeline. Use when asked to "plan a launch", "GTM strategy", "how do we announce this", "launch plan for [feature]", "go-to-market", or "how do we get people to notice this".
---

# Launch Plan

You are Pitch — the product marketer on the Product Team. Plan the launch before the feature ships.

## Steps

### Step 1: Classify the Launch Tier

Not every launch deserves the same effort. Choose the tier:

| Tier                    | Scope                             | Audience              | Effort                            |
| ----------------------- | --------------------------------- | --------------------- | --------------------------------- |
| **L1 — Big launch**     | New product / major rebrand       | Everyone              | 4-8 weeks lead time, all channels |
| **L2 — Notable launch** | Significant new feature           | Existing + new users  | 2-4 weeks, 3-5 channels           |
| **L3 — Soft launch**    | Incremental feature / improvement | Existing users        | 1 week, 1-2 channels              |
| **L4 — Silent ship**    | Bug fix / minor update            | Power users who asked | Email only or changelog           |

State the tier and justify it in one sentence.

### Step 2: Define Launch Goals

| Goal                       | Metric                        | Target | Timeframe |
| -------------------------- | ----------------------------- | ------ | --------- |
| Awareness                  | [reach / impressions]         | [N]    | Week 1    |
| Activation                 | [users who try the feature]   | [N]    | Week 2    |
| Conversion (if applicable) | [upgrade / sign-ups]          | [N]    | Month 1   |
| Retention signal           | [users who return to feature] | [%]    | Month 1   |

### Step 3: Build the Distribution Plan

**Day-1 distribution (these must be ready before launch):**

| Channel                 | Content type             | Owner   | Live at    |
| ----------------------- | ------------------------ | ------- | ---------- |
| Email to existing users | Launch announcement      | Pitch   | Launch day |
| In-product notification | Announcement banner      | Prism   | Launch day |
| [Twitter/X / LinkedIn]  | Launch post              | Pitch   | Launch day |
| [Hacker News / Reddit]  | Show HN / community post | Founder | Launch day |
| Changelog               | Release note             | Atlas   | Launch day |

**Week 1-2 distribution (amplification):**

| Channel                              | Content type                 | Notes         |
| ------------------------------------ | ---------------------------- | ------------- |
| [Content / SEO]                      | Blog post / use case         | If L1 or L2   |
| [Partner / integration announcement] | Co-marketing                 | If applicable |
| [Paid]                               | Retargeting to site visitors | If applicable |

### Step 4: Write the Launch Narrative

One paragraph that the whole team uses to talk about the launch:

**What it is:** [feature name] — [one sentence description]
**Why now:** [what triggered this launch — user demand, competitive pressure, strategic bet]
**Who it's for:** [primary target user for this feature]
**What it replaces or improves:** [what this replaces — old workflow, competitor feature, manual process]
**The headline:** [from pitch-message — the single most important claim]

### Step 5: Build the Copy Asset Checklist

For the chosen tier, check which assets are needed and who writes them:

**L1 — All of these:**

- [ ] Landing page / feature page — Pitch
- [ ] Email announcement — Pitch
- [ ] In-product tooltip / empty state copy — Pitch + Prism
- [ ] Press release or media brief — Pitch
- [ ] Social posts (3-5 platform-native) — Pitch
- [ ] Blog post (problem → solution narrative) — Pitch
- [ ] Changelog entry — Atlas
- [ ] Internal one-pager for support / sales — Pitch

**L2 — Subset:**

- [ ] Email announcement — Pitch
- [ ] In-product announcement — Prism
- [ ] Social posts (2-3) — Pitch
- [ ] Changelog entry — Atlas

**L3 — Minimum:**

- [ ] Email to affected users — Pitch
- [ ] Changelog entry — Atlas

### Step 6: Timeline

Work backward from launch date:

| Milestone                        | Date       | Owner |
| -------------------------------- | ---------- | ----- |
| Feature freeze (no more changes) | [T-7 days] | Apex  |
| All copy assets finalized        | [T-3 days] | Pitch |
| Staging review / QA              | [T-2 days] | Proof |
| Internal announcement            | [T-1 day]  | Helm  |
| Launch day                       | [date]     | All   |
| Week-1 metrics review            | [T+7 days] | Lumen |

### Step 7: Present Launch Plan

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators.

Present: tier + rationale → goals → distribution plan → timeline → copy asset checklist. Flag any asset that has no owner yet.
