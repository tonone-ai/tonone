#!/usr/bin/env python3
"""tonone-doctor — read-only health report for tonone state and the plugin repo.

Two scopes, auto-detected from the working directory (override with --root):

  project  .tonone/ context files (JSON parse, dangling paths, staleness),
           DESIGN.md / PRODUCT.md presence, token drift hint, hook registration
           vs hook scripts on disk, opt-in hook state.
  plugin   (cwd is the tonone repo) gen-skill-docs / sync-skills / sync-bundles
           drift, skill-index staleness, headline counts.

Never writes, never touches the network, fails open per check: a crashing
check becomes an INFO line. Exit 0 always unless --strict (1 on WARNING or
CRITICAL).

Usage:
    python3 scripts/tonone-doctor.py [--root DIR] [--json] [--strict]
"""

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

CRITICAL, WARNING, INFO = "CRITICAL", "WARNING", "INFO"
ICON = {CRITICAL: "■", WARNING: "▲", INFO: "●"}
STALE_DAYS = 90
PATH_KEYS = {"path", "paths", "file", "files", "source", "src", "dir", "output"}
SKIP_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    "vendor",
    ".venv",
    "__pycache__",
    "coverage",
    ".tonone",
    "target",
}
SCRIPT_RE = re.compile(r"[^\s\"'`;&|<>()]+\.(?:js|mjs|cjs|sh|py)\b")


class Finding(dict):
    def __init__(self, severity, check, message, fix=None):
        super().__init__(severity=severity, check=check, message=message, fix=fix)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def env_off(name):
    return bool(re.match(r"^(off|0|false|no)$", os.environ.get(name, ""), re.I))


def walk_strings(node, key=None):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, k)
    elif isinstance(node, list):
        for v in node:
            yield from walk_strings(v, key)
    elif isinstance(node, str):
        yield key, node


def is_plugin_repo(root):
    return (root / ".claude-plugin" / "marketplace.json").is_file() and (
        root / "team"
    ).is_dir()


# --------------------------------------------------------------------------
# project scope
# --------------------------------------------------------------------------


def check_tonone_files(root):
    out = []
    td = root / ".tonone"
    if not td.is_dir():
        out.append(
            Finding(INFO, "tonone-files", "no .tonone/ directory (nothing to check)")
        )
        return out
    now = time.time()
    count = 0
    for p in sorted(td.rglob("*")):
        if not p.is_file():
            continue
        count += 1
        rel = p.relative_to(root)
        try:
            age_days = (now - p.stat().st_mtime) / 86400
        except OSError:
            age_days = 0
        if age_days > STALE_DAYS:
            out.append(
                Finding(
                    INFO,
                    "stale",
                    f"{rel} untouched {int(age_days)}d",
                    "review or delete if no longer used",
                )
            )
        if p.suffix == ".json":
            try:
                data = read_json(p)
            except Exception as e:
                out.append(
                    Finding(
                        WARNING,
                        "json-parse",
                        f"{rel} fails to parse: {str(e)[:80]}",
                        f"fix or delete {rel}",
                    )
                )
                continue
            for key, val in walk_strings(data):
                if (
                    key not in PATH_KEYS
                    or not val
                    or any(c in val for c in "*?[{")
                    or "://" in val
                ):
                    continue
                if " " in val or ("/" not in val and "." not in val):
                    continue
                target = (root / val) if not os.path.isabs(val) else Path(val)
                if not target.exists():
                    out.append(
                        Finding(
                            WARNING,
                            "dangling-path",
                            f"{rel} references missing {val}",
                            "update the path or remove the entry",
                        )
                    )
        elif p.suffix == ".jsonl":
            bad = []
            try:
                for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                    if line.strip():
                        try:
                            json.loads(line)
                        except Exception:
                            bad.append(i)
            except Exception as e:
                bad = [f"unreadable: {e}"]
            if bad:
                out.append(
                    Finding(
                        WARNING,
                        "json-parse",
                        f"{rel} bad line(s): {bad[:5]}",
                        f"fix {rel} (append-only: edit the bad lines)",
                    )
                )
    out.append(Finding(INFO, "tonone-files", f"{count} file(s) under .tonone/"))
    return out


