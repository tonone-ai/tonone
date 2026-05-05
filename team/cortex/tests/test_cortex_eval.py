"""Tests for cortex-eval: llm_usage_scanner + prompt_evaluator + eval_scan CLI."""

from __future__ import annotations

import json
import os
import sys
import textwrap

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)

from team.shared.report_schema import AgentReport, Finding, ReportMetadata
from team.cortex.scripts.cortex_agent.llm_usage_scanner import scan_llm_usage
from team.cortex.scripts.cortex_agent.prompt_evaluator import evaluate_prompts

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


# ---------------------------------------------------------------------------
# Report schema — severity mapping
# ---------------------------------------------------------------------------

class TestSeverityMapping:
    def test_high_severity_valid(self):
        f = Finding(
            id="CORTEX-003",
            severity="HIGH",
            title="LLM call without error handling",
            detail="No try/except",
            location="app.py:10",
            recommendation="Wrap in try/except",
            effort="S",
        )
        assert f.severity == "HIGH"

    def test_medium_severity_valid(self):
        f = Finding(
            id="CORTEX-001",
            severity="MEDIUM",
            title="Missing max_tokens",
            detail="Unbounded",
            location="app.py:5",
            recommendation="Add max_tokens",
            effort="S",
        )
        assert f.severity == "MEDIUM"

    def test_low_severity_valid(self):
        f = Finding(
            id="CORTEX-005",
            severity="LOW",
            title="Hardcoded model",
            detail="Model string in code",
            location="app.py:1",
            recommendation="Use env var",
            effort="S",
        )
        assert f.severity == "LOW"

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError):
            Finding(severity="BLOCKER", title="x", detail="x", location="x", recommendation="x", effort="S")

    def test_invalid_effort_raises(self):
        with pytest.raises(ValueError):
            Finding(severity="HIGH", title="x", detail="x", location="x", recommendation="x", effort="XL")

    def test_report_summary_counts(self):
        report = AgentReport(agent="cortex", skill="cortex-eval", target=".")
        report.findings = [
            Finding(severity="HIGH", title="a", detail="d", location="l", recommendation="r", effort="S"),
            Finding(severity="HIGH", title="b", detail="d", location="l", recommendation="r", effort="S"),
            Finding(severity="MEDIUM", title="c", detail="d", location="l", recommendation="r", effort="M"),
            Finding(severity="LOW", title="e", detail="d", location="l", recommendation="r", effort="L"),
        ]
        s = report.summary
        assert s.high == 2
        assert s.medium == 1
        assert s.low == 1
        assert s.total == 4

    def test_report_json_roundtrip(self):
        report = AgentReport(
            agent="cortex",
            skill="cortex-eval",
            target="/some/path",
            metadata=ReportMetadata(tool_version="cortex-eval 0.9.8", duration_s=1.5),
        )
        report.findings = [
            Finding(id="CORTEX-001", severity="MEDIUM", title="t", detail="d", location="f.py:1", recommendation="r", effort="S"),
        ]
        restored = AgentReport.from_dict(json.loads(report.to_json()))
        assert restored.agent == "cortex"
        assert len(restored.findings) == 1
        assert restored.findings[0].id == "CORTEX-001"


# ---------------------------------------------------------------------------
# LLM usage scanner — error paths
# ---------------------------------------------------------------------------

class TestLLMUsageScannerErrorPaths:
    def test_os_walk_failure_returns_empty(self, monkeypatch):
        """When os.walk raises OSError, scanner returns []."""
        import os as _os
        def mock_walk(path):
            raise OSError("permission denied")
        monkeypatch.setattr(_os, "walk", mock_walk)
        findings = scan_llm_usage("/fake/path")
        assert findings == []

    def test_empty_directory_returns_empty(self, tmp_path):
        """An empty directory produces no findings."""
        findings = scan_llm_usage(str(tmp_path))
        assert findings == []

    def test_non_llm_python_file_returns_empty(self, tmp_path):
        """A Python file with no LLM imports produces no usage findings."""
        f = tmp_path / "pure.py"
        f.write_text("def add(a, b):\n    return a + b\n")
        findings = scan_llm_usage(str(tmp_path))
        assert findings == []

    def test_syntax_error_file_skipped(self, tmp_path):
        """A Python file with syntax errors is skipped without crashing."""
        bad = tmp_path / "broken.py"
        bad.write_text("import anthropic\ndef bad(:\n    pass\n")
        # Should not raise
        findings = scan_llm_usage(str(tmp_path))
        assert isinstance(findings, list)

    def test_unreadable_file_skipped(self, tmp_path, monkeypatch):
        """A file that cannot be read is skipped gracefully."""
        f = tmp_path / "secret.py"
        f.write_text("import anthropic\n")
        original_open = open
        def mock_open(path, *args, **kwargs):
            if str(path) == str(f):
                raise OSError("permission denied")
            return original_open(path, *args, **kwargs)
        monkeypatch.setattr("builtins.open", mock_open)
        findings = scan_llm_usage(str(tmp_path))
        assert isinstance(findings, list)


