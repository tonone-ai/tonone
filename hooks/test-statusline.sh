#!/usr/bin/env bash
# Test statusline rendering with JSON fixtures piped to stdin.
# Usage: bash hooks/test-statusline.sh
set -euo pipefail

SCRIPT="hooks/tonone-statusline.js"
PASS=0
FAIL=0

run_test() {
	local name="$1"
	local json="$2"
	shift 2
	local expected=("$@")

	echo "── $name ──"
	local output
	output=$(echo "$json" | node "$SCRIPT" 2>/dev/null) || true
	echo "$output"
	echo ""

	local ok=true
	for pattern in "${expected[@]}"; do
		# Strip ANSI codes for matching
		local stripped
		stripped=$(echo "$output" | sed 's/\x1b\[[0-9;]*m//g')
		if ! echo "$stripped" | grep -qF -- "$pattern"; then
			echo "  FAIL: expected '$pattern' not found"
			ok=false
		fi
	done

	if $ok; then
		echo "  PASS"
		((PASS++))
	else
		((FAIL++))
	fi
	echo ""
}

# State 1: Fresh session
run_test "Fresh session" '{
  "session_id": "test-fresh",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {}
}' \
	"~/repos/tn/tonone" \
	"+0 -0 lines" \
	"idle" \
	"no subs" \
	'$0.00' \
	"0m" \
	"Opus 4.6" \
	"5h: 0% --" \
	"7d: 0% --"

# State 2: Active session with agent (no subs)
run_test "Active session, no subs" '{
  "session_id": "test-active",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "agent": {"name": "spine"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {"total_cost_usd": 0.38, "total_duration_ms": 1380000, "total_lines_added": 156, "total_lines_removed": 23},
  "context_window": {"remaining_percentage": 60},
  "rate_limits": {
    "five_hour": {"used_percentage": 24, "resets_at": "'"$(date -u -v+3H +%Y-%m-%dT%H:%M:%SZ)"'"},
    "seven_day": {"used_percentage": 41, "resets_at": "'"$(date -u -v+4d +%Y-%m-%dT%H:%M:%SZ)"'"}
  }
}' \
	"~/repos/tn/tonone" \
	"spine" \
	"no subs" \
	'$0.38' \
	"23m" \
	"+156" \
	"-23" \
	"lines" \
	"Opus 4.6" \
	"5h: 24%" \
	"7d: 41%"

# State 3: Warning state (high usage)
run_test "Warning state" '{
  "session_id": "test-warn",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "agent": {"name": "spine"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {"total_cost_usd": 6.20, "total_duration_ms": 2880000, "total_lines_added": 420, "total_lines_removed": 87},
  "context_window": {"remaining_percentage": 30},
  "rate_limits": {
    "five_hour": {"used_percentage": 82, "resets_at": "'"$(date -u -v+2H +%Y-%m-%dT%H:%M:%SZ)"'"},
    "seven_day": {"used_percentage": 68, "resets_at": "'"$(date -u -v+3d +%Y-%m-%dT%H:%M:%SZ)"'"}
  }
}' \
	"spine" \
	'$6.20' \
	"48m" \
	"+420" \
	"-87" \
	"5h: 82%" \
	"7d: 68%"

# State 4: Critical state (context almost gone)
run_test "Critical state" '{
  "session_id": "test-critical",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "agent": {"name": "spine"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {"total_cost_usd": 8.40, "total_duration_ms": 4320000, "total_lines_added": 520, "total_lines_removed": 110},
  "context_window": {"remaining_percentage": 18},
  "rate_limits": {
    "five_hour": {"used_percentage": 92, "resets_at": "'"$(date -u -v+1H +%Y-%m-%dT%H:%M:%SZ)"'"},
    "seven_day": {"used_percentage": 78, "resets_at": "'"$(date -u -v+2d +%Y-%m-%dT%H:%M:%SZ)"'"}
  }
}' \
	"spine" \
	'$8.40' \
	"1h12m" \
	"compact soon" \
	"5h: 92%" \
	"7d: 78%"

# State 5: Active session with subs on different model
AGENT_BRIDGE="$TMPDIR/tonone-agents-test-subs.json"
NOW_MS=$(node -e "process.stdout.write(String(Date.now()))")
cat >"$AGENT_BRIDGE" <<AGENT_EOF
{"agents":[
  {"id":"a1","desc":"audit pipeline","model":"sonnet","started":${NOW_MS},"finished":null},
  {"id":"a2","desc":"check deps","model":"sonnet","started":${NOW_MS},"finished":null}
]}
AGENT_EOF

run_test "Subs on different model" '{
  "session_id": "test-subs",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "agent": {"name": "apex"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {"total_cost_usd": 1.50, "total_duration_ms": 900000, "total_lines_added": 80, "total_lines_removed": 12},
  "context_window": {"remaining_percentage": 55},
  "rate_limits": {
    "five_hour": {"used_percentage": 35, "resets_at": "'"$(date -u -v+4H +%Y-%m-%dT%H:%M:%SZ)"'"},
    "seven_day": {"used_percentage": 20, "resets_at": "'"$(date -u -v+5d +%Y-%m-%dT%H:%M:%SZ)"'"}
  }
}' \
	"apex" \
	"subs: audit pipeline, check deps" \
	"Opus" \
	"Sonnet" \
	'$1.50' \
	"15m"

rm -f "$AGENT_BRIDGE"

# State 6: Window reset during session
PACE_BRIDGE="$TMPDIR/tonone-pace-test-reset.json"
cat >"$PACE_BRIDGE" <<PACE_EOF
{"session_id":"test-reset","start_time":${NOW_MS},"start_5h_pct":60.0,"start_7d_pct":50.0}
PACE_EOF

run_test "Window reset during session" '{
  "session_id": "test-reset",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {"total_duration_ms": 600000},
  "rate_limits": {
    "five_hour": {"used_percentage": 5, "resets_at": "'"$(date -u -v+5H +%Y-%m-%dT%H:%M:%SZ)"'"},
    "seven_day": {"used_percentage": 10, "resets_at": "'"$(date -u -v+7d +%Y-%m-%dT%H:%M:%SZ)"'"}
  }
}' \
	"5h: 5%" \
	"7d: 10%"

rm -f "$PACE_BRIDGE"

# State 7: Long directory path (truncation)
run_test "Long directory path" '{
  "session_id": "test-longdir",
  "workspace": {"current_dir": "'"$HOME"'/very/deeply/nested/project/directory/structure/src"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {}
}' \
	"idle" \
	"no subs" \
	"Opus 4.6"

# State 8: Session goal from branch-slug
SLUG_PATH="$HOME/repos/tn/tonone/.claude/branch-slug"
SLUG_EXISTED=false
[ -f "$SLUG_PATH" ] && SLUG_EXISTED=true
echo "add-the-session-goal-row" >"$SLUG_PATH"

run_test "Session goal from branch-slug" '{
  "session_id": "test-goal",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {}
}' \
	"goal: add session goal row"

$SLUG_EXISTED || rm -f "$SLUG_PATH"

# State 9: No rate limit data
run_test "No rate limits" '{
  "session_id": "test-norate",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "model": {"display_name": "Sonnet 4.6"},
  "cost": {"total_cost_usd": 0.05, "total_duration_ms": 120000}
}' \
	"Sonnet 4.6" \
	'$0.05' \
	"5h: 0% --" \
	"7d: 0% --"

echo "═══════════════════════════"
echo "Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════"

[ "$FAIL" -eq 0 ] || exit 1
