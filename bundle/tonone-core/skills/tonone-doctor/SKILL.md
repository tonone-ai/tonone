---
name: tonone-doctor
description: 'Read-only health report for tonone state — corrupt .tonone/ files, hook wiring, drift between skills, mirror, bundles and index. Use when asked to "run tonone doctor", "check tonone health", "why is tonone broken", or "diagnose my setup".'
version: 0.1.0
author: tonone-ai <hello@tonone.ai>
license: MIT
compatibility: Designed for Claude Code
tags: [doctor, health, diagnostics, hooks]
---

# tonone-doctor

Cross-agent health check. Not tied to a single agent. Read-only: it reports and
suggests, it never fixes.

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.

## Steps

### Step 1: Run the doctor

`CLAUDE_PLUGIN_ROOT` is not always exported into the Bash tool, so locate the script first:

```bash
doc=""
for c in "${CLAUDE_PLUGIN_ROOT:-/nonexistent}/scripts/tonone-doctor.py" \
         "${CLAUDE_PLUGIN_ROOT:-/nonexistent}/../../scripts/tonone-doctor.py" \
         "$PWD/scripts/tonone-doctor.py"; do
  [ -f "$c" ] && doc="$c" && break
done
[ -z "$doc" ] && doc=$(find "$HOME/.claude/plugins/cache" -maxdepth 6 -path "*/scripts/tonone-doctor.py" 2>/dev/null | head -1)
python3 "$doc" --json
```

Scope is auto-detected from the working directory: a user project (`.tonone/` files, DESIGN.md/PRODUCT.md, hooks, opt-in hook state) or the tonone plugin repo (also runs the `gen-skill-docs`, `sync-skills`, `sync-bundles` checks, skill-index staleness, headline counts). Use `--root DIR` to point elsewhere. Use the box output (drop `--json`) for a quick look. `--usage [--since 7d]` summarizes the opt-in `.tonone/metrics.jsonl` counters (enable with `TONONE_METRICS=on`).

### Step 2: Interpret

Group findings by severity. For each WARNING or CRITICAL, give the cause in one line and the fixing command:

| Finding                            | Suggested fix                                                  |
| ---------------------------------- | -------------------------------------------------------------- |
| `.tonone/*.json` fails to parse    | Open the file, fix the JSON, or delete it if it is regenerable |
| Path in `.tonone/` file is missing | Update or remove the entry                                     |
| Hook registered but script missing | Restore the script or remove the hook entry                    |
| `gen-skill-docs` drift             | `python scripts/gen-skill-docs.py`                             |
| `sync-skills` drift                | `python scripts/sync-skills.py`                                |
| `sync-bundles` drift               | `python scripts/sync-bundles.py`                               |
| skill-index stale                  | `python scripts/gen-skill-index.py`                            |
| Headline counts mismatch           | Update totals in README/CLAUDE.md/manifests                    |

INFO lines (token drift hint, stale files, opt-in hook state) are awareness only.

### Step 3: Report

Box header `TONONE ── doctor`, one-line verdict, top findings with `■ CRITICAL` / `▲ WARNING` / `● INFO`, then the fix commands as next steps. Do not run any fix yourself; the user decides. CI use: `--strict` exits 1 on any WARNING or CRITICAL.

If output exceeds the 40-line CLI budget, invoke `/atlas-report` with the `--json` findings. CLI is the receipt: box header, verdict, top 3 findings, report path.