class TestLLMUsageScannerFindings:
    def test_fixture_finds_missing_error_handling(self):
        """llm_usage_sample.py contains a call without try/except."""
        findings = scan_llm_usage(FIXTURE_DIR)
        high_ids = [f.id for f in findings if f.severity == "HIGH"]
        assert "CORTEX-003" in high_ids, (
            "Expected CORTEX-003 (missing error handling) in fixture findings. "
            f"Got findings: {[(f.id, f.severity, f.title) for f in findings]}"
        )

    def test_fixture_finds_hardcoded_model(self):
        """llm_usage_sample.py has hardcoded model names."""
        findings = scan_llm_usage(FIXTURE_DIR)
        model_findings = [f for f in findings if f.id == "CORTEX-005"]
        assert len(model_findings) >= 1, (
            "Expected CORTEX-005 (hardcoded model) in fixture findings. "
            f"Got findings: {[(f.id, f.severity) for f in findings]}"
        )

    def test_findings_have_required_fields(self):
        """All findings from the fixture must have required fields."""
        findings = scan_llm_usage(FIXTURE_DIR)
        for f in findings:
            assert f.severity in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
            assert f.title
            assert f.location
            assert f.recommendation

    def test_inline_code_missing_max_tokens(self, tmp_path):
        """Inline code with an LLM call and no max_tokens gets CORTEX-001."""
        code = textwrap.dedent("""\
            import anthropic
            client = anthropic.Anthropic()
            def run():
                try:
                    resp = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        messages=[{"role": "user", "content": "hi"}],
                    )
                except Exception:
                    pass
        """)
        (tmp_path / "code.py").write_text(code)
        findings = scan_llm_usage(str(tmp_path))
        assert any(f.id == "CORTEX-001" for f in findings)

    def test_inline_code_with_max_tokens_no_001(self, tmp_path):
        """If max_tokens is present, CORTEX-001 should not be raised."""
        code = textwrap.dedent("""\
            import anthropic
            client = anthropic.Anthropic()
            def run():
                try:
                    resp = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=1024,
                        timeout=30,
                        messages=[{"role": "user", "content": "hi"}],
                    )
                except Exception:
                    pass
        """)
        (tmp_path / "code.py").write_text(code)
        findings = scan_llm_usage(str(tmp_path))
        assert not any(f.id == "CORTEX-001" for f in findings)


# ---------------------------------------------------------------------------
# Prompt evaluator
# ---------------------------------------------------------------------------

