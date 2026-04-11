# Communication Protocol Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate compressed communication across all 23 tonone agents and 125 skills — upgrade output-kit, add communication reinforcement, compress prose bodies.

**Architecture:** Output-kit.md is the single source of truth for communication protocol. Each agent def gets a compact inline reinforcement. All agent/skill prose compressed following consistent rules. Team-local copies synced per batch.

**Tech Stack:** Markdown only. No code changes. Text transformation + file sync.

**Spec:** `docs/superpowers/specs/2026-04-11-communication-protocol-design.md`

---

## Compression Rules (Reference for All Tasks)

Apply these when compressing any agent def or skill prose:

1. Drop articles (a/an/the) where meaning preserved
2. Drop filler words: just, really, basically, actually, simply, certainly, perhaps
3. Drop pleasantries: "Sure, I'd be happy to", "Great question"
4. Drop hedging: "It might be worth", "You could potentially", "It would be good to"
5. Drop throat-clearing: "Let me take a look at", "What I'm seeing here is"
6. Drop redundant phrasing: "in order to" → "to", "make sure to" → state it directly
7. Use short synonyms: "fix" not "implement a solution for", "use" not "utilize"
8. Fragments OK: "Monolith that works beats microservices that don't."
9. Pattern: `[thing] [action] [reason]. [next step].`

**DO NOT compress:**

- YAML frontmatter (name, description, model, allowed-tools, version, author, license)
- Code blocks (`...`)
- Table content (headers, rows, cell values)
- Format examples and templates
- File paths, URLs, commands
- Technical terms (keep exact)
- Anti-patterns sections (already terse, high-value)

**DO preserve:**

- Agent personality/voice — each agent has distinct tone
- All rules and key rules (meaning must be identical, words can be fewer)
- Section headers and structure
- Mermaid/PlantUML diagrams

---

## Chunk 1: Foundation

### Task 1: Upgrade output-kit.md Communication Protocol

**Files:**

- Modify: `docs/output-kit.md:80-103`

- [ ] **Step 1: Read current Language Rules section**

Read `docs/output-kit.md` lines 80-103.

- [ ] **Step 2: Replace "Language Rules" section with expanded "Communication Protocol"**

Replace the section starting at `## Language Rules` (line 80) through line 103 with:

```markdown
## Communication Protocol

Applies to all agent output: conversation, CLI, reports, skill responses. Not just CLI formatting — this governs how every agent communicates.

**Active every response.** No revert after many turns. No filler drift. If unsure whether still active: it is.

Write like an elite engineer who has no time to waste. Technical accuracy is non-negotiable. Filler is.

**Kill on sight:**

- Pleasantries: "Sure, I'd be happy to", "Great question", "Certainly"
- Hedging: "It might be worth considering", "You could potentially", "It would be good to"
- Filler articles: a, an, the (where removal doesn't change meaning)
- Redundant phrasing: "in order to" → "to", "make sure to" → just state it, "the reason is because" → "because"
- Throat-clearing: "Let me take a look at", "I'll go ahead and", "What I'm seeing here is"

**Keep exact:**

- Technical terms (polymorphism stays polymorphism, IAM stays IAM)
- Error messages and stack traces (quoted verbatim)
- Code, commands, file paths, URLs — never modify these

**Pattern:** `[thing] [action] [result]. [next].`

Not: _"I'd recommend that you consider implementing rate limiting on the auth endpoint, as this would help prevent potential brute-force attacks."_
Yes: _"No rate limiting on auth endpoint. Brute-force risk. Add `express-rate-limit` with 10 req/min."_

Fragments are fine. Short synonyms preferred: "fix" not "implement a solution for", "use" not "utilize", "big" not "extensive".

**Auto-clarity exceptions** — drop compressed style for:

- Security warnings and irreversible action confirmations
- Multi-step sequences where fragment order risks misread
- User confused or repeating question

Resume compressed style after clear part done.

**Boundaries** — always normal English for:

- Code blocks, commits, PR descriptions
- Documentation files (README, CHANGELOG, ADRs)
- Error messages quoted verbatim
```

- [ ] **Step 3: Verify output-kit structure intact**

