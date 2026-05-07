"""keel runner -- orchestrates all keel-agent analyzers."""

from __future__ import annotations

import argparse
import datetime
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, ROOT)

from keel_agent.ops_scanner import scan_compliance_artifacts, scan_ops_artifacts

from team.shared.report_schema import AgentReport, ReportMetadata


def main():
    parser = argparse.ArgumentParser(
        description="keel: operations artifact and compliance coverage audit"
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

    print(f"Scanning {target} for operations artifacts...")
    start = time.time()
    findings = []

    print("  [1/2] Scanning ops artifacts (SOPs, vendors, OKRs)...")
    ops_findings = scan_ops_artifacts(target)
    print(f"        {len(ops_findings)} findings")
    findings.extend(ops_findings)

    print("  [2/2] Scanning compliance and legal artifacts...")
    compliance_findings = scan_compliance_artifacts(target)
    print(f"        {len(compliance_findings)} findings")
    findings.extend(compliance_findings)

    duration = round(time.time() - start, 1)

    report = AgentReport(
        agent="keel",
        skill="keel-recon",
        target=target,
        findings=findings,
        metadata=ReportMetadata(tool_version="keel-agent 1.0.0", duration_s=duration),
    )

    if args.out:
        out_path = args.out
    else:
        reports_dir = os.path.join(os.getcwd(), ".reports")
        os.makedirs(reports_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(reports_dir, f"keel-recon-{ts}.json")

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
