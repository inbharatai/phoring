"""OASIS simulation runner.

Runs simulations in background processes and tracks per-agent actions,
round progress, and runtime state.
"""

import os
import sys
import json
import time
import threading
import subprocess
import signal
import atexit
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from..config import Config
from..utils.logger import get_logger
from.zep_graph_memory_updater import ZepGraphMemoryManager
from.simulation_ipc import SimulationIPCClient

logger = get_logger('phoring.simulation_runner')

# Whether cleanup hooks are already registered.
_cleanup_registered = False

# Platform check for subprocess handling.
IS_WINDOWS = sys.platform == 'win32'


class RunnerStatus(str, Enum):
    """Execution states for a running simulation process."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentAction:
    """Single agent action captured from simulation logs."""
    round_num: int
    timestamp: str
    platform: str # twitter / reddit
    agent_id: int
    agent_name: str
    action_type: str # CREATE_POST, LIKE_POST, etc.
    action_args: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_num": self.round_num,
            "timestamp": self.timestamp,
            "platform": self.platform,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "action_type": self.action_type,
            "action_args": self.action_args,
            "result": self.result,
            "success": self.success,
        }


@dataclass
class RoundSummary:
    """Aggregated action summary for one simulation round."""
    round_num: int
    start_time: str
    end_time: Optional[str] = None
    simulated_hour: int = 0
    twitter_actions: int = 0
    reddit_actions: int = 0
    active_agents: List[int] = field(default_factory=list)
    actions: List[AgentAction] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_num": self.round_num,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "simulated_hour": self.simulated_hour,
            "twitter_actions": self.twitter_actions,
            "reddit_actions": self.reddit_actions,
            "active_agents": self.active_agents,
            "actions_count": len(self.actions),
            "actions": [a.to_dict() for a in self.actions],
        }


@dataclass
class SimulationRunState:
    """Persistent runtime state for one simulation execution."""
    simulation_id: str
    runner_status: RunnerStatus = RunnerStatus.IDLE
    
    # Overall progress metrics.
    current_round: int = 0
    total_rounds: int = 0
    simulated_hours: int = 0
    total_simulation_hours: int = 0
    
    # Platform-specific round/time progress.
    twitter_current_round: int = 0
    reddit_current_round: int = 0
    twitter_simulated_hours: int = 0
    reddit_simulated_hours: int = 0
    
    # Platform runtime flags and action counters.
    twitter_running: bool = False
    reddit_running: bool = False
    twitter_actions_count: int = 0
    reddit_actions_count: int = 0
    
    # Completion flags inferred from end-of-simulation events.
    twitter_completed: bool = False
    reddit_completed: bool = False
    
    # Round-level summaries.
    rounds: List[RoundSummary] = field(default_factory=list)
    
    # Recent action feed for UI/API streaming.
    recent_actions: List[AgentAction] = field(default_factory=list)
    max_recent_actions: int = 50
    
    # Timestamps
    started_at: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    # Error detail for failed runs.
    error: Optional[str] = None
    
    # Subprocess ID for lifecycle control.
    process_pid: Optional[int] = None
    
    def add_action(self, action: AgentAction):
        """Add an action to the recent feed and update counters."""
        self.recent_actions.insert(0, action)
        if len(self.recent_actions) > self.max_recent_actions:
            self.recent_actions = self.recent_actions[:self.max_recent_actions]
        
        if action.platform == "twitter":
            self.twitter_actions_count += 1
        else:
            self.reddit_actions_count += 1
        
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "runner_status": self.runner_status.value,
            "current_round": self.current_round,
            "total_rounds": self.total_rounds,
            "simulated_hours": self.simulated_hours,
            "total_simulation_hours": self.total_simulation_hours,
            "progress_percent": round(self.current_round / max(self.total_rounds, 1) * 100, 1),
            # Platform-specific round and time info
            "twitter_current_round": self.twitter_current_round,
            "reddit_current_round": self.reddit_current_round,
            "twitter_simulated_hours": self.twitter_simulated_hours,
            "reddit_simulated_hours": self.reddit_simulated_hours,
            "twitter_running": self.twitter_running,
            "reddit_running": self.reddit_running,
            "twitter_completed": self.twitter_completed,
            "reddit_completed": self.reddit_completed,
            "twitter_actions_count": self.twitter_actions_count,
            "reddit_actions_count": self.reddit_actions_count,
            "total_actions_count": self.twitter_actions_count + self.reddit_actions_count,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "process_pid": self.process_pid,
        }
    
    def to_detail_dict(self) -> Dict[str, Any]:
        """Return base status plus recent actions and round count."""
        result = self.to_dict()
        result["recent_actions"] = [a.to_dict() for a in self.recent_actions]
        result["rounds_count"] = len(self.rounds)
        return result


class SimulationRunner:
    """Runtime controller for simulation execution.

    Responsibilities:
    1. Launch and monitor OASIS simulation subprocesses.
    2. Parse execution logs and persist per-agent actions.
    3. Expose queryable runtime status for APIs and UI.
    4. Handle pause/stop/resume lifecycle operations.
    """

    # Directory where runtime state snapshots are persisted.
    RUN_STATE_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../uploads/simulations'
    )

    # Directory containing scripts used to launch simulation runs.
    SCRIPTS_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../scripts'
    )

    # In-memory runtime state caches.
    _run_states: Dict[str, SimulationRunState] = {}
    _processes: Dict[str, subprocess.Popen] = {}
    _monitor_threads: Dict[str, threading.Thread] = {}
    _stdout_files: Dict[str, Any] = {}  # Open stdout handles for subprocesses.
    _stderr_files: Dict[str, Any] = {}  # Open stderr handles for subprocesses.

    # Whether graph memory updates are enabled per simulation.
    _graph_memory_enabled: Dict[str, bool] = {}  # simulation_id -> enabled
    
    @classmethod
    def recover_orphaned_simulations(cls):
        """Auto-restart simulations that were interrupted by a backend restart.

        On startup the subprocess references are lost, so any run_state.json
        with an active status represents a zombie simulation.  This scans
        every simulation directory, cleans up stale artifacts, and relaunches
        the simulation using the saved ``run_params.json``.

        If ``run_params.json`` is missing (old runs before this feature), the
        simulation is marked as failed instead.
        """
        sim_root = cls.RUN_STATE_DIR
        if not os.path.isdir(sim_root):
            return

        restarted = 0
        failed = 0
        now = datetime.now().isoformat()

        for sim_id in os.listdir(sim_root):
            sim_dir = os.path.join(sim_root, sim_id)
            if not os.path.isdir(sim_dir):
                continue

            # Check run_state.json for active status
            run_state_file = os.path.join(sim_dir, "run_state.json")
            if not os.path.isfile(run_state_file):
                continue

            try:
                with open(run_state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                status = data.get("runner_status", "idle")
                if status not in ("running", "starting"):
                    continue
            except Exception:
                continue

            # This simulation was interrupted.  Try to restart it.
            run_params_file = os.path.join(sim_dir, "run_params.json")
            config_file = os.path.join(sim_dir, "simulation_config.json")

            if os.path.isfile(run_params_file) and os.path.isfile(config_file):
                try:
                    with open(run_params_file, 'r', encoding='utf-8') as f:
                        params = json.load(f)

                    # Clean up stale run artifacts so start_simulation can proceed
                    cls.cleanup_simulation_logs(sim_id)

                    # Reset the preparation-level state to READY
                    state_file = os.path.join(sim_dir, "state.json")
                    if os.path.isfile(state_file):
                        with open(state_file, 'r', encoding='utf-8') as f:
                            sdata = json.load(f)
                        if sdata.get("status") == "running":
                            sdata["status"] = "ready"
                            sdata["updated_at"] = now
                            sdata["error"] = None
                            with open(state_file, 'w', encoding='utf-8') as f:
                                json.dump(sdata, f, ensure_ascii=False, indent=2)

                    # Relaunch
                    cls.start_simulation(
                        simulation_id=sim_id,
                        platform=params.get("platform", "parallel"),
                        max_rounds=params.get("max_rounds"),
                        enable_graph_memory_update=params.get("enable_graph_memory_update", False),
                        graph_id=params.get("graph_id"),
                    )

                    # Mark lifecycle state as running again
                    if os.path.isfile(state_file):
                        with open(state_file, 'r', encoding='utf-8') as f:
                            sdata = json.load(f)
                        sdata["status"] = "running"
                        sdata["updated_at"] = datetime.now().isoformat()
                        with open(state_file, 'w', encoding='utf-8') as f:
                            json.dump(sdata, f, ensure_ascii=False, indent=2)

                    restarted += 1
                    logger.info(f"Auto-restarted orphaned simulation {sim_id}")
                    continue

                except Exception as e:
                    logger.warning(f"Failed to restart simulation {sim_id}: {e}")
                    # Fall through to mark as failed

            # No run_params or restart failed — mark as failed
            cls._mark_simulation_failed(sim_dir, sim_id, run_state_file, now)
            failed += 1

        if restarted or failed:
            logger.info(
                f"Orphan recovery: {restarted} restarted, {failed} marked failed"
            )

    @classmethod
    def _mark_simulation_failed(cls, sim_dir, sim_id, run_state_file, now):
        """Mark a single orphaned simulation as failed on disk."""
        try:
            with open(run_state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data["runner_status"] = "failed"
            data["error"] = "Server restarted while simulation was running"
            data["completed_at"] = now
            data["updated_at"] = now
            data["twitter_running"] = False
            data["reddit_running"] = False
            with open(run_state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Could not mark run_state failed for {sim_id}: {e}")

        state_file = os.path.join(sim_dir, "state.json")
        if os.path.isfile(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get("status") == "running":
                    data["status"] = "failed"
                    data["error"] = "Server restarted while simulation was running"
                    data["updated_at"] = now
                    with open(state_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Could not mark state failed for {sim_id}: {e}")
        logger.info(f"Marked orphaned simulation {sim_id} as failed")

    @classmethod
    def get_run_state(cls, simulation_id: str) -> Optional[SimulationRunState]:
        """Return runtime state from cache or disk."""
        if simulation_id in cls._run_states:
            return cls._run_states[simulation_id]
        
        # Fallback to on-disk snapshot.
        state = cls._load_run_state(simulation_id)
        if state:
            cls._run_states[simulation_id] = state
        return state
    
    @classmethod
    def _load_run_state(cls, simulation_id: str) -> Optional[SimulationRunState]:
        """Load run state snapshot from disk."""
        state_file = os.path.join(cls.RUN_STATE_DIR, simulation_id, "run_state.json")
        if not os.path.exists(state_file):
            return None
        
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            state = SimulationRunState(
                simulation_id=simulation_id,
                runner_status=RunnerStatus(data.get("runner_status", "idle")),
                current_round=data.get("current_round", 0),
                total_rounds=data.get("total_rounds", 0),
                simulated_hours=data.get("simulated_hours", 0),
                total_simulation_hours=data.get("total_simulation_hours", 0),
                # Platform-specific round and time info
                twitter_current_round=data.get("twitter_current_round", 0),
                reddit_current_round=data.get("reddit_current_round", 0),
                twitter_simulated_hours=data.get("twitter_simulated_hours", 0),
                reddit_simulated_hours=data.get("reddit_simulated_hours", 0),
                twitter_running=data.get("twitter_running", False),
                reddit_running=data.get("reddit_running", False),
                twitter_completed=data.get("twitter_completed", False),
                reddit_completed=data.get("reddit_completed", False),
                twitter_actions_count=data.get("twitter_actions_count", 0),
                reddit_actions_count=data.get("reddit_actions_count", 0),
                started_at=data.get("started_at"),
                updated_at=data.get("updated_at", datetime.now().isoformat()),
                completed_at=data.get("completed_at"),
                error=data.get("error"),
                process_pid=data.get("process_pid"),
            )
            
            # Restore recent actions.
            actions_data = data.get("recent_actions", [])
            for a in actions_data:
                state.recent_actions.append(AgentAction(
                    round_num=a.get("round_num", 0),
                    timestamp=a.get("timestamp", ""),
                    platform=a.get("platform", ""),
                    agent_id=a.get("agent_id", 0),
                    agent_name=a.get("agent_name", ""),
                    action_type=a.get("action_type", ""),
                    action_args=a.get("action_args", {}),
                    result=a.get("result"),
                    success=a.get("success", True),
                ))
            
            return state
        except Exception as e:
            logger.error(f"Failed to load run state: {str(e)}")
            return None
    
    @classmethod
    def _save_run_state(cls, state: SimulationRunState):
        """Save run state to file."""
        sim_dir = os.path.join(cls.RUN_STATE_DIR, state.simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        state_file = os.path.join(sim_dir, "run_state.json")
        
        data = state.to_detail_dict()
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        cls._run_states[state.simulation_id] = state
    
    @classmethod
    def start_simulation(
        cls,
        simulation_id: str,
        platform: str = "parallel",  # twitter / reddit / parallel
        max_rounds: int = None,  # Optional round cap
        enable_graph_memory_update: bool = False,  # Enable Zep graph memory updates
        graph_id: str = None  # Zep graph ID
    ) -> SimulationRunState:
        """Start a simulation subprocess and initialize runtime state.

        Args:
            simulation_id: Simulation ID.
            platform: Target platform mode (twitter/reddit/parallel).
            max_rounds: Optional cap to shorten simulation duration.
            enable_graph_memory_update: Whether to write events back to Zep.
            graph_id: Graph ID required when graph memory update is enabled.

        Returns:
            Initialized runtime state.
        """
        # Reject duplicate active runs.
        existing = cls.get_run_state(simulation_id)
        if existing and existing.runner_status in [RunnerStatus.RUNNING, RunnerStatus.STARTING]:
            raise ValueError(f"Simulation is already running: {simulation_id}")
        
        # Load simulation configuration
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            raise ValueError("Simulation configuration not found; call /prepare first")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Initialize run state
        time_config = config.get("time_config", {})
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 30)
        total_rounds = int(total_hours * 60 / minutes_per_round)
        
        # If max rounds limit is set, truncate
        if max_rounds is not None and max_rounds > 0:
            original_rounds = total_rounds
            total_rounds = min(total_rounds, max_rounds)
            if total_rounds < original_rounds:
                logger.info(f"Rounds truncated: {original_rounds} -> {total_rounds} (max_rounds={max_rounds})")
        
        state = SimulationRunState(
            simulation_id=simulation_id,
            runner_status=RunnerStatus.STARTING,
            total_rounds=total_rounds,
            total_simulation_hours=total_hours,
            started_at=datetime.now().isoformat(),
        )
        
        cls._save_run_state(state)
        
        # Persist launch params so the simulation can be auto-restarted after
        # an unexpected backend restart (OOM, deploy, etc.).
        run_params = {
            "platform": platform,
            "max_rounds": max_rounds,
            "enable_graph_memory_update": enable_graph_memory_update,
            "graph_id": graph_id,
        }
        run_params_path = os.path.join(sim_dir, "run_params.json")
        with open(run_params_path, 'w', encoding='utf-8') as f:
            json.dump(run_params, f, ensure_ascii=False, indent=2)
        
        # If graph update is enabled, create the updater
        if enable_graph_memory_update:
            if not graph_id:
                raise ValueError("Graph memory update requires graph_id")
            
            try:
                ZepGraphMemoryManager.create_updater(simulation_id, graph_id)
                cls._graph_memory_enabled[simulation_id] = True
                logger.info(f"Graph memory updater enabled: simulation_id={simulation_id}, graph_id={graph_id}")
            except Exception as e:
                logger.error(f"Failed to create graph memory updater: {e}")
                cls._graph_memory_enabled[simulation_id] = False
        else:
            cls._graph_memory_enabled[simulation_id] = False
        
        # Select run script (from backend/scripts/ directory)
        if platform == "twitter":
            script_name = "run_twitter_simulation.py"
            state.twitter_running = True
        elif platform == "reddit":
            script_name = "run_reddit_simulation.py"
            state.reddit_running = True
        else:
            script_name = "run_parallel_simulation.py"
            state.twitter_running = True
            state.reddit_running = True
        
        script_path = os.path.join(cls.SCRIPTS_DIR, script_name)
        
        if not os.path.exists(script_path):
            raise ValueError(f"Script does not exist: {script_path}")
        
        # Start simulation subprocess
        try:
            # Build command with full paths
            # Log file layout:
            # twitter/actions.jsonl - Twitter action log
            # reddit/actions.jsonl - Reddit action log
            # simulation.log - Main process log
            
            cmd = [
                sys.executable, # Python interpreter
                script_path,
                "--config", config_path, # Full config file path
            ]
            
            # If max rounds limit is set, add runtime parameters
            if max_rounds is not None and max_rounds > 0:
                cmd.extend(["--max-rounds", str(max_rounds)])
            
            # Create log file to capture stdout/stderr from subprocess
            main_log_path = os.path.join(sim_dir, "simulation.log")
            main_log_file = open(main_log_path, 'w', encoding='utf-8')
            
            # Set process environment variables, ensure Windows UTF-8 encoding
            # (prevents OASIS file read encoding issues)
            env = os.environ.copy()
            env['PYTHONUTF8'] = '1'  # Python 3.7+: all open() defaults to UTF-8
            env['PYTHONIOENCODING'] = 'utf-8'  # Ensure stdout/stderr use UTF-8
            
            # Set working directory to simulation directory (for database file generation)
            # start_new_session=True creates new process group, enabling os.killpg to terminate all child processes
            process = subprocess.Popen(
                cmd,
                cwd=sim_dir,
                stdout=main_log_file,
                stderr=subprocess.STDOUT, # Merge stderr into log file
                text=True,
                encoding='utf-8', # Explicit encoding
                bufsize=1,
                env=env, # UTF-8 environment variables
                start_new_session=True, # New process group, ensures clean shutdown of all child processes
            )
            
            # Save file handles for cleanup
            cls._stdout_files[simulation_id] = main_log_file
            cls._stderr_files[simulation_id] = None # stderr merged into stdout
            
            state.process_pid = process.pid
            state.runner_status = RunnerStatus.RUNNING
            cls._processes[simulation_id] = process
            cls._save_run_state(state)
            
            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=cls._monitor_simulation,
                args=(simulation_id,),
                daemon=True
            )
            monitor_thread.start()
            cls._monitor_threads[simulation_id] = monitor_thread
            
            logger.info(f"Simulation started successfully: {simulation_id}, pid={process.pid}, platform={platform}")
            
        except Exception as e:
            # Close leaked log file handle if Popen failed after opening it.
            if 'main_log_file' in locals() and main_log_file and not main_log_file.closed:
                main_log_file.close()
            state.runner_status = RunnerStatus.FAILED
            state.error = str(e)
            cls._save_run_state(state)
            raise

        return state
    
    @classmethod
    def _monitor_simulation(cls, simulation_id: str):
        """Monitor the simulation process and parse action logs."""
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        
        # Platform-specific action log paths
        twitter_actions_log = os.path.join(sim_dir, "twitter", "actions.jsonl")
        reddit_actions_log = os.path.join(sim_dir, "reddit", "actions.jsonl")
        
        process = cls._processes.get(simulation_id)
        state = cls.get_run_state(simulation_id)
        
        if not process or not state:
            return
        
        twitter_position = 0
        reddit_position = 0
        
        # Heartbeat: adaptive stall timeout based on simulation complexity.
        # Larger simulations with more agents need more time per round.
        agent_count = 0
        try:
            config_path = os.path.join(sim_dir, "simulation_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    sim_config = json.load(f)
                agent_count = len(sim_config.get("agent_configs", []))
        except Exception:
            pass
        # Base: 15 min, +30s per agent, capped at 45 min
        STALL_TIMEOUT_SECONDS = min(2700, max(900, 900 + agent_count * 30))
        last_activity_time = time.monotonic()
        
        try:
            while process.poll() is None: # While process is running
                activity_detected = False
                
                # Read Twitter action log
                if os.path.exists(twitter_actions_log):
                    old_pos = twitter_position
                    twitter_position = cls._read_action_log(
                        twitter_actions_log, twitter_position, state, "twitter"
                    )
                    if twitter_position > old_pos:
                        activity_detected = True
                
                # Read Reddit action log
                if os.path.exists(reddit_actions_log):
                    old_pos = reddit_position
                    reddit_position = cls._read_action_log(
                        reddit_actions_log, reddit_position, state, "reddit"
                    )
                    if reddit_position > old_pos:
                        activity_detected = True
                
                if activity_detected:
                    last_activity_time = time.monotonic()
                
                # Check for stalled process
                idle_seconds = time.monotonic() - last_activity_time
                if idle_seconds > STALL_TIMEOUT_SECONDS:
                    logger.warning(
                        f"Simulation {simulation_id} stalled: no activity for "
                        f"{idle_seconds:.0f}s (threshold: {STALL_TIMEOUT_SECONDS}s). "
                        f"Terminating process."
                    )
                    try:
                        if IS_WINDOWS:
                            process.terminate()
                        else:
                            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    except Exception as kill_err:
                        logger.error(f"Failed to kill stalled process: {kill_err}")
                    state.runner_status = RunnerStatus.FAILED
                    state.error = f"Process stalled: no activity for {STALL_TIMEOUT_SECONDS}s"
                    cls._save_run_state(state)
                    break
                
                # Update status
                cls._save_run_state(state)
                time.sleep(2)
            
            # Process finished, do final log read
            if os.path.exists(twitter_actions_log):
                cls._read_action_log(twitter_actions_log, twitter_position, state, "twitter")
            if os.path.exists(reddit_actions_log):
                cls._read_action_log(reddit_actions_log, reddit_position, state, "reddit")
            
            # Check process exit status
            exit_code = process.returncode
            
            if exit_code == 0:
                state.runner_status = RunnerStatus.COMPLETED
                state.completed_at = datetime.now().isoformat()
                logger.info(f"Simulation completed: {simulation_id}")
            else:
                state.runner_status = RunnerStatus.FAILED
                # Read error info from log file
                main_log_path = os.path.join(sim_dir, "simulation.log")
                error_info = ""
                try:
                    if os.path.exists(main_log_path):
                        with open(main_log_path, 'r', encoding='utf-8') as f:
                            error_info = f.read()[-2000:] # Last 2000 characters
                except Exception:
                    pass
                state.error = f"Process exited with code: {exit_code}, error: {error_info}"
                logger.error(f"Simulation failed: {simulation_id}, error={state.error}")
            
            state.twitter_running = False
            state.reddit_running = False
            cls._save_run_state(state)
            
        except Exception as e:
            logger.error(f"Monitor thread error: {simulation_id}, error={str(e)}")
            state.runner_status = RunnerStatus.FAILED
            state.error = "Internal monitoring error"
            cls._save_run_state(state)
        
        finally:
            # Stop graph memory updater
            if cls._graph_memory_enabled.get(simulation_id, False):
                try:
                    ZepGraphMemoryManager.stop_updater(simulation_id)
                    logger.info(f"Stopped graph memory updater: simulation_id={simulation_id}")
                except Exception as e:
                    logger.error(f"Failed to stop graph memory updater: {e}")
                cls._graph_memory_enabled.pop(simulation_id, None)
            
            # Clean up process references
            cls._processes.pop(simulation_id, None)
            # Close log file handles
            if simulation_id in cls._stdout_files:
                try:
                    cls._stdout_files[simulation_id].close()
                except Exception:
                    pass
                cls._stdout_files.pop(simulation_id, None)
            if simulation_id in cls._stderr_files and cls._stderr_files[simulation_id]:
                try:
                    cls._stderr_files[simulation_id].close()
                except Exception:
                    pass
                cls._stderr_files.pop(simulation_id, None)
    
    @classmethod
    def _read_action_log(
        cls,
        log_path: str,
        position: int,
        state: SimulationRunState,
        platform: str
    ) -> int:
        """Read new entries from an action log file.

        Args:
            log_path: Path to the action log file.
            position: Current read position (byte offset).
            state: Runtime state object to update.
            platform: Platform identifier (twitter/reddit).

        Returns:
            New read position (byte offset).
        """
        # Check whether graph memory update is enabled
        graph_memory_enabled = cls._graph_memory_enabled.get(state.simulation_id, False)
        graph_updater = None
        if graph_memory_enabled:
            graph_updater = ZepGraphMemoryManager.get_updater(state.simulation_id)
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                f.seek(position)
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            action_data = json.loads(line)
                            
                            # Process event types emitted by simulation runners.
                            if "event_type" in action_data:
                                event_type = action_data.get("event_type")

                                # Mark platform completion when simulation_end arrives.
                                if event_type == "simulation_end":
                                    if platform == "twitter":
                                        state.twitter_completed = True
                                        state.twitter_running = False
                                        logger.info(
                                            f"Twitter simulation completed: {state.simulation_id}, "
                                            f"total_rounds={action_data.get('total_rounds')}, "
                                            f"total_actions={action_data.get('total_actions')}"
                                        )
                                    elif platform == "reddit":
                                        state.reddit_completed = True
                                        state.reddit_running = False
                                        logger.info(
                                            f"Reddit simulation completed: {state.simulation_id}, "
                                            f"total_rounds={action_data.get('total_rounds')}, "
                                            f"total_actions={action_data.get('total_actions')}"
                                        )

                                    # If all enabled platforms completed, mark run completed.
                                    all_completed = cls._check_all_platforms_completed(state)
                                    if all_completed:
                                        state.runner_status = RunnerStatus.COMPLETED
                                        state.completed_at = datetime.now().isoformat()
                                        logger.info(f"All platform simulations completed: {state.simulation_id}")
                                
                                # Update round progress from round_end events.
                                elif event_type == "round_end":
                                    round_num = action_data.get("round", 0)
                                    simulated_hours = action_data.get("simulated_hours", 0)
                                    
                                    # Update platform-specific round/time counters.
                                    if platform == "twitter":
                                        if round_num > state.twitter_current_round:
                                            state.twitter_current_round = round_num
                                        state.twitter_simulated_hours = simulated_hours
                                    elif platform == "reddit":
                                        if round_num > state.reddit_current_round:
                                            state.reddit_current_round = round_num
                                        state.reddit_simulated_hours = simulated_hours
                                    
                                    # Overall round is the max across platforms
                                    if round_num > state.current_round:
                                        state.current_round = round_num
                                    # Overall simulated hours is the max across platforms
                                    state.simulated_hours = max(state.twitter_simulated_hours, state.reddit_simulated_hours)
                                
                                continue
                            
                            action = AgentAction(
                                round_num=action_data.get("round", 0),
                                timestamp=action_data.get("timestamp", datetime.now().isoformat()),
                                platform=platform,
                                agent_id=action_data.get("agent_id", 0),
                                agent_name=action_data.get("agent_name", ""),
                                action_type=action_data.get("action_type", ""),
                                action_args=action_data.get("action_args", {}),
                                result=action_data.get("result"),
                                success=action_data.get("success", True),
                            )
                            state.add_action(action)
                            
                            # Update current round
                            if action.round_num and action.round_num > state.current_round:
                                state.current_round = action.round_num
                            
                            # If graph memory update is enabled, send to Zep
                            if graph_updater:
                                graph_updater.add_activity_from_dict(action_data, platform)
                            
                        except json.JSONDecodeError:
                            pass
                return f.tell()
        except Exception as e:
            logger.warning(f"Failed to read action log: {log_path}, error={e}")
            return position
    
    @classmethod
    def _check_all_platforms_completed(cls, state: SimulationRunState) -> bool:
        """Return whether all enabled platforms have finished simulation."""
        sim_dir = os.path.join(cls.RUN_STATE_DIR, state.simulation_id)
        twitter_log = os.path.join(sim_dir, "twitter", "actions.jsonl")
        reddit_log = os.path.join(sim_dir, "reddit", "actions.jsonl")
        
        # Enabled platform detection is inferred from action log presence.
        twitter_enabled = os.path.exists(twitter_log)
        reddit_enabled = os.path.exists(reddit_log)
        
        # Any enabled platform without completion should keep run active.
        if twitter_enabled and not state.twitter_completed:
            return False
        if reddit_enabled and not state.reddit_completed:
            return False
        
        # At least one enabled platform exists and all enabled ones are complete.
        return twitter_enabled or reddit_enabled
    
    @classmethod
    def _terminate_process(cls, process: subprocess.Popen, simulation_id: str, timeout: int = 10):
        """Terminate subprocess tree safely across platforms."""
        if IS_WINDOWS:
            # Windows: taskkill /T terminates child processes as well.
            logger.info(f"Terminating process on Windows: simulation={simulation_id}, pid={process.pid}")
            try:
                subprocess.run(
                    ['taskkill', '/PID', str(process.pid), '/T'],
                    capture_output=True,
                    timeout=5
                )
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Process still alive after graceful terminate: {simulation_id}")
                    subprocess.run(
                        ['taskkill', '/F', '/PID', str(process.pid), '/T'],
                        capture_output=True,
                        timeout=5
                    )
                    process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"taskkill failed, terminate: {e}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        else:
            # Unix: terminate process group created with start_new_session=True.
            pgid = os.getpgid(process.pid)
            logger.info(f"Terminating process group on Unix: simulation={simulation_id}, pgid={pgid}")
            
            # First attempt graceful shutdown.
            os.killpg(pgid, signal.SIGTERM)
            
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Escalate when graceful termination times out.
                logger.warning(f"Process group did not exit after SIGTERM: {simulation_id}")
                os.killpg(pgid, signal.SIGKILL)
                process.wait(timeout=5)
    
    @classmethod
    def stop_simulation(cls, simulation_id: str) -> SimulationRunState:
        """Stop a running simulation and persist stopped state."""
        state = cls.get_run_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation does not exist: {simulation_id}")
        
        if state.runner_status not in [RunnerStatus.RUNNING, RunnerStatus.PAUSED]:
            raise ValueError(f"Simulation is not running: {simulation_id}, status={state.runner_status}")
        
        state.runner_status = RunnerStatus.STOPPING
        cls._save_run_state(state)
        
        # Stop subprocess if it is still running.
        process = cls._processes.get(simulation_id)
        if process and process.poll() is None:
            try:
                cls._terminate_process(process, simulation_id)
            except ProcessLookupError:
                # Process already exited.
                pass
            except Exception as e:
                logger.error(f"Failed to stop process for simulation={simulation_id}, error={e}")
                # Fallback hard stop.
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception:
                    process.kill()
        
        state.runner_status = RunnerStatus.STOPPED
        state.twitter_running = False
        state.reddit_running = False
        state.completed_at = datetime.now().isoformat()
        cls._save_run_state(state)
        
        # Stop graph-memory updater if enabled.
        if cls._graph_memory_enabled.get(simulation_id, False):
            try:
                ZepGraphMemoryManager.stop_updater(simulation_id)
                logger.info(f"Graph memory updater stopped: simulation_id={simulation_id}")
            except Exception as e:
                logger.error(f"Failed to stop graph memory updater: {e}")
            cls._graph_memory_enabled.pop(simulation_id, None)
        
        logger.info(f"Simulation stopped: {simulation_id}")
        return state
    
    @classmethod
    def _read_actions_from_file(
        cls,
        file_path: str,
        default_platform: Optional[str] = None,
        platform_filter: Optional[str] = None,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None
    ) -> List[AgentAction]:
        """Read and filter action records from a JSONL file.

        Args:
            file_path: Path to the action log file.
            default_platform: Default platform when a record lacks a platform field.
            platform_filter: Only return actions from this platform.
            agent_id: Only return actions from this agent ID.
            round_num: Only return actions from this round number.
        """
        if not os.path.exists(file_path):
            return []
        
        actions = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # Skip event records (simulation_start, round_start, round_end)
                    if "event_type" in data:
                        continue

                    # Skip records without agent_id (not agent actions)
                    if "agent_id" not in data:
                        continue

                    # Get platform: use record's platform field, otherwise fall back to default
                    record_platform = data.get("platform") or default_platform or ""

                    # Apply filters
                    if platform_filter and record_platform != platform_filter:
                        continue
                    if agent_id is not None and data.get("agent_id")!= agent_id:
                        continue
                    if round_num is not None and data.get("round")!= round_num:
                        continue
                    
                    actions.append(AgentAction(
                        round_num=data.get("round", 0),
                        timestamp=data.get("timestamp", ""),
                        platform=record_platform,
                        agent_id=data.get("agent_id", 0),
                        agent_name=data.get("agent_name", ""),
                        action_type=data.get("action_type", ""),
                        action_args=data.get("action_args", {}),
                        result=data.get("result"),
                        success=data.get("success", True),
                    ))
                    
                except json.JSONDecodeError:
                    continue
        
        return actions
    
    @classmethod
    def get_all_actions(
        cls,
        simulation_id: str,
        platform: Optional[str] = None,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None
    ) -> List[AgentAction]:
        """Get all actions across all platforms (complete history).

        Args:
            simulation_id: Simulation ID.
            platform: Filter by platform (twitter/reddit).
            agent_id: Filter by agent ID.
            round_num: Filter by round number.

        Returns:
            Complete action list sorted by timestamp (newest first).
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        actions = []
        
        # Read Twitter action file (file path auto-sets platform to twitter)
        twitter_actions_log = os.path.join(sim_dir, "twitter", "actions.jsonl")
        if not platform or platform == "twitter":
            actions.extend(cls._read_actions_from_file(
                twitter_actions_log,
                default_platform="twitter",  # auto-fill platform field
                platform_filter=platform,
                agent_id=agent_id,
                round_num=round_num
            ))

        # Read Reddit action file (file path auto-sets platform to reddit)
        reddit_actions_log = os.path.join(sim_dir, "reddit", "actions.jsonl")
        if not platform or platform == "reddit":
            actions.extend(cls._read_actions_from_file(
                reddit_actions_log,
                default_platform="reddit",  # auto-fill platform field
                platform_filter=platform,
                agent_id=agent_id,
                round_num=round_num
            ))

        # If no platform-specific files exist, fall back to legacy single-file format
        if not actions:
            actions_log = os.path.join(sim_dir, "actions.jsonl")
            actions = cls._read_actions_from_file(
                actions_log,
                default_platform=None,  # legacy format includes platform field
                platform_filter=platform,
                agent_id=agent_id,
                round_num=round_num
            )

        # Sort by timestamp (newest first)
        actions.sort(key=lambda x: x.timestamp, reverse=True)
        
        return actions
    
    @classmethod
    def get_actions(
        cls,
        simulation_id: str,
        limit: int = 100,
        offset: int = 0,
        platform: Optional[str] = None,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None
    ) -> List[AgentAction]:
        """Get paginated actions with optional filters.

        Args:
            simulation_id: Simulation ID.
            limit: Maximum number of actions to return.
            offset: Number of actions to skip before returning.
            platform: Filter by platform.
            agent_id: Filter by agent ID.
            round_num: Filter by round number.

        Returns:
            Paginated action list.
        """
        actions = cls.get_all_actions(
            simulation_id=simulation_id,
            platform=platform,
            agent_id=agent_id,
            round_num=round_num
        )
        
        # Apply pagination
        return actions[offset:offset + limit]
    
    @classmethod
    def get_timeline(
        cls,
        simulation_id: str,
        start_round: int = 0,
        end_round: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get simulation timeline grouped by round.

        Args:
            simulation_id: Simulation ID.
            start_round: Starting round number.
            end_round: Ending round number (inclusive).

        Returns:
            List of per-round summary dictionaries.
        """
        actions = cls.get_actions(simulation_id, limit=10000)
        
        # Group actions by round
        rounds: Dict[int, Dict[str, Any]] = {}
        
        for action in actions:
            round_num = action.round_num
            
            if round_num < start_round:
                continue
            if end_round is not None and round_num > end_round:
                continue
            
            if round_num not in rounds:
                rounds[round_num] = {
                    "round_num": round_num,
                    "twitter_actions": 0,
                    "reddit_actions": 0,
                    "active_agents": set(),
                    "action_types": {},
                    "first_action_time": action.timestamp,
                    "last_action_time": action.timestamp,
                }
            
            r = rounds[round_num]
            
            if action.platform == "twitter":
                r["twitter_actions"] += 1
            else:
                r["reddit_actions"] += 1
            
            r["active_agents"].add(action.agent_id)
            r["action_types"][action.action_type] = r["action_types"].get(action.action_type, 0) + 1
            r["last_action_time"] = action.timestamp
        
        # Convert to sorted list
        result = []
        for round_num in sorted(rounds.keys()):
            r = rounds[round_num]
            result.append({
                "round_num": round_num,
                "twitter_actions": r["twitter_actions"],
                "reddit_actions": r["reddit_actions"],
                "total_actions": r["twitter_actions"] + r["reddit_actions"],
                "active_agents_count": len(r["active_agents"]),
                "active_agents": list(r["active_agents"]),
                "action_types": r["action_types"],
                "first_action_time": r["first_action_time"],
                "last_action_time": r["last_action_time"],
            })
        
        return result
    
    @classmethod
    def get_agent_stats(cls, simulation_id: str) -> List[Dict[str, Any]]:
        """Get per-agent statistics for a simulation.

        Returns:
            List of agent stats sorted by total actions (descending).
        """
        actions = cls.get_actions(simulation_id, limit=10000)
        
        agent_stats: Dict[int, Dict[str, Any]] = {}
        
        for action in actions:
            agent_id = action.agent_id
            
            if agent_id not in agent_stats:
                agent_stats[agent_id] = {
                    "agent_id": agent_id,
                    "agent_name": action.agent_name,
                    "total_actions": 0,
                    "twitter_actions": 0,
                    "reddit_actions": 0,
                    "action_types": {},
                    "first_action_time": action.timestamp,
                    "last_action_time": action.timestamp,
                }
            
            stats = agent_stats[agent_id]
            stats["total_actions"] += 1
            
            if action.platform == "twitter":
                stats["twitter_actions"] += 1
            else:
                stats["reddit_actions"] += 1
            
            stats["action_types"][action.action_type] = stats["action_types"].get(action.action_type, 0) + 1
            stats["last_action_time"] = action.timestamp
        
        # Sort by total actions descending
        result = sorted(agent_stats.values(), key=lambda x: x["total_actions"], reverse=True)
        
        return result
    
    @classmethod
    def cleanup_simulation_logs(cls, simulation_id: str) -> Dict[str, Any]:
        """Clean up simulation runtime logs (before restarting a simulation).

        Deletes:
        - run_state.json
        - twitter/actions.jsonl
        - reddit/actions.jsonl
        - simulation.log
        - stdout.log / stderr.log
        - twitter_simulation.db (simulation database)
        - reddit_simulation.db (simulation database)
        - env_status.json (environment status)

        Note: Does NOT delete config files (simulation_config.json) or profile files.

        Args:
            simulation_id: Simulation ID.

        Returns:
            Cleanup result info.
        """
        import shutil
        
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        
        if not os.path.exists(sim_dir):
            return {"success": True, "message": "Simulation directory does not exist; nothing to clean up"}
        
        cleaned_files = []
        errors = []
        
        # Files to delete (including database files)
        files_to_delete = [
            "run_state.json",
            "simulation.log",
            "stdout.log",
            "stderr.log",
            "twitter_simulation.db",  # Twitter platform database
            "reddit_simulation.db",  # Reddit platform database
            "env_status.json",  # Environment status file
        ]

        # Directories containing action logs to clean
        dirs_to_clean = ["twitter", "reddit"]

        # Delete files
        for filename in files_to_delete:
            file_path = os.path.join(sim_dir, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    cleaned_files.append(filename)
                except Exception as e:
                    errors.append(f"Failed to delete {filename}: {str(e)}")
        
        # Clean up platform directory action logs
        for dir_name in dirs_to_clean:
            dir_path = os.path.join(sim_dir, dir_name)
            if os.path.exists(dir_path):
                actions_file = os.path.join(dir_path, "actions.jsonl")
                if os.path.exists(actions_file):
                    try:
                        os.remove(actions_file)
                        cleaned_files.append(f"{dir_name}/actions.jsonl")
                    except Exception as e:
                        errors.append(f"Failed to delete {dir_name}/actions.jsonl: {str(e)}")
        
        # Clean up in-memory run state
        if simulation_id in cls._run_states:
            del cls._run_states[simulation_id]

        logger.info(f"Simulation log cleanup complete: {simulation_id}, deleted files: {cleaned_files}")
        
        return {
            "success": len(errors) == 0,
            "cleaned_files": cleaned_files,
            "errors": errors if errors else None
        }
    
    # Prevent duplicate cleanup
    _cleanup_done = False

    @classmethod
    def cleanup_all_simulations(cls):
        """Clean up all running simulation processes.

        Called on service shutdown to ensure all child processes are terminated.
        """
        # Prevent duplicate cleanup
        if cls._cleanup_done:
            return
        cls._cleanup_done = True
        
        # Check whether there is anything to clean up (avoid logging when there is nothing to do)
        has_processes = bool(cls._processes)
        has_updaters = bool(cls._graph_memory_enabled)

        if not has_processes and not has_updaters:
            return  # Nothing to clean up

        logger.info("Cleaning up all simulation processes...")

        # Stop all graph memory updaters
        try:
            ZepGraphMemoryManager.stop_all()
        except Exception as e:
            logger.error(f"Failed to stop graph memory updaters: {e}")
        cls._graph_memory_enabled.clear()

        # Copy process list to avoid modification during iteration
        processes = list(cls._processes.items())
        
        for simulation_id, process in processes:
            try:
                if process.poll() is None:  # Process still running
                    logger.info(f"Terminating simulation process: {simulation_id}, pid={process.pid}")

                    try:
                        # Use platform-specific process termination method
                        cls._terminate_process(process, simulation_id, timeout=5)
                    except (ProcessLookupError, OSError):
                        # Process already exited; try direct terminate as fallback
                        try:
                            process.terminate()
                            process.wait(timeout=3)
                        except Exception:
                            process.kill()
                    
                    # Update run_state.json
                    state = cls.get_run_state(simulation_id)
                    if state:
                        state.runner_status = RunnerStatus.STOPPED
                        state.twitter_running = False
                        state.reddit_running = False
                        state.completed_at = datetime.now().isoformat()
                        state.error = "Service shutdown: simulation terminated"
                        cls._save_run_state(state)
                    
                    # Update state.json to stopped status
                    try:
                        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
                        state_file = os.path.join(sim_dir, "state.json")
                        logger.info(f"Updating state.json: {state_file}")
                        if os.path.exists(state_file):
                            with open(state_file, 'r', encoding='utf-8') as f:
                                state_data = json.load(f)
                            state_data['status'] = 'stopped'
                            state_data['updated_at'] = datetime.now().isoformat()
                            with open(state_file, 'w', encoding='utf-8') as f:
                                json.dump(state_data, f, indent=2, ensure_ascii=False)
                            logger.info(f"Updated state.json status to stopped: {simulation_id}")
                        else:
                            logger.warning(f"state.json does not exist: {state_file}")
                    except Exception as state_err:
                        logger.warning(f"Failed to update state.json: {simulation_id}, error={state_err}")
                        
            except Exception as e:
                logger.error(f"Failed to clean up process: {simulation_id}, error={e}")

        # Close file handles
        for simulation_id, file_handle in list(cls._stdout_files.items()):
            try:
                if file_handle:
                    file_handle.close()
            except Exception:
                pass
        cls._stdout_files.clear()
        
        for simulation_id, file_handle in list(cls._stderr_files.items()):
            try:
                if file_handle:
                    file_handle.close()
            except Exception:
                pass
        cls._stderr_files.clear()
        
        # Clear in-memory state
        cls._processes.clear()
        logger.info("Simulation process cleanup complete")
    
    @classmethod
    def register_cleanup(cls):
        """Register cleanup handlers for graceful shutdown.

        Called during Flask initialization to ensure all simulation processes
        are terminated when the service shuts down.
        """
        global _cleanup_registered
        
        if _cleanup_registered:
            return
        
        # In Flask debug mode, only register cleanup on the reloader child process
        # (WERKZEUG_RUN_MAIN=true), not on the main reloader process.
        is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
        is_debug_mode = os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('WERKZEUG_RUN_MAIN') is not None

        # In debug mode, skip registration for the parent reloader process
        if is_debug_mode and not is_reloader_process:
            _cleanup_registered = True  # Mark as registered to prevent duplicate registration
            return
        
        # Save original signal handlers
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)
        # SIGHUP only exists on Unix (macOS/Linux), not on Windows
        original_sighup = None
        has_sighup = hasattr(signal, 'SIGHUP')
        if has_sighup:
            original_sighup = signal.getsignal(signal.SIGHUP)
        
        def cleanup_handler(signum=None, frame=None):
            """Signal handler: clean up simulation processes, then call original handler."""
            # Only log if there are processes to clean up
            if cls._processes or cls._graph_memory_enabled:
                logger.info(f"Received signal {signum}, starting cleanup...")
            cls.cleanup_all_simulations()

            # Call original handler to allow Flask to shut down properly
            if signum == signal.SIGINT and callable(original_sigint):
                original_sigint(signum, frame)
            elif signum == signal.SIGTERM and callable(original_sigterm):
                original_sigterm(signum, frame)
            elif has_sighup and signum == signal.SIGHUP:
                # SIGHUP: terminal hangup
                if callable(original_sighup):
                    original_sighup(signum, frame)
                else:
                    # Default behavior: exit
                    sys.exit(0)
            else:
                # If no original handler is callable (SIG_DFL), use default behavior
                raise KeyboardInterrupt

        # Register atexit handler (always runs on normal exit)
        atexit.register(cls.cleanup_all_simulations)

        # Register signal handlers (may fail if called from a non-main thread)
        try:
            # SIGTERM: default kill signal
            signal.signal(signal.SIGTERM, cleanup_handler)
            # SIGINT: Ctrl+C
            signal.signal(signal.SIGINT, cleanup_handler)
            # SIGHUP: terminal hangup (Unix only)
            if has_sighup:
                signal.signal(signal.SIGHUP, cleanup_handler)
        except ValueError:
            # Signal handlers can only be set in the main thread; fall back to atexit
            logger.warning("Cannot set signal handlers (not main thread); relying on atexit")
        
        _cleanup_registered = True
    
    @classmethod
    def get_running_simulations(cls) -> List[str]:
        """Get all currently running simulation IDs."""
        running = []
        for sim_id, process in cls._processes.items():
            if process.poll() is None:
                running.append(sim_id)
        return running
    
    # ============== Interview ==============

    @classmethod
    def check_env_alive(cls, simulation_id: str) -> bool:
        """Check whether the simulation environment is alive (for agent interviews).

        Args:
            simulation_id: Simulation ID.

        Returns:
            True if the environment is running, False if it has already stopped.
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            return False

        ipc_client = SimulationIPCClient(sim_dir)
        return ipc_client.check_env_alive()

    @classmethod
    def get_env_status_detail(cls, simulation_id: str) -> Dict[str, Any]:
        """Get detailed simulation environment status.

        Args:
            simulation_id: Simulation ID.

        Returns:
            Status dict including status, twitter_available, reddit_available, timestamp.
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        status_file = os.path.join(sim_dir, "env_status.json")
        
        default_status = {
            "status": "stopped",
            "twitter_available": False,
            "reddit_available": False,
            "timestamp": None
        }
        
        if not os.path.exists(status_file):
            return default_status
        
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
            return {
                "status": status.get("status", "stopped"),
                "twitter_available": status.get("twitter_available", False),
                "reddit_available": status.get("reddit_available", False),
                "timestamp": status.get("timestamp")
            }
        except (json.JSONDecodeError, OSError):
            return default_status

    @classmethod
    def interview_agent(
        cls,
        simulation_id: str,
        agent_id: int,
        prompt: str,
        platform: str = None,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """Interview one agent via the simulation IPC service.

        Args:
            simulation_id: Simulation ID.
            agent_id: Agent ID.
            prompt: Interview prompt.
            platform: Optional platform scope (twitter/reddit).
            timeout: Request timeout in seconds.

        Returns:
            Interview response payload.

        Raises:
            ValueError: If simulation path/environment is unavailable.
            TimeoutError: If the IPC call times out.
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"Simulation does not exist: {simulation_id}")

        ipc_client = SimulationIPCClient(sim_dir)

        if not ipc_client.check_env_alive():
            raise ValueError(f"Simulation environment is not running: {simulation_id}")

        logger.info(f"Interview request: simulation_id={simulation_id}, agent_id={agent_id}, platform={platform}")

        response = ipc_client.send_interview(
            agent_id=agent_id,
            prompt=prompt,
            platform=platform,
            timeout=timeout
        )

        if response.status.value == "completed":
            return {
                "success": True,
                "agent_id": agent_id,
                "prompt": prompt,
                "result": response.result,
                "timestamp": response.timestamp
            }
        else:
            return {
                "success": False,
                "agent_id": agent_id,
                "prompt": prompt,
                "error": response.error,
                "timestamp": response.timestamp
            }
    
    @classmethod
    def interview_agents_batch(
        cls,
        simulation_id: str,
        interviews: List[Dict[str, Any]],
        platform: str = None,
        timeout: float = 120.0
    ) -> Dict[str, Any]:
        """Interview a batch of agents via IPC.

        Args:
            simulation_id: Simulation ID.
            interviews: List of {agent_id, prompt, platform?} payloads.
            platform: Optional default platform when interview-level platform is absent.
            timeout: Request timeout in seconds.

        Returns:
            Batch interview response payload.

        Raises:
            ValueError: If simulation path/environment is unavailable.
            TimeoutError: If the IPC call times out.
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"Simulation does not exist: {simulation_id}")

        ipc_client = SimulationIPCClient(sim_dir)

        if not ipc_client.check_env_alive():
            raise ValueError(f"Simulation environment is not running: {simulation_id}")

        logger.info(f"Batch interview request: simulation_id={simulation_id}, count={len(interviews)}, platform={platform}")

        response = ipc_client.send_batch_interview(
            interviews=interviews,
            platform=platform,
            timeout=timeout
        )

        if response.status.value == "completed":
            return {
                "success": True,
                "interviews_count": len(interviews),
                "result": response.result,
                "timestamp": response.timestamp
            }
        else:
            return {
                "success": False,
                "interviews_count": len(interviews),
                "error": response.error,
                "timestamp": response.timestamp
            }
    
    @classmethod
    def interview_all_agents(
        cls,
        simulation_id: str,
        prompt: str,
        platform: str = None,
        timeout: float = 180.0
    ) -> Dict[str, Any]:
        """Interview all configured agents with a shared prompt.

        Args:
            simulation_id: Simulation ID.
            prompt: Interview prompt to send to all agents.
            platform: Optional platform scope (twitter/reddit).
            timeout: Request timeout in seconds.

        Returns:
            Aggregated interview results.
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"Simulation does not exist: {simulation_id}")

        # Get all agent info from config file
        config_path = os.path.join(sim_dir, "simulation_config.json")
        if not os.path.exists(config_path):
            raise ValueError(f"Simulation configuration does not exist: {simulation_id}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        agent_configs = config.get("agent_configs", [])
        if not agent_configs:
            raise ValueError(f"No agent configs found for simulation: {simulation_id}")

        # Build interview payload list.
        interviews = []
        for agent_config in agent_configs:
            agent_id = agent_config.get("agent_id")
            if agent_id is not None:
                interviews.append({
                    "agent_id": agent_id,
                    "prompt": prompt
                })

        logger.info(f"All-agent interview request: simulation_id={simulation_id}, agent_count={len(interviews)}, platform={platform}")

        return cls.interview_agents_batch(
            simulation_id=simulation_id,
            interviews=interviews,
            platform=platform,
            timeout=timeout
        )
    
    @classmethod
    def close_simulation_env(
        cls,
        simulation_id: str,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Close a running simulation environment through IPC."""
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"Simulation does not exist: {simulation_id}")
        
        ipc_client = SimulationIPCClient(sim_dir)
        
        if not ipc_client.check_env_alive():
            return {
                "success": True,
                "message": "Environment already closed"
            }
        
        logger.info(f"Close environment request: simulation_id={simulation_id}")
        
        try:
            response = ipc_client.send_close_env(timeout=timeout)
            
            return {
                "success": response.status.value == "completed",
                "message": "Environment close command sent",
                "result": response.result,
                "timestamp": response.timestamp
            }
        except TimeoutError:
            # Timeout waiting for environment close confirmation
            return {
                "success": True,
                "message": "Environment close command sent (timed out waiting for confirmation, but environment may have closed)"
            }
    
    @classmethod
    def _get_interview_history_from_db(
        cls,
        db_path: str,
        platform_name: str,
        agent_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get interview results from database."""
        import sqlite3
        
        if not os.path.exists(db_path):
            return []
        
        results = []
        
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            if agent_id is not None:
                cursor.execute("""
                    SELECT user_id, info, created_at
                    FROM trace
                    WHERE action = 'interview' AND user_id =?
                    ORDER BY created_at DESC
                    LIMIT?
                """, (agent_id, limit))
            else:
                cursor.execute("""
                    SELECT user_id, info, created_at
                    FROM trace
                    WHERE action = 'interview'
                    ORDER BY created_at DESC
                    LIMIT?
                """, (limit,))

            for user_id, info_json, created_at in cursor.fetchall():
                try:
                    info = json.loads(info_json) if info_json else {}
                except json.JSONDecodeError:
                    info = {"raw": info_json}

                results.append({
                    "agent_id": user_id,
                    "response": info.get("response", info),
                    "prompt": info.get("prompt", ""),
                    "timestamp": created_at,
                    "platform": platform_name
                })

        except Exception as e:
            logger.error(f"Failed to read interview history ({platform_name}): {e}")
        finally:
            if conn:
                conn.close()
        
        return results

    @classmethod
    def get_interview_history(
        cls,
        simulation_id: str,
        platform: str = None,
        agent_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get interview records from the simulation database.

        Args:
            simulation_id: Simulation ID.
            platform: Platform type (reddit/twitter/None).
                - "reddit": Get Reddit platform records only.
                - "twitter": Get Twitter platform records only.
                - None: Get records from all platforms.
            agent_id: Agent ID (optional; filter to a specific agent).
            limit: Maximum number of records per platform.

        Returns:
            List of interview records.
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        
        results = []
        
        # Determine which platforms to query
        if platform in ("reddit", "twitter"):
            platforms = [platform]
        else:
            # No platform specified; query all platforms
            platforms = ["twitter", "reddit"]
        
        for p in platforms:
            db_path = os.path.join(sim_dir, f"{p}_simulation.db")
            platform_results = cls._get_interview_history_from_db(
                db_path=db_path,
                platform_name=p,
                agent_id=agent_id,
                limit=limit
            )
            results.extend(platform_results)
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # If querying all platforms, cap total results to the limit
        if len(platforms) > 1 and len(results) > limit:
            results = results[:limit]
        
        return results

