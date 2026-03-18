"""
OASIS multi-platform simulation runner.
Runs Twitter and Reddit simulations in parallel, reading from a config file.

Features:
- Multi-platform (Twitter + Reddit) parallel simulation
- Keeps environment alive after simulation for command-wait mode
- IPC-based interview support
- Agent interview functionality
- Graceful environment shutdown

Usage:
    python run_parallel_simulation.py --config simulation_config.json
    python run_parallel_simulation.py --config simulation_config.json --no-wait  # Close immediately after completion
    python run_parallel_simulation.py --config simulation_config.json --twitter-only
    python run_parallel_simulation.py --config simulation_config.json --reddit-only

Log structure:
    sim_xxx/
    ├── twitter/
    │   └── actions.jsonl  # Twitter platform action log
    ├── reddit/
    │   └── actions.jsonl  # Reddit platform action log
    ├── simulation.log     # Simulation process log
    └── run_state.json     # Runtime status (for API queries)
"""

# ============================================================
# Windows encoding fix: set default UTF-8 encoding for all I/O
# Required because OASIS reads files without specifying encoding
# ============================================================
import sys
import os

if sys.platform == 'win32':
    # Set Python default I/O encoding to UTF-8
    # Affects all open() calls that don't specify encoding
    os.environ.setdefault('PYTHONUTF8', '1')
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    
    # Reconfigure stdout/stderr to use UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    
    # Set default encoding for open() function (monkey-patch)
    # Note: This ensures all file reads default to UTF-8
    import builtins
    _original_open = builtins.open
    
    def _utf8_open(file, mode='r', buffering=-1, encoding=None, errors=None, 
                   newline=None, closefd=True, opener=None):
        """
        Patched open() function that defaults to UTF-8 encoding in text mode.
        Required because OASIS reads files without specifying encoding.
        """
        # In text mode, if no encoding is specified, default to UTF-8
        if encoding is None and 'b' not in mode:
            encoding = 'utf-8'
        return _original_open(file, mode, buffering, encoding, errors, 
                              newline, closefd, opener)
    
    builtins.open = _utf8_open

import argparse
import asyncio
import json
import logging
import multiprocessing
import random
import signal
import sqlite3
import warnings
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


# Global variables for process shutdown control
_shutdown_event = None
_cleanup_done = False

# Add backend directory to Python path
# Script runs from backend/scripts/ directory
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_scripts_dir, '..'))
_project_root = os.path.abspath(os.path.join(_backend_dir, '..'))
sys.path.insert(0, _scripts_dir)
sys.path.insert(0, _backend_dir)

# Load .env file from project directory (includes LLM_API_KEY config)
from dotenv import load_dotenv
_env_file = os.path.join(_project_root, '.env')
if os.path.exists(_env_file):
    load_dotenv(_env_file)
    print(f"Loaded environment config: {_env_file}")
else:
    # Load backend/.env as fallback
    _backend_env = os.path.join(_backend_dir, '.env')
    if os.path.exists(_backend_env):
        load_dotenv(_backend_env)
        print(f"Loaded environment config: {_backend_env}")


class MaxTokensWarningFilter(logging.Filter):
    """Filter out camel-ai max_tokens warnings (not setting max_tokens is normal behavior)."""
    
    def filter(self, record):
        # Filter out log messages containing max_tokens warnings
        if "max_tokens" in record.getMessage() and "Invalid or missing" in record.getMessage():
            return False
        return True


# Add filter on module load to suppress camel-ai noise
logging.getLogger().addFilter(MaxTokensWarningFilter())


def disable_oasis_logging():
    """
    Disable verbose OASIS log output.
    OASIS logs every agent observation by default; we use action_logger instead.
    """
    # Suppress all OASIS loggers
    oasis_loggers = [
        "social.agent",
        "social.twitter", 
        "social.rec",
        "oasis.env",
        "table",
    ]
    
    for logger_name in oasis_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.CRITICAL)  # Only record critical errors
        logger.handlers.clear()
        logger.propagate = False


def init_logging_for_simulation(simulation_dir: str):
    """
    Initialize simulation logging configuration.

    Args:
        simulation_dir: Simulation directory path.
    """
    # Disable verbose OASIS logging
    disable_oasis_logging()
    
    # Clean up old log directory (if it exists)
    old_log_dir = os.path.join(simulation_dir, "log")
    if os.path.exists(old_log_dir):
        import shutil
        shutil.rmtree(old_log_dir, ignore_errors=True)


from action_logger import SimulationLogManager, PlatformActionLogger