def check_design_docs(root):
    out = []
    design, product = root / "DESIGN.md", root / "PRODUCT.md"
    for f in (design, product):
        if not f.is_file():
            out.append(
                Finding(
                    INFO,
                    "design-docs",
                    f"{f.name} missing",
                    "/form-brief" if f.name == "DESIGN.md" else "/helm-brief",
                )
            )
    if design.is_file():
        d_m = design.stat().st_mtime
        newest, newest_p, n = 0.0, None, 0
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in fns:
                low = fn.lower()
                if (
                    low.endswith((".css", ".scss"))
                    or "tokens" in low
                    or low.startswith("tailwind.config")
                ):
                    n += 1
                    if n > 5000:
                        break
                    fp = Path(dp) / fn
                    try:
                        m = fp.stat().st_mtime
                    except OSError:
                        continue
                    if m > newest:
                        newest, newest_p = m, fp
            if n > 5000:
                break
        if newest_p and newest > d_m + 1:
            out.append(
                Finding(
                    INFO,
                    "token-drift",
                    f"DESIGN.md older than {newest_p.relative_to(root)}; tokens may have drifted",
                    "/form-tokens or /form-audit to re-sync DESIGN.md",
                )
            )
    return out


def hook_script_refs(cmd, plugin_root=None):
    """Script paths named in a hook command string."""
    refs = []
    for m in SCRIPT_RE.findall(cmd):
        refs.append(m)
    return refs


def resolve_ref(ref, root, plugin_root):
    r = ref
    if plugin_root is not None:
        r = r.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root)).replace(
            "$CLAUDE_PLUGIN_ROOT", str(plugin_root)
        )
    r = r.replace("${CLAUDE_PROJECT_DIR}", str(root)).replace(
        "$CLAUDE_PROJECT_DIR", str(root)
    )
    if r.startswith("~"):
        r = os.path.expanduser(r)
    if "$" in r:
        return None  # unresolvable variable: do not guess
    p = Path(r)
    return p if p.is_absolute() else root / p


def hooks_in(data):
    """Yield command strings from a settings/hooks.json 'hooks' block."""
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return
    for entries in hooks.values():
        if not isinstance(entries, list):
            continue
        for e in entries:
            for h in (e.get("hooks", []) if isinstance(e, dict) else []):
                if isinstance(h, dict) and isinstance(h.get("command"), str):
                    yield h["command"]


def check_hooks_project(root):
    out = []
    for name in ("settings.json", "settings.local.json"):
        f = root / ".claude" / name
        if not f.is_file():
            continue
        try:
            data = read_json(f)
        except Exception as e:
            out.append(
                Finding(
                    WARNING,
                    "hooks",
                    f".claude/{name} fails to parse: {str(e)[:80]}",
                    f"fix JSON in .claude/{name}",
                )
            )
            continue
        for cmd in hooks_in(data):
            for ref in hook_script_refs(cmd):
                p = resolve_ref(ref, root, None)
                if p is not None and not p.exists():
                    out.append(
                        Finding(
                            WARNING,
                            "hooks",
                            f".claude/{name} registers missing script {ref}",
                            "restore the script or remove the hook entry",
                        )
                    )
    return out


def check_hooks_plugin(repo):
    out = []
    f = repo / "hooks" / "hooks.json"
    registered = set()
    if f.is_file():
        data = read_json(f)
        for cmd in hooks_in(data):
            for ref in hook_script_refs(cmd):
                p = resolve_ref(ref, repo, repo)
                if p is None:
                    continue
                try:
                    registered.add(p.resolve())
                except OSError:
                    pass
                if not p.exists():
                    out.append(
                        Finding(
                            WARNING,
                            "hooks",
                            f"hooks/hooks.json registers missing {ref}",
                            "restore the script or drop the registration",
                        )
                    )
    hd = repo / "hooks"
    if hd.is_dir():
        for p in sorted(hd.iterdir()):
            if (
                p.suffix in (".js", ".sh")
                and not p.name.startswith("test-")
                and p.resolve() not in registered
            ):
                out.append(
                    Finding(
                        INFO,
                        "hooks",
                        f"hooks/{p.name} present but not in hooks/hooks.json",
                    )
                )
    return out


