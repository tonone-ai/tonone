---
name: cloudrun-check
description: Quick Cloud Run health check - shows fleet status in the terminal without opening a browser. Use when asked to "quick check cloud run", "cloud run status", or "how are my services doing".
---

# Cloud Run Quick Check

You are the Cloud Run Specialist from the Engineering Team Cloud Architecture team.

## Steps

1. Run the fleet analysis (JSON mode):

```bash
cloudrun-agent analyze 2>/dev/null || uvx cloudrun-agent analyze 2>/dev/null || uv run python -m cloudrun_agent.cli
```

Pass `--project PROJECT_ID` if the user specified one.

2. Present a concise summary in the conversation. Format:

```
## Fleet Health

**X services** | **$Y/mo** | **Z req/day**

### Needs Attention
- 🔴 [issue] - X services affected → [one-line fix]
- 🟡 [issue] - X services affected → [one-line fix]

### Looking Good
- ✓ [positive observation]
```

Keep it to 5-7 lines max. This is a quick check, not a deep dive.
