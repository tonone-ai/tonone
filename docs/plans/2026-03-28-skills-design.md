# Skills Design — Engineering Team

63 skills across 13 agents. Every skill is tools-only (no Python scripts needed) — the agent uses Bash, Read, Grep, Write to do real work. Skills are workflows, not wrappers.

## Skill Pattern

Every skill follows this structure:

```markdown
---
name: {agent}-{action}
description: {when to trigger this skill}
---

# {Title}

You are {Agent} from the Engineering Team.

## Step 0: Detect Environment

Read the project to identify the stack. Adapt all subsequent steps.

## Steps

1. ...
2. ...
3. ...
```

## Full Roster

### Apex (Lead) — 4 skills

| Skill            | Description                                                                                    |
| ---------------- | ---------------------------------------------------------------------------------------------- |
| `/apex-plan`     | Discovery → challenge assumptions → present S/M/L options with token/cost estimates → dispatch |
| `/apex-review`   | Cross-cutting review of recent work — catches gaps between specialists                         |
| `/apex-status`   | CTO-level project status from git + codebase state                                             |
| `/apex-takeover` | System takeover — parallel recon across all specialists, phased deep dive, unified report      |

### Forge (Infrastructure) — 6 skills

| Skill             | Description                                                                             |
| ----------------- | --------------------------------------------------------------------------------------- |
| `/forge-infra`    | Build infrastructure from scratch — IaC with networking, IAM, secrets, monitoring hooks |
| `/forge-network`  | Design and build networking — VPCs, subnets, firewall rules, load balancers, DNS        |
| `/forge-audit`    | Audit existing infra for cost waste, security gaps, missing tags, over-provisioning     |
| `/forge-cost`     | Estimate monthly cost, flag top savings opportunities                                   |
| `/forge-diagnose` | Diagnose runtime infra issues — cold starts, undersized instances, network latency      |
| `/forge-recon`    | Inventory all infrastructure in a takeover — resources, costs, topology                 |

### Relay (DevOps) — 5 skills

| Skill             | Description                                                                               |
| ----------------- | ----------------------------------------------------------------------------------------- |
| `/relay-pipeline` | Build full CI/CD pipeline from scratch — build, test, deploy with caching and secrets     |
| `/relay-docker`   | Build production Dockerfiles — multi-stage, minimal base, security hardened, plus compose |
| `/relay-deploy`   | Set up deployment strategy — blue-green, canary, or rolling with rollback plan            |
| `/relay-audit`    | Audit existing pipeline — bottlenecks, security, caching, environment drift               |
| `/relay-recon`    | Map deployment pipeline in a takeover — how code reaches production                       |

### Spine (Backend) — 6 skills

| Skill            | Description                                                                                  |
| ---------------- | -------------------------------------------------------------------------------------------- |
| `/spine-api`     | Design and build an API — contract-first, OpenAPI spec, routes, validation, auth, pagination |
| `/spine-service` | Build a new service from scratch — project structure, config, DB, health checks, logging     |
| `/spine-design`  | System design — components, data flow, failure modes, scaling strategy                       |
| `/spine-perf`    | Find and fix performance bottlenecks — N+1s, missing indexes, sync issues, caching           |
| `/spine-review`  | API and code review — conventions, auth, error handling, rate limiting, test coverage        |
| `/spine-recon`   | Codebase survey in a takeover — architecture, tech debt, dependencies, test coverage         |

### Flux (Data) — 6 skills

| Skill            | Description                                                                               |
| ---------------- | ----------------------------------------------------------------------------------------- |
| `/flux-schema`   | Design and build a database schema — normalization, indexes, constraints, migration files |
| `/flux-migrate`  | Build zero-downtime migration — SQL/code with rollback plan, safe column operations       |
| `/flux-pipeline` | Build a data pipeline — ETL/ELT with scheduling, error recovery, idempotency              |
| `/flux-query`    | Optimize slow queries — indexes, rewrites, execution plan analysis                        |
| `/flux-health`   | Data quality and pipeline health check — schema drift, stale data, broken pipelines       |
| `/flux-recon`    | Database survey in a takeover — schema, migrations, indexes, backups, data volume         |

### Warden (Security) — 4 skills

| Skill            | Description                                                                           |
| ---------------- | ------------------------------------------------------------------------------------- |
| `/warden-audit`  | Full security audit — secrets, deps, injection, IAM, exposed endpoints, prioritized   |
| `/warden-harden` | Harden a service — auth, validation, rate limiting, headers, CORS, secrets management |
| `/warden-iam`    | Build IAM from scratch — roles, policies, service accounts, least privilege           |
| `/warden-recon`  | Security posture survey in a takeover — secrets, deps, IAM, compliance gaps           |

