#!/usr/bin/env python3
"""Run one jev-ultrafast exploration and print a single JSON transcript.

This file executes *inside the jev-ultrafast checkout's environment* (it
imports `jev_ultrafast`), launched by `cli.py explore`. Nothing else in tonone
imports it, and tonone never depends on `jev_ultrafast` being installed.

Contract, identical to lib/jev/cli.js: exit code 0 always, exactly one JSON
object on stdout, never a traceback. A failed run is a JSON document with
`ok: false`, not a crash.

The transcript carries no page text, no screenshots and no DOM — only the
actions the agent executed, the URL each one ran against, and the model's
confidence in it. That is what a test author needs and it is the smallest
thing that works.
"""

import argparse
import json
import sys
import time

FIELDS = (
    "step",
    "action",
    "kind",
    "operation",
    "text",
    "url",
    "page_changed",
    "probability",
    "confidence",
    "elapsed_ms",
)


def emit(payload):
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()
    sys.exit(0)


def step_of(entry):
    return {key: entry.get(key) for key in FIELDS}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--goal", action="append", required=True)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    try:
        from jev_ultrafast import Agent
    except Exception as exc:  # driver absent or broken install
        emit(
            {
                "ok": False,
                "reason": "driver_import_failed",
                "error": str(exc),
                "steps": [],
            }
        )

    started = time.perf_counter()
    steps, status, final_url, error = [], "error", args.url, None

    try:
        with Agent(args.url, args.goal) as agent:
            for state in agent.run():
                steps = [step_of(entry) for entry in state["history"]]
                status = state["status"]
                final_url = state["page"]["url"]
                if len(steps) >= args.max_steps:
                    status = "step_budget"
                    break
                if time.perf_counter() - started > args.timeout:
                    status = "timeout"
                    break
    except KeyboardInterrupt:
        status = "interrupted"
    except Exception as exc:
        # Includes jev-ultrafast's own budget ValueError and any browser fault.
        status = "error"
        error = f"{type(exc).__name__}: {exc}"

    emit(
        {
            "ok": error is None,
            "source": "jev-ultrafast",
            "status": status,
            "goal": args.goal,
            "start_url": args.url,
            "final_url": final_url,
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "steps": steps,
            "error": error,
        }
    )


if __name__ == "__main__":
    main()
