"""Tests for the Google Cloud integrations (BigQuery + Cloud Storage).

These tests never require real GCP credentials. They either:
- read source files to assert config-gating guards are present, or
- monkeypatch the optional GCP clients to capture calls.

Mirrors the patterns in tests/test_hardening.py.
"""

import json
import os
import sys
from types import SimpleNamespace

import pytest

# Ensure the backend package is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

GCP_CLIENTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app", "utils", "gcp_clients.py"
)
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "config.py")


# ---------------------------------------------------------------------------
# Test 1: gcp_clients.py guards on Config.ENABLE_BIGQUERY / ENABLE_GCS
# ---------------------------------------------------------------------------

class TestGcpGuards:
    def test_bigquery_logger_checks_enable_flag(self):
        with open(GCP_CLIENTS_PATH, "r", encoding="utf-8") as f:
            src = f.read()
        assert "Config.ENABLE_BIGQUERY" in src
        assert "Config.ENABLE_GCS" in src
        # The optional-dep import cascade must be present.
        assert "from google.cloud import bigquery" in src
        assert "from google.cloud import storage" in src
        assert "_GCP_AVAILABLE" in src

    def test_never_raise_contract_present(self):
        with open(GCP_CLIENTS_PATH, "r", encoding="utf-8") as f:
            src = f.read()
        # Every public method should be guarded by an enabled check.
        assert "if not self.enabled" in src
        # Failures must be logged, not raised.
        assert "logger.warning" in src

    def test_config_exposes_gcp_flags(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            src = f.read()
        for flag in (
            "GCP_PROJECT_ID",
            "ENABLE_GCS",
            "GCS_BUCKET",
            "ENABLE_BIGQUERY",
            "BIGQUERY_DATASET",
            "BIGQUERY_RUNS_TABLE",
            "BIGQUERY_EVENTS_TABLE",
            "BIGQUERY_EVALUATIONS_TABLE",
            "BIGQUERY_FEEDBACK_TABLE",
        ):
            assert flag in src, f"Config missing flag: {flag}"


# ---------------------------------------------------------------------------
# Test 2: services disabled by default (no creds in the test env)
# ---------------------------------------------------------------------------

class TestDisabledByDefault:
    def test_bigquery_logger_disabled_without_env(self, monkeypatch):
        # Force the env to the unconfigured state and re-import the module.
        for k in (
            "ENABLE_BIGQUERY", "GCP_PROJECT_ID", "BIGQUERY_DATASET",
            "ENABLE_GCS", "GCS_BUCKET",
        ):
            monkeypatch.delenv(k, raising=False)
        # Re-import config + gcp_clients fresh so flags re-read.
        import importlib
        import app.config as config_mod
        importlib.reload(config_mod)
        import app.utils.gcp_clients as gcp_mod
        importlib.reload(gcp_mod)

        assert gcp_mod.bigquery_logger.enabled is False
        assert gcp_mod.gcs_service.enabled is False

    def test_disabled_methods_are_noops(self, monkeypatch):
        for k in (
            "ENABLE_BIGQUERY", "GCP_PROJECT_ID", "BIGQUERY_DATASET",
            "ENABLE_GCS", "GCS_BUCKET",
        ):
            monkeypatch.delenv(k, raising=False)
        import importlib
        import app.config as config_mod
        importlib.reload(config_mod)
        import app.utils.gcp_clients as gcp_mod
        importlib.reload(gcp_mod)

        state = SimpleNamespace(
            simulation_id="sim_test", runner_status=SimpleNamespace(value="running"),
            total_rounds=10, started_at=None, completed_at=None,
            twitter_actions_count=5, reddit_actions_count=3, error=None,
        )
        action = SimpleNamespace(
            round_num=1, platform="twitter", agent_id=4, agent_name="a",
            action_type="CREATE_POST", success=True, timestamp=None,
        )
        # None of these should raise even with no client/creds.
        gcp_mod.bigquery_logger.log_run_start(state)
        gcp_mod.bigquery_logger.log_run_complete(state)
        gcp_mod.bigquery_logger.log_agent_event("sim_test", action)
        gcp_mod.bigquery_logger.flush_events("sim_test")
        gcp_mod.bigquery_logger.log_report_evaluation("rep_1", "sim_test", SimpleNamespace(
            validator_models=["gemini-2.5-flash"], overall_consensus="strong",
            overall_confidence=0.9, total_predictions=4, validators_used=1,
        ))
        gcp_mod.bigquery_logger.log_user_feedback("rep_1", "sim_test", "q?", "a.", 2)
        gcp_mod.gcs_service.upload("/nonexistent/path", "key")
        gcp_mod.gcs_service.upload_bytes(b"data", "key")
        assert gcp_mod.gcs_service.download_to_temp("key") is None
        assert gcp_mod.gcs_service.exists("key") is False


# ---------------------------------------------------------------------------
# Test 3: a fake-enabled BigQueryLogger captures rows via a stub client
# ---------------------------------------------------------------------------

class TestBigQueryCapturesRows:
    def test_log_run_complete_emits_row_and_flushes(self, monkeypatch):
        # Pretend the library + config are available.
        import importlib
        import app.config as config_mod
        monkeypatch.setattr(config_mod.Config, "ENABLE_BIGQUERY", True, raising=False)
        monkeypatch.setattr(config_mod.Config, "GCP_PROJECT_ID", "phoring-test", raising=False)
        monkeypatch.setattr(config_mod.Config, "BIGQUERY_DATASET", "telemetry", raising=False)
        monkeypatch.setattr(config_mod.Config, "BIGQUERY_RUNS_TABLE", "simulation_runs", raising=False)
        monkeypatch.setattr(config_mod.Config, "BIGQUERY_EVENTS_TABLE", "agent_events", raising=False)

        import app.utils.gcp_clients as gcp_mod
        importlib.reload(gcp_mod)

        # Force-enable by injecting a fake client even if google-cloud absent.
        captured = {"rows": []}

        class FakeClient:
            def insert_rows_json(self, table_id, rows):
                captured["rows"].extend((table_id, r) for r in rows)
                return []

        gcp_mod.bigquery_logger.enabled = True
        gcp_mod.bigquery_logger._client = FakeClient()
        gcp_mod.bigquery_logger._dataset_ref = "phoring-test.telemetry"

        state = SimpleNamespace(
            simulation_id="sim_abc", runner_status=SimpleNamespace(value="completed"),
            total_rounds=10, started_at="2026-07-04T10:00:00",
            completed_at="2026-07-04T10:30:00",
            twitter_actions_count=12, reddit_actions_count=8, error=None,
        )
        gcp_mod.bigquery_logger.log_run_complete(state)

        # At least one simulation_runs row captured.
        assert any(t.endswith(".simulation_runs") for t, _ in captured["rows"])
        row = [r for t, r in captured["rows"] if t.endswith(".simulation_runs")][0]
        assert row["simulation_id"] == "sim_abc"
        assert row["status"] == "completed"
        assert row["duration_seconds"] == 1800.0