### Vigil (Observability + Reliability) — 5 skills

| Skill               | Description                                                                               |
| ------------------- | ----------------------------------------------------------------------------------------- |
| `/vigil-instrument` | Instrument a service — logging, metrics (RED), tracing (OTel), health checks              |
| `/vigil-alert`      | Build alerting + runbooks — define SLOs, create alert rules, write response runbooks      |
| `/vigil-incident`   | Incident response — diagnose from logs/traces/metrics, identify root cause, propose fix   |
| `/vigil-check`      | Verify observability posture — is monitoring sufficient, are alerts working, SLOs defined |
| `/vigil-recon`      | Observability survey in a takeover — what's monitored, what's blind, alert inventory      |

### Prism (Frontend/DX) — 5 skills

| Skill              | Description                                                                                    |
| ------------------ | ---------------------------------------------------------------------------------------------- |
| `/prism-ui`        | Build a UI from scratch — right stack, components, real data, loading/error states, responsive |
| `/prism-component` | Build a reusable component — composable, accessible, typed, tested                             |
| `/prism-dashboard` | Build an internal dashboard/admin — data tables, filters, charts, CRUD                         |
| `/prism-audit`     | Frontend audit — performance, accessibility, bundle size, component quality                    |
| `/prism-recon`     | Frontend survey in a takeover — stack, bundles, components, a11y, performance                  |

### Cortex (ML/AI) — 5 skills

| Skill               | Description                                                                            |
| ------------------- | -------------------------------------------------------------------------------------- |
| `/cortex-model`     | Build ML pipeline — data prep, training, evaluation, serving endpoint, baseline first  |
| `/cortex-prompt`    | Build and test prompts — versioned, eval harness, measured quality                     |
| `/cortex-integrate` | Integrate LLM into a service — API calls, caching, fallbacks, cost controls, streaming |
| `/cortex-eval`      | Evaluate model performance — drift detection, accuracy tracking, data quality check    |
| `/cortex-recon`     | ML survey in a takeover — model inventory, training pipelines, serving, monitoring     |

### Touch (Mobile) — 5 skills

| Skill            | Description                                                                             |
| ---------------- | --------------------------------------------------------------------------------------- |
| `/touch-app`     | Build mobile app from scratch — platform choice, navigation, API integration, offline   |
| `/touch-feature` | Build a mobile feature — screen + logic + API + tests, platform conventions             |
| `/touch-release` | Set up mobile release pipeline — Fastlane, signing, store metadata, beta distribution   |
| `/touch-audit`   | Mobile audit — app store readiness, performance, crash rates, platform compliance       |
| `/touch-recon`   | Mobile survey in a takeover — store status, crash rates, dependencies, release pipeline |

### Volt (Embedded/IoT) — 4 skills

| Skill            | Description                                                                          |
| ---------------- | ------------------------------------------------------------------------------------ |
| `/volt-firmware` | Build firmware from scratch — RTOS, peripherals, power management, OTA scaffold      |
| `/volt-driver`   | Build device driver or protocol handler — I2C, SPI, BLE, MQTT, interrupt-driven      |
| `/volt-ota`      | Build OTA update system — atomic, rollback-safe, signed, version managed             |
| `/volt-recon`    | Firmware survey in a takeover — versions, OTA status, protocols, hardware interfaces |

### Atlas (Knowledge) — 4 skills

| Skill            | Description                                                                           |
| ---------------- | ------------------------------------------------------------------------------------- |
| `/atlas-map`     | Map the system — architecture diagrams, component descriptions, dependency graph      |
| `/atlas-adr`     | Write an ADR — context, decision, alternatives, consequences                          |
| `/atlas-onboard` | Generate onboarding docs — architecture, how to run, where things live, key decisions |
| `/atlas-recon`   | Documentation survey in a takeover — what exists, how stale, what's missing           |

### Lens (Analytics/BI) — 5 skills

| Skill             | Description                                                                        |
| ----------------- | ---------------------------------------------------------------------------------- |
| `/lens-dashboard` | Build analytical dashboard — pick tool, connect data, design metrics layout        |
| `/lens-metrics`   | Define and implement metrics framework — north star, KPIs, funnels, SQL + docs     |
| `/lens-report`    | Build reporting pipeline — scheduled reports, Slack/email alerts on metric changes |
| `/lens-audit`     | Review existing analytics — are metrics defined, dashboards useful, anyone looking |
| `/lens-recon`     | Analytics survey in a takeover — BI tools, what's tracked, what's blind            |
