"""Tests for snapshot history: save, load, list, compare."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cloudrun_agent.history import (
    compare_snapshots,
    list_snapshots,
    load_snapshot,
    save_snapshot,
)


@pytest.fixture
def mock_history_dir(tmp_path):
    """Patch _history_dir to use a temp directory."""
    with patch("cloudrun_agent.history._history_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def sample_data():
    return {
        "fleet": {
            "total_services": 3,
            "total_monthly_cost": 150.0,
            "total_daily_requests": 50000,
            "findings_summary": {"critical": 2, "warning": 5, "info": 3},
        },
        "services": [
            {
                "name": "svc-a",
                "cpu": "1",
                "memory": "512Mi",
                "min_instances": 1,
                "max_instances": 50,
                "concurrency": 80,
                "ingress": "internal",
                "daily_requests": 30000,
                "avg_cpu_util": 0.45,
                "avg_mem_util": 0.60,
                "latency_p99_s": 0.4,
                "monthly_cost": 80.0,
                "findings_count": {"critical": 1, "warning": 2, "info": 1},
                "time_series": {"cpu": [1, 2, 3]},
            },
            {
                "name": "svc-b",
                "cpu": "2",
                "memory": "1Gi",
                "min_instances": 0,
                "max_instances": 100,
                "concurrency": 80,
                "ingress": "all",
                "daily_requests": 20000,
                "avg_cpu_util": 0.30,
                "avg_mem_util": 0.40,
                "latency_p99_s": 0.2,
                "monthly_cost": 70.0,
                "findings_count": {"critical": 1, "warning": 3, "info": 2},
            },
        ],
        "findings_by_group": {
            "resources": [{"severity": "warning", "category": "cpu_overprovisioned"}],
        },
    }


class TestSaveSnapshot:
    def test_saves_file(self, mock_history_dir, sample_data):
        path = save_snapshot(sample_data)
        assert path.exists()
        assert path.suffix == ".json"
        assert path.parent == mock_history_dir

    def test_snapshot_content(self, mock_history_dir, sample_data):
        path = save_snapshot(sample_data)
        content = json.loads(path.read_text())
        assert "timestamp" in content
        assert content["version"] == "1"
        assert content["fleet"]["total_services"] == 3
        assert len(content["services"]) == 2
        assert content["findings_by_group"] == sample_data["findings_by_group"]

    def test_time_series_stripped(self, mock_history_dir, sample_data):
        """time_series key should be removed from service entries."""
        path = save_snapshot(sample_data)
        content = json.loads(path.read_text())
        for svc in content["services"]:
            assert "time_series" not in svc

    def test_filename_format(self, mock_history_dir, sample_data):
        path = save_snapshot(sample_data)
        assert path.name.startswith("snapshot-")
        assert path.name.endswith(".json")


class TestListSnapshots:
    def test_empty_directory(self, mock_history_dir):
        result = list_snapshots()
        assert result == []

    def test_lists_snapshots_newest_first(self, mock_history_dir, sample_data):
        # Create two snapshots
        p1 = mock_history_dir / "snapshot-20250101-000000.json"
        p2 = mock_history_dir / "snapshot-20250102-000000.json"

        snap1 = {
            "timestamp": "2025-01-01T00:00:00Z",
            "fleet": {"total_services": 1, "total_monthly_cost": 50, "findings_summary": {}},
        }
        snap2 = {
            "timestamp": "2025-01-02T00:00:00Z",
            "fleet": {"total_services": 2, "total_monthly_cost": 100, "findings_summary": {}},
        }

        p1.write_text(json.dumps(snap1))
        p2.write_text(json.dumps(snap2))

        result = list_snapshots()
        assert len(result) == 2
        assert result[0]["timestamp"] == "2025-01-02T00:00:00Z"
        assert result[1]["timestamp"] == "2025-01-01T00:00:00Z"

    def test_skips_invalid_files(self, mock_history_dir):
        bad = mock_history_dir / "snapshot-bad.json"
        bad.write_text("not valid json{{{")
        result = list_snapshots()
        assert result == []

    def test_snapshot_metadata(self, mock_history_dir):
        snap = {
            "timestamp": "2025-01-01T00:00:00Z",
            "fleet": {
                "total_services": 5,
                "total_monthly_cost": 200,
                "findings_summary": {"critical": 1},
            },
        }
        p = mock_history_dir / "snapshot-20250101-000000.json"
        p.write_text(json.dumps(snap))

        result = list_snapshots()
        assert len(result) == 1
        assert result[0]["total_services"] == 5
        assert result[0]["monthly_cost"] == 200
        assert result[0]["findings"] == {"critical": 1}
        assert result[0]["path"] == str(p)


class TestLoadSnapshot:
    def test_load_valid(self, tmp_path):
        data = {"fleet": {"total_services": 2}, "timestamp": "2025-01-01T00:00:00Z"}
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))

        result = load_snapshot(str(path))
        assert result["fleet"]["total_services"] == 2

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_snapshot("/nonexistent/path.json")


class TestCompareSnapshots:
    @pytest.fixture
    def previous_snapshot(self):
        return {
            "timestamp": "2025-01-01T00:00:00Z",
            "fleet": {
                "total_services": 2,
                "total_monthly_cost": 100.0,
                "total_daily_requests": 40000,
                "findings_summary": {"critical": 1, "warning": 3},
            },
            "services": [
                {
                    "name": "svc-a",
                    "cpu": "1",
                    "memory": "512Mi",
                    "min_instances": 1,
                    "max_instances": 50,
                    "concurrency": 80,
                    "ingress": "all",
                    "daily_requests": 30000,
                    "avg_cpu_util": 0.45,
                    "avg_mem_util": 0.60,
                    "latency_p99_s": 0.4,
                    "monthly_cost": 60.0,
                    "findings_count": {"critical": 1, "warning": 2},
                },
                {
                    "name": "svc-b",
                    "cpu": "1",
                    "memory": "256Mi",
                    "min_instances": 0,
                    "max_instances": 100,
                    "concurrency": 80,
                    "ingress": "internal",
                    "daily_requests": 10000,
                    "avg_cpu_util": 0.30,
                    "avg_mem_util": 0.40,
                    "latency_p99_s": 0.2,
                    "monthly_cost": 40.0,
                    "findings_count": {"critical": 0, "warning": 1},
                },
            ],
        }

    @pytest.fixture
    def current_snapshot(self):
        return {
            "timestamp": "2025-01-02T00:00:00Z",
            "fleet": {
                "total_services": 3,
                "total_monthly_cost": 180.0,
                "total_daily_requests": 60000,
                "findings_summary": {"critical": 2, "warning": 5},
            },
            "services": [
                {
                    "name": "svc-a",
                    "cpu": "2",  # changed from 1
                    "memory": "512Mi",
                    "min_instances": 1,
                    "max_instances": 50,
                    "concurrency": 80,
                    "ingress": "internal",  # changed from all
                    "daily_requests": 30000,
                    "avg_cpu_util": 0.45,
                    "avg_mem_util": 0.60,
                    "latency_p99_s": 0.4,
                    "monthly_cost": 80.0,  # changed >10%
                    "findings_count": {"critical": 1, "warning": 3},
                },
                {
                    "name": "svc-b",
                    "cpu": "1",
                    "memory": "256Mi",
                    "min_instances": 0,
                    "max_instances": 100,
                    "concurrency": 80,
                    "ingress": "internal",
                    "daily_requests": 10000,
                    "avg_cpu_util": 0.30,
                    "avg_mem_util": 0.40,
                    "latency_p99_s": 0.2,
                    "monthly_cost": 40.0,
                    "findings_count": {"critical": 0, "warning": 1},
                },
                {
                    "name": "svc-c",  # new
                    "cpu": "1",
                    "memory": "512Mi",
                    "monthly_cost": 60.0,
                },
            ],
        }

    def test_services_added(self, current_snapshot, previous_snapshot):
        diff = compare_snapshots(current_snapshot, previous_snapshot)
        assert "svc-c" in diff["services_added"]

    def test_services_removed(self, previous_snapshot):
        current = {
            "timestamp": "2025-01-02T00:00:00Z",
            "fleet": {"total_services": 1},
            "services": [
                {"name": "svc-a", "cpu": "1"},
            ],
        }
        diff = compare_snapshots(current, previous_snapshot)
        assert "svc-b" in diff["services_removed"]

    def test_fleet_delta(self, current_snapshot, previous_snapshot):
        diff = compare_snapshots(current_snapshot, previous_snapshot)
        fd = diff["fleet_delta"]
        assert fd["services"]["from"] == 2
        assert fd["services"]["to"] == 3
        assert fd["monthly_cost"]["from"] == 100.0
        assert fd["monthly_cost"]["to"] == 180.0

    def test_config_changes_detected(self, current_snapshot, previous_snapshot):
        diff = compare_snapshots(current_snapshot, previous_snapshot)
        svc_a_changes = [c for c in diff["service_changes"] if c["name"] == "svc-a"]
        assert len(svc_a_changes) == 1
        changes = svc_a_changes[0]
        assert "cpu" in changes
        assert changes["cpu"]["from"] == "1"
        assert changes["cpu"]["to"] == "2"
        assert "ingress" in changes
        assert changes["ingress"]["from"] == "all"
        assert changes["ingress"]["to"] == "internal"

    def test_metric_change_detected(self, current_snapshot, previous_snapshot):
        diff = compare_snapshots(current_snapshot, previous_snapshot)
        svc_a_changes = [c for c in diff["service_changes"] if c["name"] == "svc-a"]
        assert len(svc_a_changes) == 1
        changes = svc_a_changes[0]
        # monthly_cost: 60 -> 80, >10% change
        assert "monthly_cost" in changes
        assert changes["monthly_cost"]["from"] == 60.0
        assert changes["monthly_cost"]["to"] == 80.0

    def test_no_changes_for_unchanged_service(self, current_snapshot, previous_snapshot):
        diff = compare_snapshots(current_snapshot, previous_snapshot)
        svc_b_changes = [c for c in diff["service_changes"] if c["name"] == "svc-b"]
        assert len(svc_b_changes) == 0

    def test_findings_changes_detected(self, current_snapshot, previous_snapshot):
        diff = compare_snapshots(current_snapshot, previous_snapshot)
        svc_a_changes = [c for c in diff["service_changes"] if c["name"] == "svc-a"]
        changes = svc_a_changes[0]
        assert "findings" in changes

    def test_timestamps(self, current_snapshot, previous_snapshot):
        diff = compare_snapshots(current_snapshot, previous_snapshot)
        assert diff["previous_timestamp"] == "2025-01-01T00:00:00Z"
        assert diff["current_timestamp"] == "2025-01-02T00:00:00Z"

    def test_empty_snapshots(self):
        diff = compare_snapshots({}, {})
        assert diff["services_added"] == []
        assert diff["services_removed"] == []
        assert diff["service_changes"] == []

    def test_metric_small_change_ignored(self):
        """Changes < 10% should not be reported."""
        prev = {
            "fleet": {},
            "services": [
                {"name": "svc", "monthly_cost": 100.0},
            ],
        }
        curr = {
            "fleet": {},
            "services": [
                {"name": "svc", "monthly_cost": 105.0},  # 5% change
            ],
        }
        diff = compare_snapshots(curr, prev)
        svc_changes = [c for c in diff["service_changes"] if c["name"] == "svc"]
        if svc_changes:
            assert "monthly_cost" not in svc_changes[0]

    def test_metric_zero_previous_ignored(self):
        """Zero previous value should not cause division by zero."""
        prev = {
            "fleet": {},
            "services": [
                {"name": "svc", "monthly_cost": 0},
            ],
        }
        curr = {
            "fleet": {},
            "services": [
                {"name": "svc", "monthly_cost": 50.0},
            ],
        }
        diff = compare_snapshots(curr, prev)
        # Should not crash, and should not report change (prev_val == 0 check)
        assert isinstance(diff, dict)
