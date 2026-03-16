"""Tests for all 5 analyzers: resources, performance, pricing, security, traffic."""

import pytest
from cloudrun_agent.analyzers.performance import (
    analyze_performance,
)
from cloudrun_agent.analyzers.pricing import (
    REQUEST_PER_MILLION,
    PricingEstimate,
)
from cloudrun_agent.analyzers.pricing import _parse_cpu_cores as pricing_parse_cpu
from cloudrun_agent.analyzers.pricing import (
    _parse_memory_gib,
    estimate_pricing,
)
from cloudrun_agent.analyzers.resources import (
    _parse_cpu_cores,
    _parse_memory_mi,
    analyze_resource_waste,
)
from cloudrun_agent.analyzers.security import (
    analyze_security,
)
from cloudrun_agent.analyzers.traffic import (
    analyze_traffic,
)
from cloudrun_agent.models.service import (
    MetricPoint,
    NetworkConfig,
    ResourceLimits,
    ScalingConfig,
    ServiceConfig,
    ServiceMetrics,
    ServiceRevision,
)

# =============================================================================
# Resources Analyzer
# =============================================================================


class TestParseCpuCores:
    def test_millicores(self):
        assert _parse_cpu_cores("1000m") == 1.0

    def test_millicores_500(self):
        assert _parse_cpu_cores("500m") == 0.5

    def test_whole_number(self):
        assert _parse_cpu_cores("2") == 2.0

    def test_empty_string(self):
        assert _parse_cpu_cores("") == 0.0

    def test_fractional(self):
        assert _parse_cpu_cores("0.5") == 0.5

    def test_four_cores(self):
        assert _parse_cpu_cores("4") == 4.0

    def test_250m(self):
        assert _parse_cpu_cores("250m") == 0.25


class TestParseMemoryMi:
    def test_mi_suffix(self):
        assert _parse_memory_mi("512Mi") == 512.0

    def test_gi_suffix(self):
        assert _parse_memory_mi("1Gi") == 1024.0

    def test_gi_fractional(self):
        assert _parse_memory_mi("2Gi") == 2048.0

    def test_ki_suffix(self):
        assert _parse_memory_mi("1024Ki") == 1.0

    def test_empty_string(self):
        assert _parse_memory_mi("") == 0.0

    def test_raw_number(self):
        assert _parse_memory_mi("256") == 256.0

    def test_4gi(self):
        assert _parse_memory_mi("4Gi") == 4096.0


class TestAnalyzeResourceWaste:
    def test_no_findings_for_small_service(self):
        config = ServiceConfig(
            resources=ResourceLimits(cpu="1", memory="512Mi"),
            scaling=ScalingConfig(min_instances=0),
        )
        findings = analyze_resource_waste(config)
        assert len(findings) == 0

    def test_cpu_overprovisioned(self, overprovisioned_config):
        findings = analyze_resource_waste(overprovisioned_config)
        categories = [f.category for f in findings]
        assert "cpu_overprovisioned" in categories

    def test_memory_overprovisioned(self):
        config = ServiceConfig(
            resources=ResourceLimits(cpu="1", memory="4Gi"),
            scaling=ScalingConfig(min_instances=0),
        )
        findings = analyze_resource_waste(config)
        categories = [f.category for f in findings]
        assert "memory_overprovisioned" in categories

    def test_min_instances_cost(self):
        config = ServiceConfig(
            resources=ResourceLimits(cpu="1", memory="512Mi"),
            scaling=ScalingConfig(min_instances=1),
        )
        findings = analyze_resource_waste(config)
        categories = [f.category for f in findings]
        assert "min_instances_cost" in categories

    def test_idle_cpu_cost_with_min_instances_and_high_cpu(self):
        config = ServiceConfig(
            resources=ResourceLimits(cpu="2", memory="512Mi"),
            scaling=ScalingConfig(min_instances=2),
        )
        findings = analyze_resource_waste(config)
        categories = [f.category for f in findings]
        assert "idle_cpu_cost" in categories

    def test_no_idle_cpu_cost_with_1_cpu(self):
        config = ServiceConfig(
            resources=ResourceLimits(cpu="1", memory="512Mi"),
            scaling=ScalingConfig(min_instances=2),
        )
        findings = analyze_resource_waste(config)
        categories = [f.category for f in findings]
        assert "idle_cpu_cost" not in categories

    def test_cpu_underutilized_with_metrics(
        self, overprovisioned_config, underutilized_metrics
    ):
        findings = analyze_resource_waste(overprovisioned_config, underutilized_metrics)
        categories = [f.category for f in findings]
        assert "cpu_underutilized" in categories

    def test_memory_underutilized_with_metrics(
        self, overprovisioned_config, underutilized_metrics
    ):
        findings = analyze_resource_waste(overprovisioned_config, underutilized_metrics)
        categories = [f.category for f in findings]
        assert "memory_underutilized" in categories

    def test_no_metric_findings_without_metrics(self, overprovisioned_config):
        findings = analyze_resource_waste(overprovisioned_config, None)
        categories = [f.category for f in findings]
        assert "cpu_underutilized" not in categories
        assert "memory_underutilized" not in categories

    def test_no_underutilization_with_good_usage(self, basic_config, basic_metrics):
        findings = analyze_resource_waste(basic_config, basic_metrics)
        categories = [f.category for f in findings]
        assert "cpu_underutilized" not in categories
        assert "memory_underutilized" not in categories

    def test_empty_metrics(self, basic_config, empty_metrics):
        findings = analyze_resource_waste(basic_config, empty_metrics)
        categories = [f.category for f in findings]
        assert "cpu_underutilized" not in categories

    def test_findings_are_frozen(self, overprovisioned_config):
        findings = analyze_resource_waste(overprovisioned_config)
        assert len(findings) > 0
        with pytest.raises(AttributeError):
            findings[0].severity = "info"  # type: ignore[misc]

    def test_returns_tuple(self, default_config):
        result = analyze_resource_waste(default_config)
        assert isinstance(result, tuple)


