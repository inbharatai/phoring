"""Simulation configuration generator.

This service uses LLM + rule-based safeguards to build a complete simulation
configuration from:
- simulation requirements,
- source documents,
- graph entities.

Generation pipeline:
1. Build time configuration.
2. Build event configuration.
3. Build per-agent behavior profiles.
4. Build per-platform ranking/spread parameters.

Post-processing then calibrates the final config for stability and realism.
"""

import json
import math
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from..config import Config
from..utils.logger import get_logger
from.zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger('phoring.simulation_config')

# Geopolitical event categories for disruption injection.
GEOPOLITICAL_CATEGORIES = [
    "natural_disaster", "armed_conflict", "political_turmoil",
    "trade_war", "sanctions", "policy_change", "diplomatic_crisis",
    "economic_shock", "pandemic", "supply_chain_disruption",
    "election", "regulatory_change", "civil_unrest", "cyber_attack",
]


@dataclass
class AgentActivityConfig:
    """Per-agent behavior parameters used during simulation rounds."""
    agent_id: int
    entity_uuid: str
    entity_name: str
    entity_type: str
    
    # Relative activity score in the range [0.0, 1.0].
    activity_level: float = 0.5
    
    # Content generation frequency.
    posts_per_hour: float = 1.0
    comments_per_hour: float = 2.0
    
    # Active hours in 24-hour format.
    active_hours: List[int] = field(default_factory=lambda: list(range(8, 23)))
    
    # Response delay range in minutes.
    response_delay_min: int = 5
    response_delay_max: int = 60
    
    # Sentiment bias in range [-1.0, 1.0].
    sentiment_bias: float = 0.0
    
    # Supported stances: supportive, opposing, neutral, observer.
    stance: str = "neutral"
    
    # Influence (on other agents)
    influence_weight: float = 1.0


@dataclass 
class TimeSimulationConfig:
    """Global timeline and traffic envelope for the simulation run."""
    # Total simulated hours (default: 72h).
    total_simulation_hours: int = 72

    # Minutes represented by one simulation round.
    minutes_per_round: int = 60

    # Active-agent envelope per simulated hour.
    agents_per_hour_min: int = 5
    agents_per_hour_max: int = 20

    # Peak hours and relative multiplier.
    peak_hours: List[int] = field(default_factory=lambda: [19, 20, 21, 22])
    peak_activity_multiplier: float = 1.5

    # Off-peak hours and relative multiplier.
    off_peak_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    off_peak_activity_multiplier: float = 0.05

    # Morning hours and relative multiplier.
    morning_hours: List[int] = field(default_factory=lambda: [6, 7, 8])
    morning_activity_multiplier: float = 0.4

    # Workday hours and relative multiplier.
    work_hours: List[int] = field(default_factory=lambda: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18])
    work_activity_multiplier: float = 0.7


@dataclass
class EventConfig:
    """Event-level narrative and seed-post configuration."""
    # Initial posts that seed the simulation.
    initial_posts: List[Dict[str, Any]] = field(default_factory=list)

    # Scheduled events injected during the run.
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)

    # Key topics expected to trend in the run.
    hot_topics: List[str] = field(default_factory=list)

    # Narrative framing of the scenario.
    narrative_direction: str = ""


@dataclass
class PlatformConfig:
    """Ranking and spread parameters for a target platform."""
    platform: str  # twitter or reddit

    # Feed ranking weights.
    recency_weight: float = 0.4
    popularity_weight: float = 0.3
    relevance_weight: float = 0.3

    # Virality threshold for spread mechanics.
    viral_threshold: int = 10

    # Degree of echo-chamber effect.
    echo_chamber_strength: float = 0.5