Read full `docs/output-kit.md`. Confirm all other sections unchanged: The 40-Line Rule, CLI Skeleton, Severity Indicators, Tables, Formatting Rules, Browser-First Reporting, Progressive Disclosure, Skill Integration.

- [ ] **Step 4: Commit**

```bash
git add docs/output-kit.md
git commit -m "docs: upgrade output-kit Language Rules to Communication Protocol"
```

---

### Task 2: Update Atlas agent def — ownership + compression

**Files:**

- Modify: `agents/atlas.md`
- Modify: `team/atlas/agents/atlas.md`

This task sets the pattern for all other agent compressions.

- [ ] **Step 1: Read Atlas agent def**

Read `agents/atlas.md` in full.

- [ ] **Step 2: Add Communication section after opening paragraph, before Operating Principle**

Insert after the opening role description paragraph (before `## Operating Principle`):

```markdown
## Communication

Respond terse. All technical substance stays — only filler dies. Follow output-kit protocol: compressed prose, no filler, fragments OK. Code/security/commits: normal English. See docs/output-kit.md for CLI skeleton, severity indicators, 40-line rule.
```

- [ ] **Step 3: Add Communication Protocol ownership to Output Architecture section**

In the `## Output Architecture` section, add this line after the existing bullet list:

```markdown
- **Communication Protocol** (in `docs/output-kit.md` § Communication Protocol) — compressed prose rules all agents follow for all output: conversation, CLI, reports, skill responses
```

- [ ] **Step 4: Compress Atlas prose**

Apply compression rules to all prose in the file. Examples of what changes:

Before: "You are Atlas — the knowledge engineer on the Engineering Team. You think in systems, connections, and clarity. You map the terrain so the team can navigate it. A system that nobody can understand is a system nobody can maintain."
After: "You are Atlas — knowledge engineer. Think in systems, connections, clarity. Map terrain so team navigates it. System nobody understands is system nobody maintains."

Before: "You're not a technical writer — you're the engineer who makes institutional knowledge durable, navigable, and alive."
After: "Not a technical writer — engineer who makes institutional knowledge durable, navigable, alive."

Do NOT compress: frontmatter, Diátaxis table content, code blocks, section headers.

- [ ] **Step 5: Copy to team mirror**

```bash
cp agents/atlas.md team/atlas/agents/atlas.md
```

- [ ] **Step 6: Commit**

```bash
git add agents/atlas.md team/atlas/agents/atlas.md
git commit -m "docs(atlas): add communication protocol ownership + compress prose"
```

---

## Chunk 2: Remaining Agent Definitions (22 agents)

All tasks in this chunk are **independent and parallelizable**. Each follows the same pattern as Task 2 (Atlas), minus the ownership line.

For each agent: read → add Communication section → compress prose → copy to team mirror.

The Communication section is identical for all agents:

```markdown
## Communication

Respond terse. All technical substance stays — only filler dies. Follow output-kit protocol: compressed prose, no filler, fragments OK. Code/security/commits: normal English. See docs/output-kit.md for CLI skeleton, severity indicators, 40-line rule.
```

Insert after the opening role paragraph, before `## Operating Principle`.

### Task 3: Compress apex.md

**Files:**

- Modify: `agents/apex.md`
- Modify: `team/apex/agents/apex.md`

- [ ] **Step 1:** Read `agents/apex.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose (drop articles, filler, hedging). DO NOT compress: frontmatter, team roster table, S/M/L format example, Helm handoff schema, code blocks, usage receipt template
- [ ] **Step 4:** `cp agents/apex.md team/apex/agents/apex.md`
- [ ] **Step 5:** Commit: `git add agents/apex.md team/apex/agents/apex.md && git commit -m "docs(apex): add communication protocol + compress prose"`

### Task 4: Compress cortex.md

**Files:**

- Modify: `agents/cortex.md`
- Modify: `team/cortex/agents/cortex.md`

- [ ] **Step 1:** Read `agents/cortex.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, decision tree tables, code blocks, architecture patterns
- [ ] **Step 4:** `cp agents/cortex.md team/cortex/agents/cortex.md`
- [ ] **Step 5:** Commit: `git add agents/cortex.md team/cortex/agents/cortex.md && git commit -m "docs(cortex): add communication protocol + compress prose"`

