# dev.to / blog post

**Status:** Draft, not yet posted. First-person lines are a guess at your voice; rewrite them before posting. Cross-post to Hashnode and Medium with `canonical_url` pointing at the first copy.

**Tags (dev.to allows 4):** `claude`, `ai`, `productivity`, `opensource`

**Cover image:** `launch/demo-apex-plan.png`, cropped to the tier block.

---

# Make your coding agent quote before it builds

Give a coding agent "add user auth" and it starts typing. Twenty minutes later you find out whether you asked for a login form or a schema migration, an email flow, OAuth and a CI job. The size of the task was decided by the agent, silently, while it worked.

Human teams don't work like that. Someone scopes the work first, and the person paying picks how much of it to do.

That is the one habit I built into [tonone](https://github.com/tonone-ai/tonone), an MIT plugin for Claude Code. Its lead agent, Apex, answers a build request with a menu before it touches a file.

## What the menu looks like

This is an unedited answer to `/apex-plan Add user authentication to our SaaS (Next.js + Postgres)`:

```
S — Quick & focused (Spine + Warden, ~40K tokens, ~$0.25)
    Library-based email+password or OAuth login, sessions,
    protected routes. One security pass. No reset flow or CI.

M — Solid implementation (Spine + Warden + Flux + Prism,
    ~130K tokens, ~$0.80)
    Schema and migrations (users, sessions, accounts, tokens),
    signup/login/logout, password reset, email verify, OAuth
    provider, middleware route guards, UI forms, rate limit on
    auth endpoints, reviewed.

L — Full build-out (+ Relay + Vigil + Atlas, ~260K, ~$1.60)
    M plus CI with auth tests, login/failure metrics and alerts,
    auth-flow ADR and docs.

XL — Production-hardened (+ Proof + Forge, ~450K, ~$2.70)
     L plus E2E suite for every auth path, MFA/TOTP, account
     lockout, secrets/infra review, session-store perf check.

Not shown: XS (a skipped security review isn't acceptable for
auth) and XXL (this isn't a system migration).
```

Three things in that answer do the work.

**Each tier names who does it.** Spine is the backend agent, Warden security, Flux data, Prism frontend. Knowing which specialists are involved tells you what will actually change: if Flux is in the tier, there will be a migration.

**Each tier has a price.** The numbers are rough, from a blended token rate, and are meant to be read relative to each other: S is about a sixth of L. That is enough to make a real decision.

**It refuses some options.** No XS tier for auth, because the one thing you can't skip there is the security review. A menu that offers everything isn't a recommendation.

## Why specialists instead of one big prompt

Each of the 100 agents in tonone is a markdown file that owns one domain, with its own skills (also markdown). When Apex hands work to Warden, Warden loads a security-review workflow, not a general "be careful" instruction. Narrower context, more specific checklists.

The obvious cost is context: 100 agents and 429 skills would be a lot to load into every session. Two things keep it down. A session-start hook scores the skill catalogue against the current repo and hides the irrelevant ones, and `/apex-profile` trims the agent roster per project.

## Try it

```bash
claude plugin marketplace add tonone-ai/tonone
claude plugin install tonone@tonone-ai
```

Then run `/apex-plan <whatever you were about to ask for>`, and pick a tier.

The repo is at [github.com/tonone-ai/tonone](https://github.com/tonone-ai/tonone). I'm most interested in where the tiers come out wrong for your kind of work.
