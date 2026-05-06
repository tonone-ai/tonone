# tonone — Agent, Skill & Hook Sitemap

**27 agents · 182 skills · 5 runtime hooks · 26 install hooks**

---

## Runtime Hooks (root plugin)

Fires on Claude Code lifecycle events for all installs.

| Event                | Hook                      | What it does                                             |
| -------------------- | ------------------------- | -------------------------------------------------------- |
| `SessionStart`       | `install-statusline.sh`   | Installs tonone status bar into Claude Code              |
| `SessionStart`       | `tonone-update-check.js`  | Checks for plugin updates (8s timeout)                   |
| `PostToolUse[Agent]` | `tonone-agent-tracker.js` | Tracks agent invocations across the session (5s timeout) |
| `Stop`               | `tonone-notify.js`        | Sends completion notification (5s timeout)               |
| `Notification`       | `tonone-notify.js`        | Relays Claude notifications (5s timeout)                 |

---

## Engineering Team — 15 agents

### Apex — Engineering Lead

Routes tasks to specialist agents, scopes work, controls depth and budget.

| Skill            | Description                                                        |
| ---------------- | ------------------------------------------------------------------ |
| `/apex`          | Hand Apex any task — routes internally to the right specialist     |
| `/apex-plan`     | Plan and scope a project — S/M/L options with token/cost estimates |
| `/apex-recon`    | Engineering lead recon — inventory project state before planning   |
| `/apex-review`   | Cross-cutting review — catches gaps between specialists            |
| `/apex-status`   | CTO-level project status from git and codebase state               |
| `/apex-takeover` | Take ownership of an inherited or acquired codebase                |

---

### Atlas — Knowledge Engineering

Architecture docs, ADRs, API specs, system diagrams, onboarding.

| Skill              | Description                                                        |
| ------------------ | ------------------------------------------------------------------ |
| `/atlas`           | Architecture docs, ADRs, diagrams, changelogs, onboarding          |
| `/atlas-adr`       | Write an Architecture Decision Record                              |
| `/atlas-changelog` | Maintain per-repo and cross-repo changelogs                        |
| `/atlas-map`       | Map system architecture as C4 Mermaid diagrams                     |
| `/atlas-onboard`   | Generate onboarding documentation for the project                  |
| `/atlas-present`   | Generate HTML presentation + Obsidian Canvas for releases          |
| `/atlas-recon`     | Documentation recon — find all docs, assess accuracy and freshness |
| `/atlas-report`    | Render agent findings as a styled HTML report in browser           |

**Install hook:** `post_install` → `bash scripts/setup.sh`
**Runtime hook:** `PostToolUse[Agent]` → auto-runs `/atlas-changelog` when an agent skill completes

---

### Forge — Infrastructure

Cloud services, networking, IaC, cost optimization.

| Skill             | Description                                                     |
| ----------------- | --------------------------------------------------------------- |
| `/forge`          | Infrastructure engineer — cloud services, IaC, networking, cost |
| `/forge-audit`    | Audit infrastructure for security issues, waste, and misconfigs |
| `/forge-cost`     | Audit cloud costs and produce a concrete optimization plan      |
| `/forge-diagnose` | Diagnose runtime issues — cold starts, timeouts, scaling        |
| `/forge-infra`    | Build production-grade infrastructure as code                   |
| `/forge-network`  | Design and build VPCs, subnets, DNS, load balancers             |
| `/forge-recon`    | Inventory all cloud resources, map connections, estimate costs  |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Relay — DevOps

CI/CD, deployments, GitOps, developer experience.

| Skill             | Description                                                        |
| ----------------- | ------------------------------------------------------------------ |
| `/relay`          | CI/CD pipelines, deployments, GitOps, Docker, developer experience |
| `/relay-audit`    | Audit CI/CD pipeline for slowness, security, and reliability       |
| `/relay-deploy`   | Set up deployment config — Dockerfile, manifests, env vars         |
| `/relay-docker`   | Build production-ready Dockerfiles with multi-stage builds         |
| `/relay-pipeline` | Build a full CI/CD pipeline from scratch                           |
| `/relay-recon`    | Map full CI/CD pipeline — triggers, build, test, deploy flow       |
| `/relay-ship`     | End-to-end ship — merge, test, diff review, version bump, commit   |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Spine — Backend