### Task 5: Compress crest.md

**Files:**

- Modify: `agents/crest.md`
- Modify: `team/crest/agents/crest.md`

- [ ] **Step 1:** Read `agents/crest.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, framework tables, code blocks
- [ ] **Step 4:** `cp agents/crest.md team/crest/agents/crest.md`
- [ ] **Step 5:** Commit: `git add agents/crest.md team/crest/agents/crest.md && git commit -m "docs(crest): add communication protocol + compress prose"`

### Task 6: Compress draft.md

**Files:**

- Modify: `agents/draft.md`
- Modify: `team/draft/agents/draft.md`

- [ ] **Step 1:** Read `agents/draft.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, tables, wireframe examples
- [ ] **Step 4:** `cp agents/draft.md team/draft/agents/draft.md`
- [ ] **Step 5:** Commit: `git add agents/draft.md team/draft/agents/draft.md && git commit -m "docs(draft): add communication protocol + compress prose"`

### Task 7: Compress echo.md

**Files:**

- Modify: `agents/echo.md`
- Modify: `team/echo/agents/echo.md`

- [ ] **Step 1:** Read `agents/echo.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, interview templates, tables
- [ ] **Step 4:** `cp agents/echo.md team/echo/agents/echo.md`
- [ ] **Step 5:** Commit: `git add agents/echo.md team/echo/agents/echo.md && git commit -m "docs(echo): add communication protocol + compress prose"`

### Task 8: Compress flux.md

**Files:**

- Modify: `agents/flux.md`
- Modify: `team/flux/agents/flux.md`

- [ ] **Step 1:** Read `agents/flux.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, SQL examples, migration templates, tables
- [ ] **Step 4:** `cp agents/flux.md team/flux/agents/flux.md`
- [ ] **Step 5:** Commit: `git add agents/flux.md team/flux/agents/flux.md && git commit -m "docs(flux): add communication protocol + compress prose"`

### Task 9: Compress forge.md

**Files:**

- Modify: `agents/forge.md`
- Modify: `team/forge/agents/forge.md`

- [ ] **Step 1:** Read `agents/forge.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, IaC examples, tables
- [ ] **Step 4:** `cp agents/forge.md team/forge/agents/forge.md`
- [ ] **Step 5:** Commit: `git add agents/forge.md team/forge/agents/forge.md && git commit -m "docs(forge): add communication protocol + compress prose"`

### Task 10: Compress form.md

**Files:**

- Modify: `agents/form.md`
- Modify: `team/form/agents/form.md`

- [ ] **Step 1:** Read `agents/form.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, design token examples, color specs, tables
- [ ] **Step 4:** `cp agents/form.md team/form/agents/form.md`
- [ ] **Step 5:** Commit: `git add agents/form.md team/form/agents/form.md && git commit -m "docs(form): add communication protocol + compress prose"`

### Task 11: Compress helm.md

**Files:**

- Modify: `agents/helm.md`
- Modify: `team/helm/agents/helm.md`

- [ ] **Step 1:** Read `agents/helm.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, brief schema template, tables
- [ ] **Step 4:** `cp agents/helm.md team/helm/agents/helm.md`
- [ ] **Step 5:** Commit: `git add agents/helm.md team/helm/agents/helm.md && git commit -m "docs(helm): add communication protocol + compress prose"`

### Task 12: Compress lens.md

**Files:**

- Modify: `agents/lens.md`
- Modify: `team/lens/agents/lens.md`

- [ ] **Step 1:** Read `agents/lens.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, dashboard examples, tables
- [ ] **Step 4:** `cp agents/lens.md team/lens/agents/lens.md`
- [ ] **Step 5:** Commit: `git add agents/lens.md team/lens/agents/lens.md && git commit -m "docs(lens): add communication protocol + compress prose"`

### Task 13: Compress lumen.md

**Files:**

- Modify: `agents/lumen.md`
- Modify: `team/lumen/agents/lumen.md`

