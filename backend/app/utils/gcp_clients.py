"""Google Cloud integration clients (BigQuery + Cloud Storage).

Both services are *optional* and *config-gated*. When the relevant
``ENABLE_*`` flag is off, or the ``google-cloud-*`` package is not
installed, or required config is missing, the service is disabled and
every method becomes a no-op. Calls are wrapped so that a GCP failure
**never** breaks the Phoring pipeline — this mirrors the existing
graceful-degradation pattern used for web intelligence
(``web_intelligence.py``) and consensus validation
(``consensus_validator.py``).

Enabled at runtime by env vars (see ``Config``):

    ENABLE_GCS=true
    GCP_PROJECT_ID=phoring-501306
    GCS_BUCKET=phoring-artifacts
    ENABLE_BIGQUERY=true
    BIGQUERY_DATASET=phoring_telemetry
"""

import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..config import Config
from .logger import get_logger

logger = get_logger('phoring.gcp')

# Optional dependency import — degrades to None if the packages are absent.
try:
    from google.cloud import bigquery  # type: ignore
    from google.cloud import storage  # type: ignore
    _GCP_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only when deps missing
    bigquery = None  # type: ignore
    storage = None  # type: ignore
    _GCP_AVAILABLE = False


def _now_iso() -> str:
    """Current UTC timestamp as an ISO-8601 string for BigQuery rows."""
    return datetime.now(timezone.utc).isoformat()