# =============================================================================
# Performance Analyzer
# =============================================================================


class TestAnalyzePerformance:
    def test_cold_start_risk(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=0),
        )
        findings = analyze_performance(config)
        categories = [f.category for f in findings]
        assert "cold_start_risk" in categories

    def test_no_cold_start_with_min_instances(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=1),
        )
        findings = analyze_performance(config)
        categories = [f.category for f in findings]
        assert "cold_start_risk" not in categories

    def test_high_concurrency(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=1, concurrency=300),
        )
        findings = analyze_performance(config)
        categories = [f.category for f in findings]
        assert "high_concurrency" in categories

    def test_single_concurrency(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=1, concurrency=1),
        )
        findings = analyze_performance(config)
        categories = [f.category for f in findings]
        assert "single_concurrency" in categories

    def test_low_max_instances(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=1, max_instances=5),
        )
        findings = analyze_performance(config)
        categories = [f.category for f in findings]
        assert "low_max_instances" in categories

    def test_no_low_max_instances_at_10(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=1, max_instances=10),
        )
        findings = analyze_performance(config)
        categories = [f.category for f in findings]
        assert "low_max_instances" not in categories

    def test_high_latency_critical(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=1, max_instances=100)
        )
        metrics = ServiceMetrics(
            request_latency_p99=(
                MetricPoint(timestamp="t1", value=2.5),
                MetricPoint(timestamp="t2", value=3.0),
            ),
        )
        findings = analyze_performance(config, metrics)
        categories = [f.category for f in findings]
        assert "high_latency" in categories
        critical = [f for f in findings if f.category == "high_latency"]
        assert critical[0].severity == "critical"

    def test_elevated_latency_warning(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=1, max_instances=100)
        )
        metrics = ServiceMetrics(
            request_latency_p99=(
                MetricPoint(timestamp="t1", value=0.6),
                MetricPoint(timestamp="t2", value=0.8),
            ),
        )
        findings = analyze_performance(config, metrics)
        categories = [f.category for f in findings]
        assert "elevated_latency" in categories

    def test_no_latency_finding_for_fast_service(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=1, max_instances=100)
        )
        metrics = ServiceMetrics(
            request_latency_p99=(
                MetricPoint(timestamp="t1", value=0.1),
                MetricPoint(timestamp="t2", value=0.15),
            ),
        )
        findings = analyze_performance(config, metrics)
        categories = [f.category for f in findings]
        assert "high_latency" not in categories
        assert "elevated_latency" not in categories

    def test_high_error_rate_critical(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=1, max_instances=100)
        )
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=1000),),
            error_count=(MetricPoint(timestamp="t1", value=100),),
        )
        findings = analyze_performance(config, metrics)
        categories = [f.category for f in findings]
        assert "high_error_rate" in categories

    def test_elevated_error_rate_warning(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=1, max_instances=100)
        )
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=1000),),
            error_count=(MetricPoint(timestamp="t1", value=20),),
        )
        findings = analyze_performance(config, metrics)
        categories = [f.category for f in findings]
        assert "elevated_error_rate" in categories

    def test_no_error_findings_without_errors(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=1, max_instances=100)
        )
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=1000),),
            error_count=(MetricPoint(timestamp="t1", value=1),),
        )
        findings = analyze_performance(config, metrics)
        categories = [f.category for f in findings]
        assert "high_error_rate" not in categories
        assert "elevated_error_rate" not in categories

    def test_no_error_findings_zero_requests(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=1, max_instances=100)
        )
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=0),),
            error_count=(MetricPoint(timestamp="t1", value=0),),
        )
        findings = analyze_performance(config, metrics)
        categories = [f.category for f in findings]
        assert "high_error_rate" not in categories

    def test_no_metrics(self):
        config = ServiceConfig(
            scaling=ScalingConfig(min_instances=1, max_instances=100)
        )
        findings = analyze_performance(config, None)
        categories = [f.category for f in findings]
        assert "high_latency" not in categories
        assert "high_error_rate" not in categories

    def test_returns_tuple(self, default_config):
        result = analyze_performance(default_config)
        assert isinstance(result, tuple)


