# Dogfood scorecard (1.20 pieces, ~1 week)

Trial form-lint, copy-slop, apex-guard, apex-review v2, apex-decisions and
apex-profile on one real project. At the end, fill the table and decide per
piece: **keep**, **tune** (adjust rules/thresholds), or **cut**.

## Setup (once)

```bash
export TONONE=/path/to/tonone          # plugin repo checkout
export TONONE_METRICS=on               # opt-in counters -> .tonone/metrics.jsonl
cd /path/to/project
python3 $TONONE/scripts/tonone-doctor.py --usage    # sanity check; "metrics off" = env not exported
```

Counters are local, off by default, and hold counts and rule ids only (never
file contents or command text). Needs `jq` for the commands below. Day-by-day
view: `python3 $TONONE/scripts/tonone-doctor.py --usage --since 1d`.

`M=.tonone/metrics.jsonl` in every command below.

## Scorecard

| #   | Metric                                    | Measures                              | Keep                                                              | Tune                           | Cut                                 |
| --- | ----------------------------------------- | ------------------------------------- | ----------------------------------------------------------------- | ------------------------------ | ----------------------------------- |
| 1   | form-lint findings per 1k lines           | Rule noise on real code               | <= 5                                                              | 5-15                           | > 15 after one tuning pass          |
| 2   | form-lint ignore rate                     | Ignores (config + inline) per finding | < 20%                                                             | 20-50%                         | > 50% (rules ignored wholesale)     |
| 3   | copy-slop WARN/FAIL per run, waivers      | Gate vs real copy                     | FAIL on < 20% of runs, waivers <= 3                               | FAIL 20-50%                    | FAIL > 50% or waivers > 10          |
| 4   | apex-guard asks / denies                  | Guard fires per day                   | asks <= 5/day, 0 false denies                                     | one rule > 50% of asks         | any false deny, or you disabled it  |
| 5   | apex-review kept vs dropped, red-pass hit | Review signal                         | kept share > 60%, red adds >= 1 finding in 30% of red runs        | kept < 60%                     | red never adds or disputes anything |
| 6   | apex-decisions resurfaced                 | Memory use                            | resurfaced in > 50% of sessions and one entry saved a re-argument | resurfaced > 5/session (noisy) | never resurfaced or never useful    |
| 7   | startup token cost                        | Skill listing at session start        | profile cuts >= 80% vs full                                       | 50-80%                         | < 50%                               |

## Collection

**1-2. form-lint** (CLI `--json`, `.tonone/design.json`):

```bash
SRC=src
F=$(node $TONONE/team/form/scripts/design-lint/design-lint.js $SRC --tier all --json | jq '.findings|length')
L=$(find $SRC -type f \( -name '*.tsx' -o -name '*.jsx' -o -name '*.vue' -o -name '*.svelte' -o -name '*.html' -o -name '*.css' -o -name '*.scss' \) -print0 | xargs -0 cat | wc -l)
echo "findings per 1k lines: $(echo "scale=1; $F*1000/$L" | bc)"
IG=$(jq '((.ignoreRules//[])|length)+((.ignoreFiles//[])|length)' .tonone/design.json 2>/dev/null || echo 0)
IN=$(grep -rE 'design-lint-disable' $SRC | wc -l)
echo "ignore rate: $(echo "scale=2; ($IG+$IN)/($F+$IG+$IN)" | bc)"
# hook: findings surfaced to the model
jq -s '[.[]|select(.tool=="form-lint" and .event=="hook_shown")|.shown]|add' $M
```

**3. copy-slop** (run your real drafts through the gate; the hook-less path logs one `run` per invocation):

```bash
python3 $TONONE/lib/copy-gate/gate.py --slop drafts.md > /dev/null
jq -s '[.[]|select(.tool=="copy-slop")] | {runs:length, warn:(map(.warn)|add), fail:(map(.fail)|add), failed_runs:(map(select(.fail>0))|length), waived_hits:(map(.waived)|add)}' $M
jq '.waive|length' .tonone/copy-waivers.json     # waiver entries (each needs a reason)
```

**4. apex-guard** (rule ids only; the hook cannot see whether you approved an ask):

```bash
jq -s '[.[]|select(.tool=="apex-guard")] | group_by(.event) | map({event:.[0].event, n:length})' $M
jq -s '[.[]|select(.tool=="apex-guard")|.rules[]] | group_by(.) | map({rule:.[0], n:length}) | sort_by(-.n)' $M
```

**5. apex-review v2** (`merge_findings.py` writes one `merge` line per run; the
verdict text still goes to stdout). `dropped` = no evidence/bad severity,
`disputed` = red-pass dispute with evidence, `red_new` = findings carrying the
red lens:

```bash
jq -s '[.[]|select(.tool=="apex-review")] | {runs:length, kept:(map(.kept)|add), dropped:(map(.dropped)|add), disputed:(map(.disputed)|add), red_runs:(map(select(.red))|length), red_runs_with_hit:(map(select(.red and (.red_new>0 or .disputed>0)))|length)}' $M
```

Human dismissals after the merge are not on disk. Tally them by hand from the
review receipts (one line per agent: findings kept/dropped) into the table.

**6. apex-decisions** (emitted by `team/apex/hooks/apex-decisions.js` as
`{"tool":"apex-decisions","event":"resurfaced","n":<entries>}` per the metrics contract):

```bash
jq -s '[.[]|select(.tool=="apex-decisions" and .event=="resurfaced")] | {sessions:length, entries:(map(.n)|add), per_session:((map(.n)|add)/length)}' $M
wc -l .tonone/decisions.jsonl                  # total log size
```

Usefulness is judgment: note each time a resurfaced entry stopped a re-argument.

**7. startup tokens** (estimate, chars/4, from `scripts/measure-context.py`; the
`web_app_profile` block is what `/apex-profile` web-app preset leaves listed):

```bash
python3 $TONONE/scripts/measure-context.py --json | jq '{before_full:.combined.est_tokens, after_web_app:.web_app_profile.combined.est_tokens}'
```

Run `/apex-profile`, then confirm `enabledPlugins` in `.claude/settings.json`
matches the preset you measured. For a custom roster, rerun with the roster's
agents in `WEB_APP_PRESET` or sum the entries you kept.

## End of week

```bash
python3 $TONONE/scripts/tonone-doctor.py --usage --since 7d
```

Record per piece: number, verdict (keep/tune/cut), one-line why. Share the
`metrics.jsonl` only after checking it; it holds no content, but rule ids and
timestamps still describe your work.