class BigQueryLogger:
    """Append-only telemetry logger writing simulation/report/Q&A rows.

    All public methods are no-ops when disabled and never raise.
    Agent events are buffered and flushed in batches to avoid one
    ``insert_rows`` call per action (simulations emit thousands).
    """

    # Flush agent_events after this many buffered rows (or on run-complete).
    EVENT_FLUSH_BATCH = 50

    def __init__(self) -> None:
        self.enabled = (
            _GCP_AVAILABLE
            and bool(Config.ENABLE_BIGQUERY)
            and bool(Config.GCP_PROJECT_ID)
            and bool(Config.BIGQUERY_DATASET)
        )
        self._client = None
        self._dataset_ref = None
        # Per-simulation event buffer: simulation_id -> list[rows]
        self._event_buffer: Dict[str, List[Dict[str, Any]]] = {}
        self._buffer_lock = threading.Lock()

        if self.enabled:
            try:
                self._client = bigquery.Client(project=Config.GCP_PROJECT_ID)
                self._dataset_ref = f"{Config.GCP_PROJECT_ID}.{Config.BIGQUERY_DATASET}"
                logger.info(
                    f"BigQuery telemetry enabled: dataset={self._dataset_ref}"
                )
            except Exception as e:
                logger.warning(f"BigQuery client init failed — disabling: {e}")
                self.enabled = False
                self._client = None
        else:
            logger.debug("BigQuery telemetry disabled (ENABLE_BIGQUERY=false or unconfigured)")

    # ---- low-level insert ----
    def _insert(self, table_name: str, rows: List[Dict[str, Any]]) -> None:
        """Insert rows into a BigQuery table; swallow all errors."""
        if not self.enabled or not self._client or not rows:
            return
        try:
            table_id = f"{self._dataset_ref}.{table_name}"
            errors = self._client.insert_rows_json(table_id, rows)
            if errors:
                logger.warning(f"BigQuery insert returned errors for {table_name}: {errors}")
        except Exception as e:
            logger.warning(f"BigQuery insert failed for {table_name}: {e}")

    # ---- simulation runs ----
    def log_run_start(self, state: Any) -> None:
        """Emit a simulation_runs row when a run starts."""
        if not self.enabled:
            return
        try:
            self._insert(Config.BIGQUERY_RUNS_TABLE, [{
                "simulation_id": state.simulation_id,
                "status": state.runner_status.value if hasattr(state.runner_status, "value") else str(state.runner_status),
                "total_rounds": int(getattr(state, "total_rounds", 0) or 0),
                "started_at": getattr(state, "started_at", None) or _now_iso(),
                "completed_at": None,
                "duration_seconds": None,
                "twitter_actions_count": 0,
                "reddit_actions_count": 0,
                "error": None,
                "ts": _now_iso(),
            }])
        except Exception as e:
            logger.warning(f"log_run_start failed: {e}")

    def log_run_complete(self, state: Any) -> None:
        """Emit a final simulation_runs row + flush buffered agent events."""
        if not self.enabled:
            return
        try:
            started = getattr(state, "started_at", None)
            completed = getattr(state, "completed_at", None) or _now_iso()
            duration = None
            if started:
                try:
                    duration = (datetime.fromisoformat(completed) - datetime.fromisoformat(started)).total_seconds()
                except Exception:
                    duration = None
            self._insert(Config.BIGQUERY_RUNS_TABLE, [{
                "simulation_id": state.simulation_id,
                "status": state.runner_status.value if hasattr(state.runner_status, "value") else str(state.runner_status),
                "total_rounds": int(getattr(state, "total_rounds", 0) or 0),
                "started_at": started,
                "completed_at": completed,
                "duration_seconds": duration,
                "twitter_actions_count": int(getattr(state, "twitter_actions_count", 0) or 0),
                "reddit_actions_count": int(getattr(state, "reddit_actions_count", 0) or 0),
                "error": getattr(state, "error", None),
                "ts": _now_iso(),
            }])
            # Flush any remaining buffered agent events for this run.
            self.flush_events(state.simulation_id)
        except Exception as e:
            logger.warning(f"log_run_complete failed: {e}")

    # ---- agent events (batched) ----
    def log_agent_event(self, simulation_id: str, action: Any) -> None:
        """Buffer an agent_events row; flush when the batch threshold is hit."""
        if not self.enabled:
            return
        try:
            row = {
                "simulation_id": simulation_id,
                "round_num": int(getattr(action, "round_num", 0) or 0),
                "platform": getattr(action, "platform", ""),
                "agent_id": str(getattr(action, "agent_id", "")),
                "agent_name": getattr(action, "agent_name", ""),
                "action_type": getattr(action, "action_type", ""),
                "success": bool(getattr(action, "success", True)),
                "ts": getattr(action, "timestamp", None) or _now_iso(),
            }
            with self._buffer_lock:
                buf = self._event_buffer.setdefault(simulation_id, [])
                buf.append(row)
                should_flush = len(buf) >= self.EVENT_FLUSH_BATCH
            if should_flush:
                self.flush_events(simulation_id)
        except Exception as e:
            logger.warning(f"log_agent_event failed: {e}")

    def flush_events(self, simulation_id: str) -> None:
        """Flush buffered agent_events for one simulation to BigQuery."""
        if not self.enabled:
            return
        try:
            with self._buffer_lock:
                rows = self._event_buffer.pop(simulation_id, [])
            if rows:
                self._insert(Config.BIGQUERY_EVENTS_TABLE, rows)
        except Exception as e:
            logger.warning(f"flush_events failed: {e}")

    # ---- report evaluations ----
    def log_report_evaluation(
        self,
        report_id: str,
        simulation_id: Optional[str],
        validation_result: Any,
    ) -> None:
        """Emit a report_evaluations row from a consensus ValidationReport."""
        if not self.enabled:
            return
        try:
            validators = list(getattr(validation_result, "validator_models", []) or [])
            self._insert(Config.BIGQUERY_EVALUATIONS_TABLE, [{
                "report_id": report_id,
                "simulation_id": simulation_id or "",
                "validators": ",".join(validators),
                "overall_verdict": getattr(validation_result, "overall_consensus", ""),
                "overall_confidence": float(getattr(validation_result, "overall_confidence", 0.0) or 0.0),
                "total_predictions": int(getattr(validation_result, "total_predictions", 0) or 0),
                "validators_used": int(getattr(validation_result, "validators_used", 0) or 0),
                "ts": _now_iso(),
            }])
        except Exception as e:
            logger.warning(f"log_report_evaluation failed: {e}")

    # ---- user feedback / Q&A ----
    def log_user_feedback(
        self,
        report_id: Optional[str],
        simulation_id: str,
        user_message: str,
        agent_response: str,
        tool_calls_count: int = 0,
    ) -> None:
        """Emit a user_feedback row for a report Q&A exchange."""
        if not self.enabled:
            return
        try:
            self._insert(Config.BIGQUERY_FEEDBACK_TABLE, [{
                "report_id": report_id or "",
                "simulation_id": simulation_id,
                "user_message": (user_message or "")[:8000],
                "agent_response": (agent_response or "")[:8000],
                "tool_calls_count": int(tool_calls_count or 0),
                "ts": _now_iso(),
            }])
        except Exception as e:
            logger.warning(f"log_user_feedback failed: {e}")