# =============================================================================
# Pricing Analyzer
# =============================================================================


class TestPricingParseCpu:
    def test_empty_defaults_to_1(self):
        assert pricing_parse_cpu("") == 1.0

    def test_millicores(self):
        assert pricing_parse_cpu("1000m") == 1.0

    def test_whole(self):
        assert pricing_parse_cpu("2") == 2.0


class TestParseMemoryGib:
    def test_empty_defaults_to_0_5(self):
        assert _parse_memory_gib("") == 0.5

    def test_gi(self):
        assert _parse_memory_gib("2Gi") == 2.0

    def test_mi(self):
        assert _parse_memory_gib("512Mi") == pytest.approx(0.5, rel=1e-3)

    def test_raw_number(self):
        assert _parse_memory_gib("1") == 1.0


class TestEstimatePricing:
    def test_basic_estimate(self, basic_config):
        pricing = estimate_pricing(basic_config, daily_requests=100_000)
        assert isinstance(pricing, PricingEstimate)
        assert pricing.daily_total > 0
        assert pricing.monthly_estimate == pytest.approx(
            pricing.daily_total * 30, rel=1e-3
        )

    def test_default_requests_without_metrics(self, basic_config):
        pricing = estimate_pricing(basic_config)
        assert "Using estimated 10k daily requests" in pricing.findings[0]

    def test_requests_from_metrics(self, basic_config, basic_metrics):
        pricing = estimate_pricing(basic_config, basic_metrics)
        # Should not have the default request warning
        assert not any("10k daily requests" in f for f in pricing.findings)

    def test_min_instance_cost(self):
        config = ServiceConfig(
            resources=ResourceLimits(cpu="1", memory="512Mi"),
            scaling=ScalingConfig(min_instances=2),
        )
        pricing = estimate_pricing(config, daily_requests=1000)
        assert pricing.daily_min_instance_cost > 0
        assert any("Min instances" in f for f in pricing.findings)

    def test_no_min_instance_cost_at_zero(self):
        config = ServiceConfig(
            resources=ResourceLimits(cpu="1", memory="512Mi"),
            scaling=ScalingConfig(min_instances=0),
        )
        pricing = estimate_pricing(config, daily_requests=1000)
        assert pricing.daily_min_instance_cost == 0.0

    def test_overprovisioned_cpu_finding(self):
        config = ServiceConfig(
            resources=ResourceLimits(cpu="4", memory="512Mi"),
            scaling=ScalingConfig(min_instances=0),
        )
        pricing = estimate_pricing(config, daily_requests=1000)
        assert any("over-provisioned" in f for f in pricing.findings)

    def test_concurrency_1_finding(self):
        config = ServiceConfig(
            resources=ResourceLimits(cpu="2", memory="1Gi"),
            scaling=ScalingConfig(min_instances=2, concurrency=1),
        )
        pricing = estimate_pricing(config, daily_requests=100_000)
        # This should produce a high monthly cost and concurrency=1 warning
        if pricing.monthly_estimate > 100:
            assert any("Concurrency=1" in f for f in pricing.findings)

    def test_idle_cost_exceeds_active_cost_finding(self):
        config = ServiceConfig(
            resources=ResourceLimits(cpu="2", memory="1Gi"),
            scaling=ScalingConfig(min_instances=5),
        )
        pricing = estimate_pricing(config, daily_requests=100)
        assert any("Idle min-instance cost exceeds" in f for f in pricing.findings)

    def test_all_costs_rounded(self, basic_config):
        pricing = estimate_pricing(basic_config, daily_requests=50_000)
        # Verify rounding to 4 decimal places for daily costs
        assert pricing.daily_cpu_cost == round(pricing.daily_cpu_cost, 4)
        assert pricing.daily_memory_cost == round(pricing.daily_memory_cost, 4)
        assert pricing.daily_request_cost == round(pricing.daily_request_cost, 4)

    def test_explicit_daily_requests_override(self, basic_config, basic_metrics):
        pricing = estimate_pricing(basic_config, basic_metrics, daily_requests=999)
        # With explicit daily_requests, should use that value
        expected_req_cost = round((999 / 1_000_000) * REQUEST_PER_MILLION, 4)
        assert pricing.daily_request_cost == expected_req_cost

    def test_returns_frozen(self, basic_config):
        pricing = estimate_pricing(basic_config, daily_requests=1000)
        with pytest.raises(AttributeError):
            pricing.daily_total = 0  # type: ignore[misc]


