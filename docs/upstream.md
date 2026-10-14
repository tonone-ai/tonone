# Upstream ledger

tonone borrows from seven public Claude Code plugins and two open-source agent projects. This file records what was taken from each one, which release it was taken from, and what upstream has since shipped that we deliberately did not take. The machine-readable pins live in `docs/upstream.json`; `scripts/check-upstream.py` compares those pins against each project's latest release and exits non-zero when one has moved.

```bash
python scripts/check-upstream.py          # human-readable drift report
python scripts/check-upstream.py --json   # for CI or a hook
```

The one vendored artifact is the `lib/uiux` CSV corpus, which is MIT-licensed data from ui-ux-pro-max; its copyright notice ships in `lib/uiux/NOTICE.md`, as MIT requires.

Borrowing is one-directional and by hand: we read the upstream diff, decide what applies to a 100-agent team, and write it into tonone's own agents and skills in tonone's own voice. Nothing here is vendored code except the `lib/uiux` CSV corpus, which is data. `lib/copy-gate` and `lib/site-signals` are tonone code that adapts Harvey's detectors and phrase list; their MIT notice ships in each directory's `NOTICE.md`.

## harvey v0.3.0 and MiroFish v0.1.2 (read 2026-10-14)

Two autonomous-agent apps rather than plugins. Neither app is useful to us as a dependency. What's worth having is the discipline each one built around a model.

### harvey v0.3.0 (MIT)

