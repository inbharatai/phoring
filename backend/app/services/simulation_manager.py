"""Simulation manager service.

Coordinates entity extraction, profile generation, and simulation configuration
for Twitter/Reddit execution pipelines.
"""

import os
import re
import json
import shutil
import tempfile
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from..config import Config
from..utils.logger import get_logger
from.zep_entity_reader import ZepEntityReader, FilteredEntities
from.oasis_profile_generator import OasisProfileGenerator, OasisAgentProfile
from.simulation_config_generator import SimulationConfigGenerator, SimulationParameters

logger = get_logger('phoring.simulation')


class SimulationStatus(str, Enum):
    """Lifecycle states for a simulation preparation/execution record."""
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"



@dataclass
class SimulationState:
    """Persistent state snapshot for one simulation."""
    simulation_id: str
    project_id: str
    graph_id: str
    
    # Platform flags
    enable_twitter: bool = True
    enable_reddit: bool = True
    
    # Current status
    status: SimulationStatus = SimulationStatus.CREATED
    
    # Stage output metrics.
    entities_count: int = 0
    profiles_count: int = 0
    entity_types: List[str] = field(default_factory=list)
    
    # Configuration generation metadata.
    config_generated: bool = False
    config_reasoning: str = ""
    
    # Runtime progress snapshots.
    current_round: int = 0
    twitter_status: str = "not_started"
    reddit_status: str = "not_started"
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Error details when status=FAILED.
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize full simulation state."""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "enable_twitter": self.enable_twitter,
            "enable_reddit": self.enable_reddit,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "config_reasoning": self.config_reasoning,
            "current_round": self.current_round,
            "twitter_status": self.twitter_status,
            "reddit_status": self.reddit_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }
    
    def to_simple_dict(self) -> Dict[str, Any]:
        """Serialize compact state for lightweight API responses."""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "error": self.error,
        }


class SimulationManager:
    """Orchestrate full simulation preparation and state persistence.

    Core responsibilities:
    1. Read and filter entities from Zep graph data.
    2. Generate OASIS agent profiles.
    3. Generate simulation configuration parameters.
    4. Persist outputs and status files under simulation storage.

    Uses singleton pattern so the in-memory cache is shared across requests.
    """

    # Simulation data storage directory
    SIMULATION_DATA_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../uploads/simulations'
    )

    _instance = None
    _init_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    # Ensure simulation storage exists.
                    os.makedirs(cls.SIMULATION_DATA_DIR, exist_ok=True)
                    # In-memory state cache.
                    instance._simulations: Dict[str, SimulationState] = {}
                    # Per-simulation locks to prevent concurrent state corruption
                    instance._state_locks: Dict[str, threading.Lock] = {}
                    instance._state_locks_lock = threading.Lock()
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        # All init done in __new__ for singleton safety
        pass
    
    def _get_state_lock(self, simulation_id: str) -> threading.Lock:
        """Get or create a lock for a specific simulation."""
        with self._state_locks_lock:
            if simulation_id not in self._state_locks:
                self._state_locks[simulation_id] = threading.Lock()
            return self._state_locks[simulation_id]
    
    def _get_simulation_dir(self, simulation_id: str) -> str:
        """Get simulation data directory path."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', simulation_id):
            raise ValueError(f"Invalid simulation_id: {simulation_id!r}")
        sim_dir = os.path.join(self.SIMULATION_DATA_DIR, simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir

    def _build_oasis_context_payload(
        self,
        simulation_requirement: str,
        document_text: str,
        state: SimulationState,
        sim_params: SimulationParameters,
    ) -> Dict[str, Any]:
        """Build a compact payload that captures resources + generated outputs.

        This payload is persisted and also injected into agent profiles so
        OASIS/CAMEL receives the same global context during generation/runtime.
        """
        event_cfg = sim_params.event_config
        scheduled_events = event_cfg.scheduled_events or []
        event_titles = [e.get("title", "") for e in scheduled_events[:5] if isinstance(e, dict)]
        web_news_excerpt = ""
        social_sentiment_summary: List[str] = []

        # Best-effort: include live news + social signals directly in payload.
        try:
            from .web_intelligence import NewsScraperService

            svc = NewsScraperService()
            if svc.enabled:
                data = svc.gather_for_entity(
                    simulation_requirement or "scenario",
                    "Scenario",
                    max_articles=3,
                    context=simulation_requirement,
                )
                web_news_excerpt = (data.get("combined_text", "") or "")[:4000]
                social_posts = data.get("social_media_posts", []) or []
                social_sentiment_summary = [
                    f"[{p.get('platform', 'Social')}] {(p.get('snippet', '') or '')[:140]}"
                    for p in social_posts[:6]
                ]
        except Exception as e:
            logger.debug(f"Failed to gather web/social payload context: {e}")

        return {
            "simulation_id": state.simulation_id,
            "project_id": state.project_id,
            "graph_id": state.graph_id,
            "simulation_requirement": simulation_requirement,
            "document_excerpt": (document_text or "")[:3000],
            "entity_types": state.entity_types,
            "hot_topics": event_cfg.hot_topics,
            "narrative_direction": event_cfg.narrative_direction,
            "scheduled_event_titles": event_titles,
            "web_news_excerpt": web_news_excerpt,
            "social_sentiment_summary": social_sentiment_summary,
            "generation_reasoning": sim_params.generation_reasoning,
            "generated_at": datetime.now().isoformat(),
        }

    def _render_oasis_context_for_profiles(self, payload: Dict[str, Any], stance: str = "neutral") -> str:
        """Render a stance-aware context digest appended to each profile persona.

        Different stances receive different emphasis to break the echo chamber:
        - supportive: sees opportunity signals + positive news first
        - opposing: sees risk signals + negative news first
        - neutral/observer: sees balanced raw data
        """
        topics = payload.get("hot_topics") or []
        topic_str = ", ".join(topics[:6]) if topics else "none"
        event_titles = payload.get("scheduled_event_titles") or []
        event_str = "; ".join(event_titles[:4]) if event_titles else "none"
        req = (payload.get("simulation_requirement") or "").strip()[:280]
        narrative = (payload.get("narrative_direction") or "").strip()[:280]
        reasoning = (payload.get("generation_reasoning") or "").strip()[:280]
        news_excerpt = (payload.get("web_news_excerpt") or "").strip()[:1500]
        social = payload.get("social_sentiment_summary") or []
        social_str = " | ".join(social[:3]) if social else "none"

        # Stance-specific framing to prevent echo chamber
        if stance == "supportive":
            stance_guidance = (
                "Your perspective leans optimistic. Focus on opportunity signals, "
                "growth catalysts, and positive developments. Challenge bearish narratives "
                "with evidence — but acknowledge risks you find credible."
            )
        elif stance == "opposing":
            stance_guidance = (
                "Your perspective leans cautious/skeptical. Focus on risk factors, "
                "downside scenarios, and overlooked threats. Challenge bullish narratives "
                "with evidence — but acknowledge opportunities you find credible."
            )
        elif stance == "observer":
            stance_guidance = (
                "You are a detached observer. Report what you see without taking sides. "
                "Highlight contradictions between bullish and bearish signals."
            )
        else:
            stance_guidance = (
                "Analyze the scenario from your own perspective. Form your own view "
                "based on the evidence — do not simply agree with the majority."
            )

        return (
            "[SIMULATION CONTEXT]\n"
            f"Scenario: {req}\n"
            f"Narrative: {narrative}\n"
            f"Hot topics: {topic_str}\n"
            f"Potential disruption events: {event_str}\n"
            f"Live web signals: {news_excerpt}\n"
            f"Social sentiment signals: {social_str}\n"
            f"[YOUR ANALYTICAL STANCE]\n"
            f"{stance_guidance}\n"
            f"Generation guidance: {reasoning}"
        )
    
    def _save_simulation_state(self, state: SimulationState):
        """Atomically persist simulation state to disk and refresh cache."""
        lock = self._get_state_lock(state.simulation_id)
        with lock:
            sim_dir = self._get_simulation_dir(state.simulation_id)
            state_file = os.path.join(sim_dir, "state.json")
            
            state.updated_at = datetime.now().isoformat()
            
            fd, tmp_path = tempfile.mkstemp(suffix='.tmp', dir=sim_dir)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, state_file)
            except BaseException:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
            
            self._simulations[state.simulation_id] = state
    
    def _load_simulation_state(self, simulation_id: str) -> Optional[SimulationState]:
        """Load simulation state from cache or disk."""
        if simulation_id in self._simulations:
            return self._simulations[simulation_id]
        
        lock = self._get_state_lock(simulation_id)
        with lock:
            # Double-check after acquiring lock
            if simulation_id in self._simulations:
                return self._simulations[simulation_id]
            
            sim_dir = self._get_simulation_dir(simulation_id)
            state_file = os.path.join(sim_dir, "state.json")
            
            if not os.path.exists(state_file):
                return None
            
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            state = SimulationState(
                simulation_id=simulation_id,
                project_id=data.get("project_id", ""),
                graph_id=data.get("graph_id", ""),
                enable_twitter=data.get("enable_twitter", True),
                enable_reddit=data.get("enable_reddit", True),
                status=SimulationStatus(data.get("status", "created")),
                entities_count=data.get("entities_count", 0),
                profiles_count=data.get("profiles_count", 0),
                entity_types=data.get("entity_types", []),
                config_generated=data.get("config_generated", False),
                config_reasoning=data.get("config_reasoning", ""),
                current_round=data.get("current_round", 0),
                twitter_status=data.get("twitter_status", "not_started"),
                reddit_status=data.get("reddit_status", "not_started"),
                created_at=data.get("created_at", datetime.now().isoformat()),
                updated_at=data.get("updated_at", datetime.now().isoformat()),
                error=data.get("error"),
            )
            
            self._simulations[simulation_id] = state
            return state
    
    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> SimulationState:
        """Create a new simulation state record.

        Args:
            project_id: Project ID.
            graph_id: Zep graph ID.
            enable_twitter: Whether Twitter simulation is enabled.
            enable_reddit: Whether Reddit simulation is enabled.

        Returns:
            Created simulation state.
        """
        import uuid
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
            status=SimulationStatus.CREATED,
        )
        
        self._save_simulation_state(state)
        logger.info(f"Created simulation: {simulation_id}, project={project_id}, graph={graph_id}")
        
        return state
    
    def prepare_simulation(
        self,
        simulation_id: str,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]] = None,
        use_llm_for_profiles: bool = True,
        progress_callback: Optional[callable] = None,
        parallel_profile_count: int = 3
    ) -> SimulationState:
        """Prepare a simulation for execution.

        Pipeline:
        1. Read and filter entities from graph.
        2. Generate OASIS agent profiles (LLM optional, parallelized).
        3. Generate simulation parameters via configuration generator.
        4. Persist profiles and config files.
        5. Mark simulation as READY.

        Args:
            simulation_id: Simulation ID.
            simulation_requirement: Requirement text used to guide generation.
            document_text: Source document text used for prompting.
            defined_entity_types: Optional allowed entity type whitelist.
            use_llm_for_profiles: Whether to use LLM-enhanced persona generation.
            progress_callback: Optional progress callback.
            parallel_profile_count: Number of parallel profile workers.

        Returns:
            Updated simulation state.
        """
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation does not exist: {simulation_id}")
        
        try:
            state.status = SimulationStatus.PREPARING
            self._save_simulation_state(state)
            
            sim_dir = self._get_simulation_dir(simulation_id)
            
            # ========== Stage 1: Read and filter entities ==========
            if progress_callback:
                progress_callback("reading", 0, "Reading Zep graph...")
            
            reader = ZepEntityReader()
            
            if progress_callback:
                progress_callback("reading", 30, "Loading graph nodes...")
            
            filtered = reader.filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=defined_entity_types,
                enrich_with_edges=True
            )
            
            state.entities_count = filtered.filtered_count
            state.entity_types = list(filtered.entity_types)
            
            if progress_callback:
                progress_callback(
                    "reading", 100, 
                    f"Read complete: {filtered.filtered_count} entities",
                    current=filtered.filtered_count,
                    total=filtered.filtered_count
                )
            
            if filtered.filtered_count == 0:
                state.status = SimulationStatus.FAILED
                state.error = "No entities found; verify graph build and selected entity types."
                self._save_simulation_state(state)
                return state
            
            # ========== Stage 2: Generate agent profiles ==========
            total_entities = len(filtered.entities)
            
            if progress_callback:
                progress_callback(
                    "generating_profiles", 0, 
                    "Generating profiles...",
                    current=0,
                    total=total_entities
                )
            
            # Pass graph_id so generator can query Zep for enrichment
            generator = OasisProfileGenerator(graph_id=state.graph_id, simulation_requirement=simulation_requirement)
            
            def profile_progress(current, total, msg):
                if progress_callback:
                    progress_callback(
                        "generating_profiles", 
                        int(current / total * 100), 
                        msg,
                        current=current,
                        total=total,
                        item_name=msg
                    )
            
            # Set output file path (Reddit uses JSON, Twitter uses CSV)
            realtime_output_path = None
            realtime_platform = "reddit"
            if state.enable_reddit:
                realtime_output_path = os.path.join(sim_dir, "reddit_profiles.json")
                realtime_platform = "reddit"
            elif state.enable_twitter:
                realtime_output_path = os.path.join(sim_dir, "twitter_profiles.csv")
                realtime_platform = "twitter"
            
            profiles = generator.generate_profiles_from_entities(
                entities=filtered.entities,
                use_llm=use_llm_for_profiles,
                progress_callback=profile_progress,
                graph_id=state.graph_id, # graph_id Zep 
                parallel_count=parallel_profile_count,
                realtime_output_path=realtime_output_path,
                output_platform=realtime_platform
            )
            
            state.profiles_count = len(profiles)
            
            # Save profile files (Twitter=CSV, Reddit=JSON)
            # Save final profile files (Reddit may already be written during generation)
            if progress_callback:
                progress_callback(
                    "generating_profiles", 95, 
                    "Saving profile files...",
                    current=total_entities,
                    total=total_entities
                )
            
            if state.enable_reddit:
                generator.save_profiles(
                    profiles=profiles,
                    file_path=os.path.join(sim_dir, "reddit_profiles.json"),
                    platform="reddit"
                )
            
            if state.enable_twitter:
                # Twitter uses CSV format for OASIS compatibility
                generator.save_profiles(
                    profiles=profiles,
                    file_path=os.path.join(sim_dir, "twitter_profiles.csv"),
                    platform="twitter"
                )
            
            if progress_callback:
                progress_callback(
                    "generating_profiles", 100, 
                    f"Profile generation complete: {len(profiles)} profiles",
                    current=len(profiles),
                    total=len(profiles)
                )
            
            # ========== Stage 3: LLM-generated simulation configuration ==========
            if progress_callback:
                progress_callback(
                    "generating_config", 0, 
                    "Analyzing simulation requirements...",
                    current=0,
                    total=3
                )
            
            config_generator = SimulationConfigGenerator()
            
            if progress_callback:
                progress_callback(
                    "generating_config", 30, 
                    "Calling LLM to generate config...",
                    current=1,
                    total=3
                )
            
            sim_params = config_generator.generate_config(
                simulation_id=simulation_id,
                project_id=state.project_id,
                graph_id=state.graph_id,
                simulation_requirement=simulation_requirement,
                document_text=document_text,
                entities=filtered.entities,
                enable_twitter=state.enable_twitter,
                enable_reddit=state.enable_reddit
            )

            # Build a unified context payload and push it into OASIS-facing assets.
            oasis_context_payload = self._build_oasis_context_payload(
                simulation_requirement=simulation_requirement,
                document_text=document_text,
                state=state,
                sim_params=sim_params,
            )

            # Build a stance lookup from agent configs for echo-chamber-breaking context injection.
            agent_stance_map = {}
            for ac in sim_params.agent_configs:
                agent_stance_map[ac.entity_name] = ac.stance

            # Inject stance-aware context into each profile to break the echo chamber.
            for profile in profiles:
                stance = agent_stance_map.get(profile.name, "neutral")
                oasis_context_text = self._render_oasis_context_for_profiles(oasis_context_payload, stance=stance)
                if oasis_context_text not in profile.persona:
                    profile.persona = f"{profile.persona}\n\n{oasis_context_text}"[:6000]
                if oasis_context_text not in profile.bio:
                    profile.bio = f"{profile.bio}\n\n{oasis_context_text}"[:3000]

            # Overwrite profile files with context-enriched variants.
            if state.enable_reddit:
                generator.save_profiles(
                    profiles=profiles,
                    file_path=os.path.join(sim_dir, "reddit_profiles.json"),
                    platform="reddit",
                )

            if state.enable_twitter:
                generator.save_profiles(
                    profiles=profiles,
                    file_path=os.path.join(sim_dir, "twitter_profiles.csv"),
                    platform="twitter",
                )
            
            if progress_callback:
                progress_callback(
                    "generating_config", 70, 
                    "Saving configuration file...",
                    current=2,
                    total=3
                )
            
            # Persist simulation configuration file.
            config_path = os.path.join(sim_dir, "simulation_config.json")
            config_data = sim_params.to_dict()
            config_data["oasis_context"] = oasis_context_payload
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            # Persist standalone context payload for debugging/auditing.
            payload_path = os.path.join(sim_dir, "oasis_context_payload.json")
            with open(payload_path, 'w', encoding='utf-8') as f:
                json.dump(oasis_context_payload, f, ensure_ascii=False, indent=2)
            
            state.config_generated = True
            state.config_reasoning = sim_params.generation_reasoning
            
            if progress_callback:
                progress_callback(
                    "generating_config", 100, 
                    "Configuration generation complete",
                    current=3,
                    total=3
                )
            
            # Mark simulation as ready
            state.status = SimulationStatus.READY
            self._save_simulation_state(state)
            
            logger.info(f"Simulation preparation complete: {simulation_id}, "
                       f"entities={state.entities_count}, profiles={state.profiles_count}")
            
            return state
            
        except Exception as e:
            logger.error(f"Simulation preparation failed: {simulation_id}, error={e}")
            import traceback
            logger.error(traceback.format_exc())
            state.status = SimulationStatus.FAILED
            state.error = str(e)
            self._save_simulation_state(state)
            raise
    
    def get_simulation(self, simulation_id: str) -> Optional[SimulationState]:
        """Get one simulation state by ID."""
        return self._load_simulation_state(simulation_id)
    
    def list_simulations(self, project_id: Optional[str] = None) -> List[SimulationState]:
        """List simulations, optionally filtered by project ID."""
        simulations = []
        
        if os.path.exists(self.SIMULATION_DATA_DIR):
            for sim_id in os.listdir(self.SIMULATION_DATA_DIR):
                # Skip hidden files (.DS_Store) and non-directory entries
                sim_path = os.path.join(self.SIMULATION_DATA_DIR, sim_id)
                if sim_id.startswith('.') or not os.path.isdir(sim_path):
                    continue
                
                state = self._load_simulation_state(sim_id)
                if state:
                    if project_id is None or state.project_id == project_id:
                        simulations.append(state)
        
        return simulations
    
    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        """Load generated profile data for a simulation/platform."""
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation does not exist: {simulation_id}")

        sim_dir = self._get_simulation_dir(simulation_id)

        # Twitter profiles are saved as CSV; Reddit as JSON
        if platform == "twitter":
            profile_path = os.path.join(sim_dir, f"{platform}_profiles.csv")
            if not os.path.exists(profile_path):
                return []
            import csv
            with open(profile_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)
        else:
            profile_path = os.path.join(sim_dir, f"{platform}_profiles.json")
            if not os.path.exists(profile_path):
                return []
            with open(profile_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Load persisted simulation configuration JSON."""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_run_instructions(self, simulation_id: str) -> Dict[str, str]:
        """Return command-line instructions for running generated simulations."""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts'))
        
        return {
            "simulation_dir": sim_dir,
            "scripts_dir": scripts_dir,
            "config_file": config_path,
            "commands": {
                "twitter": f"python {scripts_dir}/run_twitter_simulation.py --config {config_path}",
                "reddit": f"python {scripts_dir}/run_reddit_simulation.py --config {config_path}",
                "parallel": f"python {scripts_dir}/run_parallel_simulation.py --config {config_path}",
            },
            "instructions": (
                f"1. Activate environment: conda activate Phoring\n"
                f"2. Run simulation commands from {scripts_dir}:\n"
                f" - Run Twitter: python {scripts_dir}/run_twitter_simulation.py --config {config_path}\n"
                f" - Run Reddit: python {scripts_dir}/run_reddit_simulation.py --config {config_path}\n"
                f" - Run both platforms: python {scripts_dir}/run_parallel_simulation.py --config {config_path}"
            )
        }