# =============================================================================
# Security Analyzer
# =============================================================================


class TestAnalyzeSecurity:
    def test_public_ingress_warning(self):
        config = ServiceConfig(network=NetworkConfig(ingress="all"))
        findings = analyze_security(config)
        categories = [f.category for f in findings]
        assert "public_ingress" in categories

    def test_empty_ingress_warning(self):
        config = ServiceConfig(network=NetworkConfig(ingress=""))
        findings = analyze_security(config)
        categories = [f.category for f in findings]
        assert "public_ingress" in categories

    def test_no_public_ingress_for_internal(self):
        config = ServiceConfig(network=NetworkConfig(ingress="internal"))
        findings = analyze_security(config)
        categories = [f.category for f in findings]
        assert "public_ingress" not in categories

    def test_default_service_account(self):
        config = ServiceConfig(
            service_account="123456-compute@developer.gserviceaccount.com",
            network=NetworkConfig(ingress="internal"),
        )
        findings = analyze_security(config)
        categories = [f.category for f in findings]
        assert "default_service_account" in categories

    def test_empty_service_account(self):
        config = ServiceConfig(
            service_account="",
            network=NetworkConfig(ingress="internal"),
        )
        findings = analyze_security(config)
        categories = [f.category for f in findings]
        assert "default_service_account" in categories

    def test_custom_service_account_ok(self):
        config = ServiceConfig(
            service_account="my-svc@my-project.iam.gserviceaccount.com",
            network=NetworkConfig(ingress="internal"),
        )
        findings = analyze_security(config)
        categories = [f.category for f in findings]
        assert "default_service_account" not in categories

    def test_no_vpc_connector(self):
        config = ServiceConfig(
            network=NetworkConfig(ingress="internal", vpc_connector=""),
        )
        findings = analyze_security(config)
        categories = [f.category for f in findings]
        assert "no_vpc_connector" in categories

    def test_has_vpc_connector(self):
        config = ServiceConfig(
            network=NetworkConfig(
                ingress="internal",
                vpc_connector="projects/p/locations/r/connectors/c",
            ),
        )
        findings = analyze_security(config)
        categories = [f.category for f in findings]
        assert "no_vpc_connector" not in categories

    def test_iam_all_users(self):
        config = ServiceConfig(
            service_account="sa@proj.iam.gserviceaccount.com",
            network=NetworkConfig(ingress="internal", vpc_connector="conn"),
        )
        iam_policy = {
            "bindings": [
                {
                    "role": "roles/run.invoker",
                    "members": ["allUsers"],
                }
            ]
        }
        findings = analyze_security(config, iam_policy)
        categories = [f.category for f in findings]
        assert "public_iam" in categories

    def test_iam_all_authenticated_users(self):
        config = ServiceConfig(
            service_account="sa@proj.iam.gserviceaccount.com",
            network=NetworkConfig(ingress="internal", vpc_connector="conn"),
        )
        iam_policy = {
            "bindings": [
                {
                    "role": "roles/run.invoker",
                    "members": ["allAuthenticatedUsers"],
                }
            ]
        }
        findings = analyze_security(config, iam_policy)
        categories = [f.category for f in findings]
        assert "broad_iam" in categories

    def test_iam_specific_user_ok(self):
        config = ServiceConfig(
            service_account="sa@proj.iam.gserviceaccount.com",
            network=NetworkConfig(ingress="internal", vpc_connector="conn"),
        )
        iam_policy = {
            "bindings": [
                {
                    "role": "roles/run.invoker",
                    "members": ["serviceAccount:other@proj.iam.gserviceaccount.com"],
                }
            ]
        }
        findings = analyze_security(config, iam_policy)
        categories = [f.category for f in findings]
        assert "public_iam" not in categories
        assert "broad_iam" not in categories

    def test_no_iam_policy(self, basic_config):
        findings = analyze_security(basic_config, None)
        categories = [f.category for f in findings]
        assert "public_iam" not in categories

    def test_plaintext_secrets(self, insecure_config):
        findings = analyze_security(insecure_config)
        categories = [f.category for f in findings]
        assert "plaintext_secrets" in categories

    def test_secret_from_secret_manager_ok(self):
        config = ServiceConfig(
            service_account="sa@proj.iam.gserviceaccount.com",
            network=NetworkConfig(ingress="internal", vpc_connector="conn"),
            env_vars={"API_KEY": "<from-secret>"},
        )
        findings = analyze_security(config)
        categories = [f.category for f in findings]
        assert "plaintext_secrets" not in categories

    def test_non_sensitive_env_vars_ok(self):
        config = ServiceConfig(
            service_account="sa@proj.iam.gserviceaccount.com",
            network=NetworkConfig(ingress="internal", vpc_connector="conn"),
            env_vars={"PORT": "8080", "LOG_LEVEL": "info"},
        )
        findings = analyze_security(config)
        categories = [f.category for f in findings]
        assert "plaintext_secrets" not in categories

    def test_multiple_iam_bindings(self):
        config = ServiceConfig(
            service_account="sa@proj.iam.gserviceaccount.com",
            network=NetworkConfig(ingress="internal", vpc_connector="conn"),
        )
        iam_policy = {
            "bindings": [
                {"role": "roles/run.invoker", "members": ["allUsers"]},
                {"role": "roles/run.admin", "members": ["allAuthenticatedUsers"]},
            ]
        }
        findings = analyze_security(config, iam_policy)
        categories = [f.category for f in findings]
        assert "public_iam" in categories
        assert "broad_iam" in categories

    def test_empty_iam_bindings(self):
        config = ServiceConfig(
            service_account="sa@proj.iam.gserviceaccount.com",
            network=NetworkConfig(ingress="internal", vpc_connector="conn"),
        )
        findings = analyze_security(config, {"bindings": []})
        categories = [f.category for f in findings]
        assert "public_iam" not in categories

    def test_returns_tuple(self, default_config):
        result = analyze_security(default_config)
        assert isinstance(result, tuple)


