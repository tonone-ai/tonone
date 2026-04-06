# Tonone Roadmap

Tonone is an open source Claude Code plugin that gives you a full company of specialized AI agents. Each department is a self-contained expansion — install only what you need.

Current version: **v0.6.0**
Agents: **23** (Engineering + Product teams)
Skills: **125**

---

## Now — Stability and Quality (v0.5)

The foundation is built. Next focus is making it solid enough for contributors to extend.

**Agent Quality**

- [ ] Audit all 77 skill definitions for accuracy and completeness
- [ ] Standardize skill frontmatter (name, description, trigger conditions)
- [ ] Remove redundant or overlapping skills between agents

**Plugin Reliability**

- [ ] Add CI — smoke test that all skills load and parse correctly
- [ ] Lint skill YAML/Markdown on every push
- [ ] Fix any remaining agent routing gaps (wrong agent gets invoked)

**Documentation**

- [ ] Each agent: clear description of what it does and when to use it
- [ ] Getting started guide — from zero to first agent invoked
- [ ] Contribution guide — how to add or improve a skill

**Release: v0.5.0**

---

## Next — Stability and Community (v1.0)

Both teams are shipped. Next focus is making the foundation solid enough for contributors to extend confidently.

**Quality**

- [ ] Audit all 125 skill definitions for accuracy and completeness
- [ ] Standardize skill frontmatter (name, description, trigger conditions)
- [ ] Remove redundant or overlapping skills between agents

**Plugin Reliability**

- [ ] Add CI — smoke test that all skills load and parse correctly
- [ ] Lint skill YAML/Markdown on every push
- [ ] Fix any remaining agent routing gaps (wrong agent gets invoked)
- [ ] `bundle/product-team/` install script
- [ ] `bundle/full-team/` — engineering + product in one install

**Release: v1.0.0** — Two teams. 23 agents. 125 skills. Stable, documented, community-ready.

---

## Expansion Phases

Each phase adds one department as an installable bundle. Teams are independent — install Revenue without Finance, or everything at once.

---

### Phase 1 — Revenue (v1.1)

_Turn product into money. The loop that matters most after product-market fit._

| Agent      | Role                                                    |
| ---------- | ------------------------------------------------------- |
| **Arc**    | Revenue lead — orchestrates the team, owns pipeline     |
| **Scout**  | BizDev — prospects, qualifies, sources deals            |
| **Close**  | Sales — pipeline management, negotiations, deal closing |
| **Keep**   | Customer Success — retention, expansion, NPS            |
| **Bridge** | Partnerships — ISV integrations, resellers, ecosystem   |

**Adds:** 5 agents → 28 total
**Bundle:** `bundle/revenue-team/`

---

### Phase 2 — Marketing (v1.2)

_Build the audience, tell the story, generate demand._

| Agent      | Role                                                                   |
| ---------- | ---------------------------------------------------------------------- |
| **Signal** | PR & Comms — press, media, brand voice, analyst briefings              |
| **Quill**  | Content — blog, SEO, docs, thought leadership                          |
| **Grove**  | Community & DevRel — OSS community, Discord, contributors, conferences |
| **Spark**  | Demand Gen — paid acquisition, campaigns, ABM, lead nurturing          |

**Adds:** 4 agents → 32 total
**Bundle:** `bundle/marketing-team/`

---

### Phase 3 — Finance & Legal (v1.3)

_Keep the lights on. Stay solvent. Don't go to jail._

| Agent      | Role                                                      |
| ---------- | --------------------------------------------------------- |
| **Vault**  | Finance — modeling, runway, budgeting, investor reporting |
| **Tally**  | Accounting — books, invoices, expense tracking, tax prep  |
| **Clause** | Legal — contracts, IP, entity management, compliance      |

**Adds:** 3 agents → 35 total
**Bundle:** `bundle/finance-legal-team/`

---

### Phase 4 — People (v1.4)

_Hire well. Keep people. Build culture._

| Agent    | Role                                                 |
| -------- | ---------------------------------------------------- |
| **Crew** | Recruiting — sourcing, screening, offers, onboarding |
| **Mesh** | People Ops — culture, performance, policies, comp    |

**Adds:** 2 agents → 37 total
**Bundle:** `bundle/people-team/`

---

### Phase 5 — Operations (v1.5)

_Make the trains run. Remove friction from how work moves._

| Agent    | Role                                                              |
| -------- | ----------------------------------------------------------------- |
| **Keel** | Ops lead — cross-team execution, OKR tracking, program management |
| **Grid** | Systems — SaaS stack, integrations, tools, vendor management      |
| **Flow** | Process — SOPs, workflow automation, operational efficiency       |

**Adds:** 3 agents → 40 total
**Bundle:** `bundle/operations-team/`

---

### Phase 6 — Support (v1.6)

_Handle what happens after the sale._

| Agent    | Role                                                                      |
| -------- | ------------------------------------------------------------------------- |
| **Port** | Customer Support — inbound tickets, escalations, knowledge base, Tier 1/2 |

**Adds:** 1 agent → 41 total
**Bundle:** `bundle/support-team/`

---

### Phase 7 — Strategy & Board (v1.7)

_Set company direction. Pressure-test major decisions._

| Agent     | Role                                                                                                         |
| --------- | ------------------------------------------------------------------------------------------------------------ |
| **North** | Company orchestrator — direction, OKRs, stakeholder comms, coordinates all team leads                        |
| **Bench** | Board simulator — adversarial review of major decisions from financial, strategic, customer, and risk lenses |

**Adds:** 2 agents → 43 total
**Bundle:** `bundle/strategy-board/`

---

## Full Company

When all phases are complete:

```
Bench (Board)
│
North (Strategy)
├── Apex     Engineering  →  14 specialists
├── Helm     Product      →   7 specialists
├── Arc      Revenue      →   4 specialists
├── Signal   Marketing    →   3 specialists
├── Vault    Finance      →   2 specialists
├── Crew     People       →   1 specialist
├── Keel     Operations   →   2 specialists
├── Port     Support
└── (Clause, Grove, Spark as cross-team)
```

**43 agents. One install.**
`claude mcp add tonone` — full company in your terminal.

---

## What We're Not Building

To stay focused:

- No web UI in this repo (that's tonone.ai — separate)
- No database, auth, or payment logic (plugin stays stateless)
- No agent that requires proprietary APIs — everything runs with a Claude API key
- No management titles (COO, CFO, CMO) — agents represent functions, not org chart positions

---

## Contributing

See [CLAUDE.md](CLAUDE.md) for how agents and skills are structured.
Each agent lives in `agents/`. Each skill is a Markdown file in `team/<agent>/skills/`.

Open an issue before building a new agent — we want to make sure it fits the system.