@dataclass
class SimulationParameters:
    """Serializable container for all simulation parameters."""
    # Core identifiers.
    simulation_id: str
    project_id: str
    graph_id: str
    simulation_requirement: str

    # Time configuration.
    time_config: TimeSimulationConfig = field(default_factory=TimeSimulationConfig)

    # Per-agent behavior configuration.
    agent_configs: List[AgentActivityConfig] = field(default_factory=list)

    # Scenario event configuration.
    event_config: EventConfig = field(default_factory=EventConfig)

    # Platform-specific ranking/spread configuration.
    twitter_config: Optional[PlatformConfig] = None
    reddit_config: Optional[PlatformConfig] = None

    # LLM metadata used during generation.
    llm_model: str = ""
    llm_base_url: str = ""

    # Generation metadata.
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_reasoning: str = ""
    
    def to_dict(self) -> dict:
        """Serialize parameters to a JSON-compatible dictionary."""
        time_dict = asdict(self.time_config)
        # Compute total_rounds so downstream consumers never see null
        time_dict["total_rounds"] = max(
            1,
            round(time_dict["total_simulation_hours"] * 60 / time_dict["minutes_per_round"]),
        )
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "time_config": time_dict,
            "agent_configs": [asdict(a) for a in self.agent_configs],
            "event_config": asdict(self.event_config),
            "twitter_config": asdict(self.twitter_config) if self.twitter_config else None,
            "reddit_config": asdict(self.reddit_config) if self.reddit_config else None,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_reasoning": self.generation_reasoning,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize parameters to JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SimulationConfigGenerator:
    """Generate simulation parameters from requirements, documents, and entities.

    Supports calibration profiles:
    - realism: conservative defaults for credible social dynamics
    - aggressive: higher activity for virality stress testing
    """
    
    # Max context length in characters
    MAX_CONTEXT_LENGTH = 50000
    # Number of agents to generate per batch
    AGENTS_PER_BATCH = 15

    # Per-step context truncation lengths (characters)
    TIME_CONFIG_CONTEXT_LENGTH = 15000   # Time config generation
    EVENT_CONFIG_CONTEXT_LENGTH = 12000  # Event config generation
    ENTITY_SUMMARY_LENGTH = 300          # Entity summary preview
    AGENT_SUMMARY_LENGTH = 300           # Agent config entity summary
    ENTITIES_PER_TYPE_DISPLAY = 20       # Entities shown per type

    CALIBRATION_PROFILES = {
        "realism": {
            "post_target_per_active_agent": 0.35,
            "comment_target_per_active_agent": 0.90,
            "volume_overage_allowance": 1.8,
            "max_posts_per_hour": 8.0,
            "max_comments_per_hour": 15.0,
            "max_activity_level": 0.92,
            "max_response_delay": 1800,
        },
        "aggressive": {
            "post_target_per_active_agent": 0.70,
            "comment_target_per_active_agent": 1.70,
            "volume_overage_allowance": 2.4,
            "max_posts_per_hour": 14.0,
            "max_comments_per_hour": 30.0,
            "max_activity_level": 1.00,
            "max_response_delay": 1200,
        },
        "fast": {
            "post_target_per_active_agent": 0.50,
            "comment_target_per_active_agent": 1.20,
            "volume_overage_allowance": 2.0,
            "max_posts_per_hour": 10.0,
            "max_comments_per_hour": 20.0,
            "max_activity_level": 0.95,
            "max_response_delay": 900,
        },
        "express": {
            "post_target_per_active_agent": 0.60,
            "comment_target_per_active_agent": 1.40,
            "volume_overage_allowance": 2.2,
            "max_posts_per_hour": 12.0,
            "max_comments_per_hour": 25.0,
            "max_activity_level": 0.98,
            "max_response_delay": 600,
        },
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        calibration_mode: Optional[str] = None,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY not yet configured")
        
        from openai import OpenAI
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        selected_mode = calibration_mode or Config.SIMULATION_CALIBRATION_MODE or "realism"
        self.calibration_mode = (
            selected_mode if selected_mode in self.CALIBRATION_PROFILES else "realism"
        )
    
    def generate_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SimulationParameters:
        """Generate complete simulation configuration (step-by-step).

        Args:
            simulation_id: Simulation ID.
            project_id: Project ID.
            graph_id: Graph ID.
            simulation_requirement: Simulation requirement description.
            document_text: Document content.
            entities: Filtered entity list.
            enable_twitter: Whether to enable Twitter platform.
            enable_reddit: Whether to enable Reddit platform.
            progress_callback: Progress callback function (current_step, total_steps, message).

        Returns:
            SimulationParameters: Complete simulation parameters.
        """
        logger.info(f"Starting simulation config generation: simulation_id={simulation_id}, entities={len(entities)}")
        
        # Calculate total steps
        num_batches = math.ceil(len(entities) / self.AGENTS_PER_BATCH)
        total_steps = 3 + num_batches  # time config + event config + N agent batches + platform config
        current_step = 0
        
        def report_progress(step: int, message: str):
            nonlocal current_step
            current_step = step
            if progress_callback:
                progress_callback(step, total_steps, message)
            logger.info(f"[{step}/{total_steps}] {message}")
        
        # 1. Build base context info
        context = self._build_context(
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            entities=entities
        )
        
        reasoning_parts = []
        
        # ========== Step 1: Generate time config ==========
        report_progress(1, "Generating time configuration...")
        num_entities = len(entities)
        time_config_result = self._generate_time_config(context, num_entities)
        time_config = self._parse_time_config(time_config_result, num_entities)
        reasoning_parts.append(f"time config: {time_config_result.get('reasoning', 'success')}")

        # ========== Step 2: Generate event config ==========
        report_progress(2, "Generating event configuration...")
        event_config_result = self._generate_event_config(context, simulation_requirement, entities)
        event_config = self._parse_event_config(event_config_result)
        reasoning_parts.append(f"event config: {event_config_result.get('reasoning', 'success')}")
        
        # ========== Step 3-N: Generate agent configuration ==========
        all_agent_configs = []
        for batch_idx in range(num_batches):
            start_idx = batch_idx * self.AGENTS_PER_BATCH
            end_idx = min(start_idx + self.AGENTS_PER_BATCH, len(entities))
            batch_entities = entities[start_idx:end_idx]
            
            report_progress(
                3 + batch_idx,
                f"Generate agent config ({start_idx + 1}-{end_idx}/{len(entities)})..."
            )
            
            batch_configs = self._generate_agent_configs_batch(
                context=context,
                entities=batch_entities,
                start_idx=start_idx,
                simulation_requirement=simulation_requirement
            )
            all_agent_configs.extend(batch_configs)
        
        reasoning_parts.append(f"agent config: successfully generated {len(all_agent_configs)} agents")
        
        # ========== Post-process initial post ownership ==========
        logger.info("Assigning initial posts to concrete agents...")
        event_config = self._assign_initial_post_agents(event_config, all_agent_configs)
        assigned_count = len([p for p in event_config.initial_posts if p.get("poster_agent_id") is not None])
        reasoning_parts.append(f"initial posts assigned: {assigned_count}")

        # ========== Geopolitical event injection ==========
        if Config.ENABLE_GEOPOLITICAL_EVENTS:
            report_progress(total_steps, "Generating geopolitical disruption events...")
            geopolitical_events = self._generate_geopolitical_events(
                simulation_requirement=simulation_requirement,
                time_config=time_config,
                entities=entities,
                context=context,
            )
            event_config.scheduled_events = geopolitical_events
            reasoning_parts.append(f"geopolitical events: {len(geopolitical_events)} injected")
            logger.info(f"Injected {len(geopolitical_events)} geopolitical disruption events")
        else:
            logger.info("Geopolitical event injection disabled")

        # ========== Last step: Generate platform config ==========
        report_progress(total_steps, "Generating platform configuration...")
        twitter_config = None
        reddit_config = None
        
        if enable_twitter:
            twitter_config = PlatformConfig(
                platform="twitter",
                recency_weight=0.4,
                popularity_weight=0.3,
                relevance_weight=0.3,
                viral_threshold=10,
                echo_chamber_strength=0.5
            )
        
        if enable_reddit:
            reddit_config = PlatformConfig(
                platform="reddit",
                recency_weight=0.3,
                popularity_weight=0.4,
                relevance_weight=0.3,
                viral_threshold=15,
                echo_chamber_strength=0.6
            )

        all_agent_configs = self._calibrate_agent_configs(all_agent_configs, time_config)
        event_config = self._align_initial_posts(event_config, all_agent_configs)
        if twitter_config:
            twitter_config = self._normalize_platform_config(twitter_config)
        if reddit_config:
            reddit_config = self._normalize_platform_config(reddit_config)

        quality_summary = self._build_quality_summary(
            simulation_requirement=simulation_requirement,
            entities=entities,
            time_config=time_config,
            agent_configs=all_agent_configs,
            event_config=event_config
        )
        
        # Build final parameters
        params = SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=all_agent_configs,
            event_config=event_config,
            twitter_config=twitter_config,
            reddit_config=reddit_config,
            llm_model=self.model_name,
            llm_base_url=self.base_url,
            generation_reasoning=" | ".join(reasoning_parts + [quality_summary])
        )
        
        logger.info(f"Simulation configuration generation complete: {len(params.agent_configs)} agent configs")
        
        return params

    # ---- Temporal context -------------------------------------------------------

    @staticmethod
    def _extract_temporal_context(simulation_requirement: str) -> str:
        """Extract date, time, and temporal references from the user's prompt.

        Returns a structured summary so downstream prompts understand the
        user's intended time horizon and critical dates.
        """
        import re as _re
        now = datetime.now()
        lines: List[str] = [f"Current date: {now.strftime('%B %d, %Y')} ({now.strftime('%A')})"]

        # Explicit dates (e.g. "March 15, 2026", "2025-12-31", "15/03/2026")
        date_patterns = [
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b',
            r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b',
        ]
        found_dates = []
        for pat in date_patterns:
            for m in _re.finditer(pat, simulation_requirement, _re.IGNORECASE):
                found_dates.append(m.group(0))
        if found_dates:
            lines.append(f"Explicit dates mentioned: {', '.join(found_dates)}")

        # Relative time references
        relative_patterns = {
            r'\bnext\s+(?:week|month|quarter|year)\b': 'relative future',
            r'\bthis\s+(?:week|month|quarter|year)\b': 'current period',
            r'\bby\s+(?:Friday|Monday|Tuesday|Wednesday|Thursday|Saturday|Sunday)\b': 'deadline this week',
            r'\bwithin\s+\d+\s+(?:days?|weeks?|months?|hours?)\b': 'bounded timeframe',
            r'\bin\s+\d+\s+(?:days?|weeks?|months?)\b': 'future offset',
            r'\b(?:Q[1-4])\s*\d{4}\b': 'fiscal quarter',
            r'\b(?:FY|fiscal\s+year)\s*\d{2,4}\b': 'fiscal year',
            r'\b(?:short[\s-]term|medium[\s-]term|long[\s-]term)\b': 'horizon indicator',
            r'\b(?:overnight|intraday|end[\s-]of[\s-]day|EOD|close\s+of\s+business)\b': 'trading session',
            r'\b(?:pre[\s-]?market|post[\s-]?market|after[\s-]?hours)\b': 'market timing',
            r'\b\d+[\s-](?:day|week|month|year)\s+(?:outlook|forecast|prediction|projection)\b': 'forecast horizon',
        }
        temporal_refs = []
        for pat, label in relative_patterns.items():
            for m in _re.finditer(pat, simulation_requirement, _re.IGNORECASE):
                temporal_refs.append(f"{m.group(0)} ({label})")
        if temporal_refs:
            lines.append(f"Temporal references: {'; '.join(temporal_refs)}")

        # Year mentions (standalone years 2024-2030)
        years = set(_re.findall(r'\b(20[2-3]\d)\b', simulation_requirement))
        if years:
            lines.append(f"Years referenced: {', '.join(sorted(years))}")

        # Named events with implicit timing (budget, earnings, elections)
        event_timing = {
            r'\b(?:union\s+)?budget\b': 'annual budget (typically Jan-Feb in India)',
            r'\b(?:earnings|quarterly\s+results|Q[1-4]\s+results)\b': 'earnings season',
            r'\b(?:election|polling|ballot)\b': 'election cycle',
            r'\b(?:monsoon|kharif|rabi)\b': 'agricultural season',
            r'\b(?:RBI\s+)?(?:MPC|monetary\s+policy)\b': 'RBI MPC meeting cycle (bi-monthly)',
            r'\b(?:FOMC|Fed\s+meeting)\b': 'FOMC meeting cycle',
            r'\b(?:AGM|annual\s+general\s+meeting)\b': 'annual corporate calendar',
            r'\b(?:expiry|futures?\s+expiry|options?\s+expiry)\b': 'derivatives expiry',
        }
        event_refs = []
        for pat, label in event_timing.items():
            if _re.search(pat, simulation_requirement, _re.IGNORECASE):
                event_refs.append(label)
        if event_refs:
            lines.append(f"Implied calendar events: {'; '.join(event_refs)}")

        return "\n".join(lines)
    
    def _build_context(
        self,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode]
    ) -> str:
        """Build the LLM context payload with safe truncation limits."""
        
        # Build entity summary
        entity_summary = self._summarize_entities(entities)

        # Extract temporal context so LLMs understand dates/deadlines in the prompt
        temporal_context = self._extract_temporal_context(simulation_requirement)
        
        # Build context payload
        context_parts = [
            f"## Simulation Requirement\n{simulation_requirement}",
            f"\n## Temporal Context\n{temporal_context}",
            f"\n## Entity Info ({len(entities)})\n{entity_summary}",
        ]

        current_length = sum(len(p) for p in context_parts)
        remaining_length = self.MAX_CONTEXT_LENGTH - current_length - 500  # 500 char buffer

        if remaining_length > 0 and document_text:
            doc_text = document_text[:remaining_length]
            if len(document_text) > remaining_length:
                doc_text += "\n...(document truncated to fit context budget)"
            context_parts.append(f"\n## Document Content\n{doc_text}")
        
        return "\n".join(context_parts)
    
    def _summarize_entities(self, entities: List[EntityNode]) -> str:
        """Create a compact, type-grouped entity summary for prompting."""
        lines = []
        
        # Group entities by type
        by_type: Dict[str, List[EntityNode]] = {}
        for e in entities:
            t = e.get_entity_type() or "Unknown"
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(e)
        
        for entity_type, type_entities in by_type.items():
            lines.append(f"\n### {entity_type} ({len(type_entities)})")
            # Use configured display count and summary length
            display_count = self.ENTITIES_PER_TYPE_DISPLAY
            summary_len = self.ENTITY_SUMMARY_LENGTH
            for e in type_entities[:display_count]:
                summary_preview = (e.summary[:summary_len] + "...") if len(e.summary) > summary_len else e.summary
                lines.append(f"- {e.name}: {summary_preview}")
            if len(type_entities) > display_count:
                lines.append(f"... and {len(type_entities) - display_count} more")
        
        return "\n".join(lines)
    
    def _call_llm_with_retry(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """Call the LLM with retries and robust JSON recovery."""
        import re
        
        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1),  # Lower temperature on retries
                    timeout=120,  # 2-minute timeout to prevent indefinite hangs
                )
                
                content = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason
                
                # Check whether truncated
                if finish_reason == 'length':
                    logger.warning(f"LLM output truncated (attempt {attempt + 1})")
                    content = self._fix_truncated_json(content)
                
                # Parse JSON
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse failed (attempt {attempt + 1}): {str(e)[:80]}")
                    
                    # Attempt JSON repair
                    fixed = self._try_fix_config_json(content)
                    if fixed:
                        return fixed
                    
                    last_error = e
                    
            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt + 1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(2 * (attempt + 1))
        
        raise last_error or Exception("LLM call failed")
    
    def _fix_truncated_json(self, content: str) -> str:
        """Repair common truncated-JSON endings by balancing braces/brackets."""
        content = content.strip()
        
        # Add closing quote if response ended in the middle of a string.
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')
        
        # Check whether the last character suggests truncation mid-string
        if content and content[-1] not in '",}]':
            content += '"'

        # Close remaining brackets and braces (only if positive)
        content += ']' * max(0, open_brackets)
        content += '}' * max(0, open_braces)
        
        return content
    
    def _try_fix_config_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Best-effort cleanup for malformed JSON-like model output."""
        import re
        
        # Fix truncated content first
        content = self._fix_truncated_json(content)

        # Extract JSON object from content
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()

            # Remove newline characters inside string values
            def fix_string(match):
                s = match.group(0)
                s = s.replace('\n', ' ').replace('\r', ' ')
                s = re.sub(r'\s+', ' ', s)
                return s
            
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string, json_str)
            
            try:
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                # Remove all control characters and retry
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                json_str = re.sub(r'\s+', ' ', json_str)
                try:
                    return json.loads(json_str)
                except (json.JSONDecodeError, ValueError):
                    pass
        
        return None
    
    def _generate_time_config(self, context: str, num_entities: int) -> Dict[str, Any]:
        """Generate timeline and activity envelope configuration."""
        # Truncate context to configured length
        context_truncated = context[:self.TIME_CONFIG_CONTEXT_LENGTH]

        today_str = datetime.now().strftime("%B %d, %Y (%A)")
        
        # Max active agents allowed (90% of total entities)
        max_agents_allowed = max(1, int(num_entities * 0.9))
        
        prompt = f"""Today is {today_str}. simulation requirement, generate timesimulation configuration.

