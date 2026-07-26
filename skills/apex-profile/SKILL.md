---
name: apex-profile
description: Scope the tonone agent roster for this project — install a curated subset of agents instead of the full 100-agent bundle. Use when "cut down the agent list", "profile for this project", "too many agents", "only need the engineering core", or after apex-stats shows a roster that's mostly unused.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
version: 0.1.0
author: tonone-ai <hello@tonone.ai>
license: MIT
compatibility: Designed for Claude Code
tags: [engineering, orchestration, profile]
---

# Apex Profile

You are Apex — the engineering lead. Scope the installed agent roster to what this project actually uses.

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.

## Why this exists

Each tonone agent is registered as its own plugin (`<agent>@tonone-ai`) in `.claude-plugin/marketplace.json`, self-contained with its own skills, hooks, and scripts. Installing the monolithic `tonone@tonone-ai` plugin registers all ~100 agents in every session regardless of project. Toggling individual agent plugins on/off via `enabledPlugins` in `.claude/settings.json` gives per-project scoping without any new plugin architecture — this skill automates writing that config correctly.

## Steps

1. **Read current state.** Check for an existing `.claude/settings.json` and `.claude/settings.local.json` in the project root. If either has an `enabledPlugins` block, show what's currently enabled (in particular, whether `tonone@tonone-ai` — the full bundle — is on).

2. **Ask how to pick the roster** (AskUserQuestion, single-select):
   - **Preset** — pick from a named project-type roster (below)
   - **Custom list** — user names the agents directly
   - **From apex-stats** — run `/apex-stats` first, then default the roster to every agent with at least one spawn in the lookback window
   - **Full roster (undo)** — revert to installing all agents

   Presets (curated, extend as needed — cite these verbatim, don't invent new ones without asking):

   | Preset           | Agents                                             |
   | ---------------- | -------------------------------------------------- |
   | `web-app`        | apex, spine, flux, prism, proof, warden, crest     |
   | `mobile-app`     | apex, touch, spine, flux, proof, warden            |
   | `platform-infra` | apex, forge, relay, terra, kube, vigil, warden     |
   | `security-audit` | apex, warden, red, blue, hunt, patch, chain, sast  |
   | `ml-product`     | apex, cortex, flux, feat, fit, score, drift, embed |

   Always include `apex` — it's the orchestrator and the front door for any takeover/status/review workflow, even in a scoped profile.

3. **Ask where to write it** (AskUserQuestion, single-select) — this is a real tradeoff, not a formality:
   - **`.claude/settings.json`** — committed, shared with the team, everyone gets the same scoped roster
   - **`.claude/settings.local.json`** — gitignored, this developer only, doesn't affect teammates

4. **Merge, don't overwrite.** Read the target file if it exists (else start from `{}`). Update only the `enabledPlugins` key, preserving every other key untouched:

   ```bash
   python3 - "$TARGET_FILE" "$ROSTER_CSV" <<'PYEOF'
   import json, sys, pathlib

   target = pathlib.Path(sys.argv[1])
   roster = [a.strip() for a in sys.argv[2].split(",") if a.strip()]

   data = json.loads(target.read_text()) if target.exists() else {}
   plugins = data.setdefault("enabledPlugins", {})

   if roster:
       plugins["tonone@tonone-ai"] = False
       for agent in roster:
           plugins[f"{agent}@tonone-ai"] = True
   else:
       # full roster / undo
       plugins["tonone@tonone-ai"] = True
       for key in list(plugins):
           if key != "tonone@tonone-ai" and key.endswith("@tonone-ai"):
               del plugins[key]

   target.parent.mkdir(parents=True, exist_ok=True)
   target.write_text(json.dumps(data, indent=2) + "\n")
   PYEOF
   ```

5. **Report.** Roster size vs full 100, which file was written, and that the change takes effect on the **next Claude Code session** (plugin enablement is read at startup, not live). Note each enabled agent brings its own skills automatically (e.g. `spine@tonone-ai` includes `spine-api`, `spine-design`, etc. — no separate skill toggles needed). If output exceeds the 40-line CLI budget, invoke `/atlas-report` with the full findings. The HTML report is the output. CLI is the receipt — box header, one-line verdict, and the report path.

## Notes

- This scopes the **Agent tool menu**, not this skill itself or other gstack/root skills — `apex-status`, `apex-profile`, etc. stay available regardless of roster.
- Disabling `tonone@tonone-ai` while enabling individual `<agent>@tonone-ai` plugins is intentional — the monolithic bundle and the per-agent plugins both register the same `agents/*.md` files, so leaving the bundle on defeats the scoping.
- If unsure which agents a project needs, run `/apex-stats` first — it's the evidence this skill should act on.
- **Recommended default:** install the lean core (the preset, not the full 100) and lean on `/apex-route` for occasional long-tail needs — that combination gets a small "Available agent types" listing every session AND full access to all 100 specialists. Reserve installing an extra agent natively for one that `apex-stats` shows is used often enough that the per-route persona-read cost isn't worth paying repeatedly.
