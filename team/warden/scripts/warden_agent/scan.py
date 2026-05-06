"""Main entry point for /warden-scan — orchestrates SAST + dep audit."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import AgentReport, ReportMetadata
from team.warden.scripts.warden_agent.pip_auditor import run_pip_audit
from team.warden.scripts.warden_agent.semgrep_scanner import run_semgrep


def main():
    parser = argparse.ArgumentParser(description="warden-scan: SAST + dependency audit")
    parser.add_argument(
        "target", nargs="?", default=".", help="Path to scan (default: .)"
    )
    parser.add_argument(
        "--semgrep-config", default="auto", help="Semgrep ruleset (default: auto)"
    )
    parser.add_argument("--skip-semgrep", action="store_true")
    parser.add_argument("--skip-deps", action="store_true")
    parser.add_argument(
        "--out",
        help="Write JSON report to this path (default: .reports/warden-<ts>.json)",
    )
    args = parser.parse_args()

    target = os.path.abspath(args.target)
    if not os.path.exists(target):
        print(f"Error: target path does not exist: {target}", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Scanning {target}...")
    start = time.time()
    findings = []

    if not args.skip_semgrep:
        print("  [1/2] Running Semgrep SAST...")
        sast_findings = run_semgrep(target, config=args.semgrep_config)
        print(f"        {len(sast_findings)} findings")
        findings.extend(sast_findings)

    if not args.skip_deps:
        print("  [2/2] Running pip-audit dependency scan...")
        dep_findings = run_pip_audit(target)
        print(f"        {len(dep_findings)} vulnerable dependencies")
        findings.extend(dep_findings)

    duration = round(time.time() - start, 1)

    try:
        import semgrep

        semgrep_ver = semgrep.__version__ if hasattr(semgrep, "__version__") else "?"
    except ImportError:
        semgrep_ver = "not installed"
    try:
        import pip_audit as _pa

        pip_audit_ver = _pa.__version__ if hasattr(_pa, "__version__") else "?"
    except ImportError:
        pip_audit_ver = "not installed"
    tool_ver = f"semgrep {semgrep_ver} / pip-audit {pip_audit_ver}"

    report = AgentReport(
        agent="warden",
        skill="warden-scan",
        target=target,
        findings=findings,
        metadata=ReportMetadata(tool_version=tool_ver, duration_s=duration),
    )

    # determine output path
    if args.out:
        out_path = args.out
    else:
        reports_dir = os.path.join(os.getcwd(), ".reports")
        os.makedirs(reports_dir, exist_ok=True)
        import datetime

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(reports_dir, f"warden-{ts}.json")

    try:
        with open(out_path, "w") as f:
            f.write(report.to_json())
        print(f"\n✅ Report written: {out_path}")
    except IOError as e:
        print(
            f"\nWarning: could not write report file ({e}). Printing to stdout:",
            file=sys.stderr,
        )
        print(report.to_json())

    # print summary
    s = report.summary
    print(
        f"\nSummary: {s.critical} critical  {s.high} high  {s.medium} medium  {s.low} low  ({s.total} total)"
    )
    if s.critical > 0 or s.high > 0:
        sys.exit(2)  # non-zero exit for CI gates


if __name__ == "__main__":
    main()