[ethanplusai/harvey](https://github.com/ethanplusai/harvey) is an autonomous cold-email agent that runs on a Claude Code or Codex subscription. Read at commit `e2632eb`, the `v0.3.0` tag (its README still says 0.2.1).

**Taken:**

- **Verification in code, not just the prompt.** `harvey/gate.py` blocks an email before it sends: banned phrases, leftover merge tags, length, links, HTML, a recipient that doesn't match the record. Generalised into `lib/copy-gate/gate.py` with one profile per channel (cold email, LinkedIn note, press pitch, press release, HN, marketing copy, microcopy), plus checks Harvey lacked: unfilled `[slot]` placeholders, TODO markers, fake `Re:`/`Fwd:` subjects. It is the last step of `deal-outreach`, `deal-close` (objection replies), `buzz-outreach`, `buzz-pitch`, `buzz-hn`, `pitch-copy` and `copy-write`. A failing draft is never shown.
- **The cold-email playbook** (`skills/email_frameworks.md`, `signal_playbook.md`) into `deal-outreach`: compliance rules that override every style rule (CAN-SPAM, honest subjects, opt-out is final, GDPR legitimate interest, honest about automation); deliverability first; per-touch word ceilings; the four reply triggers; signal → opening-line map with a ranking; a ban list on AI tells. It also removed tonone's own "Worth a quick chat?" CTA, which the playbook bans.
- **Objection handling** (`skills/objection_handling.md`) into `deal-close` Step 2b: diagnose the reply type before answering (brush-off, condition, smokescreen, genuine), LAARC, and hard lines on opt-outs, anger and fabrication.
- **Signals, confirmed by the user, stored one fact per row.** Harvey's free HTTP profiler and its observation table became `lib/site-signals/` (`profile.py`, `cohort.py`) and the new `deal-signals` skill. Nothing is collected until the user picks signals; every fact carries confidence and an evidence URL; a cohort is a query; `--changes` turns re-observation into triggers; failures are reported, never silent.

**Changed on the way in:** the profiler sends an honest user agent and respects `robots.txt` (Harvey rotates Chrome user agents). "Powered by" no longer counts as an agency credit, after it labelled a partner badge as an incumbent agency on a live test. Job-title detection requires a role noun and reports when roles load from an ATS (Greenhouse, Ashby) instead of returning nothing.

**Not taken:** the always-on heartbeat loop, the approval dashboard, the Gmail/SMTP/Instantly senders and bounce kill switch (tonone is a plugin, not a daemon); paid discovery providers; email-pattern finding and verification; the Claude subscription quota gauge, which reads the OAuth token from the keychain and calls an undocumented endpoint.

### MiroFish v0.1.2 (AGPL-3.0, ideas only)

[666ghj/MiroFish](https://github.com/666ghj/MiroFish) builds a simulated social world from a seed document (OASIS for the simulation, Zep for graph memory) and writes a forecast from it. Read at main commit `7657031` (2026-10-02), ahead of the `v0.1.2` release. **The license is AGPL-3.0, so no code or prompt text was copied.** Everything below was written fresh.

**Taken, as ideas:**

- **A synthetic stakeholder panel** became `echo-panel`: groups extracted from the stimulus (actors only, plus catch-all buckets); grounded archetype personas, with a mix forced on purpose (champion, skeptic, neutral, expert, the person who loses); an independent round, then a cross-reaction round; follow-up interviews chosen for diversity. Unlike MiroFish, tonone treats the output as hypotheses, not a forecast: it is labelled synthetic everywhere, ends in a "What this is not" box, and hands seeds to `echo-interview`.
- **Evidence-first section writing** from its report agent became a short rule block in `atlas-report`, `lens-report` and `apex-review`: outline first, 3-5 mixed lookups per section, cite every claim, don't restate earlier sections, "insufficient evidence" instead of filler, never write a tool result you didn't receive.

**Not taken:** OASIS, Zep, the Vue frontend, simulations with hundreds of agents, and the forecasting claims, which are unvalidated.

## open-seo v0.1.9 (read 2026-09-24)

[every-app/open-seo](https://github.com/every-app/open-seo) is an MIT, self-hostable Semrush/Ahrefs alternative built on DataForSEO. The app itself is not useful to us; its ten agent skills in `plugins/openseo/skills/` are. Read at commit `0ffff93` on main, just after the `v0.1.9` release.

**Taken (into Ink):**

- **Metrics come from a tool or are `unknown`.** `ink-cluster`, `ink-seo`, and `ink-brief` all asked for an estimated monthly search volume with no data source, which invited invented numbers. Every Ink SEO skill now labels numbers by source and states a data tier (SEO data MCP / Search Console / web-only), and web-only runs are marked directional. WebSearch result order is never reported as a Google position.
- **Audit discipline.** `ink-seo` was rewritten around open-seo's `seo-audit`: read page families from the sitemap, shortlist five to ten candidates across at least three kinds of opportunity, recommend one to three, put every other row in "What else we checked" with a real reason, adversarially review the strongest rejected row before writing.
- **Honest benefit sizing.** Volume is not visits; a ranking page already gets part of the volume; variants overlap; position-one scenarios are labeled hypothetical; no invented conversion rates.
- **Rank-reporting conventions.** Organic listings only, `#10 (page 1)`, depth 20, a failed lookup is `unknown`, same-day disagreement is not a trend.
- **Protect winners.** Never recommend rewriting a page that already ranks near the top.
- **Search Console striking-distance first** (position 5–20, 50+ impressions) before broad keyword discovery.
- **Clustering by SERP overlap, not word similarity**, plus evidence-only cannibalization checks (`ink-cluster`).
- **Two new skills:** `ink-links` (never invent contacts, flag paid placements) and `ink-local` (match by `place_id`, cost warning before grid checks, no review gating, no keyword-stuffed names).
- **A light shared research log.** `.tonone/seo/context.md` and `.tonone/seo/research-log.md` so SEO runs reuse results under 30 days old instead of re-buying data.

**Not taken:** the OpenSEO MCP server, hosted reports, and HTML report template (tonone delivers through the output kit and `/atlas-report`); `seo-coach` mode; `competitor-analysis` and `competitive-landscape` (Crest owns competitive strategy; candidates for a later SEO-specific pass); the "AI visibility" workflow, which lives in the app, not in a skill. The skills name SEO data providers only as examples of a capability, never as a recommended vendor.

## Sweep of 2026-09-20

| Plugin          | Repo                                                                                            | Release read                       | What tonone took this pass                                                                                                                                |
| --------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| superpowers     | [obra/superpowers](https://github.com/obra/superpowers)                                         | `v6.4.1` (2026-09-19)              | Review Focus in plans, plan-before-execution gate, execution-path choice, reviewer standards, whole-suite green, `merge-base` diff base, `/apex-diagnose` |
| impeccable      | [pbakaus/impeccable](https://github.com/pbakaus/impeccable)                                     | `skill-v4.3.1` (2026-09-09)        | 14 named craft-floor bans for Form, browser-surface theming, bounded verification passes, refinement-vs-redesign                                          |
| ui-ux-pro-max   | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | `v2.15.0` (2026-08-13)             | Full corpus refresh, new `motion` domain, 6 new stacks, freshness contract columns, `uiux stack` CLI                                                      |
| caveman         | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)                               | `v2.7.0` (2026-09-15)              | Corrected compression rules in the output kit — what actually saves tokens and what only looks like it does                                               |
| open-design     | [nexu-io/open-design](https://github.com/nexu-io/open-design)                                   | `open-design-v0.23.0` (2026-09-20) | Reference split (Keep / Change / Do-not-copy) and the implementation-handoff artifact in `form-brief`                                                     |
| frontend-design | bundled with Claude Code                                                                        | n/a                                | Nothing new this pass — absorbed in v1.11.1                                                                                                               |

### superpowers v6.4.1

Upstream's own evals drove most of this release, which makes its findings unusually worth copying: each rule exists because a measured run failed without it.

**Taken:**

- **Review Focus.** Plans now name the five input classes or failure modes the spec implies but no task's tests exercise, each pinned to a test in the task that owns the code. Upstream added it after every implementer in an eval shipped the same crash on an input the spec implied but never named. Landed in `apex-plan` step 4b.
- **Plan review is its own gate.** Approving an idea or a scope is not approving a plan nobody has read. In `apex-plan` step 4 and Apex's iron rules.
- **Execution path is a stated choice with a price.** Dispatched (a fresh specialist per chunk plus independent review) versus inline (this session implements, one review at the end), with a recommendation drawn from the plan. tonone's XS–XXL tiers already carried cost; they now carry the path too. `apex-plan` step 4c.
- **The spec is a vision document.** Where a spec is silent, a reasonable user's expectation is the requirement and the silence is not permission. Grade by effect on that person, not by whether a doc names the trigger. `apex-review` step 2b.
- **Declined to judge.** The reviewer lists every behavior it set aside as out of scope, one line each with a reason; the requester rules on each line. Nothing gets dropped silently. `apex-review` step 5b.
- **Green means the project's suite.** In 11 of 12 probe runs upstream measured, sessions ran only the one test file their task named and missed a broken test next door. Added as an iron rule to all 10 agents carrying `test-driven-development`.
- **`git merge-base origin/main HEAD` as the diff base.** A bare `origin/main` shows main's newer files as phantom deletions once main moves past the branch point. `apex-review` step 1.
- **Intent before features.** Ask why the person wants the thing, write the understanding back for correction, keep what they said separate from what you assumed. `helm-brief` step 1.
- **`diagnosing-superpowers` → `/apex-diagnose`.** A new Apex skill: reconstruct what happened in a session from the local transcripts, every finding cited `path:line`, no theory without evidence. Reuses `apex-stats`' transcript parsing.

**Not taken:** the harness-support work (OpenCode 2.0, Muse, Qwen Code) is upstream's distribution problem, not ours. The `proving-it-works-with-a-movie` skill is held back upstream. Upstream's four new process skills — `requesting-code-review`, `receiving-code-review`, `diagnosing-superpowers`, `using-superpowers` — are now listed in `docs/agent-guide.md`, but only the rules they carry are embedded in personas: subagents cannot invoke the Skill tool, so a reference to a skill they cannot call is decoration.

### impeccable skill-v4.3.1

**Taken:** fourteen named bans added to Form's anti-pattern list — eyebrow/kicker labels, gradient text, glass as decoration, side-stripe borders, hard offset shadows outside a genuinely neobrutalist world, the ghost card (border under a wide shadow), glyph and emoji icons, system display faces, nested and uniform card grids, geometric occlusion masks, theme picked by product category. Plus the positive rule most often skipped: **browser surfaces carry the design** — selection color, caret, scrollbars, focus rings, underline offset, tabular numerals all ship with defaults belonging to no design system, and theming them is the cheapest signal a page was built rather than assembled (`form-web`).

Two process rules came with it: **verify in bounded passes, not a loop** (build fully, one batched inspection round covering every viewport, fix in one batch, at most one confirm round, stop) in `draft-proto`, and **refinement preserves, redesign replaces** — never split the difference into polish on a look that is being discarded — as a key rule for Form and Draft, together with its corollary that a missing design file is not proof of a greenfield.

**Not taken:** impeccable's runtime — the detector CLI, live browser server, hook system, and harness-specific (Codex/Gemini) blocks. tonone agents produce specs and critiques; they do not run impeccable's engine.

### ui-ux-pro-max v2.15.0

The largest mechanical change this pass. `lib/uiux` was carrying the corpus as of the May 2026 import.

| Dataset              | Was                 | Now                      |
| -------------------- | ------------------- | ------------------------ |
| Color palettes       | 161                 | 192                      |
| UX guidelines        | 99                  | 119                      |
| Product types        | 161                 | 192                      |
| UI reasoning rules   | 161                 | 192                      |
| Styles               | 84                  | 88                       |
| Google Fonts         | 1,923               | 1,934                    |
| Stack guideline sets | 16 files / 841 rows | 22 files / 1,260 rows    |
| Motion presets       | —                   | 17 (new `motion` domain) |

Beyond row counts:

- **`motion` domain** — GSAP presets with trigger, duration, easing, snippet, framework notes, and performance notes, tiered by intensity. Granted to Form (direction) and Prism (implementation); reachable by every prompt-only agent through `python -m uiux search --domain motion`.
- **Six new stacks** — javafx, wpf, winui, avalonia, uno, uwp. Upstream renamed `shadcn-ui` to `shadcn`; `STACK_ALIASES` keeps the old key working.
- **Freshness contract** — every stack row now carries `Applies To`, `Status`, and `Verified At`. These are surfaced in search output, and `tests/test_domains.py` fails if a stack file loses them. A row marked legacy describes an older major and must be quoted as such.
- **Richer reasoning and icon rows** — `Reasoning` and `Confidence` on ui-reasoning, `Semantic Role` and `Allowed Contexts` on icons.
- **New CLI verbs** — `uiux stacks` and `uiux stack --stack <name> --query <q>`, so the 1,260 stack rows are reachable without a Python import.

**Not taken:** upstream's BM25 query rewriting, typo recovery, and version-aware abstain logic. tonone's search is a stdlib BM25 with no dependencies and that constraint is deliberate; the routing work is a bigger port than this pass warranted. Worth revisiting — it is the highest-value thing left on the table here.

### caveman v2.7.0

The compression protocol in `docs/output-kit.md` came from caveman. Upstream has since measured which of its own tricks actually pay, and the corrections matter more than the original rules:

- **Invented abbreviations save nothing.** `cfg`, `impl`, `req`, `res`, `fn`, `auth` tokenize the same as the full word — zero saved, and the reader still decodes. Standard acronyms (DB, API, HTTP) are single known tokens and stay.
- **Causal arrows in prose save nothing.** `→` is its own token. It stays in the CLI skeleton as a structural indicator; it is not a prose connector.
- **Compression never grows the output.** No word added to sound terse, no inserted pronoun or copula to fake broken grammar.
- **Never compress away** a negation, a number, a unit, or a correct verb form that costs the same as the mangled one.
- **Scale honestly.** Prose is a small fraction of a session's tokens. The reason to compress is signal density, not the bill.

**Not taken:** caveman's proxy, its CLI, and its memory-file compressor. tonone's statusline and memory formats are their own thing.

### open-design v0.23.0

The skill catalogue went from ~19 skills when `form-brief` was built (May 2026) to 163. Most of the growth is media generation (fal, venice, replicate, imagegen), templates, and catalogue shims pointing at other people's upstreams — not things a 100-agent engineering-and-product team needs.

**Taken:** the reference-to-contract discipline from `reference-design-contract`, folded into `form-brief` as Phase 1b and Phase 3. Every supplied reference is split into **Keep** (qualities: density, composition, material, type rhythm, color temperature, motion attitude), **Change** (subject, copy, layout), and **Do not copy** (screenshots, logos, claims, pricing, proprietary UI) — with each row's evidence labeled `observed`, `provided`, or `inferred`. Then an `implementation-handoff.md` ships next to DESIGN.md, so the next builder executes the direction instead of re-deriving it.

**Worth a look next pass:** `marketing-psychology` (→ Pitch, Surge), `paywall-upgrade-cro` (→ Surge), `research-decision-room` (→ Echo, Crest), `theme-factory` and `color-expert` (→ Hue, Tone), `apple-hig` and `web-design-guidelines` (→ Touch, Draft), `pr-feedback-quality-gate` (→ Apex). Several are catalogue entries pointing at third-party upstreams; check the real source before absorbing.

## How to run the next sweep

1. `python scripts/check-upstream.py` — see which pins moved.
2. For each that moved, read the release notes between the pinned tag and the latest one. The question is always "what did their evals catch that our agents would also fail?", never "what can we copy?".
3. Write what applies into tonone's own agents and skills, in tonone's voice. A rule that lives in a skill nobody invokes is not absorbed; the rules that stick go in the persona, because subagents cannot invoke the Skill tool.
4. Update `docs/upstream.json` with the new tag and date, and add a section here describing what was taken and what was deliberately left.
5. `python scripts/sync-skills.py` then `python -m pytest tests/ -q` before committing.
