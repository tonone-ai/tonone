"""Shared report schema for all tonone deep agents."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

SCHEMA_VERSION = "1.0"


@dataclass
class Finding:
    severity: str          # CRITICAL | HIGH | MEDIUM | LOW | INFO
    title: str
    detail: str
    location: str          # file:line, table.column, resource type, etc.
    recommendation: str
    effort: str            # S | M | L
    id: Optional[str] = None   # CVE-ID, rule ID, etc.

    def __post_init__(self):
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
        if self.severity not in valid:
            raise ValueError(f"severity must be one of {valid}")
        valid_effort = {"S", "M", "L"}
        if self.effort not in valid_effort:
            raise ValueError(f"effort must be one of {valid_effort}")


@dataclass
class Summary:
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0

    @property
    def total(self) -> int:
        return self.critical + self.high + self.medium + self.low + self.info


@dataclass
class ReportMetadata:
    tool_version: str
    duration_s: float
    schema_version: str = SCHEMA_VERSION


@dataclass
class AgentReport:
    agent: str
    skill: str
    target: str
    findings: list[Finding] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Optional[ReportMetadata] = None

    @property
    def summary(self) -> Summary:
        s = Summary()
        for f in self.findings:
            match f.severity:
                case "CRITICAL": s.critical += 1
                case "HIGH":     s.high += 1
                case "MEDIUM":   s.medium += 1
                case "LOW":      s.low += 1
                case "INFO":     s.info += 1
        return s

    def to_dict(self) -> dict:
        d = asdict(self)
        d["summary"] = asdict(self.summary)
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, d: dict) -> "AgentReport":
        findings = [Finding(**f) for f in d.get("findings", [])]
        metadata = ReportMetadata(**d["metadata"]) if d.get("metadata") else None
        return cls(
            agent=d["agent"],
            skill=d["skill"],
            target=d["target"],
            findings=findings,
            timestamp=d.get("timestamp", ""),
            metadata=metadata,
        )
