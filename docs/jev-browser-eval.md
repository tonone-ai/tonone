# jev-browser — evaluation for tonone's browser-driven surfaces

**Status:** evaluation only. No code was written, nothing was installed, no dependency was added.
**Date:** 2026-09-20
**Scope:** `github.com/Ying-Kai-Liao/jev-browser` (MIT) and `github.com/filedcom/playjev` (MIT), assessed against every browser-driven surface tonone owns or depends on.

**Verdict in one line:** one narrow go (E2E spec discovery, as a new opt-in Proof skill), one conditional go (Axe flow traversal), everything else no-go — and no MCP server, because a jev-browser MCP server would sit in direct tension with the `/browse` mandate in `CLAUDE.md` while giving up the one thing that makes gstack's browser valuable: the user's real, already-signed-in sessions.

---

## 1. What the two projects actually are

### jev-browser

The inversion is the point. In snapshot-based automation the LLM reads a serialized DOM, reasons about it, and emits a selector. In jev-browser the LLM states an _outcome_ and never reads the page; an in-page script describes the elements, Jev answers four structured questions — which element, which action, which value, is it done — and Playwright executes.

Surface, taken from the README rather than the pitch:

| Layer   | Entry points                                                                                                                                                                                                                                                                |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Library | `JevBrowser.launch()`, `open(url)`, `do(goal, values?, max_actions?, allow_irreversible?, explain?)`, `check(question)`, `choose(question, options)`, `snapshot()`, `act(action, element, value?, key?, destination?, accept_dialog?)`, `screenshot(full_page?)`, `close()` |
| MCP     | `browser_open`, `browser_do`, `browser_check`, `browser_choose`, `browser_snapshot`, `browser_act`, `browser_screenshot`, `browser_close` — same semantics as the library                                                                                                   |
| CLI     | `node bin/jev-browser.mjs do <url> "<goal>" key=value` and `node bin/jev-browser.mjs run <flow.json>`                                                                                                                                                                       |

`browser_do` returns a status from `done`, `likely_done`, `needs_login`, `needs_confirmation`, `error`, `stuck`, `max_actions`, `ambiguous`, `blocked`, alongside `url`, `actions[]`, `done_score`, and situational `page_text` / `info` / `candidates` / `pending`. That status vocabulary is the most useful thing in the project: `needs_login`, `ambiguous` and `stuck` are exactly the distinctions a QA harness normally has to infer from a timeout.

Environment: `TYPESAFE_API_KEY` (required), `JEV_BROWSER_HEADED=1`, `JEV_BROWSER_PROFILE=/dir`, `JEV_BROWSER_LOG=1` (all optional).

Claims, and what they are worth:

| Claim                                                                            | Reading                                                                                                                                                                                                                          |
| -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 40/42 tasks correct, 42 tasks across 16 categories on live sites, 0 false `done` | Maintainer-run, no published harness or task list to reproduce. Treat as directional. The "0 false done claims" figure matters more than the pass rate — a false `done` is the failure mode that silently corrupts a test suite. |
| ~5x fewer tokens, "≈8k vs ≈557k tokens in total", described as a median estimate | The mechanism is real and the direction is certainly right — not serializing the DOM into the context window is a large saving by construction. The specific multiple is an estimate on the author's own task set.               |
| ~300 ms per Jev call, 2–4 calls per step, ~14 s for a 5-step checkout            | Plausible and consistent with the ~325 ms p50 documented for Jev generally. 14 s for five steps is _slower_ than a hand-written Playwright script and faster than an LLM-in-the-loop snapshot agent.                             |
| Irreversible-action detection, one flag in ~200 rounds                           | One flag in two hundred rounds is a precision datum with nothing to say about recall. It is a convenience, not a safety control, and must not be treated as one.                                                                 |

Documented limitations: ordered sub-goals in one step need splitting; open-ended goals need a measurable outcome; multi-value comparisons (table sorting, exact numeric change) fall back to `browser_check` or `browser_snapshot`.