# =============================================================================
# Traffic Analyzer
# =============================================================================


class TestAnalyzeTraffic:
    def test_traffic_split(self):
        config = ServiceConfig(
            revisions=(
                ServiceRevision(name="rev-1", traffic_percent=80),
                ServiceRevision(name="rev-2", traffic_percent=20),
            ),
        )
        findings = analyze_traffic(config)
        categories = [f.category for f in findings]
        assert "traffic_split" in categories

    def test_no_traffic_split_single_revision(self):
        config = ServiceConfig(
            revisions=(ServiceRevision(name="rev-1", traffic_percent=100),),
        )
        findings = analyze_traffic(config)
        categories = [f.category for f in findings]
        assert "traffic_split" not in categories

    def test_no_traffic_split_zero_percent_revision(self):
        config = ServiceConfig(
            revisions=(
                ServiceRevision(name="rev-1", traffic_percent=100),
                ServiceRevision(name="rev-2", traffic_percent=0),
            ),
        )
        findings = analyze_traffic(config)
        categories = [f.category for f in findings]
        assert "traffic_split" not in categories

    def test_no_metrics_finding(self):
        config = ServiceConfig()
        findings = analyze_traffic(config, None)
        categories = [f.category for f in findings]
        assert "no_metrics" in categories

    def test_zero_traffic(self):
        config = ServiceConfig()
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=0),),
        )
        findings = analyze_traffic(config, metrics)
        categories = [f.category for f in findings]
        assert "no_traffic" in categories

    def test_low_traffic(self):
        config = ServiceConfig()
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=50),),
        )
        findings = analyze_traffic(config, metrics)
        categories = [f.category for f in findings]
        assert "low_traffic" in categories

    def test_normal_traffic_no_finding(self):
        config = ServiceConfig()
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=5000),),
        )
        findings = analyze_traffic(config, metrics)
        categories = [f.category for f in findings]
        assert "no_traffic" not in categories
        assert "low_traffic" not in categories

    def test_traffic_spikes(self):
        config = ServiceConfig()
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=1000),),
            instance_count=(
                MetricPoint(timestamp="t1", value=1),
                MetricPoint(timestamp="t2", value=1),
                MetricPoint(timestamp="t3", value=1),
                MetricPoint(timestamp="t4", value=1),
                MetricPoint(timestamp="t5", value=100),
            ),
        )
        # avg ~20.8, max=100, ratio=100/20.8 ~4.8 -> needs >5
        # Actually: avg=(1+1+1+1+100)/5=20.8, max/avg=100/20.8=4.8 < 5
        # Use more extreme values
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=1000),),
            instance_count=(
                MetricPoint(timestamp="t1", value=1),
                MetricPoint(timestamp="t2", value=1),
                MetricPoint(timestamp="t3", value=1),
                MetricPoint(timestamp="t4", value=1),
                MetricPoint(timestamp="t5", value=1),
                MetricPoint(timestamp="t6", value=60),
            ),
        )
        # avg=(1*5+60)/6=10.83, max=60, ratio=60/10.83=5.54 > 5
        findings = analyze_traffic(config, metrics)
        categories = [f.category for f in findings]
        assert "traffic_spikes" in categories

    def test_scale_to_zero(self):
        config = ServiceConfig()
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=1000),),
            instance_count=(
                MetricPoint(timestamp="t1", value=0),
                MetricPoint(timestamp="t2", value=2),
            ),
        )
        findings = analyze_traffic(config, metrics)
        categories = [f.category for f in findings]
        assert "scale_to_zero" in categories

    def test_no_scale_to_zero_always_running(self):
        config = ServiceConfig()
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=1000),),
            instance_count=(
                MetricPoint(timestamp="t1", value=2),
                MetricPoint(timestamp="t2", value=3),
            ),
        )
        findings = analyze_traffic(config, metrics)
        categories = [f.category for f in findings]
        assert "scale_to_zero" not in categories

    def test_latency_tail(self):
        config = ServiceConfig()
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=1000),),
            request_latency_p50=(MetricPoint(timestamp="t1", value=0.01),),
            request_latency_p99=(MetricPoint(timestamp="t1", value=0.5),),  # 50x p50
        )
        findings = analyze_traffic(config, metrics)
        categories = [f.category for f in findings]
        assert "latency_tail" in categories

    def test_no_latency_tail_tight_spread(self):
        config = ServiceConfig()
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=1000),),
            request_latency_p50=(MetricPoint(timestamp="t1", value=0.1),),
            request_latency_p99=(
                MetricPoint(timestamp="t1", value=0.3),  # 3x, < 10x threshold
            ),
        )
        findings = analyze_traffic(config, metrics)
        categories = [f.category for f in findings]
        assert "latency_tail" not in categories

    def test_high_billable_time(self):
        config = ServiceConfig()
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=100),),
            billable_instance_time=(MetricPoint(timestamp="t1", value=1000),),
        )
        findings = analyze_traffic(config, metrics)
        categories = [f.category for f in findings]
        assert "high_billable_time" in categories

    def test_normal_billable_time(self):
        config = ServiceConfig()
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=1000),),
            billable_instance_time=(MetricPoint(timestamp="t1", value=1000),),
        )
        findings = analyze_traffic(config, metrics)
        categories = [f.category for f in findings]
        assert "high_billable_time" not in categories

    def test_empty_request_count_no_billable_finding(self):
        config = ServiceConfig()
        metrics = ServiceMetrics(
            request_count=(),
            billable_instance_time=(MetricPoint(timestamp="t1", value=1000),),
        )
        findings = analyze_traffic(config, metrics)
        categories = [f.category for f in findings]
        assert "high_billable_time" not in categories

    def test_returns_tuple(self, default_config):
        result = analyze_traffic(default_config)
        assert isinstance(result, tuple)

    def test_zero_requests_billable_no_error(self):
        """Zero total requests should not cause division by zero."""
        config = ServiceConfig()
        metrics = ServiceMetrics(
            request_count=(MetricPoint(timestamp="t1", value=0),),
            billable_instance_time=(MetricPoint(timestamp="t1", value=500),),
        )
        findings = analyze_traffic(config, metrics)
        categories = [f.category for f in findings]
        assert "high_billable_time" not in categories