APIs, system design, performance, distributed systems.

| Skill            | Description                                                          |
| ---------------- | -------------------------------------------------------------------- |
| `/spine`         | APIs, system design, performance, distributed systems                |
| `/spine-api`     | Design and spec an API — endpoints, shapes, error codes, auth        |
| `/spine-design`  | Produce a system design doc with components, data flow, tradeoffs    |
| `/spine-perf`    | Find and fix performance bottlenecks — N+1, missing indexes, sync    |
| `/spine-recon`   | Map all routes, middleware, models, dependencies, auth patterns      |
| `/spine-review`  | API and backend code review — REST, auth, validation, error handling |
| `/spine-service` | Build a new production-ready service from scratch                    |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Flux — Data

Databases, migrations, pipelines, data modeling.

| Skill            | Description                                                         |
| ---------------- | ------------------------------------------------------------------- |
| `/flux`          | Databases, migrations, pipelines, schema design, query optimization |
| `/flux-health`   | Data quality and pipeline health check — freshness, drift, nulls    |
| `/flux-migrate`  | Build zero-downtime database migrations with forward + rollback SQL |
| `/flux-pipeline` | Build an ETL/ELT pipeline with error handling and observability     |
| `/flux-query`    | Optimize slow queries — execution plans, indexes, rewrites          |
| `/flux-recon`    | Inventory schema, migrations, data volume, backup strategy          |
| `/flux-schema`   | Design database schema — tables, types, indexes, constraints        |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Warden — Security

IAM, secrets, threat modeling, hardening, auth, supply chain.

| Skill            | Description                                                        |
| ---------------- | ------------------------------------------------------------------ |
| `/warden`        | IAM, secrets, threat modeling, hardening, auth, supply chain       |
| `/warden-audit`  | Full security audit — secrets, IAM, auth, injection, XSS, HTTPS    |
| `/warden-harden` | Produce a hardening spec and implement it — headers, rate limits   |
| `/warden-iam`    | Build IAM from scratch — roles, policies, least-privilege accounts |
| `/warden-recon`  | Inventory secrets management, IAM, dependencies, auth patterns     |
| `/warden-scan`   | Automated SAST + dependency vulnerability scan (Semgrep)           |
| `/warden-threat` | Produce a threat model — assets, ranked threats, mitigations       |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Vigil — Observability & Reliability

SLOs, alerting, instrumentation, incident response.

| Skill               | Description                                                         |
| ------------------- | ------------------------------------------------------------------- |
| `/vigil`            | SLOs, alerting, instrumentation, and incident response              |
| `/vigil-alert`      | Write SLO-based alert rules with burn rate thresholds and runbooks  |
| `/vigil-check`      | Verify observability posture — audit monitoring, find blind spots   |
| `/vigil-incident`   | Incident response — diagnose production issues, find root cause     |
| `/vigil-instrument` | Instrument a service with OpenTelemetry — RED metrics, logs, traces |
| `/vigil-recon`      | Inventory monitoring, map coverage, highlight gaps                  |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Prism — Frontend & DX

UI components, dashboards, design system implementation.

| Skill              | Description                                                          |
| ------------------ | -------------------------------------------------------------------- |
| `/prism`           | UI components, dashboards, design system implementation              |
| `/prism-audit`     | Frontend audit — bundle size, deps, a11y, performance, components    |
| `/prism-chart`     | Build data visualization components                                  |
| `/prism-component` | Implement a reusable, accessible, typed component from a design spec |
| `/prism-dashboard` | Build an internal dashboard with tables, filters, detail views, CRUD |
| `/prism-recon`     | Map component tree, routing, state management, build setup           |
| `/prism-stack`     | Audit and document the frontend technology stack                     |
| `/prism-ui`        | Implement a complete UI screen or feature from a Form visual spec    |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Cortex — ML/AI

