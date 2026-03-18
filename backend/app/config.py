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


class Config:
    """Flask configuration."""
    
    # Flask config
    SECRET_KEY = os.environ.get('SECRET_KEY') or __import__('secrets').token_hex(32)
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
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

    # ===== Simulation Speed Mode =====
    # normal | fast | express
    SIMULATION_SPEED_MODE = os.environ.get('SIMULATION_SPEED_MODE', 'normal').strip().lower()

    # ===== Geopolitical Event Injection =====
    ENABLE_GEOPOLITICAL_EVENTS = os.environ.get('ENABLE_GEOPOLITICAL_EVENTS', 'true').strip().lower() == 'true'

    # file upload config
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024 # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # Text processing config
    DEFAULT_CHUNK_SIZE = 500 # default chunk size
    DEFAULT_CHUNK_OVERLAP = 50 # default chunk overlap
    
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
        """Validate config"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY not yet configured")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY not yet configured")
        return errors

