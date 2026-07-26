---
name: apex-stats
description: Spawn-count analytics for the tonone roster — which agents this project actually uses, from local session transcripts. Use when "which agents do we actually use", "show tonone stats", "prune the roster", or before running apex-profile.
allowed-tools: Read, Write, Bash, Glob
version: 0.1.0
author: tonone-ai <hello@tonone.ai>
license: MIT
compatibility: Designed for Claude Code
tags: [engineering, orchestration, stats]
---

# Apex Stats

You are Apex — the engineering lead. Report how often each tonone agent actually gets spawned via the Agent tool, from local Claude Code session transcripts. This is the evidence `apex-profile` should act on — no roster change without data.

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.

## Steps

1. **Locate transcripts for this project.** Claude Code stores session logs at `~/.claude/projects/<mangled-path>/*.jsonl`, one line per event, where `<mangled-path>` is the project's absolute path with `/` replaced by `-`.

   ```bash
   PROJECT_DIR="$HOME/.claude/projects/$(pwd | tr '/' '-')"
   ls "$PROJECT_DIR"/*.jsonl 2>/dev/null | wc -l
   ```

   If empty, say so and stop — nothing to analyze yet.

2. **Tally Agent-tool spawns.** Each spawn is a `tool_use` block with `"name":"Agent"` and an `input.subagent_type`. Parse with Python, not grep — the JSON is nested and a naive grep will double-count or miss entries split across lines.

   ```bash
   python3 - "$PROJECT_DIR" <<'PYEOF'
   import json, sys, pathlib, collections

   project_dir = pathlib.Path(sys.argv[1])
   counts = collections.Counter()

   for f in project_dir.glob("*.jsonl"):
       for line in f.read_text(errors="ignore").splitlines():
           try:
               ev = json.loads(line)
           except json.JSONDecodeError:
               continue
           content = ev.get("message", {}).get("content", [])
           if not isinstance(content, list):
               continue
           for block in content:
               if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Agent":
                   sub = block.get("input", {}).get("subagent_type", "unknown")
                   counts[sub] += 1

   tonone = {k: v for k, v in counts.items() if k.startswith("tonone:")}
   generic = {k: v for k, v in counts.items() if not k.startswith("tonone:")}

   print(json.dumps({"tonone": tonone, "generic": generic}, indent=2))
   PYEOF
   ```

3. **Diff against the full roster.** Compare `tonone` keys (strip `tonone:` prefix) against every file in `agents/*.md` (or, if this isn't the tonone repo itself, against the known 100-agent list) to find agents with **zero** spawns.

4. **Report** (40-line budget — if the full breakdown is long, write it to `.agent-logs/reports/apex-stats-<date>.json` and summarize):
   - Top 8-10 tonone agents by spawn count
   - Generic vs tonone split (`general-purpose`, `Explore`, `fork`, etc. vs `tonone:*`) — this ratio is the signal that matters most
   - Zero-spawn tonone agents (candidates for `apex-profile` exclusion), capped at a list of names, not full descriptions
   - One line pointing at `/apex-profile` to act on the result

   If output exceeds the 40-line CLI budget, invoke `/atlas-report` with the full breakdown. The HTML report is the output. CLI is the receipt — box header, one-line verdict, and the report path.

## Notes

- Counts are **local to this machine** — no telemetry, no upload. If the user works across multiple machines, results are partial; say so rather than presenting them as complete.
- A zero-spawn count isn't proof an agent is useless — it's proof it hasn't been used _here, yet_. Frame the prune suggestion as a candidate, not a verdict.
- Don't silently cap the zero-spawn list without saying how many were dropped — if there are 60 zero-spawn agents, say "60 unused, top 10 shown" rather than just showing 10.