{context_truncated}

## task
pleasegenerate time configJSON.

### basic ( reference, concreteevent group): 
- usergroup, time 
- dawn0-5 (active 0.05)
- 6-8 gradually active(active 0.4)
- time9-18 active(active 0.7)
- evening19-22 peak (active 1.5)
- 23 active (active 0.5)
-: dawn active, morning,, eveningpeak
- ** **: example reference, event, group concrete 
  -: grouppeak 21-23; media active; institution time
  -:, off_peak_hours 

### returnJSON format(do notmarkdown)

example: 
{{
    "total_simulation_hours": 72,
    "minutes_per_round": 60,
    "agents_per_hour_min": 5,
    "agents_per_hour_max": 50,
    "peak_hours": [19, 20, 21, 22],
    "off_peak_hours": [0, 1, 2, 3, 4, 5],
    "morning_hours": [6, 7, 8],
    "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    "reasoning": " event time config "
}}

field: 
- total_simulation_hours (int): simulation, 24-168, event, 
- minutes_per_round (int): round, 30-120, recommendation60 
- agents_per_hour_min (int): Agent (: 1-{max_agents_allowed})
- agents_per_hour_max (int): Agent (: 1-{max_agents_allowed})
- peak_hours (int): peak, event group 
- off_peak_hours (int):, dawn
- morning_hours (int): morning 
- work_hours (int): 
- reasoning (string): brief config"""

        system_prompt = " social media simulation.return JSON format, time config."
        
        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Time config generation failed, using defaults: {e}")
            return self._get_default_time_config(num_entities)
    
    def _get_default_time_config(self, num_entities: int) -> Dict[str, Any]:
        """Return deterministic fallback time configuration."""
        return {
            "total_simulation_hours": 72,
            "minutes_per_round": 60,  # 1 round = 1 simulated hour
            "agents_per_hour_min": max(1, num_entities // 15),
            "agents_per_hour_max": max(5, num_entities // 5),
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "morning_hours": [6, 7, 8],
            "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            "reasoning": "Default configuration (1 round per simulated hour)"
        }
    
    def _parse_time_config(self, result: Dict[str, Any], num_entities: int) -> TimeSimulationConfig:
        """Parse and clamp time config to safe operational bounds."""
        # Get agent-per-hour bounds
        agents_per_hour_min = result.get("agents_per_hour_min", max(1, num_entities // 15))
        agents_per_hour_max = result.get("agents_per_hour_max", max(5, num_entities // 5))

        # Validate: Ensure agent counts do not exceed entity count
        if agents_per_hour_min > num_entities:
            logger.warning(
                f"agents_per_hour_min ({agents_per_hour_min}) exceeds entity count ({num_entities}); clamping"
            )
            agents_per_hour_min = max(1, num_entities // 10)
        
        if agents_per_hour_max > num_entities:
            logger.warning(
                f"agents_per_hour_max ({agents_per_hour_max}) exceeds entity count ({num_entities}); clamping"
            )
            agents_per_hour_max = max(agents_per_hour_min + 1, num_entities // 2)
        
        # Ensure min < max
        if agents_per_hour_min >= agents_per_hour_max:
            agents_per_hour_min = max(1, agents_per_hour_max // 2)
            logger.warning(f"agents_per_hour_min >= agents_per_hour_max; adjusted to {agents_per_hour_min}")
        
        return TimeSimulationConfig(
            total_simulation_hours=max(24, min(168, result.get("total_simulation_hours", 72))),
            minutes_per_round=self._apply_speed_mode(
                max(30, min(120, result.get("minutes_per_round", 60))),
                max(24, min(168, result.get("total_simulation_hours", 72))),
            ),
            agents_per_hour_min=agents_per_hour_min,
            agents_per_hour_max=agents_per_hour_max,
            peak_hours=[h for h in result.get("peak_hours", [19, 20, 21, 22]) if 0 <= h <= 23],
            off_peak_hours=[h for h in result.get("off_peak_hours", [0, 1, 2, 3, 4, 5]) if 0 <= h <= 23],
            off_peak_activity_multiplier=0.05,
            morning_hours=[h for h in result.get("morning_hours", [6, 7, 8]) if 0 <= h <= 23],
            morning_activity_multiplier=0.4,
            work_hours=[h for h in result.get("work_hours", list(range(9, 19))) if 0 <= h <= 23],
            work_activity_multiplier=0.7,
            peak_activity_multiplier=1.5
        )

    @staticmethod
    def _apply_speed_mode(base_minutes_per_round: int, total_hours: int) -> int:
        """Apply speed mode overrides to minutes_per_round.

        Speed modes:
        - normal: use LLM-generated value as-is
        - fast: widen rounds to ~180 min (24 rounds for 72h)
        - express: widen rounds to ~240 min (12 rounds for 48h)
        """
        speed = Config.SIMULATION_SPEED_MODE
        if speed == "fast":
            return max(base_minutes_per_round, 180)
        elif speed == "express":
            return max(base_minutes_per_round, 240)
        return base_minutes_per_round
    
    def _generate_event_config(
        self, 
        context: str, 
        simulation_requirement: str,
        entities: List[EntityNode]
    ) -> Dict[str, Any]:
        """Generate hot-topic and initial-post event configuration."""
        
        # Get available entity types for LLM reference
        entity_types_available = list(set(
            e.get_entity_type() or "Unknown" for e in entities
        ))

        # Collect example entities per type
        type_examples = {}
        for e in entities:
            etype = e.get_entity_type() or "Unknown"
            if etype not in type_examples:
                type_examples[etype] = []
            if len(type_examples[etype]) < 3:
                type_examples[etype].append(e.name)
        
        type_info = "\n".join([
            f"- {t}: {', '.join(examples)}" 
            for t, examples in type_examples.items()
        ])
        
        # Truncate context to configured length
        context_truncated = context[:self.EVENT_CONFIG_CONTEXT_LENGTH]
        
        prompt = f""" simulation requirement, generate event config.