- [ ] **Step 1:** Read `agents/lumen.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, metrics framework tables, A/B test templates
- [ ] **Step 4:** `cp agents/lumen.md team/lumen/agents/lumen.md`
- [ ] **Step 5:** Commit: `git add agents/lumen.md team/lumen/agents/lumen.md && git commit -m "docs(lumen): add communication protocol + compress prose"`

### Task 14: Compress pave.md

**Files:**

- Modify: `agents/pave.md`
- Modify: `team/pave/agents/pave.md`

- [ ] **Step 1:** Read `agents/pave.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, golden path templates, tables
- [ ] **Step 4:** `cp agents/pave.md team/pave/agents/pave.md`
- [ ] **Step 5:** Commit: `git add agents/pave.md team/pave/agents/pave.md && git commit -m "docs(pave): add communication protocol + compress prose"`

### Task 15: Compress pitch.md

**Files:**

- Modify: `agents/pitch.md`
- Modify: `team/pitch/agents/pitch.md`

- [ ] **Step 1:** Read `agents/pitch.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, messaging frameworks, tables
- [ ] **Step 4:** `cp agents/pitch.md team/pitch/agents/pitch.md`
- [ ] **Step 5:** Commit: `git add agents/pitch.md team/pitch/agents/pitch.md && git commit -m "docs(pitch): add communication protocol + compress prose"`

### Task 16: Compress prism.md

**Files:**

- Modify: `agents/prism.md`
- Modify: `team/prism/agents/prism.md`

- [ ] **Step 1:** Read `agents/prism.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, component examples, tables
- [ ] **Step 4:** `cp agents/prism.md team/prism/agents/prism.md`
- [ ] **Step 5:** Commit: `git add agents/prism.md team/prism/agents/prism.md && git commit -m "docs(prism): add communication protocol + compress prose"`

### Task 17: Compress proof.md

**Files:**

- Modify: `agents/proof.md`
- Modify: `team/proof/agents/proof.md`

- [ ] **Step 1:** Read `agents/proof.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, test strategy tables, code blocks
- [ ] **Step 4:** `cp agents/proof.md team/proof/agents/proof.md`
- [ ] **Step 5:** Commit: `git add agents/proof.md team/proof/agents/proof.md && git commit -m "docs(proof): add communication protocol + compress prose"`

### Task 18: Compress relay.md

**Files:**

- Modify: `agents/relay.md`
- Modify: `team/relay/agents/relay.md`

- [ ] **Step 1:** Read `agents/relay.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, CI/CD pipeline examples, tables
- [ ] **Step 4:** `cp agents/relay.md team/relay/agents/relay.md`
- [ ] **Step 5:** Commit: `git add agents/relay.md team/relay/agents/relay.md && git commit -m "docs(relay): add communication protocol + compress prose"`

### Task 19: Compress spine.md

**Files:**

- Modify: `agents/spine.md`
- Modify: `team/spine/agents/spine.md`

- [ ] **Step 1:** Read `agents/spine.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, API design examples, REST/GraphQL decision table, code blocks
- [ ] **Step 4:** `cp agents/spine.md team/spine/agents/spine.md`
- [ ] **Step 5:** Commit: `git add agents/spine.md team/spine/agents/spine.md && git commit -m "docs(spine): add communication protocol + compress prose"`

### Task 20: Compress surge.md

**Files:**

- Modify: `agents/surge.md`
- Modify: `team/surge/agents/surge.md`

- [ ] **Step 1:** Read `agents/surge.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, growth framework tables, funnel templates
- [ ] **Step 4:** `cp agents/surge.md team/surge/agents/surge.md`
- [ ] **Step 5:** Commit: `git add agents/surge.md team/surge/agents/surge.md && git commit -m "docs(surge): add communication protocol + compress prose"`

### Task 21: Compress touch.md

**Files:**

- Modify: `agents/touch.md`
- Modify: `team/touch/agents/touch.md`

