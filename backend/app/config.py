"""
Application configuration.
Loads settings from project root .env file.
"""

import os
from dotenv import load_dotenv

# Load project root .env file
# Path: Phoring/.env (loaded in backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # If .env not found, load from environment variables
    load_dotenv(override=True)


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable consistently."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


class Config:
    """Flask configuration."""

    # Flask config
    SECRET_KEY = os.environ.get('SECRET_KEY') or __import__('secrets').token_hex(32)
    DEBUG = _env_bool('FLASK_DEBUG', False)

    # JSON config - allow non-ASCII characters (avoid \uXXXX escaping)
    JSON_AS_ASCII = False

    # LLM config (OpenAI format)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')

    # Zep config
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')

    # News search APIs
    SERPER_API_KEY = os.environ.get('SERPER_API_KEY')
    NEWS_API_KEY = os.environ.get('NEWS_API_KEY')

    # ===== Multi-AI Validator Configuration =====
    # Validator AI #2 (e.g. Anthropic Claude)
    LLM_VALIDATOR_2_API_KEY = os.environ.get('LLM_VALIDATOR_2_API_KEY', '')
    LLM_VALIDATOR_2_BASE_URL = os.environ.get('LLM_VALIDATOR_2_BASE_URL', '')
    LLM_VALIDATOR_2_MODEL_NAME = os.environ.get('LLM_VALIDATOR_2_MODEL_NAME', '')

    # Validator AI #3 (e.g. Google Gemini)
    LLM_VALIDATOR_3_API_KEY = os.environ.get('LLM_VALIDATOR_3_API_KEY', '')
    LLM_VALIDATOR_3_BASE_URL = os.environ.get('LLM_VALIDATOR_3_BASE_URL', '')
    LLM_VALIDATOR_3_MODEL_NAME = os.environ.get('LLM_VALIDATOR_3_MODEL_NAME', '')

    # ===== Reproducibility and versioning =====
    # Stable seed used as the root for deterministic per-run/per-agent sub-seeds.
    SIMULATION_BASE_SEED = int(os.environ.get('SIMULATION_BASE_SEED', '20260717'))
    RUN_MANIFEST_VERSION = os.environ.get('RUN_MANIFEST_VERSION', '1').strip()
    PROMPT_VERSION = os.environ.get('PROMPT_VERSION', '2026-07-17').strip()
    RUN_MANIFEST_ENABLED = _env_bool('RUN_MANIFEST_ENABLED', True)
    PROFILE_PROVENANCE_V2 = _env_bool('PROFILE_PROVENANCE_V2', False)

    # ===== Simulation Speed Mode =====
    # normal | fast | express
    SIMULATION_SPEED_MODE = os.environ.get('SIMULATION_SPEED_MODE', 'normal').strip().lower()

    # ===== Event Injection =====
    # Legacy switch retained so existing deployments keep their current behavior.
    ENABLE_GEOPOLITICAL_EVENTS = _env_bool('ENABLE_GEOPOLITICAL_EVENTS', True)
    # off | observed_only | stress_test | hybrid
    EVENT_MODE = os.environ.get(
        'EVENT_MODE',
        'hybrid' if ENABLE_GEOPOLITICAL_EVENTS else 'off',
    ).strip().lower()

    # ===== Google Cloud integrations (optional, default off) =====
    # BigQuery telemetry + Cloud Storage artifact mirror. Both are config-gated
    # and degrade to no-ops when unset — see backend/app/utils/gcp_clients.py.
    GCP_PROJECT_ID = os.environ.get('GCP_PROJECT_ID', '')
    ENABLE_GCS = _env_bool('ENABLE_GCS', False)
    GCS_BUCKET = os.environ.get('GCS_BUCKET', '')
    GCS_UPLOAD_PREFIX = os.environ.get('GCS_UPLOAD_PREFIX', 'uploads/')
    GCS_REPORTS_PREFIX = os.environ.get('GCS_REPORTS_PREFIX', 'reports/')
    ENABLE_BIGQUERY = _env_bool('ENABLE_BIGQUERY', False)
    BIGQUERY_DATASET = os.environ.get('BIGQUERY_DATASET', '')
    BIGQUERY_RUNS_TABLE = os.environ.get('BIGQUERY_RUNS_TABLE', 'simulation_runs')
    BIGQUERY_EVENTS_TABLE = os.environ.get('BIGQUERY_EVENTS_TABLE', 'agent_events')
    BIGQUERY_EVALUATIONS_TABLE = os.environ.get('BIGQUERY_EVALUATIONS_TABLE', 'report_evaluations')
    BIGQUERY_FEEDBACK_TABLE = os.environ.get('BIGQUERY_FEEDBACK_TABLE', 'user_feedback')

    # file upload config
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    # Text processing config
    DEFAULT_CHUNK_SIZE = 500  # default chunk size
    DEFAULT_CHUNK_OVERLAP = 50  # default chunk overlap

    # Graph pagination caps
    MAX_GRAPH_NODES = int(os.environ.get('MAX_GRAPH_NODES', '2000'))
    MAX_GRAPH_EDGES = int(os.environ.get('MAX_GRAPH_EDGES', '5000'))

    # OASIS simulation configuration
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')

    # OASIS platform config
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]

    # Simulation calibration profile
    # - realism: conservative, lower volume, higher behavioral stability
    # - aggressive: higher posting/commenting volume for virality stress tests
    SIMULATION_CALIBRATION_MODE = os.environ.get('SIMULATION_CALIBRATION_MODE', 'realism').strip().lower()

    # Report agent config
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    @classmethod
    def validate(cls):
        """Validate required and bounded configuration values."""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY not yet configured")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY not yet configured")
        if cls.SIMULATION_SPEED_MODE not in {'normal', 'fast', 'express'}:
            errors.append(
                "SIMULATION_SPEED_MODE must be one of: normal, fast, express"
            )
        if cls.EVENT_MODE not in {'off', 'observed_only', 'stress_test', 'hybrid'}:
            errors.append(
                "EVENT_MODE must be one of: off, observed_only, stress_test, hybrid"
            )
        if cls.SIMULATION_BASE_SEED < 0:
            errors.append("SIMULATION_BASE_SEED must be non-negative")
        return errors
