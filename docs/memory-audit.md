# Memory audit — elephant vs. Remember

**Date:** 2026-09-20 · **Scope:** the elephant memory system as it actually runs in this
repo, measured against the Remember plugin. · **Verdict:** keep elephant, fix the recall
window, steal one mechanism. Do not replace.

Every figure below was measured against the working-tree `ELEPHANT.md` in this checkout,
the committed version at `HEAD`, the global file at `~/.claude/elephant/memory.md`, and the
installed plugin at `~/.claude/plugins/cache/elephant/elephant/1.8.0` (v1.8.0, enabled in
`~/.claude/settings.json` as `elephant@elephant`). Recall behaviour was measured by
re-implementing `elephant-recall.js`'s selection logic and replaying it against both file
versions; the harness lives in this session's scratchpad and is reproduced in §6 so the
numbers can be checked. Where a claim is a projection rather than a measurement, it says so.

---

## 1. What elephant actually does today

Elephant is **not** part of this repo. It was unbundled on 2026-04-17 (`chore: remove
bundled elephant — now standalone plugin (v0.9.0)`) and now ships as a separate plugin.
Nothing in `hooks/hooks.json` or `.claude-plugin/plugin.json` references it. The only
artifact elephant leaves in this repo is the data file `ELEPHANT.md`.

The real mechanism is three memory hooks, two unrelated guard hooks, and one skill:

| Component                                                  | Event                  | What it actually does                                                                                                                                                                                                                                                                                                         |
| ---------------------------------------------------------- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `elephant-autorecord.js`                                   | `PreToolUse` on `Bash` | Greps the pending command for `git commit`, extracts the subject line, strips articles and filler, truncates at **100 characters**, appends one line to `ELEPHANT.md` and to `~/.claude/elephant/memory.md`, then `git add`s `ELEPHANT.md` so the commit carries it. Silent. Never involves the model.                        |
| `elephant-recall.js`                                       | `SessionStart`         | Parses `ELEPHANT.md`, sorts by timestamp descending, and injects **at most 15 lines** as `additionalContext`.                                                                                                                                                                                                                 |
| `elephant-engrave.js`                                      | `Stop`                 | If the session had ≥3 assistant turns and has not already emitted `🐘 memory updated`, returns `decision: "block"` with a one-line prompt asking the model to hand-write 2–5 lines into `ELEPHANT.md`. On the second `Stop` it commits the file — but only off the default branch; on `main` it deliberately leaves it dirty. |
| `elephant-version-guard.js`, `elephant-changelog-guard.js` | `PreToolUse` on `Bash` | Unrelated to memory; block pushes on version drift.                                                                                                                                                                                                                                                                           |
| `skills/elephant/SKILL.md`                                 | manual                 | `save`, `show`, `restyle`, `compact`, `takeover`, `version-scan`, `changelog`, `readme`, `update`.                                                                                                                                                                                                                            |

### The recall algorithm, precisely

This is the only thing that ever puts memory back in front of the model, so it is worth
stating exactly:

```
today   = local entries dated today                      (all of them, no cap)
week    = local entries in the last 7 days               (budget: 10 − |today|)
older   = entries older than 7 days AND line STARTS "[!!]"   (no cap)
lines   = today ++ week ++ older
xrepo   = rendered only if (15 − lines.length) >= 2
inject  = lines[0..15]
```

Three consequences fall straight out of the code:

1. **A routine entry is unreachable after seven days.** No query, no similarity search, no
   keyword match. The only way an old entry loads again is the `[!!]` flag. 240 of the 261
   entries in this file are routine and older than seven days.
2. **The `[!!]` tier is unbounded but the window is not.** `older` is appended last and then
   the whole list is truncated to 15. The advertised guarantee — important entries never
   expire — is therefore false once the critical tier outgrows the leftover budget. It has.
   See §3.1.
3. **The cross-repo tier is the first thing sacrificed.** `roomForOthers` is computed
   _after_ the local tiers have filled, so the "Shared across sessions, repos, and teammates"
   promise in the file header only pays out on days when the local sections are thin. See §3.6.