- [ ] **Step 1:** Read `agents/touch.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, platform decision tables, code blocks
- [ ] **Step 4:** `cp agents/touch.md team/touch/agents/touch.md`
- [ ] **Step 5:** Commit: `git add agents/touch.md team/touch/agents/touch.md && git commit -m "docs(touch): add communication protocol + compress prose"`

### Task 22: Compress vigil.md

**Files:**

- Modify: `agents/vigil.md`
- Modify: `team/vigil/agents/vigil.md`

- [ ] **Step 1:** Read `agents/vigil.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, SLO tables, alerting templates, code blocks
- [ ] **Step 4:** `cp agents/vigil.md team/vigil/agents/vigil.md`
- [ ] **Step 5:** Commit: `git add agents/vigil.md team/vigil/agents/vigil.md && git commit -m "docs(vigil): add communication protocol + compress prose"`

### Task 23: Compress volt.md

**Files:**

- Modify: `agents/volt.md`
- Modify: `team/volt/agents/volt.md`

- [ ] **Step 1:** Read `agents/volt.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, firmware architecture tables, protocol specs, code blocks
- [ ] **Step 4:** `cp agents/volt.md team/volt/agents/volt.md`
- [ ] **Step 5:** Commit: `git add agents/volt.md team/volt/agents/volt.md && git commit -m "docs(volt): add communication protocol + compress prose"`

### Task 24: Compress warden.md

**Files:**

- Modify: `agents/warden.md`
- Modify: `team/warden/agents/warden.md`

- [ ] **Step 1:** Read `agents/warden.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening paragraph, before `## Operating Principle`
- [ ] **Step 3:** Compress all prose. DO NOT compress: frontmatter, threat model tables, security checklists, code blocks
- [ ] **Step 4:** `cp agents/warden.md team/warden/agents/warden.md`
- [ ] **Step 5:** Commit: `git add agents/warden.md team/warden/agents/warden.md && git commit -m "docs(warden): add communication protocol + compress prose"`

### Task 24b: Update template and agent guide

**Files:**

- Modify: `templates/new-agent/agents/AGENT_SLUG.md`
- Modify: `docs/agent-guide.md`

- [ ] **Step 1:** Read `templates/new-agent/agents/AGENT_SLUG.md` in full
- [ ] **Step 2:** Add `## Communication` section after opening role paragraph, before `## Operating Principle` (same block as all agents):

```markdown
## Communication

Respond terse. All technical substance stays — only filler dies. Follow output-kit protocol: compressed prose, no filler, fragments OK. Code/security/commits: normal English. See docs/output-kit.md for CLI skeleton, severity indicators, 40-line rule.
```

- [ ] **Step 3:** Compress template prose using same rules as agent defs
- [ ] **Step 4:** Read `docs/agent-guide.md` in full
- [ ] **Step 5:** Add a note in the agent structure section that `## Communication` is a mandatory section for all agents, placed after the opening role paragraph and before `## Operating Principle`
- [ ] **Step 6:** Commit: `git add templates/new-agent/agents/AGENT_SLUG.md docs/agent-guide.md && git commit -m "docs: add communication protocol to agent template + guide"`

---

## Chunk 3: Skill Updates (125 skills, grouped by agent)

All tasks in this chunk are **independent and parallelizable**. Each task handles one agent's skills.

For each skill SKILL.md:

1. **Add/update output-kit reference.** Target string (must appear exactly once in every skill):

   ```
   Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.
   ```

   - If missing: add as last line before the first `## ` section header
   - If present but using old string (ending `...indicators.` without `, compressed prose.`): replace with target string
   - If already correct: no change

2. **Compress skill prose** — same rules as agent defs. DO NOT compress: frontmatter, step headers, code blocks, templates, format examples, anti-patterns lists.

3. **Copy to team mirror**: `cp skills/{name}/SKILL.md team/{agent}/skills/{name}/SKILL.md`

### Task 25: Compress apex skills (5 skills)

**Files:**

- Modify + sync: `skills/apex-plan/SKILL.md` → `team/apex/skills/apex-plan/SKILL.md`
- Modify + sync: `skills/apex-recon/SKILL.md` → `team/apex/skills/apex-recon/SKILL.md`
- Modify + sync: `skills/apex-review/SKILL.md` → `team/apex/skills/apex-review/SKILL.md`
- Modify + sync: `skills/apex-status/SKILL.md` → `team/apex/skills/apex-status/SKILL.md`
- Modify + sync: `skills/apex-takeover/SKILL.md` → `team/apex/skills/apex-takeover/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/apex-*/SKILL.md team/apex/skills/apex-*/SKILL.md && git commit -m "docs(apex-skills): add output-kit ref + compress prose"`

