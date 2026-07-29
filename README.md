# Tonone

<img src="https://img.shields.io/badge/version-1.10.3-green"> <img src="https://img.shields.io/badge/license-MIT-green"> <img src="https://img.shields.io/badge/platform-Claude%20Code-blue">

**Founder + Tonone = whole company.**

100 specialists across 10 teams. Engineering executes. Product decides. Operations runs. Legal de-risks. Design polishes. Data Science decides with data. Security Operations defends. Developer Experience ships good APIs. Infrastructure Specialist runs the cloud. AI Operations ships models. One session, a handful of commands, zero meetings. 421 skills across every discipline. MIT licensed.

## The idea

A solo founder used to have one choice: stay small, or hire. Now there's a third path.

Tonone is an open-source AI team you install into Claude Code. Not a generalist assistant — specialists. Each agent owns one domain deeply: infrastructure, security, user research, product strategy, growth, legal, brand, ML, IAM, API design. They share context, hand off cleanly, and produce work you can ship.

The engineering team (15 agents) builds and ships. The product team (12 agents) decides what to build and why. The operations team (4 agents) keeps the company running. The legal team (10 agents) de-risks every move. The design team (10 agents) makes it beautiful and accessible. The data science team (10 agents) turns data into decisions. The security operations team (10 agents) keeps everything safe. The developer experience team (10 agents) ensures external developers succeed. The infrastructure specialist team (10 agents) runs the cloud in depth. The AI operations team (9 agents) ships models to production. Together, one founder can run what used to take a company.

## Install

