"""Tests for frozen dataclass models."""

import pytest
from dataclasses import FrozenInstanceError

from cloudrun_agent.models.service import (
    MetricPoint,
    NetworkConfig,
    ResourceLimits,
    ScalingConfig,
    ServiceConfig,
    ServiceMetrics,
    ServiceRevision,
)


class TestResourceLimits:
    def test_defaults(self):
        rl = ResourceLimits()
        assert rl.cpu == ""
        assert rl.memory == ""

    def test_custom_values(self):
        rl = ResourceLimits(cpu="2", memory="1Gi")
        assert rl.cpu == "2"
        assert rl.memory == "1Gi"

    def test_frozen(self):
        rl = ResourceLimits(cpu="1", memory="512Mi")
        with pytest.raises(FrozenInstanceError):
            rl.cpu = "2"  # type: ignore[misc]


class TestScalingConfig:
    def test_defaults(self):
        sc = ScalingConfig()
        assert sc.min_instances == 0
        assert sc.max_instances == 100
        assert sc.concurrency == 80

    def test_custom_values(self):
        sc = ScalingConfig(min_instances=2, max_instances=50, concurrency=200)
        assert sc.min_instances == 2
        assert sc.max_instances == 50
        assert sc.concurrency == 200

    def test_frozen(self):
        sc = ScalingConfig()
        with pytest.raises(FrozenInstanceError):
            sc.min_instances = 5  # type: ignore[misc]


class TestNetworkConfig:
    def test_defaults(self):
        nc = NetworkConfig()
        assert nc.ingress == "all"
        assert nc.egress == ""
        assert nc.vpc_network == ""
        assert nc.vpc_subnet == ""
        assert nc.vpc_connector == ""
        assert nc.default_url_disabled is False
        assert nc.invoker_iam_disabled is False

    def test_custom_values(self):
        nc = NetworkConfig(
            ingress="internal",
            egress="all-traffic",
            vpc_network="my-vpc",
            vpc_subnet="my-subnet",
            vpc_connector="projects/p/locations/r/connectors/c",
            default_url_disabled=True,
            invoker_iam_disabled=True,
        )
        assert nc.ingress == "internal"
        assert nc.default_url_disabled is True

    def test_frozen(self):
        nc = NetworkConfig()
        with pytest.raises(FrozenInstanceError):
            nc.ingress = "internal"  # type: ignore[misc]


class TestServiceRevision:
    def test_defaults(self):
        sr = ServiceRevision()
        assert sr.name == ""
        assert sr.traffic_percent == 0
        assert sr.active is True
        assert sr.create_time == ""

    def test_custom_values(self):
        sr = ServiceRevision(
            name="my-svc-00001-abc",
            traffic_percent=100,
            active=True,
            create_time="2025-01-01T00:00:00Z",
        )
        assert sr.name == "my-svc-00001-abc"
        assert sr.traffic_percent == 100

    def test_frozen(self):
        sr = ServiceRevision()
        with pytest.raises(FrozenInstanceError):
            sr.active = False  # type: ignore[misc]


class TestServiceConfig:
    def test_defaults(self):
        sc = ServiceConfig()
        assert sc.name == ""
        assert sc.region == ""
        assert sc.project == ""
        assert sc.url == ""
        assert sc.service_account == ""
        assert isinstance(sc.network, NetworkConfig)
        assert isinstance(sc.resources, ResourceLimits)
        assert isinstance(sc.scaling, ScalingConfig)
        assert sc.revisions == ()
        assert sc.labels == {}
        assert sc.env_vars == {}
        assert sc.startup_cpu_boost is False
        assert sc.threat_detection is False
        assert sc.created_by == ""
        assert sc.last_modified_by == ""
        assert sc.generation == 0
        assert sc.latest_revision == ""
        assert sc.raw == {}

    def test_ingress_property(self):
        sc = ServiceConfig(network=NetworkConfig(ingress="internal"))
        assert sc.ingress == "internal"

    def test_vpc_connector_property(self):
        sc = ServiceConfig(
            network=NetworkConfig(vpc_connector="projects/p/locations/r/connectors/c")
        )
        assert sc.vpc_connector == "projects/p/locations/r/connectors/c"

    def test_ingress_property_default(self):
        sc = ServiceConfig()
        assert sc.ingress == "all"

    def test_vpc_connector_property_empty(self):
        sc = ServiceConfig()
        assert sc.vpc_connector == ""

    def test_frozen(self):
        sc = ServiceConfig(name="test")
        with pytest.raises(FrozenInstanceError):
            sc.name = "other"  # type: ignore[misc]

    def test_labels_default_factory_isolation(self):
        """Each instance gets its own labels dict."""
        sc1 = ServiceConfig()
        sc2 = ServiceConfig()
        assert sc1.labels is not sc2.labels

    def test_env_vars_default_factory_isolation(self):
        sc1 = ServiceConfig()
        sc2 = ServiceConfig()
        assert sc1.env_vars is not sc2.env_vars


class TestMetricPoint:
    def test_defaults(self):
        mp = MetricPoint()
        assert mp.timestamp == ""
        assert mp.value == 0.0

    def test_custom_values(self):
        mp = MetricPoint(timestamp="2025-01-01T00:00:00Z", value=42.5)
        assert mp.timestamp == "2025-01-01T00:00:00Z"
        assert mp.value == 42.5

    def test_frozen(self):
        mp = MetricPoint()
        with pytest.raises(FrozenInstanceError):
            mp.value = 1.0  # type: ignore[misc]


class TestServiceMetrics:
    def test_defaults(self):
        sm = ServiceMetrics()
        assert sm.service_name == ""
        assert sm.region == ""
        assert sm.cpu_utilization == ()
        assert sm.memory_utilization == ()
        assert sm.request_count == ()
        assert sm.request_latency_p50 == ()
        assert sm.request_latency_p95 == ()
        assert sm.request_latency_p99 == ()
        assert sm.instance_count == ()
        assert sm.billable_instance_time == ()
        assert sm.error_count == ()

    def test_with_points(self):
        points = (MetricPoint(timestamp="t1", value=1.0),)
        sm = ServiceMetrics(cpu_utilization=points)
        assert len(sm.cpu_utilization) == 1
        assert sm.cpu_utilization[0].value == 1.0

    def test_frozen(self):
        sm = ServiceMetrics()
        with pytest.raises(FrozenInstanceError):
            sm.service_name = "x"  # type: ignore[misc]