class GcsService:
    """Cloud Storage mirror for uploaded documents and generated reports.

    No-op when disabled; never raises. The local filesystem remains the
    primary working store — GCS is a durable mirror plus the download
    fallback when a local cache file is missing.
    """

    def __init__(self) -> None:
        self.enabled = (
            _GCP_AVAILABLE
            and bool(Config.ENABLE_GCS)
            and bool(Config.GCS_BUCKET)
        )
        self._client = None
        self._bucket = None
        if self.enabled:
            try:
                self._client = storage.Client(project=Config.GCP_PROJECT_ID)
                self._bucket = self._client.bucket(Config.GCS_BUCKET)
                logger.info(f"GCS storage enabled: bucket={Config.GCS_BUCKET}")
            except Exception as e:
                logger.warning(f"GCS client init failed — disabling: {e}")
                self.enabled = False
                self._client = None
                self._bucket = None
        else:
            logger.debug("GCS storage disabled (ENABLE_GCS=false or unconfigured)")

    def upload(self, local_path: str, gcs_key: str) -> None:
        """Upload a local file to ``gs://<bucket>/<gcs_key>``; never raise."""
        if not self.enabled or not self._bucket:
            return
        try:
            if not os.path.exists(local_path):
                return
            blob = self._bucket.blob(gcs_key)
            blob.upload_from_filename(local_path)
            logger.debug(f"GCS uploaded: {gcs_key}")
        except Exception as e:
            logger.warning(f"GCS upload failed for {gcs_key}: {e}")

    def upload_bytes(self, data: bytes, gcs_key: str, content_type: str = "text/markdown") -> None:
        """Upload raw bytes to GCS; never raise."""
        if not self.enabled or not self._bucket:
            return
        try:
            blob = self._bucket.blob(gcs_key)
            blob.upload_from_string(data, content_type=content_type)
            logger.debug(f"GCS uploaded bytes: {gcs_key}")
        except Exception as e:
            logger.warning(f"GCS upload_bytes failed for {gcs_key}: {e}")

    def download_to_temp(self, gcs_key: str) -> Optional[str]:
        """Download a GCS object to a local temp file and return its path.

        Returns None if disabled, the object is missing, or download fails.
        """
        if not self.enabled or not self._bucket:
            return None
        try:
            import tempfile
            blob = self._bucket.blob(gcs_key)
            if not blob.exists():
                return None
            suffix = os.path.splitext(gcs_key)[1] or ".bin"
            fd, temp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            blob.download_to_filename(temp_path)
            logger.debug(f"GCS downloaded: {gcs_key} -> {temp_path}")
            return temp_path
        except Exception as e:
            logger.warning(f"GCS download failed for {gcs_key}: {e}")
            return None

    def exists(self, gcs_key: str) -> bool:
        """Return whether a GCS object exists; False when disabled/error."""
        if not self.enabled or not self._bucket:
            return False
        try:
            return self._bucket.blob(gcs_key).exists()
        except Exception as e:
            logger.warning(f"GCS exists check failed for {gcs_key}: {e}")
            return False


# Module-level singletons. Re-imported by callers as
# `from ..utils.gcp_clients import bigquery_logger, gcs_service`.
bigquery_logger = BigQueryLogger()
gcs_service = GcsService()