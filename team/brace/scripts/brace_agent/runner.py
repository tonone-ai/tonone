"""brace runner -- orchestrates all brace-agent analyzers."""

from __future__ import annotations

import argparse
import datetime
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, ROOT)

from brace_agent.support_scanner import scan_support_artifacts, scan_support_metrics

from team.shared.report_schema import AgentReport, ReportMetadata


def main():
    parser = argparse.ArgumentParser(
        description="brace: support operation and knowledge base coverage audit"
    )
    parser.add_argument(
        "target", nargs="?", default=".", help="Path to scan (default: .)"
    )
    parser.add_argument("--out", help="Write JSON report to this path")
    args = parser.parse_args()

    target = os.path.abspath(args.target)
    if not os.path.exists(target):
        print(f"Error: target path does not exist: {target}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {target} for support artifacts...")
    start = time.time()
    findings = []

    print("  [1/2] Scanning support artifacts...")
    artifact_findings = scan_support_artifacts(target)
    print(f"        {len(artifact_findings)} findings")
    findings.extend(artifact_findings)

    print("  [2/2] Scanning support metrics and quality artifacts...")
    metrics_findings = scan_support_metrics(target)
    print(f"        {len(metrics_findings)} findings")
    findings.extend(metrics_findings)

    duration = round(time.time() - start, 1)

    report = AgentReport(
        agent="brace",
        skill="brace-recon",
        target=target,
        findings=findings,
        metadata=ReportMetadata(tool_version="brace-agent 1.0.0", duration_s=duration),
    )

    if args.out:
        out_path = args.out
    else:
        reports_dir = os.path.join(os.getcwd(), ".reports")
        os.makedirs(reports_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(reports_dir, f"brace-recon-{ts}.json")

    try:
        with open(out_path, "w") as fh:
            fh.write(report.to_json())
        print(f"\nReport written: {out_path}")
    except IOError as e:
        print(
            f"\nWarning: could not write report ({e}). Printing to stdout:",
            file=sys.stderr,
        )
        print(report.to_json())

    s = report.summary
    print(
        f"\nSummary: {s.critical} critical  {s.high} high  {s.medium} medium  "
        f"{s.low} low  ({s.total} total)"
    )


if __name__ == "__main__":
    main()
