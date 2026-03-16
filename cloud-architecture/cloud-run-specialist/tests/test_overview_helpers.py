"""Tests for overview.py helper functions."""

import pytest
from cloudrun_agent.models.service import (
    NetworkConfig,
    ResourceLimits,
    ScalingConfig,
    ServiceConfig,
)
from cloudrun_agent.overview import (
    _compute_fleet_infra,
    _count_by_severity,
    _group_findings,
    _severity_rank,
    _worst_severity,
)


class TestSeverityRank:
    def test_critical(self):
        assert _severity_rank("critical") == 0

    def test_warning(self):
        assert _severity_rank("warning") == 1

    def test_info(self):
        assert _severity_rank("info") == 2

    def test_unknown(self):
        assert _severity_rank("unknown") == 3

    def test_empty_string(self):
        assert _severity_rank("") == 3

    def test_ordering(self):
        assert _severity_rank("critical") < _severity_rank("warning")
        assert _severity_rank("warning") < _severity_rank("info")
        assert _severity_rank("info") < _severity_rank("unknown")


class TestWorstSeverity:
    def test_empty_list(self):
        assert _worst_severity([]) == "ok"

    def test_single_critical(self):
        findings = [{"severity": "critical"}]
        assert _worst_severity(findings) == "critical"

    def test_mixed_severities(self):
        findings = [
            {"severity": "info"},
            {"severity": "critical"},
            {"severity": "warning"},
        ]
        assert _worst_severity(findings) == "critical"

    def test_all_info(self):
        findings = [{"severity": "info"}, {"severity": "info"}]
        assert _worst_severity(findings) == "info"

    def test_warning_and_info(self):
        findings = [{"severity": "warning"}, {"severity": "info"}]
        assert _worst_severity(findings) == "warning"


class TestCountBySeverity:
    def test_empty_list(self):
        result = _count_by_severity([])
        assert result == {"critical": 0, "warning": 0, "info": 0}

    def test_counts(self):
        findings = [
            {"severity": "critical"},
            {"severity": "critical"},
            {"severity": "warning"},
            {"severity": "info"},
            {"severity": "info"},
            {"severity": "info"},
        ]
        result = _count_by_severity(findings)
        assert result["critical"] == 2
        assert result["warning"] == 1
        assert result["info"] == 3

    def test_unknown_severity_counted(self):
        findings = [{"severity": "unknown"}]
        result = _count_by_severity(findings)
        assert result.get("unknown", 0) == 1

    def test_missing_severity_defaults_to_info(self):
        findings = [{}]
        result = _count_by_severity(findings)
        assert result["info"] == 1


class TestGroupFindings:
    def test_empty(self):
        assert _group_findings([]) == []

    def test_single_finding(self):
        findings = [
            {
                "severity": "warning",
                "category": "cpu_overprovisioned",
                "message": "Too much CPU",
                "recommendation": "Reduce CPU",
                "service": "svc-a",
                "group": "resources",
            }
        ]
        result = _group_findings(findings)
        assert len(result) == 1
        assert result[0]["category"] == "cpu_overprovisioned"
        assert result[0]["affected_services"] == ["svc-a"]

    def test_groups_same_category(self):
        findings = [
            {
                "severity": "warning",
                "category": "public_ingress",
                "message": "Public",
                "recommendation": "Fix",
                "service": "svc-a",
                "group": "security",
            },
            {
                "severity": "warning",
                "category": "public_ingress",
                "message": "Public",
                "recommendation": "Fix",
                "service": "svc-b",
                "group": "security",
            },
        ]
        result = _group_findings(findings)
        assert len(result) == 1
        assert set(result[0]["affected_services"]) == {"svc-a", "svc-b"}

    def test_different_categories_separate(self):
        findings = [
            {
                "severity": "critical",
                "category": "high_error_rate",
                "message": "Errors",
                "recommendation": "Fix",
                "service": "svc-a",
                "group": "performance",
            },
            {
                "severity": "warning",
                "category": "public_ingress",
                "message": "Public",
                "recommendation": "Fix",
                "service": "svc-a",
                "group": "security",
            },
        ]
        result = _group_findings(findings)
        assert len(result) == 2

    def test_severity_upgrade_in_group(self):
        """If a more severe finding is added to a group, severity should upgrade."""
        findings = [
            {
                "severity": "warning",
                "category": "issue",
                "message": "Warning message",
                "recommendation": "Fix",
                "service": "svc-a",
                "group": "perf",
            },
            {
                "severity": "critical",
                "category": "issue",
                "message": "Critical message",
                "recommendation": "Fix now",
                "service": "svc-b",
                "group": "perf",
            },
        ]
        result = _group_findings(findings)
        assert len(result) == 1
        assert result[0]["severity"] == "critical"
        assert result[0]["message"] == "Critical message"

    def test_sorted_by_severity_then_count(self):
        findings = [
            {
                "severity": "info",
                "category": "info_issue",
                "message": "Info",
                "recommendation": "OK",
                "service": "svc-a",
                "group": "other",
            },
            {
                "severity": "info",
                "category": "info_issue",
                "message": "Info",
                "recommendation": "OK",
                "service": "svc-b",
                "group": "other",
            },
            {
                "severity": "critical",
                "category": "crit_issue",
                "message": "Critical",
                "recommendation": "Fix",
                "service": "svc-a",
                "group": "other",
            },
        ]
        result = _group_findings(findings)
        assert result[0]["category"] == "crit_issue"
        assert result[1]["category"] == "info_issue"

    def test_group_field_preserved(self):
        findings = [
            {
                "severity": "warning",
                "category": "test",
                "message": "msg",
                "recommendation": "rec",
                "service": "svc",
                "group": "resources",
            }
        ]
        result = _group_findings(findings)
        assert result[0]["group"] == "resources"


