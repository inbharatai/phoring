"""Report Agent service.

Generates simulation reports with a ReACT-style loop over Zep-backed tools,
supports staged section generation, and provides report-grounded chat.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from..config import Config
from..utils.llm_client import LLMClient
from..utils.logger import get_logger
from.zep_tools import ZepToolsService

logger = get_logger('phoring.report_agent')


class ReportLogger:
    """Structured JSONL logger for report-generation actions.

    Writes one JSON object per line to `agent_log.jsonl` with timestamp,
    stage, action type, and contextual details.
    """
    
    def __init__(self, report_id: str):
        """Initialize report action logger for a report ID."""
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'agent_log.jsonl'
        )
        self.start_time = datetime.now()
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Ensure the target log directory exists."""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _get_elapsed_time(self) -> float:
        """Return elapsed seconds since logger initialization."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def log(
        self, 
        action: str, 
        stage: str,
        details: Dict[str, Any],
        section_title: str = None,
        section_index: int = None
    ):
        """Append one structured log entry to `agent_log.jsonl`."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(self._get_elapsed_time(), 2),
            "report_id": self.report_id,
            "action": action,
            "stage": stage,
            "section_title": section_title,
            "section_index": section_index,
            "details": details
        }
        
        # Write one JSON object per line.
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def log_start(self, simulation_id: str, graph_id: str, simulation_requirement: str):
        """Log report-generation start metadata."""
        self.log(
            action="report_start",
            stage="pending",
            details={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "simulation_requirement": simulation_requirement,
                "message": "Report generation started"
            }
        )
    
    def log_planning_start(self):
        """Log outline planning start."""
        self.log(
            action="planning_start",
            stage="planning",
            details={"message": "Outline planning started"}
        )
    
    def log_planning_context(self, context: Dict[str, Any]):
        """Log planning context snapshot."""
        self.log(
            action="planning_context",
            stage="planning",
            details={
                "message": "Loaded simulation context",
                "context": context
            }
        )
    
    def log_planning_complete(self, outline_dict: Dict[str, Any]):
        """Log outline planning completion."""
        self.log(
            action="planning_complete",
            stage="planning",
            details={
                "message": "Outline planning completed",
                "outline": outline_dict
            }
        )
    
    def log_section_start(self, section_title: str, section_index: int):
        """Log section generation start."""
        self.log(
            action="section_start",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={"message": f"Started generating section: {section_title}"}
        )
    
    def log_react_thought(self, section_title: str, section_index: int, iteration: int, thought: str):
        """Log one ReACT thought step."""
        self.log(
            action="react_thought",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "thought": thought,
                "message": f"ReACT thought iteration {iteration}"
            }
        )
    
    def log_tool_call(
        self, 
        section_title: str, 
        section_index: int,
        tool_name: str, 
        parameters: Dict[str, Any],
        iteration: int
    ):
        """Log a tool call request."""
        self.log(
            action="tool_call",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "parameters": parameters,
                "message": f"Tool call: {tool_name}"
            }
        )
    
    def log_tool_result(
        self,
        section_title: str,
        section_index: int,
        tool_name: str,
        result: str,
        iteration: int
    ):
        """Log a tool call result payload."""
        self.log(
            action="tool_result",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "result": result,
                "result_length": len(result),
                "message": f"Tool result received: {tool_name}"
            }
        )
    
    def log_llm_response(
        self,
        section_title: str,
        section_index: int,
        response: str,
        iteration: int,
        has_tool_calls: bool,
        has_final_answer: bool
    ):
        """Log one LLM response in the ReACT loop."""
        self.log(
            action="llm_response",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "response": response,
                "response_length": len(response),
                "has_tool_calls": has_tool_calls,
                "has_final_answer": has_final_answer,
                "message": f"LLM response (tool_calls={has_tool_calls}, final_answer={has_final_answer})"
            }
        )
    
    def log_section_content(
        self,
        section_title: str,
        section_index: int,
        content: str,
        tool_calls_count: int
    ):
        """Log finalized section content for one section."""
        self.log(
            action="section_content",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": content,
                "content_length": len(content),
                "tool_calls_count": tool_calls_count,
                "message": f"Section content generated: {section_title}"
            }
        )
    
    def log_section_full_complete(
        self,
        section_title: str,
        section_index: int,
        full_content: str
    ):
        """Log full section completion output."""
        self.log(
            action="section_complete",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": full_content,
                "content_length": len(full_content),
                "message": f"Section generation complete: {section_title}"
            }
        )
    
    def log_report_complete(self, total_sections: int, total_time_seconds: float):
        """Log full report completion summary."""
        self.log(
            action="report_complete",
            stage="completed",
            details={
                "total_sections": total_sections,
                "total_time_seconds": round(total_time_seconds, 2),
                "message": "Report generation completed"
            }
        )
    
    def log_error(self, error_message: str, stage: str, section_title: str = None):
        """Log one error event."""
        self.log(
            action="error",
            stage=stage,
            section_title=section_title,
            section_index=None,
            details={
                "error": error_message,
                "message": f"Error: {error_message}"
            }
        )


class ReportConsoleLogger:
    """File logger that mirrors runtime logs to `console_log.txt`."""
    
    def __init__(self, report_id: str):
        """Initialize console logger for a report ID."""
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'console_log.txt'
        )
        self._ensure_log_file()
        self._file_handler = None
        self._setup_file_handler()
    
    def _ensure_log_file(self):
        """Ensure the console log directory exists."""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _setup_file_handler(self):
        """Attach file handler to relevant loggers."""
        import logging
        
        # Create file handler
        self._file_handler = logging.FileHandler(
            self.log_file_path,
            mode='a',
            encoding='utf-8'
        )
        self._file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)
        
        # Attach file handler to report and zep tools loggers.
        loggers_to_attach = [
            'phoring.report_agent',
            'phoring.zep_tools',
        ]
        
        for logger_name in loggers_to_attach:
            target_logger = logging.getLogger(logger_name)
            # Avoid duplicate handlers.
            if self._file_handler not in target_logger.handlers:
                target_logger.addHandler(self._file_handler)
    
    def close(self):
        """Detach and close file handler."""
        import logging
        
        if self._file_handler:
            loggers_to_detach = [
                'phoring.report_agent',
                'phoring.zep_tools',
            ]
            
            for logger_name in loggers_to_detach:
                target_logger = logging.getLogger(logger_name)
                if self._file_handler in target_logger.handlers:
                    target_logger.removeHandler(self._file_handler)
            
            self._file_handler.close()
            self._file_handler = None
    
    def __del__(self):
        """Best-effort cleanup on GC."""
        self.close()


class ReportStatus(str, Enum):
    """Lifecycle states for report generation."""
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportSection:
    """One report section with title and markdown content."""
    title: str
    content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content
        }

    def to_markdown(self, level: int = 2) -> str:
        """Render section as markdown heading + content."""
        md = f"{'#' * level} {self.title}\n\n"
        if self.content:
            md += f"{self.content}\n\n"
        return md


@dataclass
class ReportOutline:
    """Report outline containing title, summary, and section plan."""
    title: str
    summary: str
    sections: List[ReportSection]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": [s.to_dict() for s in self.sections]
        }
    
    def to_markdown(self) -> str:
        """Render outline as markdown."""
        md = f"# {self.title}\n\n"
        md += f"> {self.summary}\n\n"
        for section in self.sections:
            md += section.to_markdown()
        return md


@dataclass
class Report:
    """Full report object persisted by ReportManager."""
    report_id: str
    simulation_id: str
    graph_id: str
    simulation_requirement: str
    status: ReportStatus
    outline: Optional[ReportOutline] = None
    markdown_content: str = ""
    created_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None
    executive_summary: str = ""
    consensus_validation: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "status": self.status.value,
            "outline": self.outline.to_dict() if self.outline else None,
            "markdown_content": self.markdown_content,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "executive_summary": self.executive_summary,
            "consensus_validation": self.consensus_validation,
        }


# ═══════════════════════════════════════════════════════════════
# Prompt template constants
# ═══════════════════════════════════════════════════════════════

# ── Tool descriptions ──

TOOL_DESC_INSIGHT_FORGE = """\
[Deep Analysis Tool]
A tool for in-depth analysis and research. Key capabilities:
1. Automatically decomposes complex queries into sub-questions
2. Retrieves relevant information from the simulation knowledge graph
3. Performs entity analysis, relation analysis, and synthesizes results
4. Returns comprehensive, well-structured analysis content

[Use Cases]
- Analyzing a specific topic in depth
- Understanding the impact and consequences of events
- Gathering background information for report sections

[Returns]
- Related facts and evidence
- Entity analysis results
- Relationship analysis"""

TOOL_DESC_PANORAMA_SEARCH = """\
[Panorama Search - Full Picture View]
A comprehensive search tool that retrieves simulation results and contextual events. Key capabilities:
1. Retrieves node relationships and structure
2. Shows current state and historical changes
3. Helps build a complete picture of the situation

[Use Cases]
- Understanding the full scope of an event
- Analyzing how a situation evolved over time
- Mapping entity relationships and interactions

[Returns]
- Current state (from simulation results)
- Historical changes and records
- Entity relationship information"""

TOOL_DESC_QUICK_SEARCH = """\
[Quick Search - Fast Lookup]
A lightweight search tool for quick queries and information retrieval.

[Use Cases]
- Looking up specific facts or details
- Verifying a particular claim or data point
- Quick information retrieval

[Returns]
- A list of relevant results matching the query"""

TOOL_DESC_INTERVIEW_AGENTS = """\
[Agent Interview - Interview Simulation Agents (Multi-Platform)]
Calls the OASIS simulation environment's Interview API to interview currently running simulation agents!
Unlike LLM simulation, this calls the actual Interview API to get responses from simulation agents.
Interviews agents on both Twitter and Reddit platforms to gather diverse opinions.

Key capabilities:
1. Automatically locates persona files and identifies simulation agents
2. Selects relevant agents for the interview topic (by role, stance, expertise, etc.)
3. Auto-generates appropriate interview questions
4. Calls /api/simulation/interview/batch API to conduct multi-platform interviews
5. Collects and analyzes interview results

[Use Cases]
- Getting first-person perspectives on events (What do they think? How do they feel? What will they do?)
- Understanding different stakeholder positions
- Getting direct agent opinions from the OASIS simulation environment
- Adding an "agent interview" section to the report

[Returns]
- Interviewed agents' identity information
- Agent responses from both Twitter and Reddit platforms
- Key quotes and notable statements
- Interview summary and opinion analysis

[Note] The OASIS simulation environment must be currently running to use this tool!"""

