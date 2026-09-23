# lib/jev-ultrafast — opt-in live-app exploration

A thin, dependency-free bridge to [jev-ultrafast](https://github.com/browser-use/jev-ultrafast)
(MIT, Browser Use). It exists so one skill — `/proof-explore` — can walk a
running frontend and hand back a flow transcript that `/proof-e2e` turns into
ordinary Playwright specs.

tonone does not depend on jev-ultrafast. Nothing here imports it, `runner.py`
is the only file that does and it runs inside the driver's own environment as a
subprocess. With no driver and no keys, every call still returns a JSON answer.

## What jev-ultrafast is

A browser agent with a dynamic, indexed action space. Each observation produces
a table of the page's real controls; TypeSafe's Jev picks one operation
(`CLICK`, `TYPE_TEXT`, `SELECT`, `SCROLL_UP`, `SCROLL_DOWN`, `WAIT`, `DONE`,
`BLOCKED`) and one target in a single request, and a small text model writes a
value only when the operation is `TYPE_TEXT`. No screenshots in the default
loop, no DOM in the context window, no model-authored selectors — every
executed target resolves back to an observed node.

That shape is why it is worth a bridge: exploration is the token-heavy half of
writing an E2E suite, and this pays only for the states it stops at.

## The two commands

Both print exactly one JSON object and exit 0 — always, including on failure.

```bash
python3 lib/jev-ultrafast/cli.py preflight
python3 lib/jev-ultrafast/cli.py explore --url http://localhost:3000 --goal 'Sign up with a new account' --goal 'Reach the dashboard'
```

`preflight` reads the environment only. No network, no import, no prompt:

```json
{
  "ok": true,
  "available": false,
  "mode": "unavailable",
  "opt_in": false,
  "home": null,
  "keys": { "typesafe": false, "text_model": false },
  "reason": "opt_in_unset",
  "fallback": "gstack /browse, then source-only"
}
```

`explore` returns a flow transcript — the executed actions, the URL each ran
against, and the model's confidence in each one:

```json
{
  "ok": true,
  "source": "jev-ultrafast",
  "status": "done",
  "start_url": "http://localhost:3000",
  "final_url": "http://localhost:3000/dashboard",
  "elapsed_ms": 8120,
  "steps": [
    {
      "step": 1,
      "action": "textbox Email",
      "kind": "fill",
      "operation": "TYPE_TEXT",
      "text": "qa+1@example.test",
      "url": "http://localhost:3000/signup",
      "page_changed": true,
      "probability": 0.94,
      "confidence": 0.91,
      "elapsed_ms": 1840
    }
  ]
}
```

`status` is jev-ultrafast's own (`done`, `blocked`) or this bridge's stop
reason (`step_budget`, `timeout`, `interrupted`, `error`). A `done` is the
model's claim, not a verified outcome — assert the outcome yourself.

## Environment

| Variable                     | Who sets it    | Meaning                                                                                                 |
| ---------------------------- | -------------- | ------------------------------------------------------------------------------------------------------- |
| `TONONE_JEV_ULTRAFAST`       | user           | Master opt-in. Anything other than `1` and the bridge reports itself unavailable.                       |
| `TONONE_JEV_ULTRAFAST_HOME`  | user           | Path to a jev-ultrafast checkout (`git clone` + `uv sync`). Not on PyPI; pin a commit.                  |
| `TONONE_JEV_ULTRAFAST_HOSTS` | user, optional | Comma-separated extra hosts. A leading dot matches subdomains (`.staging.example.com`).                 |
| `TONONE_JEV_ULTRAFAST_CMD`   | user, optional | Replaces the `uv run --project <home> [--env-file <home>/.env] python` launcher prefix.                 |
| `TYPESAFE_API_KEY`           | user           | Required by jev-ultrafast. `JEV_API_KEY` is bridged into the child process when it is the only one set. |
| `TEXT_MODEL_API_KEY`         | user           | Required for `TYPE_TEXT`. OpenRouter key in the upstream example configuration.                         |

## The rules this file keeps

1. **Never throws, never prompts, never blocks.** Unavailable is a JSON answer.
   Same promise as `lib/jev`, same reason: a caller must never have an error
   path that depends on someone's credentials.
2. **Deny-default targets.** `localhost`, `127.0.0.1`, `::1`, `*.localhost`,
   `file://`, plus whatever `TONONE_JEV_ULTRAFAST_HOSTS` names. Everything else
   is refused. Production is not a target — it is a refusal, not a warning.
3. **Credentials are environment-only.** No config file is read, no key is
   written anywhere, and the agent never types a credential into a page. A flow
   that needs a login stops and says so.
4. **The transcript carries no page content.** Actions, URLs and confidences
   only — no page text, no screenshots, no DOM. Every decision jev-ultrafast
   makes still ships a description of the page to TypeSafe, which is the reason
   for rule 2.
5. **The committed artefact never depends on this.** What lands in the repo is
   an ordinary Playwright spec. CI sees no key, makes no decision-API call and
   stays deterministic. jev-ultrafast is a test-authoring tool, never a test
   dependency.

## Setup

```bash
git clone https://github.com/browser-use/jev-ultrafast.git ~/src/jev-ultrafast
cd ~/src/jev-ultrafast && git checkout <pinned-commit> && uv sync && cp .env.example .env
# put TYPESAFE_API_KEY and TEXT_MODEL_API_KEY in that .env

export TONONE_JEV_ULTRAFAST=1
export TONONE_JEV_ULTRAFAST_HOME=~/src/jev-ultrafast
```

Chrome connects through [Browser Harness](https://github.com/browser-use/browser-harness),
installed by `uv sync`; `uv run browser-harness --doctor` fixes a broken
connection. Harness drives the existing Chrome profile, so the browser it
touches is the user's — one more reason the host allowlist is deny-default.

Pin the checkout. jev-ultrafast is days old, single-repo, not published to
PyPI; `git checkout <commit>` is the only pin available and re-pinning is a
reviewed change, not a background `git pull`.

## Files

| File        | Job                                                                          |
| ----------- | ---------------------------------------------------------------------------- |
| `cli.py`    | Preflight, target allowlist, launcher, JSON contract. Standard library only. |
| `runner.py` | Runs inside the driver environment, drives `Agent`, prints one transcript.   |

See `docs/jev-ultrafast.md` for the integration decision and what was ruled
out, and `docs/jev-browser-eval.md` for the wider evaluation this follows.