try:
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType
    import oasis
    from oasis import (
        ActionType,
        LLMAction,
        ManualAction,
        generate_twitter_agent_graph,
        generate_reddit_agent_graph
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install dependencies: pip install oasis-ai camel-ai")
    sys.exit(1)


# Twitter available actions (INTERVIEW is handled via ManualAction separately)
TWITTER_ACTIONS = [
    ActionType.CREATE_POST,
    ActionType.LIKE_POST,
    ActionType.REPOST,
    ActionType.FOLLOW,
    ActionType.DO_NOTHING,
    ActionType.QUOTE_POST,
]

# Reddit available actions (INTERVIEW is handled via ManualAction separately)
REDDIT_ACTIONS = [
    ActionType.LIKE_POST,
    ActionType.DISLIKE_POST,
    ActionType.CREATE_POST,
    ActionType.CREATE_COMMENT,
    ActionType.LIKE_COMMENT,
    ActionType.DISLIKE_COMMENT,
    ActionType.SEARCH_POSTS,
    ActionType.SEARCH_USER,
    ActionType.TREND,
    ActionType.REFRESH,
    ActionType.DO_NOTHING,
    ActionType.FOLLOW,
    ActionType.MUTE,
]


# IPC constants
IPC_COMMANDS_DIR = "ipc_commands"
IPC_RESPONSES_DIR = "ipc_responses"
ENV_STATUS_FILE = "env_status.json"

class CommandType:
    """Command type constants."""
    INTERVIEW = "interview"
    BATCH_INTERVIEW = "batch_interview"
    CLOSE_ENV = "close_env"


class ParallelIPCHandler:
    """
    Multi-platform IPC command handler.

    Manages environments for both platforms, processing interview commands.
    """
    
    def __init__(
        self,
        simulation_dir: str,
        twitter_env=None,
        twitter_agent_graph=None,
        reddit_env=None,
        reddit_agent_graph=None
    ):
        self.simulation_dir = simulation_dir
        self.twitter_env = twitter_env
        self.twitter_agent_graph = twitter_agent_graph
        self.reddit_env = reddit_env
        self.reddit_agent_graph = reddit_agent_graph
        
        self.commands_dir = os.path.join(simulation_dir, IPC_COMMANDS_DIR)
        self.responses_dir = os.path.join(simulation_dir, IPC_RESPONSES_DIR)
        self.status_file = os.path.join(simulation_dir, ENV_STATUS_FILE)
        
        # Ensure directories exist
        os.makedirs(self.commands_dir, exist_ok=True)
        os.makedirs(self.responses_dir, exist_ok=True)
    
    def update_status(self, status: str):
        """Update environment status."""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump({
                "status": status,
                "twitter_available": self.twitter_env is not None,
                "reddit_available": self.reddit_env is not None,
                "timestamp": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
    
    def poll_command(self) -> Optional[Dict[str, Any]]:
        """Poll for pending commands to process."""
        if not os.path.exists(self.commands_dir):
            return None
        
        # Get command files sorted by modification time
        command_files = []
        for filename in os.listdir(self.commands_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.commands_dir, filename)
                command_files.append((filepath, os.path.getmtime(filepath)))
        
        command_files.sort(key=lambda x: x[1])
        
        for filepath, _ in command_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
        
        return None
    
    def send_response(self, command_id: str, status: str, result: Dict = None, error: str = None):
        """Send a response for a processed command."""
        response = {
            "command_id": command_id,
            "status": status,
            "result": result,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        response_file = os.path.join(self.responses_dir, f"{command_id}.json")
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=2)
        
        # Delete processed command file
        command_file = os.path.join(self.commands_dir, f"{command_id}.json")
        try:
            os.remove(command_file)
        except OSError:
            pass
    
    def _get_env_and_graph(self, platform: str):
        """
        Get the environment and agent_graph for a given platform.

        Args:
            platform: Platform name ("twitter" or "reddit").

        Returns:
            (env, agent_graph, platform_name) or (None, None, None) if unavailable.
        """
        if platform == "twitter" and self.twitter_env:
            return self.twitter_env, self.twitter_agent_graph, "twitter"
        elif platform == "reddit" and self.reddit_env:
            return self.reddit_env, self.reddit_agent_graph, "reddit"
        else:
            return None, None, None
    
    async def _interview_single_platform(self, agent_id: int, prompt: str, platform: str) -> Dict[str, Any]:
        """
        Run an interview on a single platform.

        Returns:
            Dict with result on success, or dict with error on failure.
        """
        env, agent_graph, actual_platform = self._get_env_and_graph(platform)
        
        if not env or not agent_graph:
            return {"platform": platform, "error": f"{platform} platform is not available"}
        
        try:
            agent = agent_graph.get_agent(agent_id)
            interview_action = ManualAction(
                action_type=ActionType.INTERVIEW,
                action_args={"prompt": prompt}
            )
            actions = {agent: interview_action}
            await env.step(actions)
            
            result = self._get_interview_result(agent_id, actual_platform)
            result["platform"] = actual_platform
            return result
            
        except Exception as e:
            return {"platform": platform, "error": f"Interview failed: {type(e).__name__}"}
    
    async def handle_interview(self, command_id: str, agent_id: int, prompt: str, platform: str = None) -> bool:
        """
        Process an agent interview request.

        Args:
            command_id: Command ID.
            agent_id: Agent ID.
            prompt: Interview prompt.
            platform: Target platform (optional).
                - "twitter": Interview on Twitter platform only.
                - "reddit": Interview on Reddit platform only.
                - None: Interview on all available platforms.

        Returns:
            True on success, False on failure.
        """
        # If a specific platform is specified, interview on that platform only
        if platform in ("twitter", "reddit"):
            result = await self._interview_single_platform(agent_id, prompt, platform)
            
            if "error" in result:
                self.send_response(command_id, "failed", error=result["error"])
                print(f"  Interview failed: agent_id={agent_id}, platform={platform}, error={result['error']}")
                return False
            else:
                self.send_response(command_id, "completed", result=result)
                print(f"  Interview complete: agent_id={agent_id}, platform={platform}")
                return True
        
        # No platform specified: interview on all available platforms
        if not self.twitter_env and not self.reddit_env:
            self.send_response(command_id, "failed", error="No simulation environment available")
            return False
        
        results = {
            "agent_id": agent_id,
            "prompt": prompt,
            "platforms": {}
        }
        success_count = 0
        
        # Interview on all available platforms concurrently
        tasks = []
        platforms_to_interview = []
        
        if self.twitter_env:
            tasks.append(self._interview_single_platform(agent_id, prompt, "twitter"))
            platforms_to_interview.append("twitter")
        
        if self.reddit_env:
            tasks.append(self._interview_single_platform(agent_id, prompt, "reddit"))
            platforms_to_interview.append("reddit")
        
        # Run interviews concurrently
        platform_results = await asyncio.gather(*tasks)
        
        for platform_name, platform_result in zip(platforms_to_interview, platform_results):
            results["platforms"][platform_name] = platform_result
            if "error" not in platform_result:
                success_count += 1
        
        if success_count > 0:
            self.send_response(command_id, "completed", result=results)
            print(f"  Interview complete: agent_id={agent_id}, successful platforms={success_count}/{len(platforms_to_interview)}")
            return True
        else:
            errors = [f"{p}: {r.get('error', 'unknown error')}" for p, r in results["platforms"].items()]
            self.send_response(command_id, "failed", error="; ".join(errors))
            print(f"  Interview failed: agent_id={agent_id}, all platforms failed")
            return False
    
    async def handle_batch_interview(self, command_id: str, interviews: List[Dict], platform: str = None) -> bool:
        """
        Process a batch of agent interviews.

        Args:
            command_id: Command ID.
            interviews: [{"agent_id": int, "prompt": str, "platform": str (optional)}, ...].
            platform: Default platform for all interviews.
                - "twitter": Interview on Twitter platform only.
                - "reddit": Interview on Reddit platform only.
                - None: Interview each agent on all available platforms.
        """
        # Split interviews by platform
        twitter_interviews = []
        reddit_interviews = []
        both_platforms_interviews = []  # Interviews that should run on all platforms
        
        for interview in interviews:
            item_platform = interview.get("platform", platform)
            if item_platform == "twitter":
                twitter_interviews.append(interview)
            elif item_platform == "reddit":
                reddit_interviews.append(interview)
            else:
                # No platform specified: interview on all available platforms
                both_platforms_interviews.append(interview)

        # Distribute unspecified-platform interviews to all available platforms
        if both_platforms_interviews:
            if self.twitter_env:
                twitter_interviews.extend(both_platforms_interviews)
            if self.reddit_env:
                reddit_interviews.extend(both_platforms_interviews)
        
        results = {}
        
        # Process Twitter platform interview
        if twitter_interviews and self.twitter_env:
            try:
                twitter_actions = {}
                for interview in twitter_interviews:
                    agent_id = interview.get("agent_id")
                    prompt = interview.get("prompt", "")
                    try:
                        agent = self.twitter_agent_graph.get_agent(agent_id)
                        twitter_actions[agent] = ManualAction(
                            action_type=ActionType.INTERVIEW,
                            action_args={"prompt": prompt}
                        )
                    except Exception as e:
                        print(f"  Warning: Failed to get Twitter agent {agent_id}: {e}")
                
                if twitter_actions:
                    await self.twitter_env.step(twitter_actions)
                    
                    for interview in twitter_interviews:
                        agent_id = interview.get("agent_id")
                        result = self._get_interview_result(agent_id, "twitter")
                        result["platform"] = "twitter"
                        results[f"twitter_{agent_id}"] = result
            except Exception as e:
                print(f"  Twitter batch interview failed: {e}")
        
        # Process Reddit platform interview
        if reddit_interviews and self.reddit_env:
            try:
                reddit_actions = {}
                for interview in reddit_interviews:
                    agent_id = interview.get("agent_id")
                    prompt = interview.get("prompt", "")
                    try:
                        agent = self.reddit_agent_graph.get_agent(agent_id)
                        reddit_actions[agent] = ManualAction(
                            action_type=ActionType.INTERVIEW,
                            action_args={"prompt": prompt}
                        )
                    except Exception as e:
                        print(f"  Warning: Failed to get Reddit agent {agent_id}: {e}")
                
                if reddit_actions:
                    await self.reddit_env.step(reddit_actions)
                    
                    for interview in reddit_interviews:
                        agent_id = interview.get("agent_id")
                        result = self._get_interview_result(agent_id, "reddit")
                        result["platform"] = "reddit"
                        results[f"reddit_{agent_id}"] = result
            except Exception as e:
                print(f"  Reddit batch interview failed: {e}")
        
        if results:
            self.send_response(command_id, "completed", result={
                "interviews_count": len(results),
                "results": results
            })
            print(f"  Batch interview complete: {len(results)} agents")
            return True
        else:
            self.send_response(command_id, "failed", error="No successful interviews")
            return False
    
    def _get_interview_result(self, agent_id: int, platform: str) -> Dict[str, Any]:
        """Get the latest interview result from the database."""
        db_path = os.path.join(self.simulation_dir, f"{platform}_simulation.db")
        
        result = {
            "agent_id": agent_id,
            "response": None,
            "timestamp": None
        }
        
        if not os.path.exists(db_path):
            return result
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Query the latest interview record
            cursor.execute("""
                SELECT user_id, info, created_at
                FROM trace
                WHERE action =? AND user_id =?
                ORDER BY created_at DESC
                LIMIT 1
            """, (ActionType.INTERVIEW.value, agent_id))
            
            row = cursor.fetchone()
            if row:
                user_id, info_json, created_at = row
                try:
                    info = json.loads(info_json) if info_json else {}
                    result["response"] = info.get("response", info)
                    result["timestamp"] = created_at
                except json.JSONDecodeError:
                    result["response"] = info_json
            
            conn.close()
            
        except Exception as e:
            print(f"  Failed to read interview result: {e}")
        
        return result
    
    async def process_commands(self) -> bool:
        """
        Process all pending commands.

        Returns:
            True to continue running, False to shut down.
        """
        command = self.poll_command()
        if not command:
            return True
        
        command_id = command.get("command_id")
        command_type = command.get("command_type")
        args = command.get("args", {})
        
        print(f"\n  Received IPC command: {command_type}, id={command_id}")
        
        if command_type == CommandType.INTERVIEW:
            await self.handle_interview(
                command_id,
                args.get("agent_id", 0),
                args.get("prompt", ""),
                args.get("platform")
            )
            return True
            
        elif command_type == CommandType.BATCH_INTERVIEW:
            await self.handle_batch_interview(
                command_id,
                args.get("interviews", []),
                args.get("platform")
            )
            return True
            
        elif command_type == CommandType.CLOSE_ENV:
            print("  Received close environment command")
            self.send_response(command_id, "completed", result={"message": "Environment closed"})
            return False
        
        else:
            self.send_response(command_id, "failed", error=f"Unknown command type: {command_type}")
            return True


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# Filter non-core action types (excluded from analysis)
FILTERED_ACTIONS = {'refresh', 'sign_up'}

# Action type mapping (database value -> display name)
ACTION_TYPE_MAP = {
    'create_post': 'CREATE_POST',
    'like_post': 'LIKE_POST',
    'dislike_post': 'DISLIKE_POST',
    'repost': 'REPOST',
    'quote_post': 'QUOTE_POST',
    'follow': 'FOLLOW',
    'mute': 'MUTE',
    'create_comment': 'CREATE_COMMENT',
    'like_comment': 'LIKE_COMMENT',
    'dislike_comment': 'DISLIKE_COMMENT',
    'search_posts': 'SEARCH_POSTS',
    'search_user': 'SEARCH_USER',
    'trend': 'TREND',
    'do_nothing': 'DO_NOTHING',
    'interview': 'INTERVIEW',
}


def get_agent_names_from_config(config: Dict[str, Any]) -> Dict[int, str]:
    """
    Get the agent_id -> entity_name mapping from simulation_config.

    Used to replace generic "Agent_0" names in actions.jsonl with actual entity names.

    Args:
        config: Parsed simulation_config.json content.

    Returns:
        Dict mapping agent_id to entity_name.
    """
    agent_names = {}
    agent_configs = config.get("agent_configs", [])
    
    for agent_config in agent_configs:
        agent_id = agent_config.get("agent_id")
        entity_name = agent_config.get("entity_name", f"Agent_{agent_id}")
        if agent_id is not None:
            agent_names[agent_id] = entity_name
    
    return agent_names


def fetch_new_actions_from_db(
    db_path: str,
    last_rowid: int,
    agent_names: Dict[int, str]
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Fetch new action records from the database with enriched info.

    Args:
        db_path: Database file path.
        last_rowid: Last processed max rowid (using rowid instead of created_at to avoid format issues).
        agent_names: Dict mapping agent_id to agent_name.

    Returns:
        (actions_list, new_last_rowid)
        - actions_list: List of dicts with agent_id, agent_name, action_type, action_args (enriched).
        - new_last_rowid: New maximum rowid for next fetch.
    """
    actions = []
    new_last_rowid = last_rowid
    
    if not os.path.exists(db_path):
        return actions, new_last_rowid
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Track already-processed row IDs (rowid is a SQLite built-in field)
        # Using rowid instead of created_at to avoid timestamp format inconsistencies
        cursor.execute("""
            SELECT rowid, user_id, action, info
            FROM trace
            WHERE rowid >?
            ORDER BY rowid ASC
        """, (last_rowid,))
        
        for rowid, user_id, action, info_json in cursor.fetchall():
            # Update max rowid
            new_last_rowid = rowid
            
            # Filter out non-core action types
            if action in FILTERED_ACTIONS:
                continue
            
            # Parse action parameters
            try:
                action_args = json.loads(info_json) if info_json else {}
            except json.JSONDecodeError:
                action_args = {}
            
            # Extract relevant fields from action_args (keep full content, no truncation)
            simplified_args = {}
            if 'content' in action_args:
                simplified_args['content'] = action_args['content']
            if 'post_id' in action_args:
                simplified_args['post_id'] = action_args['post_id']
            if 'comment_id' in action_args:
                simplified_args['comment_id'] = action_args['comment_id']
            if 'quoted_id' in action_args:
                simplified_args['quoted_id'] = action_args['quoted_id']
            if 'new_post_id' in action_args:
                simplified_args['new_post_id'] = action_args['new_post_id']
            if 'follow_id' in action_args:
                simplified_args['follow_id'] = action_args['follow_id']
            if 'query' in action_args:
                simplified_args['query'] = action_args['query']
            if 'like_id' in action_args:
                simplified_args['like_id'] = action_args['like_id']
            if 'dislike_id' in action_args:
                simplified_args['dislike_id'] = action_args['dislike_id']
            
            # Convert action type to display name
            action_type = ACTION_TYPE_MAP.get(action, action.upper())
            
            # Enrich with contextual info (post content, usernames, etc.)
            _enrich_action_context(cursor, action_type, simplified_args, agent_names)
            
            actions.append({
                'agent_id': user_id,
                'agent_name': agent_names.get(user_id, f'Agent_{user_id}'),
                'action_type': action_type,
                'action_args': simplified_args,
            })
        
        conn.close()
    except Exception as e:
        print(f"Failed to read database: {e}")
    
    return actions, new_last_rowid


def _enrich_action_context(
    cursor,
    action_type: str,
    action_args: Dict[str, Any],
    agent_names: Dict[int, str]
) -> None:
    """
    Enrich action args with contextual info (post content, usernames, etc.).

    Args:
        cursor: Database cursor.
        action_type: Action type string.
        action_args: Action parameters dict (modified in-place).
        agent_names: Dict mapping agent_id to agent_name.
    """
    try:
        # Like/dislike post: enrich with post content and author
        if action_type in ('LIKE_POST', 'DISLIKE_POST'):
            post_id = action_args.get('post_id')
            if post_id:
                post_info = _get_post_info(cursor, post_id, agent_names)
                if post_info:
                    action_args['post_content'] = post_info.get('content', '')
                    action_args['post_author_name'] = post_info.get('author_name', '')
        
        # Repost: enrich with original post content
        elif action_type == 'REPOST':
            new_post_id = action_args.get('new_post_id')
            if new_post_id:
                # Get original_post_id from the reposted post
                cursor.execute("""
                    SELECT original_post_id FROM post WHERE post_id =?
                """, (new_post_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    original_post_id = row[0]
                    original_info = _get_post_info(cursor, original_post_id, agent_names)
                    if original_info:
                        action_args['original_content'] = original_info.get('content', '')
                        action_args['original_author_name'] = original_info.get('author_name', '')
        
        # Quote post: enrich with original content and quote comment
        elif action_type == 'QUOTE_POST':
            quoted_id = action_args.get('quoted_id')
            new_post_id = action_args.get('new_post_id')
            
            if quoted_id:
                original_info = _get_post_info(cursor, quoted_id, agent_names)
                if original_info:
                    action_args['original_content'] = original_info.get('content', '')
                    action_args['original_author_name'] = original_info.get('author_name', '')
            
            # Get the quote comment content (quote_content)
            if new_post_id:
                cursor.execute("""
                    SELECT quote_content FROM post WHERE post_id =?
                """, (new_post_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    action_args['quote_content'] = row[0]
        
        # Follow: enrich with target username
        elif action_type == 'FOLLOW':
            follow_id = action_args.get('follow_id')
            if follow_id:
                # Get the followee_id from the follow record
                cursor.execute("""
                    SELECT followee_id FROM follow WHERE follow_id =?
                """, (follow_id,))
                row = cursor.fetchone()
                if row:
                    followee_id = row[0]
                    target_name = _get_user_name(cursor, followee_id, agent_names)
                    if target_name:
                        action_args['target_user_name'] = target_name
        
        # Mute: enrich with target username
        elif action_type == 'MUTE':
            # Get target user_id or target_id from action_args
            target_id = action_args.get('user_id') or action_args.get('target_id')
            if target_id:
                target_name = _get_user_name(cursor, target_id, agent_names)
                if target_name:
                    action_args['target_user_name'] = target_name
        
        # Like/dislike comment: enrich with comment content and author
        elif action_type in ('LIKE_COMMENT', 'DISLIKE_COMMENT'):
            comment_id = action_args.get('comment_id')
            if comment_id:
                comment_info = _get_comment_info(cursor, comment_id, agent_names)
                if comment_info:
                    action_args['comment_content'] = comment_info.get('content', '')
                    action_args['comment_author_name'] = comment_info.get('author_name', '')
        
        # Create comment: enrich with parent post info
        elif action_type == 'CREATE_COMMENT':
            post_id = action_args.get('post_id')
            if post_id:
                post_info = _get_post_info(cursor, post_id, agent_names)
                if post_info:
                    action_args['post_content'] = post_info.get('content', '')
                    action_args['post_author_name'] = post_info.get('author_name', '')
    
    except Exception as e:
        # Enrichment failure should not affect main workflow
        print(f"  Context enrichment failed: {e}")


def _get_post_info(
    cursor,
    post_id: int,
    agent_names: Dict[int, str]
) -> Optional[Dict[str, str]]:
    """
    Get post info from the database.

    Args:
        cursor: Database cursor.
        post_id: Post ID.
        agent_names: Dict mapping agent_id to agent_name.

    Returns:
        Dict with content and author_name, or None if not found.
    """
    try:
        cursor.execute("""
            SELECT p.content, p.user_id, u.agent_id
            FROM post p
            LEFT JOIN user u ON p.user_id = u.user_id
            WHERE p.post_id =?
        """, (post_id,))
        row = cursor.fetchone()
        if row:
            content = row[0] or ''
            user_id = row[1]
            agent_id = row[2]
            
            # Look up author name from agent_names first
            author_name = ''
            if agent_id is not None and agent_id in agent_names:
                author_name = agent_names[agent_id]
            elif user_id:
                # Fall back to user table lookup
                cursor.execute("SELECT name, user_name FROM user WHERE user_id =?", (user_id,))
                user_row = cursor.fetchone()
                if user_row:
                    author_name = user_row[0] or user_row[1] or ''

            return {'content': content, 'author_name': author_name}
    except Exception:
        pass
    return None


def _get_user_name(
    cursor,
    user_id: int,
    agent_names: Dict[int, str]
) -> Optional[str]:
    """
    Get username by user ID.

    Args:
        cursor: Database cursor.
        user_id: User ID.
        agent_names: Dict mapping agent_id to agent_name.

    Returns:
        Username string, or None if not found.
    """
    try:
        cursor.execute("""
            SELECT agent_id, name, user_name FROM user WHERE user_id =?
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            agent_id = row[0]
            name = row[1]
            user_name = row[2]
            
            # Look up from agent_names first
            if agent_id is not None and agent_id in agent_names:
                return agent_names[agent_id]
            return name or user_name or ''
    except Exception:
        pass
    return None


def _get_comment_info(
    cursor,
    comment_id: int,
    agent_names: Dict[int, str]
) -> Optional[Dict[str, str]]:
    """
    Get comment info from the database.

    Args:
        cursor: Database cursor.
        comment_id: Comment ID.
        agent_names: Dict mapping agent_id to agent_name.

    Returns:
        Dict with content and author_name, or None if not found.
    """
    try:
        cursor.execute("""
            SELECT c.content, c.user_id, u.agent_id
            FROM comment c
            LEFT JOIN user u ON c.user_id = u.user_id
            WHERE c.comment_id =?
        """, (comment_id,))
        row = cursor.fetchone()
        if row:
            content = row[0] or ''
            user_id = row[1]
            agent_id = row[2]
            
            # Look up author name from agent_names first
            author_name = ''
            if agent_id is not None and agent_id in agent_names:
                author_name = agent_names[agent_id]
            elif user_id:
                # Fall back to user table lookup
                cursor.execute("SELECT name, user_name FROM user WHERE user_id =?", (user_id,))
                user_row = cursor.fetchone()
                if user_row:
                    author_name = user_row[0] or user_row[1] or ''

            return {'content': content, 'author_name': author_name}
    except Exception:
        pass
    return None


def create_model(config: Dict[str, Any], use_boost: bool = False):
    """
    Create an LLM model instance.

    Supports two LLM configurations for running simulations:
    - Primary config: LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME
    - Boost config (optional): LLM_BOOST_API_KEY, LLM_BOOST_BASE_URL, LLM_BOOST_MODEL_NAME

    If a boost LLM is configured, the simulation can use a separate model for each platform.

    Args:
        config: Simulation configuration dict.
        use_boost: Whether to use the boost LLM config (if available).
    """
    # Check for boost configuration
    boost_api_key = os.environ.get("LLM_BOOST_API_KEY", "")
    boost_base_url = os.environ.get("LLM_BOOST_BASE_URL", "")
    boost_model = os.environ.get("LLM_BOOST_MODEL_NAME", "")
    has_boost_config = bool(boost_api_key)
    
    # Select boost or primary LLM config based on parameter
    if use_boost and has_boost_config:
        # Use boost config
        llm_api_key = boost_api_key
        llm_base_url = boost_base_url
        llm_model = boost_model or os.environ.get("LLM_MODEL_NAME", "")
        config_label = "[Boost LLM]"
    else:
        # Use primary config
        llm_api_key = os.environ.get("LLM_API_KEY", "")
        llm_base_url = os.environ.get("LLM_BASE_URL", "")
        llm_model = os.environ.get("LLM_MODEL_NAME", "")
        config_label = "[Primary LLM]"
    
    # If not in .env, fall back to config file
    if not llm_model:
        llm_model = config.get("llm_model", "gpt-4o-mini")
    
    # Set camel-ai environment variables
    if llm_api_key:
        os.environ["OPENAI_API_KEY"] = llm_api_key
    
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("API Key not configured. Please set LLM_API_KEY in the project .env file.")
    
    if llm_base_url:
        os.environ["OPENAI_API_BASE_URL"] = llm_base_url
    
    print(f"{config_label} model={llm_model}, base_url={llm_base_url[:40] if llm_base_url else 'default'}...")
    
    return ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=llm_model,
    )


def get_active_agents_for_round(
    env,
    config: Dict[str, Any],
    current_hour: int,
    round_num: int
) -> List:
    """Get active agents for this round based on time config."""
    time_config = config.get("time_config", {})
    agent_configs = config.get("agent_configs", [])
    
    base_min = time_config.get("agents_per_hour_min", 5)
    base_max = time_config.get("agents_per_hour_max", 20)
    
    peak_hours = time_config.get("peak_hours", [9, 10, 11, 14, 15, 20, 21, 22])
    off_peak_hours = time_config.get("off_peak_hours", [0, 1, 2, 3, 4, 5])
    
    if current_hour in peak_hours:
        multiplier = time_config.get("peak_activity_multiplier", 1.5)
    elif current_hour in off_peak_hours:
        multiplier = time_config.get("off_peak_activity_multiplier", 0.3)
    else:
        multiplier = 1.0
    
    target_count = int(random.uniform(base_min, base_max) * multiplier)
    
    candidates = []
    for cfg in agent_configs:
        agent_id = cfg.get("agent_id", 0)
        active_hours = cfg.get("active_hours", list(range(8, 23)))
        activity_level = cfg.get("activity_level", 0.5)
        
        if current_hour not in active_hours:
            continue
        
        if random.random() < activity_level:
            candidates.append(agent_id)
    
    selected_ids = random.sample(
        candidates, 
        min(target_count, len(candidates))
    ) if candidates else []
    
    active_agents = []
    for agent_id in selected_ids:
        try:
            agent = env.agent_graph.get_agent(agent_id)
            active_agents.append((agent_id, agent))
        except Exception:
            pass
    
    return active_agents


class PlatformSimulation:
    """Container for platform simulation results."""
    def __init__(self):
        self.env = None
        self.agent_graph = None
        self.total_actions = 0


async def run_twitter_simulation(
    config: Dict[str, Any], 
    simulation_dir: str,
    action_logger: Optional[PlatformActionLogger] = None,
    main_logger: Optional[SimulationLogManager] = None,
    max_rounds: Optional[int] = None
) -> PlatformSimulation:
    """Run Twitter simulation
    
    Args:
        config: Simulation configuration
        simulation_dir: Simulation directory
        action_logger: Action logger
        main_logger: Log manager
        max_rounds: Maximum simulation rounds (optional, truncates long simulations)
        
    Returns:
        PlatformSimulation: Object containing env, agent_graph, and results
    """
    result = PlatformSimulation()
    
    def log_info(msg):
        if main_logger:
            main_logger.info(f"[Twitter] {msg}")
        print(f"[Twitter] {msg}")
    
    log_info("Initialize...")
    
    # Create LLM model with primary config for Twitter
    model = create_model(config, use_boost=False)
    
    # Load OASIS Twitter CSV profile
    profile_path = os.path.join(simulation_dir, "twitter_profiles.csv")
    if not os.path.exists(profile_path):
        log_info(f"Error: Profile file does not exist: {profile_path}")
        return result
    
    result.agent_graph = await generate_twitter_agent_graph(
        profile_path=profile_path,
        model=model,
        available_actions=TWITTER_ACTIONS,
    )
    
    # Get agent names from config file (entity_name defaults to Agent_X)
    agent_names = get_agent_names_from_config(config)
    # If config doesn't cover a certain agent, use OASIS default name
    for agent_id, agent in result.agent_graph.get_agents():
        if agent_id not in agent_names:
            agent_names[agent_id] = getattr(agent, 'name', f'Agent_{agent_id}')

    db_path = os.path.join(simulation_dir, "twitter_simulation.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    result.env = oasis.make(
        agent_graph=result.agent_graph,
        platform=oasis.DefaultPlatformType.TWITTER,
        database_path=db_path,
        semaphore=30,  # Max concurrent LLM requests, prevents API overload
    )

    await result.env.reset()
    log_info("Environment initialized")
    
    if action_logger:
        action_logger.log_simulation_start(config)
    
    total_actions = 0
    last_rowid = 0  # Track last processed database row (using rowid to avoid created_at format issues)

    # Execute initial events
    event_config = config.get("event_config", {})
    initial_posts = event_config.get("initial_posts", [])

    # Record round 0 start (initial events stage)
    if action_logger:
        action_logger.log_round_start(0, 0)  # round 0, simulated_hour 0

    initial_action_count = 0
    if initial_posts:
        initial_actions = {}
        for post in initial_posts:
            agent_id = post.get("poster_agent_id", 0)
            content = post.get("content", "")
            # Tag seeded content so downstream analysis can distinguish it
            tagged_content = f"[SEED] {content}"
            try:
                agent = result.env.agent_graph.get_agent(agent_id)
                initial_actions[agent] = ManualAction(
                    action_type=ActionType.CREATE_POST,
                    action_args={"content": tagged_content}
                )

                if action_logger:
                    action_logger.log_action(
                        round_num=0,
                        agent_id=agent_id,
                        agent_name=agent_names.get(agent_id, f"Agent_{agent_id}"),
                        action_type="CREATE_POST",
                        action_args={"content": tagged_content, "is_synthetic": True}
                    )
                    total_actions += 1
                    initial_action_count += 1
            except Exception:
                pass

        if initial_actions:
            await result.env.step(initial_actions)
            log_info(f"Published {len(initial_actions)} seeded posts (tagged [SEED])")

    # Record round 0 finish
    if action_logger:
        action_logger.log_round_end(0, initial_action_count)
    
    # Simulation parameters
    time_config = config.get("time_config", {})
    total_hours = time_config.get("total_simulation_hours", 72)
    minutes_per_round = time_config.get("minutes_per_round", 30)
    total_rounds = (total_hours * 60) // minutes_per_round

    # If max rounds limit specified, truncate
    if max_rounds is not None and max_rounds > 0:
        original_rounds = total_rounds
        total_rounds = min(total_rounds, max_rounds)
        if total_rounds < original_rounds:
            log_info(f"Rounds truncated: {original_rounds} -> {total_rounds} (max_rounds={max_rounds})")
    
    start_time = datetime.now()
    
    for round_num in range(total_rounds):
        # Check for shutdown signal
        if _shutdown_event and _shutdown_event.is_set():
            if main_logger:
                main_logger.info(f"Shutdown signal received, stopping simulation at round {round_num + 1}")
            break
        
        simulated_minutes = round_num * minutes_per_round
        simulated_hour = (simulated_minutes // 60) % 24
        simulated_day = simulated_minutes // (60 * 24) + 1
        
        active_agents = get_active_agents_for_round(
            result.env, config, simulated_hour, round_num
        )
        
        # Record round start regardless of active agent count
        if action_logger:
            action_logger.log_round_start(round_num + 1, simulated_hour)

        if not active_agents:
            # No active agents; record round finish with 0 actions
            if action_logger:
                action_logger.log_round_end(round_num + 1, 0)
            continue
        
        actions = {agent: LLMAction() for _, agent in active_agents}
        await result.env.step(actions)
        
        # Get new action records from database
        actual_actions, last_rowid = fetch_new_actions_from_db(
            db_path, last_rowid, agent_names
        )
        
        round_action_count = 0
        for action_data in actual_actions:
            if action_logger:
                action_logger.log_action(
                    round_num=round_num + 1,
                    agent_id=action_data['agent_id'],
                    agent_name=action_data['agent_name'],
                    action_type=action_data['action_type'],
                    action_args=action_data['action_args']
                )
                total_actions += 1
                round_action_count += 1
        
        if action_logger:
            action_logger.log_round_end(round_num + 1, round_action_count)
        
        if (round_num + 1) % 20 == 0:
            progress = (round_num + 1) / total_rounds * 100
            log_info(f"Day {simulated_day}, {simulated_hour:02d}:00 - Round {round_num + 1}/{total_rounds} ({progress:.1f}%)")
    
    # Note: do not close environment yet; it may be needed for interviews
    
    if action_logger:
        action_logger.log_simulation_end(total_rounds, total_actions)
    
    result.total_actions = total_actions
    elapsed = (datetime.now() - start_time).total_seconds()
    log_info(f"Simulation complete! Duration: {elapsed:.1f}s, total actions: {total_actions}")
    
    return result


async def run_reddit_simulation(
    config: Dict[str, Any], 
    simulation_dir: str,
    action_logger: Optional[PlatformActionLogger] = None,
    main_logger: Optional[SimulationLogManager] = None,
    max_rounds: Optional[int] = None
) -> PlatformSimulation:
    """Run Reddit simulation
    
    Args:
        config: Simulation configuration
        simulation_dir: Simulation directory
        action_logger: Action logger
        main_logger: Log manager
        max_rounds: Maximum simulation rounds (optional, truncates long simulations)
        
    Returns:
        PlatformSimulation: Object containing env, agent_graph, and results
    """
    result = PlatformSimulation()
    
    def log_info(msg):
        if main_logger:
            main_logger.info(f"[Reddit] {msg}")
        print(f"[Reddit] {msg}")
    
    log_info("Initialize...")
    
    # Create LLM model with boost config for Reddit (falls back to primary if unavailable)
    model = create_model(config, use_boost=True)
    
    profile_path = os.path.join(simulation_dir, "reddit_profiles.json")
    if not os.path.exists(profile_path):
        log_info(f"Error: Profile file does not exist: {profile_path}")
        return result
    
    result.agent_graph = await generate_reddit_agent_graph(
        profile_path=profile_path,
        model=model,
        available_actions=REDDIT_ACTIONS,
    )
    
    # Get agent names from config file (entity_name defaults to Agent_X)
    agent_names = get_agent_names_from_config(config)
    # If config doesn't cover a certain agent, use OASIS default name
    for agent_id, agent in result.agent_graph.get_agents():
        if agent_id not in agent_names:
            agent_names[agent_id] = getattr(agent, 'name', f'Agent_{agent_id}')

    db_path = os.path.join(simulation_dir, "reddit_simulation.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    result.env = oasis.make(
        agent_graph=result.agent_graph,
        platform=oasis.DefaultPlatformType.REDDIT,
        database_path=db_path,
        semaphore=30,  # Max concurrent LLM requests, prevents API overload
    )

    await result.env.reset()
    log_info("Environment initialized")
    
    if action_logger:
        action_logger.log_simulation_start(config)
    
    total_actions = 0
    last_rowid = 0  # Track last processed database row (using rowid to avoid created_at format issues)

    # Execute initial events
    event_config = config.get("event_config", {})
    initial_posts = event_config.get("initial_posts", [])

    # Record round 0 start (initial events stage)
    if action_logger:
        action_logger.log_round_start(0, 0)  # round 0, simulated_hour 0

    initial_action_count = 0
    if initial_posts:
        initial_actions = {}
        for post in initial_posts:
            agent_id = post.get("poster_agent_id", 0)
            content = post.get("content", "")
            # Tag seeded content so downstream analysis can distinguish it
            tagged_content = f"[SEED] {content}"
            try:
                agent = result.env.agent_graph.get_agent(agent_id)
                if agent in initial_actions:
                    if not isinstance(initial_actions[agent], list):
                        initial_actions[agent] = [initial_actions[agent]]
                    initial_actions[agent].append(ManualAction(
                        action_type=ActionType.CREATE_POST,
                        action_args={"content": tagged_content}
                    ))
                else:
                    initial_actions[agent] = ManualAction(
                        action_type=ActionType.CREATE_POST,
                        action_args={"content": tagged_content}
                    )
                
                if action_logger:
                    action_logger.log_action(
                        round_num=0,
                        agent_id=agent_id,
                        agent_name=agent_names.get(agent_id, f"Agent_{agent_id}"),
                        action_type="CREATE_POST",
                        action_args={"content": tagged_content, "is_synthetic": True}
                    )
                    total_actions += 1
                    initial_action_count += 1
            except Exception:
                pass
        
        if initial_actions:
            await result.env.step(initial_actions)
            log_info(f"Published {len(initial_actions)} seeded posts (tagged [SEED])")

    # Record round 0 finish
    if action_logger:
        action_logger.log_round_end(0, initial_action_count)
    
    # Simulation parameters
    time_config = config.get("time_config", {})
    total_hours = time_config.get("total_simulation_hours", 72)
    minutes_per_round = time_config.get("minutes_per_round", 30)
    total_rounds = (total_hours * 60) // minutes_per_round

    # If max rounds limit specified, truncate
    if max_rounds is not None and max_rounds > 0:
        original_rounds = total_rounds
        total_rounds = min(total_rounds, max_rounds)
        if total_rounds < original_rounds:
            log_info(f"Rounds truncated: {original_rounds} -> {total_rounds} (max_rounds={max_rounds})")
    
    start_time = datetime.now()
    
    for round_num in range(total_rounds):
        # Check for shutdown signal
        if _shutdown_event and _shutdown_event.is_set():
            if main_logger:
                main_logger.info(f"Shutdown signal received, stopping simulation at round {round_num + 1}")
            break
        
        simulated_minutes = round_num * minutes_per_round
        simulated_hour = (simulated_minutes // 60) % 24
        simulated_day = simulated_minutes // (60 * 24) + 1
        
        active_agents = get_active_agents_for_round(
            result.env, config, simulated_hour, round_num
        )
        
        # Record round start regardless of active agent count
        if action_logger:
            action_logger.log_round_start(round_num + 1, simulated_hour)

        if not active_agents:
            # No active agents; record round finish with 0 actions
            if action_logger:
                action_logger.log_round_end(round_num + 1, 0)
            continue
        
        actions = {agent: LLMAction() for _, agent in active_agents}
        await result.env.step(actions)
        
        # Get new action records from database
        actual_actions, last_rowid = fetch_new_actions_from_db(
            db_path, last_rowid, agent_names
        )
        
        round_action_count = 0
        for action_data in actual_actions:
            if action_logger:
                action_logger.log_action(
                    round_num=round_num + 1,
                    agent_id=action_data['agent_id'],
                    agent_name=action_data['agent_name'],
                    action_type=action_data['action_type'],
                    action_args=action_data['action_args']
                )
                total_actions += 1
                round_action_count += 1
        
        if action_logger:
            action_logger.log_round_end(round_num + 1, round_action_count)
        
        if (round_num + 1) % 20 == 0:
            progress = (round_num + 1) / total_rounds * 100
            log_info(f"Day {simulated_day}, {simulated_hour:02d}:00 - Round {round_num + 1}/{total_rounds} ({progress:.1f}%)")
    
    # Note: do not close environment yet; it may be needed for interviews
    
    if action_logger:
        action_logger.log_simulation_end(total_rounds, total_actions)
    
    result.total_actions = total_actions
    elapsed = (datetime.now() - start_time).total_seconds()
    log_info(f"Simulation complete! Duration: {elapsed:.1f}s, total actions: {total_actions}")
    
    return result


async def main():
    parser = argparse.ArgumentParser(description='OASIS multi-platform simulation runner')
    parser.add_argument(
        '--config', 
        type=str, 
        required=True,
        help='Config filepath (simulation_config.json)'
    )
    parser.add_argument(
        '--twitter-only',
        action='store_true',
        help='Run Twitter simulation only'
    )
    parser.add_argument(
        '--reddit-only',
        action='store_true',
        help='Run Reddit simulation only'
    )
    parser.add_argument(
        '--max-rounds',
        type=int,
        default=None,
        help='Maximum simulation rounds (optional, truncates simulation)'
    )
    parser.add_argument(
        '--no-wait',
        action='store_true',
        default=False,
        help='Close environment immediately after simulation completes, skip command-wait mode'
    )
    
    args = parser.parse_args()
    
    # Create shutdown event at main function start
    global _shutdown_event
    _shutdown_event = asyncio.Event()
    
    if not os.path.exists(args.config):
        print(f"Error: Config file does not exist: {args.config}")
        sys.exit(1)
    
    config = load_config(args.config)
    simulation_dir = os.path.dirname(args.config) or "."
    wait_for_commands = not args.no_wait
    
    # Initialize logging config (suppress OASIS logs, clean up old files)
    init_logging_for_simulation(simulation_dir)
    
    # Create log manager
    log_manager = SimulationLogManager(simulation_dir)
    twitter_logger = log_manager.get_twitter_logger()
    reddit_logger = log_manager.get_reddit_logger()
    
    log_manager.info("=" * 60)
    log_manager.info("OASIS multi-platform simulation started")
    log_manager.info(f"Config file: {args.config}")
    log_manager.info(f"Simulation ID: {config.get('simulation_id', 'unknown')}")
    log_manager.info(f"  Wait mode: {'enabled' if wait_for_commands else 'disabled'}")
    log_manager.info("=" * 60)
    
    time_config = config.get("time_config", {})
    total_hours = time_config.get('total_simulation_hours', 72)
    minutes_per_round = time_config.get('minutes_per_round', 30)
    config_total_rounds = (total_hours * 60) // minutes_per_round
    
    log_manager.info(f"Simulation parameters:")
    log_manager.info(f"  - Total simulation hours: {total_hours}")
    log_manager.info(f"  - Minutes per round: {minutes_per_round}")
    log_manager.info(f"  - Total configured rounds: {config_total_rounds}")
    if args.max_rounds:
        log_manager.info(f"  - Max rounds limit: {args.max_rounds}")
        if args.max_rounds < config_total_rounds:
            log_manager.info(f"  - Actual rounds: {args.max_rounds} (truncated)")
    log_manager.info(f"  - Agent count: {len(config.get('agent_configs', []))}")

    log_manager.info("Log files:")
    log_manager.info(f"  - Main log: simulation.log")
    log_manager.info(f"  - Twitter: twitter/actions.jsonl")
    log_manager.info(f"  - Reddit: reddit/actions.jsonl")
    log_manager.info("=" * 60)
    
    start_time = datetime.now()
    
    # Store platform simulation results
    twitter_result: Optional[PlatformSimulation] = None
    reddit_result: Optional[PlatformSimulation] = None
    
    if args.twitter_only:
        twitter_result = await run_twitter_simulation(config, simulation_dir, twitter_logger, log_manager, args.max_rounds)
    elif args.reddit_only:
        reddit_result = await run_reddit_simulation(config, simulation_dir, reddit_logger, log_manager, args.max_rounds)
    else:
        # Run both platforms in parallel (each with its own action logger)
        results = await asyncio.gather(
            run_twitter_simulation(config, simulation_dir, twitter_logger, log_manager, args.max_rounds),
            run_reddit_simulation(config, simulation_dir, reddit_logger, log_manager, args.max_rounds),
        )
        twitter_result, reddit_result = results
    
    total_elapsed = (datetime.now() - start_time).total_seconds()
    log_manager.info("=" * 60)
    log_manager.info(f"Simulation complete! Duration: {total_elapsed:.1f} seconds")
    
    # Enter command-wait mode if enabled
    if wait_for_commands:
        log_manager.info("")
        log_manager.info("=" * 60)
        log_manager.info("Command-wait mode - environment is running")
        log_manager.info("Available commands: interview, batch_interview, close_env")
        log_manager.info("=" * 60)
        
        # Create IPC handler
        ipc_handler = ParallelIPCHandler(
            simulation_dir=simulation_dir,
            twitter_env=twitter_result.env if twitter_result else None,
            twitter_agent_graph=twitter_result.agent_graph if twitter_result else None,
            reddit_env=reddit_result.env if reddit_result else None,
            reddit_agent_graph=reddit_result.agent_graph if reddit_result else None
        )
        ipc_handler.update_status("alive")
        
        # Poll for commands until shutdown event is set
        try:
            while not _shutdown_event.is_set():
                should_continue = await ipc_handler.process_commands()
                if not should_continue:
                    break
                # Use wait_for instead of sleep so shutdown_event can interrupt
                try:
                    await asyncio.wait_for(_shutdown_event.wait(), timeout=0.5)
                    break  # Shutdown event received
                except asyncio.TimeoutError:
                    pass  # Timeout expired, continue polling
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received")
        except asyncio.CancelledError:
            print("\nTask cancelled")
        except Exception as e:
            print(f"\nCommand processing error: {type(e).__name__}")
        
        log_manager.info("\nClosing environment...")
        ipc_handler.update_status("stopped")

    # Close environments
    if twitter_result and twitter_result.env:
        await twitter_result.env.close()
        log_manager.info("[Twitter] Environment closed")

    if reddit_result and reddit_result.env:
        await reddit_result.env.close()
        log_manager.info("[Reddit] Environment closed")

    log_manager.info("=" * 60)
    log_manager.info(f"All tasks complete!")
    log_manager.info(f"Log files:")
    log_manager.info(f"  - {os.path.join(simulation_dir, 'simulation.log')}")
    log_manager.info(f"  - {os.path.join(simulation_dir, 'twitter', 'actions.jsonl')}")
    log_manager.info(f"  - {os.path.join(simulation_dir, 'reddit', 'actions.jsonl')}")
    log_manager.info("=" * 60)


def setup_signal_handlers(loop=None):
    """
    Set up signal handlers to ensure graceful shutdown on SIGTERM/SIGINT.

    In the simulation scenario, the simulation may complete but the interview
    environment is still running. Graceful shutdown requires:
    1. Signaling the asyncio event loop to stop
    2. Cleaning up resources (closing database connections, environments)
    3. Exiting the process
    """
    def signal_handler(signum, frame):
        global _cleanup_done
        sig_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        print(f"\nReceived {sig_name}, shutting down...")

        if not _cleanup_done:
            _cleanup_done = True
            # Set the shutdown event so the asyncio loop can clean up gracefully
            if _shutdown_event:
                _shutdown_event.set()

        # Do not call sys.exit() on first signal; let asyncio clean up.
        # On repeated signal, force exit.
        else:
            print("Forcing shutdown...")
            sys.exit(1)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    setup_signal_handlers()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received")
    except SystemExit:
        pass
    finally:
        # Clean up multiprocessing resources (prevent warning)
        try:
            from multiprocessing import resource_tracker
            resource_tracker._resource_tracker._stop()
        except Exception:
            pass
        print("Simulation process exited")
