"""Tests for gcloud JSON parser."""

from cloudrun_agent.tools.parser import (
    _parse_network_interfaces,
    _safe_int,
    parse_revision,
    parse_service,
)


class TestSafeInt:
    def test_valid_int(self):
        assert _safe_int(42) == 42

    def test_string_int(self):
        assert _safe_int("10") == 10

    def test_none_returns_default(self):
        assert _safe_int(None) == 0

    def test_none_returns_custom_default(self):
        assert _safe_int(None, 5) == 5

    def test_empty_string(self):
        assert _safe_int("") == 0

    def test_non_numeric_string(self):
        assert _safe_int("abc") == 0

    def test_float_string(self):
        assert _safe_int("3.14") == 0

    def test_zero(self):
        assert _safe_int(0) == 0

    def test_negative(self):
        assert _safe_int(-3) == -3


class TestParseNetworkInterfaces:
    def test_valid_json(self):
        raw = '[{"network":"my-vpc","subnetwork":"my-subnet"}]'
        network, subnet = _parse_network_interfaces(raw)
        assert network == "my-vpc"
        assert subnet == "my-subnet"

    def test_empty_string(self):
        assert _parse_network_interfaces("") == ("", "")

    def test_invalid_json(self):
        assert _parse_network_interfaces("not json") == ("", "")

    def test_empty_list(self):
        assert _parse_network_interfaces("[]") == ("", "")

    def test_none(self):
        assert _parse_network_interfaces(None) == ("", "")

    def test_missing_keys(self):
        raw = '[{"other": "value"}]'
        network, subnet = _parse_network_interfaces(raw)
        assert network == ""
        assert subnet == ""

    def test_multiple_interfaces_uses_first(self):
        raw = '[{"network":"vpc1","subnetwork":"sub1"},{"network":"vpc2","subnetwork":"sub2"}]'
        network, subnet = _parse_network_interfaces(raw)
        assert network == "vpc1"
        assert subnet == "sub1"


class TestParseService:
    def test_full_service(self, realistic_gcloud_service_json):
        config = parse_service(realistic_gcloud_service_json)

        assert config.name == "my-api"
        assert config.region == "us-central1"
        assert config.project == "my-project-123"
        assert config.url == "https://my-api-abc123-uc.a.run.app"
        assert (
            config.service_account == "my-api-sa@my-project-123.iam.gserviceaccount.com"
        )

        # Resources
        assert config.resources.cpu == "2"
        assert config.resources.memory == "1Gi"

        # Scaling
        assert config.scaling.min_instances == 2
        assert config.scaling.max_instances == 50
        assert config.scaling.concurrency == 100

        # Network
        assert config.network.ingress == "internal-and-cloud-load-balancing"
        assert config.network.egress == "all-traffic"
        assert config.network.vpc_network == "my-vpc"
        assert config.network.vpc_subnet == "my-subnet"
        assert (
            config.network.vpc_connector
            == "projects/my-project-123/locations/us-central1/connectors/my-vpc-conn"
        )
        assert config.network.default_url_disabled is True
        assert config.network.invoker_iam_disabled is False

        # Revisions
        assert len(config.revisions) == 2
        assert config.revisions[0].name == "my-api-00007-abc"
        assert config.revisions[0].traffic_percent == 90
        assert config.revisions[1].name == "my-api-00006-xyz"
        assert config.revisions[1].traffic_percent == 10

        # Env vars
        assert config.env_vars["PORT"] == "8080"
        assert config.env_vars["LOG_LEVEL"] == "info"
        assert config.env_vars["DB_PASSWORD"] == "<from-secret>"

        # Metadata
        assert config.startup_cpu_boost is True
        assert config.threat_detection is True
        assert config.created_by == "deployer@my-project.iam.gserviceaccount.com"
        assert config.last_modified_by == "admin@example.com"
        assert config.generation == 7
        assert config.latest_revision == "my-api-00007-abc"
        assert config.labels["env"] == "production"

        # Raw preserved
        assert config.raw is realistic_gcloud_service_json

    def test_empty_data(self):
        config = parse_service({})
        assert config.name == ""
        assert config.region == ""
        assert config.project == ""
        assert config.url == ""
        assert config.resources.cpu == ""
        assert config.resources.memory == ""
        assert config.scaling.min_instances == 0
        assert config.scaling.max_instances == 100
        assert config.scaling.concurrency == 80
        assert config.revisions == ()
        assert config.env_vars == {}

    def test_url_fallback_to_address(self):
        """When status.url is missing, fall back to status.address.url."""
        data = {
            "status": {
                "address": {"url": "https://fallback.example.com"},
            },
        }
        config = parse_service(data)
        assert config.url == "https://fallback.example.com"

    def test_no_containers(self):
        """Handle missing containers gracefully."""
        data = {
            "spec": {"template": {"spec": {}}},
        }
        config = parse_service(data)
        assert config.resources.cpu == ""
        assert config.resources.memory == ""

    def test_empty_containers_list(self):
        data = {
            "spec": {"template": {"spec": {"containers": []}}},
        }
        # Falls back to [{}][0] = {}
        config = parse_service(data)
        assert config.resources.cpu == ""

    def test_no_traffic(self):
        data = {"spec": {}}
        config = parse_service(data)
        assert config.revisions == ()

    def test_annotations_missing(self):
        """Missing annotations should use defaults."""
        data = {
            "metadata": {"name": "svc"},
            "spec": {"template": {"metadata": {}, "spec": {}}},
        }
        config = parse_service(data)
        assert config.network.ingress == "all"
        assert config.network.default_url_disabled is False
        assert config.startup_cpu_boost is False

    def test_default_url_disabled_false_string(self):
        data = {
            "metadata": {
                "annotations": {"run.googleapis.com/default-url-disabled": "false"}
            }
        }
        config = parse_service(data)
        assert config.network.default_url_disabled is False


class TestParseRevision:
    def test_full_revision(self, realistic_gcloud_revision_json):
        rev = parse_revision(realistic_gcloud_revision_json)

        assert rev.name == "my-api-00007-abc"
        assert rev.traffic_percent == 0  # Always 0 from revision parse
        assert rev.active is True
        assert rev.create_time == "2025-01-15T10:30:00Z"

    def test_inactive_revision(self):
        data = {
            "metadata": {
                "name": "rev-old",
                "creationTimestamp": "2025-01-01T00:00:00Z",
            },
            "status": {
                "conditions": [
                    {"type": "Ready", "status": "False"},
                    {"type": "Active", "status": "False"},
                ],
            },
        }
        rev = parse_revision(data)
        assert rev.name == "rev-old"
        assert rev.active is False

    def test_empty_data(self):
        rev = parse_revision({})
        assert rev.name == ""
        assert rev.active is False
        assert rev.create_time == ""

    def test_no_conditions(self):
        data = {
            "metadata": {"name": "rev-1"},
            "status": {},
        }
        rev = parse_revision(data)
        assert rev.active is False

    def test_mixed_conditions(self):
        """Ready=True among other conditions."""
        data = {
            "metadata": {"name": "rev-1"},
            "status": {
                "conditions": [
                    {"type": "ContainerHealthy", "status": "True"},
                    {"type": "Ready", "status": "True"},
                ],
            },
        }
        rev = parse_revision(data)
        assert rev.active is True

    def test_ready_false_explicitly(self):
        data = {
            "metadata": {"name": "rev-1"},
            "status": {
                "conditions": [
                    {"type": "Ready", "status": "False"},
                ],
            },
        }
        rev = parse_revision(data)
        assert rev.active is False