LLM integration, prompt engineering, RAG, evals, MLOps.

| Skill               | Description                                                             |
| ------------------- | ----------------------------------------------------------------------- |
| `/cortex`           | LLM integrations, prompt engineering, model pipelines, evals, RAG       |
| `/cortex-eval`      | Evaluate model performance — accuracy drops, data drift, error patterns |
| `/cortex-integrate` | Design and implement an AI feature — model selection, architecture      |
| `/cortex-model`     | Build an ML pipeline — from data to trained model to serving endpoint   |
| `/cortex-prompt`    | Build a production-ready prompt package — system prompt, few-shots      |
| `/cortex-recon`     | Inventory all models, pipelines, data sources, and monitoring           |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Touch — Mobile

Native iOS/Android, cross-platform, app stores, mobile performance.

| Skill            | Description                                                         |
| ---------------- | ------------------------------------------------------------------- |
| `/touch`         | Native iOS/Android, cross-platform, app stores, mobile performance  |
| `/touch-app`     | Produce a complete mobile app architecture design                   |
| `/touch-audit`   | Mobile audit — app size, startup, crash reporting, store compliance |
| `/touch-feature` | Produce a mobile feature spec — user story, technical approach      |
| `/touch-recon`   | Understand app tech stack, architecture, and dependencies           |
| `/touch-release` | Set up mobile release pipeline — Fastlane, code signing, CI, beta   |
| `/touch-ui`      | Mobile UI implementation                                            |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Volt — Embedded & IoT

Firmware, microcontrollers, OTA updates, edge computing, device protocols.

| Skill            | Description                                                         |
| ---------------- | ------------------------------------------------------------------- |
| `/volt`          | Firmware, microcontrollers, OTA updates, device protocols           |
| `/volt-driver`   | Build a device driver or protocol handler — I2C, BLE, MQTT          |
| `/volt-firmware` | Produce a complete firmware architecture spec for a device          |
| `/volt-ota`      | Design a complete OTA update system — partition layout, update flow |
| `/volt-power`    | Power management audit — sleep modes, wake sources, power states    |
| `/volt-recon`    | Firmware recon — inventory MCU, peripherals, RTOS, protocols        |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Lens — Data Analytics & BI

Dashboards, metrics design, reporting, data storytelling.

| Skill             | Description                                                             |
| ----------------- | ----------------------------------------------------------------------- |
| `/lens`           | Dashboards, metrics design, reporting pipelines, data storytelling      |
| `/lens-audit`     | Review existing analytics — find dashboards, check usage and quality    |
| `/lens-chart`     | Build charts and data visualizations                                    |
| `/lens-dashboard` | Design an analytical dashboard — define the question each chart answers |
| `/lens-metrics`   | Produce a complete metrics definition doc with formulas and sources     |
| `/lens-recon`     | Find all analytics tools, inventory what's tracked and what's missing   |
| `/lens-report`    | Build a reporting pipeline — scheduled SQL reports via Slack or email   |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Proof — QA & Testing

Test strategy, E2E suites, integration testing, flaky test triage.

| Skill             | Description                                                          |
| ----------------- | -------------------------------------------------------------------- |
| `/proof`          | Test strategy, E2E suites, API tests, flaky test triage              |
| `/proof-api`      | Build API test suites — endpoint, contract, and load testing         |
| `/proof-audit`    | Audit test suite health — flaky tests, slow tests, coverage gaps     |
| `/proof-design`   | Design a testing approach for a feature or service                   |
| `/proof-e2e`      | Build E2E test specs for critical user journeys (Playwright/Cypress) |
| `/proof-recon`    | Inventory all tests, frameworks, coverage, and CI integration        |
| `/proof-strategy` | Produce a test strategy — risk map, test type decisions, tooling     |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Pave — Platform Engineering

Developer experience, golden paths, service catalogs, environment management.