def check_optin_hooks(root):
    """Report opt-in state for hooks whose switches are read from their sources."""
    out = []
    # form-design-lint: .tonone/design.json {"hook": true} or TONONE_DESIGN_LINT
    on = False
    cfg = root / ".tonone" / "design.json"
    if cfg.is_file():
        try:
            on = read_json(cfg).get("hook") is True
        except Exception:
            pass
    env = os.environ.get("TONONE_DESIGN_LINT", "")
    if env_off("TONONE_DESIGN_LINT"):
        state = "off (TONONE_DESIGN_LINT)"
    elif env.lower() == "on" or on:
        state = (
            "on ("
            + ("env" if env.lower() == "on" else ".tonone/design.json hook:true")
            + ")"
        )
    else:
        state = "off (opt-in: .tonone/design.json hook:true or TONONE_DESIGN_LINT=on)"
    out.append(Finding(INFO, "optin-hooks", f"form-design-lint: {state}"))
    # apex-guard: .claude/tonone-guard.json state file, TONONE_GUARD / TONONE_APEX_GUARD off
    disabled = env_off("TONONE_GUARD") or env_off("TONONE_APEX_GUARD")
    gf = root / ".claude" / "tonone-guard.json"
    if disabled:
        gs = "disabled by env"
    elif gf.is_file():
        try:
            st = read_json(gf)
            age = (time.time() - gf.stat().st_mtime) / 3600
            gs = f"armed careful={st.get('careful')} freeze={st.get('freeze')}" + (
                " (state >24h old, ignored)" if age > 24 else ""
            )
        except Exception as e:
            gs = "state file unparseable"
            out.append(
                Finding(
                    WARNING,
                    "json-parse",
                    f".claude/tonone-guard.json: {str(e)[:80]}",
                    "delete it and re-arm with /apex-guard",
                )
            )
    else:
        gs = "not armed (arm with /apex-guard)"
    out.append(Finding(INFO, "optin-hooks", f"apex-guard: {gs}"))
    # apex-decisions: .tonone/decisions.jsonl, TONONE_DECISIONS
    dl = root / ".tonone" / "decisions.jsonl"
    ds = (
        "disabled by env"
        if env_off("TONONE_DECISIONS")
        else ("log present" if dl.is_file() else "no log yet")
    )
    out.append(Finding(INFO, "optin-hooks", f"apex-decisions: {ds}"))
    return out


# --------------------------------------------------------------------------
# plugin-repo scope
# --------------------------------------------------------------------------


