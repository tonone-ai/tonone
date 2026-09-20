# lib/compact — verbatim transcript selection

Decides which tool calls and tool results in a Claude Code transcript are still
worth carrying, and reports that decision as a plan. It never summarizes, never
paraphrases and never rewrites. Every entry it keeps is kept byte-for-byte,
every entry it drops is dropped whole, and the only lossy operation is a middle
elision whose head and tail are exact substrings of the original.

```js
const sel = require("../../lib/compact/transcript-select");

const entries = sel.parse(fs.readFileSync(transcriptPath, "utf8"));
const p = await sel.plan(entries, {}); // or sel.planSync(entries, {}) — no I/O
console.log(sel.render(p)); // <= 40 lines, per docs/output-kit.md
fs.writeFileSync(out, sel.emit(entries, p));
```

```bash
node lib/compact/transcript-select.js --transcript <path>          # summary
node lib/compact/transcript-select.js --transcript <path> --json   # full plan
node lib/compact/transcript-select.js --transcript <path> --emit   # filtered JSONL
node --test tests/test_compact.js
```

## Why this is a library and not a hook

Claude Code exposes no hook that can replace the messages being compacted. The
`PreCompact` command hook can read `transcript_path` and can block compaction,
but its only other output is natural-language instructions appended to the
summarizer prompt — there is no `PreCompact` member in the `hookSpecificOutput`
schema at all, and compaction reads in-memory messages rather than the file on
disk. The evidence and the surface that _would_ work are recorded in
`docs/adr/0001-no-precompact-transcript-rewrite.md`. The user-facing entry point
is the `/token-compact` skill.

## The three rules

1. **Keeping too much is the cheap mistake.** Losing a file path, an exact error
   string or a stated constraint is expensive and silent. Every rule is written
   so the failure mode is "we kept something we did not need".
2. **Nothing throws and nothing needs credentials.** The deterministic heuristic
   is the primary path and performs zero network I/O. `lib/jev` is consulted
   only when a provider is already configured in the environment.
3. **User and assistant prose is never touched.** Only `tool_use` /
   `tool_result` pairs are candidates. Text, thinking, system records and every
   other record type are copied through untouched, including lines that failed
   to parse as JSON.

## The heuristic

| Rule                                                               | Effect                                                     |
| ------------------------------------------------------------------ | ---------------------------------------------------------- |
| Within the last `keepRecent` (30) exchanges                        | always keep                                                |
| Result under `smallBytes` (2000)                                   | always keep                                                |
| Tool is `Write` / `Edit` / `MultiEdit` / `NotebookEdit` / Artifact | never drop                                                 |
| Result is an error                                                 | always keep                                                |
| Read-shaped tool, same target read again later                     | drop                                                       |
| Otherwise, over `hugeBytes` (20000)                                | middle elision, `keepHeadBytes` + `keepTailBytes` verbatim |

Only read-shaped tools (`Read`, `Bash`, `Glob`, `Grep`, `WebFetch`, ...) are
eligible for a full drop, and only on a real supersession — a later entry that
looked at the same target — never on a guess about staleness.

A target is the subject of the call _plus every other input field_. The extra
fields are what make two calls on one subject different calls:
`Read(file_path, offset: 1)` and `Read(file_path, offset: 900)` return disjoint
regions, `Grep(output_mode: "content")` and `Grep(output_mode:
"files_with_matches")` return different things, and two `WebFetch` calls on one
URL with different prompts do too. Only a purely cosmetic field
(`description`) is excluded. Long inputs are bounded by a hash rather than a
slice, so two different calls that share a prefix never collapse onto one
target.

A tool result is written twice in a Claude Code transcript: as a `tool_result`
block inside `message.content`, and again as the structured top-level
`toolUseResult` field on the same record — usually the larger of the two. Both
copies are measured, and both are rewritten when an entry is dropped or elided.
The sidecar is replaced by a marker rather than elided, because the verbatim
head and tail already live in the block beside it. When a record carries more
than one `tool_result` block the sidecar cannot be attributed to either, so it
is left alone and not counted.

On real transcripts this is deliberately quiet: measured across six sessions of
6–12 MB, it dropped nothing and elided 0–32% of tool-result bytes. A 0% plan is
a correct answer for a transcript with no supersessions and no oversized
results, not a threshold to tune away.

## The Jev veto

When `lib/jev` resolves a provider, `plan()` sends **one** batched request
carrying a bounded digest of the candidate entries and asks, per entry, whether
it is still needed. The answer is a veto, not a proposal:

- "still needed" moves an entry one step toward keeping (`drop` → `truncate`,
  `truncate` → `keep`)
- "not needed" demotes a `keep` no further than `truncate`
- nothing it says can turn a `keep` into a `drop`
- an answer with `source !== "jev"` is discarded entirely — lexical overlap is
  not a judgment about whether information is still needed

A confidently wrong decision model therefore costs tokens. It cannot cost
information. With no provider configured the module never calls out at all and
reports `source: "heuristic"`.

## Options

| Field                             | Default        | Meaning                                        |
| --------------------------------- | -------------- | ---------------------------------------------- |
| `keepRecent`                      | `30`           | Exchanges from the end that are always kept    |
| `smallBytes`                      | `2000`         | Results below this are never touched           |
| `hugeBytes`                       | `20000`        | Old unsuperseded results above this get elided |
| `keepHeadBytes` / `keepTailBytes` | `1200` / `600` | Verbatim bytes kept by an elision              |
| `maxJevQuestions`                 | `80`           | Cap on entries sent for review                 |
| `useJev`                          | `true`         | `false` forces the heuristic                   |
| `jev`                             | —              | Inject a decision layer. Tests only.           |

Out-of-range and non-numeric options are clamped or ignored rather than raising.
