"""Shared fixtures for cloudrun-agent tests."""

import pytest
from cloudrun_agent.models.service import (
    MetricPoint,
    NetworkConfig,
    ResourceLimits,
    ScalingConfig,
    ServiceConfig,
    ServiceMetrics,
    ServiceRevision,
)


@pytest.fixture
def default_config() -> ServiceConfig:
    """A minimal ServiceConfig with defaults."""
    return ServiceConfig()


@pytest.fixture
def basic_config() -> ServiceConfig:
    """A typical Cloud Run service config."""
    return ServiceConfig(
        name="my-api",
        region="us-central1",
        project="my-project",
        url="https://my-api-abc123-uc.a.run.app",
        service_account="my-api-sa@my-project.iam.gserviceaccount.com",
        network=NetworkConfig(
            ingress="internal-and-cloud-load-balancing",
            egress="all-traffic",
            vpc_network="default",
            vpc_subnet="default",
            vpc_connector="projects/my-project/locations/us-central1/connectors/my-conn",
        ),
        resources=ResourceLimits(cpu="1000m", memory="512Mi"),
        scaling=ScalingConfig(min_instances=1, max_instances=50, concurrency=80),
        revisions=(
            ServiceRevision(name="my-api-00001-abc", traffic_percent=100, active=True),
        ),
        labels={"env": "production"},
        env_vars={"PORT": "8080", "LOG_LEVEL": "info"},
        startup_cpu_boost=True,
        threat_detection=True,
        created_by="user@example.com",
        last_modified_by="user@example.com",
        generation=5,
        latest_revision="my-api-00001-abc",
    )


@pytest.fixture
def insecure_config() -> ServiceConfig:
    """A service with security issues."""
    return ServiceConfig(
        name="insecure-svc",
        region="us-central1",
        project="my-project",
        service_account="123456-compute@developer.gserviceaccount.com",
        network=NetworkConfig(ingress="all"),
        resources=ResourceLimits(cpu="1", memory="256Mi"),
        scaling=ScalingConfig(min_instances=0, max_instances=100, concurrency=80),
        env_vars={
            "DATABASE_URL": "postgres://...",
            "API_KEY": "sk-secret-value",
            "SECRET_TOKEN": "<from-secret>",
        },
    )


@pytest.fixture
def overprovisioned_config() -> ServiceConfig:
    """A service with excessive resource allocation."""
    return ServiceConfig(
        name="fat-svc",
        region="us-east1",
        project="my-project",
        resources=ResourceLimits(cpu="4", memory="4Gi"),
        scaling=ScalingConfig(min_instances=3, max_instances=100, concurrency=80),
    )


@pytest.fixture
def basic_metrics() -> ServiceMetrics:
    """Metrics representing a healthy service."""
    return ServiceMetrics(
        service_name="my-api",
        region="us-central1",
        cpu_utilization=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=0.45),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=0.50),
            MetricPoint(timestamp="2025-01-01T02:00:00Z", value=0.55),
        ),
        memory_utilization=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=0.60),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=0.65),
            MetricPoint(timestamp="2025-01-01T02:00:00Z", value=0.70),
        ),
        request_count=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=5000),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=6000),
            MetricPoint(timestamp="2025-01-01T02:00:00Z", value=4000),
        ),
        request_latency_p50=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=0.05),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=0.06),
        ),
        request_latency_p95=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=0.2),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=0.25),
        ),
        request_latency_p99=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=0.4),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=0.45),
        ),
        instance_count=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=3),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=5),
            MetricPoint(timestamp="2025-01-01T02:00:00Z", value=2),
        ),
        billable_instance_time=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=100),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=120),
        ),
        error_count=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=5),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=3),
        ),
    )


@pytest.fixture
def underutilized_metrics() -> ServiceMetrics:
    """Metrics showing very low utilization."""
    return ServiceMetrics(
        service_name="fat-svc",
        region="us-east1",
        cpu_utilization=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=0.02),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=0.05),
            MetricPoint(timestamp="2025-01-01T02:00:00Z", value=0.03),
        ),
        memory_utilization=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=0.10),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=0.15),
            MetricPoint(timestamp="2025-01-01T02:00:00Z", value=0.12),
        ),
        request_count=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=10),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=5),
        ),
        instance_count=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=3),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=3),
        ),
    )