simulation requirement: {simulation_requirement}

{context_truncated}

## entitytype example
{type_info}

## task
pleasegenerate event configJSON: 
- 
- descriptionopinion 
- post content, **eachpostmust poster_type(publish type)**

** **: poster_type must " entitytype", post Agent publish.
: Official/University typepublish, news MediaOutlet publish, opinion Student publish.

returnJSON format(do notmarkdown): 
{{
    "hot_topics": [" 1", " 2",...],
    "narrative_direction": "<opinion description>",
    "initial_posts": [
        {{"content": "post content", "poster_type": "entitytype(must type)"}},
        ...
    ],
    "reasoning": "<brief >"
}}"""

        system_prompt = " opinionanalyze.return JSON format.note poster_type must match entitytype."
        
        try:
            return self._call_llm_with_retry(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Event config generation failed, using defaults: {e}")
            return {
                "hot_topics": [],
                "narrative_direction": "",
                "initial_posts": [],
                "reasoning": "Fallback default configuration"
            }
    
    def _parse_event_config(self, result: Dict[str, Any]) -> EventConfig:
        """Parse event config response into the EventConfig dataclass."""
        return EventConfig(
            initial_posts=result.get("initial_posts", []),
            scheduled_events=[],
            hot_topics=result.get("hot_topics", []),
            narrative_direction=result.get("narrative_direction", "")
        )
    
    def _assign_initial_post_agents(
        self,
        event_config: EventConfig,
        agent_configs: List[AgentActivityConfig]
    ) -> EventConfig:
        """Assign each initial post to a concrete agent by entity-type mapping."""
        if not event_config.initial_posts:
            return event_config
        
        # Index agents by entity type
        agents_by_type: Dict[str, List[AgentActivityConfig]] = {}
        for agent in agent_configs:
            etype = agent.entity_type.lower()
            if etype not in agents_by_type:
                agents_by_type[etype] = []
            agents_by_type[etype].append(agent)
        
        # Type aliases (to handle variations in LLM output)
        type_aliases = {
            "official": ["official", "university", "governmentagency", "government"],
            "university": ["university", "official"],
            "mediaoutlet": ["mediaoutlet", "media"],
            "student": ["student", "person"],
            "professor": ["professor", "expert", "teacher"],
            "alumni": ["alumni", "person"],
            "organization": ["organization", "ngo", "company", "group"],
            "person": ["person", "student", "alumni"],
        }
        
        # Track per-type round-robin index so the same agent is not always selected.
        used_indices: Dict[str, int] = {}
        
        updated_posts = []
        for post in event_config.initial_posts:
            poster_type = post.get("poster_type", "").lower()
            content = post.get("content", "")
            
            # Match to a concrete agent
            matched_agent_id = None

            # 1. Direct type match
            if poster_type in agents_by_type:
                agents = agents_by_type[poster_type]
                idx = used_indices.get(poster_type, 0) % len(agents)
                matched_agent_id = agents[idx].agent_id
                used_indices[poster_type] = idx + 1
            else:
                # 2. Alias match
                for alias_key, aliases in type_aliases.items():
                    if poster_type in aliases or alias_key == poster_type:
                        for alias in aliases:
                            if alias in agents_by_type:
                                agents = agents_by_type[alias]
                                idx = used_indices.get(alias, 0) % len(agents)
                                matched_agent_id = agents[idx].agent_id
                                used_indices[alias] = idx + 1
                                break
                    if matched_agent_id is not None:
                        break
            
            # 3. Final fallback: choose highest-influence agent.
            if matched_agent_id is None:
                logger.warning(
                    f"No agent type match for poster_type='{poster_type}'; using highest-influence fallback"
                )
                if agent_configs:
                    # Sort by influence weight descending and pick the top agent
                    sorted_agents = sorted(agent_configs, key=lambda a: a.influence_weight, reverse=True)
                    matched_agent_id = sorted_agents[0].agent_id
                else:
                    matched_agent_id = 0
            
            updated_posts.append({
                "content": content,
                "poster_type": post.get("poster_type", "Unknown"),
                "poster_agent_id": matched_agent_id
            })
            
            logger.info(f"Initial post mapping: poster_type='{poster_type}' -> agent_id={matched_agent_id}")
            
        
        event_config.initial_posts = updated_posts
        return event_config

    def _generate_geopolitical_events(
        self,
        simulation_requirement: str,
        time_config: "TimeSimulationConfig",
        entities: List[EntityNode],
        context: str = "",
    ) -> List[Dict[str, Any]]:
        """Generate potential geopolitical disruption events using LLM + live news.

        These are injected into EventConfig.scheduled_events so the OASIS
        simulation can trigger mid-run narrative disruptions.
        """
        total_rounds = max(
            1,
            int(time_config.total_simulation_hours * 60 / time_config.minutes_per_round),
        )
        target_event_count = self._plan_geopolitical_event_count(total_rounds)
        intelligence_brief = self._build_geopolitical_intelligence_brief(
            simulation_requirement=simulation_requirement,
            entities=entities,
            context=context,
        )

        today_str = datetime.now().strftime("%B %d, %Y")

        # Gather real-world context from web intelligence (best-effort)
        real_context = ""
        web_intel_available = False
        headlines_for_citation = []
        try:
            from .web_intelligence import NewsScraperService
            svc = NewsScraperService()
            if svc.enabled:
                # Use dedicated geopolitical search with focused queries
                data = svc.search_geopolitical_news(
                    simulation_requirement=simulation_requirement,
                    entities=entities,
                    max_articles=max(6, target_event_count + 2),
                    additional_queries=intelligence_brief.get("search_queries", []),
                )
                real_context = (data.get("combined_text", "") or "")[:6000]
                headlines_for_citation = data.get("headlines", [])
                if real_context.strip():
                    web_intel_available = True
                    logger.info(
                        f"Geopolitical events grounded with {len(real_context)} chars of live context, "
                        f"{len(headlines_for_citation)} headlines"
                    )
                else:
                    logger.warning("Web intelligence returned empty — events will rely on LLM knowledge only")
            else:
                logger.warning("SERPER_API_KEY not loaded — geopolitical events will rely on LLM knowledge only")
        except Exception as e:
            logger.warning(f"Web intelligence unavailable for geopolitical events: {e}")

        entity_types = list(set(
            e.get_entity_type() or "Unknown" for e in entities
        ))

        # Build entity name examples per type so the LLM is grounded in the scenario
        type_examples: Dict[str, List[str]] = {}
        for e in entities:
            etype = e.get_entity_type() or "Unknown"
            if etype not in type_examples:
                type_examples[etype] = []
            if len(type_examples[etype]) < 4:
                type_examples[etype].append(e.name)
        entity_examples_str = "\n".join(
            f"  {t}: {', '.join(names)}" for t, names in type_examples.items()
        )

        # Include truncated document/scenario context for geographic anchoring
        scenario_context = context[:6000] if context else ""

        # Extract temporal intelligence from the user's prompt
        temporal_context = self._extract_temporal_context(simulation_requirement)
        intelligence_brief_json = json.dumps({
            "priority_entities": intelligence_brief.get("priority_entities", []),
            "priority_entity_types": intelligence_brief.get("priority_entity_types", []),
            "topic_keywords": intelligence_brief.get("topic_keywords", []),
            "regional_keywords": intelligence_brief.get("regional_keywords", []),
            "search_queries": intelligence_brief.get("search_queries", []),
        }, ensure_ascii=False, indent=2)

        # Build the real-world grounding block
        if web_intel_available:
            # Build a headline list the LLM must cite
            headline_block = ""
            if headlines_for_citation:
                hl_lines = "\n".join(f"  - {h}" for h in headlines_for_citation[:10])
                headline_block = f"""