**There is no key-free path.** Nothing in the README describes offline or degraded operation. Without `TYPESAFE_API_KEY` the project does not function.

### playjev

The same idea as a TypeScript library — "Stagehand, but with Jev" — with four primitives that map onto the ones `lib/jev` already exposes:

| playjev                                                                      | `lib/jev` equivalent                              |
| ---------------------------------------------------------------------------- | ------------------------------------------------- |
| `page.check(q)` → `{ answer, probability }`                                  | `jev.noul()`                                      |
| `page.choose(q, options)`                                                    | `jev.choice()`                                    |
| `page.rate(q, levels)`                                                       | `jev.score()`                                     |
| `page.act(instruction, { minTargetConfidence, minVerificationProbability })` | no equivalent — this is the browser-specific part |

The confidence thresholds on `act` are the good idea here: the caller sets both a target-selection floor and a post-action verification floor, which is the same discipline `lib/jev/README.md` asks for when it says never gate anything destructive on a non-`jev` answer. Claims: 8/8 on a Stagehand test set, 4/4 on a WebVoyager golden subset, bulk form fill 0.91 s against 7.41 s sequential. Node 20+, Chromium/CDP only, `TYPESAFE_API_KEY` required.

**Packaging: playjev is published to npm and is pinnable.** It ships as `@filed/playjev@0.1.0` (MIT, Node ≥20), with an sha512 integrity hash and npm provenance enabled in its `publishConfig`; the upstream install command is `npm install @filed/playjev playwright`. That is the same footing as `jev-browser@0.1.1` — slightly better, in fact, since jev-browser publishes without provenance, and playjev takes Playwright as a _peer_ dependency (the consumer pins the browser) where jev-browser depends on `playwright`, `zod` and `@modelcontextprotocol/sdk` directly. Both are 0.1.x, days old and single-maintainer; that is a shared risk, not a discriminator. Packaging is therefore not a reason to exclude playjev, and the verdict below rests on merit.

**On merit, playjev loses the one surface tonone has a GO for — narrowly, and for a reason that could change.**

In its favour: its primitives are the closest thing in either project to what `lib/jev` already exposes, so a tonone integration would reuse a vocabulary the repo already documents rather than learning a second one. The explicit `minTargetConfidence` / `minVerificationProbability` thresholds on `act` are the best safety idea in either project, and they are the discipline `lib/jev/README.md` already asks for. It also supports attaching to an existing Chromium over CDP (`PLAYJEV_CDP_URL`), which is the only mechanism in either project that could in principle reuse a browser tonone did not launch — subject to the unverified caveat in §5.6.

Against it, for §3.1 specifically: playjev is a TypeScript library and nothing else. jev-browser ships a CLI (`bin/jev-browser.mjs run <flow.json>`), which is the shape a skill can shell out to and parse — one JSON document on stdout, matching what `lib/jev/cli.js` already does. Driving playjev from a skill means generating and running a throwaway TypeScript entrypoint, with `tsx` or a build step behind it, on every invocation. That is more moving parts in the exact place where the integration is meant to be thin and optional. jev-browser's status vocabulary (`needs_login`, `ambiguous`, `stuck`, `needs_confirmation`) is also the substance of the flow transcript §3.1 specifies; playjev returns probabilities, which is a different and less directly usable signal for that artefact.

Everything in §5 applies to playjev unchanged: the same hard `TYPESAFE_API_KEY` requirement with no key-free path, the same single-vendor dependency, the same page-content egress, and the same objection to standing up a second browsing path beside `/browse`.

**Verdict: NO-GO for now, but not excluded.** playjev is not a candidate today for the same reasons nothing here is a default path, plus the CLI-shape mismatch above. If a library-level integration is ever wanted — a Node helper inside a tonone skill rather than a subprocess — playjev is the better base of the two, and this verdict should be re-derived rather than inherited. Sections 2–4 are written against jev-browser because it is the candidate that fits the one GO surface.