class TestPromptEvaluator:
    def test_fixture_bad_prompt_triggers_high_length(self):
        """bad_prompt.txt is >8000 tokens and must trigger CORTEX-101 HIGH."""
        findings = evaluate_prompts(FIXTURE_DIR)
        high_length = [f for f in findings if f.id == "CORTEX-101" and f.severity == "HIGH"]
        assert len(high_length) >= 1, (
            "Expected CORTEX-101 HIGH (length) from bad_prompt.txt. "
            f"Got: {[(f.id, f.severity, f.title) for f in findings]}"
        )

    def test_fixture_bad_prompt_triggers_injection(self):
        """bad_prompt.txt uses {user_input} and must trigger CORTEX-102."""
        findings = evaluate_prompts(FIXTURE_DIR)
        injection = [f for f in findings if f.id == "CORTEX-102"]
        assert len(injection) >= 1, (
            "Expected CORTEX-102 (injection risk) from bad_prompt.txt. "
            f"Got: {[(f.id, f.severity, f.title) for f in findings]}"
        )

    def test_short_clean_prompt_no_findings(self, tmp_path):
        """A short prompt with no issues should produce no HIGH/CRITICAL findings."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "short.txt").write_text(
            "You are a helpful assistant. Respond with valid JSON matching: {\"answer\": \"...\"}"
        )
        findings = evaluate_prompts(str(tmp_path))
        bad = [f for f in findings if f.severity in ("HIGH", "CRITICAL")]
        assert bad == []

    def test_injection_detected_in_format_string(self, tmp_path):
        """A prompt file using {user_message} triggers CORTEX-102."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "risky.txt").write_text(
            "Answer this: {user_message}\nPlease respond in JSON format."
        )
        findings = evaluate_prompts(str(tmp_path))
        assert any(f.id == "CORTEX-102" for f in findings)

    def test_empty_file_produces_no_findings(self, tmp_path):
        """An empty prompt file should produce no findings."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "empty.txt").write_text("")
        findings = evaluate_prompts(str(tmp_path))
        assert findings == []

    def test_missing_output_format_detected(self, tmp_path):
        """A longer prompt with no format instructions triggers CORTEX-103."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        # Write a prompt of >50 tokens with no format instructions
        text = (
            "You are a helpful AI assistant. "
            "The user will ask you questions and you should answer them accurately and helpfully. "
            "Always be polite and professional in your responses to all users at all times. "
            "Here is the user question to answer:"
        )
        (prompts_dir / "no_format.txt").write_text(text)
        findings = evaluate_prompts(str(tmp_path))
        assert any(f.id == "CORTEX-103" for f in findings)

    def test_os_error_returns_empty(self, monkeypatch):
        """When os.walk raises OSError, evaluator returns []."""
        import os as _os
        def mock_walk(path):
            raise OSError("permission denied")
        monkeypatch.setattr(_os, "walk", mock_walk)
        findings = evaluate_prompts("/fake/path")
        assert findings == []


# ---------------------------------------------------------------------------
# CLI: eval_scan.py
# ---------------------------------------------------------------------------

class TestEvalScanCLI:
    def test_nonexistent_target_exits_1(self):
        """eval_scan.py with a nonexistent path exits with code 1."""
        result = _run_eval_scan(["/nonexistent/path/that/does/not/exist"])
        assert result.returncode == 1
        assert "does not exist" in result.stderr

    def test_valid_target_exits_0_or_2(self, tmp_path):
        """eval_scan.py on a valid empty directory exits 0 (no findings)."""
        result = _run_eval_scan([str(tmp_path)])
        assert result.returncode in (0, 2)

    def test_writes_report_file(self, tmp_path):
        """eval_scan.py writes a JSON report file."""
        out = str(tmp_path / "report.json")
        result = _run_eval_scan([str(tmp_path), "--out", out])
        assert os.path.exists(out), f"Report not written. returncode={result.returncode}, stderr={result.stderr}"
        with open(out) as fh:
            data = json.load(fh)
        assert data["agent"] == "cortex"
        assert data["skill"] == "cortex-eval"

    def test_skip_usage_flag(self, tmp_path):
        """--skip-usage skips the LLM usage scan step."""
        out = str(tmp_path / "r.json")
        result = _run_eval_scan([str(tmp_path), "--skip-usage", "--out", out])
        assert result.returncode in (0, 2)
        assert os.path.exists(out)

    def test_skip_prompts_flag(self, tmp_path):
        """--skip-prompts skips the prompt evaluation step."""
        out = str(tmp_path / "r.json")
        result = _run_eval_scan([str(tmp_path), "--skip-prompts", "--out", out])
        assert result.returncode in (0, 2)
        assert os.path.exists(out)

    def test_high_findings_exit_2(self, tmp_path):
        """When HIGH findings exist, eval_scan exits with code 2."""
        code = textwrap.dedent("""\
            import anthropic
            client = anthropic.Anthropic()
            def run():
                resp = client.messages.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": "hi"}],
                )
        """)
        (tmp_path / "bad.py").write_text(code)
        out = str(tmp_path / "r.json")
        result = _run_eval_scan([str(tmp_path), "--skip-prompts", "--out", out])
        assert result.returncode == 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_eval_scan(args: list[str]):
    """Run eval_scan.py as a subprocess and return CompletedProcess."""
    import subprocess
    scan_py = os.path.join(ROOT, "team/cortex/scripts/cortex_agent/eval_scan.py")
    return subprocess.run(
        [sys.executable, scan_py] + args,
        capture_output=True,
        text=True,
    )
