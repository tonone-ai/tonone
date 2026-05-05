"""Main entry point for /forge-cost — orchestrates IaC cost analysis + cloud spend."""

from __future__ import annotations

import argparse
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import AgentReport, ReportMetadata
from team.forge.scripts.forge_agent.infracost_analyzer import run_infracost, check_infracost
from team.forge.scripts.forge_agent.cloud_cost_fetcher import run_cloud_cost_fetch


def main():
    parser = argparse.ArgumentParser(description="forge-cost: IaC cost analysis + cloud spend audit")
    parser.add_argument("target", nargs="?", default=".", help="Path to scan (default: .)")
    parser.add_argument("--skip-infracost", action="store_true", help="Skip infracost IaC analysis")
    parser.add_argument("--skip-cloud", action="store_true", help="Skip cloud CLI cost fetch")
    parser.add_argument("--out", help="Write JSON report to this path")
    args = parser.parse_args()

    target = os.path.abspath(args.target)
    if not os.path.exists(target):
        print(f"Error: target path does not exist: {target}", file=sys.stderr)
        sys.exit(1)

    print(f"💰 Scanning {target}...")
    start = time.time()
    findings = []

    if not args.skip_infracost:
        print("  [1/2] Running infracost IaC analysis...")
        iac_findings = run_infracost(target)
        print(f"        {len(iac_findings)} cost findings")
        findings.extend(iac_findings)

    if not args.skip_cloud:
        print("  [2/2] Fetching cloud spend (AWS/GCP)...")
        cloud_findings = run_cloud_cost_fetch(target)
        print(f"        {len(cloud_findings)} spend findings")
        findings.extend(cloud_findings)

    duration = round(time.time() - start, 1)

    try:
        import infracost as _ic
        ic_ver = getattr(_ic, "__version__", "?")
    except ImportError:
        available, ver_str = check_infracost()
        ic_ver = ver_str.split()[-1] if available and ver_str else "not installed"

    tool_ver = f"infracost {ic_ver}"

    report = AgentReport(
        agent="forge",
        skill="forge-cost",
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
        out_path = os.path.join(reports_dir, f"forge-cost-{ts}.json")

    try:
        with open(out_path, "w") as f:
            f.write(report.to_json())
        print(f"\n✅ Report written: {out_path}")
    except IOError as e:
        print(f"\nWarning: could not write report ({e}). Printing to stdout:", file=sys.stderr)
        print(report.to_json())

    s = report.summary
    total_cost = sum(
        float(f.detail.split("$")[1].split("/")[0].split(" ")[0])
        for f in findings
        if "$" in f.detail
    )
    print(f"\nSummary: {s.critical} critical  {s.high} high  {s.medium} medium  {s.low} low  ({s.total} total)")
    if total_cost > 0:
        print(f"Estimated monthly cost in findings: ${total_cost:,.2f}")


if __name__ == "__main__":
    main()
