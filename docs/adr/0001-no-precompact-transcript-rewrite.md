# 0001. Ship verbatim compaction as an on-demand skill, not a PreCompact hook

**Date:** 2026-09-20
**Status:** Accepted

## Context

The Jev decision layer at `lib/jev/` makes per-entry yes/no decisions cheap
(~325ms, roughly $0.000013 per decision, batched into a single request). The
obvious application is verbatim context compaction: instead of letting the
built-in compactor summarize the conversation — which paraphrases, and so can
silently lose an exact error string, a file path or a stated constraint — score
each tool call and tool result, drop or elide the stale ones, and keep
everything else byte-for-byte. The upstream reference implementation,
`imadcat/fast-jev-compaction`, does exactly this.

The plan assumed this would hang off a `PreCompact` hook, because that is the
one lifecycle event whose name matches. Before building, we spiked whether
`PreCompact` in the Claude Code on this machine (2.1.278) can actually inspect
and modify what gets compacted. The evidence, gathered from the shipped binary
and the public docs:

- `PreCompact` exists and is a real command-hook event. Its input is the base
  hook input (`session_id`, `transcript_path`, `cwd`, ...) plus
  `hook_event_name`, `trigger` (`"manual" | "auto"`) and `custom_instructions`.
  So it can **read** the transcript.
- Its output is not a transcript. The internal hook runner collects three
  things and nothing else: `blockedBy` (exit 2 blocks compaction entirely),
  `newCustomInstructions` (stdout, appended to the summarizer prompt as
  natural-language instructions), and `userDisplayMessage`. The binary's own
  hook reference states it plainly: "Exit code 0 — stdout appended as custom
  compact instructions. Exit code 2 — block compaction."
- The `hookSpecificOutput` schema is a discriminated union over hook event
  names. It has members for `PreToolUse`, `PostToolUse` (including
  `updatedToolOutput`), `SessionStart`, `Stop`, `MessageDisplay` and fifteen
  others. It has **no** `PreCompact` member at all. There is no field a
  `PreCompact` hook could return to change the messages.
- Compaction reads the in-memory message array, not the transcript file. The
  transcript on disk is an append-only session log. Rewriting it would not
  change what is compacted, and would corrupt `--resume`.
- The public docs at `code.claude.com/docs/en/hooks` list `PreCompact` in the
  event table but ship no input schema, no output fields and no statement about
  whether it can modify what gets compacted. Building on it would have meant
  building on an assumption.

The spike also found the surface that _would_ work, and it is not a
`hooks.json` hook. Claude Code has a second, in-process hook system — "function
hooks", JS/TS modules named from a plugin's `hooks.json` `modules` key — whose
event list includes `session.compact`. That handler receives
`{ trigger, agentId?, instructions?, messages }` and may return
`{ messages }`; when it does, the runner logs "a hook's N messages stand" and
those messages replace the compaction result verbatim. This is what
`fast-jev-compaction` hooks. It is gated behind the `tengu_plugin_hooks_modules`
feature flag, overridable with `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`, is absent
from the public hook documentation, and is not enabled for this machine.

## Decision

We do not build a `PreCompact` hook. Verbatim selection ships as
`lib/compact/transcript-select.js` plus the user-invocable `/token-compact`
skill, which runs the selection on demand against a transcript file and reports
what it would drop, truncate and keep. Automatic compaction is left to Claude
Code.

## Alternatives Considered

### Register a `session.compact` function hook, like upstream does

**Pros:** It is the real thing. Messages are replaced verbatim; there is no
summarizer in the path at all. It is the mechanism the reference implementation
already proves works.
**Cons:** Requires `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1` or a feature-flag
rollout, so it is off for every user by default and we could not test it here.
The event is undocumented publicly, so its argument and result shapes are
version-coupled to an internal schema that can change without a deprecation.
The module is linked and scanned by a loader with its own budget semantics,
which is a much larger surface than a CommonJS file exiting 0. Wiring it also
requires a `modules` key in `hooks.json`.
**Why not:** A default path that is dark for everyone and coupled to an
undocumented internal schema fails the "works with zero configuration" bar this
repo holds every other hook to.

### Use `PreCompact` to inject custom compact instructions

**Pros:** Fully documented behavior, works today, one small script. We could
compute which entries matter and tell the summarizer, in prose, to preserve
them.
**Cons:** The summarizer is still a summarizer. "Preserve the exact error
string from entry 41" is a request, not a guarantee, and the whole point of
this workstream is that paraphrase is the failure mode. It would look like
verbatim compaction while being nothing of the kind.
**Why not:** It would fake the feature. Dropping information less often is not
the same promise as never rewriting what is kept.

### Use `PreCompact` to block compaction and rewrite the transcript file

**Pros:** `PreCompact` can block (exit 2), and it does receive
`transcript_path`.
**Cons:** Compaction operates on in-memory messages; the file is an append-only
log. Rewriting it changes nothing about the next compaction and breaks
`--resume` and `/resume` for that session. Blocking compaction outright pushes
the session toward a hard context limit.
**Why not:** It does not work, and the way it fails is data loss.

## Consequences

**What becomes easier:**

- The selection logic is exercised and testable today. `lib/compact/transcript-select.js`
  runs with zero credentials and zero network, and `tests/test_compact.js`
  covers it without either.
- When `session.compact` becomes generally available, the adapter is small: the
  ranking, the veto semantics and the verbatim guarantee are already written and
  tested. Only the message-shape translation is missing.
- Nothing in the automatic compaction path can be broken by our code, because we
  are not in it.

**What becomes harder or more expensive:**

- Compaction is not automatic. A user has to run `/token-compact`, and the
  result is a report, not an applied change to the live session.
- The emitted JSONL is useful for inspection and for feeding a fresh session,
  not for editing a session in place.

**What this decision constrains:**

- `lib/compact/transcript-select.js` must stay pure and synchronous-capable
  (`planSync`) so a future `session.compact` handler can call it inside a hook
  module's time budget.
- The Jev call must stay strictly a veto that can only move an entry toward
  keeping. A future automatic path will run without a human reading the plan
  first, and that is only safe if a confidently wrong model costs tokens rather
  than information.

## What to watch for

- `session.compact` appearing in the public hook docs, or
  `tengu_plugin_hooks_modules` defaulting on. Either is the signal to build the
  adapter. Re-check with:
  `strings "$(readlink -f "$(command -v claude)")" | grep -c CLAUDE_CODE_ENABLE_FUNCTION_HOOKS`
- A `PreCompact` member appearing in the `hookSpecificOutput` union, which would
  mean command hooks gained a say in compaction after all.
- Upstream `imadcat/fast-jev-compaction` changing its registration away from
  `session.compact`, which would mean a better-supported surface exists.
