-- Phoring BigQuery telemetry schema.
-- Run via: bq mk --use_legacy_sql=false phoring_telemetry <each statement>
-- Or apply the whole file with deploy/gcp/setup_gcp.sh.
-- Dataset location: asia-south1 (matches the GCE/GKE deploy region).

-- ===== simulation_runs: one row per run start + one per run completion =====
CREATE TABLE IF NOT EXISTS `phoring_telemetry.simulation_runs` (
  simulation_id        STRING    NOT NULL,
  status               STRING,
  total_rounds         INT64,
  started_at           STRING,
  completed_at         STRING,
  duration_seconds     FLOAT64,
  twitter_actions_count INT64,
  reddit_actions_count  INT64,
  error                STRING,
  ts                   STRING    NOT NULL
);

-- ===== agent_events: one row per streamed agent action (batched at source) =====
CREATE TABLE IF NOT EXISTS `phoring_telemetry.agent_events` (
  simulation_id        STRING    NOT NULL,
  round_num            INT64,
  platform             STRING,
  agent_id             STRING,
  agent_name           STRING,
  action_type          STRING,
  success              BOOL,
  ts                   STRING    NOT NULL
);

-- ===== report_evaluations: one row per consensus validation result =====
CREATE TABLE IF NOT EXISTS `phoring_telemetry.report_evaluations` (
  report_id            STRING    NOT NULL,
  simulation_id        STRING,
  validators           STRING,
  overall_verdict      STRING,
  overall_confidence   FLOAT64,
  total_predictions    INT64,
  validators_used      INT64,
  ts                   STRING    NOT NULL
);

-- ===== user_feedback: one row per report Q&A exchange =====
CREATE TABLE IF NOT EXISTS `phoring_telemetry.user_feedback` (
  report_id            STRING,
  simulation_id        STRING    NOT NULL,
  user_message         STRING,
  agent_response       STRING,
  tool_calls_count     INT64,
  ts                   STRING    NOT NULL
);