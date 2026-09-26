# Reddit post — r/ClaudeAI (also fits r/ClaudeCode)

**Status:** Draft, not yet posted. The opening paragraph ("My problem with long Claude Code tasks...") is a guess at your motivation. Rewrite it in your own words before posting; Reddit spots borrowed voice fast.

**Flair:** Built with Claude (r/ClaudeAI requires it for project posts, plus a disclosure that you built it)

**Image:** attach `launch/demo-apex-plan.png`. Reddit does not render SVG.

**Timing:** a weekday morning US time. Stay in the comments for the first two hours. Reply to every question, and take criticism without arguing.

## Title

```
I got tired of Claude Code starting big tasks without telling me what they'd cost, so I built a lead agent that scopes first
```

## Body

```
Disclosure: I built this. It's MIT, free, and there is no paid tier.

My problem with long Claude Code tasks was that I didn't know how big they
would get until they were done. "Add auth" could be a 20 minute job or a
two hour one that touched the schema, CI and half the UI.

So the entry point of tonone is a lead agent (Apex) that plans before it
builds. You describe the task and it comes back with depth tiers: which
specialist agents each tier uses, a rough token budget, a rough cost, and
what you get. You pick one, then it runs. The screenshot is an unedited
answer for "add user auth to a Next.js + Postgres app".

A few things worth knowing:

- It is opinionated. For auth it refused to offer an XS tier, because
  skipping the security review isn't acceptable there.
- The specialists are plain markdown agents and skills, nothing hidden.
  There are 100 agents in total (engineering, product, design, security,
  legal, ops...), but you don't have to load them all. /apex-profile
  trims the roster per project.
- Cost numbers are estimates from a blended token rate, not billing data.
  Treat them as "S is about a sixth of L", not as a quote.

Install:

  claude plugin marketplace add tonone-ai/tonone
  claude plugin install tonone@tonone-ai

Then: /apex-plan <what you want to build>

Repo: https://github.com/tonone-ai/tonone

I'd especially like to hear where the tiering is wrong for your kind of
work. That is the part I'm least sure about.
```

## Replies to prepare

- **"100 agents is bloat / eats context."** A skill gate hook loads only the skills a project needs (in my setup it cut the tokens spent on skill listings by about 90%), and `/apex-profile` scopes the agent roster. Give numbers, don't argue.
- **"How accurate are the costs?"** Rough and relative, from a blended rate. Say that plainly.
- **"Why not just prompt Claude to plan?"** You can. This packages the plan format, the stop-before-building rule and the specialist handoffs, so you get the same shape every time.
