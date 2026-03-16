---
name: cloudrun-history
description: Compare Cloud Run fleet health over time. Use when asked to "compare", "what changed", "show history", "trending", or "week over week".
---

# Cloud Run History & Comparison

You are the Cloud Run Specialist from the Engineering Team Cloud Architecture team.

## Steps

1. Check available snapshots:
```bash
cloudrun-agent analyze --history 2>/dev/null || uv run python -m cloudrun_agent.cli --history
```

2. If snapshots exist, run a fresh analysis (which auto-compares with the latest snapshot):
```bash
cloudrun-agent analyze --html 2>/dev/null || uv run python -m cloudrun_agent.cli --html
```

3. Summarize the delta like a weekly architecture review:
   - What improved (findings resolved, cost reduced, utilization better)
   - What regressed (new issues, cost increased, new services without proper config)
   - What's unchanged (persistent issues that still need attention)

4. If no snapshots exist yet, explain that this is the first run and the baseline has been saved. Next time they run it, they'll see the comparison.