class TestComputeFleetInfra:
    def test_empty_list(self):
        result = _compute_fleet_infra([])
        assert result["regions"] == {}
        assert result["total_vcpu_allocated"] == 0.0
        assert result["total_memory_gib"] == 0.0
        assert result["max_instance_capacity"] == 0
        assert result["services_with_min_instances"] == 0
        assert result["services_with_vpc"] == 0
        assert result["services_with_startup_boost"] == 0
        assert result["services_with_threat_detection"] == 0
        assert result["unique_service_accounts"] == 0
        assert result["services_using_default_sa"] == 0
        assert result["single_concurrency_services"] == 0

    def test_single_service(self):
        configs = [
            ServiceConfig(
                name="svc-a",
                region="us-central1",
                service_account="sa@proj.iam.gserviceaccount.com",
                resources=ResourceLimits(cpu="2", memory="1Gi"),
                scaling=ScalingConfig(
                    min_instances=1, max_instances=50, concurrency=80
                ),
                network=NetworkConfig(
                    ingress="internal",
                    vpc_connector="projects/p/locations/r/connectors/c",
                ),
                startup_cpu_boost=True,
                threat_detection=True,
            ),
        ]
        result = _compute_fleet_infra(configs)
        assert result["regions"] == {"us-central1": 1}
        assert result["total_vcpu_allocated"] == 2.0
        assert result["total_memory_gib"] == 1.0
        assert result["max_instance_capacity"] == 50
        assert result["services_with_min_instances"] == 1
        assert result["ingress_breakdown"] == {"internal": 1}
        assert result["services_with_vpc"] == 1
        assert result["services_with_startup_boost"] == 1
        assert result["services_with_threat_detection"] == 1
        assert result["unique_service_accounts"] == 1
        assert result["services_using_default_sa"] == 0
        assert result["single_concurrency_services"] == 0

    def test_multiple_services(self):
        configs = [
            ServiceConfig(
                name="svc-a",
                region="us-central1",
                service_account="sa-a@proj.iam.gserviceaccount.com",
                resources=ResourceLimits(cpu="1", memory="512Mi"),
                scaling=ScalingConfig(
                    min_instances=0, max_instances=100, concurrency=1
                ),
                network=NetworkConfig(ingress="all"),
            ),
            ServiceConfig(
                name="svc-b",
                region="us-central1",
                service_account="sa-b@proj.iam.gserviceaccount.com",
                resources=ResourceLimits(cpu="2", memory="1Gi"),
                scaling=ScalingConfig(
                    min_instances=2, max_instances=50, concurrency=80
                ),
                network=NetworkConfig(ingress="internal", vpc_network="my-vpc"),
            ),
            ServiceConfig(
                name="svc-c",
                region="europe-west1",
                service_account="",
                resources=ResourceLimits(cpu="500m", memory="256Mi"),
                scaling=ScalingConfig(
                    min_instances=0, max_instances=10, concurrency=80
                ),
                network=NetworkConfig(ingress="all"),
            ),
        ]
        result = _compute_fleet_infra(configs)
        assert result["regions"] == {"us-central1": 2, "europe-west1": 1}
        assert result["total_vcpu_allocated"] == pytest.approx(3.5, rel=1e-3)
        # round((512+1024+256)/1024, 1) = round(1.75, 1) = 1.8 (Python banker's rounding)
        assert result["total_memory_gib"] == 1.8
        assert result["max_instance_capacity"] == 160
        assert result["services_with_min_instances"] == 1
        assert result["ingress_breakdown"] == {"all": 2, "internal": 1}
        assert result["services_with_vpc"] == 1
        assert result["unique_service_accounts"] == 2
        assert result["services_using_default_sa"] == 1
        assert result["single_concurrency_services"] == 1

    def test_default_service_account_detection(self):
        configs = [
            ServiceConfig(
                name="svc",
                service_account="123456-compute@developer.gserviceaccount.com",
                resources=ResourceLimits(cpu="1", memory="256Mi"),
            ),
        ]
        result = _compute_fleet_infra(configs)
        assert result["services_using_default_sa"] == 1
        assert result["unique_service_accounts"] == 1

    def test_empty_service_account(self):
        configs = [
            ServiceConfig(
                name="svc",
                service_account="",
                resources=ResourceLimits(cpu="1", memory="256Mi"),
            ),
        ]
        result = _compute_fleet_infra(configs)
        assert result["services_using_default_sa"] == 1
        assert result["unique_service_accounts"] == 0

    def test_vpc_network_counts_as_vpc(self):
        configs = [
            ServiceConfig(
                name="svc",
                resources=ResourceLimits(cpu="1", memory="256Mi"),
                network=NetworkConfig(vpc_network="my-vpc"),
            ),
        ]
        result = _compute_fleet_infra(configs)
        assert result["services_with_vpc"] == 1

    def test_empty_ingress_defaults_to_all(self):
        configs = [
            ServiceConfig(
                name="svc",
                resources=ResourceLimits(cpu="1", memory="256Mi"),
                network=NetworkConfig(ingress=""),
            ),
        ]
        result = _compute_fleet_infra(configs)
        assert result["ingress_breakdown"] == {"all": 1}