@pytest.fixture
def empty_metrics() -> ServiceMetrics:
    """Metrics with no data points."""
    return ServiceMetrics(service_name="empty-svc", region="us-central1")


@pytest.fixture
def high_latency_metrics() -> ServiceMetrics:
    """Metrics showing high latency and error rates."""
    return ServiceMetrics(
        service_name="slow-svc",
        region="us-central1",
        request_count=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=1000),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=1000),
        ),
        request_latency_p50=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=0.1),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=0.12),
        ),
        request_latency_p99=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=3.0),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=3.5),
        ),
        error_count=(
            MetricPoint(timestamp="2025-01-01T00:00:00Z", value=80),
            MetricPoint(timestamp="2025-01-01T01:00:00Z", value=70),
        ),
    )


@pytest.fixture
def realistic_gcloud_service_json() -> dict:
    """Realistic gcloud run services describe --format=json output."""
    return {
        "apiVersion": "serving.knative.dev/v1",
        "kind": "Service",
        "metadata": {
            "name": "my-api",
            "namespace": "my-project-123",
            "generation": 7,
            "labels": {
                "cloud.googleapis.com/location": "us-central1",
                "env": "production",
            },
            "annotations": {
                "run.googleapis.com/ingress": "internal-and-cloud-load-balancing",
                "run.googleapis.com/default-url-disabled": "true",
                "run.googleapis.com/invoker-iam-disabled": "false",
                "run.googleapis.com/threat-detection": "true",
                "serving.knative.dev/creator": "deployer@my-project.iam.gserviceaccount.com",
                "serving.knative.dev/lastModifier": "admin@example.com",
            },
        },
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "autoscaling.knative.dev/minScale": "2",
                        "autoscaling.knative.dev/maxScale": "50",
                        "run.googleapis.com/startup-cpu-boost": "true",
                        "run.googleapis.com/vpc-access-connector": "projects/my-project-123/locations/us-central1/connectors/my-vpc-conn",
                        "run.googleapis.com/vpc-access-egress": "all-traffic",
                        "run.googleapis.com/network-interfaces": '[{"network":"my-vpc","subnetwork":"my-subnet"}]',
                    },
                },
                "spec": {
                    "containerConcurrency": 100,
                    "serviceAccountName": "my-api-sa@my-project-123.iam.gserviceaccount.com",
                    "containers": [
                        {
                            "image": "us-docker.pkg.dev/my-project-123/repo/my-api:v1.2.3",
                            "resources": {
                                "limits": {
                                    "cpu": "2",
                                    "memory": "1Gi",
                                },
                            },
                            "env": [
                                {"name": "PORT", "value": "8080"},
                                {"name": "LOG_LEVEL", "value": "info"},
                                {"name": "DB_PASSWORD"},
                            ],
                            "ports": [{"containerPort": 8080}],
                        }
                    ],
                },
            },
            "traffic": [
                {"revisionName": "my-api-00007-abc", "percent": 90},
                {"revisionName": "my-api-00006-xyz", "percent": 10},
            ],
        },
        "status": {
            "url": "https://my-api-abc123-uc.a.run.app",
            "latestReadyRevisionName": "my-api-00007-abc",
            "conditions": [
                {"type": "Ready", "status": "True"},
            ],
        },
    }


@pytest.fixture
def realistic_gcloud_revision_json() -> dict:
    """Realistic gcloud run revisions describe --format=json output."""
    return {
        "apiVersion": "serving.knative.dev/v1",
        "kind": "Revision",
        "metadata": {
            "name": "my-api-00007-abc",
            "namespace": "my-project-123",
            "creationTimestamp": "2025-01-15T10:30:00Z",
            "labels": {
                "serving.knative.dev/service": "my-api",
            },
        },
        "spec": {
            "containerConcurrency": 100,
            "containers": [
                {
                    "image": "us-docker.pkg.dev/my-project-123/repo/my-api:v1.2.3",
                    "resources": {"limits": {"cpu": "2", "memory": "1Gi"}},
                }
            ],
        },
        "status": {
            "conditions": [
                {"type": "Ready", "status": "True"},
                {"type": "Active", "status": "True"},
                {"type": "ContainerHealthy", "status": "True"},
            ],
        },
    }