## REAL HEADLINES (you MUST base events on these, not fabricate new ones):
{hl_lines}
"""
            real_world_block = f"""
## CURRENT REAL-WORLD INTELLIGENCE (as of {today_str})
The following is LIVE data retrieved from news sources and social media. You MUST use
this to ground your events in reality. Do NOT contradict facts stated here.

{real_context}
{headline_block}
INSTRUCTIONS FOR USING REAL-WORLD CONTEXT:
- Each event you generate MUST be based on or inspired by one of the REAL HEADLINES above.
- In each event description, include a "source_hint" that quotes or paraphrases the real
  headline it is based on. Example: "...following reports that [Reuters] SEBI tightens margin rules."
- If the news reports specific ongoing events (e.g., actual trade disputes, actual policy
  changes, actual economic data), base your disruption events on realistic ESCALATIONS
  or CONSEQUENCES of those real events — not fabricated ones.
- If inflation is currently falling, do NOT generate an inflation surge event.
- If there is no trade war happening, do NOT fabricate one — pick a different category.
- Reference specific real entities, policies, or data points from the news above."""
        else:
            real_world_block = f"""
## NOTE: No live news data was available for grounding (as of {today_str}).
Generate events based on realistic, currently plausible risks for the specific geography,
sector, and entities in this scenario. Avoid generic textbook scenarios.
Prefer risks that are specific to the named companies and institutions listed below."""

        prompt = f"""You are a senior geopolitical risk analyst producing disruption events
for a simulation. Today's date is {today_str}.

Generate exactly {target_event_count} disruptive events that are SPECIFIC, PLAUSIBLE, and GROUNDED in the real
world for the scenario below. Events will be injected at specific rounds during a
{time_config.total_simulation_hours}-hour simulation ({total_rounds} rounds).

## SCENARIO
{simulation_requirement}

## SCENARIO CONTEXT
{scenario_context}

## TEMPORAL CONTEXT
{temporal_context}
Events must be consistent with this timeline. If the user specifies a particular date,
timeframe, or deadline, events should be plausible within that window.

## ENTITIES IN SIMULATION
{entity_examples_str}

Entity types present: {', '.join(entity_types)}

## INTELLIGENCE BRIEF
Use this to reason globally first, then localize to the scenario.
{intelligence_brief_json}
{real_world_block}

Event categories: {', '.join(GEOPOLITICAL_CATEGORIES)}

## QUALITY REQUIREMENTS — READ CAREFULLY
1. SPECIFICITY: Name real institutions, policies, regulatory bodies, or trade agreements
   relevant to the scenario. "Government announces new tax regulations" is TOO VAGUE.
   Instead: "SEBI tightens margin requirements for F&O segment" or "RBI raises repo rate
   by 25bps citing food price pressures".
2. PLAUSIBILITY: Each event must be something that could realistically happen given
   current conditions. Do not invent crises that contradict available real-world data.
3. ENTITY GROUNDING: Reference specific entity names from the simulation where possible.
   "Tariffs on steel" should become "15% safeguard duty on steel imports affecting SAIL
   and Tata Steel" if those entities are in the simulation.
    At least 70% of events should explicitly name one or more scenario entities or entity types.
4. CAUSAL CHAIN: Each event description must explain the immediate mechanism of impact,
   not just state that something happened. HOW does this event affect the named entities?
5. TEMPORAL SPREAD: Distribute trigger rounds across the timeline — early, mid, and late.
   Not all events should be negative; include at least one that has a mixed or positive angle.
6. MAGNITUDE CALIBRATION: Reserve impact factors beyond +/-0.7 for truly extreme events.
   Most realistic disruptions land between -0.5 and +0.3.
7. Do NOT generate generic events like "unexpected inflation surge" or "new tax regulations"
   without naming the specific policy, regulator, or mechanism.

