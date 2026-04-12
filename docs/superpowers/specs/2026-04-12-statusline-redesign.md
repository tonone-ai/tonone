# Statusline Redesign Spec

Three-line CLI status bar for Claude Code sessions. Replaces the current two-line design that suffers from symbol soup, cognitive overload, and layout instability.

## Layout

Three lines, grouped by mental model:

```
Line 1  ~/repos/tn/tonone │ main ↑3 │ 2 dirty │ +156 -23 lines
Line 2  spine │ subs: audit pipeline, check deps │ $0.38 │ 23m
Line 3  Opus → Sonnet │ ████░░░░░░ 48% │ 5h: 24% ok 0.6× │ 7d: 41% ok 0.8×
```

| Line | Theme | Segments |
|------|-------|----------|
| 1 | **Where** — location & code state | directory, branch + ahead, dirty count, lines changed |
| 2 | **What** — session activity | agent + subs, cost, duration |
| 3 | **How much left** — runway gauges | model(s), context window, 5h pace, 7d pace |

## Static Fields

All segments are always visible. No progressive disclosure. When a value is zero or unavailable, show a dim placeholder instead of hiding the segment:

| Segment | Active | Empty/Zero |
|---------|--------|------------|
| Directory | `~/repos/tn/tonone` | always present (from cwd) |
| Branch | `main ↑3` | `main` (no ↑ when 0) |
| Dirty | `2 dirty` (yellow) | `clean` (dim) |
| Lines | `+156 -23 lines` (green/red) | `+0 -0 lines` (dim) |
| Agent | `spine` (magenta bold) | `idle` (dim) |
| Subs | `subs: audit, recon` (magenta) | `no subs` (dim) |
| Cost | `$0.38` | `$0.00` (dim) |
| Duration | `23m` | `0m` (dim) |
| Model | `Opus → Sonnet` | `Opus 4.6` (just main, no arrow) |
| Context bar | `████░░░░░░ 48%` | `░░░░░░░░░░ 100%` (dim) |
| 5h pace | `5h: 24% ok 0.6×` | `5h: 0% --` (dim) |
| 7d pace | `7d: 41% ok 0.8×` | `7d: 0% --` (dim) |

## Segment Details

### Line 1: Location & Git

1. **Working directory** — `data.workspace.current_dir`. Replace `$HOME` prefix with `~`. If the result exceeds 40 characters, truncate from the left with `…/` prefix (e.g., `…/tn/tonone`). Dim white.
2. **Branch + ahead** — `git rev-parse --abbrev-ref HEAD` + `git rev-list --count @{u}..HEAD`. Branch in cyan, `↑N` in green. Omit `↑` entirely when 0 (no dim placeholder for this sub-element — branch name alone is stable enough).
3. **Dirty count** — `git status --porcelain` line count. Yellow `N dirty` when >0, dim `clean` when 0.
4. **Lines changed** — `data.cost.total_lines_added` / `total_lines_removed`. Green `+N`, red `-N`, dim label `lines`. All dim when both are 0.

### Line 2: Session Activity

1. **Agent name** — `data.agent.name`. Magenta bold when active, dim `idle` when none.
2. **Subagent list** — Read from bridge file `/tmp/tonone-agents-{session}.json`. Show active agent descriptions (truncated to 20 chars each). Format: `subs: desc1, desc2`. If >3 active: `subs: desc1, desc2, +N more`. Dim `no subs` when none. Magenta color. Also track `model` field in bridge file for Line 3 display.
3. **Session cost** — `data.cost.total_cost_usd`. Dim white normally, yellow >$1, red >$5.
4. **Session duration** — `data.cost.total_duration_ms`. Formats: `0m`, `23m`, `1h12m`. Dim white.

### Line 3: Model & Runway

1. **Model display** — `data.model.display_name` for main model. When subagents are active on a different model (read from bridge file), show `Main → Sub` (e.g., `Opus → Sonnet`). If subs use multiple different models: `Opus → Sonnet, Haiku`. When no subs or all subs on same model as main: just `Opus 4.6`. Dim white, arrow dim.
2. **Context window bar** — `data.context_window.remaining_percentage`. 10-block meter. Color escalation: green >50%, yellow >25%, red >10%, blinking red ≤10%. Append `compact soon` text at ≤10%.
3. **5-hour pace** — `data.rate_limits.five_hour`. Format: `5h: N% verdict X.X×`. See Pace Calculation below.
4. **7-day pace** — `data.rate_limits.seven_day`. Same format: `7d: N% verdict X.X×`.