| Skill              | Description                                                                |
| ------------------ | -------------------------------------------------------------------------- |
| `/pave`            | Developer experience, golden paths, service catalogs, local tooling        |
| `/pave-audit`      | Audit developer experience — onboarding time, build speed, deploy friction |
| `/pave-catalog`    | Build a service catalog — schema, starter entries, governance model        |
| `/pave-contribute` | Contribute a session learning back to the upstream tonone repo             |
| `/pave-env`        | Set up local dev environments — devcontainers, Docker Compose              |
| `/pave-golden`     | Define a golden path — opinionated, supported way to do common tasks       |
| `/pave-recon`      | Inventory all developer tooling, environments, build systems               |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

## Product Team — 12 agents

### Helm — Head of Product

Orchestrates the product team, writes briefs, hands off to Apex.

| Skill           | Description                                                   |
| --------------- | ------------------------------------------------------------- |
| `/helm`         | Orchestrate the product team, write briefs, plan initiatives  |
| `/helm-arbiter` | Scope arbitration — resolve product/engineering disagreements |
| `/helm-brief`   | Write a product brief from research and strategy inputs       |
| `/helm-handoff` | Hand off a brief to Apex using the 6-field schema             |
| `/helm-plan`    | Plan a product initiative end-to-end                          |
| `/helm-recon`   | Survey existing briefs, research, strategy, and roadmap docs  |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Echo — User Research

Interviews, personas, Jobs-to-Be-Done, customer feedback synthesis.

| Skill             | Description                                                              |
| ----------------- | ------------------------------------------------------------------------ |
| `/echo`           | User interviews, personas, Jobs-to-Be-Done, feedback synthesis           |
| `/echo-feedback`  | Cluster support tickets, NPS verbatims, app reviews into themes          |
| `/echo-interview` | Produce an interview guide and synthesize outputs into insights          |
| `/echo-jobs`      | Jobs-to-Be-Done analysis from product, user descriptions, or transcripts |
| `/echo-recon`     | Survey existing personas, research docs, and interview archives          |
| `/echo-segment`   | User segmentation and persona creation from mixed data sources           |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Lumen — Product Analytics

Metrics frameworks, funnel analysis, OKRs, A/B test design, retention.

| Skill               | Description                                                           |
| ------------------- | --------------------------------------------------------------------- |
| `/lumen`            | Metrics architecture, funnel analysis, A/B test design, retention     |
| `/lumen-abtest`     | A/B test design — hypothesis, primary metric, MDE, sample size        |
| `/lumen-funnel`     | Funnel analysis and drop-off diagnosis                                |
| `/lumen-instrument` | Instrumentation plan — event taxonomy, property schema, tracking plan |
| `/lumen-metrics`    | Metrics architecture — complete metrics plan for a product            |
| `/lumen-recon`      | Scan existing event tracking, metric definitions, and dashboards      |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Draft — UX Design

User flows, information architecture, wireframes, interaction design.

| Skill              | Description                                                          |
| ------------------ | -------------------------------------------------------------------- |
| `/draft`           | User flows, information architecture, wireframes, interaction design |
| `/draft-flow`      | Design user flows                                                    |
| `/draft-ia`        | Information architecture — navigation structure, content hierarchy   |
| `/draft-landing`   | Design landing page structure and flow                               |
| `/draft-patterns`  | Design interaction patterns                                          |
| `/draft-recon`     | Scan existing frontend routes, components, and navigation patterns   |
| `/draft-review`    | Usability review against heuristics, flows, and edge cases           |
| `/draft-wireframe` | Produce wireframes for a screen or feature                           |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Form — Visual Design

Brand identity, color systems, typography, UI design, design systems.