---

## 2. Inventory: every browser-driven surface

Two separate codebases matter here, and the distinction drives most of the verdicts.

**gstack** lives at `~/.claude/skills/gstack`. It is a separately installed product, upgraded by `/gstack-upgrade`, and tonone does not own a line of it. Its skills carry `<!-- AUTO-GENERATED from SKILL.md.tmpl -->` headers. Any edit tonone makes there is destroyed on the next upgrade.

**tonone** is this repository. Of its 425 skills, three launch a browser: `form-critique`
plus `form-animate` and `form-direction`, which both render HTML for visual review.

| Surface                           | Owner  | Drives a browser today?       | How                                                                                                                                                                                  |
| --------------------------------- | ------ | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `/browse`                         | gstack | Yes — the canonical driver    | Aside (the user's real browser, real cookies, real sessions) via `aside repl`; falls back to gstack's own headless Chromium binary `$B` at `browse/dist/browse` when Aside is absent |
| `/scrape`                         | gstack | Yes                           | Aside, read-only, returns one JSON document                                                                                                                                          |
| `/qa`                             | gstack | Yes                           | The `/browse` cookbook: flow scripts, `CONSOLE_ERRORS=`, screenshots, then a fix-and-reverify loop                                                                                   |
| `/qa-only`                        | gstack | Yes                           | Same driving, report only                                                                                                                                                            |
| `/design-review`                  | gstack | Yes                           | Screenshots via the same cookbook, before/after pairs, visual judgement                                                                                                              |
| `/ios-qa`                         | gstack | **No — not a browser at all** | A real iPhone over a USB CoreDevice IPv6 tunnel, HTTP to an embedded SwiftUI `StateServer`, vision-driven screenshot loop                                                            |
| `team/proof/skills/proof-e2e`     | tonone | No                            | Authors Playwright/Cypress spec files, page objects and CI config. Never executes them                                                                                               |
| `team/proof/skills/proof-recon`   | tonone | No                            | Reads `playwright.config.ts` and counts test files                                                                                                                                   |
| `team/axe/skills/axe-audit`       | tonone | **No**                        | `allowed-tools: Read, Bash, Glob, Grep, Write, WebFetch, WebSearch, AskUserQuestion`. Audits source, or a URL through `WebFetch` — which returns markdown, not a rendered page       |
| `team/axe/skills/axe-fix`         | tonone | No                            | Writes the corrected implementation from a described failure                                                                                                                         |
| `team/draft/skills/draft-proto`   | tonone | **Yes — the only one**        | `npx playwright screenshot "file://.../output.html" out.png --viewport-size=390,844`, plus a `chromium.launch()` script for three click tests against its own generated HTML         |
| `team/wire/skills/wire-prototype` | tonone | No                            | Prose spec: screen inventory, state machine, annotations                                                                                                                             |

Two facts from this table shape everything that follows.

**First, tonone's browser problem is not a driving problem, it is an absence problem.** `axe-audit` claims to check colour contrast, focus management and keyboard navigability, and has no tool that can render a page. `WebFetch` gives it markdown — no computed styles, no contrast ratios, no tab order, no focus ring, no ARIA tree after JavaScript runs. jev-browser does not fix this. Running `axe-core` in a real browser fixes this, and gstack's `$B js` can already do it today at zero marginal cost.

**Second, the surfaces where jev-browser would genuinely reduce token cost — `/qa`, `/design-review`, `/browse` — are all gstack's.** tonone cannot change them and should not try.

---

## 3. Go / no-go, surface by surface

### 3.1 `team/proof/skills/proof-e2e` — **GO**, as a new sibling skill

**Reasoning.** This is the only place where jev-browser's economics and tonone's constraints line up, and it lines up unusually well.

Writing an E2E spec for an app you have not seen is mostly discovery: what is the sign-up flow, what does the primary action actually require, what are the stable selectors, where does the flow branch. Done with a snapshot-based loop that is many rounds of DOM into the context window. `browser_do("sign up with a new account", { email, password })` followed by `browser_snapshot()` at each landing state gets the same information and only pays for the states you stopped at.

The decisive property is that **the artefact is deterministic and the dependency is not in it**. jev-browser is used at authoring time; what gets committed is an ordinary Playwright spec with real selectors and real assertions. CI never sees a key, never makes a network call to a decision API, and never becomes non-deterministic. The dependency is confined to a developer's machine, during authoring, behind an opt-in flag.

The `browser_do` status vocabulary earns its keep during discovery: `needs_login` tells the spec author the flow has an auth precondition, `ambiguous` marks a place where the UI genuinely has two plausible paths and the spec needs a decision, and `needs_confirmation` marks a step the test must never execute against a shared environment.

**Explicitly out of scope:** jev-browser must never appear _inside_ a generated test. A test that calls a paid, probabilistic decision API per assertion is flaky by construction, costs money on every CI run, and turns a red build into a question about model behaviour. `proof-e2e` already says it: "The E2E suite should be ≤10 tests… Every test you add is maintenance cost."

#### Integration spec

**Where it plugs in.** A **new** skill, `team/proof/skills/proof-explore/SKILL.md`, not a modification of `proof-e2e`. Reasons: `proof-e2e` must keep working with zero credentials and zero network for the 99% of invocations that have no key; and a new skill can be absent from a user's mental model entirely without degrading anything. `proof-e2e` gains at most one sentence in its Step 0 — "if a live URL is available and `/proof-explore` has produced a flow transcript, read it before inventing selectors" — and behaves exactly as today when no transcript exists.

**Invocation: CLI, not MCP.** See §5. The skill shells out:

```
node bin/jev-browser.mjs run <flow.json>     # a whole flow, one shot, JSON out
node bin/jev-browser.mjs do <url> "<goal>" key=value
```

The `run <flow.json>` form is the right shape for a skill step: it matches what `lib/jev/cli.js` already does for decisions — one JSON document on stdout that the skill parses — and it keeps the exploration reproducible, because the flow file is an artefact that can be re-run and diffed.

**Environment variables.**

| Variable                                                       | Set by         | Meaning                                                                                                                               |
| -------------------------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `TONONE_JEV_BROWSER`                                           | user           | Master opt-in. Anything other than `1` and the skill behaves as if jev-browser does not exist.                                        |
| `TYPESAFE_API_KEY`                                             | user           | Required by jev-browser itself.                                                                                                       |
| `TONONE_JEV_BROWSER_CMD`                                       | user, optional | Overrides the invocation. Default is a **pinned** `npx -y -p jev-browser@<exact-version> jev-browser`. Never a floating tag — see §5. |
| `JEV_BROWSER_HEADED`, `JEV_BROWSER_PROFILE`, `JEV_BROWSER_LOG` | user, optional | Passed straight through. `JEV_BROWSER_PROFILE` is how a developer gets a signed-in session; the skill never creates or manages it.    |

**Preflight, and one trap.** Detect the key through the foundation rather than reading the environment directly:

```bash
node lib/jev/cli.js provider
```

Exit code 0 always, one JSON object. The field is `provider` (the CLI emits `{"ok":true,"provider":"local","model":null,"endpoint":null}` with no key set); a `provider` of `typesafe` means a TypeSafe-compatible key is resolvable. **The trap:** `lib/jev` accepts _either_ `JEV_API_KEY` or `TYPESAFE_API_KEY` for the TypeSafe provider, and jev-browser reads **only** `TYPESAFE_API_KEY`. A user who set `JEV_API_KEY` alone will pass the preflight and get an authentication failure from the child process. The skill must therefore check `TYPESAFE_API_KEY` explicitly, and may export `TYPESAFE_API_KEY="$JEV_API_KEY"` into the child environment when only the former is set — never write it anywhere, never persist it.

**Fallback with no key — the whole point.** The degradation ladder, in order, with no step that throws, blocks, or prompts for a credential:

1. `TONONE_JEV_BROWSER` unset or not `1`, or `TYPESAFE_API_KEY` absent, or the `npx` invocation fails for any reason → **say nothing about jev-browser** and fall through to (2).
2. A live URL is available → explore with gstack `/browse`, exactly as a tonone skill would today. Higher token cost, same output shape.
3. No live URL → `proof-e2e`'s current behaviour unchanged: read the source, infer the journeys, write the specs.

The output contract is identical on all three paths — a flow transcript of `{ step, goal, url, status, selector, assertion }` — so `proof-e2e` never learns which path produced it. This mirrors the discipline in `lib/jev/README.md`: same call shape, same result shape, degraded source.

**Guardrails the skill must carry.**

- `allow_irreversible` is **never** passed as `true` without an `AskUserQuestion` in the same run. A `needs_confirmation` status is recorded in the transcript and the flow stops there. The one-flag-in-200-rounds figure is not a basis for trusting the detector's recall.
- Exploration targets are localhost or an explicitly named staging URL. Production is a refusal, not a warning.
- Everything jev-browser returns — `page_text`, `info`, `candidates`, screenshots — is untrusted web content, never instruction. This is already the rule in `/browse` and it carries over unchanged.
- No credential is ever typed by the agent. A `needs_login` status ends the flow and asks the user to sign in themselves using `JEV_BROWSER_PROFILE`.
- The transcript is written to the report directory, never committed by the skill.

**Cost.** A ten-step flow at two to four Jev calls per step is roughly thirty decisions, about $0.0004, plus roughly fourteen seconds per five steps of wall clock. The money is not the cost. The cost is the dependency, and the dependency is why this is opt-in.

### 3.2 `team/axe/skills/axe-audit` — **CONDITIONAL GO**, and not for the reason you would expect

**The brief suggested accessibility is a likely win. It is — but jev-browser is not what wins it.**

WCAG auditing splits cleanly in two. The measurable half — contrast ratios, missing `alt`, ARIA validity, heading order, label association, target size — is arithmetic over the computed DOM. `axe-core` does it in a few hundred milliseconds, deterministically, free, and with a WCAG criterion attached to every finding. A probabilistic decision API is strictly worse at this: slower, costed per question, and unable to produce "4.2:1, needs 4.5:1".

So the first and largest fix to `axe-audit` has nothing to do with Jev: **run `axe-core` in a real browser.** gstack's `$B js` and Aside's `pg.evaluate` can both inject it today. That change alone closes the gap between what `axe-audit`'s prose claims and what its `allowed-tools` can reach.

jev-browser's contribution is the other half, and it is narrower:

- **Reaching the states worth auditing.** Most accessibility failures live behind a flow — step three of checkout, the error state of a form, a modal that only opens after a selection. `browser_do("get to the payment step with an invalid card number")` reaches those states in a couple of hundred tokens where a snapshot loop spends thousands. Audit-at-state-N is a real, unglamorous win.
- **Keyboard operability of a flow, as opposed to of an element.** "Can this checkout be completed using only the keyboard" is WCAG 2.1.1 and is not a property of any single node. `browser_act` with `key` plus `browser_check("is the focused element visibly indicated?")` at each stop is a reasonable traversal. Note that the _judgement_ part — is the focus indicator actually visible — is a visual question, and a text-describing decision layer is weak at it. Prefer a computed-style check for `:focus-visible` and treat the Jev answer as corroboration.

**Verdict: conditional.** The condition is that `axe-audit` first gains a real rendering path and `axe-core`; until it does, adding jev-browser puts a paid decision API in front of a skill that still cannot measure a contrast ratio. Sequence matters: `axe-core` in a browser first, jev-browser state-reaching second, and only if the first change proves that state-depth is the remaining bottleneck.

**Integration spec, for when the condition is met.** Identical shape to §3.1 — the same `TONONE_JEV_BROWSER` opt-in, the same `lib/jev/cli.js provider` preflight, the same `TYPESAFE_API_KEY`-vs-`JEV_API_KEY` trap, the same never-`allow_irreversible` rule. One difference: the artefact is not a committed test but a list of `{url, state, reached_by}` audit points, each re-derivable from the recorded flow. Fallback with no key: audit the states reachable from a bare URL, and state plainly in the report which states were not reached and why. An audit that says "I could not reach the payment step" is honest; one that silently audits the landing page and calls it a flow audit is not.

### 3.3 gstack `/qa` and `/qa-only` — **NO-GO** (structural)

On merit these are the best technical fit in the whole inventory. QA is exactly the workload jev-browser was built for: many flows, many steps, most of the DOM irrelevant, the only questions that matter being "did it work" and "what broke".

They are not tonone's to change. They live in `~/.claude/skills/gstack`, carry auto-generated headers, and are replaced by `/gstack-upgrade`. Any edit is a change that silently disappears, which is worse than no change.

If this capability is wanted, the correct route is upstream: a proposal to gstack that `$B` grow an optional Jev-backed decision path, keeping Aside as the driver. That is a contribution to another project, not a tonone task, and it is the only version of this that preserves the real-session advantage described in §5.

### 3.4 gstack `/design-review` — **NO-GO** (on merit)

A visual design review is a judgement about pixels: spacing rhythm, optical alignment, hierarchy, the specific tells of generic AI-generated layout, contrast in the aesthetic sense rather than the WCAG sense. jev-browser's entire value proposition is _not looking at the page_ — it replaces perception with structured questions over a text description of the elements.

That is the wrong trade for this skill. A screenshot into a vision model is the right tool and `/design-review` already uses it. The only sliver jev-browser could add is navigating to the screens worth screenshotting, which is a small fraction of that skill's cost.

### 3.5 gstack `/ios-qa` — **IRRELEVANT**

No DOM, no Playwright, no CDP. It drives a physical iPhone over a USB CoreDevice IPv6 tunnel and talks HTTP to a `StateServer` embedded in the SwiftUI app under test, with a vision loop on top. jev-browser has no point of contact with any part of that. Worth recording only so the question is not asked again.

Adjacent and out of scope: the _pattern_ — state one outcome, let a cheap decision model pick the tap target from a described accessibility tree — would transfer to iOS, since UIKit/SwiftUI expose an accessibility hierarchy that describes elements much as jev-browser's in-page script does. That is a research note about `lib/jev`, not a jev-browser integration.

### 3.6 gstack `/browse` and `/scrape` — **NO-GO**

`/browse` is the mandated entry point for all web browsing in this repo and the driver every other browsing skill borrows from. Replacing or shadowing it is out of scope by policy and unwise by design: see §5 on sessions. `/scrape` is read-only extraction into one JSON document, where the DOM _is_ the deliverable — there is nothing for a decision layer to decide.

### 3.7 `team/draft/skills/draft-proto` — **NO-GO** (low value)

The only tonone skill that launches a browser, and the worst candidate. It verifies a single-file HTML prototype that the agent wrote seconds earlier, against a `file://` URL, with three click tests. The agent has perfect knowledge of the markup, so element selection — the problem jev-browser solves — does not exist here. Adding a paid API key to smoke-test your own generated file is cost with no matching benefit.

One speculative note, recorded and not recommended: `browser_do("complete the signup flow")` against a prototype by an agent that has _not_ seen the source is a crude discoverability probe — if a naive actor cannot find the primary action from the rendered page alone, that is a usability signal. Interesting; not worth a dependency; revisit only if `draft-proto` ever grows a usability-testing phase.

---

## 4. Summary table

| Surface                               | Owner  | Verdict                         | One-line reason                                                                                                                                             |
| ------------------------------------- | ------ | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `proof-e2e` (as new `/proof-explore`) | tonone | **GO**                          | Discovery is token-heavy; the committed artefact stays deterministic and key-free                                                                           |
| `axe-audit`                           | tonone | **CONDITIONAL GO**              | Only after `axe-core` runs in a real browser; the win is reaching states, not measuring them                                                                |
| `/qa`, `/qa-only`                     | gstack | **NO-GO**                       | Best fit on merit, not tonone's code; `/gstack-upgrade` overwrites edits                                                                                    |
| `/design-review`                      | gstack | **NO-GO**                       | Visual judgement needs pixels; jev-browser's premise is avoiding them                                                                                       |
| `/browse`, `/scrape`                  | gstack | **NO-GO**                       | Mandated entry point; and for `/scrape` the DOM is the deliverable                                                                                          |
| `/ios-qa`                             | gstack | **IRRELEVANT**                  | No DOM, no Playwright, no CDP                                                                                                                               |
| `draft-proto`                         | tonone | **NO-GO**                       | Agent already knows the markup it just wrote                                                                                                                |
| playjev (`@filed/playjev`)            | —      | **NO-GO for now**, not excluded | Packaging is sound (npm, pinnable, provenance); library-only with no CLI, so it loses §3.1 on shape — revisit if a library-level integration is ever wanted |

---

## 5. Risks, stated plainly

### 5.1 Hard API-key requirement — a direct conflict with this repo's first principle

`lib/jev` exists on a stated promise: works with zero credentials and zero network, never throws, never blocks, no required dependency. jev-browser has no such path. Without `TYPESAFE_API_KEY` it does not run at all.

The two are reconcilable only one way: **jev-browser is never on a default path.** It sits behind `TONONE_JEV_BROWSER=1` _and_ a resolvable key, in a skill that does not otherwise exist, with gstack `/browse` as the documented fallback for every step. What must never happen is a skill that degrades from "explored the live app" to "silently wrote specs from source" without saying which one it did. The fallback must be announced in the output, once, in one line.

### 5.2 Single-vendor dependency, at alpha stage

`lib/jev` hedges: TypeSafe or OpenRouter, selected from the environment, with a local scorer under both. jev-browser hardcodes TypeSafe. One vendor, one endpoint, one key name, on an API whose OpenRouter sibling is still served from an `/api/alpha/` path. A pricing change, a rate limit, or a shutdown takes the capability with it.

Mitigated only by containment: if the deliverable is a committed Playwright spec (§3.1), a vendor disappearing costs future exploration and breaks nothing that already exists. If jev-browser were ever inside a running test, the same event would break CI.

### 5.3 Supply chain

The documented install is `npx -y -p jev-browser jev-browser-mcp`. Unpinned, `-y`, fetching and executing the latest published version on every invocation, from a single-maintainer package, with Playwright and a Chromium download behind it. That is a fresh remote-code-execution surface opened every time a skill runs.

Non-negotiable if any integration proceeds: pin an exact version, record it in the doc and the skill, and never install globally. Re-pinning is a reviewed change, not a background upgrade. `playjev` is the better-behaved of the two here — its documented install is an ordinary `npm install @filed/playjev playwright` into a project, pinned by the lockfile, published with an integrity hash and npm provenance — so this risk is jev-browser's invocation pattern, not a property of the Jev browser projects generally (§1).

### 5.4 Data egress from authenticated pages

Every decision ships a description of the current page to a third party. On an authenticated page that description contains whatever the page contains — account identifiers, order contents, customer records. The `/browse` rules already say credentials never pass through the agent and cookies are never read or printed; this is a different leak with the same shape, and it is the reason §3.1 confines exploration to localhost and named staging.

Any use against a tenant's real data needs the vendor's data-handling terms reviewed first. That is a Terms/Shield question, not an engineering one, and it should be answered before, not after.

### 5.5 Irreversible-action detection is not a safety control

One flag across roughly two hundred rounds tells you the detector is not noisy. It tells you nothing about how often it misses. The status is `needs_confirmation`; the caller opts past it with `allow_irreversible: true`. Treat the flag as a helpful nudge and put the actual control where it belongs: a human confirmation in the same run, and a hard refusal to explore production.

### 5.6 The `CLAUDE.md` browse mandate

The rule in this repo is exact:

> gstack is installed at `~/.claude/skills/gstack`. Use `/browse` for all web browsing — never use `mcp__claude-in-chrome__*` tools.

Two clauses, and they behave differently toward a jev-browser MCP server.

**The prohibition does not literally apply.** It names `mcp__claude-in-chrome__*`. A jev-browser MCP server would expose `mcp__jev-browser__browser_*` and is not that.

**The mandate does apply, and it is the binding one.** "Use `/browse` for all web browsing" has no carve-out. An always-registered MCP server offering `browser_open` and `browser_do` is a second browsing entry point sitting next to the mandated one, available to any agent in any session, with its own consent path and its own driver — precisely the fragmentation the mandate was written to prevent.

There is also a practical objection that is larger than the policy one. gstack's `/browse` drives **Aside, the user's real browser, with their real cookies and their already-signed-in accounts**; it falls back to gstack's own headless Chromium only when Aside is unavailable. jev-browser launches **its own Playwright Chromium** with no sessions at all — `JEV_BROWSER_PROFILE` means a separate, manually established sign-in per site, maintained by hand. For QA of an authenticated application, that is not a smaller version of what gstack does. It is a strictly worse starting position that also happens to cost money per decision.

(A note for anyone who reads the fallback path and hopes to bridge the two: gstack's `$B` is a Chromium daemon whose `cdp` command is a deny-default allowlisted dispatch, enumerated in `browse/src/cdp-allowlist.ts`, not an open debugging endpoint. Whether a raw CDP websocket is reachable was not verified in this evaluation, and the allowlist design suggests it is deliberately not. Do not plan on attaching playjev or jev-browser to gstack's browser without confirming that first.)

**Resolution — recommended.** Do not register a jev-browser MCP server. Invoke the **CLI** from inside the one opt-in skill that needs it, as a subprocess, scoped to that skill's run. `/browse` remains the browsing entry point and the mandate holds unamended; jev-browser becomes a test-authoring tool that happens to use a browser, which is what it is actually good for here.

**Resolution — rejected, recorded.** Register the MCP server and amend `CLAUDE.md` with a carve-out. This makes a second browser available to every agent in every session, permanently, in exchange for a capability two skills want occasionally. The cost is borne by the whole system; the benefit is local. Not worth it.

---

## 6. Recommended sequence

1. **Nothing, for now.** Everything above is reversible and nothing is urgent.
2. **`axe-core` in a real browser for `axe-audit`.** No key, no vendor, no new dependency, and it closes the widest gap found in this evaluation — a skill that promises contrast and focus checks with no tool that can render a page.
3. **`/proof-explore` as specified in §3.1**, if and only if someone has a `TYPESAFE_API_KEY` and a live staging app to point it at. Pinned version, opt-in flag, CLI not MCP, deterministic committed artefact.
4. **Revisit `axe-audit` state-reaching** only after (2) ships and the remaining bottleneck is measured to be flow depth.
5. **Upstream to gstack** if `/qa` is where the value really is. That is a contribution to another project and the only path that keeps Aside's real sessions.

## 7. References

- `github.com/Ying-Kai-Liao/jev-browser` — MIT, library + CLI + MCP, `TYPESAFE_API_KEY` required
- `github.com/filedcom/playjev` — MIT, TypeScript, published as `@filed/playjev@0.1.0` on npm (integrity hash, provenance, Playwright as a peer dependency), `check`/`choose`/`rate`/`act`, Chromium/CDP, `TYPESAFE_API_KEY` required
- `lib/jev/README.md` — tonone's key-free decision layer; the contract every integration here defers to
- `~/.claude/skills/gstack/browse/SKILL.md` — the Aside cookbook and the `$B` fallback command table
- `docs/skill-guide.md`, `docs/output-kit.md` — authoring rules for any skill that comes out of this
