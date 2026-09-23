# jev-ultrafast — integration decision and contract

**Status:** shipped, opt-in, one skill. `lib/jev-ultrafast/` + `/proof-explore`.
**Date:** 2026-09-20
**Upstream:** `github.com/browser-use/jev-ultrafast` (MIT, Browser Use), pinned at `1231850` (2026-09-18).
**Companion:** `docs/jev-browser-eval.md` — the wider evaluation of the Jev browser projects. This document is the third candidate assessed against the same frame, and the first one built.

**Verdict in one line:** the same narrow go as §3.1 of that evaluation — live-app exploration for E2E authoring, behind an opt-in flag, as a subprocess, with a deterministic committed artefact — and everything else still no-go, because none of the structural objections changed.

---

## 1. What it is, and how it differs from the two already evaluated

A browser agent with a dynamic, indexed action space. Each observation builds a table of the page's real controls; one TypeSafe request picks an operation (`CLICK`, `TYPE_TEXT`, `SELECT`, `SCROLL_UP`, `SCROLL_DOWN`, `WAIT`, `DONE`, `BLOCKED`) and its target speculatively in the same round trip; a small text model writes a value only when the operation is `TYPE_TEXT`. No screenshots in the default loop, no DOM in the context window. Model output never becomes a selector, a coordinate, a shell command or executable JavaScript — every executed target resolves back to an observed node, and the executor rechecks page freshness and click occlusion first.

|                   | jev-browser                                                  | playjev                         | **jev-ultrafast**                                         |
| ----------------- | ------------------------------------------------------------ | ------------------------------- | --------------------------------------------------------- |
| Language          | Node                                                         | TypeScript library              | Python ≥ 3.12                                             |
| Packaged          | npm, `jev-browser@0.1.1`                                     | npm, `@filed/playjev@0.1.0`     | **not published — git checkout only**                     |
| Browser           | its own Playwright Chromium, no sessions                     | Chromium/CDP, `PLAYJEV_CDP_URL` | **Browser Harness over CDP, the existing Chrome profile** |
| Entry shape       | library + CLI + MCP                                          | library                         | library + a demo inspector                                |
| Status vocabulary | `needs_login`, `ambiguous`, `stuck`, `needs_confirmation`, … | probabilities                   | **`done` / `blocked` only**                               |
| Keys              | `TYPESAFE_API_KEY`                                           | `TYPESAFE_API_KEY`              | `TYPESAFE_API_KEY` + `TEXT_MODEL_API_KEY`                 |

Three differences decided the integration.

**It reaches real sessions.** Browser Harness drives the Chrome the user already has, with the accounts they are already signed into. §5.6 of the evaluation rejected jev-browser partly because a fresh Playwright Chromium with no cookies is a strictly worse starting position than gstack's Aside for QA of an authenticated app. That objection does not apply here. The flip side is blast radius: an agent in the user's real browser can reach the user's real accounts, which is why `lib/jev-ultrafast` refuses every host it was not explicitly given.

**Its status vocabulary is thinner.** jev-browser's `needs_login` / `ambiguous` / `needs_confirmation` were the most useful thing in that project, and jev-ultrafast has no equivalent — it reports `done` or `blocked`, where `blocked` also means "three actions in a row changed nothing". The transcript recovers the distinctions from the step record instead: a flow that never leaves `/login` has an auth precondition, a step with low `probability` is a contested target, a repeated `page_changed: false` is stuck. Weaker signal, derivable.

**It has no CLI and no package.** `examples/run.py` prints human-readable lines, and there is nothing on PyPI to pin. `lib/jev-ultrafast/runner.py` supplies the missing JSON boundary, and the pin is `git checkout <commit>` in a checkout the user names. That is a worse supply-chain story than an npm integrity hash and a better one than `npx -y` against a floating tag (§5.3): nothing is fetched at invocation time at all.

