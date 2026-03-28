# Bundle Plugin + Discoverable Names

**Date:** 2026-03-28
**Status:** Approved

## Problem

1. No way to install all 13 agents at once — users must run `/plugin install` 13 times.
2. Agent names (prism, forge, vigil) don't tell users what they do without memorization.

## Solution

### Discoverable plugin names

Rename each plugin to `<agent>-<role>` so listings are self-documenting:

| Agent  | Plugin name     | Agent name (unchanged) |
| ------ | --------------- | ---------------------- |
| apex   | apex-lead       | apex                   |
| forge  | forge-infra     | forge                  |
| relay  | relay-devops    | relay                  |
| spine  | spine-backend   | spine                  |
| flux   | flux-data       | flux                   |
| warden | warden-security | warden                 |
| vigil  | vigil-sre       | vigil                  |
| prism  | prism-frontend  | prism                  |
| cortex | cortex-ml       | cortex                 |
| touch  | touch-mobile    | touch                  |
| volt   | volt-embedded   | volt                   |
| atlas  | atlas-docs      | atlas                  |
| lens   | lens-analytics  | lens                   |

Only the `name` field in `plugin.json` and the keys in `marketplace.json` change. Agent definitions, directory names, and skill names stay the same.

### Bundle meta-plugin

An `engineering-team` plugin whose post-install hook installs all 13 agents.

**User flow:**

```
/plugin marketplace add tonone-ai/tonone
/plugin install engineering-team@tonone-ai
# All 13 agents installed automatically
```

**Structure:**

```
bundle/engineering-team/
  .claude-plugin/plugin.json    - manifest
  hooks/hooks.json              - post-install hook
  scripts/install-all.sh        - installs all agent plugins
```

**install-all.sh** uses a hardcoded list of plugin names. For each, runs `claude plugin install <name>@tonone-ai`. Falls back to printing copy-paste commands if `claude` CLI isn't available in hook context.

Hardcoded over dynamic because the list changes infrequently and avoids jq/JSON parsing dependencies.

### marketplace.json

Add `engineering-team` entry alongside the 13 agents (using new hyphenated names):

```json
{
  "engineering-team": {
    "path": "bundle/engineering-team",
    "description": "Install all 13 Engineering Team agents at once"
  },
  "apex-lead": { "path": "team/apex", ... },
  "forge-infra": { "path": "team/forge", ... }
}
```

## Scope

**In scope:**

- Rename `name` in all 13 `plugin.json` files
- Update `marketplace.json` keys to match
- Create `bundle/engineering-team/` with manifest, hook, script
- Update existing design docs to reflect new names

**Out of scope:**

- No directory renames (team/forge stays team/forge)
- No agent definition changes (agent names stay short)
- No skill changes
- No selective/interactive picker
