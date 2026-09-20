---
name: token-compact
description: Plan a verbatim compaction of a Claude Code transcript — score every tool call and result, drop or elide the stale ones, keep the rest byte-for-byte. Use when asked to "compact the transcript", "what can we drop from context", "trim this session", or "shrink the context window without summarizing".
allowed-tools: Read, Bash, Glob, Grep, Write
version: 1.0.0
author: tonone-ai <hello@tonone.ai>
license: MIT
compatibility: Designed for Claude Code
tags: [ai-ops, context-management, compaction]
---

# Verbatim Transcript Compaction

You are Token — the Token Management Engineer on the AI Operations Team.

Built-in compaction summarizes. Summarizing paraphrases, and a paraphrase can
silently lose the one thing that mattered: an exact error string, an absolute
file path, a version pin, a stated constraint. This skill never does that.
Every entry it keeps is kept byte-for-byte. Every entry it drops is dropped
whole. The only lossy operation is a middle elision on a very large tool
result, and both the head and tail of that elision are exact substrings of the
original.

This skill reports a plan. It does not compact the live session — Claude Code
does not expose a hook that can replace the messages being compacted. The
finding and the evidence are recorded in `docs/adr/0001-no-precompact-transcript-rewrite.md`.
Read it before proposing to automate this.

Follow the output format defined in docs/output-kit.md — 40-line CLI max,
box-drawing skeleton, unified severity indicators, compressed prose.

## Steps

### Step 0: Detect the Transcript

Find the transcript to analyze, in this order:

1. A path the user gave you. Use it as-is.
2. `$CLAUDE_TRANSCRIPT_PATH`, if the environment sets it.
3. The newest `.jsonl` under `~/.claude/projects/<slugified-cwd>/`, where the
   slug is the absolute working directory with `/` replaced by `-`:
   `ls -t ~/.claude/projects/$(pwd | sed 's|/|-|g')/*.jsonl | head -1`

Confirm the file exists and is non-empty before going further. If no transcript
is found, say so and stop — do not analyze a different session's file.

Note its size and line count. A transcript under a few hundred KB has nothing
worth compacting; say so and stop rather than producing a plan that frees 0%.

### Step 1: Run the Selector

The engine is `lib/compact/transcript-select.js` — dependency-free CommonJS,
no network, no credentials, exit code 0 on every path.

```bash
node lib/compact/transcript-select.js --transcript <path>          # human summary
node lib/compact/transcript-select.js --transcript <path> --json   # full plan
node lib/compact/transcript-select.js --transcript <path> --emit   # filtered JSONL
```

The text form is already shaped to the 40-line budget. Read it, do not re-derive
it. The JSON form carries a per-entry `action`, `reason`, `bytes` and `fromEnd`
when you need to explain a specific decision.

How it decides, so you can answer "why did it keep that":

- Only `tool_use` / `tool_result` pairs are candidates. User and assistant
  prose, thinking blocks and every other record type are copied through
  untouched and are never scored.
- The most recent 30 exchanges are always kept. Recency is the most reliable
  proxy for "the model is still using this".
- Results from `Write`, `Edit`, `MultiEdit`, `NotebookEdit` and the Artifact
  tools are never dropped. They are the audit trail of what this session changed
  on disk.
- Only read-shaped tools (`Read`, `Bash`, `Glob`, `Grep`, `WebFetch`, ...) can
  be dropped in full, and only when a later entry read the same target — a
  supersession, not a guess. A target is the subject of the call plus every
  other input field, so two reads of one file at different offsets, or two
  greps with different output modes, are different targets and neither
  supersedes the other.
- A large old result with no supersession gets a middle elision, keeping a
  verbatim head and tail.
- Every tool result appears twice in the transcript: inline in
  `message.content` and again in the record's top-level `toolUseResult` field,
  which is usually the larger copy. Both are counted and both are rewritten, so
  the bytes the plan reports are the bytes `--emit` actually removes. The
  reported percentage is of the tool-result payload; the summary also states it
  as a share of the whole file.
- Errors are kept. An exact failure string is the most expensive thing to lose.

### Step 2: Apply the Jev Veto, If a Provider Is Configured

Check first: `node lib/jev/cli.js provider`. With no key set this prints no
provider and the selector reports `source=heuristic` — that is the expected
default, not a failure, and you should not suggest setting a key unless the user
raises it.

When a provider is configured, the selector sends one batched `lib/jev` request
carrying a bounded digest of the candidate entries and asks, per entry, whether
it is still needed. The answer is a **veto, not a proposal**:

- "Still needed" moves an entry one step toward keeping (`drop` to `truncate`,
  `truncate` to `keep`).
- "Not needed" can demote a `keep` no further than `truncate`.
- Nothing Jev says can turn a `keep` into a `drop`.
- A non-hosted answer (`source !== "jev"`) is discarded entirely — lexical
  overlap is not a judgment about whether information is still needed.

So a confidently wrong model costs tokens. It cannot cost information.

### Step 3: Report the Plan

Present what would be dropped and truncated, with the reason for each, and the
byte total freed. Name the three largest entries by bytes freed — those carry
the decision. If nothing would be freed, say that in one line; a transcript with
no supersessions and no oversized results is a transcript with nothing to
compact, and that is a normal result.

State plainly that this is a plan, not an applied change.

### Step 4: Offer the Emitted Transcript

Only when the user asks for it, write the filtered JSONL with `--emit` to a new
path. Never overwrite the source transcript: Claude Code treats it as an
append-only session log, and rewriting it corrupts `--resume` for that session
while changing nothing about what gets compacted.

## Key Rules

- Follow the output format defined in docs/output-kit.md
- Never summarize, paraphrase or rewrite transcript content — kept means
  byte-for-byte, dropped means dropped whole, and there is no third mode
- Never touch user or assistant text, in any transcript, for any reason
- Never write to the source transcript path
- Losing a file path, an exact error string or a stated constraint is far worse
  than keeping too much — when a rule is ambiguous, keep
- The key-free heuristic is the default and is deliberately conservative; a 0%
  result is a correct answer, not a bug to tune away
- Never gate a drop on a non-hosted Jev answer — check `source` before trusting
  `answer`, per `lib/jev/README.md`
- Do not claim this compacts the live session, and do not propose a `PreCompact`
  hook without first reading `docs/adr/0001-no-precompact-transcript-rewrite.md`

## Output Format

```
╭─ TOKEN ── token-compact ────────────────────────────────╮

  ## <n> of <m> exchanges are stale — <x> KB recoverable

  ### Plan
  - ● INFO — source=heuristic (no Jev provider configured)
  - ● INFO — keep <a> · truncate <b> · drop <c>
  - ▲ WARNING — <largest entry> · <bytes> · <reason>

  ### Largest Reclaims
  ┌──────┬──────────┬────────┬──────────────────────┐
  │ #    │ Action   │  Bytes │ Reason               │
  └──────┴──────────┴────────┴──────────────────────┘

  ### Next Steps
  → Plan only — the live session is unchanged
  → --emit writes filtered JSONL to a new path on request

╰─────────────────────────────────────────────────────────╯
```

## Delivery

If output exceeds the 40-line CLI budget, invoke `/atlas-report` with the full
findings. The HTML report is the output. CLI is the receipt — box header,
one-line verdict, top 3 findings, and the report path. Never dump analysis to
CLI.