**A `DONE` is still a claim.** Upstream says so plainly, and the skill enforces independent verification of every one.

## 2. What shipped

| Piece                              | What it does                                                                                                                               |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `lib/jev-ultrafast/cli.py`         | `preflight` (environment only, no network, no import) and `explore` (one flow, one JSON transcript). Standard library only, exit 0 always. |
| `lib/jev-ultrafast/runner.py`      | Runs inside the driver's environment, drives `Agent`, prints one transcript. The only file that imports `jev_ultrafast`.                   |
| `team/proof/skills/proof-explore/` | The skill. Plans flows, runs them, reads the transcript, hands off to `/proof-e2e`.                                                        |
| `proof-e2e` Step 0                 | One sentence: read the transcript if one exists. Unchanged behaviour when none does.                                                       |

Opt-in is `TONONE_JEV_ULTRAFAST=1` plus `TONONE_JEV_ULTRAFAST_HOME`; see `lib/jev-ultrafast/README.md` for the full variable table and the degradation ladder.

## 3. The constraints it inherits

Unchanged from `docs/jev-browser-eval.md`, restated because they are load-bearing:

- **Never a default path.** `lib/jev`'s promise is zero credentials, zero network, never throws. jev-ultrafast needs two keys and a checkout, so it sits behind a flag with gstack `/browse` as the announced fallback and source-reading below that. A skill that degrades without saying which path it took is the failure mode to avoid.
- **CLI, not MCP.** No MCP server is registered. `/browse` remains the mandated browsing entry point in `CLAUDE.md`; a second always-available browser tool for every agent in every session is a systemic cost for a local benefit.
- **The committed artefact is key-free.** Playwright specs with real assertions. CI sees no key, makes no decision-API call, stays deterministic. The driver never enters a test file, a CI config or `package.json`.
- **Deny-default targets.** `localhost`, `*.localhost`, `file://`, and hosts named in `TONONE_JEV_ULTRAFAST_HOSTS`. Production is a refusal. Every decision ships a description of the current page to TypeSafe (§5.4), and here the page may be inside the user's signed-in browser.
- **No credential typing, no irreversible action.** A login-gated flow stops and asks the user to sign in themselves. Delete, cancel, pay and send need a confirmation in the same run — jev-ultrafast has no irreversible-action detector at all, which makes the rule simpler rather than weaker.
- **Page content is data.** Anything the browser returns is untrusted content, never instruction. Same rule as `/browse`.

## 4. Still no-go

`/qa`, `/qa-only`, `/design-review`, `/browse`, `/scrape` are gstack's and are overwritten by `/gstack-upgrade` — best technical fit, not tonone's code (§3.3–3.6). `draft-proto` knows the markup it just wrote (§3.7). `axe-audit` remains conditional and unchanged in sequence: `axe-core` in a real browser first, state-reaching second, and the state-reaching half is exactly what `/proof-explore` now demonstrates — revisit once a rendering path exists there.

## 5. Performance, as claimed

Upstream reports a 7,073 ms Google Flights run; across six alternating runs, median task time 9.450 s to 7.092 s (25% lower) and median browser protocol calls 1,092 to 101. Three repeats of one task on one profile, maintainer-run — directional, not a reliability benchmark. The number that matters for this integration is neither: it is that exploration cost scales with states visited instead of DOM serialized, and the artefact it produces costs nothing to run afterwards.

## 6. References

- `github.com/browser-use/jev-ultrafast` — MIT, Python, `Agent(url, goals)`, `TYPESAFE_API_KEY` + `TEXT_MODEL_API_KEY`
- `github.com/browser-use/browser-harness` — the CDP layer, pinned upstream at `0.1.13`
- `docs/jev-browser-eval.md` — the evaluation this follows; §3.1 is the specification, §5 the risks
- `lib/jev/README.md` — the key-free decision layer whose contract this bridge copies
- `lib/jev-ultrafast/README.md` — commands, environment, transcript shape
