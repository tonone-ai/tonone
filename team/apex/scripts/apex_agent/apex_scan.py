"""Main entry point for /apex-review depth scan — health aggregator + dep graph."""

from __future__ import annotations

import argparse
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import AgentReport, ReportMetadata
from team.apex.scripts.apex_agent.health_aggregator import aggregate_health
from team.apex.scripts.apex_agent.dependency_graph import analyze_dependencies


def main() -> None:
    parser = argparse.ArgumentParser(
        description="apex-review: cross-cutting health snapshot (all agents + dep graph)"
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Repo root to scan (default: .)",
    )
    parser.add_argument(
        "--skip-health", action="store_true", help="Skip sub-agent health aggregation"
    )
    parser.add_argument(
        "--skip-deps", action="store_true", help="Skip dependency graph analysis"
    )
    parser.add_argument("--out", help="Write JSON report to this path")
    args = parser.parse_args()

    target = os.path.abspath(args.target)
    if not os.path.exists(target):
        print(f"Error: target path does not exist: {target}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {target}...")
    start = time.time()
    findings = []

    if not args.skip_health:
        print("  [1/2] Running sub-agent health scans (parallel)...")
        health_findings, _errors = aggregate_health(target)
        print(f"        {len(health_findings)} finding(s) from sub-agents")
        findings.extend(health_findings)

    if not args.skip_deps:
        print("  [2/2] Analyzing dependency graph...")
        dep_findings = analyze_dependencies(target)
        print(f"        {len(dep_findings)} dependency finding(s)")
        findings.extend(dep_findings)

    duration = round(time.time() - start, 1)
    tool_ver = "apex-scan 0.9.9"

    report = AgentReport(
        agent="apex",
        skill="apex-review",
        target=target,
        findings=findings,
        metadata=ReportMetadata(tool_version=tool_ver, duration_s=duration),
    )

    if args.out:
        out_path = args.out
    else:
        reports_dir = os.path.join(os.getcwd(), ".reports")
        os.makedirs(reports_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(reports_dir, f"apex-{ts}.json")

    try:
        with open(out_path, "w") as fh:
            fh.write(report.to_json())
        print(f"\nReport written: {out_path}")
    except IOError as e:
        print(f"\nWarning: could not write report ({e}). Printing to stdout:", file=sys.stderr)
        print(report.to_json())

    s = report.summary
    print(
        f"\nSummary: {s.critical} critical  {s.high} high  "
        f"{s.medium} medium  {s.low} low  ({s.total} total)"
    )

    if s.critical > 0 or s.high > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