TOOL_DESC_WEB_NEWS = """\
[Web News - Live News Fetch]
Searches for recent news about a specific entity using the Serper API and newsapi.ai,
scraping full article bodies from trusted financial/global news sources.

[Use Cases]
- Verify simulation predictions against real-world current events
- Enrich report sections with grounded, live context
- Contrast or validate agent behavior with actual published news

[Returns]
- Recent news articles (title, source, text excerpt)
- Combined text from up to 3 scraped/fetched articles"""

TOOL_DESC_GEOPOLITICAL_CONTEXT = """\
[Geopolitical Context - Scheduled Disruption Events]
Retrieves the geopolitical disruption events that were injected into this simulation run.
These events were generated based on the simulation scenario and real-world context,
and represent plausible disruptive events that could impact the entities during the simulation.

[Use Cases]
- Ground predictions in concrete geopolitical risk factors
- Reference specific disruption scenarios that were modeled
- Connect agent behavior changes to injected events

[Returns]
- List of scheduled geopolitical events (title, description, category, severity, trigger timing, impact factor)
- Summary of how these events were designed to affect entity types"""

# ── Outline prompt ──

PLAN_SYSTEM_PROMPT = """\
You are a "Predictive Report Planner" for a simulation world that serves as a "digital twin" of reality -- you can observe every agent's behavior and interactions within the simulation.

[Background]
We have built a simulation world and injected "Simulation Requirements" (a hypothetical scenario) into it. Based on the simulation world's results, we make predictions about real-world outcomes. The data comes "from simulation", not "from reality".

[Your Task]
Plan a "Predictive Report" outline with the following structure:
1. Given the scenario described in the simulation requirements, what is likely to happen?
2. How will the agents (representing real-world entities) likely react?
3. What trends and patterns emerge from the simulation?

[Report Guidelines]
- This is a simulation-based predictive report: "If this scenario happens, what would likely follow?"
- Prediction focus: causality, trends, stakeholder reactions, potential outcomes
- Base predictions on simulation agent behavior and interaction data
- NOT a real-world analysis report
- NOT a literature review or academic paper
- ALL analysis MUST be grounded in the geography and market described in the simulation requirements
- Do NOT introduce risk factors, events, or political scenarios from other countries or regions
  unless the simulation requirements explicitly involve those regions
- If the user mentions a specific market (e.g. Indian stock market), all predictions must be about that market

[Section Count]
- Minimum 2 sections, maximum 5 sections
- Sections should have clear, descriptive titles
- Each section should serve a distinct purpose in the prediction narrative
- Organize sections around different prediction angles

Output a JSON-format report outline in the following structure:
{
    "title": "Report Title",
    "summary": "Report summary (focused on prediction scope)",
    "sections": [
        {
            "title": "Section Title",
            "description": "Brief description of section content"
        }
    ]
}

Note: sections must have at least 2 and at most 5 items!"""

PLAN_USER_PROMPT_TEMPLATE = """\
[Prediction Scenario Setup]
The simulation world was injected with the following variable (Simulation Requirements): {simulation_requirement}

[Simulation World Overview]
- Total entities in simulation graph: {total_nodes}
- Entity relationships: {total_edges}
- Entity types: {entity_types}
- Agent count: {total_entities}

[Simulation Prediction Context]
{related_facts_json}

Based on this "digital twin" simulation world, plan a predictive report addressing:
1. Given the scenario in the simulation requirements, what outcomes are likely?
2. How do agents (representing real entities) react?
3. What trends and patterns emerge from the simulation?

IMPORTANT: The simulation requirements above are the user's EXACT request.
If the user specified a timeframe, date, or specific prediction target, the report outline
MUST include sections that directly address those specifics.
For example, if the user says "prediction for Friday", at least one section must make a
concrete prediction for that date/timeframe.

Design the report outline based on these prediction goals.

[Note] Section count: minimum 2, maximum 5. Content should focus on predictions and forecasting."""

# ── Section generation prompt ──

SECTION_SYSTEM_PROMPT_TEMPLATE = """\
You are a "Predictive Report Writer" currently writing one section of a simulation-based predictive report.

Report Title: {report_title}
Report Summary: {report_summary}
Prediction Scenario (Simulation Requirements): {simulation_requirement}
{geopolitical_context}
Current Section: {section_title}

[Core Principle]
The simulation world is a digital twin of reality. We injected a scenario (Simulation Requirements) into it,
then observed agent behavior and interactions to make real-world predictions.

[CRITICAL — Scenario Grounding]
- Your analysis MUST stay within the geography, market, and domain described in the Simulation Requirements.
- If the scenario is about India/Indian markets, ALL predictions, risk factors, and references must be India-specific.
- Do NOT reference events, regulations, or agencies from other countries unless the scenario explicitly involves them.
- If geopolitical events listed above seem irrelevant to the scenario's geography (e.g. FDA events for an India scenario),
  IGNORE them and instead ground your risk analysis in actual, plausible risks for the correct geography.
- Never fabricate political events (e.g. votes of no-confidence, coups) that have no basis in reality.

Your task for this section:
- Given the scenario, predict likely outcomes
- Analyze agent behavior patterns to forecast real-world reactions
- Identify trends and key developments

This is a "what-if prediction" using simulation results to forecast what would happen, NOT a retrospective real-world analysis.

[Writing Methodology - ReACT]

1. [Call tools to explore the simulation world]
   - You are a "digital twin observer" - use tools to examine what happened in the simulation
   - Content must be grounded in actual simulation events and agent behavior data
   - Use the knowledge gained to build your report section content
   - Call at least 3 tools (max 5) to thoroughly explore the simulation world

2. [Agent Behavior to Real-World Prediction]
   - Agent behavior in the simulation maps to predicted real-world behavior
   - Use quote format for key predictions, for example:
    > "Prediction: [specific prediction content]..."
   - Conclusions should be based on simulation evidence

3. [Quality Standards - Rich Content]
   - Tool-returned content is raw material - integrate and analyze it, don't just copy
   - If the simulation requirements mention specific scenarios, address them
   - Synthesize tool results into coherent analytical content
   - Ensure logical flow and consistency
   - FLAG CONTRADICTIONS: If different tools return conflicting data, explicitly note it
     e.g., "Note: Agent behavior data suggests X, while graph relationships indicate Y."

3a. [User Intent Alignment - CRITICAL]
   - The Prediction Scenario above is the user's EXACT request. Your analysis MUST directly answer it.
   - If the user mentions a specific timeframe (e.g. "by Friday", "next week", "in 30 days"),
     your predictions MUST explicitly reference and answer for that timeframe.
   - If the user asks about a specific outcome, entity, or event, address it by name.
   - Do NOT produce generic analysis — every prediction should tie back to what the user asked for.
   - When using web_news or geopolitical_context tools, connect the retrieved data explicitly
     to the user's scenario and uploaded documents context.

4. [Prediction Results]
   - Report content must be grounded in actual simulation world results
   - Do not fabricate information not present in the simulation
   - If information is insufficient, state that limitation clearly
   - Posts tagged with [SEED] are injected seed content, NOT organic agent reactions.
     When citing simulation evidence, clearly distinguish seeded prompts from genuine agent-generated responses.
     Evidence from organic (non-[SEED]) agent behavior is stronger than reactions to seeded content.

5. [Confidence Scoring - REQUIRED]
    - Every major prediction must include a confidence tag: [HIGH], [MEDIUM], or [LOW]
   - HIGH = supported by 3+ independent data points from different tools
   - MEDIUM = supported by 1-2 data points or inferred from patterns
   - LOW = extrapolated with limited direct evidence
   - End the section with a "Confidence Summary" line, e.g.:
     > **Section Confidence: MEDIUM** — Based on 4 data points from 3 tools. Key uncertainty: limited agent coverage.

[Format Rules - IMPORTANT!]
- Each report section should have substantial content
- Do NOT use Markdown headings (#, ##, ###, #### etc.) within the section
- The system will automatically add section headings
- Use **bold text**, bullet lists, numbered lists, and blockquotes to structure content

[Available Tools] (call 3-5 times)
{tools_description}

[Tool Usage Recommendations]
- insight_forge: Deep analysis, auto-decomposes queries and finds relationships
- panorama_search: Full picture search, event overview, timeline analysis
- quick_search: Verify specific facts or data points
- interview_agents: Interview simulation agents, get first-person perspectives
- web_news: Fetch live news articles about entities to ground predictions in current events
- geopolitical_context: Retrieve scheduled geopolitical disruption events from this simulation

[Response Format]
Each reply must be ONE of the following (never mix them):

  Option A - Call a tool:
Think about what information you need, then call ONE tool:
<tool_call>
{{"name": "ToolName", "parameters": {{"param_name": "param_value"}}}}
</tool_call>
The system will execute the tool and return results.

  Option B - Output final content:
After gathering sufficient information via tools, prefix with "Final Answer:" and write the section content.

Important:
- Never include both a tool call and Final Answer in the same reply
- Tool results (Observations) will be injected by the system
- Each reply should call at most one tool

[Content Requirements]
1. Content must be based on simulation data retrieved via tools
2. Connect simulation observations to real-world predictions
3. Use Markdown formatting (but no headings):
   - Use **bold** for emphasis
   - Use bullet lists (- or 1.2.3.)
   - Use blockquotes for key predictions
   - Do NOT use #, ##, ###, #### headings
4. Ensure proper spacing around blockquotes
5. Reference and compare with other relevant findings
6. Avoid repeating content from already-completed sections
7. Write substantial, detailed content
8. Tag every prediction with [HIGH], [MEDIUM], or [LOW] confidence
9. End with a Confidence Summary line for the section
10. CITE SOURCES: When using data from the web_news tool, include the numbered references [N]
   provided in the tool results. Place them inline after the relevant claim, e.g.:
   "India's EV market grew 40% year-over-year [3]."
   This lets readers verify your claims against the original sources."""

