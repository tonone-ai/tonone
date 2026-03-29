# Changelog Hook

When an agent skill completes and produces output matching the CLI skeleton format (the `╭─ AGENT NAME ── skill-name` header), extract structured data and update changelogs.

## Detection

Look for output containing:

- `╭─` followed by an agent name and skill name
- Severity indicators: `■ CRITICAL`, `▲ WARNING`, `● INFO`
- A structured findings section

If the output does not match this pattern, do nothing.

## Extraction

From the CLI skeleton output, extract:

- **Agent name** — from the `╭─ AGENT NAME` header
- **Skill name** — from the `── skill-name` part of the header
- **Target repo** — from the current working directory
- **Verdict** — the one-line verdict
- **Findings summary** — count of critical/warning/info items
- **Key actions** — from the Next Steps section

## Action

Run `/atlas-changelog` with the extracted data to update all three changelog layers:

1. Per-repo changelog
2. Cross-repo changelog (if in multi-repo workspace)
3. Per-agent activity log
