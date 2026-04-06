# Tonone

**Engineering + product, second to none.**

Your elite AI team as [Claude Code](https://docs.anthropic.com/en/docs/claude-code) agents. 2 leads + 21 specialists. 125 skills. Every major engineering and product discipline covered.

Simple by default. Scalable by design.

## Why This Exists

Right now, everyone gets a generalized AI assistant. Engineers, product managers, designers, strategists — all prompting separately, getting separate outputs, then copying results into Slack threads for the next person to feed back into AI. It's a relay race where every handoff loses context.

**That's the wrong unit of automation.** Instead of giving each person an AI assistant, give the whole company an AI team. Specialists that talk to each other, share context, and run the show end to end — from user research to infrastructure to deployment — without the copy-paste relay.

That's Tonone. Not twenty-three copies of the same generalist. Twenty-three specialists, each owning one domain, coordinated by leads who know when to call who and at what depth.

### The Mindset

**Complexity is debt.** Every unnecessary abstraction, every over-engineered solution, every "just in case" feature — it all accrues interest. It slows you down today and buries you tomorrow.

**Scalability compounds.** When you build simple, correct foundations, they carry more weight over time without breaking. Simple systems are easier to debug, easier to extend, and easier to hand off.

No boilerplate generators. No tutorial-grade scaffolds. Production-ready output that respects your codebase, your stack, and your time.

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

### Product — 8 agents

| Agent     | Hat               | What They Do                                                    |
| --------- | ----------------- | --------------------------------------------------------------- |
| **Helm**  | Head of Product   | Orchestrates the product team, writes briefs, hands off to Apex |
| **Echo**  | User Research     | User interviews, personas, Jobs-to-Be-Done, feedback synthesis  |
| **Lumen** | Product Analytics | Metrics frameworks, funnel analysis, OKRs, A/B test design      |
| **Draft** | UX Design         | User flows, information architecture, wireframes                |
| **Form**  | Visual Design     | Brand identity, color systems, typography, design system        |
| **Crest** | Product Strategy  | Roadmap planning, prioritization, competitive analysis          |
| **Pitch** | Product Marketing | Positioning, messaging, value prop, GTM, launch copy            |
| **Surge** | Growth            | Acquisition channels, activation funnels, retention playbooks   |

## Quick Start

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed (v1.0+)

### Install

```
/plugin marketplace add tonone-ai/tonone
/plugin install tonone@tonone-ai
```

### Then just talk to them

```
> /apex-plan Build a real-time analytics platform for our IoT fleet
> /helm-brief Define the next product sprint
> /forge-infra Set up cloud infrastructure for a new SaaS product
> /spine-api Design a REST API for user management
> /warden-audit Run a full security audit on this codebase
> /echo-interview Run a user research session
> /crest-roadmap Build a product roadmap
```

## What You Get

Every agent can **build**, **review**, and **recon**:

| Mode       | What It Means                                         | Example Skills                                                  |
| ---------- | ----------------------------------------------------- | --------------------------------------------------------------- |
| **Build**  | Create from scratch — production-ready, not tutorials | `/forge-infra`, `/spine-api`, `/prism-ui`, `/touch-app`         |
| **Review** | Audit and fix existing systems                        | `/warden-audit`, `/relay-audit`, `/prism-audit`, `/vigil-check` |
| **Recon**  | Survey a domain for system takeover                   | `/forge-recon`, `/spine-recon`, `/flux-recon`, `/apex-takeover` |

### Platform-Aware

Every engineering agent detects your stack and adapts:

- **Cloud:** GCP, AWS, Azure, Cloudflare, Vercel, Fly.io, Hetzner, DigitalOcean
- **CI/CD:** GitHub Actions, GitLab CI, Cloud Build, CircleCI, Bitbucket Pipelines
- **Backend:** Node.js, Python, Go, Rust, Java/Kotlin, Ruby
- **Databases:** PostgreSQL, MySQL, MongoDB, Redis, BigQuery, Snowflake, Supabase, Planetscale
- **Frontend:** React/Next.js, Vue/Nuxt, Svelte/SvelteKit, Astro
- **Mobile:** Swift/SwiftUI, Kotlin/Compose, React Native, Flutter
- **ML:** PyTorch, scikit-learn, Vertex AI, SageMaker, OpenAI, Anthropic

### The Leads

**Apex** is the engineering lead. Give it a task, it figures out who to involve and at what depth:

```
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

### System Takeover

Inherited a codebase? Apex runs parallel reconnaissance across all specialists:

```
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

## All 125 Skills

<details>
<summary>Click to expand full skill list</summary>

### Apex (Engineering Lead)

- `/apex-plan` — Plan and scope a project with S/M/L options
- `/apex-review` — Cross-cutting review of recent work
- `/apex-status` — CTO-level project status
- `/apex-recon` — Engineering reconnaissance
- `/apex-takeover` — System takeover with parallel recon

### Forge (Infrastructure)

- `/forge-infra` — Build infrastructure from scratch
- `/forge-network` — Design and build networking
- `/forge-audit` — Audit existing infrastructure
- `/forge-cost` — Estimate and optimize infrastructure cost
- `/forge-diagnose` — Diagnose runtime infra issues
- `/forge-recon` — Infrastructure reconnaissance

### Relay (DevOps)

- `/relay-pipeline` — Build CI/CD pipeline from scratch
- `/relay-docker` — Build production Dockerfiles
- `/relay-deploy` — Set up deployment strategy
- `/relay-audit` — Audit existing pipeline
- `/relay-recon` — Pipeline reconnaissance

### Spine (Backend)

- `/spine-api` — Design and build an API
- `/spine-service` — Build a new service from scratch
- `/spine-design` — System design
- `/spine-perf` — Find and fix performance bottlenecks
- `/spine-review` — API and code review
- `/spine-recon` — Backend reconnaissance

### Flux (Data)

- `/flux-schema` — Design and build database schema
- `/flux-migrate` — Build zero-downtime migration
- `/flux-pipeline` — Build a data pipeline
- `/flux-query` — Optimize slow queries
- `/flux-health` — Data quality and pipeline health
- `/flux-recon` — Database reconnaissance

### Warden (Security)

- `/warden-audit` — Full security audit
- `/warden-harden` — Harden a service
- `/warden-iam` — Build IAM from scratch
- `/warden-threat` — Threat model a system
- `/warden-recon` — Security reconnaissance

### Vigil (Observability + Reliability)

- `/vigil-instrument` — Instrument a service
- `/vigil-alert` — Build alerting and runbooks
- `/vigil-incident` — Incident response
- `/vigil-check` — Verify observability posture
- `/vigil-recon` — Observability reconnaissance

### Prism (Frontend/DX)

- `/prism-ui` — Build a UI from scratch
- `/prism-component` — Build a reusable component
- `/prism-dashboard` — Build an internal dashboard
- `/prism-audit` — Frontend audit
- `/prism-recon` — Frontend reconnaissance

### Cortex (ML/AI)

- `/cortex-model` — Build an ML pipeline
- `/cortex-prompt` — Build and test prompts
- `/cortex-integrate` — Integrate LLM into a service
- `/cortex-eval` — Evaluate model performance
- `/cortex-recon` — ML reconnaissance

### Touch (Mobile)

- `/touch-app` — Build mobile app from scratch
- `/touch-feature` — Build a mobile feature
- `/touch-release` — Set up mobile release pipeline
- `/touch-audit` — Mobile audit
- `/touch-recon` — Mobile reconnaissance

### Volt (Embedded/IoT)

- `/volt-firmware` — Build firmware from scratch
- `/volt-driver` — Build device driver or protocol handler
- `/volt-ota` — Build OTA update system
- `/volt-power` — Power management and optimization
- `/volt-recon` — Firmware reconnaissance

### Atlas (Knowledge)

- `/atlas-map` — Map the system architecture
- `/atlas-adr` — Write an Architecture Decision Record
- `/atlas-onboard` — Generate onboarding documentation
- `/atlas-report` — Render findings as styled HTML reports in browser
- `/atlas-changelog` — Three-layer changelog management (per-repo, cross-repo, per-agent)
- `/atlas-present` — Release presentations as HTML + Obsidian Canvas
- `/atlas-recon` — Documentation reconnaissance

### Lens (Analytics/BI)

- `/lens-dashboard` — Build an analytical dashboard
- `/lens-metrics` — Define and implement metrics framework
- `/lens-report` — Build a reporting pipeline
- `/lens-audit` — Review existing analytics
- `/lens-recon` — Analytics reconnaissance

### Proof (QA & Testing)

- `/proof-strategy` — Design a test strategy for a project
- `/proof-e2e` — Build E2E test suites with Playwright/Cypress
- `/proof-api` — Build API test suites
- `/proof-audit` — Audit test suite health
- `/proof-recon` — Testing reconnaissance

### Pave (Platform Engineering)

- `/pave-golden` — Build golden path templates
- `/pave-env` — Set up local development environments
- `/pave-catalog` — Build a service catalog
- `/pave-audit` — Audit developer experience
- `/pave-recon` — Platform reconnaissance

### Helm (Head of Product)

- `/helm-plan` — Plan a product sprint or initiative
- `/helm-brief` — Write a structured product brief for Apex
- `/helm-handoff` — End-to-end Helm → Apex delivery
- `/helm-arbiter` — Resolve product vs. engineering tension
- `/helm-recon` — Product reconnaissance

### Echo (User Research)

- `/echo-interview` — Run a structured user interview
- `/echo-feedback` — Synthesize user feedback
- `/echo-segment` — Define user segments and personas
- `/echo-jobs` — Map Jobs-to-Be-Done
- `/echo-recon` — Research reconnaissance

### Lumen (Product Analytics)

- `/lumen-metrics` — Define a metrics framework
- `/lumen-funnel` — Analyze and improve a funnel
- `/lumen-abtest` — Design an A/B test
- `/lumen-instrument` — Instrument product analytics
- `/lumen-recon` — Analytics reconnaissance

### Draft (UX Design)

- `/draft-wireframe` — Wireframe a flow or screen
- `/draft-flow` — Map a user flow end to end
- `/draft-ia` — Design information architecture
- `/draft-review` — Review a design for UX quality
- `/draft-recon` — UX reconnaissance

### Form (Visual Design)

- `/form-brand` — Define or audit brand identity
- `/form-logo` — Design a logo system
- `/form-tokens` — Build a design token system
- `/form-component` — Specify UI components
- `/form-web` — Design a web interface
- `/form-mobile` — Design a mobile screen
- `/form-email` — Design an email template
- `/form-social` — Design social and ad creatives
- `/form-audit` — Audit visual quality and consistency
- `/form-deck` — Design a presentation deck

### Crest (Product Strategy)

- `/crest-roadmap` — Build a product roadmap
- `/crest-okr` — Define OKRs for a team or product
- `/crest-compete` — Competitive analysis
- `/crest-narrative` — Write a strategic narrative
- `/crest-recon` — Strategy reconnaissance

### Pitch (Product Marketing)

- `/pitch-position` — Define positioning and value prop
- `/pitch-message` — Write core messaging
- `/pitch-copy` — Write launch copy
- `/pitch-launch` — Plan a product launch
- `/pitch-recon` — Marketing reconnaissance

### Surge (Growth)

- `/surge-activation` — Design an activation funnel
- `/surge-plg` — Build a PLG strategy
- `/surge-experiment` — Design a growth experiment
- `/surge-retention` — Build a retention playbook
- `/surge-recon` — Growth reconnaissance

</details>

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) to get started — improve skills, propose agents, or fix bugs.

| Doc                                  | Covers                       |
| ------------------------------------ | ---------------------------- |
| [Architecture](docs/architecture.md) | How the plugin system works  |
| [Skill Guide](docs/skill-guide.md)   | Writing and improving skills |
| [Agent Guide](docs/agent-guide.md)   | Creating new agents          |
| [Naming Guide](docs/naming-guide.md) | Agent naming conventions     |

## License

MIT — see [LICENSE](LICENSE)