### Task 26: Compress atlas skills (7 skills)

**Files:**

- Modify + sync: `skills/atlas-adr/SKILL.md` → `team/atlas/skills/atlas-adr/SKILL.md`
- Modify + sync: `skills/atlas-changelog/SKILL.md` → `team/atlas/skills/atlas-changelog/SKILL.md`
- Modify + sync: `skills/atlas-map/SKILL.md` → `team/atlas/skills/atlas-map/SKILL.md`
- Modify + sync: `skills/atlas-onboard/SKILL.md` → `team/atlas/skills/atlas-onboard/SKILL.md`
- Modify + sync: `skills/atlas-present/SKILL.md` → `team/atlas/skills/atlas-present/SKILL.md`
- Modify + sync: `skills/atlas-recon/SKILL.md` → `team/atlas/skills/atlas-recon/SKILL.md`
- Modify + sync: `skills/atlas-report/SKILL.md` → `team/atlas/skills/atlas-report/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/atlas-*/SKILL.md team/atlas/skills/atlas-*/SKILL.md && git commit -m "docs(atlas-skills): add output-kit ref + compress prose"`

### Task 27: Compress cortex skills (5 skills)

**Files:**

- Modify + sync: `skills/cortex-{eval,integrate,model,prompt,recon}/SKILL.md` → `team/cortex/skills/cortex-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/cortex-*/SKILL.md team/cortex/skills/cortex-*/SKILL.md && git commit -m "docs(cortex-skills): add output-kit ref + compress prose"`

### Task 28: Compress crest skills (5 skills)

**Files:**

- Modify + sync: `skills/crest-{compete,narrative,okr,recon,roadmap}/SKILL.md` → `team/crest/skills/crest-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/crest-*/SKILL.md team/crest/skills/crest-*/SKILL.md && git commit -m "docs(crest-skills): add output-kit ref + compress prose"`

### Task 29: Compress draft skills (5 skills)

**Files:**

- Modify + sync: `skills/draft-{flow,ia,recon,review,wireframe}/SKILL.md` → `team/draft/skills/draft-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/draft-*/SKILL.md team/draft/skills/draft-*/SKILL.md && git commit -m "docs(draft-skills): add output-kit ref + compress prose"`

### Task 30: Compress echo skills (5 skills)

**Files:**

- Modify + sync: `skills/echo-{feedback,interview,jobs,recon,segment}/SKILL.md` → `team/echo/skills/echo-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/echo-*/SKILL.md team/echo/skills/echo-*/SKILL.md && git commit -m "docs(echo-skills): add output-kit ref + compress prose"`

### Task 31: Compress flux skills (6 skills)

**Files:**

- Modify + sync: `skills/flux-{health,migrate,pipeline,query,recon,schema}/SKILL.md` → `team/flux/skills/flux-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/flux-*/SKILL.md team/flux/skills/flux-*/SKILL.md && git commit -m "docs(flux-skills): add output-kit ref + compress prose"`

### Task 32: Compress forge skills (6 skills)

**Files:**

- Modify + sync: `skills/forge-{audit,cost,diagnose,infra,network,recon}/SKILL.md` → `team/forge/skills/forge-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/forge-*/SKILL.md team/forge/skills/forge-*/SKILL.md && git commit -m "docs(forge-skills): add output-kit ref + compress prose"`

### Task 33: Compress form skills (10 skills)

**Files:**

- Modify + sync: `skills/form-{audit,brand,component,deck,email,logo,mobile,social,tokens,web}/SKILL.md` → `team/form/skills/form-*/SKILL.md`

Note: form has 10 skills — largest batch. Some team copies may be under `team/form/skills/` (verify paths exist before copying).

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Verify team mirror paths exist, copy each
- [ ] **Step 3:** Commit: `git add skills/form-*/SKILL.md team/form/skills/form-*/SKILL.md && git commit -m "docs(form-skills): add output-kit ref + compress prose"`

### Task 34: Compress helm skills (5 skills)

**Files:**

