"""CLI entry point for standalone usage."""

import argparse
import json
import sys
import tempfile
import traceback
import webbrowser
from pathlib import Path

from cloudrun_agent import __version__
from cloudrun_agent.dashboard import generate_dashboard
from cloudrun_agent.history import (
    build_comparison_from_current,
    list_snapshots,
    save_snapshot,
)
from cloudrun_agent.overview import build_overview
from cloudrun_agent.runner import analyze_service, discover_services
from cloudrun_agent.tools.gcloud import GcloudError


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Analyze Cloud Run services")
    parser.add_argument(
        "--version", action="version", version=f"cloudrun-agent {__version__}"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output and full tracebacks on error",
    )
    parser.add_argument("--project", help="GCP project ID")
    parser.add_argument("--region", help="GCP region filter")
    parser.add_argument("--service", help="Analyze a specific service")
    parser.add_argument("--list", action="store_true", help="List services only")
    parser.add_argument("--no-metrics", action="store_true", help="Skip metrics fetch")
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML dashboard and open in browser",
    )
    parser.add_argument(
        "--output", help="Write HTML to this path instead of a temp file"
    )
    parser.add_argument("--history", action="store_true", help="Show snapshot history")
    parser.add_argument(
        "--no-save", action="store_true", help="Don't save snapshot after analysis"
    )

    args = parser.parse_args(argv)

    try:
        if args.history:
            snapshots = list_snapshots()
            if not snapshots:
                print("No snapshots yet. Run an analysis first.", file=sys.stderr)
            else:
                print(json.dumps(snapshots, indent=2))
            return

        if args.list:
            services = discover_services(project=args.project, region=args.region)
            print(json.dumps(services, indent=2))
            return

        if args.service:
            if not args.region:
                print(
                    "Error: --region is required when analyzing a specific service",
                    file=sys.stderr,
                )
                sys.exit(1)
            result = analyze_service(
                args.service,
                region=args.region,
                project=args.project,
                include_metrics=not args.no_metrics,
            )
            print(json.dumps(result, indent=2))
            return

        # Fleet overview
        result = build_overview(
            project=args.project,
            region=args.region,
            verbose=args.verbose,
        )

        # Compare with previous snapshot
        comparison = build_comparison_from_current(result)

        # Save snapshot (unless --no-save)
        if not args.no_save:
            snap_path = save_snapshot(result)
            print(f"Snapshot saved: {snap_path}", file=sys.stderr)

        if args.html:
            html_content = generate_dashboard(result, comparison=comparison)
            if args.output:
                out_path = Path(args.output)
            else:
                tmp = tempfile.NamedTemporaryFile(
                    suffix=".html",
                    prefix="cloudrun-dashboard-",
                    delete=False,
                )
                out_path = Path(tmp.name)
                tmp.close()

            out_path.write_text(html_content, encoding="utf-8")
            print(f"Dashboard written to: {out_path}", file=sys.stderr)
            webbrowser.open(f"file://{out_path.resolve()}")
        else:
            output = {"analysis": result}
            if comparison:
                output["comparison"] = comparison
            print(json.dumps(output, indent=2))

    except GcloudError as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse response - {e}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(
            "  Is gcloud installed? https://cloud.google.com/sdk/docs/install",
            file=sys.stderr,
        )
        sys.exit(1)
    except PermissionError as e:
        print(f"Error: Permission denied - {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc(file=sys.stderr)
        else:
            print("  Run with --verbose for full traceback.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
