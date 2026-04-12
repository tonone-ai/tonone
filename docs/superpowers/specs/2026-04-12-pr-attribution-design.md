# PR Attribution — Design Spec

**Date:** 2026-04-12  
**Status:** Draft  
**Goal:** Increase K-factor by making tonone visible in PRs — team credits that create FOMO for other Claude Code users.

---

## Problem

K-factor 0.05–0.15. No attribution in output means tonone is invisible to everyone except the person running it. PRs are the highest-visibility artifact in any team's workflow — teammates, leads, and reviewers all read them.

## Scope

- Agent session tracking: skills write their name to `.claude/session-agents` on activation
- PR hook: reads session agents, appends attribution block to PR description
- Attribution format: agent credits + tonone link

## Out of Scope

- Doc/spec footers (future)
- Commit message attribution (future)
- Share moments / tweet generation (future)
- Attribution in non-PR git output (future)

---

## Design

### 1. Session Agent Tracking

Each tonone skill appends its agent name to `.claude/session-agents` when it activates. This file lives in the repo root under `.claude/` alongside other Claude Code session files.

**File:** `.claude/session-agents`  
**Format:** One agent name per line, lowercase, deduplicated on read.

```
spine
warden
proof
atlas
```

**Write mechanism:** Each skill's entrypoint shell block appends to the file:

```bash
echo "spine" >> .claude/session-agents
```

Skills already run bash at activation — this is a one-liner addition to each skill's preamble.

**Lifecycle:** File is cleared at the start of each new PR hook run (post-write). This scopes credits to the session that produced the PR, not accumulated history. If no PR is created, the file accumulates and clears on next PR.

**Deduplication:** Hook deduplicates lines on read — if spine is invoked 5 times, it appears once in credits.

---

### 2. PR Attribution Hook

**Trigger:** PostToolUse on Bash, pattern match on `gh pr create`.

**Mechanism:** After `gh pr create` succeeds, hook runs `gh pr edit` to append the attribution block to the PR body.

Why PostToolUse + edit (not PreToolUse injection):
- `gh pr create` accepts `--body` but intercepting and rewriting arbitrary shell arguments in a hook is fragile
- PostToolUse + `gh pr edit --body "$(gh pr view --json body -q .body)<attribution>"` is clean and reliable
- Downside: two API calls instead of one. Acceptable.

**Hook reads:** `.claude/session-agents`, deduplicates, sorts alphabetically, formats credits.

**Clears:** `.claude/session-agents` after appending to PR (so next session starts fresh).

**No agents logged:** If `.claude/session-agents` is empty or missing, hook appends minimal attribution: `*— [tonone](link)*`. Never skips attribution entirely.

---

### 3. Attribution Format

Appended as a final section in the PR description, separated by a horizontal rule:

```markdown

---
*Spine · Warden · Proof — [tonone](https://claude.ai/plugins/tonone)*
```

Rules:
- Agent names title-cased
- Alphabetical order
- Max 5 agents shown; if more, truncate to top 5 + "and N more"
- Single line — no headers, no extra explanation
- Link target: tonone plugin registry page

**What it looks like in a real PR:**

```
## Summary
- Redesigned auth middleware to use short-lived tokens
- Added rate limiting on login endpoint

## Test plan
- [ ] Token expiry tested at boundary
- [ ] Rate limiter verified under load

---
*Atlas · Spine · Warden — [tonone](https://claude.ai/plugins/tonone)*
```

---

### 4. Implementation Components

| Component | Location | Type |
|---|---|---|
| Session write | Each skill preamble | bash one-liner |
| PR hook | `team/relay/hooks/tonone-pr-attribution.js` | PostToolUse JS hook |
| Hook registration | `team/relay/`.claude-plugin`/plugin.json` | PostToolUse Bash |
| Tests | `team/relay/tests/test-pr-attribution.js` | Unit tests |

Relay owns this — it lives in DevOps/GitOps territory (PR lifecycle, CI/CD hooks).

---

### 5. Edge Cases

| Case | Behavior |
|---|---|
| No `gh pr create` in session | Hook never fires, file accumulates until next PR |
| `gh pr create` fails | Hook still fires (PostToolUse fires on tool completion regardless) — check exit code, skip edit if PR creation failed |
| Multiple PRs in one session | Attribution appended to each; file cleared after first (subsequent PRs show only agents since last PR) |
| `.claude/session-agents` missing | Hook appends `*— [tonone](link)*` without agent names |
| User manually strips attribution | Out of scope — not worth defending against |

---

## Success Metrics

- K-factor moves from 0.05–0.15 toward 0.20+ within 60 days of shipping
- Attribution visible in ≥90% of PRs created during tonone sessions
- Zero user complaints about attribution being disruptive or breaking PR format

## Open Questions

- What is the exact plugin registry URL for tonone? (needed for link target)
- Do all 23 agent skills get the session-write one-liner, or only a subset (e.g., only skills that produce substantial output)?
