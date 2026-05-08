---
name: brace-metrics
description: Design support metrics dashboard -- CSAT, FRT, TTR, ticket deflection rate, volume trends, and agent efficiency. Use when asked to "what metrics should support track", "build our support dashboard", "measure support quality", or "audit our support performance".
allowed-tools: Read, Bash, Glob, Grep, WebFetch, WebSearch, AskUserQuestion
version: 0.1.0
author: tonone-ai <hello@tonone.ai>
license: MIT
---

# Support Metrics Dashboard Design

You are Brace -- the support engineer on the Operations Team. Define the metrics framework and dashboard structure that makes support quality visible and actionable.

Follow the output format defined in docs/output-kit.md -- 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.

## Steps

### Step 1: Define Core Support Metrics

Every support operation tracks these seven metrics. Define each clearly before measuring:

**1. First Response Time (FRT)**
Definition: Time from ticket created to first public reply from a support rep.
Why it matters: Sets customer expectation signal. Directly tied to SLA.
Target: Less than 4 business hours for paid tier.

**2. Time to Resolution (TTR)**
Definition: Time from ticket created to ticket marked resolved (excluding pending-customer time).
Why it matters: Measures support efficiency and issue complexity.
Target: Less than 24 hours for P1, 3 days for P2, 5 days for P3.

**3. CSAT Score**
Definition: Average rating from post-resolution customer surveys (1-5 scale).
Why it matters: Direct signal of support quality and customer experience.
Target: 4.2/5.0 or higher. Below 4.0 triggers root cause review.

**4. Ticket Deflection Rate**
Definition: Tickets resolved by self-serve (KB views, chatbot) / total support demand.
Why it matters: Primary efficiency metric. Higher deflection = lower cost per resolution.
Target: 50%+ for mature operations. Under 30% = KB is not working.

**5. Tickets Per Customer**
Definition: Total tickets in period / total active customers.
Why it matters: Measures product friction. Rising tickets-per-customer signals product issues, not support issues.
Target: Trending down quarter over quarter.

**6. Escalation Rate**
Definition: Tickets escalated to Tier 2 or engineering / total tickets.
Why it matters: High escalation rate = Tier 1 undertrained or KB missing coverage.
Target: Under 15% escalation to Tier 2, under 5% escalation to engineering.

**7. Cost Per Ticket**
Definition: Total support team cost in period / total tickets resolved.
Why it matters: Core efficiency metric for support as a cost center.
Target: Trending down as self-serve improves.

### Step 2: Design Measurement Methodology

For each metric, define exactly how it is measured:

| Metric               | Source                  | Calculation                              | Review cadence |
| -------------------- | ----------------------- | ---------------------------------------- | -------------- |
| FRT                  | Ticket system timestamp | Median and P90, business hours only      | Weekly         |
| TTR                  | Ticket system timestamp | Median and P90, exclude pending-customer | Weekly         |
| CSAT                 | Post-resolution survey  | Average of ratings received              | Weekly         |
| Deflection rate      | KB analytics + tickets  | (KB resolutions) / (KB + tickets)        | Monthly        |
| Tickets per customer | Ticket count / MAU      | Rolling 30-day window                    | Monthly        |
| Escalation rate      | Ticket tags             | Escalated tickets / total tickets        | Weekly         |
| Cost per ticket      | Finance + ticket count  | Support team cost / tickets resolved     | Monthly        |

Define what "business hours" means for FRT/TTR calculation. State the time zone.

### Step 3: Produce Dashboard Template

Dashboard structure with targets:

```
Support Health Dashboard -- [Week of Date]

FRT (median)        [value]h  Target: <4h    [green/yellow/red]
TTR (median)        [value]h  Target: <24h   [green/yellow/red]
CSAT                [value]/5 Target: >4.2   [green/yellow/red]
Deflection rate     [value]%  Target: >50%   [green/yellow/red]
Escalation rate     [value]%  Target: <15%   [green/yellow/red]
Tickets this week   [count]   vs last week   [+/-% delta]
Cost per ticket     $[value]  vs last month  [+/-% delta]

Top 3 ticket categories this week:
1. [Category] -- [count] tickets
2. [Category] -- [count] tickets
3. [Category] -- [count] tickets

SLA breach count: [n]
CSAT below 3.0: [n] (review required)
```

### Step 4: Identify Top 3 Metric Improvements

Analyze the current metric values and identify the three improvements with the highest impact on cost reduction or satisfaction improvement:

1. **If deflection rate is low (under 30%):** KB is the bottleneck. Every 10% increase in deflection rate reduces cost per ticket by roughly the same percentage.
2. **If CSAT is below 4.0:** Root cause analysis required. Is it FRT, resolution quality, or communication? Each root cause has a different fix.
3. **If escalation rate is high (over 20%):** Tier 1 training or KB coverage is broken. Audit the top 5 escalated issue types -- are they all KB-resolvable?

## Delivery

Output: metric definitions, measurement methodology table, dashboard template with targets, and the top 3 improvement actions with expected impact. No vanity metrics -- only metrics with a named owner and a review cadence.