| Skill             | Description                                                     |
| ----------------- | --------------------------------------------------------------- |
| `/form`           | Brand identity, color systems, typography, design tokens        |
| `/form-audit`     | Audit visual design for consistency, accessibility, and quality |
| `/form-brand`     | Brand identity design — logo, colors, typography                |
| `/form-brief`     | Write a design brief for a visual project                       |
| `/form-component` | Design a UI component with states, variants, and specs          |
| `/form-deck`      | Design a slide deck or presentation                             |
| `/form-email`     | Design email templates                                          |
| `/form-exam`      | Design system examination — audit coverage, gaps, consistency   |
| `/form-logo`      | Logo design direction and iteration                             |
| `/form-mobile`    | Mobile design — adapt components and layouts for small screens  |
| `/form-palette`   | Design a color palette with semantic tokens                     |
| `/form-social`    | Design social media assets and templates                        |
| `/form-style`     | Write a style guide — typography, spacing, color usage rules    |
| `/form-tokens`    | Define design tokens — spacing, radius, shadow, motion          |
| `/form-web`       | Design a web page or section                                    |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Crest — Product Strategy

Diagnosis-first strategy, roadmap sequencing, competitive positioning.

| Skill              | Description                                                        |
| ------------------ | ------------------------------------------------------------------ |
| `/crest`           | Roadmaps, competitive analysis, OKRs, strategic narratives         |
| `/crest-compete`   | Competitive analysis ending in a clear positioning call            |
| `/crest-narrative` | Write a standalone strategy memo framing product direction         |
| `/crest-okr`       | OKR design with North Star metric, input metrics, and initiatives  |
| `/crest-recon`     | Read existing roadmaps, OKRs, and competitive docs                 |
| `/crest-roadmap`   | Build a product roadmap with sequenced bets and explicit tradeoffs |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Pitch — Product Marketing

Positioning, messaging, value proposition, GTM strategy, launch copy.

| Skill             | Description                                                              |
| ----------------- | ------------------------------------------------------------------------ |
| `/pitch`          | Positioning, messaging, value prop, GTM strategy, launch copy            |
| `/pitch-copy`     | Landing page and marketing copy — hero, problem/solution, pricing        |
| `/pitch-landing`  | Write or redesign a landing page                                         |
| `/pitch-launch`   | Launch plan with announcement copy, channel sequence, day-of run         |
| `/pitch-message`  | Messaging framework — headline, subheadline, proof points, CTA           |
| `/pitch-position` | Complete positioning doc using the Dunford framework                     |
| `/pitch-recon`    | Read existing landing pages, copy, positioning, and competitor messaging |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Surge — Growth

Acquisition channels, activation funnels, retention playbooks, PLG strategy.

| Skill               | Description                                                      |
| ------------------- | ---------------------------------------------------------------- |
| `/surge`            | Acquisition channels, activation funnels, retention, PLG         |
| `/surge-activation` | Design activation sequence and first-value milestones            |
| `/surge-experiment` | Growth experiment design — hypothesis, metric, baseline, rollout |
| `/surge-landing`    | Build a growth-optimized landing or onboarding page              |
| `/surge-plg`        | PLG motion — free tier, activation sequence, expansion triggers  |
| `/surge-recon`      | Scan onboarding flows, acquisition channels, and retention data  |
| `/surge-retention`  | Retention diagnosis + intervention plan from the retention curve |

---

### Deal — Revenue & Sales

B2B pipeline, deal strategy, pricing, sales playbooks, enterprise closing.

| Skill            | Description                                                             |
| ---------------- | ----------------------------------------------------------------------- |
| `/deal`          | B2B pipeline, deal strategy, pricing, sales playbooks                   |
| `/deal-close`    | Diagnose why a deal stalls and write a tailored proposal                |
| `/deal-outreach` | Cold outbound sequence builder — 5-7 touch email + LinkedIn by persona  |
| `/deal-pipeline` | Design or audit B2B sales pipeline — stages, criteria, quotas           |
| `/deal-playbook` | Write sales playbooks — outbound sequences, discovery guides            |
| `/deal-pricing`  | Design pricing strategy and packaging — tiers, enterprise pricing       |
| `/deal-proposal` | Generate a complete B2B proposal — exec summary, pricing, ROI, timeline |
| `/deal-qualify`  | MEDDPICC-based deal qualification worksheet — gaps and next action      |
| `/deal-recon`    | Audit current pipeline, deal patterns, and ICP definitions              |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Keep — Customer Success

