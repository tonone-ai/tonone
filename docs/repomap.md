# Repomap

Orientation map for this repo — 100 agents, 10 teams, 421 skills across `team/`. Read this first, then drill into the specific `agents/<name>.md` or `team/<agent>/skills/<skill>/SKILL.md` the task needs. Don't crawl the whole tree; use the indexes below.

This map exists because the [platform repo](https://github.com/tonone-ai/platform) (`~/repos/tn/platform`, the tonone.ai showcase site) reads its catalog content from this repo, and that sync has drifted badly — see **Known drift** below. This file is the map platform's sync should follow to catch up, and the one any agent working in this repo should read before exploring.

## Two machine-readable indexes (read these, not the raw tree)

| File                    | What                                                     | Rows | Generator                                                                   |
| ----------------------- | -------------------------------------------------------- | ---- | --------------------------------------------------------------------------- |
| `docs/agent-index.json` | name, hat, team, owns, path — one row per agent          | 100  | `scripts/gen-agent-index.py` (reads `CLAUDE.md` team tables)                |
| `docs/skill-index.json` | name, agent, team, description, path — one row per skill | 421  | `scripts/gen-skill-index.py` (reads `team/*/skills/*/SKILL.md` frontmatter) |

Both are the "sitemap" — look a name up here, then open the one file it points to. Regenerate after adding/renaming an agent or skill (neither runs in CI yet).

## Where things physically live

```
agents/<name>.md              ← full agent persona (100 files, mirrors team/<name>/agents/<name>.md)
skills/<skill>/SKILL.md        ← root skill mirror — INCOMPLETE, see Known drift
team/<name>/                   ← canonical source per agent, self-contained
  agents/<name>.md             ← source of truth for the persona (agents/ is the copy)
  skills/<skill>/SKILL.md      ← source of truth for skills (skills/ at root is the copy)
  hooks/                       ← agent-specific lifecycle hooks, if any
  scripts/                     ← Python analyzers + own venv
  tests/
hooks/                         ← root plugin lifecycle hooks (statusline, update-check, tracker, notify)
bundle/<name>-team/            ← install bundles (engineering, product, revenue, marketing, operations,
                                  legal, design, data-science, secops, devx, infra-specialist, ai-ops, full)
docs/                          ← this file, agent-index.json, skill-index.json, naming/output/skill guides
CLAUDE.md                      ← team roster tables (source `gen-agent-index.py` parses)
```

`skill-guide.md` states the rule: edit `team/<agent>/skills/`, copy to root `skills/`, both must stay in sync. In practice that sync is behind — treat `team/*/skills/` as ground truth, `skills/` at root as a maybe-stale distribution copy.

## Known drift (found 2026-07-26 while building this map)

Fixed same day:

- ~~27 skills with no YAML frontmatter~~ — whole AI Operations team (deploy, evals, trace, guard, budget, token, prompt, embed, rank — Wave 7) shipped as bare `# heading` stubs, no `name`/`description`, not registering as real slash commands. Added frontmatter + real `## Steps`/`## Key Rules`/`## Output Format` content to all 27.
- ~~`evals-*` skill naming collision~~ — the AI Ops **Evals** agent's skills were named `eval-*`, colliding with the Data Science **Eval** agent's skill slugs. 2 of them (`eval-analyze`, `eval-design`) were byte-identical copy-paste from the Data Science agent, wrong persona and wrong domain (A/B testing instead of LLM eval). Renamed all 5 to `evals-*` and rewrote the 2 duplicated ones for the correct domain.
- ~~16 skills named `skill.md` instead of `SKILL.md`~~ (14 in `form/`, 1 in `draft/`, 1 in `relay/` — `relay-ship`). Was invisible on any case-sensitive filesystem (Linux CI, Docker, raw GitHub/npm serving) despite rendering fine on a case-insensitive local Mac checkout. Fixed via two-step `git mv` (case-insensitive filesystems can't rename in place).

Fixed 2026-08-07:

- ~~**Root `skills/` mirror is incomplete.**~~ Root had 192 skill dirs against 421 in `team/*/skills/` — Legal, Design, Data Science, Security Operations, Developer Experience, Infrastructure Specialist, and AI Operations (7 of 10 teams) had zero skills mirrored. This was not cosmetic: the bundle plugin (`tonone`, source `./` in `marketplace.json`) discovers skills from root `skills/` and only from there, so `claude plugin install tonone@tonone-ai` installed 100 agents but shipped skills for only 27 of them. The per-agent plugins read `team/<agent>/skills/` and were unaffected, which is why installing one-by-one appeared to be the only thing that worked. Fixed by `scripts/sync-skills.py`; root is now 449 dirs (421 mirrored + 28 root-only hub skills), and `tests/test_structure.py::test_root_skills_mirror_is_complete` fails the build if it regresses.
- ~~**7 teams were never compliance-checked.**~~ `tests/test_skill_compliance.py` reads root `skills/`, so the 257 unmirrored skills escaped every contract test. Syncing them surfaced two real gaps, both now fixed at the `team/` source: 233 skills missing the `atlas-report` overflow clause, and 209 skill descriptions with fewer than 2 quoted trigger phrases (which degrades Claude Code's skill routing).

Still open:

- **Platform repo is stale against all of the above.** `~/repos/tn/platform/.planning/skills-data.json` currently has 23 agents / 138 skills, vs the 100 agents / 421 skills actually in this repo. Platform's `REPOMAP.md` (in that repo) documents its own file layout; it does not yet explain how to pull fresh data from here. See **Briefing for the platform-side sync agent** below.

## Briefing for the platform-side sync agent

Give the agent working in `~/repos/tn/platform` this:

1. **Read `~/repos/tn/tonone/docs/agent-index.json`** (100 rows: `name`, `hat`, `team`, `owns`, `agent_path`) and **`~/repos/tn/tonone/docs/skill-index.json`** (421 rows: `name`, `agent`, `team`, `description`, `path`). Both are absolute source of truth — regenerated same-day, no known bugs left.
2. **Map to platform's schema** (`src/types/index.ts` in the platform repo):
   - `Agent.hat`, `.team` → copy directly from `agent-index.json`.
   - `Agent.description` → `agent-index.json`'s `owns` is a one-line summary, not the full paragraph platform currently uses for the 23 agents it has. For a fuller description, open the `agent_path` file (`tonone/agents/<name>.md`) and pull the persona intro paragraph.
   - `Agent.oneliner`, `.color` → **not present in either index.** These are platform-only fields platform invented (probably by hand) for the current 23 agents. For the other 77, either hand-pick colors/oneliners the same way, or derive a oneliner from the agent's `owns` field and assign colors programmatically (e.g. hash team name → a fixed palette per team, distinct color per agent within it).
   - `Skill.command` → `/${name}` (skill-index.json's `name` is already the bare command, e.g. `apex-plan`).
   - `Skill.category` → not in the index; derive from the naming convention in `docs/skill-guide.md`'s Skill Categories table: name ends in `-audit`/`-check` → `review`, ends in `-recon` → `recon`, otherwise → `build`.
   - `Skill.whenToUse` → not in the index. `skill-index.json`'s `description` field often already embeds "Use when asked to..." trigger phrases (per the frontmatter convention in `skill-guide.md`) — extract that clause if present, otherwise summarize the SKILL.md body's `## Steps`.
3. **Do a full resync, not a diff-and-patch** — going from 23→100 agents and 138→421 skills, a merge is more error-prone than regenerating `.planning/skills-data.json` and `.planning/hooks-data.json` from scratch against the two indexes above.
4. **`.planning/hooks-data.json`** (hooks catalog) has no equivalent index here yet — for that one, still read `~/repos/tn/tonone/hooks/hooks.json` directly.
5. Everything above was broken until today (frontmatter-less skills, a skill-name collision, wrong-case filenames) — all fixed as of this session, so a fresh pull now is safe. If a future pull looks wrong again, check `docs/repomap.md`'s "Known drift" section here first before assuming the platform-side code is at fault.

## Task → where to look

- **Find an agent's full persona** → `docs/agent-index.json` for the path, then read that `agents/<name>.md`
- **Find a skill's prompt** → `docs/skill-index.json` for the path, then read that `team/<agent>/skills/<skill>/SKILL.md`
- **Add a new agent** → `templates/new-agent/`, then follow "Adding a New Agent" in `CLAUDE.md`; rerun `gen-agent-index.py` after
- **Add/edit a skill** → edit under `team/<agent>/skills/`, copy to root `skills/` (per `skill-guide.md`), rerun `gen-skill-index.py`
- **Runtime hook behavior (statusline, update check, notifications)** → `hooks/` + `hooks/hooks.json`
- **What's in a given install bundle** → `bundle/<name>-team/`
- **Naming a new agent/skill** → `docs/naming-guide.md`
- **CLI output formatting rules** → `docs/output-kit.md`
- **Sync platform repo's catalog** → this file's indexes are the source; platform's `.planning/*.json` is the destination (currently out of date — see Known drift)

## Stale — do not use

`docs/sitemap.md` — hand-written, last updated at 31 agents/214 skills (before Legal, Design, Data Science, Security Operations, Developer Experience, Infrastructure Specialist, and AI Operations teams existed). Superseded by the two JSON indexes above. Kept for now; should be deleted or regenerated once the drift fixes above land.