Return JSON only (no markdown fences):
{{
    "events": [
        {{
            "trigger_round": <int, 1 to {total_rounds}>,
            "category": "<category from list>",
            "title": "<specific event title, max 10 words>",
            "description": "<1-2 sentences: what happened, which mechanism, who is affected and how>",
            "source_hint": "<headline or real-world anchor; required when live news is available>",
            "impact_factor": <float -1.0 to 1.0>,
            "affected_entity_types": ["<entity types impacted>"],
            "severity": "<low|medium|high|critical>"
        }}
    ]
}}"""

        system_prompt = (
            "You are a senior geopolitical risk analyst specializing in scenario simulation. "
            "You generate SPECIFIC, institution-naming, mechanism-explaining disruption events "
            "grounded in real-world conditions. Never produce generic or textbook events. "
            "Return valid JSON only — no markdown fences, no commentary."
        )

        # Known foreign-only agencies/terms that signal irrelevant events
        FOREIGN_MARKERS = {
            "fda", "sec ", "epa", "fbi", "cia", "pentagon", "congress",
            "u.s.", "us port", "us government", "american", "european union",
            "eu commission", "boe", "bank of england", "ecb",
        }

        # Expanded generic markers — catches partial substring matches (all lowercase)
        GENERIC_TITLE_MARKERS = [
            "unexpected inflation surge", "inflation surge",
            "new tax regulations", "new tax regulation", "tax regulations",
            "trade tensions escalate", "trade tensions",
            "government announces", "government announcement",
            "market shock", "sudden market",
            "economic downturn", "economic slowdown",
            "global recession", "recession fears",
            "policy change announced", "policy change",
            "new regulations introduced", "new regulations",
            "sudden market crash",
            "regulatory change", "regulatory changes",
            "interest rate hike",
            "supply chain disruption",
            "geopolitical tension", "geopolitical tensions",
            "market volatility",
            "economic uncertainty",
            "financial crisis",
            "currency fluctuation", "currency devaluation",
        ]

        entity_names = intelligence_brief.get("priority_entities", [])
        entity_types_lower = {
            entity_type.lower(): entity_type
            for entity_type in intelligence_brief.get("priority_entity_types", [])
        }
        mechanism_markers = {
            "sanction", "tariff", "ceasefire", "blockade", "export control", "repo rate",
            "margin requirement", "wto", "shipping", "strait", "pipeline", "embargo",
            "policy", "regulator", "regulatory", "cyber", "election", "strike",
            "port", "customs", "central bank", "ministry", "oil", "gas",
        }
        category_keywords = {
            "natural_disaster": ["earthquake", "flood", "storm", "wildfire", "cyclone"],
            "armed_conflict": ["war", "missile", "drone", "conflict", "ceasefire", "military"],
            "political_turmoil": ["cabinet", "protest", "coalition", "impeachment", "leadership"],
            "trade_war": ["tariff", "export control", "trade", "customs", "import duty"],
            "sanctions": ["sanction", "embargo", "blacklist", "restriction"],
            "policy_change": ["policy", "mandate", "subsidy", "framework"],
            "diplomatic_crisis": ["embassy", "diplomatic", "consulate", "envoy"],
            "economic_shock": ["inflation", "fx", "currency", "bond", "bank", "yield"],
            "pandemic": ["pandemic", "virus", "outbreak", "variant"],
            "supply_chain_disruption": ["shipping", "port", "logistics", "container", "route"],
            "election": ["election", "vote", "ballot", "poll"],
            "regulatory_change": ["regulator", "regulatory", "circular", "compliance"],
            "civil_unrest": ["riot", "strike", "unrest", "demonstration"],
            "cyber_attack": ["cyber", "ransomware", "hack", "breach"],
        }

        def _infer_category(raw_category: Any, combined_text: str) -> str:
            category = str(raw_category or "").strip().lower()
            if category in GEOPOLITICAL_CATEGORIES:
                return category
            for candidate, markers in category_keywords.items():
                if any(marker in combined_text for marker in markers):
                    return candidate
            return "economic_shock"

        def _specificity_score(title: str, description: str, grounded_in_news: bool) -> int:
            combined_text = f"{title} {description}".lower()
            score = 0
            if grounded_in_news:
                score += 2
            if any(entity_name.lower() in combined_text for entity_name in entity_names):
                score += 3
            if any(entity_type in combined_text for entity_type in entity_types_lower):
                score += 1
            if any(marker in combined_text for marker in mechanism_markers):
                score += 2
            if re.search(r"\b\d+(?:\.\d+)?%|\b\d+\s?(?:bps|basis points|million|billion)\b", combined_text):
                score += 1
            if re.search(r"\b(?:rbi|sebi|wto|opec|imf|fed|ecb|un|eu)\b", combined_text):
                score += 1
            return score

        def _validate_and_filter(raw_events):
            """Return (validated_events, rejected_titles)."""
            # If we have real headlines, relax the generic filter — an event matching
            # a real headline is NOT generic even if its title looks simple
            headline_text_lower = " ".join(headlines_for_citation).lower() if headlines_for_citation else ""
            ok, rejected = [], []
            for evt in raw_events[:max(target_event_count * 2, target_event_count + 2)]:
                title = str(evt.get("title", "Unnamed Event"))[:80]
                description = str(evt.get("description", ""))[:360]
                source_hint = str(evt.get("source_hint", ""))[:180]
                combined_text = f"{title} {description}".lower()
                title_lower = title.lower()

                is_foreign = any(marker in combined_text for marker in FOREIGN_MARKERS)
                if is_foreign:
                    scenario_lower = simulation_requirement.lower()
                    if not any(marker in scenario_lower for marker in FOREIGN_MARKERS):
                        logger.warning(f"Filtered geographically irrelevant event: '{title}'")
                        rejected.append(title)
                        continue

                is_generic = any(marker in title_lower for marker in GENERIC_TITLE_MARKERS)
                grounded_in_news = headline_text_lower and any(
                    word in headline_text_lower
                    for word in [w for w in title_lower.split() if len(w) > 3]
                )
                specificity = _specificity_score(title, description, bool(grounded_in_news))
                if is_generic:
                    if specificity < 4:
                        logger.warning(f"Filtered generic event (lacks specificity): '{title}'")
                        rejected.append(title)
                        continue
                    else:
                        logger.info(f"Generic-looking event kept after specificity check: '{title}'")

                if web_intel_available and not source_hint and not grounded_in_news:
                    logger.warning(f"Filtered ungrounded event without source hint: '{title}'")
                    rejected.append(title)
                    continue

                if specificity < 3:
                    logger.warning(f"Filtered low-specificity geopolitical event: '{title}'")
                    rejected.append(title)
                    continue

                detected_types = [
                    entity_type for key, entity_type in entity_types_lower.items()
                    if key in combined_text
                ]
                affected_types = [
                    str(entity_type)[:30]
                    for entity_type in evt.get("affected_entity_types", [])[:5]
                    if str(entity_type).lower() in entity_types_lower
                ]
                if not affected_types and detected_types:
                    affected_types = detected_types[:3]
                if not affected_types:
                    affected_types = intelligence_brief.get("priority_entity_types", [])[:3]

                if not affected_types and not grounded_in_news:
                    logger.warning(f"Filtered event without entity or type grounding: '{title}'")
                    rejected.append(title)
                    continue

                trigger = max(1, min(total_rounds, int(evt.get("trigger_round", 1))))
                impact = max(-1.0, min(1.0, float(evt.get("impact_factor", 0.0))))
                if abs(impact) > 0.8:
                    impact = 0.8 * (1.0 if impact > 0 else -1.0)
                severity = evt.get("severity", "medium")
                if severity not in ("low", "medium", "high", "critical"):
                    severity = "medium"

                ok.append({
                    "trigger_round": trigger,
                    "category": _infer_category(evt.get("category", "other"), combined_text),
                    "title": title,
                    "description": description,
                    "source_hint": source_hint,
                    "impact_factor": round(impact, 2),
                    "affected_entity_types": affected_types,
                    "severity": severity,
                })
                logger.info(
                    f"Geopolitical event accepted: round={trigger}, "
                    f"category={evt.get('category')}, title={title}"
                )
            return ok, rejected

        MAX_GEO_RETRIES = 3
        active_prompt = prompt
        all_rejected = []

        for geo_attempt in range(MAX_GEO_RETRIES):
            try:
                result = self._call_llm_with_retry(active_prompt, system_prompt)
                raw_events = result.get("events", [])
            except Exception as exc:
                logger.warning(f"Geopolitical event generation failed (attempt {geo_attempt + 1}): {exc}")
                return []

            validated, rejected = _validate_and_filter(raw_events)
            all_rejected.extend(rejected)

            if validated:
                return self._spread_geopolitical_events(validated, total_rounds, target_event_count)

            if not raw_events:
                logger.warning("LLM returned zero geopolitical events — skipping.")
                return []

            logger.warning(
                f"All {len(raw_events)} geopolitical events were filtered as generic "
                f"(attempt {geo_attempt + 1}/{MAX_GEO_RETRIES}). Retrying with penalty prompt."
            )
            rejected_list = "\n".join(f'  - "{t}"' for t in all_rejected[:8])
            active_prompt = (
                prompt
                + f"\n\n## CRITICAL REJECTION NOTICE (attempt {geo_attempt + 2})\n"
                + "Your previous response was ENTIRELY REJECTED — every event title was too generic.\n"
                + f"REJECTED TITLES:\n{rejected_list}\n\n"
                + "You MUST fix this. Each new title MUST:\n"
                + "1. Name the SPECIFIC regulator, law, institution, or policy instrument involved.\n"
                + "2. Name at least one entity from the simulation by its exact name.\n"
                + "3. Reference a real mechanism (e.g. SEBI circular, RBI repo rate, WTO dispute panel).\n"
                + "Generic titles like 'Inflation Surge' or 'New Tax Regulations' will be auto-rejected.\n"
            )

        logger.warning("Geopolitical events: all retry attempts exhausted, no valid events produced.")
        return []

    @staticmethod
    def _plan_geopolitical_event_count(total_rounds: int) -> int:
        """Scale geopolitical event count with simulation duration."""
        return max(3, min(8, math.ceil(max(1, total_rounds) / 12)))

    @staticmethod
    def _extract_geopolitical_keywords(text: str, limit: int = 10) -> List[str]:
        """Extract scenario keywords for geopolitical retrieval and grounding."""
        keyword_patterns = [
            r'\b(?:iran|israel|gaza|ukraine|russia|china|taiwan|india|pakistan|red sea|hormuz|opec|brics)\b',
            r'\b(?:sanctions?|tariffs?|trade war|shipping|strait|oil|gas|energy|cyber|election|currency|inflation|supply chain)\b',
            r'\b(?:semiconductor|banking|steel|defense|telecom|shipping|aviation|pharma|agriculture)\b',
        ]
        found = []
        lowered = text.lower()
        for pattern in keyword_patterns:
            found.extend(match.group(0) for match in re.finditer(pattern, lowered, re.IGNORECASE))

        title_case_matches = re.findall(r'\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b', text)
        found.extend(title_case_matches)

        unique = []
        seen = set()
        for keyword in found:
            normalized = " ".join(keyword.lower().split())
            if len(normalized) < 3 or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(keyword.strip())
            if len(unique) >= limit:
                break
        return unique

    @classmethod
    def _build_geopolitical_intelligence_brief(
        cls,
        simulation_requirement: str,
        entities: List[EntityNode],
        context: str = "",
    ) -> Dict[str, Any]:
        """Build a scenario-aware intelligence brief and search plan."""
        combined_text = "\n".join(part for part in [simulation_requirement, context[:3000]] if part)

        priority_entities = []
        seen_entities = set()
        priority_entity_types = []
        seen_types = set()
        for entity in entities:
            if entity.name and entity.name.lower() not in seen_entities and len(priority_entities) < 10:
                priority_entities.append(entity.name)
                seen_entities.add(entity.name.lower())
            entity_type = entity.get_entity_type() or "Unknown"
            if entity_type.lower() not in seen_types and len(priority_entity_types) < 6:
                priority_entity_types.append(entity_type)
                seen_types.add(entity_type.lower())

        topic_keywords = cls._extract_geopolitical_keywords(combined_text, limit=10)
        regional_keywords = [
            keyword for keyword in topic_keywords
            if keyword.lower() in {"iran", "israel", "gaza", "ukraine", "russia", "china", "taiwan", "india", "pakistan", "red sea", "hormuz"}
        ][:4]

        search_queries = [
            "global geopolitical risk sanctions conflict shipping energy cyber latest news",
            "global supply chain disruption trade policy sanctions election cyber risk latest news",
        ]
        if topic_keywords:
            search_queries.append(" ".join(topic_keywords[:4]) + " latest news")
        if regional_keywords:
            search_queries.append(" ".join(regional_keywords[:3]) + " conflict sanctions shipping policy latest news")
        if priority_entities:
            search_queries.append(" ".join(priority_entities[:3]) + " regulation sanctions market impact news")
        if priority_entity_types:
            search_queries.append(" ".join(priority_entity_types[:3]) + " sector geopolitical policy disruption news")

        deduped_queries = []
        seen_queries = set()
        for query in search_queries:
            normalized = " ".join(query.lower().split())
            if normalized not in seen_queries:
                deduped_queries.append(query[:220])
                seen_queries.add(normalized)

        return {
            "priority_entities": priority_entities,
            "priority_entity_types": priority_entity_types,
            "topic_keywords": topic_keywords,
            "regional_keywords": regional_keywords,
            "search_queries": deduped_queries[:6],
        }

    @staticmethod
    def _spread_geopolitical_events(
        events: List[Dict[str, Any]],
        total_rounds: int,
        target_event_count: int,
    ) -> List[Dict[str, Any]]:
        """Spread accepted events across the simulation timeline."""
        if not events:
            return []

        deduped = []
        seen_titles = set()
        for event in sorted(events, key=lambda item: (item.get("trigger_round", 1), -abs(item.get("impact_factor", 0)))):
            title_key = str(event.get("title", "")).strip().lower()
            if not title_key or title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            deduped.append(dict(event))
            if len(deduped) >= target_event_count:
                break

        anchor_rounds = [
            max(1, min(total_rounds, round(total_rounds * (idx + 1) / (len(deduped) + 1))))
            for idx in range(len(deduped))
        ]

        spread = []
        previous_round = 0
        for event, anchor in zip(deduped, anchor_rounds):
            trigger_round = max(1, min(total_rounds, int(event.get("trigger_round", anchor))))
            if abs(trigger_round - anchor) > max(2, total_rounds // max(6, len(deduped) * 2)):
                trigger_round = anchor
            if trigger_round <= previous_round:
                trigger_round = min(total_rounds, previous_round + 1)
            event["trigger_round"] = trigger_round
            spread.append(event)
            previous_round = trigger_round

        return spread

    def _generate_agent_configs_batch(
        self,
        context: str,
        entities: List[EntityNode],
        start_idx: int,
        simulation_requirement: str
    ) -> List[AgentActivityConfig]:
        """Generate behavior configs for one batch of entities."""
        
        # Build entity info (using configured summary length)
        entity_list = []
        summary_len = self.AGENT_SUMMARY_LENGTH
        for i, e in enumerate(entities):
            entity_list.append({
                "agent_id": start_idx + i,
                "entity_name": e.name,
                "entity_type": e.get_entity_type() or "Unknown",
                "summary": e.summary[:summary_len] if e.summary else ""
            })
        
        prompt = f""" info, eachentitygeneratesocialmedia config.

