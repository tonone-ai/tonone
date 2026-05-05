"""Main entry point for /spine-perf — orchestrates N+1 detector + endpoint profiler."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import AgentReport, ReportMetadata
from team.spine.scripts.spine_agent.endpoint_profiler import profile_endpoints
from team.spine.scripts.spine_agent.n_plus_one_detector import scan_directory


def main():
    parser = argparse.ArgumentParser(
        description="spine-perf: N+1 detector + endpoint profiler"
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Path to scan for N+1 patterns (default: .)",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Base URL for endpoint profiling (e.g. http://localhost:8000)",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=[],
        help="Endpoint paths to profile (e.g. /api/orders /api/users)",
    )
    parser.add_argument(
        "--skip-n1", action="store_true", help="Skip N+1 static analysis"
    )
    parser.add_argument(
        "--skip-endpoints", action="store_true", help="Skip endpoint profiling"
    )
    parser.add_argument("--out", help="Write JSON report to this path")
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Per-request timeout in seconds for endpoint profiling (default: 5)",
    )
    args = parser.parse_args()

    target = os.path.abspath(args.target)
    if not os.path.exists(target):
        print(f"Error: target path does not exist: {target}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {target}...")
    start = time.time()
    findings = []

    if not args.skip_n1:
        print("  [1/2] Running N+1 static analysis...")
        n1_findings = scan_directory(target)
        print(f"        {len(n1_findings)} findings")
        findings.extend(n1_findings)

    if not args.skip_endpoints:
        if args.base_url and args.paths:
            print(
                f"  [2/2] Profiling {len(args.paths)} endpoint(s) at {args.base_url}..."
            )
            ep_findings = profile_endpoints(
                base_url=args.base_url,
                paths=args.paths,
                timeout=args.timeout,
            )
            print(f"        {len(ep_findings)} slow endpoints")
            findings.extend(ep_findings)
        else:
            print(
                "  [2/2] Skipping endpoint profiler (no --base-url / --paths provided)"
            )

    duration = round(time.time() - start, 1)

    # build tool version string
    try:
        import httpx as _hx

        httpx_ver = getattr(_hx, "__version__", "?")
    except ImportError:
        httpx_ver = "not installed"
    tool_ver = f"spine-perf 0.9.8 / httpx {httpx_ver}"

    report = AgentReport(
        agent="spine",
        skill="spine-perf",
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
        out_path = os.path.join(reports_dir, f"spine-perf-{ts}.json")

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
        f"\nSummary: {s.critical} critical  {s.high} high  "
        f"{s.medium} medium  {s.low} low  ({s.total} total)"
    )

    if s.critical > 0 or s.high > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
