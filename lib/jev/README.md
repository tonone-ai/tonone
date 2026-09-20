# lib/jev — the shared decision layer

A small, dependency-free decision layer that answers structured questions about
a piece of state: yes/no, one-of-N, and a position on an ordered rubric.

It works with **zero credentials and zero network**. If a Jev API key is
present in the environment it uses the hosted decision model; if not it falls
back to a local TF-IDF scorer. Either way the call shape, the result shape, and
the promise that nothing ever throws are identical.

```js
const jev = require("../../lib/jev/client");

const team = await jev.choice(ticketText, "Which team owns this ticket?", {
  billing: "Charges, invoices, refunds, subscriptions",
  orders: "Order status, delivery, cancellation, returns",
  account: "Login, permissions, password and profile issues",
});
// { type: "choice", answer: "billing", confidence: 0.91,
//   probabilities: { billing: 0.91, ... }, source: "jev" }
```

## The three rules

1. **Never throws, never rejects, never prompts.** Every function resolves. No
   credentials, no network, a 500, a malformed body, an empty option list — all
   of them degrade to the local scorer. There is no error path to handle.
2. **Credentials are opt-in and environment-only.** Nothing here reads a config
   file, asks the user, or writes a key anywhere. With no key set, the module
   performs no network I/O at all.
3. **Always read `source` before you trust `answer`.** `"jev"` is a hosted
   model. `"local"` and `"fallback"` are lexical overlap. Never gate anything
   destructive on a non-`"jev"` answer.

## API

All four functions are `async`.

### `noul(state, question, opts?) -> Promise<NoulResult>`

Yes/no gate.

```js
const isBug = await jev.noul(
  ticketText,
  "Is the customer reporting a defect?",
  {
    criteria: {
      true: "The customer describes broken or unexpected product behaviour.",
      false: "The customer is asking a question or requesting a feature.",
    },
  },
);
// { type: "noul", answer: true, probability: 0.96, confidence: 0.92, source: "jev" }
```

`answer` is `probability >= 0.5`. When the decision has teeth, read
`probability` and pick your own threshold — `0.62` means "leaning yes", not
"yes". A probability near `0.5` is a coin flip, not a medium-intensity answer;
the right response is to ask for more state or escalate.

**Always pass `opts.criteria`.** It is the single biggest accuracy lever on both
paths. Without it the local scorer can only measure topical overlap between the
state and the question — it answers "does the state talk about this", not "is
this true" — and it caps its own confidence at 0.35 to say so.

### `choice(state, question, options, opts?) -> Promise<ChoiceResult>`

Pick one of N. `options` is either an array of strings or, much better, an
object mapping a stable key to a description:

```js
const route = await jev.choice(state, "Which subsystem owns this?", {
  billing: { what: "Charges, invoices, refunds", not_for: "Order tracking" },
  orders: { what: "Order status, delivery, returns", not_for: "Charges" },
});
// { type: "choice", answer: "billing", confidence: 0.75,
//   probabilities: { billing: 0.84, orders: 0.16 }, source: "jev" }
```

`answer` is always one of your keys, or `null` when you supplied no options.
`probabilities` covers every key you sent, including zeros — a zero means the
option was considered and ruled out, which is information.

A choice cannot select a value you did not offer. If the right answer might not
be in your list, put an `unclear` option in it; otherwise the model confidently
picks the nearest thing it was given. Contrastive descriptions (`what` /
`not_for` / `examples`) beat bare labels by a wide margin, and bare one-word
labels give the local scorer almost nothing to work with.

### `score(state, question, levels, opts?) -> Promise<ScoreResult>`

Grade on an ordered rubric. Array order defines the scale, index `0` first.

```js
const urgency = await jev.score(state, "How urgent is this?", [
  "Can wait for the next release",
  "Should be fixed this week",
  "Blocking revenue right now",
]);
// { type: "score", answer: 1.99, confidence: 0.99,
//   probabilities: { "0": 0, "1": 0.01, "2": 0.99 },
//   legend: { "0": "Can wait...", ... }, source: "jev" }
```

`answer` is a probability-weighted mean of the level indices, so it lands
_between_ levels on purpose. Do not round it away before you have used it: `1.4`
and `1.6` are different answers. Two to ten levels; more are dropped.

