"""Snapshot history - stores and compares analysis results over time."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _history_dir() -> Path:
    """Get the history directory, creating if needed."""
    d = Path.home() / ".cloudrun-agent" / "history"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_snapshot(data: dict[str, Any]) -> Path:
    """Save an analysis snapshot to disk. Returns the snapshot path."""
    ts = datetime.now(timezone.utc)
    filename = f"snapshot-{ts.strftime('%Y%m%d-%H%M%S')}.json"
    path = _history_dir() / filename

    snapshot = {
        "timestamp": ts.isoformat(),
        "version": "1",
        "fleet": data["fleet"],
        "services": [
            {k: v for k, v in svc.items() if k != "time_series"}
            for svc in data.get("services", [])
        ],
        "findings_by_group": data.get("findings_by_group", {}),
    }

    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return path


def list_snapshots() -> list[dict[str, Any]]:
    """List all saved snapshots, newest first."""
    history_dir = _history_dir()
    snapshots = []
    for path in sorted(history_dir.glob("snapshot-*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            snapshots.append(
                {
                    "path": str(path),
                    "timestamp": data.get("timestamp", ""),
                    "total_services": data.get("fleet", {}).get("total_services", 0),
                    "monthly_cost": data.get("fleet", {}).get("total_monthly_cost", 0),
                    "findings": data.get("fleet", {}).get("findings_summary", {}),
                }
            )
        except Exception:
            continue
    return snapshots


def load_snapshot(path: str) -> dict[str, Any]:
    """Load a snapshot from disk."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare_snapshots(
    current: dict[str, Any],
    previous: dict[str, Any],
) -> dict[str, Any]:
    """Compare two snapshots and return a diff summary."""
    cur_fleet = current.get("fleet", {})
    prev_fleet = previous.get("fleet", {})

    cur_findings = cur_fleet.get("findings_summary", {})
    prev_findings = prev_fleet.get("findings_summary", {})

    # Service-level diffs
    cur_svcs = {s["name"]: s for s in current.get("services", [])}
    prev_svcs = {s["name"]: s for s in previous.get("services", [])}

    added = [n for n in cur_svcs if n not in prev_svcs]
    removed = [n for n in prev_svcs if n not in cur_svcs]

    # Per-service changes
    service_changes: list[dict[str, Any]] = []
    for name in sorted(set(cur_svcs) & set(prev_svcs)):
        cur = cur_svcs[name]
        prev = prev_svcs[name]
        changes: dict[str, Any] = {"name": name}
        changed = False

        for key in (
            "cpu",
            "memory",
            "min_instances",
            "max_instances",
            "concurrency",
            "ingress",
        ):
            if cur.get(key) != prev.get(key):
                changes[key] = {"from": prev.get(key), "to": cur.get(key)}
                changed = True

        # Metric changes
        for key in (
            "daily_requests",
            "avg_cpu_util",
            "avg_mem_util",
            "latency_p99_s",
            "monthly_cost",
        ):
            cur_val = cur.get(key)
            prev_val = prev.get(key)
            if cur_val is not None and prev_val is not None and prev_val != 0:
                pct_change = (cur_val - prev_val) / abs(prev_val)
                if abs(pct_change) > 0.1:  # >10% change
                    changes[key] = {
                        "from": prev_val,
                        "to": cur_val,
                        "change_pct": round(pct_change * 100, 1),
                    }
                    changed = True

        # Finding count changes
        cur_fc = cur.get("findings_count", {})
        prev_fc = prev.get("findings_count", {})
        if cur_fc != prev_fc:
            changes["findings"] = {"from": prev_fc, "to": cur_fc}
            changed = True

        if changed:
            service_changes.append(changes)

    return {
        "previous_timestamp": previous.get("timestamp", ""),
        "current_timestamp": current.get(
            "timestamp", datetime.now(timezone.utc).isoformat()
        ),
        "fleet_delta": {
            "services": {
                "from": prev_fleet.get("total_services", 0),
                "to": cur_fleet.get("total_services", 0),
            },
            "monthly_cost": {
                "from": prev_fleet.get("total_monthly_cost", 0),
                "to": cur_fleet.get("total_monthly_cost", 0),
            },
            "daily_requests": {
                "from": prev_fleet.get("total_daily_requests", 0),
                "to": cur_fleet.get("total_daily_requests", 0),
            },
            "critical": {
                "from": prev_findings.get("critical", 0),
                "to": cur_findings.get("critical", 0),
            },
            "warnings": {
                "from": prev_findings.get("warning", 0),
                "to": cur_findings.get("warning", 0),
            },
        },
        "services_added": added,
        "services_removed": removed,
        "service_changes": service_changes,
    }


def get_latest_snapshot() -> dict[str, Any] | None:
    """Get the most recent snapshot, if any."""
    snapshots = list_snapshots()
    if not snapshots:
        return None
    return load_snapshot(snapshots[0]["path"])


def build_comparison_from_current(
    current_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Compare current analysis against the most recent snapshot.

    Returns None if no previous snapshot exists.
    """
    previous = get_latest_snapshot()
    if previous is None:
        return None

    # Build a snapshot-like structure from current data
    current_snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fleet": current_data["fleet"],
        "services": current_data.get("services", []),
    }

    return compare_snapshots(current_snapshot, previous)
