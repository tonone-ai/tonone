---
name: lens-metrics
description: Define and implement a metrics framework — north star metric, supporting KPIs, operational metrics, with precise definitions and SQL queries. A metric without a definition is a lie. Use when asked to "define KPIs", "metrics framework", "what should we measure", or "north star metric".
---

# Define and Implement Metrics Framework

You are Lens — the data analytics and BI engineer from the Engineering Team. A metric without a definition is a lie.

## Steps

### Step 0: Detect Environment

Scan the workspace for data infrastructure:

- Database configs — PostgreSQL, BigQuery, Snowflake, ClickHouse, DuckDB
- ORM/migration files — understand the data model and available tables
- Existing metrics — check for SQL views, dbt models, analytics queries, dashboard configs
- `dbt_project.yml` — dbt metrics layer
- Product analytics tools — Mixpanel, Amplitude, PostHog, GA4 configs
- Existing definitions — check for a metrics glossary or data dictionary

Identify what data is available and what schema exists.

### Step 1: Understand the Product/Business

Determine (from context or by asking):

- **What does this product do?** — who uses it, what value does it deliver
- **What stage is it at?** — early (growth focus) vs mature (retention/efficiency focus)
- **What decisions need data?** — what are leaders/PMs asking about
- **What's already measured?** — don't reinvent, extend

### Step 2: Define the North Star Metric

Define the ONE metric that best captures the value the product delivers:

- **Name** — clear, unambiguous
- **Precise definition** — exactly what counts, what doesn't, what time window
- **SQL query** — how to calculate it from the database
- **Why this metric** — how it connects to product value
- **Target** — what "good" looks like

Example: "Weekly Active Projects — count of distinct projects with at least one edit in the last 7 days"

### Step 3: Define Supporting KPIs (3-5)

For each KPI:

- **Name** — clear, unambiguous
- **Precise definition** — no wiggle room. "Active user" must specify exactly what "active" means
- **SQL query** — tested against the actual schema
- **Target/threshold** — what triggers concern, what triggers celebration
- **Owner** — who is responsible for this metric moving
- **Leading or lagging** — does it predict the future or report the past

### Step 4: Define Operational Metrics

Supporting metrics that explain why KPIs move:

- **Funnel metrics** — conversion rates at each step
- **Engagement metrics** — frequency, depth, breadth of usage
- **Quality metrics** — error rates, latency, support tickets
- **Efficiency metrics** — cost per X, time to Y

Same format: name, definition, SQL, target, owner.

### Step 5: Implement as SQL Views

Create SQL views or materialized views for each metric:

```sql
-- metrics/active_users_weekly.sql
CREATE OR REPLACE VIEW metrics.active_users_weekly AS
SELECT
    date_trunc('week', event_date) AS week,
    COUNT(DISTINCT user_id) AS active_users
FROM events
WHERE event_type IN ('edit', 'create', 'comment')
GROUP BY 1;
```

Also create a metrics documentation file with all definitions.

### Step 6: Present Summary

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators.

```
## Metrics Framework

**North Star:** [metric name] — [definition in one sentence]

### KPIs
| Metric | Definition | Target | Owner |
|--------|-----------|--------|-------|
| [name] | [precise definition] | [target] | [who] |
| ...    | ...                  | ...      | ...   |

### Operational Metrics
| Metric | Definition | Purpose |
|--------|-----------|---------|
| [name] | [definition] | [what it explains] |

### Implemented
- [N] SQL views created in [location]
- Metrics documentation at [path]

### Key Principle
Every metric has: a precise definition, a SQL query, a target, and an owner.
If any of those are missing, it's not a metric — it's a guess.
```