def run_check_script(repo, script, label, fix):
    r = subprocess.run(
        [sys.executable, str(repo / "scripts" / script), "--check"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.strip()]
    if r.returncode == 0:
        return [Finding(INFO, label, "in sync")]
    detail = "; ".join(lines[:3])[:160]
    more = f" (+{len(lines) - 3} more lines)" if len(lines) > 3 else ""
    return [Finding(WARNING, label, f"drift: {detail}{more}", fix)]


def team_skills(repo):
    names = set()
    for agent in sorted((repo / "team").iterdir()):
        sd = agent / "skills"
        if sd.is_dir():
            for d in sd.iterdir():
                if d.is_dir() and (d / "SKILL.md").exists():
                    names.add(d.name)
    return names


def check_skill_index(repo):
    idx = repo / "docs" / "skill-index.json"
    if not idx.is_file():
        return [
            Finding(
                WARNING,
                "skill-index",
                "docs/skill-index.json missing",
                "python scripts/gen-skill-index.py",
            )
        ]
    data = read_json(idx)
    entries = data if isinstance(data, list) else data.get("skills", [])
    indexed = {e.get("name") for e in entries if isinstance(e, dict)}
    tree = team_skills(repo)
    missing, extra = sorted(tree - indexed), sorted(indexed - tree)
    if not missing and not extra:
        return [Finding(INFO, "skill-index", f"{len(indexed)} skills indexed, in sync")]
    return [
        Finding(
            WARNING,
            "skill-index",
            f"stale: {len(missing)} not indexed {missing[:4]}, {len(extra)} orphaned {extra[:4]}",
            "python scripts/gen-skill-index.py",
        )
    ]


def check_headline_counts(repo):
    agents = len(
        [
            d
            for d in (repo / "team").iterdir()
            if d.is_dir() and (d / ".claude-plugin" / "plugin.json").exists()
        ]
    )
    skills = len(team_skills(repo))
    wrong = []
    for rel in (
        "README.md",
        "CLAUDE.md",
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
    ):
        f = repo / rel
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        for m in re.finditer(r"\b(\d+) (?:agents|specialists)\b", text, re.I):
            if int(m.group(1)) >= 50 and int(m.group(1)) != agents:
                wrong.append(f"{rel}: '{m.group(0)}' (tree {agents})")
        # "(15 agents, 105 skills)" per-team headers are subtotals (same rule
        # as tests/test_structure.py::test_headline_counts_match_tree).
        for m in re.finditer(r"(?<!agents, )\b(\d{3}) skills\b", text, re.I):
            if int(m.group(1)) != skills:
                wrong.append(f"{rel}: '{m.group(0)}' (tree {skills})")
    if not wrong:
        return [
            Finding(
                INFO,
                "headline-counts",
                f"{agents} agents, {skills} skills match public copy",
            )
        ]
    return [
        Finding(
            WARNING,
            "headline-counts",
            f"{len(wrong)} mismatch(es): {wrong[0]}",
            "update the hardcoded totals in README/CLAUDE.md/manifests",
        )
    ]


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def collect(root):
    checks = [
        ("tonone-files", lambda: check_tonone_files(root)),
        ("design-docs", lambda: check_design_docs(root)),
        ("hooks-project", lambda: check_hooks_project(root)),
        ("optin-hooks", lambda: check_optin_hooks(root)),
    ]
    scope = "project"
    if is_plugin_repo(root):
        scope = "plugin"
        checks += [
            ("hooks-plugin", lambda: check_hooks_plugin(root)),
            (
                "gen-skill-docs",
                lambda: run_check_script(
                    root,
                    "gen-skill-docs.py",
                    "gen-skill-docs",
                    "python scripts/gen-skill-docs.py",
                ),
            ),
            (
                "sync-skills",
                lambda: run_check_script(
                    root,
                    "sync-skills.py",
                    "sync-skills",
                    "python scripts/sync-skills.py",
                ),
            ),
            (
                "sync-bundles",
                lambda: run_check_script(
                    root,
                    "sync-bundles.py",
                    "sync-bundles",
                    "python scripts/sync-bundles.py",
                ),
            ),
            ("skill-index", lambda: check_skill_index(root)),
            ("headline-counts", lambda: check_headline_counts(root)),
        ]
    findings = []
    for name, fn in checks:
        try:
            findings += fn()
        except Exception as e:  # fail open
            findings.append(Finding(INFO, name, f"check {name} failed: {str(e)[:100]}"))
    return scope, findings


def render(scope, root, findings):
    order = {CRITICAL: 0, WARNING: 1, INFO: 2}
    fs = sorted(findings, key=lambda f: order[f["severity"]])
    n = {s: sum(1 for f in fs if f["severity"] == s) for s in order}
    if n[CRITICAL]:
        verdict = f"{n[CRITICAL]} critical, {n[WARNING]} warning"
    elif n[WARNING]:
        verdict = f"{n[WARNING]} warning(s) to fix"
    else:
        verdict = "healthy"
    shown = [f for f in fs if f["severity"] != INFO][:7]
    infos = [f for f in fs if f["severity"] == INFO]
    room = max(0, 7 - len(shown))
    shown += infos[:room]
    lines = [
        f"╭─ TONONE ── doctor ({scope}) ──────────╮",
        "",
        f"  ## {verdict}",
        "",
        "  ### Findings",
    ]
    for f in shown:
        lines.append(
            f"  - {ICON[f['severity']]} {f['severity']} — [{f['check']}] {f['message']}"
        )
    hidden = len(fs) - len(shown)
    if hidden > 0:
        lines.append(f"  - {hidden} more (use --json)")
    fixes = []
    for f in fs:
        if f["fix"] and f["severity"] != INFO and f["fix"] not in fixes:
            fixes.append(f["fix"])
    if fixes:
        lines += ["", "  ### Next Steps"] + [f"  → {x}" for x in fixes[:3]]
    lines += ["", "╰─ Full report: --json ──────────────────────────╯"]
    return "\n".join(lines)


def usage_summary(root, since=None):
    """Aggregate .tonone/metrics.jsonl per tool/event. Bad lines are skipped."""
    f = Path(root) / ".tonone" / "metrics.jsonl"
    if not f.is_file():
        return None
    cutoff = None
    if since:
        m = re.fullmatch(r"(\d+)([dh])", since)
        if not m:
            raise ValueError("--since expects Nd or Nh, e.g. 7d")
        n = int(m.group(1))
        cutoff = datetime.now(timezone.utc) - (
            timedelta(days=n) if m.group(2) == "d" else timedelta(hours=n)
        )
    tools, bad = {}, 0
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            tool, ev = str(e["tool"]), str(e["event"])
            if cutoff:
                ts = datetime.fromisoformat(str(e["ts"]).replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < cutoff:
                    continue
        except (ValueError, KeyError, TypeError, AttributeError):
            bad += 1
            continue
        t = tools.setdefault(tool, {}).setdefault(ev, {"n": 0, "sums": {}})
        t["n"] += 1
        for k, v in e.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                t["sums"][k] = t["sums"].get(k, 0) + v
    return {"tools": tools, "skipped": bad, "since": since}


def render_usage(u):
    if u is None:
        return "metrics off (set TONONE_METRICS=on)"
    lines = ["╭─ TONONE ── usage ──────────────────────────────╮", ""]
    if not u["tools"]:
        lines.append("  ● no events" + (f" in last {u['since']}" if u["since"] else ""))
    for tool in sorted(u["tools"]):
        lines.append(f"  ### {tool}")
        for ev, d in sorted(u["tools"][tool].items()):
            sums = " ".join(f"{k}={v:g}" for k, v in sorted(d["sums"].items()))
            lines.append(f"  - {ev} x{d['n']}" + (f"  {sums}" if sums else ""))
    if u["skipped"]:
        lines.append(f"  ▲ {u['skipped']} malformed line(s) skipped")
    lines += ["", "╰─ Full data: .tonone/metrics.jsonl ─────────────╯"]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only tonone health report.")
    ap.add_argument(
        "--root", default=".", help="project or plugin-repo root (default: cwd)"
    )
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument(
        "--strict", action="store_true", help="exit 1 on WARNING or CRITICAL"
    )
    ap.add_argument(
        "--usage", action="store_true", help="summarize .tonone/metrics.jsonl"
    )
    ap.add_argument("--since", help="with --usage: window, e.g. 7d or 12h")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    if args.usage:
        try:
            u = usage_summary(root, args.since)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print(
            json.dumps(u or {"metrics": "off"}, indent=2)
            if args.json
            else render_usage(u)
        )
        return 0
    scope, findings = collect(root)
    bad = any(f["severity"] in (WARNING, CRITICAL) for f in findings)
    if args.json:
        print(
            json.dumps(
                {
                    "scope": scope,
                    "root": str(root),
                    "findings": findings,
                    "ok": not bad,
                },
                indent=2,
            )
        )
    else:
        print(render(scope, root, findings))
    return 1 if (args.strict and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