SECTION_USER_PROMPT_TEMPLATE = """\
Previously completed content (do not repeat):
{previous_content}

[Current Task] Section: {section_title}

[Instructions]
1. Review completed sections above to avoid repeating content!
2. Start by calling tools to gather simulation data
3. Use multiple different tools for comprehensive coverage
4. Base your report content on tool results, supplemented with analytical reasoning

[Format Warning - IMPORTANT]
- No headings (#, ##, ###, #### etc.)
- Do not repeat the section title "{section_title}"
- The system will automatically add the section heading
- Use bold text, lists, and blockquotes for structure

Please begin:
1. Think (Thought) about what information you need for this section
2. Call a tool (Action) to retrieve simulation data
3. After gathering enough info, output Final Answer (substantial, detailed content)"""

# ── ReACT message templates ──

REACT_OBSERVATION_TEMPLATE = """\
Observation (Tool Result):

=== Tool {tool_name} Result ===
{result}
===
Tools called: {tool_calls_count}/{max_tool_calls} (used: {used_tools_str}){unused_hint}
- If you have enough information: prefix with "Final Answer:" and output section content
- If you need more information: call another tool to continue gathering data
==="""

REACT_INSUFFICIENT_TOOLS_MSG = (
    "[Note] You have only called {tool_calls_count} tool(s), minimum is {min_tool_calls}."
    " Please call more tools to gather additional simulation data before outputting Final Answer.{unused_hint}"
)

REACT_INSUFFICIENT_TOOLS_MSG_ALT = (
    "You have called {tool_calls_count} tool(s) so far, minimum is {min_tool_calls}."
    " Please call more tools to gather simulation data.{unused_hint}"
)

REACT_TOOL_LIMIT_MSG = (
    "Tool call limit reached ({tool_calls_count}/{max_tool_calls}), no more tool calls allowed."
    ' Based on the information gathered, prefix with "Final Answer:" and output the section content.'
)

REACT_UNUSED_TOOLS_HINT = "\n Unused tools: {unused_list}. Consider using them for additional insights."

REACT_FORCE_FINAL_MSG = "Tool call limit reached. Please output Final Answer: followed by the section content now."

# ── Chat prompts ──

CHAT_SYSTEM_PROMPT_TEMPLATE = """\
You are a simulation prediction analyst assistant.

[Background]
Prediction scenario: {simulation_requirement}

[Generated Analysis Report]
{report_content}

[Instructions]
1. Answer questions based on the report content
2. Be precise and avoid vague responses
3. If the report doesn't contain enough information, use tools to fetch more data
4. Maintain a professional yet conversational tone

[Available Tools] (use sparingly, call 1-2 max)
{tools_description}

[Tool Call Format]
<tool_call>
{{"name": "ToolName", "parameters": {{"param_name": "param_value"}}}}
</tool_call>

[Response Guidelines]
- Give clear, direct answers
- Use > blockquote format for key findings
- Provide evidence-based conclusions"""

CHAT_OBSERVATION_SUFFIX = "\n\nPlease respond based on this information."


# ═══════════════════════════════════════════════════════════════
# Report Agent
# ═══════════════════════════════════════════════════════════════