- Modify + sync: `skills/helm-{arbiter,brief,handoff,plan,recon}/SKILL.md` → `team/helm/skills/helm-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/helm-*/SKILL.md team/helm/skills/helm-*/SKILL.md && git commit -m "docs(helm-skills): add output-kit ref + compress prose"`

### Task 35: Compress lens skills (5 skills)

**Files:**

- Modify + sync: `skills/lens-{audit,dashboard,metrics,recon,report}/SKILL.md` → `team/lens/skills/lens-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/lens-*/SKILL.md team/lens/skills/lens-*/SKILL.md && git commit -m "docs(lens-skills): add output-kit ref + compress prose"`

### Task 36: Compress lumen skills (5 skills)

**Files:**

- Modify + sync: `skills/lumen-{abtest,funnel,instrument,metrics,recon}/SKILL.md` → `team/lumen/skills/lumen-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/lumen-*/SKILL.md team/lumen/skills/lumen-*/SKILL.md && git commit -m "docs(lumen-skills): add output-kit ref + compress prose"`

### Task 37: Compress pave skills (5 skills)

**Files:**

- Modify + sync: `skills/pave-{audit,catalog,env,golden,recon}/SKILL.md` → `team/pave/skills/pave-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/pave-*/SKILL.md team/pave/skills/pave-*/SKILL.md && git commit -m "docs(pave-skills): add output-kit ref + compress prose"`

### Task 38: Compress pitch skills (5 skills)

**Files:**

- Modify + sync: `skills/pitch-{copy,launch,message,position,recon}/SKILL.md` → `team/pitch/skills/pitch-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/pitch-*/SKILL.md team/pitch/skills/pitch-*/SKILL.md && git commit -m "docs(pitch-skills): add output-kit ref + compress prose"`

### Task 39: Compress prism skills (5 skills)

**Files:**

- Modify + sync: `skills/prism-{audit,component,dashboard,recon,ui}/SKILL.md` → `team/prism/skills/prism-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/prism-*/SKILL.md team/prism/skills/prism-*/SKILL.md && git commit -m "docs(prism-skills): add output-kit ref + compress prose"`

### Task 40: Compress proof skills (5 skills)

**Files:**

- Modify + sync: `skills/proof-{api,audit,e2e,recon,strategy}/SKILL.md` → `team/proof/skills/proof-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/proof-*/SKILL.md team/proof/skills/proof-*/SKILL.md && git commit -m "docs(proof-skills): add output-kit ref + compress prose"`

### Task 41: Compress relay skills (5 root skills)

**Files:**

- Modify + sync: `skills/relay-{audit,deploy,docker,pipeline,recon}/SKILL.md` → `team/relay/skills/relay-*/SKILL.md`

Note: `team/relay/skills/relay-ship/SKILL.md` exists as orphan (no root counterpart). Do NOT delete it. Do NOT create a root copy. Report it in the verification step.

- [ ] **Step 1:** Read each root skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Also compress `team/relay/skills/relay-ship/SKILL.md` in place (orphan — compress but no root copy)
- [ ] **Step 4:** Commit: `git add skills/relay-*/SKILL.md team/relay/skills/relay-*/SKILL.md && git commit -m "docs(relay-skills): add output-kit ref + compress prose"`

### Task 42: Compress spine skills (6 skills)

**Files:**

- Modify + sync: `skills/spine-{api,design,perf,recon,review,service}/SKILL.md` → `team/spine/skills/spine-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/spine-*/SKILL.md team/spine/skills/spine-*/SKILL.md && git commit -m "docs(spine-skills): add output-kit ref + compress prose"`

### Task 43: Compress surge skills (5 skills)

**Files:**

- Modify + sync: `skills/surge-{activation,experiment,plg,recon,retention}/SKILL.md` → `team/surge/skills/surge-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/surge-*/SKILL.md team/surge/skills/surge-*/SKILL.md && git commit -m "docs(surge-skills): add output-kit ref + compress prose"`

### Task 44: Compress touch skills (5 skills)

**Files:**

- Modify + sync: `skills/touch-{app,audit,feature,recon,release}/SKILL.md` → `team/touch/skills/touch-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/touch-*/SKILL.md team/touch/skills/touch-*/SKILL.md && git commit -m "docs(touch-skills): add output-kit ref + compress prose"`