Onboarding optimization, health scoring, expansion revenue, churn prevention.

| Skill            | Description                                                                     |
| ---------------- | ------------------------------------------------------------------------------- |
| `/keep`          | Onboarding optimization, health scoring, expansion revenue                      |
| `/keep-churn`    | Churn risk classification (CRITICAL/HIGH/MEDIUM) + intervention sequences       |
| `/keep-expand`   | Design expansion revenue playbooks — upsell triggers, seat expansion            |
| `/keep-health`   | Design a customer health scoring model — signals, weights, thresholds           |
| `/keep-onboard`  | Optimize customer onboarding — activation sequence, drop-off points             |
| `/keep-playbook` | Write churn prevention and win-back playbooks                                   |
| `/keep-qbr`      | Generate a QBR — health summary, wins, expansion opportunity, next quarter plan |
| `/keep-recon`    | Audit onboarding completion, health signals, and churn patterns                 |
| `/keep-segment`  | Customer segmentation model — tier by ARR, health, and expansion potential      |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Ink — Content Marketing

Blog strategy, SEO, thought leadership, developer content, case studies.

| Skill             | Description                                                                |
| ----------------- | -------------------------------------------------------------------------- |
| `/ink`            | Blog strategy, SEO, thought leadership, developer content                  |
| `/ink-brief`      | Content brief generator — keyword, intent, structure, internal links, CTA  |
| `/ink-calendar`   | Build a content calendar — editorial plan, cadence, topic assignment       |
| `/ink-case`       | Write customer case studies and success stories                            |
| `/ink-cluster`    | Topic cluster architect — pillar + supporting posts + internal linking map |
| `/ink-distribute` | Distribution plan per piece — channels, timing, framing, repurposing       |
| `/ink-post`       | Write a blog post — keyword research, draft, publish-ready output          |
| `/ink-recon`      | Audit current content, SEO health, and competitor coverage                 |
| `/ink-seo`        | SEO strategy — topic clusters, keyword gap analysis, prioritization        |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

### Buzz — PR & Community

Press pitches, social media, open source community, DevRel, launch moments.

| Skill             | Description                                                                      |
| ----------------- | -------------------------------------------------------------------------------- |
| `/buzz`           | Press pitches, social media, open source community, DevRel                       |
| `/buzz-community` | Build and manage open source community — Discord/Slack, contributors             |
| `/buzz-devrel`    | Developer relations program — community tiers, ambassadors, metrics              |
| `/buzz-hn`        | Hacker News post crafter — title, body, anti-shadowban rules, response templates |
| `/buzz-launch`    | Design and execute a launch plan — Product Hunt, HN, newsletter                  |
| `/buzz-outreach`  | Personalized media/podcast pitch per target journalist or host                   |
| `/buzz-pitch`     | Write media pitches and press releases — journalist outreach                     |
| `/buzz-recon`     | Audit press coverage, social presence, community health                          |
| `/buzz-social`    | Social media strategy and post drafting — HN, Twitter/X, LinkedIn                |

**Install hook:** `post_install` → `bash scripts/setup.sh`

---

## Cross-team

| Skill             | Description                                                             |
| ----------------- | ----------------------------------------------------------------------- |
| `/tonone-onboard` | First-run onboarding tour — walkthrough of all 27 agents and key skills |

---

## Bundles

Install sets for team deployment. All bundle hooks are empty (install-only).

| Bundle             | Agents included                                                                                      |
| ------------------ | ---------------------------------------------------------------------------------------------------- |
| `engineering-team` | apex, forge, relay, spine, flux, warden, vigil, prism, cortex, touch, volt, atlas, lens, proof, pave |
| `product-team`     | helm, echo, lumen, draft, form, crest, pitch, surge, deal, keep, ink, buzz                           |
| `revenue-team`     | deal, keep, surge                                                                                    |
| `marketing-team`   | ink, buzz, pitch                                                                                     |
| `full-team`        | All 27 agents                                                                                        |