class ReportAgent:
    """Report generation agent using a ReACT-style section workflow.

    High-level stages:
    1. Plan the report outline from simulation context.
    2. Generate each section with tool-assisted reasoning.
    3. Assemble and persist the final report artifacts.
    """
    
    # Maximum number of tool calls allowed per section.
    MAX_TOOL_CALLS_PER_SECTION = 5
    
    # Maximum number of tool calls allowed per chat turn.
    MAX_TOOL_CALLS_PER_CHAT = 2
    
    def __init__(
        self, 
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        llm_client: Optional[LLMClient] = None,
        zep_tools: Optional[ZepToolsService] = None,
        consensus_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize a report agent for one graph/simulation pair.

        Args:
            graph_id: Graph ID.
            simulation_id: Simulation ID.
            simulation_requirement: Requirement text that defines the scenario.
            llm_client: Optional LLM client override.
            zep_tools: Optional Zep tools service override.
            consensus_config: Optional consensus settings from frontend.
                {"enabled": bool, "validators": [1, 2, 3]}
        """
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement
        self.consensus_config = consensus_config or {}
        
        self.llm = llm_client or LLMClient()
        self.zep_tools = zep_tools or ZepToolsService()
        
        # Tool schema exposed to the ReACT loop.
        self.tools = self._define_tools()
        
        # Pre-load geopolitical events context (cached for all sections).
        self._geopolitical_summary = self._load_geopolitical_summary()
        
        # Accumulated source references for Perplexity-style citations.
        self._collected_sources: List[Dict[str, str]] = []

        # Action logger (initialized in generate_report).
        self.report_logger: Optional[ReportLogger] = None
        # Console logger (initialized in generate_report).
        self.console_logger: Optional[ReportConsoleLogger] = None
        
        logger.info(f"ReportAgent initialization complete: graph_id={graph_id}, simulation_id={simulation_id}")

    def _load_geopolitical_summary(self) -> str:
        """Load geopolitical events from simulation config at init time.

        Returns a short text block summarising the events, or an empty string
        if none exist.  This is injected into every section prompt so the LLM
        always has the geopolitical context even without calling the tool.
        """
        try:
            from .simulation_manager import SimulationManager
            config = SimulationManager().get_simulation_config(self.simulation_id)
            if not config:
                return ""
            event_config = config.get("event_config", config)
            scheduled = event_config.get("scheduled_events", [])
            if not scheduled:
                return ""
            parts = []
            for evt in scheduled:
                parts.append(
                    f"- {evt.get('title','?')} [{evt.get('severity','?')}]: "
                    f"{evt.get('description','N/A')} (impact {evt.get('impact_factor',0)})"
                )
            return (
                "\n[Geopolitical Disruption Events injected into this simulation]\n"
                + "\n".join(parts)
                + "\n\nIMPORTANT: Only reference these events in your analysis if they are directly "
                "relevant to the geography and market described in the simulation requirements. "
                "Discard any events that appear to be from a different country or region than the scenario."
            )
        except Exception as e:
            logger.debug(f"Geopolitical summary load skipped: {e}")
            return ""

    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """Define tool metadata used by prompts and runtime validation."""
        return {
            "insight_forge": {
                "name": "insight_forge",
                "description": TOOL_DESC_INSIGHT_FORGE,
                "parameters": {
                    "query": "analysis query text",
                    "report_context": "current report section context (optional)"
                }
            },
            "panorama_search": {
                "name": "panorama_search",
                "description": TOOL_DESC_PANORAMA_SEARCH,
                "parameters": {
                    "query": "search query text",
                    "include_expired": "include expired content (default: true)"
                }
            },
            "quick_search": {
                "name": "quick_search",
                "description": TOOL_DESC_QUICK_SEARCH,
                "parameters": {
                    "query": "search query text",
                    "limit": "max number of results (optional, default: 10)"
                }
            },
            "interview_agents": {
                "name": "interview_agents",
                "description": TOOL_DESC_INTERVIEW_AGENTS,
                "parameters": {
                    "interview_topic": "interview topic or requirement",
                    "max_agents": "number of agents to interview (optional, default: 5, max: 10)"
                }
            },
            "web_news": {
                "name": "web_news",
                "description": TOOL_DESC_WEB_NEWS,
                "parameters": {
                    "entity": "entity name to search news for",
                    "entity_type": "type of entity (e.g. Company, Index, Person, Sector)"
                }
            },
            "geopolitical_context": {
                "name": "geopolitical_context",
                "description": TOOL_DESC_GEOPOLITICAL_CONTEXT,
                "parameters": {}
            }
        }
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], report_context: str = "") -> str:
        """Execute one tool call and return text output for the LLM loop."""
        logger.info(f"Executing tool: {tool_name}, parameters={parameters}")
        
        try:
            if tool_name == "insight_forge":
                query = parameters.get("query", "")
                ctx = parameters.get("report_context", "") or report_context
                result = self.zep_tools.insight_forge(
                    graph_id=self.graph_id,
                    query=query,
                    simulation_requirement=self.simulation_requirement,
                    report_context=ctx
                )
                return result.to_text()
            
            elif tool_name == "panorama_search":
                # Panorama search over simulation graph context.
                query = parameters.get("query", "")
                include_expired = parameters.get("include_expired", True)
                if isinstance(include_expired, str):
                    include_expired = include_expired.lower() in ['true', '1', 'yes']
                result = self.zep_tools.panorama_search(
                    graph_id=self.graph_id,
                    query=query,
                    include_expired=include_expired
                )
                return result.to_text()
            
            elif tool_name == "quick_search":
                # Quick fact lookup.
                query = parameters.get("query", "")
                limit = parameters.get("limit", 10)
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.zep_tools.quick_search(
                    graph_id=self.graph_id,
                    query=query,
                    limit=limit
                )
                return result.to_text()
            
            elif tool_name == "interview_agents":
                # Interview - call OASIS interview API to get simulation agent answers (per platform)
                interview_topic = parameters.get("interview_topic", parameters.get("query", ""))
                max_agents = parameters.get("max_agents", 5)
                if isinstance(max_agents, str):
                    max_agents = int(max_agents)
                max_agents = min(max_agents, 10)
                result = self.zep_tools.interview_agents(
                    simulation_id=self.simulation_id,
                    interview_requirement=interview_topic,
                    simulation_requirement=self.simulation_requirement,
                    max_agents=max_agents
                )
                return result.to_text()
            
            elif tool_name == "web_news":
                return self._tool_web_news(parameters)
            
            elif tool_name == "geopolitical_context":
                return self._tool_geopolitical_context()
            
            # ---------- Legacy tool aliases ----------
            
            elif tool_name == "search_graph":
                # Backward compatibility alias.
                logger.info("Alias resolved: search_graph -> quick_search")
                return self._execute_tool("quick_search", parameters, report_context)
            
            elif tool_name == "get_graph_statistics":
                result = self.zep_tools.get_graph_statistics(self.graph_id)
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_entity_summary":
                entity_name = parameters.get("entity_name", "")
                result = self.zep_tools.get_entity_summary(
                    graph_id=self.graph_id,
                    entity_name=entity_name
                )
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_simulation_context":
                # Backward compatibility alias.
                logger.info("Alias resolved: get_simulation_context -> insight_forge")
                query = parameters.get("query", self.simulation_requirement)
                return self._execute_tool("insight_forge", {"query": query}, report_context)
            
            elif tool_name == "get_entities_by_type":
                entity_type = parameters.get("entity_type", "")
                nodes = self.zep_tools.get_entities_by_type(
                    graph_id=self.graph_id,
                    entity_type=entity_type
                )
                result = [n.to_dict() for n in nodes]
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            else:
                return (
                    f"Unsupported tool: {tool_name}. Available tools: "
                    f"insight_forge, panorama_search, quick_search, interview_agents, web_news, geopolitical_context"
                )
                
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}, error={type(e).__name__}: {e}")
            return f"Tool execution failed: {type(e).__name__}"
    
    def _extract_confidence_summary(self, markdown_content: str) -> Optional[str]:
        """Extract per-section confidence tags and produce an evidence-based report-level summary.

        Instead of simple averaging, counts actual evidence indicators:
        - Number of tool-sourced data citations
        - Number of prediction tags with backing evidence
        - Penalizes sections that flagged data limitations
        """
        confidence_pattern = re.compile(
            r'\*\*Section Confidence:\s*(HIGH|MEDIUM|LOW)\*\*',
            re.IGNORECASE
        )
        tag_pattern = re.compile(r'\[(HIGH|MEDIUM|LOW)\]', re.IGNORECASE)
        # Count evidence markers (blockquoted predictions, data citations)
        evidence_pattern = re.compile(r'>\s*"?Prediction|data point|tool result|simulation data|agent behavior', re.IGNORECASE)
        # Count limitation/uncertainty markers
        limitation_pattern = re.compile(r'limited.*data|insufficient|no.*data.*found|unavailable|data limitation', re.IGNORECASE)
        
        matches = confidence_pattern.findall(markdown_content)
        tag_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for m in tag_pattern.findall(markdown_content):
            tag_counts[m.upper()] += 1
        
        evidence_count = len(evidence_pattern.findall(markdown_content))
        limitation_count = len(limitation_pattern.findall(markdown_content))
        
        if not matches and sum(tag_counts.values()) == 0:
            return None
        
        section_levels = [m.upper() for m in matches]
        total_tags = sum(tag_counts.values())
        
        # Evidence-based confidence calculation
        score_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        if section_levels:
            base_avg = sum(score_map[s] for s in section_levels) / len(section_levels)
            # Boost for high evidence count, penalize for limitations
            evidence_modifier = min(0.5, evidence_count * 0.05) - min(0.5, limitation_count * 0.15)
            adjusted_score = base_avg + evidence_modifier
            
            if adjusted_score >= 2.5:
                overall = "HIGH"
            elif adjusted_score >= 1.5:
                overall = "MEDIUM"
            else:
                overall = "LOW"
        else:
            overall = "MEDIUM"
        
        summary_lines = [
            "\n\n---\n",
            "## Report Confidence Summary\n",
            f"**Overall Confidence: {overall}**\n",
            f"- Prediction tags found: {total_tags} "
            f"(HIGH: {tag_counts['HIGH']}, MEDIUM: {tag_counts['MEDIUM']}, LOW: {tag_counts['LOW']})",
            f"- Evidence indicators found: {evidence_count}",
            f"- Data limitation flags: {limitation_count}",
        ]
        if section_levels:
            summary_lines.append(
                f"- Section-level assessments: {', '.join(section_levels)}"
            )
        summary_lines.append(
            "\n> *Confidence levels are based on evidence count from simulation tools, "
            "data limitations encountered, and consistency of supporting data. "
            "Sections flagging data gaps receive lower confidence.*\n"
        )
        return "\n".join(summary_lines)

    def _validate_timeframe_coverage(self, markdown_content: str) -> Optional[str]:
        """Check whether the report addresses the user's requested timeframe.

        Extracts timeframe references from the simulation requirement and verifies
        the report content mentions them. Returns a warning note if the timeframe
        appears to be unaddressed.
        """
        requirement = self.simulation_requirement.lower()

        # Common timeframe patterns
        timeframe_patterns = [
            (r'\b(by|before|until)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', 'day-specific'),
            (r'\b(next|this)\s+(week|month|quarter|year)\b', 'period'),
            (r'\bin\s+(\d+)\s+(days?|weeks?|months?|hours?)\b', 'duration'),
            (r'\b(by|before)\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b', 'month-specific'),
            (r'\b(short[\s-]?term|medium[\s-]?term|long[\s-]?term)\b', 'horizon'),
            (r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b', 'date'),
            (r'\b(tomorrow|today|tonight|this evening)\b', 'immediate'),
        ]

        found_timeframes = []
        for pattern, tf_type in timeframe_patterns:
            matches = re.findall(pattern, requirement)
            if matches:
                found_timeframes.append((tf_type, matches))

        if not found_timeframes:
            return None  # No specific timeframe requested

        # Check if the report content mentions any of these timeframes
        content_lower = markdown_content.lower()
        addressed = False
        for tf_type, matches in found_timeframes:
            for match in matches:
                match_str = match if isinstance(match, str) else " ".join(match)
                if match_str.lower() in content_lower:
                    addressed = True
                    break
            if addressed:
                break

        if addressed:
            return None

        # Timeframe was requested but not addressed — append a warning
        tf_descriptions = [f"{m}" for _, matches in found_timeframes for m in matches]
        return (
            "\n\n---\n\n"
            "> **Timeframe Coverage Notice:** The user's request referenced specific timeframes "
            f"({', '.join(str(t) for t in tf_descriptions[:3])}), but the report may not "
            "have explicitly addressed predictions for those exact periods. "
            "Readers should factor in that predictions may need to be adjusted "
            "for the specific time horizon requested.\n"
        )

    def _tool_web_news(self, parameters: Dict[str, Any]) -> str:
        """Fetch live Serper + newsapi.ai news + social media posts for a named entity."""
        try:
            from .web_intelligence import NewsScraperService
            entity = parameters.get("entity", "")
            entity_type = parameters.get("entity_type", "Entity")
            if not entity:
                return "No entity name specified."
            svc = NewsScraperService()
            if not svc.enabled:
                return "Web news unavailable (SERPER_API_KEY not configured)."
            data = svc.gather_for_entity(
                entity, entity_type, max_articles=3,
                context=self.simulation_requirement,
            )
            articles = data.get("articles", [])
            social_posts = data.get("social_media_posts", [])
            
            result_parts = []

            # Build citation-annotated news results
            if articles:
                news_lines = [f"=== Recent News & Coverage: {entity} ===\n"]
                for article in articles:
                    url = article.get("url", "")
                    title = article.get("title", "Untitled")
                    source = article.get("source", "Unknown")
                    text = article.get("text", article.get("snippet", ""))

                    if url:
                        # Assign a sequential citation number
                        ref_num = len(self._collected_sources) + 1
                        self._collected_sources.append({
                            "num": ref_num,
                            "title": title,
                            "source": source,
                            "url": url,
                        })
                        news_lines.append(
                            f"[{ref_num}] [{source}] {title}\n"
                            f"URL: {url}\n"
                            f"{text}\n"
                        )
                    else:
                        news_lines.append(f"[{source}] {title}\n{text}\n")
                result_parts.append("\n".join(news_lines))
            
            # Include social media posts if available
            if social_posts:
                social_summary = f"\n\n=== Social Media Discussion ({len(social_posts)} posts) ===\n"
                for post in social_posts:
                    platform = post.get("platform", "Social Media")
                    title = post.get("title", post.get("snippet", ""))[:100]
                    snippet = post.get("snippet", "")[:300]
                    url = post.get("url", "")

                    if url:
                        ref_num = len(self._collected_sources) + 1
                        self._collected_sources.append({
                            "num": ref_num,
                            "title": title,
                            "source": platform,
                            "url": url,
                        })
                        social_summary += f"\n[{ref_num}] [{platform}] {title}\n{snippet}\n"
                    else:
                        social_summary += f"\n[{platform}] {title}\n{snippet}\n"
                result_parts.append(social_summary)

            if result_parts:
                result_parts.append(
                    "\n[CITATION INSTRUCTION: Use the [N] reference numbers above "
                    "when citing these sources in your analysis. For example: "
                    '"According to recent reports [1], the market showed..."]\n'
                )
            
            if not result_parts:
                return f"No recent news or social media discussion found for '{entity}'."
            
            return "".join(result_parts)
        except Exception as e:
            return f"Web news error: {type(e).__name__}"

    def _tool_geopolitical_context(self) -> str:
        """Load geopolitical disruption events from the simulation config."""
        try:
            from .simulation_manager import SimulationManager
            manager = SimulationManager()
            config = manager.get_simulation_config(self.simulation_id)
            if not config:
                return "No simulation configuration found."

            events = []
            # Events may be nested under event_config.scheduled_events or at top level
            event_config = config.get("event_config", config)
            scheduled = event_config.get("scheduled_events", [])

            if not scheduled:
                return "No geopolitical disruption events were scheduled for this simulation."

            lines = [f"=== Geopolitical Disruption Events ({len(scheduled)} total) ===\n"]
            for i, evt in enumerate(scheduled, 1):
                lines.append(f"Event {i}: {evt.get('title', 'Unnamed')}")
                lines.append(f"  Category: {evt.get('category', 'N/A')}")
                lines.append(f"  Severity: {evt.get('severity', 'N/A')}")
                lines.append(f"  Impact Factor: {evt.get('impact_factor', 'N/A')}")
                lines.append(f"  Trigger Round: {evt.get('trigger_round', 'N/A')}")
                lines.append(f"  Description: {evt.get('description', 'N/A')}")
                affected = evt.get("affected_entity_types", [])
                if affected:
                    lines.append(f"  Affected Entity Types: {', '.join(affected)}")
                lines.append("")

            return "\n".join(lines)
        except Exception as e:
            return f"Geopolitical context error: {type(e).__name__}"

    def _build_references_section(self) -> str:
        """Build a Perplexity-style Sources & References section from collected sources."""
        if not self._collected_sources:
            return ""
        # Deduplicate by URL while preserving order
        seen_urls = set()
        unique_sources = []
        for src in self._collected_sources:
            if src["url"] not in seen_urls:
                seen_urls.add(src["url"])
                unique_sources.append(src)

        lines = ["\n\n---\n\n## Sources & References\n"]
        for src in unique_sources:
            lines.append(
                f"[{src['num']}] {src['title']} — *{src['source']}*  \n"
                f"{src['url']}\n"
            )
        lines.append(
            "\n*Sources were retrieved from live web data at the time of report generation. "
            "Links may expire or change over time.*\n"
        )
        return "\n".join(lines)

    def _generate_executive_summary(self, markdown_content: str) -> str:
        """Generate a 5-bullet plain-English executive summary of the full report.

        Uses the full report content (up to model context limits) rather than
        an arbitrary truncation, to prevent the summary from fabricating
        unsupported bullets.
        """
        if not markdown_content:
            return ""
        try:
            # Use a generous context window — 24k chars covers most reports fully.
            # If the report is longer, summarize from sections rather than truncating mid-sentence.
            report_text = markdown_content[:24000]
            if len(markdown_content) > 24000:
                report_text += (
                    "\n\n[NOTE: Report truncated for summary generation. "
                    f"Full report is {len(markdown_content)} chars. "
                    "Base your summary ONLY on the content shown above.]"
                )

            prompt = (
                f"Prediction Scenario (the user's exact request): {self.simulation_requirement}\n\n"
                f"Full Report:\n{report_text}\n\n"
                "Write EXACTLY 5 bullet point predictions/key findings from this report.\n"
                "Format each as: • [plain English, max 30 words]\n"
                "Cover: main outcome, key players, top risk, timing signal, one contrarian view.\n"
                "No jargon. No hedging. Start each bullet with a strong verb or entity name.\n\n"
                "CRITICAL RULES:\n"
                "1. Your predictions MUST directly address the user's original request above.\n"
                "2. Every bullet MUST be directly supported by content in the report above.\n"
                "3. Do NOT invent findings, statistics, or events not mentioned in the report.\n"
                "4. If the user specified a timeframe (e.g. 'by Friday', 'next week', 'in 30 days'), "
                "your predictions must reference and answer for that specific timeframe.\n"
                "5. If the user asked for a specific type of prediction, address it explicitly."
            )
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You write concise executive summaries. Output only the 5 bullet points, nothing else."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=400
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Executive summary generation failed: {e}")
            return ""

    # Valid tool names accepted from LLM tool-call JSON.
    VALID_TOOL_NAMES = {"insight_forge", "panorama_search", "quick_search", "interview_agents", "web_news", "geopolitical_context"}

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Parse tool calls from an LLM response.

        Supported formats:
        1. `<tool_call>{"name": "tool_name", "parameters": {...}}</tool_call>`
        2. Raw JSON object (without `<tool_call>` wrappers)
        """
        tool_calls = []

        # Format 1: XML-style wrapped JSON payload.
        xml_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        for match in re.finditer(xml_pattern, response, re.DOTALL):
            try:
                call_data = json.loads(match.group(1))
                tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        if tool_calls:
            return tool_calls

        # Format 2: raw JSON output when no XML-wrapped call is present.
        stripped = response.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            try:
                call_data = json.loads(stripped)
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
                    return tool_calls
            except json.JSONDecodeError:
                pass

        # Fallback: trailing JSON object after reasoning text.
        json_pattern = r'(\{"(?:name|tool)"\s*:.*?\})\s*$'
        match = re.search(json_pattern, stripped, re.DOTALL)
        if match:
            try:
                call_data = json.loads(match.group(1))
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        return tool_calls

    def _is_valid_tool_call(self, data: dict) -> bool:
        """Validate and normalize tool-call JSON payloads."""
        # Supports both {name, parameters} and {tool, params} schemas.
        tool_name = data.get("name") or data.get("tool")
        if tool_name and tool_name in self.VALID_TOOL_NAMES:
            # Normalize alternate schema keys.
            if "tool" in data:
                data["name"] = data.pop("tool")
            if "params" in data and "parameters" not in data:
                data["parameters"] = data.pop("params")
            return True
        return False
    
    def _get_tools_description(self) -> str:
        """Build human-readable tool descriptions for prompt injection."""
        desc_parts = ["Available tools:"]
        for name, tool in self.tools.items():
            params_desc = ", ".join([f"{k}: {v}" for k, v in tool["parameters"].items()])
            desc_parts.append(f"- {name}: {tool['description']}")
            if params_desc:
                desc_parts.append(f"  parameters: {params_desc}")
        return "\n".join(desc_parts)
    
    def plan_outline(
        self, 
        progress_callback: Optional[Callable] = None
    ) -> ReportOutline:
        """Generate report outline from simulation context and requirements."""
        logger.info("Starting report outline planning...")
        
        if progress_callback:
            progress_callback("planning", 0, "Analyzing simulation requirements...")
        
        # Fetch simulation context used for outline planning.
        context = self.zep_tools.get_simulation_context(
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement
        )
        
        if progress_callback:
            progress_callback("planning", 30, "Generating report outline...")
        
        system_prompt = PLAN_SYSTEM_PROMPT
        user_prompt = PLAN_USER_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            total_nodes=context.get('graph_statistics', {}).get('total_nodes', 0),
            total_edges=context.get('graph_statistics', {}).get('total_edges', 0),
            entity_types=list(context.get('graph_statistics', {}).get('entity_types', {}).keys()),
            total_entities=context.get('total_entities', 0),
            related_facts_json=json.dumps(context.get('related_facts', [])[:10], ensure_ascii=False, indent=2),
        )

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            if progress_callback:
                progress_callback("planning", 80, "Parsing outline response...")
            
            # Parse planned sections from LLM JSON.
            sections = []
            for section_data in response.get("sections", []):
                sections.append(ReportSection(
                    title=section_data.get("title", ""),
                    content=""
                ))
            
            outline = ReportOutline(
                title=response.get("title", "Simulation Predictive Report"),
                summary=response.get("summary", ""),
                sections=sections
            )
            
            if progress_callback:
                progress_callback("planning", 100, "Outline planning complete")
            
            logger.info(f"Outline planning complete: {len(sections)} sections")
            return outline
            
        except Exception as e:
            logger.error(f"Outline planning failed: {type(e).__name__}: {e}")
            # Return a safe default outline as fallback.
            return ReportOutline(
                title="Simulation Predictive Report",
                summary="A fallback outline generated from simulation trend analysis.",
                sections=[
                    ReportSection(title="Scenario Overview"),
                    ReportSection(title="Agent Behavior Analysis"),
                    ReportSection(title="Trend Signals")
                ]
            )
    
    def _generate_section_react(
        self, 
        section: ReportSection,
        outline: ReportOutline,
        previous_sections: List[str],
        progress_callback: Optional[Callable] = None,
        section_index: int = 0
    ) -> str:
        """Generate one section using a ReACT loop with tool calls.

        Args:
            section: Current target section.
            outline: Full report outline.
            previous_sections: Previously generated section markdown.
            progress_callback: Optional progress callback.
            section_index: 1-based section index for logging.

        Returns:
            Generated section markdown content.
        """
        logger.info(f"Starting ReACT section generation: {section.title}")
        
        # Record section start.
        if self.report_logger:
            self.report_logger.log_section_start(section.title, section_index)
        
        system_prompt = SECTION_SYSTEM_PROMPT_TEMPLATE.format(
            report_title=outline.title,
            report_summary=outline.summary,
            simulation_requirement=self.simulation_requirement,
            section_title=section.title,
            tools_description=self._get_tools_description(),
            geopolitical_context=self._geopolitical_summary,
        )

        # Build user prompt with truncated previous sections for context.
        if previous_sections:
            previous_parts = []
            for sec in previous_sections:
                # Keep each section snippet bounded to avoid oversized prompts.
                truncated = sec[:4000] + "..." if len(sec) > 4000 else sec
                previous_parts.append(truncated)
            previous_content = "\n\n---\n\n".join(previous_parts)
        else:
            previous_content = "(No previously completed sections.)"
        
        user_prompt = SECTION_USER_PROMPT_TEMPLATE.format(
            previous_content=previous_content,
            section_title=section.title,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # ReACT loop state.
        tool_calls_count = 0
        max_iterations = 5  # Max interaction rounds.
        min_tool_calls = 3  # Minimum tools before accepting final answer.
        conflict_retries = 0  # Retry budget when response mixes tool call + final answer.
        used_tools = set()  # Tracks tools already called in this section.
        all_tools = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

        report_context = f"section title: {section.title}\nsimulation requirement: {self.simulation_requirement}"
        
        for iteration in range(max_iterations):
            if progress_callback:
                progress_callback(
                    "generating", 
                    int((iteration / max_iterations) * 100),
                    f"Tool calls: {tool_calls_count}/{self.MAX_TOOL_CALLS_PER_SECTION}"
                )
            
            # Query LLM for the next ReACT step.
            response = self.llm.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=4096
            )

            # Guard against empty LLM responses.
            if response is None:
                logger.warning(f"Section {section.title} iteration {iteration + 1}: LLM returned None")
                if iteration < max_iterations - 1:
                    messages.append({"role": "assistant", "content": ""})
                    messages.append({"role": "user", "content": "Please continue with a valid response."})
                    continue
                # Exit and force a final fallback response below.
                break

            logger.debug(f"LLM: {response[:200]}...")

            # Parse possible tool calls and final-answer marker.
            tool_calls = self._parse_tool_calls(response)
            has_tool_calls = bool(tool_calls)
            has_final_answer = "Final Answer:" in response

            # Handle invalid mixed responses that include both tool call and final answer.
            if has_tool_calls and has_final_answer:
                conflict_retries += 1
                logger.warning(
                    f"Section {section.title} iteration {iteration + 1}: "
                    f"response mixed tool call and final answer (retry {conflict_retries})"
                )

                if conflict_retries <= 2:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "[Format Error] Your reply included both a tool call and a final answer.\n"
                            "Please send exactly one of:\n"
                            "- A tool call only (inside <tool_call>...</tool_call>)\n"
                            "- A final answer only (prefixed with 'Final Answer:')"
                        ),
                    })
                    continue
                else:
                    logger.warning(
                        f"Section {section.title}: mixed response persisted after retries; "
                        "truncating to first tool call"
                    )
                    first_tool_end = response.find('</tool_call>')
                    if first_tool_end != -1:
                        response = response[:first_tool_end + len('</tool_call>')]
                        tool_calls = self._parse_tool_calls(response)
                        has_tool_calls = bool(tool_calls)
                    has_final_answer = False
                    conflict_retries = 0

            # Record raw LLM response in structured log.
            if self.report_logger:
                self.report_logger.log_llm_response(
                    section_title=section.title,
                    section_index=section_index,
                    response=response,
                    iteration=iteration + 1,
                    has_tool_calls=has_tool_calls,
                    has_final_answer=has_final_answer
                )

            # Branch 1: final answer received.
            if has_final_answer:
                if tool_calls_count < min_tool_calls:
                    messages.append({"role": "assistant", "content": response})
                    unused_tools = all_tools - used_tools
                    unused_hint = f" (unused tools: {', '.join(unused_tools)})" if unused_tools else ""
                    messages.append({
                        "role": "user",
                        "content": REACT_INSUFFICIENT_TOOLS_MSG.format(
                            tool_calls_count=tool_calls_count,
                            min_tool_calls=min_tool_calls,
                            unused_hint=unused_hint,
                        ),
                    })
                    continue

                final_answer = response.split("Final Answer:")[-1].strip()
                logger.info(f"Section generation complete: {section.title} (tool calls: {tool_calls_count})")

                if self.report_logger:
                    self.report_logger.log_section_content(
                        section_title=section.title,
                        section_index=section_index,
                        content=final_answer,
                        tool_calls_count=tool_calls_count
                    )
                return final_answer

            # Branch 2: tool call requested.
            if has_tool_calls:
                # Enforce tool-call limit.
                if tool_calls_count >= self.MAX_TOOL_CALLS_PER_SECTION:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": REACT_TOOL_LIMIT_MSG.format(
                            tool_calls_count=tool_calls_count,
                            max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        ),
                    })
                    continue

                # Execute only the first requested tool call.
                call = tool_calls[0]
                if len(tool_calls) > 1:
                    logger.info(f"LLM requested {len(tool_calls)} tools; executing first: {call['name']}")

                if self.report_logger:
                    self.report_logger.log_tool_call(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        parameters=call.get("parameters", {}),
                        iteration=iteration + 1
                    )

                result = self._execute_tool(
                    call["name"],
                    call.get("parameters", {}),
                    report_context=report_context
                )

                # Validate tool result relevance — flag empty/error results
                result_is_useful = bool(
                    result
                    and len(result.strip()) > 50
                    and not result.startswith("No ")
                    and "error" not in result[:50].lower()
                    and "unavailable" not in result[:80].lower()
                )
                if not result_is_useful:
                    result = (
                        f"{result}\n\n"
                        "[SYSTEM NOTE: This tool returned limited or no useful data. "
                        "Do NOT fabricate information to fill the gap. "
                        "Instead, acknowledge this data limitation in your analysis "
                        "and lower the confidence level accordingly.]"
                    )

                if self.report_logger:
                    self.report_logger.log_tool_result(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        result=result,
                        iteration=iteration + 1
                    )

                tool_calls_count += 1
                used_tools.add(call['name'])

                # Suggest unused tools while budget remains.
                unused_tools = all_tools - used_tools
                unused_hint = ""
                if unused_tools and tool_calls_count < self.MAX_TOOL_CALLS_PER_SECTION:
                    unused_hint = REACT_UNUSED_TOOLS_HINT.format(unused_list=", ".join(unused_tools))

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": REACT_OBSERVATION_TEMPLATE.format(
                        tool_name=call["name"],
                        result=result,
                        tool_calls_count=tool_calls_count,
                        max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        used_tools_str=", ".join(used_tools),
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # Branch 3: plain text response without tool call or final marker.
            messages.append({"role": "assistant", "content": response})

            if tool_calls_count < min_tool_calls:
                unused_tools = all_tools - used_tools
                unused_hint = f" (unused tools: {', '.join(unused_tools)})" if unused_tools else ""

                messages.append({
                    "role": "user",
                    "content": REACT_INSUFFICIENT_TOOLS_MSG_ALT.format(
                        tool_calls_count=tool_calls_count,
                        min_tool_calls=min_tool_calls,
                        unused_hint=unused_hint,
                    ),
                })
                continue

            logger.info(
                f"Section {section.title} returned content without explicit 'Final Answer:' "
                f"after {tool_calls_count} tool calls"
            )
            final_answer = response.strip()

            if self.report_logger:
                self.report_logger.log_section_content(
                    section_title=section.title,
                    section_index=section_index,
                    content=final_answer,
                    tool_calls_count=tool_calls_count
                )
            return final_answer
        
        # Iteration limit reached; force one final answer request.
        logger.warning(f"Section {section.title} reached max iterations; forcing final response")
        messages.append({"role": "user", "content": REACT_FORCE_FINAL_MSG})
        
        response = self.llm.chat(
            messages=messages,
            temperature=0.5,
            max_tokens=4096
        )

        # Handle final forced response.
        if response is None:
            logger.error(f"Section {section.title}: forced-final response returned None")
            final_answer = "(Section generation failed: empty LLM response. Please retry.)"
        elif "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
        else:
            final_answer = response
        
        # Persist final section content log.
        if self.report_logger:
            self.report_logger.log_section_content(
                section_title=section.title,
                section_index=section_index,
                content=final_answer,
                tool_calls_count=tool_calls_count
            )
        
        return final_answer
    
    def generate_report(
        self, 
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        report_id: Optional[str] = None
    ) -> Report:
        """Generate a complete report and persist all intermediate artifacts.

        Output folder structure:
        - `meta.json`: report metadata/status
        - `outline.json`: planned outline
        - `progress.json`: live generation progress
        - `section_XX.md`: section outputs
        - `full_report.md`: assembled final markdown report

        Args:
            progress_callback: Optional callback `(stage, progress, message)`.
            report_id: Optional explicit report ID.

        Returns:
            Completed (or failed) report object.
        """
        import uuid
        
        # Auto-generate report ID when not provided.
        if not report_id:
            report_id = f"report_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()
        
        report = Report(
            report_id=report_id,
            simulation_id=self.simulation_id,
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
            status=ReportStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        # Tracks completed section titles for progress payloads.
        completed_section_titles = []
        
        try:
            # Initialize report folder and status files.
            ReportManager._ensure_report_folder(report_id)
            
            # Initialize structured action logger.
            self.report_logger = ReportLogger(report_id)
            self.report_logger.log_start(
                simulation_id=self.simulation_id,
                graph_id=self.graph_id,
                simulation_requirement=self.simulation_requirement
            )
            
            # Initialize plain-text console logger.
            self.console_logger = ReportConsoleLogger(report_id)
            
            ReportManager.update_progress(
                report_id, "pending", 0, "Initializing report generation...",
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            # Stage 1: outline planning
            report.status = ReportStatus.PLANNING
            ReportManager.update_progress(
                report_id, "planning", 5, "Starting report outline planning...",
                completed_sections=[]
            )
            
            # Record planning start.
            self.report_logger.log_planning_start()
            
            if progress_callback:
                progress_callback("planning", 0, "Starting report outline planning...")
            
            outline = self.plan_outline(
                progress_callback=lambda stage, prog, msg: 
                    progress_callback(stage, prog // 5, msg) if progress_callback else None
            )
            report.outline = outline
            
            # Record planning completion.
            self.report_logger.log_planning_complete(outline.to_dict())
            
            # Persist outline artifacts.
            ReportManager.save_outline(report_id, outline)
            ReportManager.update_progress(
                report_id, "planning", 15, f"Outline complete: {len(outline.sections)} sections",
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            logger.info(f"Outline saved: {report_id}/outline.json")
            
            # Stage 2: generate sections and persist each one.
            report.status = ReportStatus.GENERATING
            
            total_sections = len(outline.sections)
            generated_sections = []  # Keeps generated markdown for context reuse.
            
            for i, section in enumerate(outline.sections):
                section_num = i + 1
                base_progress = 20 + int((i / total_sections) * 70)
                
                # Update progress before section generation.
                ReportManager.update_progress(
                    report_id, "generating", base_progress,
                    f"Generating section: {section.title} ({section_num}/{total_sections})",
                    current_section=section.title,
                    completed_sections=completed_section_titles
                )
                
                if progress_callback:
                    progress_callback(
                        "generating", 
                        base_progress, 
                        f"Generating section: {section.title} ({section_num}/{total_sections})"
                    )
                
                # Generate section content with ReACT loop.
                section_content = self._generate_section_react(
                    section=section,
                    outline=outline,
                    previous_sections=generated_sections,
                    progress_callback=lambda stage, prog, msg:
                        progress_callback(
                            stage, 
                            base_progress + int(prog * 0.7 / total_sections),
                            msg
                        ) if progress_callback else None,
                    section_index=section_num
                )
                
                section.content = section_content
                generated_sections.append(f"## {section.title}\n\n{section_content}")

                # Save section markdown file.
                ReportManager.save_section(report_id, section_num, section)
                completed_section_titles.append(section.title)

                # Record section completion in action log.
                full_section_content = f"## {section.title}\n\n{section_content}"

                if self.report_logger:
                    self.report_logger.log_section_full_complete(
                        section_title=section.title,
                        section_index=section_num,
                        full_content=full_section_content.strip()
                    )

                logger.info(f"Section saved: {report_id}/section_{section_num:02d}.md")
                
                # Update progress after section completion.
                ReportManager.update_progress(
                    report_id, "generating", 
                    base_progress + int(70 / total_sections),
                    f"Section complete: {section.title}",
                    current_section=None,
                    completed_sections=completed_section_titles
                )
            
            # Stage 3: assemble final report.
            if progress_callback:
                progress_callback("generating", 95, "Assembling final report...")
            
            ReportManager.update_progress(
                report_id, "generating", 95, "Assembling final report...",
                completed_sections=completed_section_titles
            )
            
            # Build and persist full report markdown.
            report.markdown_content = ReportManager.assemble_full_report(report_id, outline)
            
            # Extract and append confidence summary
            confidence_summary = self._extract_confidence_summary(report.markdown_content)
            if confidence_summary:
                report.markdown_content += confidence_summary
                # Re-save the full report file with the appended summary
                full_path = ReportManager._get_report_markdown_path(report_id)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(report.markdown_content)

            # Append Sources & References section (Perplexity-style citations)
            references_section = self._build_references_section()
            if references_section:
                report.markdown_content += references_section
                full_path = ReportManager._get_report_markdown_path(report_id)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(report.markdown_content)

            # Generate 5-bullet executive summary and prepend to report
            if progress_callback:
                progress_callback("generating", 97, "Generating executive summary...")
            ReportManager.update_progress(
                report_id, "generating", 97, "Generating executive summary...",
                completed_sections=completed_section_titles
            )
            exec_summary = self._generate_executive_summary(report.markdown_content)
            if exec_summary:
                report.executive_summary = exec_summary
                exec_block = f"## Executive Summary\n\n{exec_summary}\n\n---\n\n"
                report.markdown_content = exec_block + report.markdown_content
                full_path = ReportManager._get_report_markdown_path(report_id)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(report.markdown_content)

            # Timeframe validation: check if the report addresses the user's specific time horizon
            timeframe_warning = self._validate_timeframe_coverage(report.markdown_content)
            if timeframe_warning:
                report.markdown_content += timeframe_warning
                full_path = ReportManager._get_report_markdown_path(report_id)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(report.markdown_content)

            # Multi-AI consensus validation (user-controlled)
            consensus_enabled = self.consensus_config.get("enabled", False)
            consensus_validators = self.consensus_config.get("validators", [])
            if consensus_enabled and consensus_validators:
                try:
                    from .consensus_validator import ConsensusValidator
                    consensus_validator = ConsensusValidator(
                        validator_indices=consensus_validators
                    )
                    if consensus_validator.is_available():
                        if progress_callback:
                            progress_callback("generating", 98, "Running multi-AI consensus validation...")
                        ReportManager.update_progress(
                            report_id, "generating", 98, "Running multi-AI consensus validation...",
                            completed_sections=completed_section_titles
                        )
                        validation_result = consensus_validator.validate_report(
                            report.markdown_content, self.simulation_requirement
                        )
                        report.consensus_validation = validation_result.to_dict()
                        # Append consensus markdown to report
                        if validation_result.markdown_section:
                            report.markdown_content += validation_result.markdown_section
                            full_path = ReportManager._get_report_markdown_path(report_id)
                            with open(full_path, 'w', encoding='utf-8') as f:
                                f.write(report.markdown_content)
                        logger.info(
                            f"Consensus validation complete: {validation_result.overall_consensus} "
                            f"({validation_result.validators_used} validators)"
                        )
                    else:
                        logger.info("Consensus validation skipped: selected validators not available")
                except Exception as e:
                    logger.warning(f"Consensus validation failed (non-fatal): {e}")
            else:
                logger.info(
                    f"Consensus validation skipped by user (enabled={consensus_enabled}, "
                    f"validators={consensus_validators})"
                )

            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()
            
            # Compute elapsed generation time.
            total_time_seconds = (datetime.now() - start_time).total_seconds()
            
            # Record report completion.
            if self.report_logger:
                self.report_logger.log_report_complete(
                    total_sections=total_sections,
                    total_time_seconds=total_time_seconds
                )
            
            # Save report
            ReportManager.save_report(report)
            ReportManager.update_progress(
                report_id, "completed", 100, "Report generation complete",
                completed_sections=completed_section_titles
            )
            
            if progress_callback:
                progress_callback("completed", 100, "Report generation complete")
            
            logger.info(f"Report generation complete: {report_id}")
            
            # Close console logger.
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
            
        except Exception as e:
            logger.error(f"Report generation failed: {type(e).__name__}: {e}")
            report.status = ReportStatus.FAILED
            report.error = f"Report generation failed: {type(e).__name__}"

            # Record failure event.
            if self.report_logger:
                self.report_logger.log_error(f"{type(e).__name__}: report generation encountered an error", "failed")

            # Persist failed state best-effort.
            try:
                ReportManager.save_report(report)
                ReportManager.update_progress(
                    report_id, "failed", -1, f"Report generation failed: {type(e).__name__}",
                    completed_sections=completed_section_titles
                )
            except Exception:
                pass  # Ignore save failure during failure handling.
            
            # Close console logger.
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
    
    def chat(
        self, 
        message: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Answer follow-up questions using report context and optional tool calls.

        Args:
            message: User message.
            chat_history: Optional prior chat messages.

        Returns:
            Dict with keys `response`, `tool_calls`, and `sources`.
        """
        logger.info(f"Report agent chat request: {message[:50]}...")
        
        chat_history = chat_history or []
        
        # Load previously generated report content (truncated for prompt safety).
        report_content = ""
        try:
            report = ReportManager.get_report_by_simulation(self.simulation_id)
            if report and report.markdown_content:
                # Cap prompt context to avoid oversized LLM requests.
                report_content = report.markdown_content[:15000]
                if len(report.markdown_content) > 15000:
                    report_content += "\n\n... [Report content truncated for context window] ..."
        except Exception as e:
            logger.warning(f"Failed to load report content for chat: {e}")
        
        system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            report_content=report_content if report_content else "(No report content available yet.)",
            tools_description=self._get_tools_description(),
        )

        # Build chat message list.
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add up to the last 10 history entries.
        for h in chat_history[-10:]:
            messages.append(h)
        
        # Add latest user message.
        messages.append({
            "role": "user", 
            "content": message
        })
        
        # Lightweight ReACT loop for chat mode.
        tool_calls_made = []
        max_iterations = 2
        
        for iteration in range(max_iterations):
            response = self.llm.chat(
                messages=messages,
                temperature=0.5
            )
            
            # Parse potential tool calls.
            tool_calls = self._parse_tool_calls(response)
            
            if not tool_calls:
                # No tool calls: return direct answer.
                clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
                clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
                
                return {
                    "response": clean_response.strip(),
                    "tool_calls": tool_calls_made,
                    "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
                }
            
            # Execute at most one tool per chat turn.
            tool_results = []
            for call in tool_calls[:1]:
                if len(tool_calls_made) >= self.MAX_TOOL_CALLS_PER_CHAT:
                    break
                result = self._execute_tool(call["name"], call.get("parameters", {}))
                tool_results.append({
                    "tool": call["name"],
                    "result": result[:1500]
                })
                tool_calls_made.append(call)
            
            # Feed tool observation back into the conversation.
            messages.append({"role": "assistant", "content": response})
            observation = "\n".join([f"[{r['tool']} result]\n{r['result']}" for r in tool_results])
            messages.append({
                "role": "user",
                "content": observation + CHAT_OBSERVATION_SUFFIX
            })
        
        # Final response after tool-augmented turns.
        final_response = self.llm.chat(
            messages=messages,
            temperature=0.5
        )
        
        # Remove any residual tool-call markup.
        clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL)
        clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
        
        return {
            "response": clean_response.strip(),
            "tool_calls": tool_calls_made,
            "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
        }


class ReportManager:
    """Report persistence manager for metadata, sections, and markdown artifacts.

        Folder structure:
        reports/
            {report_id}/
                meta.json
                outline.json
                progress.json
                section_01.md
                section_02.md
                ...
                full_report.md
        """
    
    # Report storage root directory.
    REPORTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'reports')
    
    @classmethod
    def _ensure_reports_dir(cls):
        """Ensure the reports root directory exists."""
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)
    
    @classmethod
    def _get_report_folder(cls, report_id: str) -> str:
        """Return folder path for one report."""
        return os.path.join(cls.REPORTS_DIR, report_id)
    
    @classmethod
    def _ensure_report_folder(cls, report_id: str) -> str:
        """Ensure report folder exists and return its path."""
        folder = cls._get_report_folder(report_id)
        os.makedirs(folder, exist_ok=True)
        return folder
    
    @classmethod
    def _get_report_path(cls, report_id: str) -> str:
        """Return path to report metadata JSON."""
        return os.path.join(cls._get_report_folder(report_id), "meta.json")
    
    @classmethod
    def _get_report_markdown_path(cls, report_id: str) -> str:
        """Get complete report Markdown file path."""
        return os.path.join(cls._get_report_folder(report_id), "full_report.md")
    
    @classmethod
    def _get_outline_path(cls, report_id: str) -> str:
        """Return path to outline JSON."""
        return os.path.join(cls._get_report_folder(report_id), "outline.json")
    
    @classmethod
    def _get_progress_path(cls, report_id: str) -> str:
        """Return path to progress JSON."""
        return os.path.join(cls._get_report_folder(report_id), "progress.json")
    
    @classmethod
    def _get_section_path(cls, report_id: str, section_index: int) -> str:
        """Get section Markdown file path."""
        return os.path.join(cls._get_report_folder(report_id), f"section_{section_index:02d}.md")
    
    @classmethod
    def _get_agent_log_path(cls, report_id: str) -> str:
        """Return path to structured agent log JSONL."""
        return os.path.join(cls._get_report_folder(report_id), "agent_log.jsonl")
    
    @classmethod
    def _get_console_log_path(cls, report_id: str) -> str:
        """Return path to console log file."""
        return os.path.join(cls._get_report_folder(report_id), "console_log.txt")
    
    @classmethod
    def get_console_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """Read plain-text console logs starting from a specific line."""
        log_path = cls._get_console_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    # Keep original line text but remove line endings.
                    logs.append(line.rstrip('\n\r'))
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # Entire file is returned from from_line.
        }
    
    @classmethod
    def get_console_log_stream(cls, report_id: str) -> List[str]:
        """Return all console log lines for a report."""
        result = cls.get_console_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def get_agent_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """Read structured agent log entries starting from a specific line."""
        log_path = cls._get_agent_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        # Skip malformed log rows.
                        continue
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # Entire file is returned from from_line.
        }
    
    @classmethod
    def get_agent_log_stream(cls, report_id: str) -> List[Dict[str, Any]]:
        """Return all structured agent log entries for a report."""
        result = cls.get_agent_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def save_outline(cls, report_id: str, outline: ReportOutline) -> None:
        """Persist report outline JSON."""
        cls._ensure_report_folder(report_id)
        
        with open(cls._get_outline_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"Outline saved: {report_id}")
    
    @classmethod
    def save_section(
        cls,
        report_id: str,
        section_index: int,
        section: ReportSection
    ) -> str:
        """Persist one section markdown file and return the file path."""
        cls._ensure_report_folder(report_id)

        # Build section markdown and remove duplicate top heading if present.
        cleaned_content = cls._clean_section_content(section.content, section.title)
        md_content = f"## {section.title}\n\n"
        if cleaned_content:
            md_content += f"{cleaned_content}\n\n"

        # Persist section markdown file.
        file_suffix = f"section_{section_index:02d}.md"
        file_path = os.path.join(cls._get_report_folder(report_id), file_suffix)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(f"Section saved: {report_id}/{file_suffix}")
        return file_path
    
    @classmethod
    def _clean_section_content(cls, content: str, section_title: str) -> str:
        """Normalize section content by removing duplicate headings."""
        import re
        
        if not content:
            return content
        
        content = content.strip()
        lines = content.split('\n')
        cleaned_lines = []
        skip_next_empty = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Check whether the line is a Markdown heading.
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title_text = heading_match.group(2).strip()
                
                # Remove duplicate section title headings near the top.
                if i < 5:
                    if title_text == section_title or title_text.replace(' ', '') == section_title.replace(' ', ''):
                        skip_next_empty = True
                        continue
                
                # Convert nested headings to bold text inside section content.
                cleaned_lines.append(f"**{title_text}**")
                cleaned_lines.append("")  # Add a spacer line after converted heading.
                continue
            
            # Skip immediate empty line after removing a duplicate heading.
            if skip_next_empty and stripped == '':
                skip_next_empty = False
                continue
            
            skip_next_empty = False
            cleaned_lines.append(line)
        
        # Trim leading blank lines.
        while cleaned_lines and cleaned_lines[0].strip() == '':
            cleaned_lines.pop(0)
        
        # Remove leading horizontal rule markers.
        while cleaned_lines and cleaned_lines[0].strip() in ['---', '***', '___']:
            cleaned_lines.pop(0)
            # Trim blank lines after marker removal.
            while cleaned_lines and cleaned_lines[0].strip() == '':
                cleaned_lines.pop(0)
        
        return '\n'.join(cleaned_lines)
    
    @classmethod
    def update_progress(
        cls, 
        report_id: str, 
        status: str, 
        progress: int, 
        message: str,
        current_section: str = None,
        completed_sections: List[str] = None
    ) -> None:
        """Persist current report-generation progress snapshot."""
        cls._ensure_report_folder(report_id)
        
        progress_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "current_section": current_section,
            "completed_sections": completed_sections or [],
            "updated_at": datetime.now().isoformat()
        }
        
        with open(cls._get_progress_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def get_progress(cls, report_id: str) -> Optional[Dict[str, Any]]:
        """Load progress JSON for a report, if present."""
        path = cls._get_progress_path(report_id)
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @classmethod
    def get_generated_sections(cls, report_id: str) -> List[Dict[str, Any]]:
        """Return metadata/content for all persisted section markdown files."""
        folder = cls._get_report_folder(report_id)
        
        if not os.path.exists(folder):
            return []
        
        sections = []
        for filename in sorted(os.listdir(folder)):
            if filename.startswith('section_') and filename.endswith('.md'):
                file_path = os.path.join(folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse section index from filename.
                parts = filename.replace('.md', '').split('_')
                section_index = int(parts[1])

                sections.append({
                    "filename": filename,
                    "section_index": section_index,
                    "content": content
                })

        return sections
    
    @classmethod
    def assemble_full_report(cls, report_id: str, outline: ReportOutline) -> str:
        """Assemble full report markdown from saved sections and persist it."""
        folder = cls._get_report_folder(report_id)
        
        # Build report header.
        md_content = f"# {outline.title}\n\n"
        md_content += f"> {outline.summary}\n\n"
        md_content += f"---\n\n"
        
        # Append all generated section files.
        sections = cls.get_generated_sections(report_id)
        for section_info in sections:
            md_content += section_info["content"]
        
        # Post-process heading consistency.
        md_content = cls._post_process_report(md_content, outline)
        
        # Persist full report markdown.
        full_path = cls._get_report_markdown_path(report_id)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Full report assembled: {report_id}")
        return md_content
    
    @classmethod
    def _post_process_report(cls, content: str, outline: ReportOutline) -> str:
        """Normalize heading levels and spacing in assembled report markdown."""
        import re
        
        lines = content.split('\n')
        processed_lines = []
        prev_was_heading = False
        
        # Build section title set for validation.
        section_titles = set()
        for section in outline.sections:
            section_titles.add(section.title)
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Detect markdown headings.
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # Remove duplicate headings that appear near each other.
                is_duplicate = False
                for j in range(max(0, len(processed_lines) - 5), len(processed_lines)):
                    prev_line = processed_lines[j].strip()
                    prev_match = re.match(r'^(#{1,6})\s+(.+)$', prev_line)
                    if prev_match:
                        prev_title = prev_match.group(2).strip()
                        if prev_title == title:
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    # Skip duplicate heading and trailing blank lines.
                    i += 1
                    while i < len(lines) and lines[i].strip() == '':
                        i += 1
                    continue
                
                # Heading normalization rules:
                # - # = report title
                # - ## = section title
                # - ### and deeper = bold inline heading
                
                if level == 1:
                    if title == outline.title:
                        # Preserve canonical report title.
                        processed_lines.append(line)
                        prev_was_heading = True
                    elif title in section_titles:
                        # Normalize section title level.
                        processed_lines.append(f"## {title}")
                        prev_was_heading = True
                    else:
                        # Convert other headings to bold text.
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                elif level == 2:
                    if title in section_titles or title == outline.title:
                        # Preserve recognized section heading.
                        processed_lines.append(line)
                        prev_was_heading = True
                    else:
                        # Convert non-section level-2 heading to bold text.
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                else:
                    # Convert level-3+ headings to bold text.
                    processed_lines.append(f"**{title}**")
                    processed_lines.append("")
                    prev_was_heading = False
                
                i += 1
                continue
            
            elif stripped == '---' and prev_was_heading:
                # Skip horizontal rule directly after heading.
                i += 1
                continue
            
            elif stripped == '' and prev_was_heading:
                # Keep at most one blank line after heading.
                if processed_lines and processed_lines[-1].strip()!= '':
                    processed_lines.append(line)
                prev_was_heading = False
            
            else:
                processed_lines.append(line)
                prev_was_heading = False
            
            i += 1
        
        # Collapse runs of blank lines to at most two.
        result_lines = []
        empty_count = 0
        for line in processed_lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    result_lines.append(line)
            else:
                empty_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @classmethod
    def save_report(cls, report: Report) -> None:
        """Persist report metadata, outline, and markdown content."""
        cls._ensure_report_folder(report.report_id)
        
        # Save metadata JSON.
        with open(cls._get_report_path(report.report_id), 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        
        # Save outline if present.
        if report.outline:
            cls.save_outline(report.report_id, report.outline)
        
        # Save full markdown report if present.
        if report.markdown_content:
            with open(cls._get_report_markdown_path(report.report_id), 'w', encoding='utf-8') as f:
                f.write(report.markdown_content)
        
        logger.info(f"Report saved: {report.report_id}")
    
    @classmethod
    def get_report(cls, report_id: str) -> Optional[Report]:
        """Load one report by ID from new or legacy storage format."""
        path = cls._get_report_path(report_id)
        
        if not os.path.exists(path):
            # Legacy format fallback.
            old_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
            if os.path.exists(old_path):
                path = old_path
            else:
                return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstruct outline object.
        outline = None
        if data.get('outline'):
            outline_data = data['outline']
            sections = []
            for s in outline_data.get('sections', []):
                sections.append(ReportSection(
                    title=s['title'],
                    content=s.get('content', '')
                ))
            outline = ReportOutline(
                title=outline_data['title'],
                summary=outline_data['summary'],
                sections=sections
            )
        
        # Fallback to reading full_report.md when markdown is absent in metadata.
        markdown_content = data.get('markdown_content', '')
        if not markdown_content:
            full_report_path = cls._get_report_markdown_path(report_id)
            if os.path.exists(full_report_path):
                with open(full_report_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
        
        return Report(
            report_id=data['report_id'],
            simulation_id=data['simulation_id'],
            graph_id=data['graph_id'],
            simulation_requirement=data['simulation_requirement'],
            status=ReportStatus(data['status']),
            outline=outline,
            markdown_content=markdown_content,
            created_at=data.get('created_at', ''),
            completed_at=data.get('completed_at', ''),
            error=data.get('error'),
            executive_summary=data.get('executive_summary', ''),
            consensus_validation=data.get('consensus_validation', {}),
        )
    
    @classmethod
    def get_report_by_simulation(cls, simulation_id: str) -> Optional[Report]:
        """Return the first report matching a simulation ID."""
        cls._ensure_reports_dir()
        
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # New format: per-report folder.
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report and report.simulation_id == simulation_id:
                    return report
            # Legacy format: report JSON file.
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report and report.simulation_id == simulation_id:
                    return report
        
        return None
    
    @classmethod
    def list_reports(cls, simulation_id: Optional[str] = None, limit: int = 50) -> List[Report]:
        """List reports, optionally filtered by simulation ID."""
        cls._ensure_reports_dir()
        
        reports = []
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # New format: per-report folder.
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
            # Legacy format: report JSON file.
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
        
        # Sort by creation time descending.
        reports.sort(key=lambda r: r.created_at, reverse=True)
        
        return reports[:limit]
    
    @classmethod
    def delete_report(cls, report_id: str) -> bool:
        """Delete report artifacts in new and legacy storage formats."""
        import shutil
        
        folder_path = cls._get_report_folder(report_id)
        
        # New format: delete report folder.
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            logger.info(f"Report folder deleted: {report_id}")
            return True
        
        # Legacy format: delete individual files.
        deleted = False
        old_json_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
        old_md_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.md")
        
        if os.path.exists(old_json_path):
            os.remove(old_json_path)
            deleted = True
        if os.path.exists(old_md_path):
            os.remove(old_md_path)
            deleted = True
        
        return deleted