**Prerequisites:** [Claude Code](https://docs.anthropic.com/en/docs/claude-code) v1.0+

From your terminal:

```bash
claude plugin marketplace add tonone-ai/tonone
claude plugin install tonone@tonone-ai
```

Or inside an active Claude Code session:

```text
/plugin marketplace add tonone-ai/tonone
/plugin install tonone@tonone-ai
```

Installing the full roster pulls in all 100 agents. If that's more than a given project needs, run `/apex-profile` after install to scope the roster down to a curated subset (e.g. just the engineering core).

### Codex CLI

**Prerequisites:** [Codex CLI](https://github.com/openai/codex) installed

```bash
git clone https://github.com/tonone-ai/tonone
cd tonone
codex
```

Codex reads `AGENTS.md` automatically. Invoke agents and skills by describing what you want:

```text
> Read agents/forge.md and act as Forge — audit this infrastructure
> Read agents/apex.md — plan this project with XS-XXL depth options
> Follow the workflow in skills/warden-audit/SKILL.md
```

Skills are markdown workflow documents in `skills/<name>/SKILL.md`. Read them and follow the steps — no slash commands needed.

## Usage

```text
> /apex-plan Build a real-time analytics platform for our IoT fleet
> /helm-brief Define the next product sprint
> /forge-infra Set up cloud infrastructure for a new SaaS product
> /spine-api Design a REST API for user management
> /warden-audit Run a full security audit on this codebase
> /echo-interview Run a user research session
> /crest-roadmap Build a product roadmap
> /mint-runway How long is our runway and how do we extend it?
> /folk-hire Build a hiring pipeline for a senior engineer
> /brace-sla Define our support SLA tiers
> /bind-gap Run a SOC2 gap analysis
> /hue-palette Design a color palette with WCAG-compliant contrast
> /feat-engineer Design a feature engineering pipeline for churn prediction
> /red-pentest Plan a penetration test against our staging environment
> /guide-write Write API reference docs for our new webhook endpoint
> /kube-design Design a Kubernetes cluster architecture for our workload
> /evals-harness Design an eval harness for our RAG pipeline
```

Every specialist ships in three modes:

| Mode       | What It Means                                         | Example Skills                                                  |
| ---------- | ----------------------------------------------------- | --------------------------------------------------------------- |
| **Build**  | Create from scratch — production-ready, not tutorials | `/forge-infra`, `/spine-api`, `/prism-ui`, `/touch-app`         |
| **Review** | Audit and fix existing systems                        | `/warden-audit`, `/relay-audit`, `/prism-audit`, `/vigil-check` |
| **Recon**  | Survey a domain for system takeover                   | `/forge-recon`, `/spine-recon`, `/flux-recon`, `/apex-takeover` |

### The Leads

**Apex** leads the engineering team. Tell it what you're building:

```text
You: "Build user authentication for our SaaS"

Apex: I see 3 ways to approach this:

  S — Quick & focused (Spine + Warden, ~30K tokens, ~$0.05)
      Basic JWT auth with security review.

  M — Solid implementation (Spine + Warden + Flux + Relay, ~120K tokens, ~$0.20)
      Auth + session management + user schema + CI tests.

  L — Full build-out (+ Vigil + Atlas, ~250K tokens, ~$0.45)
      Everything in M + monitoring + documentation.

  My recommendation: M. Which level?
```

**Helm** is the head of product. It orchestrates research, strategy, design, and marketing — then hands off a structured brief to Apex when it's time to build.

Beyond the two leads, `/apex-route` reaches any specialist on demand — even ones not currently installed in a scoped roster — so a `/apex-profile`-trimmed project never loses access to the full 100-agent bench.

### System Takeover

Inherited a codebase? Apex runs parallel reconnaissance across all specialists:

```text
> /apex-takeover

Phase 1 — Recon (parallel):
  Atlas maps the architecture
  Forge inventories infrastructure
  Relay assesses the pipeline
  Warden scans for security issues
  Vigil checks observability

Phase 2 — Deep dive (targeted):
  Spine reviews backend quality
  Flux assesses database health
  Prism audits frontend

Phase 3 — Takeover report:
  System map, risk assessment, quick wins, roadmap
```

## The Team

### Engineering — 15 agents

| Agent      | Hat                         | What They Do                                                  |
| ---------- | --------------------------- | ------------------------------------------------------------- |
| **Apex**   | Engineering Lead            | Orchestrates the team, scopes work, controls depth and budget |
| **Forge**  | Infrastructure              | Cloud services, networking, IaC, cost optimization            |
| **Relay**  | DevOps                      | CI/CD, deployments, GitOps, developer experience              |
| **Spine**  | Backend                     | APIs, system design, performance, distributed systems         |
| **Flux**   | Data                        | Databases, migrations, pipelines, data modeling               |
| **Warden** | Security                    | IAM, secrets, compliance, threat modeling                     |
| **Vigil**  | Observability + Reliability | Monitoring, alerting, SRE, incident response, SLOs            |
| **Prism**  | Frontend/DX                 | UI, internal tools, developer portals                         |
| **Cortex** | ML/AI                       | Model training, MLOps, feature engineering, LLM integration   |
| **Touch**  | Mobile                      | Native iOS/Android, cross-platform, app stores                |
| **Volt**   | Embedded/IoT                | Firmware, microcontrollers, edge computing, protocols         |
| **Atlas**  | Knowledge Engineering       | Architecture docs, ADRs, API specs, system diagrams           |
| **Lens**   | Data Analytics & BI         | Dashboards, metrics design, reporting, data storytelling      |
| **Proof**  | QA & Testing                | Test strategy, E2E suites, integration testing, flaky triage  |
| **Pave**   | Platform Engineering        | Developer experience, golden paths, service catalogs          |

### Product — 12 agents

| Agent     | Hat               | What They Do                                                                 |
| --------- | ----------------- | ---------------------------------------------------------------------------- |
| **Helm**  | Head of Product   | Orchestrates the product team, writes briefs, hands off to Apex              |
| **Echo**  | User Research     | User interviews, personas, Jobs-to-Be-Done, feedback synthesis               |
| **Lumen** | Product Analytics | Metrics frameworks, funnel analysis, OKRs, A/B test design                   |
| **Draft** | UX Design         | User flows, information architecture, wireframes                             |
| **Form**  | Visual Design     | Brand identity, color systems, typography, design system                     |
| **Crest** | Product Strategy  | Roadmap planning, prioritization, competitive analysis                       |
| **Pitch** | Product Marketing | Positioning, messaging, value prop, GTM, launch copy                         |
| **Surge** | Growth            | Acquisition channels, activation funnels, retention playbooks                |
| **Deal**  | Revenue & Sales   | B2B pipeline, deal strategy, pricing, sales playbooks, enterprise closing    |
| **Keep**  | Customer Success  | Onboarding optimization, health scoring, expansion revenue, churn prevention |
| **Ink**   | Content Marketing | Blog strategy, SEO, thought leadership, developer content, content calendar  |
| **Buzz**  | PR & Community    | Press pitches, social media, open source community, DevRel, launch moments   |

### Operations — 4 agents

| Agent     | Hat        | What They Do                                                                                     |
| --------- | ---------- | ------------------------------------------------------------------------------------------------ |
| **Mint**  | Finance    | P&L, runway, unit economics, fundraising, board reporting, cap table                             |
| **Folk**  | People     | Org design, hiring pipelines, comp frameworks, onboarding, performance, human-to-agent migration |
| **Keel**  | Operations | Process design, vendor management, legal ops, compliance (SOC2/GDPR), OKR execution              |
| **Brace** | Support    | Ticket workflow, SLA design, knowledge base, escalation paths, support operations                |

### Legal — 10 agents

| Agent      | Hat                           | What They Do                                                              |
| ---------- | ----------------------------- | ------------------------------------------------------------------------- |
| **Brief**  | Contract & Policy Drafter     | NDAs, MSAs, employment agreements, SLAs, vendor contracts                 |
| **Clause** | Contract Clause Analyst       | Redlining, risk scoring, negotiation playbooks                            |
| **Bind**   | Compliance Framework Engineer | SOC2, GDPR, HIPAA, ISO 27001 gap analysis and remediation                 |
| **Frame**  | Corporate Governance Advisor  | Board resolutions, cap table hygiene, equity plan docs                    |
| **Shield** | Regulatory Risk Advisor       | GDPR exposure, CCPA, FTC rules, financial regulation, export controls     |
| **Scope**  | IP & Trademark Advisor        | Trademark clearance, patent landscape, open source license compliance     |
| **Audit**  | Legal Compliance Auditor      | Internal controls review, legal risk register, audit trail docs           |
| **Cite**   | Legal Researcher              | Case law synthesis, statute analysis, jurisdiction comparison             |
| **Lodge**  | Regulatory Filing Advisor     | DMCA, FTC disclosures, GDPR DPAs, government filings, state registrations |
| **Terms**  | Privacy & ToS Drafter         | GDPR-compliant privacy policies, ToS, cookie policies, DPAs               |

### Design — 10 agents

| Agent     | Hat                          | What They Do                                                                |
| --------- | ---------------------------- | --------------------------------------------------------------------------- |
| **Hue**   | Color Systems Designer       | Color palettes, semantic tokens, dark/light mode, WCAG contrast             |
| **Grid**  | Layout Systems Designer      | Spacing systems, responsive grids, breakpoints, layout primitives           |
| **Glyph** | Typography Designer          | Font selection, type scale, hierarchy, readability tokens                   |
| **Move**  | Motion Designer              | Animation systems, transitions, micro-interactions, motion tokens           |
| **Wire**  | Prototyping Engineer         | Interactive prototypes, flow documentation, design handoff specs            |
| **Mark**  | Brand Designer               | Logo usage, brand guidelines, visual identity, asset library                |
| **Cut**   | Illustration & Icon Designer | Custom illustrations, icon systems, SVG optimization                        |
| **Axe**   | Accessibility Engineer       | WCAG audits, keyboard navigation, screen reader testing, ARIA               |
| **Tone**  | Design Token Engineer        | Token architecture, multi-brand theming, style-dictionary pipelines         |
| **Copy**  | Content Designer             | UX writing, microcopy, error messages, onboarding copy, UI content strategy |

### Data Science — 10 agents

| Agent     | Hat                                 | What They Do                                                          |
| --------- | ----------------------------------- | --------------------------------------------------------------------- |
| **Cast**  | Forecasting Engineer                | Time series forecasting, demand prediction, seasonal decomposition    |
| **Feat**  | Feature Engineer                    | Feature engineering, encodings, feature stores, pipeline design       |
| **Fit**   | Model Training Engineer             | Algorithm selection, hyperparameter tuning, training pipelines        |
| **Score** | Model Evaluation Engineer           | Metrics design, statistical significance, model comparison            |
| **Drift** | ML Monitoring Engineer              | Data drift, concept drift, model degradation, production ML health    |
| **Vect**  | Embeddings & Vector Search Engineer | Semantic search, RAG pipelines, vector database design                |
| **Tune**  | LLM Fine-tuning Engineer            | PEFT/LoRA, RLHF, instruction tuning, prompt optimization              |
| **Plot**  | Data Visualization Engineer         | Chart design, EDA, visualization libraries, dashboard specs           |
| **Clean** | Data Quality Engineer               | Deduplication, validation, outlier detection, ETL pipelines           |
| **Eval**  | Experiment Design Engineer          | A/B testing, statistical power, experiment tracking, causal inference |

### Security Operations — 10 agents

| Agent     | Hat                               | What They Do                                                      |
| --------- | --------------------------------- | ----------------------------------------------------------------- |
| **Red**   | Offensive Security Engineer       | Pen testing plans, red team exercises, attack path documentation  |
| **Blue**  | Defensive Security Engineer       | SOC design, detection engineering, hardening playbooks            |
| **Hunt**  | Threat Hunter                     | Hypothesis-driven hunting, compromise assessment, IOC analysis    |
| **Patch** | Vulnerability Management Engineer | CVE triage, CVSS + EPSS prioritization, patch SLA design          |
| **Chain** | Supply Chain Security Engineer    | SBOM generation, dependency scanning, third-party risk            |
| **Sast**  | Application Security Engineer     | SAST/DAST pipelines, code security review, secure SDLC            |
| **Siem**  | Detection & SIEM Engineer         | Log pipeline design, SIGMA rules, alert tuning                    |
| **Resp**  | Incident Response Engineer        | IR playbooks, containment runbooks, DFIR, post-incident review    |
| **Zero**  | Zero Trust Architect              | Zero trust roadmap, network microsegmentation, ZTNA design        |
| **Phish** | Security Awareness Engineer       | Phishing simulations, security training programs, culture metrics |

### Developer Experience — 10 agents

| Agent       | Hat                                        | What They Do                                                     |
| ----------- | ------------------------------------------ | ---------------------------------------------------------------- |
| **Guide**   | API Documentation Engineer                 | API reference docs, integration guides, SDK documentation        |
| **Sample**  | Code Sample Engineer                       | Working examples, quickstarts, language-specific tutorials       |
| **Mock**    | API Mocking & Contract Engineer            | Mock servers, consumer-driven contract testing, API simulation   |
| **Schema**  | API Schema Engineer                        | OpenAPI, GraphQL, gRPC schema quality and design standards       |
| **Port**    | SDK Design Engineer                        | Multi-language SDK architecture, idiomatic patterns, consistency |
| **Change**  | Changelog & Release Communication Engineer | Breaking change docs, deprecation notices, migration guides      |
| **Onboard** | Developer Onboarding Engineer              | Quickstart design, time-to-first-call optimization               |
| **Bench**   | API Performance Engineer                   | Latency profiling, throughput testing, regression detection      |
| **Compat**  | Backwards Compatibility Engineer           | Breaking change detection, deprecation management, semver        |
| **Gate**    | API Quality Gate Engineer                  | Linting, style enforcement, breaking change CI, API governance   |

### Infrastructure Specialist — 10 agents

| Agent     | Hat                          | What They Do                                                              |
| --------- | ---------------------------- | ------------------------------------------------------------------------- |
| **Kube**  | Kubernetes Engineer          | Cluster design, RBAC, networking policies, operators, Helm charts         |
| **Terra** | Terraform Engineer           | IaC modules, state management, provider config, drift detection           |
| **Finop** | FinOps Engineer              | Cloud cost optimization, budget alerts, rightsizing, waste elimination    |
| **Serv**  | Service Reliability Engineer | SLO design, error budgets, reliability reviews, capacity planning         |
| **Edge**  | Edge Computing Engineer      | CDN config, edge functions, latency optimization, global routing          |
| **Cache** | Caching Engineer             | Redis/Memcached design, cache invalidation, TTL strategy, hit-rate tuning |
| **Queue** | Message Queue Engineer       | Kafka/SQS/RabbitMQ design, consumer groups, DLQs, backpressure            |
| **Mesh**  | Service Mesh Engineer        | Istio/Linkerd config, mTLS, traffic management, observability             |
| **Multi** | Multi-Cloud Engineer         | Cross-cloud architecture, vendor portability, cloud-agnostic patterns     |
| **Chaos** | Chaos Engineering Lead       | Failure injection, game days, resilience testing, blast radius control    |

### AI Operations — 9 agents

| Agent      | Hat                        | What They Do                                                                           |
| ---------- | -------------------------- | -------------------------------------------------------------------------------------- |
| **Deploy** | AI Deployment Engineer     | Model serving, inference APIs, blue/green deploys, rollback, canary releases           |
| **Evals**  | LLM Evaluation Engineer    | Eval harness design, benchmark suites, automated regression, human eval pipelines      |
| **Trace**  | LLM Observability Engineer | LLM tracing, span capture, prompt/completion logging, cost attribution, debugging      |
| **Guard**  | AI Guardrails Engineer     | Input/output safety filters, PII detection, content moderation, policy enforcement     |
| **Budget** | AI Cost Engineer           | LLM spend tracking, model cost optimization, budget alerts, token efficiency audits    |
| **Token**  | Token Management Engineer  | Context window optimization, token counting, truncation strategies, chunking patterns  |
| **Prompt** | Prompt Engineer            | System prompt design, few-shot libraries, chain-of-thought patterns, prompt versioning |
| **Embed**  | Embeddings Engineer        | Embedding model selection, vector pipeline design, similarity search, index management |
| **Rank**   | AI Ranking Engineer        | Retrieval reranking, relevance scoring, learning-to-rank, result quality evaluation    |

## How it works

Each agent is a system prompt (a markdown file in `agents/`) paired with a set of skills (markdown workflow documents in `team/<agent>/skills/<name>/SKILL.md`, mirrored to `skills/<name>/SKILL.md` at the repo root). The Claude Code plugin system installs all 100 agents and 421 skills in a single command. When you invoke a skill, Claude loads the workflow document and follows it — no code runs, no build step, no configuration.

Every engineering agent detects your stack automatically:

- **Cloud:** GCP, AWS, Azure, Cloudflare, Vercel, Fly.io, Hetzner, DigitalOcean
- **CI/CD:** GitHub Actions, GitLab CI, Cloud Build, CircleCI, Bitbucket Pipelines
- **Backend:** Node.js, Python, Go, Rust, Java/Kotlin, Ruby
- **Databases:** PostgreSQL, MySQL, MongoDB, Redis, BigQuery, Snowflake, Supabase, Planetscale
- **Frontend:** React/Next.js, Vue/Nuxt, Svelte/SvelteKit, Astro
- **Mobile:** Swift/SwiftUI, Kotlin/Compose, React Native, Flutter
- **ML:** PyTorch, scikit-learn, Vertex AI, SageMaker, OpenAI, Anthropic

## All 421 Skills

<details>
<summary>Click to expand full skill list</summary>

#### Engineering Team (15 agents, 91 skills)

**Apex** (Engineering Lead)

- `/apex-plan` — Plan and scope a project
- `/apex-profile` — Scope the tonone agent roster for this project
- `/apex-recon` — Engineering lead reconnaissance
- `/apex-review` — Cross-cutting review of recent work
- `/apex-route` — Reach ANY tonone specialist on demand, even ones not installed in this session's roster
- `/apex-stats` — Spawn-count analytics for the tonone roster
- `/apex-status` — CTO-level project status from git and codebase state
- `/apex-takeover` — System takeover

**Forge** (Infrastructure)

- `/forge-audit` — Audit existing infrastructure for security issues, waste, and misconfigurations
- `/forge-cost` — Audit cloud infrastructure costs and produce a concrete optimization plan with specific changes and estimated savings
- `/forge-diagnose` — Diagnose runtime infrastructure issues
- `/forge-infra` — Build production-grade infrastructure as code for a service or project
- `/forge-network` — Design and build networking infrastructure
- `/forge-recon` — Infrastructure reconnaissance

**Relay** (DevOps)

- `/relay-audit` — Audit an existing CI/CD pipeline for slowness, security issues, and reliability gaps
- `/relay-deploy` — Set up a complete deployment configuration
- `/relay-docker` — Build production-ready Dockerfiles with multi-stage builds, security hardening, and docker-compose for local dev
- `/relay-pipeline` — Build a full CI/CD pipeline from scratch
- `/relay-recon` — Map the full CI/CD pipeline
- `/relay-ship` — End-to-end ship workflow

**Spine** (Backend)

- `/spine-api` — Design and spec an API
- `/spine-design` — Produce a system design doc
- `/spine-perf` — Find and fix performance bottlenecks
- `/spine-recon` — Backend reconnaissance
- `/spine-review` — API and backend code review
- `/spine-service` — Build a new production-ready service from scratch

**Flux** (Data)

- `/flux-health` — Data quality and pipeline health check
- `/flux-migrate` — Build zero-downtime database migrations
- `/flux-pipeline` — Build a data pipeline
- `/flux-query` — Optimize slow database queries
- `/flux-recon` — Database reconnaissance
- `/flux-schema` — Design and build database schema

**Warden** (Security)

- `/warden-audit` — Full security audit
- `/warden-harden` — Produce a hardening spec and implement it
- `/warden-iam` — Build IAM from scratch
- `/warden-recon` — Security reconnaissance
- `/warden-scan` — Automated SAST + dependency vulnerability scan
- `/warden-threat` — Produce a threat model

**Vigil** (Observability + Reliability)

- `/vigil-alert` — Write SLO-based alert rules with burn rate thresholds and paired runbooks
- `/vigil-check` — Verify observability posture
- `/vigil-incident` — Incident response
- `/vigil-instrument` — Instrument a service with OpenTelemetry
- `/vigil-recon` — Observability reconnaissance

**Prism** (Frontend/DX)

- `/prism-audit` — Frontend audit
- `/prism-chart` — Select and implement a data visualization component
- `/prism-component` — Implement a reusable, accessible, typed component from a design spec
- `/prism-dashboard` — Build an internal dashboard with data tables, filters, detail views, and CRUD
- `/prism-recon` — Frontend reconnaissance
- `/prism-stack` — Framework-specific implementation guidelines (React/Vue/Svelte/Next.js)
- `/prism-ui` — Implement a complete UI screen or feature from a Form visual spec

**Cortex** (ML/AI)

- `/cortex-eval` — Evaluate model performance
- `/cortex-integrate` — Design and implement an AI feature integration
- `/cortex-model` — Build an ML pipeline
- `/cortex-prompt` — Build a production-ready prompt package
- `/cortex-recon` — ML reconnaissance

**Touch** (Mobile)

- `/touch-app` — Produce a complete mobile app architecture design
- `/touch-audit` — Mobile audit
- `/touch-feature` — Produce a mobile feature spec
- `/touch-recon` — Mobile reconnaissance
- `/touch-release` — Set up mobile release pipeline
- `/touch-ui` — Mobile UI guidelines — touch targets, platform-specific patterns

**Volt** (Embedded/IoT)

- `/volt-driver` — Build a device driver or protocol handler
- `/volt-firmware` — Produce a complete firmware architecture spec for a described device
- `/volt-ota` — Produce a complete OTA update system design
- `/volt-power` — Power management audit
- `/volt-recon` — Firmware reconnaissance for takeover

**Atlas** (Knowledge Engineering)

- `/atlas-adr` — Write an Architecture Decision Record
- `/atlas-changelog` — Maintain per-repo and cross-repo changelogs
- `/atlas-map` — Map the system architecture
- `/atlas-onboard` — Generate onboarding documentation
- `/atlas-present` — Generate a polished HTML presentation page and Obsidian Canvas for big releases
- `/atlas-recon` — Documentation reconnaissance for takeover
- `/atlas-report` — Render agent findings as a styled HTML report in the browser

**Lens** (Data Analytics & BI)

- `/lens-audit` — Review existing analytics
- `/lens-chart` — Select chart types for analytics dashboards and BI visualizations
- `/lens-dashboard` — Design and spec an analytical dashboard
- `/lens-metrics` — Produce a complete metrics definition doc
- `/lens-recon` — Analytics reconnaissance for takeover
- `/lens-report` — Build a reporting pipeline

**Proof** (QA & Testing)

- `/proof-api` — Build API test suites
- `/proof-audit` — Audit test suite health
- `/proof-design` — Design QA audit — visual bugs, severity classification, quality scorecard
- `/proof-e2e` — Build E2E test specs for critical user journeys
- `/proof-recon` — Testing reconnaissance
- `/proof-strategy` — Produce a test strategy for a project or feature

**Pave** (Platform Engineering)

- `/pave-audit` — Audit developer experience
- `/pave-catalog` — Build a service catalog
- `/pave-contribute` — Contribute a session learning back to the upstream tonone repo
- `/pave-env` — Set up local development environments
- `/pave-golden` — Define a golden path
- `/pave-recon` — Platform reconnaissance

#### Product Team (12 agents, 89 skills)

**Helm** (Head of Product)

- `/helm-arbiter` — Scope arbitration
- `/helm-brief` — Write a product brief and turn a feature idea into a spec
- `/helm-handoff` — Hand a finalized product brief off to Apex to kick off engineering
- `/helm-plan` — Build a product roadmap and prioritize the backlog
- `/helm-recon` — Product landscape reconnaissance

**Echo** (User Research)

- `/echo-feedback` — Feedback synthesis
- `/echo-interview` — Run a user interview
- `/echo-jobs` — Jobs-to-Be-Done analysis
- `/echo-recon` — User research reconnaissance
- `/echo-segment` — User segmentation and persona creation from mixed data sources

**Lumen** (Product Analytics)

- `/lumen-abtest` — A/B test design
- `/lumen-funnel` — Analyze a funnel and diagnose where users drop off
- `/lumen-instrument` — Instrumentation plan
- `/lumen-metrics` — Metrics architecture
- `/lumen-recon` — Analytics reconnaissance

**Draft** (UX Design)

- `/draft-flow` — Design a user flow and map how a user moves through a feature
- `/draft-ia` — Information architecture
- `/draft-landing` — Structure a landing page for conversion
- `/draft-patterns` — UX pattern reference — form design, navigation, loading states
- `/draft-proto` — Hi-fi interactive HTML prototype, single-file, Playwright-verified
- `/draft-recon` — UI and UX reconnaissance
- `/draft-review` — Usability review
- `/draft-wireframe` — Wireframe a screen — ASCII by default, hand-drawn HTML mode available

**Form** (Visual Design)

- `/form-animate` — Motion design — HTML animations exported to MP4/GIF
- `/form-audit` — Audit UI for visual quality, consistency, and brand alignment
- `/form-brand` — Create a brand identity — palette, type system, style guide
- `/form-brief` — Translate a design brief into a concrete DESIGN.md
- `/form-component` — Design a UI component spec — button, input, card, modal
- `/form-critique` — Expert 5-dimension design critique, scored and actionable
- `/form-deck` — Design a pitch deck or presentation
- `/form-direction` — Generate 3 differentiated visual directions with live HTML demos
- `/form-email` — Design an email template or campaign asset
- `/form-exam` — Theory-backed design audit citing the principle and source
- `/form-logo` — Create a logo concept or brand mark
- `/form-mobile` — Design iOS or Android mobile app screens
- `/form-palette` — Generate an industry-matched color palette
- `/form-social` — Design social media graphics and ad creatives
- `/form-style` — Select a UI style or visual direction for a product
- `/form-tokens` — Define a design token system and CSS custom properties
- `/form-web` — Design a landing page or marketing website

**Crest** (Product Strategy)

- `/crest-compete` — Competitive analysis ending in a clear positioning call
- `/crest-narrative` — Strategic narrative
- `/crest-okr` — OKR design
- `/crest-recon` — Strategic context reconnaissance
- `/crest-roadmap` — Build a product roadmap with sequenced bets and explicit tradeoffs

**Pitch** (Product Marketing)

- `/pitch-copy` — Landing page and marketing copy
- `/pitch-landing` — Structure a landing page for positioning and conversion
- `/pitch-launch` — Produce an actual launch plan with announcement copy, channel sequence, and day-1 checklist
- `/pitch-message` — Messaging framework
- `/pitch-position` — Produce a complete positioning document using the Dunford framework
- `/pitch-recon` — Marketing and messaging reconnaissance

**Surge** (Growth)

- `/surge-activation` — Improve activation and map the growth funnel
- `/surge-experiment` — Growth experiment design
- `/surge-landing` — Design growth-optimized landing pages and activation layouts
- `/surge-plg` — PLG motion design
- `/surge-recon` — Growth state reconnaissance
- `/surge-retention` — Retention diagnosis + intervention plan

**Deal** (Revenue & Sales)

- `/deal-close` — Close a specific deal
- `/deal-outreach` — Cold outbound sequence builder
- `/deal-pipeline` — Design or audit B2B sales pipeline
- `/deal-playbook` — Write sales playbooks
- `/deal-pricing` — Design pricing strategy and packaging
- `/deal-proposal` — B2B proposal generator
- `/deal-qualify` — MEDDPICC-based deal qualification worksheet
- `/deal-recon` — Revenue reconnaissance

**Keep** (Customer Success)

- `/keep-churn` — Churn risk identification and intervention
- `/keep-expand` — Design expansion revenue playbooks
- `/keep-health` — Design a customer health scoring model
- `/keep-onboard` — Optimize customer onboarding
- `/keep-playbook` — Write churn prevention and win-back playbooks
- `/keep-qbr` — Quarterly Business Review template generator
- `/keep-recon` — Customer success reconnaissance
- `/keep-segment` — Customer segmentation model builder

**Ink** (Content Marketing)

- `/ink-brief` — Content brief generator
- `/ink-calendar` — Build a content calendar
- `/ink-case` — Write customer case studies and success stories
- `/ink-cluster` — Topic cluster architecture builder
- `/ink-distribute` — Content distribution plan
- `/ink-post` — Write a blog post or article
- `/ink-recon` — Content marketing reconnaissance
- `/ink-seo` — SEO strategy and keyword research

**Buzz** (PR & Community)

- `/buzz-community` — Build and manage open source community
- `/buzz-devrel` — Developer relations playbook builder
- `/buzz-hn` — Hacker News post crafter
- `/buzz-launch` — Design and execute a launch plan
- `/buzz-outreach` — Media and podcast outreach personalizer
- `/buzz-pitch` — Write media pitches and press releases
- `/buzz-recon` — PR and community reconnaissance
- `/buzz-social` — Social media strategy and post drafting

#### Operations Team (4 agents, 32 skills)

**Mint** (Finance)

- `/mint-board` — Produce board financial package
- `/mint-budget` — Design or review annual operating budget
- `/mint-model` — Build or audit a financial model
- `/mint-raise` — Prepare fundraising financial materials
- `/mint-recon` — Financial reconnaissance
- `/mint-report` — Generate financial reports
- `/mint-runway` — Calculate and extend runway
- `/mint-unit` — Audit and improve unit economics

**Folk** (People)

- `/folk-comp` — Design compensation framework - salary bands, equity philosophy, offer templates, and total comp benchmarking
- `/folk-culture` — Document and strengthen company culture - values articulation, team norms, communication protocols, and culture health diagnostics
- `/folk-hire` — Build a hiring pipeline - job description, sourcing strategy, interview scorecard, and offer process
- `/folk-migrate` — Run human-to-agent migration - audit which roles can be agent-assisted or replaced, design the transition playbook, and manage the offboarding of displaced roles
- `/folk-onboard` — Build onboarding playbook - day 1 through week 4 checklist, access provisioning, context transfer, and success milestones
- `/folk-org` — Design or review org structure - spans of control, reporting lines, role clarity, headcount plan, and team topology
- `/folk-perf` — Design performance management system - review cycles, calibration process, career ladder, and PIP framework
- `/folk-recon` — People reconnaissance - audit org design, hiring pipeline, comp structure, onboarding, and performance systems to understand what is working and where the constraint is

**Keel** (Operations)

- `/keel-audit` — Operational efficiency audit
- `/keel-cadence` — Design meeting and communication cadence
- `/keel-comply` — Build or audit compliance program
- `/keel-legal` — Draft or review legal ops documents
- `/keel-okr` — Design and run OKR program
- `/keel-process` — Document or redesign a business process
- `/keel-recon` — Operations reconnaissance
- `/keel-vendor` — Manage vendor relationships

**Brace** (Support)

- `/brace-escalate` — Design escalation path -- Tier 1 to Tier 2 to Engineering handoff, decision criteria, and communication templates
- `/brace-kb` — Build or audit knowledge base -- article structure, coverage gaps, deflection rate, and maintenance process
- `/brace-metrics` — Design support metrics dashboard -- CSAT, FRT, TTR, ticket deflection rate, volume trends, and agent efficiency
- `/brace-onboard` — Design customer support onboarding flow -- first-contact experience, proactive support touchpoints, and setup success checklist
- `/brace-playbook` — Write support playbook -- response templates, issue-type runbooks, tone guide, and common resolution paths
- `/brace-recon` — Support operations reconnaissance -- audit current ticket volume, SLA compliance, knowledge base coverage, escalation paths, and CSAT to understand where support is the constraint
- `/brace-sla` — Design SLA framework -- response time targets, resolution time targets, tier definitions, and breach escalation process
- `/brace-triage` — Design ticket triage system -- routing rules, priority tags, queue structure, and first-response automation

#### Legal Team (10 agents, 30 skills)

**Brief** (Contract & Policy Drafter)

- `/brief-draft` — Draft a contract or policy document from a description or template
- `/brief-recon` — Survey the project's existing contracts and policy docs
- `/brief-review` — Review and redline a contract

**Clause** (Contract Clause Analyst)

- `/clause-analyze` — Deep clause-by-clause analysis of a contract with risk scores
- `/clause-playbook` — Generate negotiation playbook for a specific contract type
- `/clause-recon` — Survey existing contracts for common clause patterns and risks

**Bind** (Compliance Framework Engineer)

- `/bind-gap` — Run a compliance gap analysis against SOC2, GDPR, HIPAA, or ISO 27001
- `/bind-policy` — Draft compliance policies required by a framework (access control, incident response, data retention)
- `/bind-recon` — Survey existing compliance artifacts

**Frame** (Corporate Governance Advisor)

- `/frame-board` — Draft board resolutions, consent documents, and meeting minutes
- `/frame-equity` — Draft equity plan documents
- `/frame-recon` — Survey corporate documents

**Shield** (Regulatory Risk Advisor)

- `/shield-assess` — Regulatory exposure assessment for a described product or geography
- `/shield-recon` — Survey product features and data flows for regulatory exposure
- `/shield-respond` — Draft regulatory response letter or regulator communication

**Scope** (IP & Trademark Advisor)

- `/scope-oss` — Open source license compliance audit
- `/scope-recon` — Survey project IP assets
- `/scope-trademark` — Trademark clearance research and filing preparation for a name or mark

**Audit** (Legal Compliance Auditor)

- `/audit-controls` — Internal legal controls review
- `/audit-legal` — Full legal compliance audit
- `/audit-recon` — Survey legal artifacts for audit readiness

**Cite** (Legal Researcher)

- `/cite-compare` — Jurisdiction comparison for a legal requirement or contract clause
- `/cite-recon` — Survey open legal questions and research gaps in the project
- `/cite-research` — Legal research on a specific question

**Lodge** (Regulatory Filing Advisor)

- `/lodge-dmca` — Draft DMCA takedown notice or counter-notice
- `/lodge-filing` — Prepare a regulatory filing, disclosure notice, or government submission
- `/lodge-recon` — Survey pending and required regulatory filings

**Terms** (Privacy & ToS Drafter)

- `/terms-privacy` — Draft a GDPR-compliant privacy policy for the described product and data flows
- `/terms-recon` — Survey existing privacy and legal docs for completeness and GDPR compliance
- `/terms-tos` — Draft Terms of Service for the described product

#### Design Team (10 agents, 30 skills)

**Hue** (Color Systems Designer)

- `/hue-palette` — Design a color palette with semantic tokens for a brand or product
- `/hue-recon` — Audit existing color usage in a codebase
- `/hue-token` — Audit or refactor a design token system for color

**Grid** (Layout Systems Designer)

- `/grid-layout` — Design a layout system
- `/grid-recon` — Audit existing layout patterns in a codebase
- `/grid-responsive` — Audit or redesign responsive behavior of a layout

**Glyph** (Typography Designer)

- `/glyph-pair` — Select and pair fonts for a product
- `/glyph-recon` — Audit existing typography in a codebase
- `/glyph-scale` — Design a type scale and hierarchy

**Move** (Motion Designer)

- `/move-animate` — Design an animation spec for a component or interaction
- `/move-recon` — Audit existing animations in a codebase
- `/move-system` — Design a motion system for a product

**Wire** (Prototyping Engineer)

- `/wire-prototype` — Document a prototype or user flow
- `/wire-recon` — Audit existing design documentation
- `/wire-spec` — Write a developer handoff spec for a component or feature

**Mark** (Brand Designer)

- `/mark-asset` — Design an asset library structure
- `/mark-brand` — Write brand guidelines
- `/mark-recon` — Audit existing brand assets and usage

**Cut** (Illustration & Icon Designer)

- `/cut-icon` — Design an icon system spec or audit existing icons for consistency and accessibility
- `/cut-illustrate` — Spec or critique custom illustrations
- `/cut-recon` — Audit existing icons and illustrations in a codebase

**Axe** (Accessibility Engineer)

- `/axe-audit` — Run a WCAG accessibility audit against a component, page, or full product
- `/axe-fix` — Write accessibility fixes for specific WCAG failures
- `/axe-recon` — Survey a codebase for accessibility debt

**Tone** (Design Token Engineer)

- `/tone-recon` — Audit existing token usage in a codebase
- `/tone-theme` — Build or fix a theming system
- `/tone-token` — Design or refactor a design token architecture

**Copy** (Content Designer)

- `/copy-audit` — Audit UX copy in a product or codebase
- `/copy-recon` — Survey all user-facing strings in a codebase
- `/copy-write` — Write UX copy for a feature, flow, or component

#### Data Science Team (10 agents, 30 skills)

**Cast** (Forecasting Engineer)

- `/cast-forecast` — Build a forecasting model for a time series
- `/cast-recon` — Survey existing forecasting code or models in a codebase
- `/cast-validate` — Validate and benchmark a forecasting model

**Feat** (Feature Engineer)

- `/feat-engineer` — Design and implement a feature engineering pipeline for a ML problem
- `/feat-recon` — Audit feature engineering code for leakage, quality issues, and pipeline correctness
- `/feat-store` — Design or audit a feature store

**Fit** (Model Training Engineer)

- `/fit-recon` — Audit existing model training code
- `/fit-train` — Design a model training pipeline
- `/fit-tune` — Design a hyperparameter tuning strategy for a model

**Score** (Model Evaluation Engineer)

- `/score-compare` — Compare two or more models statistically
- `/score-eval` — Design an evaluation framework for a ML model
- `/score-recon` — Audit existing model evaluation code

**Drift** (ML Monitoring Engineer)

- `/drift-alert` — Design drift alerts and escalation
- `/drift-monitor` — Design a drift monitoring system for a production ML model
- `/drift-recon` — Audit existing ML monitoring

**Vect** (Embeddings & Vector Search Engineer)

- `/vect-embed` — Design an embedding pipeline
- `/vect-recon` — Audit existing vector search or RAG implementation
- `/vect-search` — Design a vector search or RAG system

**Tune** (LLM Fine-tuning Engineer)

- `/tune-finetune` — Design a fine-tuning pipeline
- `/tune-prompt` — Systematically optimize prompts for a task
- `/tune-recon` — Audit existing fine-tuning or prompt engineering work

**Plot** (Data Visualization Engineer)

- `/plot-chart` — Design or critique a data visualization
- `/plot-eda` — Design an exploratory data analysis workflow for a dataset
- `/plot-recon` — Audit existing visualizations in a codebase or notebook

**Clean** (Data Quality Engineer)

- `/clean-recon` — Audit existing data cleaning code
- `/clean-transform` — Design a data cleaning and transformation pipeline
- `/clean-validate` — Design a data validation pipeline

**Eval** (Experiment Design Engineer)

- `/eval-analyze` — Analyze A/B test results
- `/eval-design` — Design an A/B test
- `/eval-recon` — Audit existing experimentation infrastructure and past experiments for methodology issues

#### Security Operations Team (10 agents, 30 skills)

**Red** (Offensive Security Engineer)

- `/red-pentest` — Design a penetration testing plan
- `/red-recon` — Design a reconnaissance plan
- `/red-report` — Write a penetration test or red team finding report

**Blue** (Defensive Security Engineer)

- `/blue-detect` — Design detection rules for a threat
- `/blue-harden` — Write a hardening playbook for a system or service
- `/blue-recon` — Audit existing security controls and detection coverage

**Hunt** (Threat Hunter)

- `/hunt-assess` — Design a compromise assessment
- `/hunt-ioc` — Analyze indicators of compromise
- `/hunt-recon` — Design a threat hunting program

**Patch** (Vulnerability Management Engineer)

- `/patch-plan` — Design a vulnerability management program
- `/patch-recon` — Audit existing vulnerability management
- `/patch-triage` — Triage a set of CVEs

**Chain** (Supply Chain Security Engineer)

- `/chain-recon` — Audit existing dependency security
- `/chain-sbom` — Design an SBOM generation pipeline
- `/chain-scan` — Design a dependency scanning program

**Sast** (Application Security Engineer)

- `/sast-fix` — Analyze and fix a SAST finding
- `/sast-recon` — Audit existing application security tooling and code for OWASP Top 10 coverage
- `/sast-scan` — Design a SAST/DAST scanning pipeline

**Siem** (Detection & SIEM Engineer)

- `/siem-alert` — Tune a SIEM alert
- `/siem-recon` — Audit existing SIEM deployment
- `/siem-rule` — Write SIEM detection rules for a threat or TTP

**Resp** (Incident Response Engineer)

- `/resp-contain` — Design containment procedures for an active incident
- `/resp-playbook` — Write an incident response playbook for a threat scenario
- `/resp-recon` — Audit existing incident response capability

**Zero** (Zero Trust Architect)

- `/zero-audit` — Audit an existing environment against zero trust principles
- `/zero-design` — Design a zero trust architecture
- `/zero-recon` — Survey existing network and identity controls for zero trust readiness

**Phish** (Security Awareness Engineer)

- `/phish-assess` — Design a phishing simulation program
- `/phish-recon` — Audit existing security awareness program
- `/phish-train` — Design a security awareness training curriculum

#### Developer Experience Team (10 agents, 30 skills)

**Guide** (API Documentation Engineer)

- `/guide-audit` — Audit existing API documentation for completeness, accuracy, and developer experience
- `/guide-recon` — Survey documentation coverage across an API or SDK
- `/guide-write` — Write API reference documentation for an endpoint or SDK method

**Sample** (Code Sample Engineer)

- `/sample-recon` — Survey existing code samples
- `/sample-review` — Review existing code samples for correctness, runnability, and developer experience
- `/sample-write` — Write a working code sample or tutorial for an API feature or integration pattern

**Mock** (API Mocking & Contract Engineer)

- `/mock-contract` — Design a consumer-driven contract testing setup
- `/mock-design` — Design a mock server for an API
- `/mock-recon` — Audit existing mocks and test doubles

**Schema** (API Schema Engineer)

- `/schema-design` — Design an API schema
- `/schema-recon` — Audit existing API schemas across a codebase
- `/schema-review` — Review an API schema for consistency, completeness, and developer ergonomics

**Port** (SDK Design Engineer)

- `/port-design` — Design an SDK architecture for an API
- `/port-recon` — Audit multi-language SDK coverage
- `/port-review` — Review an existing SDK for idiomatic quality, consistency, and developer ergonomics

**Change** (Changelog & Release Communication Engineer)

- `/change-policy` — Design an API versioning and deprecation policy
- `/change-recon` — Audit existing changelog and deprecation practices
- `/change-write` — Write a changelog entry or release notes for an API version

**Onboard** (Developer Onboarding Engineer)

- `/onboard-audit` — Audit the developer onboarding experience
- `/onboard-quickstart` — Write a developer quickstart
- `/onboard-recon` — Survey existing onboarding docs and developer portal

**Bench** (API Performance Engineer)

- `/bench-compare` — Compare API performance across versions
- `/bench-profile` — Design a performance benchmark for an API
- `/bench-recon` — Audit existing performance testing

**Compat** (Backwards Compatibility Engineer)

- `/compat-audit` — Audit a proposed API change for breaking changes
- `/compat-policy` — Design an API compatibility and deprecation policy
- `/compat-recon` — Audit existing API for breaking change risks and missing compatibility controls

**Gate** (API Quality Gate Engineer)

- `/gate-ci` — Integrate API quality gates into CI
- `/gate-lint` — Design an API linting ruleset
- `/gate-recon` — Audit existing API quality controls

#### Infrastructure Specialist Team (10 agents, 30 skills)

**Kube** (Kubernetes Engineer)

- `/kube-design` — Design a Kubernetes cluster architecture
- `/kube-rbac` — Design or audit Kubernetes RBAC
- `/kube-recon` — Audit an existing Kubernetes cluster

**Terra** (Terraform Engineer)

- `/terra-drift` — Design a Terraform drift detection and remediation workflow
- `/terra-module` — Design a Terraform module structure
- `/terra-recon` — Audit existing Terraform code

**Finop** (FinOps Engineer)

- `/finop-audit` — Audit cloud spend
- `/finop-recon` — Survey existing cloud cost controls
- `/finop-reserve` — Design a reservation and savings plan strategy

**Serv** (Service Reliability Engineer)

- `/serv-cold` — Diagnose and optimize Lambda/serverless cold start performance
- `/serv-design` — Design a serverless architecture for a workload
- `/serv-recon` — Audit existing serverless functions

**Edge** (Edge Computing Engineer)

- `/edge-cdn` — Design a CDN configuration
- `/edge-recon` — Audit existing CDN and edge configuration
- `/edge-route` — Design an edge routing and geo-distribution strategy

**Cache** (Caching Engineer)

- `/cache-design` — Design a caching strategy for an application
- `/cache-evict` — Design a cache invalidation and eviction strategy
- `/cache-recon` — Audit existing caching implementation

**Queue** (Message Queue Engineer)

- `/queue-design` — Design a message queuing or streaming architecture for a workload
- `/queue-recon` — Audit existing queue and streaming infrastructure
- `/queue-scale` — Design a backpressure and scaling strategy for a queue consumer system

**Mesh** (Service Mesh Engineer)

- `/mesh-design` — Design a service mesh deployment
- `/mesh-observe` — Design service mesh observability
- `/mesh-recon` — Audit existing service mesh configuration

**Multi** (Multi-Cloud Engineer)

- `/multi-design` — Design a multi-cloud or cloud portability strategy
- `/multi-port` — Assess and improve cloud portability
- `/multi-recon` — Survey existing cloud architecture for lock-in depth and portability gaps

**Chaos** (Chaos Engineering Lead)

- `/chaos-design` — Design a chaos engineering experiment
- `/chaos-game` — Design a game day
- `/chaos-recon` — Audit existing resilience

#### AI Operations Team (9 agents, 29 skills)

**Deploy** (AI Deployment Engineer)

- `/deploy-canary` — Plan and execute canary releases for model updates
- `/deploy-recon` — Audit current model deployment topology
- `/deploy-serve` — Design and configure model serving infrastructure

**Evals** (LLM Evaluation Engineer)

- `/evals-analyze` — Analyze LLM eval results
- `/evals-design` — Design an LLM eval
- `/evals-harness` — Design eval harnesses
- `/evals-recon` — Audit existing eval coverage
- `/evals-regress` — Build automated regression suites

**Trace** (LLM Observability Engineer)

- `/trace-debug` — Debug AI system behavior using traces
- `/trace-instrument` — Instrument LLM calls with tracing
- `/trace-recon` — Audit LLM observability coverage

**Guard** (AI Guardrails Engineer)

- `/guard-audit` — Audit guardrail coverage
- `/guard-design` — Design guardrail layers
- `/guard-recon` — Map current AI safety controls

**Budget** (AI Cost Engineer)

- `/budget-audit` — Audit AI spend
- `/budget-optimize` — Design cost reduction strategies
- `/budget-recon` — Map AI cost topology

**Token** (Token Management Engineer)

- `/token-budget` — Design token budgets
- `/token-chunk` — Design chunking strategies
- `/token-recon` — Audit token usage patterns

**Prompt** (Prompt Engineer)

- `/prompt-design` — Design production prompts
- `/prompt-recon` — Audit prompt library
- `/prompt-version` — Build prompt versioning systems

**Embed** (Embeddings Engineer)

- `/embed-design` — Design embedding pipelines
- `/embed-recon` — Audit embedding infrastructure
- `/embed-search` — Optimize similarity search

**Rank** (AI Ranking Engineer)

- `/rank-design` — Design ranking pipelines
- `/rank-eval` — Build ranking evaluation
- `/rank-recon` — Audit ranking quality

</details>

## Roadmap

| Phase                                     | Status | What it covers                                      |
| ----------------------------------------- | ------ | --------------------------------------------------- |
| **Engineering** (15 agents)               | Done   | Build, ship, operate                                |
| **Product** (12 agents)                   | Done   | Research, strategy, design, growth                  |
| **Operations** (4 agents)                 | Done   | Finance, people, ops, support                       |
| **Legal** (10 agents)                     | Done   | Contracts, compliance, governance, IP, filings      |
| **Design** (10 agents)                    | Done   | Color, layout, typography, motion, accessibility    |
| **Data Science** (10 agents)              | Done   | Forecasting, feature engineering, evaluation, drift |
| **Security Operations** (10 agents)       | Done   | Red/blue team, threat hunting, IR, zero trust       |
| **Developer Experience** (10 agents)      | Done   | API docs, SDKs, mocking, versioning, quality gates  |
| **Infrastructure Specialist** (10 agents) | Done   | Kubernetes, Terraform, FinOps, mesh, chaos          |
| **AI Operations** (9 agents)              | Done   | Model serving, evals, guardrails, cost, ranking     |

## Contributing

Everything is Markdown. Fork it, improve it, open a PR. Agents are system prompts. Skills are workflow docs. No build step.

See [CONTRIBUTING.md](CONTRIBUTING.md) to get started. The highest-leverage contributions right now:

- **Sharpen existing skills** — better steps, sharper output formats, fewer hallucinations
- **Build a new agent** — extend the roster with a domain not yet covered
- **Test on real codebases** — try `/apex-takeover` on a production repo and file what breaks

Tests run with `uv run pytest` from any agent's `scripts/` directory.

| Doc                                  | Covers                                               |
| ------------------------------------ | ---------------------------------------------------- |
| [Architecture](docs/architecture.md) | How the plugin system works                          |
| [Skill Guide](docs/skill-guide.md)   | Writing and improving skills                         |
| [Agent Guide](docs/agent-guide.md)   | Creating new agents                                  |
| [Naming Guide](docs/naming-guide.md) | Agent naming conventions                             |
| [Repomap](docs/repomap.md)           | Orientation map for this repo — indexes, known drift |

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full release history.

## Shoutouts

Tonone stands on the shoulders of giants. Big thanks to the plugins that shaped how this team thinks and works:

| Plugin              | What it brought                                                                                                                                                                                                                          |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **superpowers**     | Structured skill workflows, brainstorming loops, TDD discipline, and the worktree-native development model that Tonone runs on                                                                                                           |
| **impeccable**      | Design critique vocabulary and the polish-first mindset baked into Form and Draft                                                                                                                                                        |
| **frontend-design** | Frontend implementation patterns that Prism and Touch draw from                                                                                                                                                                          |
| **ui-ux-pro-max**   | 161 color palettes, 84 UI styles, 57 font pairings, 99 UX guidelines, and the BM25 design search engine now powering `lib/uiux`                                                                                                          |
| **caveman**         | The communication mode that cuts every response to its bones — no fluff, all signal                                                                                                                                                      |
| **open-design**     | 19 design skills and the I-Lang brief protocol that power `form-brief`, the hand-drawn wireframe mode in `draft-wireframe`, and the HTML radar report in `form-critique` — [nexu-io/open-design](https://github.com/nexu-io/open-design) |

## License

MIT. Fork it. Ship it. Use it anywhere. [LICENSE](LICENSE)

---

> README maintained automatically by [🐘 elephant](https://github.com/tonone-ai/elephant) — keep your docs in sync without the manual work.