### `batch(state, questions, opts?) -> Promise<BatchResult>`

Several named questions about one state, in **one** request.

```js
const result = await jev.batch(ticketText, {
  isBug: { type: "noul", question: "Is this a defect?", criteria: { ... } },
  team: { type: "choice", question: "Which team owns it?", options: { ... } },
  urgency: { type: "score", question: "How urgent?", levels: [ ... ] },
});
result.answers.isBug.answer;   // true
result.answers.team.answer;    // "payments"
result.answers.urgency.answer; // 1.99
result.source;                 // weakest source across the answers
```

**Prefer `batch` whenever you have more than one question about the same
state.** Each single call re-sends the whole state; eight sequential calls
measured roughly 4x the tokens of one batched call for the same eight answers.
Questions are evaluated independently, so batching costs nothing in accuracy.

Every name you pass appears in `answers`, whatever happened — except names whose
spec is not a valid `noul` / `choice` / `score`, which are dropped.

## Result shapes

```ts
type Source = "jev" | "local" | "fallback";

type NoulResult = {
  type: "noul";
  answer: boolean; // probability >= 0.5
  probability: number; // 0..1, P(true)
  confidence: number; // 0..1
  source: Source;
  method?: string; // local paths only: "tfidf-criteria" | "tfidf-topical"
  note?: string;
  cached?: boolean;
  provider?: "typesafe" | "openrouter";
};

type ChoiceResult = {
  type: "choice";
  answer: string | null; // one of your keys; null only when no options were given
  confidence: number;
  probabilities: Record<string, number>;
  source: Source;
  method?: string;
  note?: string;
  cached?: boolean;
  provider?: string;
};

type ScoreResult = {
  type: "score";
  answer: number | null; // weighted mean of level indices
  confidence: number;
  probabilities: Record<string, number>; // keyed by level index
  legend: Record<string, string>;
  source: Source;
  method?: string;
  note?: string;
  cached?: boolean;
  provider?: string;
};

type BatchResult = {
  answers: Record<string, NoulResult | ChoiceResult | ScoreResult>;
  source: Source; // the weakest source among the answers
  provider: string | null; // the provider that actually answered, else null
  cached: boolean;
  usage: {
    input_tokens?: number;
    output_tokens?: number;
    cost?: number;
  } | null;
  model: string | null; // resolved snapshot id reported by the provider
  error: string | null; // why the API path was not used, if it was not
};
```

### Reading `confidence`

`confidence` measures how concentrated the distribution is, not whether the
answer is correct. High confidence on a wrong answer is possible; low confidence
on a harmless preference is normal. It is a gate for _routing_, not a
correctness guarantee.

On the local path it is additionally **capped at 0.75** (and at 0.35 for
criteria-free `noul`), specifically so that code thresholding at 0.8 can never
mistake lexical overlap for a decided answer. A local `confidence` of `0` means
there was no lexical signal at all and the returned `answer` is a deterministic
placeholder — check for it.

## Options (`opts`)

| Field       | Default       | Meaning                                                         |
| ----------- | ------------- | --------------------------------------------------------------- |
| `criteria`  | —             | `noul` only: `{ true: "...", false: "..." }`. Always supply it. |
| `cache`     | `true`        | `false` bypasses the response cache in both directions.         |
| `timeoutMs` | `8000`        | Per-attempt request deadline.                                   |
| `retries`   | `1`           | Extra attempts, transient failures only (429, 5xx, network).    |
| `sessionId` | —             | Passed through to the provider for observability.               |
| `env`       | `process.env` | Environment used for provider resolution.                       |
| `provider`  | —             | Inject a resolved provider. Tests only.                         |

## Provider resolution

| Environment                         | Endpoint                                    | Model               | `source` |
| ----------------------------------- | ------------------------------------------- | ------------------- | -------- |
| `JEV_API_KEY` or `TYPESAFE_API_KEY` | `https://api.typesafe.ai/v1/systemone`      | `jev-latest`        | `jev`    |
| `OPENROUTER_API_KEY`                | `https://openrouter.ai/api/alpha/decisions` | `typesafe/jev-1.13` | `jev`    |
| neither                             | none — `lib/jev/local.js`                   | —                   | `local`  |

