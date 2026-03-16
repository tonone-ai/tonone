"""Data models for Cloud Run service information."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResourceLimits:
    cpu: str = ""
    memory: str = ""


@dataclass(frozen=True)
class ScalingConfig:
    min_instances: int = 0
    max_instances: int = 100
    concurrency: int = 80


@dataclass(frozen=True)
class NetworkConfig:
    ingress: str = "all"
    egress: str = ""
    vpc_network: str = ""
    vpc_subnet: str = ""
    vpc_connector: str = ""
    default_url_disabled: bool = False
    invoker_iam_disabled: bool = False


@dataclass(frozen=True)
class ServiceRevision:
    name: str = ""
    traffic_percent: int = 0
    active: bool = True
    create_time: str = ""


@dataclass(frozen=True)
class ServiceConfig:
    name: str = ""
    region: str = ""
    project: str = ""
    url: str = ""
    service_account: str = ""
    network: NetworkConfig = field(default_factory=NetworkConfig)
    resources: ResourceLimits = field(default_factory=ResourceLimits)
    scaling: ScalingConfig = field(default_factory=ScalingConfig)
    revisions: tuple[ServiceRevision, ...] = ()
    labels: dict[str, str] = field(default_factory=dict)
    env_vars: dict[str, str] = field(default_factory=dict)
    startup_cpu_boost: bool = False
    threat_detection: bool = False
    created_by: str = ""
    last_modified_by: str = ""
    generation: int = 0
    latest_revision: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def ingress(self) -> str:
        return self.network.ingress

    @property
    def vpc_connector(self) -> str:
        return self.network.vpc_connector


@dataclass(frozen=True)
class MetricPoint:
    timestamp: str = ""
    value: float = 0.0


@dataclass(frozen=True)
class ServiceMetrics:
    service_name: str = ""
    region: str = ""
    cpu_utilization: tuple[MetricPoint, ...] = ()
    memory_utilization: tuple[MetricPoint, ...] = ()
    request_count: tuple[MetricPoint, ...] = ()
    request_latency_p50: tuple[MetricPoint, ...] = ()
    request_latency_p95: tuple[MetricPoint, ...] = ()
    request_latency_p99: tuple[MetricPoint, ...] = ()
    instance_count: tuple[MetricPoint, ...] = ()
    billable_instance_time: tuple[MetricPoint, ...] = ()
    error_count: tuple[MetricPoint, ...] = ()