## Pace Calculation

### Bridge File

New file: `/tmp/tonone-pace-{session}.json`

Created by the statusline script itself (not a separate hook) on first render for a session. Format:

```json
{
  "session_id": "abc123",
  "start_time": 1712959264000,
  "start_5h_pct": 18.0,
  "start_7d_pct": 35.0
}
```

### Algorithm

For each rate limit window (5h and 7d):

```
session_elapsed_hours = (now - start_time) / 3_600_000
session_burn = current_pct - start_pct
burn_rate = session_burn / session_elapsed_hours    (% per hour)

time_remaining_hours = (resets_at - now) / 3_600_000
projected_additional = burn_rate * time_remaining_hours
projected_total = current_pct + projected_additional

pace_multiplier = burn_rate / safe_rate
  where safe_rate = (100 - current_pct) / time_remaining_hours
```

### Verdict Logic

| Condition | Verdict | Color |
|-----------|---------|-------|
| Session < 2 minutes | `--` | dim |
| `projected_total ≤ 80` | `ok` | green |
| `projected_total ≤ 100` | `tight` | yellow |
| `projected_total > 100` | `~Xm` or `~Xh` (time to impact) | red |

Time to impact = `(100 - current_pct) / burn_rate`, formatted as minutes or hours.

Pace multiplier always shown next to verdict: `ok 0.6×`, `tight 1.4×`, `~18m 2.1×`. Same color as verdict.

### Edge Cases

- `burn_rate = 0` (session hasn't consumed any of this window): show `ok 0.0×` in green
- `resets_at` missing or past: show `--` dim
- `session_burn < 0` (window reset during session, start_pct was from old window): re-initialize bridge file with current values
- Bridge file missing or corrupt: create fresh one, show `--` for first render

## Agent Tracker Changes

The existing `tonone-agent-tracker.js` bridge file needs a `model` field added to each agent entry:

```json
{
  "agents": [
    {
      "id": "agentId",
      "desc": "audit pipeline",
      "model": "sonnet",
      "started": 1712959264000,
      "finished": null
    }
  ]
}
```

Source: `data.tool_input.model` from the Agent tool call (falls back to `null` if not specified, meaning same as parent model).

## Colors

| Element | ANSI | Code |
|---------|------|------|
| Directory | dim white | `\x1b[2;37m` |
| Branch | cyan | `\x1b[36m` |
| ↑N | green | `\x1b[32m` |
| Dirty count | yellow | `\x1b[33m` |
| "clean" | dim | `\x1b[2m` |
| Lines +N | green | `\x1b[32m` |
| Lines -N | red | `\x1b[31m` |
| Agent name | magenta bold | `\x1b[35m\x1b[1m` |
| Sub names | magenta | `\x1b[35m` |
| "idle", "no subs" | dim | `\x1b[2m` |
| Cost normal | dim white | `\x1b[2;37m` |
| Cost >$1 | yellow | `\x1b[33m` |
| Cost >$5 | red | `\x1b[31m` |
| Duration | dim white | `\x1b[2;37m` |
| Model names | dim white | `\x1b[2;37m` |
| Arrow → | dim | `\x1b[2m` |
| Context bar >50% | green | `\x1b[32m` |
| Context bar >25% | yellow | `\x1b[33m` |
| Context bar >10% | red | `\x1b[31m` |
| Context bar ≤10% | blink red | `\x1b[5m\x1b[31m` |
| Pace ok | green | `\x1b[32m` |
| Pace tight | yellow | `\x1b[33m` |
| Pace ~Xm | red | `\x1b[31m` |
| Pace -- | dim | `\x1b[2m` |
| Separators │ | dim | `\x1b[2m` |

## Files Modified

1. `hooks/tonone-statusline.js` — full rewrite of `render()` function
2. `hooks/tonone-agent-tracker.js` — add `model` field from `tool_input.model`

## Files Created

None. Pace bridge file is written at runtime to `/tmp/`.

## States to Test

1. Fresh session (all fields at zero/empty)
2. Active session with agent + subs on different model
3. Active session, no agent running
4. Warning state (context <25%, rate limit >70%)
5. Critical state (context <10%, rate limit >90%, pace showing time to impact)
6. Window reset during session (bridge file re-initialization)
7. Very long directory path (truncation behavior)
