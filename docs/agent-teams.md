# Agent Teams vs Subagents

Which parallel-work mechanism Apex (or you) should reach for, what each costs, and how to split work so workers never collide. Read before turning on agent teams.

Verified against the Claude Code docs on 2026-11-09 ([agent teams](https://code.claude.com/docs/en/agent-teams), [costs](https://code.claude.com/docs/en/costs#agent-team-token-costs), [subagents](https://code.claude.com/docs/en/sub-agents)). The feature is experimental; re-check the docs before relying on any detail here.

## What each is

**Subagents.** Helpers spawned inside one session via the Agent tool. Each has its own context window, does a focused job, and returns a summary to the caller. The caller manages all coordination. This is how tonone works today: Apex dispatches specialists (Spine, Prism, Warden, ...) as subagents and consolidates their reports.

**Agent teams.** Experimental. One session is the team lead; teammates are separate full Claude Code sessions. They message each other directly and share a task list (pending / in progress / completed, with dependencies). You can talk to any teammate yourself. Limits per the docs: one team per session, no nested teams, no resumption of in-process teammates after `/resume`, task status can lag, shutdown can be slow.

## Cost

Agent teams cost more because every teammate is a full session with its own context. Docs say "significantly more tokens" and scale roughly linearly with active teammates. The costs page gives one figure: **about 7x a standard session when teammates run in plan mode**. Commonly cited community numbers (3-4x and up) are not from the docs; treat any multiplier as an estimate and measure with `/usage`.

Subagents cost less: verbose work stays in the subagent's context and only a summary returns. They still draw on your usage.

Cost controls from the docs: keep teams small (3-5 to start), use Sonnet for teammates, keep spawn prompts focused, shut teammates down when done.

## When Apex uses which

Default: **subagents**. Escalate to agent teams only when all three hold:

1. Workers must talk to each other mid-task (debate, share findings, challenge conclusions).
2. The task has clear file or topic boundaries per worker.
3. The user has opted in and the budget allows.

| Situation                                             | Use                              |
| ----------------------------------------------------- | -------------------------------- |
| Independent specialists, report back (audit fan-out)  | Subagents                        |
| One focused lookup, test run, log digest              | Subagent                         |
| Sequential steps, or many dependencies                | Single session                   |
| Several workers editing the same file                 | Don't parallelize; one owner     |
| Competing hypotheses on a bug; workers disprove peers | Agent team                       |
| Cross-layer feature where owners must agree on a seam | Agent team (if budget allows)    |
| Parallel review with distinct lenses, no cross-talk   | Subagents (cheaper, same result) |
| Routine or small task                                 | Single session                   |

## Enabling agent teams (opt-in)

Disabled by default. Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in your shell or in `settings.json`:

```json
{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
```

Gotchas from the docs:

- While enabled, a subagent that Claude _names_ on its own launches as a teammate, so teams can form without you asking. Set the variable to `0` to get plain subagents back.
- Interactive sessions only. With `-p` or the Agent SDK, no teammates spawn.
- Teammates do not inherit the lead's conversation; put task context in the spawn prompt. They load CLAUDE.md, MCP servers and skills.
- Teammates start in the lead's permission mode; no per-teammate mode at spawn.
- Tonone agent definitions can be named as teammate roles. The docs say a definition's `skills` are not applied to teammates, so a teammate relies on project/user skills instead.

tonone does not enable this for you. Nothing in the repo sets the flag.

## How to split work

Applies to subagents and teams alike.

- **Split by file ownership.** Each worker owns a disjoint set of paths. Never two workers on one file; concurrent edits overwrite.
- **Lead owns shared files.** CHANGELOG, indexes (`docs/*.json`), README, CLAUDE.md, manifests. Workers report what should change; the lead integrates once, at the end.
- **Explicit "don't touch" list per worker.** Name the paths outside its scope, including the shared files above. Absence of a rule is permission.
- **Brief like a peer.** Goal, owned paths, don't-touch paths, what is already ruled out, output format. The worker has no other context.
- **Size tasks to a deliverable.** A file, a test suite, a review. Too small and coordination outweighs the gain; too large and workers drift unchecked.
- **Verify before consolidating.** Check each worker's evidence (paths, command output) before merging findings; see Apex's fan-out rule.
- **Start with read-only work.** Research and review have no write conflicts and show the value first.

## Boundaries of this doc

Covers the decision, not the mechanics. For panes, hooks (`TeammateIdle`, `TaskCreated`, `TaskCompleted`) and troubleshooting, use the [agent teams docs](https://code.claude.com/docs/en/agent-teams). For how Apex routes work, see [agent-guide.md](agent-guide.md).