First match wins, in that order. `TONONE_JEV_OFFLINE=1` forces the local scorer
even when a key is set. `TONONE_JEV_ENDPOINT` and `TONONE_JEV_MODEL` override
the endpoint and model (tests, gateways, proxies). Cost on both providers is
$0.042 per million input tokens with free output; a small decision is on the
order of $0.000013.

Check what would be used without making a call:

```js
jev.resolveProvider(); // -> { name, endpoint, model, key } | null
```

## The local scorer

`lib/jev/local.js` is a TF-IDF vector space over the option texts with cosine
similarity against the state, plus adjacent bigrams, crude suffix stemming and a
stopword list. The option set is the corpus, so IDF measures which words
actually discriminate between _your_ options.

It is good at topical routing when the option descriptions share vocabulary with
the state, and at giving the same answer every time for the same input. It is
blind to negation ("no errors in the log" scores like "errors in the log"),
blind to synonyms with no shared stem ("cannot sign in" vs "authentication
failure"), and cannot judge intent, severity or truth. `tests/test_jev.js`
asserts that a no-overlap case reports `confidence: 0` rather than a confident
guess — that behaviour is part of the contract, not an accident.

Practical consequence for callers: **write option descriptions, not labels.**
`{ billing: "Charges, invoices, refunds, subscriptions" }` works on both paths;
`["billing", "orders"]` works well only on the hosted one.

## Cache

Content-addressed under `~/.cache/tonone/jev/`, 7-day TTL, `0600` entries,
sharded by the first two hex characters of the key. Only API responses are
cached; the local scorer is deterministic and cheap.

Writes go to a unique temporary file and are moved into place with `rename(2)`,
so concurrent writers are last-writer-wins and a reader never sees a partial
file. A corrupt or expired entry is treated as a miss and removed. A cache that
cannot be written is not an error, just a cache that does nothing.

`TONONE_JEV_CACHE_DIR` relocates it. `cache.purge()` drops expired entries.

## CLI

For prose skills that call out from a Bash step. One JSON object on stdout,
**exit code 0 always** — failures are reported as `{"ok": false, "error": ...}`.

```bash
node lib/jev/cli.js provider

node lib/jev/cli.js choice \
  --state-file /tmp/ticket.txt \
  --question "Which team owns this ticket?" \
  --options billing,orders,account

node lib/jev/cli.js noul \
  --state "The app crashes when I click save" \
  --question "Is this a defect?" \
  --criteria-true "A crash, an error, or broken behaviour" \
  --criteria-false "A question or a feature request"

node lib/jev/cli.js score --state-file - --question "How urgent?" \
  --levels "can wait,this week,blocking revenue now"

node lib/jev/cli.js batch --state-file ctx.txt --questions-file questions.json
```

Flags: `--state` / `--state-file` (`-` for stdin), `--question`,
`--criteria-true`, `--criteria-false`, `--options` / `--options-file`,
`--levels` / `--levels-file`, `--questions-file`, `--session-id`, `--timeout`,
`--no-cache`, `--pretty`. Comma lists are trimmed; use the `--*-file` form for
values that contain commas.

Reading one field in a skill step:

```bash
TEAM=$(node lib/jev/cli.js choice --state-file ctx.txt \
  --question "Which team?" --options billing,orders | python3 -c \
  'import json,sys; d=json.load(sys.stdin); print(d["answer"] if d.get("source")=="jev" or d.get("confidence",0)>=0.5 else "unclear")')
```

## Tests

```bash
node --test tests/test_jev.js
```

Covers the no-credentials path, provider resolution order, cache hit/miss/
expiry/corruption, malformed and unparseable API responses, HTTP error statuses,
network failure and timeout, empty and degenerate input, and the CLI contract.
The API paths run against a throwaway localhost server, so the suite needs no
credentials and no network.

## Reference

The hosted API shapes this layer targets are documented in
[`lazniak/jevskill`](https://github.com/lazniak/jevskill) (MIT). `openjev.com`
(SemIf) explores the same primitives against local GGUF weights in the browser
by reading choice logits instead of generating JSON — the same idea as this
module's local path, with a real model behind it, and a plausible future
upgrade for `lib/jev/local.js`.
