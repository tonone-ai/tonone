"""Parse gcloud JSON output into typed data models."""

from typing import Any
import json

from cloudrun_agent.models.service import (
    NetworkConfig,
    ResourceLimits,
    ScalingConfig,
    ServiceConfig,
    ServiceRevision,
)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_network_interfaces(raw: str) -> tuple[str, str]:
    """Parse VPC network interface JSON annotation."""
    try:
        interfaces = json.loads(raw)
        if interfaces and isinstance(interfaces, list):
            return interfaces[0].get("network", ""), interfaces[0].get("subnetwork", "")
    except (json.JSONDecodeError, TypeError, IndexError):
        pass
    return "", ""


def parse_service(data: dict[str, Any]) -> ServiceConfig:
    """Parse a gcloud service description into a ServiceConfig."""
    metadata = data.get("metadata", {})
    meta_annotations = metadata.get("annotations", {})
    spec = data.get("spec", {})
    template = spec.get("template", {})
    template_spec = template.get("spec", {})
    container = (template_spec.get("containers") or [{}])[0]
    container_resources = container.get("resources", {}).get("limits", {})
    annotations = template.get("metadata", {}).get("annotations", {})
    status = data.get("status", {})

    resources = ResourceLimits(
        cpu=container_resources.get("cpu", ""),
        memory=container_resources.get("memory", ""),
    )

    scaling = ScalingConfig(
        min_instances=_safe_int(
            annotations.get("autoscaling.knative.dev/minScale", 0)
        ),
        max_instances=_safe_int(
            annotations.get("autoscaling.knative.dev/maxScale", 100)
        ),
        concurrency=_safe_int(template_spec.get("containerConcurrency", 80)),
    )

    # Network configuration
    vpc_network, vpc_subnet = _parse_network_interfaces(
        annotations.get("run.googleapis.com/network-interfaces", "")
    )
    network = NetworkConfig(
        ingress=meta_annotations.get("run.googleapis.com/ingress", "all"),
        egress=annotations.get("run.googleapis.com/vpc-access-egress", ""),
        vpc_network=vpc_network,
        vpc_subnet=vpc_subnet,
        vpc_connector=annotations.get("run.googleapis.com/vpc-access-connector", ""),
        default_url_disabled=meta_annotations.get("run.googleapis.com/default-url-disabled", "false") == "true",
        invoker_iam_disabled=meta_annotations.get("run.googleapis.com/invoker-iam-disabled", "false") == "true",
    )

    env_list = container.get("env", [])
    env_vars = {e["name"]: e.get("value", "<from-secret>") for e in env_list}

    revisions = tuple(
        ServiceRevision(
            name=t.get("revisionName", ""),
            traffic_percent=_safe_int(t.get("percent", 0)),
            active=True,
        )
        for t in spec.get("traffic", [])
    )

    return ServiceConfig(
        name=metadata.get("name", ""),
        region=metadata.get("labels", {}).get("cloud.googleapis.com/location", ""),
        project=metadata.get("namespace", ""),
        url=(status.get("url") or status.get("address", {}).get("url", "")),
        service_account=template_spec.get("serviceAccountName", ""),
        network=network,
        resources=resources,
        scaling=scaling,
        revisions=revisions,
        labels=metadata.get("labels", {}),
        env_vars=env_vars,
        startup_cpu_boost=annotations.get("run.googleapis.com/startup-cpu-boost", "false") == "true",
        threat_detection=meta_annotations.get("run.googleapis.com/threat-detection", "false") == "true",
        created_by=meta_annotations.get("serving.knative.dev/creator", ""),
        last_modified_by=meta_annotations.get("serving.knative.dev/lastModifier", ""),
        generation=_safe_int(metadata.get("generation", 0)),
        latest_revision=status.get("latestReadyRevisionName", ""),
        raw=data,
    )


def parse_revision(data: dict[str, Any]) -> ServiceRevision:
    """Parse a gcloud revision into a ServiceRevision."""
    metadata = data.get("metadata", {})
    status = data.get("status", {})
    conditions = status.get("conditions", [])
    is_active = any(
        c.get("type") == "Ready" and c.get("status") == "True"
        for c in conditions
    )

    return ServiceRevision(
        name=metadata.get("name", ""),
        traffic_percent=0,
        active=is_active,
        create_time=metadata.get("creationTimestamp", ""),
    )
