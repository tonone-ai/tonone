"""Main entry point for /cortex-eval — orchestrates LLM usage + prompt evaluation."""

from __future__ import annotations

import argparse
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import AgentReport, ReportMetadata
from team.cortex.scripts.cortex_agent.llm_usage_scanner import scan_llm_usage
from team.cortex.scripts.cortex_agent.prompt_evaluator import evaluate_prompts


def main():
    parser = argparse.ArgumentParser(
        description="cortex-eval: LLM usage static analysis + prompt quality checks"
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Path to scan (default: current directory)",
    )
    parser.add_argument("--skip-usage", action="store_true", help="Skip LLM usage scan")
    parser.add_argument("--skip-prompts", action="store_true", help="Skip prompt evaluation")
    parser.add_argument(
        "--out",
        help="Write JSON report to this path (default: .reports/cortex-eval-<ts>.json)",
    )
    args = parser.parse_args()

    target = os.path.abspath(args.target)
    if not os.path.exists(target):
        print(f"Error: target path does not exist: {target}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {target}...")
    start = time.time()
    findings = []

    if not args.skip_usage:
        print("  [1/2] Scanning for LLM usage anti-patterns...")
        usage_findings = scan_llm_usage(target)
        print(f"        {len(usage_findings)} findings")
        findings.extend(usage_findings)

    if not args.skip_prompts:
        print("  [2/2] Evaluating prompt files...")
        prompt_findings = evaluate_prompts(target)
        print(f"        {len(prompt_findings)} findings")
        findings.extend(prompt_findings)

    duration = round(time.time() - start, 1)

    tool_ver = f"cortex-eval 0.9.8 (Python {sys.version.split()[0]})"

    report = AgentReport(
        agent="cortex",
        skill="cortex-eval",
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
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(reports_dir, f"cortex-eval-{ts}.json")

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