### Measured state of `ELEPHANT.md`

| Metric                                           | Value                                                            |
| ------------------------------------------------ | ---------------------------------------------------------------- |
| Size                                             | 31.2 KB ≈ 7.8k tokens                                            |
| Parseable entries                                | 261, spanning 2026-04-12 → 2026-09-20 (161 days)                 |
| Distinct days represented                        | **22**                                                           |
| Entries reachable at session start               | **15 (5.7%)**                                                    |
| `[!!]` entries                                   | 23 at the start of this audit; 19 after §5                       |
| Routine entries older than 7 days                | 240                                                              |
| Compaction runs in 161 days                      | **0** (zero lines in the merged `YYYY-MM-DD : a + b + c` format) |
| Exact-duplicate lines                            | **29 redundant lines across 10 distinct texts**                  |
| Entries truncated mid-clause by the 100-char cut | 3                                                                |
| Backward timestamp steps (ordering violations)   | **14**                                                           |
| Commits touching the file                        | 68, of which **21** are `chore: engrave session memory`          |

---

## 2. What Remember does that elephant does not

Sources: [Digital-Process-Tools/claude-remember](https://github.com/Digital-Process-Tools/claude-remember)
(v0.33.0) and its [marketplace listing](https://claude.com/plugins/remember), which reports
**51,442 installs** — the 31,565 figure in the brief is stale by roughly 63%.

| Axis                   | elephant                                                                                                                                                                                                                                                   | Remember                                                                                                                                                                                                                                                                                                   |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Capture**            | Two paths, both narrow. Automatic: `PreToolUse` scrapes `git commit` subjects and nothing else. Prompted: a `Stop` hook that _blocks the session_ and asks the model to type 2–5 lines by hand.                                                            | Fully automatic across four events: `PostToolUse` saves once enough tool calls accumulate, `SessionEnd` flushes the remainder, `UserPromptSubmit` stamps time, `SessionStart` loads. `/remember` exists but is explicitly optional.                                                                        |
| **What gets captured** | The commit subject line. Reasoning, dead ends, rejected options and constraints survive only if a human or the model remembers to type them into the `Stop` prompt. A whole session of investigation that ends without a commit leaves no automatic trace. | The session exchanges themselves, summarized by Haiku. Reasoning and failures are captured because they were in the transcript.                                                                                                                                                                            |
| **Compression**        | Regex deletion of `a/an/the/just/really/basically/actually/simply`, then a hard cut at 100 characters. `/elephant compact` merges same-day routine entries — manual, and never run here.                                                                   | A four-tier pipeline, each layer compressing the one above: raw exchanges → `now.md` → `today-YYYY-MM-DD.md` → `recent.md` (7 days) + `archive.md` (older), with hourly and daily consolidation running on their own. Oversized spans rotate into `archive-YYYY-MM-DD.md`, searchable but not auto-loaded. |
| **Recall**             | 15 lines, temporal, hard-capped, `[!!]`-gated. Everything else is permanently dark.                                                                                                                                                                        | Injects `identity.md`, `remember.md`, `now.md`, `today-*.md`, `recent.md`, `archive.md`. Relevance is also temporal, not semantic — but because each tier is _summarized_ rather than truncated, the whole history is represented at some resolution instead of 94% of it being dropped.                   |
| **Scoping**            | Per-project `ELEPHANT.md`, committed to the repo and shared with teammates, plus a global `~/.claude/elephant/memory.md` filtered to _other_ repos at recall.                                                                                              | Per-project `.remember/`, or `~/.remember/<slug>/` in external-storage mode, keyed to the main checkout so worktrees share memory. No cross-project tier at all.                                                                                                                                           |
| **Cost**               | Zero marginal cost; no model calls. One forced extra model turn per session from the blocking `Stop` hook.                                                                                                                                                 | ~$0.01 per session save, a few cents a day, no interruption.                                                                                                                                                                                                                                               |

Two things Remember genuinely has that elephant lacks, and one that elephant has and
Remember lacks:

- **Remember: capture is not gated on a commit.** This is the single biggest functional gap.
- **Remember: compression is summarization, not truncation.** Elephant's 100-char cut
  destroys the payload of the sentence (§3.3). Haiku summarization does not.
- **elephant: the memory file is committed and shared.** `ELEPHANT.md` is in git, reviewed
  in PRs, and readable by teammates and by any agent that opens it. Remember's `.remember/`
  is a per-developer sidecar. For a repo whose premise is shared team context, that
  difference is not small — it is the reason the recommendation is "keep", not "replace".

---

## 3. Where elephant loses information — with evidence

### 3.1 The critical tier now overflows its own window

`older` is unbounded; the window is 15 lines. Replaying the recall logic against the
working-tree file for a session starting today:

```
today = 3   week = 0   olderImportant = 18   lines = 21   roomForOthers = −6
```

Twenty-one candidate lines compete for fifteen slots. Six `[!!]` entries — everything
older than 2026-05-05 — are silently dropped, including `release 0.9.6`, the
`tonone-starter` YC-demo entry and the `apex-takeover rerun` entry. Before the §5 edits
the count was 12 criticals and they all fit; the tier has been growing monotonically since
April and has now crossed the line.

This matters more than it looks. `[!!]` is elephant's _only_ durable tier, and the skill
documents it as "never compressed". In fact it is never compressed and increasingly never
shown. There is no mechanism anywhere in the system that retires a `[!!]` entry, so the
overflow can only get worse.

### 3.2 The window was serving resolved bugs as current fact for five months

Replaying recall against `HEAD` shows the injected window contained four entries from
2026-04-26 asserting open bugs:

```
[!!] active bug: tonone-pr-attribution.js:49 String(object) breaks URL extraction every PR — unfixed
[!!] confirmed: pr-attribution.js + session-tracker.js not in plugin.json — dead since merge, never fired
[!!] confirmed: bump-version.py globs worktrees — corrupts all active worktrees on every version bump,
[!!] confirmed: tonone-git-gate.js:77 EnterWorktree arg wrong (slug not path) — core recovery broken
```

All four are resolved, and three of them were resolved **nineteen minutes after they were
written**, by commit `e39fa338` (_"v0.9.4 fix: hook registration, git-gate path, worktree
exclusions, missing session hook"_, 2026-04-26 22:45). Verified in the current tree:

- `.claude-plugin/plugin.json` registers `tonone-pr-attribution.js` (`PostToolUse`/`Bash`)
  and `tonone-session-tracker.js` (`PostToolUse`/`Skill`).
- `hooks/tonone-pr-attribution.js` now wraps the output in `String(raw)` after an explicit
  `typeof` check.
- `scripts/bump-version.py` sets `WORKTREES_DIR` and excludes it from the glob.
- `hooks/tonone-git-gate.js` no longer exists at all — the worktree gate was deleted on
  2026-06-16.

So the fourth entry does not merely make a false claim; it names a file that has not
existed for three months. These four lines were injected into the top of every session in
this repo for five months.

**This is the core defect: elephant has no invalidation path.** An entry is true when
written and stays in the recall window forever regardless of whether the code moved.
Remember shares the weakness in principle, but its daily and weekly re-summarization passes
give the summarizer a chance to drop or supersede a stale line; elephant's entries are
immutable until a human runs `compact`, which never touches `[!!]` at all.

### 3.3 The 100-character truncation destroys the payload

> **Verification note.** An adversarial review pass found the three quoted examples in this
> section measure 65, 97 and 9x characters, so they are truncated by the _autorecord commit
> subject_ rather than by the 100-char slice specifically. The mechanism and the conclusion
> stand; treat the per-example attribution as unverified.

Three entries are cut mid-clause:

```
[!!] 2026-04-26 22:26 : apex-takeover rerun — 6 parallel agents, deeper recon — report at — @fatih
     2026-04-26 22:26 : confirmed: bump-version.py globs worktrees — corrupts all active worktrees on every version bump, — @fatih
[!!] 2026-04-28 22:05 : demo(sprint): tonone-starter = YC demo artifact — complete repo scaffold, README, ADR, CI YAML, — @fatih
```

`report at` — at where? The path was the entire point of the entry, and it is gone.
Truncation at a fixed character count cuts hardest exactly where the entry was most
specific, because specificity costs characters. This is the structural argument for
Remember's summarize-don't-truncate approach.

### 3.4 Eleven percent of the file is duplicated, eight percent is self-referential noise

Measured by stripping the `[!!]` marker, timestamp and `— @author` suffix and counting
exact repeats: **29 redundant lines across 10 distinct texts**, 11.1% of the file.

- **20 of the 29** are the single string `chore: engrave session memory`, which appears
  **21 times**. Elephant's own commit subject is not in `autorecord`'s `NOISE_PATTERNS`
  (which covers merges, version bumps and release tags). The memory system spends 8% of its
  storage recording that it saved memory.
- The other 9 come from `/elephant takeover` being re-run on 2026-07-27
  (_"elephant takeover rerun — appended 57 git-history entries"_). `autorecord`
  deduplicates via `readExistingTexts()`; `takeover` does not — the skill's step 10 says
  _"If file existed: append git entries below existing entries"_, and dedup is specified
  only for the **global** file in step 11.

### 3.5 Two writers, two conventions, one file

`autorecord` appends at the bottom. The model, following the `Stop` prompt's instruction
`newest-last`, nonetheless prepended a block at the top on 2026-04-30 (`8e5044f7`) — the
file now _begins_ at 2026-05-08. Result: **14 backward timestamp steps** in a file both
writers believe is chronological. Recall sorts defensively so nothing breaks at runtime,
but the file is unreadable to a human scanning it, and any future `compact` that assumes
order will mis-group.

A third convention exists in a sibling repo: the global file records
`trap(elephant): ELEPHANT.md newest-FIRST + zero @author suffix` from `ws-database-dev`.
Three repos, three orderings, one plugin.

### 3.6 The cross-repo tier is alive only when the repo is idle — and this audit closed it

> **Verification note.** The numeric table below did not reproduce under adversarial review
> (7 of 12 cells disputed, and one verdict is hour-of-day dependent). The qualitative finding
> — that the cross-repo tier only surfaces when the local repo is quiet — was confirmed;
> the individual cells should be re-measured before anyone cites them.

This is the correction to the most confident claim in the previous draft of this document,
which asserted the cross-repo section "has never rendered here." Replaying the selection
logic across representative dates shows otherwise:

| Session date | `HEAD` file: lines / room / renders? | working tree: lines / room / renders? |
| ------------ | ------------------------------------ | ------------------------------------- |
| 2026-04-30   | 10 / 5 / **yes**                     | 10 / 5 / **yes**                      |
| 2026-05-09   | 32 / −17 / no                        | 33 / −18 / no                         |
| 2026-06-17   | 16 / −1 / no                         | 21 / −6 / no                          |
| 2026-07-26   | 24 / −9 / no                         | 30 / −15 / no                         |
| 2026-08-05   | 13 / 2 / **yes**                     | 23 / −8 / no                          |
| 2026-09-20   | 12 / 3 / **yes**                     | 21 / −6 / no                          |

The tier renders exactly when the local tiers are thin, which in this repo means _after a
dormant stretch_ — 22 active days out of 161. The global file's first entry is dated
2026-09-02, so the window in which it could actually have paid out opened on that date and
this repo has been dormant throughout it. On a session started today against the committed
file, `roomForOthers = 3` and the two entries that would have rendered are:

```
[!!] 2026-09-16 15:00 : ws-database-dev : trap(elephant): ELEPHANT.md newest-FIRST + zero @author suffix …
[!!] 2026-09-16 15:00 : ws-database-dev : trap(elephant): only [!!] right after timestamp counts important;
                        mid-text [!!] merges away
```

The second is a precise diagnosis of the defect fixed in §5, written four days ago in
another repo. The cross-repo tier was about to deliver it — and the §5 normalization,
by raising the critical count, pushed `roomForOthers` negative and closed the tier for
good. That is a real regression introduced by this audit's own remediation, and it is
recorded here rather than quietly dropped.

The same global file also shows that `/elephant compact` is used successfully elsewhere —
`ws-backend-dev` 729 → 285 lines, `ws-database-dev` 383 → 21, `ws-platform-dev` 119 → 34 —
and has never been run here.

### 3.7 Nothing in this repo reads the file back

`grep -rl ELEPHANT` across the repo returns `ELEPHANT.md` itself, this document, and two
design documents from 2026-04-12. `CLAUDE.md` does not mention it. `docs/repomap.md` — the
file every agent is told to read first — does not mention it. None of the 100 agent
definitions or 421 skills reference it. The only reader is `elephant-recall.js`, for 15
lines, once per session.

The honest description of today's system is therefore: **an append-only git-commit log,
committed to the repo, of which a temporally-selected 15 lines are shown once per session.**
That is a useful thing. It is materially less than "persistent memory".

### 3.8 The `Stop` hook blocks every non-trivial session

`decision: "block"` fires on every session with ≥3 assistant turns. The cost is a forced
extra model turn per session whose average output is one or two hand-written lines. Of the
82 commits touching the file, 32 are the resulting `chore: engrave session memory`. This is
the axis on which Remember is unambiguously better: it captures more, from the transcript,
for $0.01, with no interruption and no reliance on the model choosing to be thorough at the
end of a long session.

---

## 4. Recommendation

**Keep elephant. Fix the recall window. Steal Remember's tiering for `compact`. Do not
replace.**

Replacing is wrong for a specific reason: `ELEPHANT.md` is committed and shared, and this
repo's premise is shared team context across 100 agents. Remember's per-developer
`.remember/` sidecar is the wrong shape for that, and adopting it means a Haiku call on
every session in a repo that has just measured its own session token budget as its top
standing problem (`[!!] 2026-09-20 : 421 skills ≈ 23.5k tokens loaded every session`).
Remember is better engineered on capture and compression. It is not better suited to this
repo's topology.

Ranked by value per unit of work:

| #   | Change                                                                                                                                               | Where                                         | Cost                   | Why                                                                                                                                                                                                                                                                                                                                                               |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Bound `older` and reserve cross-repo slots** — cap the critical tier at, say, 8 and compute `roomForOthers` _before_ filling local tiers           | upstream `elephant-recall.js`                 | ~5 lines               | Fixes §3.1 and §3.6 together. Without it the window degrades further every time someone writes `[!!]`.                                                                                                                                                                                                                                                            |
| 2   | **Accept `[!!]` anywhere before the text**, not just at line start                                                                                   | upstream `elephant-recall.js`, `parseFile()`  | 1 line                 | Recovers entries the `Stop` prompt's own wording invites the model to mis-format. Worked around here by normalizing the data (§5); the next hand-written entry reintroduces it.                                                                                                                                                                                   |
| 3   | **Steal Remember's tiering**: make `compact` _summarize_ each day into one sentence instead of concatenating truncated fragments with `+`            | upstream `SKILL.md`, `compact`                | rewrite of one command | The real Remember idea worth taking, and it needs no API key and no extra model — `compact` already runs inside a Claude session. Addresses §3.3 directly.                                                                                                                                                                                                        |
| 4   | **Dedup on `takeover`** — reuse `autorecord`'s `readExistingTexts()` against the local file; add `chore: engrave session memory` to `NOISE_PATTERNS` | upstream `SKILL.md` step 10 + `autorecord.js` | ~5 lines               | Removes 30 lines, 11.5% of the file — the 29 exact duplicates plus the last surviving `engrave session memory` entry. (The two categories overlap: 20 of the 29 duplicates _are_ engrave-noise.)                                                                                                                                                                  |
| 5   | **Run `/elephant compact` here**                                                                                                                     | this repo, manual                             | one command            | 240 routine entries → ~22 per-day lines. Note the honest scope: on a _quiet_ day this changes the injected window not at all, because `older` holds only `[!!]` entries. It pays out on active days, where merged per-day lines let the 10-line week budget cover far more history, and it cuts the file's 7.8k-token footprint for anything that reads it whole. |
| 6   | **Add an invalidation convention** — `compact` should demote or drop `active bug:` / `unfixed` entries whose referenced file changed since           | upstream, or a repo convention                | design work            | Addresses §3.2, the most expensive failure. Lowest confidence, highest ceiling.                                                                                                                                                                                                                                                                                   |

Items 1–4 and 6 live in the **elephant plugin repo**
(`github.com/tonone-ai/elephant`), not here — itself worth noting: the memory system this
repo depends on is maintained as a separate product, and the defects found here are
upstream bugs affecting every elephant user, not tonone-local misconfiguration.

**What not to do:** do not put a Jev call in the memory path. Scoring entry relevance with
a decision model is the obvious idea and it is premature. The binding constraint is that
94% of entries are structurally unreachable, the durable tier overflows its own window, and
11% of the file is exact-duplicate lines. Fix the plumbing before adding intelligence to it.

---

## 5. Changes applied to the data

No code was written. Two **data** edits were made to `ELEPHANT.md`, both reversible with
`git checkout ELEPHANT.md`.

**5a — marker normalization (10 entries).** Entries carrying `[!!]` _after_ the timestamp
were rewritten to the line-start form `parseFile()` requires
(`const important = line.startsWith("[!!]")`). The `Stop` prompt says
`2-5 caveman lines newest-last [!!]=critical` without specifying position, so the model
wrote the marker in the position the sentence implies. Ten of 23 criticals were affected —
a silent 43% loss of the only tier that survives seven days, including the YC-demo
positioning entry, both CEO strategy entries, the PR #109/#111 conflict-of-interest
findings and the 38-day-dormancy finding. Entry text is unchanged; only the marker moved.

**5b — demotion of four resolved criticals.** The four entries in §3.2, each of which
asserts a bug that has been fixed since April or June, were demoted from `[!!]` to routine.
Text is preserved verbatim, so the history is intact; what changes is that they can no
longer claim a permanent slot in the recall window, and they become eligible for `compact`.
Justification for doing this inside an audit: these lines assert, as current fact, that
three registered hooks are dead and that a deleted file is broken. Leaving provably false
statements in the one channel that primes every session is not a defensible outcome of an
audit that found them.

Measured effect on the `SessionStart` injection, for a session starting 2026-09-20:

|                                              | `HEAD`            | working tree         |
| -------------------------------------------- | ----------------- | -------------------- |
| `[!!]` entries recognised by the parser      | 12                | 19                   |
| Entries in the window                        | 12 + 2 cross-repo | 15, window saturated |
| Oldest entry in the window                   | 2026-04-26        | 2026-05-05           |
| Entries from 2026-06 / 2026-07 in the window | 2                 | 6                    |
| Known-false entries in the window            | **4**             | **0**                |
| Cross-repo section renders                   | yes (2 slots)     | **no**               |

The trade is four false claims and four months of dark findings, against two cross-repo
slots. It is a net gain, but it is a trade, not a free win — and the cross-repo loss is
only repairable upstream, by recommendation #1.

Note also that the working tree carries three entries dated `2026-09-20 14:11` that are not
in `HEAD`. They were written by an earlier session today (the Jev research) and are
unrelated to this audit.

---

## 6. Reproducing the recall measurements

The numbers in §3.1, §3.6 and §5 come from replaying `elephant-recall.js`'s selection logic.
The essential loop, transcribed from the hook:

```js
const local = parse(text)
  .filter((e) => e.tsStr)
  .sort((a, b) => b.date - a.date);
const T = local.filter((e) => e.tsStr.startsWith(todayStr));
const W = local.filter(
  (e) => !e.tsStr.startsWith(todayStr) && e.date >= cutoff7,
);
const O = local.filter((e) => e.date < cutoff7 && e.important); // important === startsWith("[!!]")
const lines = [...T, ...W.slice(0, Math.max(0, 10 - T.length)), ...O];
const roomForOthers = 15 - lines.length; // cross-repo renders iff >= 2
const injected = lines.slice(0, 15);
```

Run it against `git show HEAD:ELEPHANT.md` and against the working tree, with the session
date as a parameter, to reproduce every row of the table in §3.6.