simulation requirement: {simulation_requirement}

## entitylist
```json
{json.dumps(entity_list, ensure_ascii=False, indent=2)}
```

## task
 eachentitygenerate config, note: 
- **time **: dawn0-5, evening19-22 active
- ** institution**(University/GovernmentAgency): active (0.1-0.3), time(9-17), (60-240), influence (2.5-3.0)
- **media**(MediaOutlet): active (0.4-0.6), (8-23), (5-30), influence (2.0-2.5)
- **personal**(Student/Person/Alumni): active (0.6-0.9), mainevening (18-23), (1-15), influence (0.8-1.2)
- ** / **: active (0.4-0.6), influence (1.5-2.0)

returnJSON format(do notmarkdown): 
{{
    "agent_configs": [
        {{
            "agent_id": <must input >,
            "activity_level": <0.0-1.0>,
            "posts_per_hour": < frequency>,
            "comments_per_hour": <commentfrequency>,
            "active_hours": [<active list, >],
            "response_delay_min": <min >,
            "response_delay_max": <max >,
            "sentiment_bias": <-1.0 1.0>,
            "stance": "<supportive/opposing/neutral/observer>",
            "influence_weight": <influence >
        }},
        ...
    ]
}}"""

        system_prompt = " socialmediabehavioranalyze.return JSON, config."
        
        try:
            result = self._call_llm_with_retry(prompt, system_prompt)
            llm_configs = {cfg["agent_id"]: cfg for cfg in result.get("agent_configs", [])}
        except Exception as e:
            logger.warning(f"Agent config batch generation failed; falling back to rules: {e}")
            llm_configs = {}
        
        # Build AgentActivityConfig objects
        configs = []
        for i, entity in enumerate(entities):
            agent_id = start_idx + i
            cfg = llm_configs.get(agent_id, {})
            
            # Fall back to deterministic defaults when model output is missing.
            if not cfg:
                cfg = self._generate_agent_config_by_rule(entity)
            
            config = AgentActivityConfig(
                agent_id=agent_id,
                entity_uuid=entity.uuid,
                entity_name=entity.name,
                entity_type=entity.get_entity_type() or "Unknown",
                activity_level=max(0.0, min(1.0, cfg.get("activity_level", 0.5))),
                posts_per_hour=max(0.0, min(20.0, cfg.get("posts_per_hour", 0.5))),
                comments_per_hour=max(0.0, min(50.0, cfg.get("comments_per_hour", 1.0))),
                active_hours=[h for h in cfg.get("active_hours", list(range(9, 23))) if 0 <= h <= 23],
                response_delay_min=max(1, min(600, cfg.get("response_delay_min", 5))),
                response_delay_max=max(1, min(1440, cfg.get("response_delay_max", 60))),
                sentiment_bias=max(-1.0, min(1.0, cfg.get("sentiment_bias", 0.0))),
                stance=cfg.get("stance", "neutral") if cfg.get("stance") in ("supportive", "opposing", "neutral", "observer") else "neutral",
                influence_weight=max(0.1, min(10.0, cfg.get("influence_weight", 1.0)))
            )
            configs.append(config)
        
        return configs
    
    def _generate_agent_config_by_rule(self, entity: EntityNode) -> Dict[str, Any]:
        """Rule-based fallback for agent behavior when LLM output is unavailable."""
        entity_type = (entity.get_entity_type() or "Unknown").lower()
        
        if entity_type in ["university", "governmentagency", "ngo"]:
            # Institutions: business hours only, low frequency, high influence
            return {
                "activity_level": 0.2,
                "posts_per_hour": 0.1,
                "comments_per_hour": 0.05,
                "active_hours": list(range(9, 18)), # 9:00-17:59
                "response_delay_min": 60,
                "response_delay_max": 240,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 3.0
            }
        elif entity_type in ["mediaoutlet"]:
            # Media: long active hours, moderate frequency, high influence
            return {
                "activity_level": 0.5,
                "posts_per_hour": 0.8,
                "comments_per_hour": 0.3,
                "active_hours": list(range(7, 24)), # 7:00-23:59
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "observer",
                "influence_weight": 2.5
            }
        elif entity_type in ["professor", "expert", "official"]:
            # Experts/officials: work hours + evening, moderate frequency
            return {
                "activity_level": 0.4,
                "posts_per_hour": 0.3,
                "comments_per_hour": 0.5,
                "active_hours": list(range(8, 22)), # 8:00-21:59
                "response_delay_min": 15,
                "response_delay_max": 90,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 2.0
            }
        elif entity_type in ["student"]:
            # Students: mainly evening activity, high frequency
            return {
                "activity_level": 0.8,
                "posts_per_hour": 0.6,
                "comments_per_hour": 1.5,
                "active_hours": [8, 9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23], # morning+evening
                "response_delay_min": 1,
                "response_delay_max": 15,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 0.8
            }
        elif entity_type in ["alumni"]:
            # Alumni: lunch break + evening activity
            return {
                "activity_level": 0.6,
                "posts_per_hour": 0.4,
                "comments_per_hour": 0.8,
                "active_hours": [12, 13, 19, 20, 21, 22, 23],  # lunch + evening
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0
            }
        else:
            # Default: evening peak activity, with individual variance
            import random
            base_activity = random.uniform(0.4, 0.85)
            base_posts = random.uniform(0.2, 0.8)
            base_comments = random.uniform(0.5, 1.8)
            # Randomize stance to avoid all-neutral herding
            stance = random.choice(["supportive", "opposing", "neutral", "neutral", "observer"])
            return {
                "activity_level": round(base_activity, 2),
                "posts_per_hour": round(base_posts, 2),
                "comments_per_hour": round(base_comments, 2),
                "active_hours": [9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23],  # work hours + evening
                "response_delay_min": random.randint(1, 10),
                "response_delay_max": random.randint(15, 45),
                "sentiment_bias": round(random.uniform(-0.3, 0.3), 2),
                "stance": stance,
                "influence_weight": round(random.uniform(0.6, 1.4), 2)
            }

    def _calibrate_agent_configs(
        self,
        agent_configs: List[AgentActivityConfig],
        time_config: TimeSimulationConfig
    ) -> List[AgentActivityConfig]:
        """Calibrate LLM-generated configs to avoid unstable simulation dynamics."""
        if not agent_configs:
            return agent_configs

        profile = self.CALIBRATION_PROFILES[self.calibration_mode]
        active_agents_cap = max(1, min(len(agent_configs), time_config.agents_per_hour_max))
        target_posts_per_hour = max(1.0, active_agents_cap * profile["post_target_per_active_agent"])
        target_comments_per_hour = max(2.0, active_agents_cap * profile["comment_target_per_active_agent"])

        current_posts = sum(a.posts_per_hour for a in agent_configs)
        current_comments = sum(a.comments_per_hour for a in agent_configs)

        post_scale = 1.0
        comment_scale = 1.0
        if current_posts > target_posts_per_hour * profile["volume_overage_allowance"]:
            post_scale = (target_posts_per_hour * profile["volume_overage_allowance"]) / max(current_posts, 1e-6)
        if current_comments > target_comments_per_hour * profile["volume_overage_allowance"]:
            comment_scale = (target_comments_per_hour * profile["volume_overage_allowance"]) / max(current_comments, 1e-6)

        default_hours = sorted(set(
            time_config.morning_hours + time_config.work_hours + time_config.peak_hours
        ))
        if not default_hours:
            default_hours = list(range(9, 23))

        for agent in agent_configs:
            entity_type = (agent.entity_type or "unknown").lower()

            if entity_type in {"governmentagency", "university", "official"}:
                agent.activity_level = min(agent.activity_level, 0.45)
                agent.influence_weight = max(agent.influence_weight, 1.8)
            elif entity_type in {"mediaoutlet", "journalist"}:
                agent.activity_level = max(agent.activity_level, 0.45)
                agent.influence_weight = max(agent.influence_weight, 1.6)

            agent.activity_level = max(0.0, min(profile["max_activity_level"], agent.activity_level))
            agent.posts_per_hour = max(0.0, min(profile["max_posts_per_hour"], agent.posts_per_hour * post_scale))
            agent.comments_per_hour = max(0.0, min(profile["max_comments_per_hour"], agent.comments_per_hour * comment_scale))

            if not agent.active_hours:
                agent.active_hours = default_hours
            else:
                cleaned_hours = sorted({h for h in agent.active_hours if 0 <= h <= 23})
                agent.active_hours = cleaned_hours or default_hours

            # Add per-agent hour variance to prevent all agents peaking simultaneously.
            # Shift active hours by ±1-2 hours for each agent to create realistic staggering.
            import random
            hour_shift = random.choice([-2, -1, 0, 0, 1, 2])
            if hour_shift != 0 and len(agent.active_hours) > 3:
                shifted = sorted({max(0, min(23, h + hour_shift)) for h in agent.active_hours})
                agent.active_hours = shifted

            agent.response_delay_min = max(1, min(600, int(agent.response_delay_min)))
            agent.response_delay_max = max(
                agent.response_delay_min + 1,
                min(profile["max_response_delay"], int(agent.response_delay_max))
            )

        return agent_configs

    def _align_initial_posts(
        self,
        event_config: EventConfig,
        agent_configs: List[AgentActivityConfig]
    ) -> EventConfig:
        """Trim and normalize initial posts to match available active agents."""
        if not event_config.initial_posts:
            return event_config

        max_posts = max(1, min(12, len(agent_configs) // 2 if agent_configs else 1))
        trimmed = event_config.initial_posts[:max_posts]

        normalized_posts = []
        for post in trimmed:
            content = str(post.get("content", "")).strip()
            if not content:
                continue
            normalized_posts.append({
                "content": content[:400],
                "poster_type": str(post.get("poster_type", "Person"))[:64],
                "poster_agent_id": post.get("poster_agent_id")
            })

        event_config.initial_posts = normalized_posts
        return event_config

    def _normalize_platform_config(self, config: PlatformConfig) -> PlatformConfig:
        """Ensure ranking weights are stable and sum to 1.0."""
        weights = [
            max(0.0, config.recency_weight),
            max(0.0, config.popularity_weight),
            max(0.0, config.relevance_weight),
        ]
        total = sum(weights)
        if total <= 0:
            config.recency_weight = 0.34
            config.popularity_weight = 0.33
            config.relevance_weight = 0.33
            return config

        config.recency_weight = round(weights[0] / total, 3)
        config.popularity_weight = round(weights[1] / total, 3)
        config.relevance_weight = round(weights[2] / total, 3)
        return config

    def _build_quality_summary(
        self,
        simulation_requirement: str,
        entities: List[EntityNode],
        time_config: TimeSimulationConfig,
        agent_configs: List[AgentActivityConfig],
        event_config: EventConfig
    ) -> str:
        """Generate a compact quality note for observability and debugging."""
        total_posts = round(sum(a.posts_per_hour for a in agent_configs), 2)
        total_comments = round(sum(a.comments_per_hour for a in agent_configs), 2)
        active_span = len({h for a in agent_configs for h in a.active_hours}) if agent_configs else 0
        scenario_size = "broad" if len(simulation_requirement) > 280 else "focused"

        return (
            f"quality: entities={len(entities)}, agents={len(agent_configs)}, "
            f"calibration_mode={self.calibration_mode}, "
            f"scenario={scenario_size}, sim_hours={time_config.total_simulation_hours}, "
            f"init_posts={len(event_config.initial_posts)}, posts_per_hour={total_posts}, "
            f"comments_per_hour={total_comments}, active_hour_coverage={active_span}/24"
        )
    