### Task 45: Compress vigil skills (5 skills)

**Files:**

- Modify + sync: `skills/vigil-{alert,check,incident,instrument,recon}/SKILL.md` → `team/vigil/skills/vigil-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/vigil-*/SKILL.md team/vigil/skills/vigil-*/SKILL.md && git commit -m "docs(vigil-skills): add output-kit ref + compress prose"`

### Task 46: Compress volt skills (5 skills)

**Files:**

- Modify + sync: `skills/volt-{driver,firmware,ota,power,recon}/SKILL.md` → `team/volt/skills/volt-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/volt-*/SKILL.md team/volt/skills/volt-*/SKILL.md && git commit -m "docs(volt-skills): add output-kit ref + compress prose"`

### Task 47: Compress warden skills (5 skills)

**Files:**

- Modify + sync: `skills/warden-{audit,harden,iam,recon,threat}/SKILL.md` → `team/warden/skills/warden-*/SKILL.md`

- [ ] **Step 1:** Read each skill, add/update output-kit reference, compress prose
- [ ] **Step 2:** Copy each to team mirror
- [ ] **Step 3:** Commit: `git add skills/warden-*/SKILL.md team/warden/skills/warden-*/SKILL.md && git commit -m "docs(warden-skills): add output-kit ref + compress prose"`

---

## Chunk 4: Verification

### Task 48: Verify all changes

- [ ] **Step 1: Check output-kit reference in all 125 root skills**

```bash
# Should return 125 (all skills have the reference)
grep -rl "compressed prose" skills/*/SKILL.md | wc -l

# Should return 0 (no skill missing the reference)
grep -rL "compressed prose" skills/*/SKILL.md | wc -l
```

- [ ] **Step 2: Check Communication section in all 23 agent defs**

```bash
# Should return 23
grep -rl "## Communication" agents/*.md | wc -l
```

- [ ] **Step 3: Check team mirrors match root**

```bash
# For each agent, diff root vs team — should show no differences
for agent in apex atlas cortex crest draft echo flux forge form helm lens lumen pave pitch prism proof relay spine surge touch vigil volt warden; do
  diff agents/${agent}.md team/${agent}/agents/${agent}.md || echo "MISMATCH: ${agent}"
done
```

- [ ] **Step 4: Check skill team mirrors match root**

```bash
# For each root skill, diff against team copy
for skill_dir in skills/*/; do
  skill=$(basename "$skill_dir")
  agent=$(echo "$skill" | sed 's/-.*//')
  if [ -f "team/${agent}/skills/${skill}/SKILL.md" ]; then
    diff "skills/${skill}/SKILL.md" "team/${agent}/skills/${skill}/SKILL.md" || echo "MISMATCH: ${skill}"
  fi
done
```

- [ ] **Step 5: Report orphans**

Known orphan: `team/relay/skills/relay-ship/SKILL.md` (team-only, no root counterpart). Verify it was compressed but not deleted.

- [ ] **Step 6: Spot-check compression quality**

Pick 3 agent defs and 3 skills. Compare line count before (git show HEAD~N:path) vs after. Verify ~30% reduction. If a file shows <10% reduction, the compression was likely skipped — re-do it.

```bash
# Example spot-check (adjust commit refs based on actual history)
for f in agents/spine.md agents/form.md agents/vigil.md; do
  echo "$f: before=$(git show main:$f | wc -l) after=$(wc -l < $f)"
done
```

- [ ] **Step 7: Count total commits and files changed**

```bash
# Record starting SHA before execution begins (run this BEFORE Chunk 1)
# START_SHA=$(git rev-parse HEAD)

# Then at verification time:
git log --oneline ${START_SHA}..HEAD | grep -c "communication protocol\|compress prose\|output-kit ref"
git diff --stat ${START_SHA}..HEAD -- agents/ skills/ team/ docs/output-kit.md docs/agent-guide.md templates/ | tail -1
```

- [ ] **Step 8: Commit verification results (optional)**

If any mismatches found, fix them before this step.

```bash
git add agents/ skills/ team/ docs/ templates/ && git commit -m "chore: verify communication protocol rollout complete"
```
