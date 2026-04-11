# Communication Protocol — Full Stack Compression

Integrate compressed communication across all tonone agents: output-kit upgrade, agent definition compression, skill compression, Atlas ownership.

## Problem

Agents produce verbose output. Agent definitions and skills contain filler prose the LLM reads as input tokens every dispatch. More tokens = slower + more expensive. No persistence rule — agents drift toward verbose after many turns.

## Approach: Hybrid (Output-Kit as Single Source + Compact Inline)

Upgrade existing `docs/output-kit.md` Language Rules into full Communication Protocol. Each agent def gets 2-line reinforcement. Compress all agent/skill prose bodies.

## Changes

### 1. Output-Kit Upgrade (`docs/output-kit.md`)

Rename "Language Rules" section (lines 82-103) to "Communication Protocol". Add:

- **Scope expansion** — applies to all agent output: conversation, CLI, reports, skill responses. Not just CLI.
- **Persistence** — active every response. No revert after many turns. No filler drift.
- **Auto-clarity exceptions** — drop compressed style for: security warnings, irreversible action confirmations, user confused or repeating question. Resume compressed style after clear part done.
- **Boundaries** — code blocks, commits, PRs, documentation files, error messages → always normal English.
- **Intensity** — all agents operate at one level: drop articles (where meaning preserved), fragments OK, short synonyms, no pleasantries/hedging/filler.

Existing content stays: kill-on-sight list, pattern rule, keep-exact list, before/after example, 40-line rule, CLI skeleton, severity indicators, tables, formatting rules.

### 2. Agent Definition Updates (23 files in `agents/`)

**Add communication reinforcement** after opening role paragraph, before Operating Principle:

```markdown
## Communication

Respond terse. All technical substance stays — only filler dies. Follow output-kit protocol: compressed prose, no filler, fragments OK. Code/security/commits: normal English. See docs/output-kit.md for CLI skeleton, severity indicators, 40-line rule.
```

**Compress agent prose** — apply compression rules to definition text:

- Drop articles where meaning preserved
- Drop filler words (just, really, basically, actually, simply)
- Keep all technical terms exact
- Keep agent personality/voice — each agent has distinct tone, preserve it
- Keep rules, key rules, anti-patterns verbatim in meaning
- Don't compress code blocks, examples, table content, frontmatter
- Target ~30-40% token reduction per file

Files: apex.md, atlas.md, cortex.md, crest.md, draft.md, echo.md, flux.md, forge.md, form.md, helm.md, lens.md, lumen.md, pave.md, pitch.md, prism.md, proof.md, relay.md, spine.md, surge.md, touch.md, vigil.md, volt.md, warden.md

### 3. Skill Updates (125 SKILL.md files in `skills/`)

**Verify output-kit reference** — each SKILL.md must contain:

```
Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.
```

Add if missing. If present but using older string (without "compressed prose"), update to new string. All 125 skills must have the current reference.

**Compress skill prose** — same compression rules as agent defs:

- Don't compress step names/headers (structural)
- Don't compress code blocks, templates, format examples
- Keep allowed-tools, frontmatter, version info unchanged
- Keep anti-patterns sections (high-value, already terse)
- Target ~25-35% token reduction per file

### 4. Atlas Ownership

Add one line to Atlas agent def (`agents/atlas.md`) Output Architecture section:

```markdown
- **Communication Protocol** (in `docs/output-kit.md` § Communication Protocol) — compressed prose rules all agents follow for all output: conversation, CLI, reports, skill responses
```

### 5. Team-Local Copies (`team/*/agents/` and `team/*/skills/`)

All changes to `agents/*.md` must be mirrored in `team/*/agents/*.md`.
All changes to `skills/*/SKILL.md` must be mirrored in `team/*/skills/*/SKILL.md`.

**Bidirectional sync check:** Before mirroring, diff both directions. Some team-local skills may exist without a root counterpart (e.g., `team/relay/skills/relay-ship/` has no `skills/relay-ship/`). Surface orphans for human decision — do not delete them.

**Sync per batch, not at end:** Mirror team copies immediately after each agent/skill batch completes (after step 3, then after step 4). Do not defer all syncing to a final step — team copies may be read mid-run.

## What Does NOT Change

- Output-kit structural sections (40-line rule, CLI skeleton, severity indicators, tables, formatting rules, browser-first reporting, progressive disclosure)
- Agent frontmatter (name, description, model)
- Skill frontmatter (name, description, allowed-tools, version, author, license)
- Code blocks, examples, templates in any file
- Plugin manifests (.claude-plugin/plugin.json)
- Marketplace.json
- CLAUDE.md
- docs/naming-guide.md

## Estimated Impact

- **Output tokens**: ~30-40% reduction in agent conversation verbosity
- **Input tokens per agent dispatch**: ~30-40% reduction from compressed agent defs
- **Input tokens per skill invocation**: ~25-35% reduction from compressed skill prose
- **Files touched**: 1 (output-kit) + 23 (agent defs) + 125 (skills) + team-local mirrors
- **Risk**: Low. Prose compression preserves all technical meaning. Communication reinforcement is additive.

## Implementation Order

1. Upgrade output-kit.md (single file, foundation for everything else)
2. Update Atlas agent def (ownership line)
3. Compress + update remaining 22 agent defs (batch, parallelizable)
   3b. Sync team-local agent copies immediately
4. Compress + update 125 skills (batch, parallelizable)
   4b. Sync team-local skill copies immediately
5. Bidirectional orphan check — surface any team-local files without root counterparts
6. Verify no broken references
7. Post-run diff count against expected file changes (rollback safety net)
