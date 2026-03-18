"""
Zep tools service.
Provides graph search, node reading, multi-dimensional query tools for Report Agent.

Core tools (high-level):
1. InsightForge (deep analysis) - multi-dimensional query, auto-generates sub-queries, aggregates results
2. PanoramaSearch (full-scope search) - gets all info including historical content
3. QuickSearch (fast search) - lightweight single-query search
"""

import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from zep_cloud.client import Zep

from..config import Config
from..utils.logger import get_logger
from..utils.llm_client import LLMClient
from..utils.zep_paging import fetch_all_nodes, fetch_all_edges

logger = get_logger('phoring.zep_tools')


@dataclass
class SearchResult:
    """Search result container."""
    facts: List[str]
    edges: List[Dict[str, Any]]
    nodes: List[Dict[str, Any]]
    query: str
    total_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": self.facts,
            "edges": self.edges,
            "nodes": self.nodes,
            "query": self.query,
            "total_count": self.total_count
        }
    
    def to_text(self) -> str:
        """Convert to text format for LLM consumption."""
        text_parts = [f"Search query: {self.query}", f"Found {self.total_count} relevant items"]

        if self.facts:
            text_parts.append("\n### Key Facts:")
            for i, fact in enumerate(self.facts, 1):
                text_parts.append(f"{i}. {fact}")
        
        return "\n".join(text_parts)


@dataclass
class NodeInfo:
    """Node information container."""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes
        }
    
    def to_text(self) -> str:
        """Convert to text format."""
        entity_type = next((l for l in self.labels if l not in ["Entity", "Node"]), "unknown type")
        return f"Entity: {self.name} (type: {entity_type})\nSummary: {self.summary}"


@dataclass
class EdgeInfo:
    """Edge (relationship) information container."""
    uuid: str
    name: str
    fact: str
    source_node_uuid: str
    target_node_uuid: str
    source_node_name: Optional[str] = None
    target_node_name: Optional[str] = None
    # Temporal info
    created_at: Optional[str] = None
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "fact": self.fact,
            "source_node_uuid": self.source_node_uuid,
            "target_node_uuid": self.target_node_uuid,
            "source_node_name": self.source_node_name,
            "target_node_name": self.target_node_name,
            "created_at": self.created_at,
            "valid_at": self.valid_at,
            "invalid_at": self.invalid_at,
            "expired_at": self.expired_at
        }
    
    def to_text(self, include_temporal: bool = False) -> str:
        """Convert to text format."""
        source = self.source_node_name or self.source_node_uuid[:8]
        target = self.target_node_name or self.target_node_uuid[:8]
        base_text = f"Relation: {source} --[{self.name}]--> {target}\nFact: {self.fact}"

        if include_temporal:
            valid_at = self.valid_at or "unknown"
            invalid_at = self.invalid_at or "ongoing"
            base_text += f"\nValidity: {valid_at} - {invalid_at}"
            if self.expired_at:
                base_text += f" (expired: {self.expired_at})"
        
        return base_text
    
    @property
    def is_expired(self) -> bool:
        """Whether this edge has expired."""
        return self.expired_at is not None

    @property
    def is_invalid(self) -> bool:
        """Whether this edge has been invalidated."""
        return self.invalid_at is not None


@dataclass
class InsightForgeResult:
    """
    Deep analysis result (InsightForge).
    Includes aggregated search results and multi-dimensional analysis.
    """
    query: str
    simulation_requirement: str
    sub_queries: List[str]
    
    # Search results
    semantic_facts: List[str] = field(default_factory=list)        # Semantic search results
    entity_insights: List[Dict[str, Any]] = field(default_factory=list)  # Entity insights
    relationship_chains: List[str] = field(default_factory=list)   # Relationship chains

    # Statistics
    total_facts: int = 0
    total_entities: int = 0
    total_relationships: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "simulation_requirement": self.simulation_requirement,
            "sub_queries": self.sub_queries,
            "semantic_facts": self.semantic_facts,
            "entity_insights": self.entity_insights,
            "relationship_chains": self.relationship_chains,
            "total_facts": self.total_facts,
            "total_entities": self.total_entities,
            "total_relationships": self.total_relationships
        }
    
    def to_text(self) -> str:
        """Convert to detailed text format for LLM consumption."""
        text_parts = [
            f"## Prediction Engine Analysis",
            f"Query: {self.query}",
            f"Prediction scenario: {self.simulation_requirement}",
            f"\n### Prediction Data Summary",
            f"- Facts found: {self.total_facts}",
            f"- Entities: {self.total_entities}",
            f"- Relationships: {self.total_relationships}"
        ]

        # Sub-queries
        if self.sub_queries:
            text_parts.append(f"\n### Analysis Dimensions")
            for i, sq in enumerate(self.sub_queries, 1):
                text_parts.append(f"{i}. {sq}")

        # Semantic search results
        if self.semantic_facts:
            text_parts.append(f"\n### [Key Facts] (please cite in report)")
            for i, fact in enumerate(self.semantic_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")

        # Entity insights
        if self.entity_insights:
            text_parts.append(f"\n### [Core Entities]")
            for entity in self.entity_insights:
                text_parts.append(f"- **{entity.get('name', 'unknown')}** ({entity.get('type', 'entity')})")
                if entity.get('summary'):
                    text_parts.append(f"  Summary: \"{entity.get('summary')}\"")
                if entity.get('related_facts'):
                    text_parts.append(f"  Related facts: {len(entity.get('related_facts', []))}")

        # Relationship chains
        if self.relationship_chains:
            text_parts.append(f"\n### [Relationships]")
            for chain in self.relationship_chains:
                text_parts.append(f"- {chain}")
        
        return "\n".join(text_parts)


@dataclass
class PanoramaResult:
    """
    Full-scope search result (Panorama).
    Includes all graph information, including historical content.
    """
    query: str
    
    # All nodes
    all_nodes: List[NodeInfo] = field(default_factory=list)
    # All edges (including historical)
    all_edges: List[EdgeInfo] = field(default_factory=list)
    # Currently active facts
    active_facts: List[str] = field(default_factory=list)
    # Expired/invalidated facts (historical record)
    historical_facts: List[str] = field(default_factory=list)

    # Statistics
    total_nodes: int = 0
    total_edges: int = 0
    active_count: int = 0
    historical_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "all_nodes": [n.to_dict() for n in self.all_nodes],
            "all_edges": [e.to_dict() for e in self.all_edges],
            "active_facts": self.active_facts,
            "historical_facts": self.historical_facts,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "active_count": self.active_count,
            "historical_count": self.historical_count
        }
    
    def to_text(self) -> str:
        """Convert to text format (complete output, no truncation)."""
        text_parts = [
            f"## Full-Scope Search Results",
            f"Query: {self.query}",
            f"\n### Statistics",
            f"- Nodes: {self.total_nodes}",
            f"- Edges: {self.total_edges}",
            f"- Active facts: {self.active_count}",
            f"- Expired/invalidated: {self.historical_count}"
        ]

        # Active facts (complete output, no truncation)
        if self.active_facts:
            text_parts.append(f"\n### [Active Facts] (simulation results)")
            for i, fact in enumerate(self.active_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")

        # Historical facts (complete output, no truncation)
        if self.historical_facts:
            text_parts.append(f"\n### [Expired/Invalidated] (historical record)")
            for i, fact in enumerate(self.historical_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")

        # All entities (complete output, no truncation)
        if self.all_nodes:
            text_parts.append(f"\n### [All Entities]")
            for node in self.all_nodes:
                entity_type = next((l for l in node.labels if l not in ["Entity", "Node"]), "entity")
                text_parts.append(f"- **{node.name}** ({entity_type})")
        
        return "\n".join(text_parts)


@dataclass
class AgentInterview:
    """Single agent interview result."""
    agent_name: str
    agent_role: str    # Role type (e.g., investor, analyst, media)
    agent_bio: str     # Agent biography
    question: str      # Interview question(s)
    response: str      # Interview response
    key_quotes: List[str] = field(default_factory=list)  # Notable quotes
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "agent_bio": self.agent_bio,
            "question": self.question,
            "response": self.response,
            "key_quotes": self.key_quotes
        }
    
    def to_text(self) -> str:
        text = f"**{self.agent_name}** ({self.agent_role})\n"
        # Output full agent_bio without truncation
        text += f"_Bio: {self.agent_bio}_\n\n"
        text += f"**Q:** {self.question}\n\n"
        text += f"**A:** {self.response}\n"
        if self.key_quotes:
            text += "\n**Key Quotes:**\n"
            for quote in self.key_quotes:
                # Clean up quotation marks
                clean_quote = quote.replace('\u201c', '').replace('\u201d', '').replace('"', '')
                clean_quote = clean_quote.replace('\u300c', '').replace('\u300d', '')
                clean_quote = clean_quote.strip()
                # Strip leading punctuation
                while clean_quote and clean_quote[0] in ',,;;::,.!?\n\r\t ':
                    clean_quote = clean_quote[1:]
                # Filter out question-number content (e.g., "Question 1-9")
                skip = False
                for d in '123456789':
                    if f'\u95ee\u9898{d}' in clean_quote:
                        skip = True
                        break
                if skip:
                    continue
                # Truncate overly long quotes at a sentence boundary
                if len(clean_quote) > 150:
                    dot_pos = clean_quote.find('\u3002', 80)
                    if dot_pos > 0:
                        clean_quote = clean_quote[:dot_pos + 1]
                    else:
                        clean_quote = clean_quote[:147] + "..."
                if clean_quote and len(clean_quote) >= 10:
                    text += f'> "{clean_quote}"\n'
        return text


@dataclass
class InterviewResult:
    """
    Interview result container.
    Includes simulation agent interview responses.
    """
    interview_topic: str                    # Interview topic
    interview_questions: List[str]          # Interview question list

    # Selected agents for interview
    selected_agents: List[Dict[str, Any]] = field(default_factory=list)
    # Agent interview responses
    interviews: List[AgentInterview] = field(default_factory=list)

    # Agent selection reasoning
    selection_reasoning: str = ""
    # Interview summary
    summary: str = ""

    # Statistics
    total_agents: int = 0
    interviewed_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "interview_topic": self.interview_topic,
            "interview_questions": self.interview_questions,
            "selected_agents": self.selected_agents,
            "interviews": [i.to_dict() for i in self.interviews],
            "selection_reasoning": self.selection_reasoning,
            "summary": self.summary,
            "total_agents": self.total_agents,
            "interviewed_count": self.interviewed_count
        }
    
    def to_text(self) -> str:
        """Convert to detailed text format for LLM report citation."""
        text_parts = [
            "## Interview Report",
            f"**Topic:** {self.interview_topic}",
            f"**Interviewed:** {self.interviewed_count} / {self.total_agents} simulation agents",
            "\n### Selection Rationale",
            self.selection_reasoning or "(auto-selected)",
            "\n---",
            "\n### Interview Details",
        ]

        if self.interviews:
            for i, interview in enumerate(self.interviews, 1):
                text_parts.append(f"\n#### Interview #{i}: {interview.agent_name}")
                text_parts.append(interview.to_text())
                text_parts.append("\n---")
        else:
            text_parts.append("(No interview records)\n\n---")

        text_parts.append("\n### Interview Summary & Key Opinions")
        text_parts.append(self.summary or "(No summary available)")

        return "\n".join(text_parts)


class ZepToolsService:
    """
    Zep tools service.

    [Core tools - high level]
    1. insight_forge - Deep analysis (multi-dimensional query, auto-generates sub-queries, aggregates results)
    2. panorama_search - Full-scope search (gets all info including historical content)
    3. quick_search - Fast search (lightweight single-query)
    4. interview_agents - Agent interview (interview simulation agents, get opinions)

    [Base tools]
    - search_graph - Semantic graph search
    - get_all_nodes - Get all graph nodes
    - get_all_edges - Get all graph edges (with temporal info)
    - get_node_detail - Get detailed node info
    - get_node_edges - Get edges for a node
    - get_entities_by_type - Get entities by type
    - get_entity_summary - Get entity relationship summary
    """

    # Retry config
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0
    
    def __init__(self, api_key: Optional[str] = None, llm_client: Optional[LLMClient] = None):
        self.api_key = api_key or Config.ZEP_API_KEY
        if not self.api_key:
            raise ValueError("ZEP_API_KEY not yet configured")
        
        self.client = Zep(api_key=self.api_key)
        # Use LLM client for InsightForge generation
        self._llm_client = llm_client
        logger.info("ZepToolsService initialized")

    @property
    def llm(self) -> LLMClient:
        """Lazily initialize the LLM client."""
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client
    
    def _call_with_retry(self, func, operation_name: str, max_retries: int = None):
        """Call an API function with retry logic."""
        max_retries = max_retries or self.MAX_RETRIES
        last_exception = None
        delay = self.RETRY_DELAY
        
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Zep {operation_name} attempt {attempt + 1} failed: {str(e)[:100]}, "
                        f"retrying in {delay:.1f} seconds..."
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error(f"Zep {operation_name} failed after {max_retries} attempts: {str(e)}")
        
        if last_exception is not None:
            raise last_exception
        raise RuntimeError(f"Zep {operation_name} failed: max_retries was 0")

    def search_graph(
        self, 
        graph_id: str, 
        query: str, 
        limit: int = 10,
        scope: str = "edges"
    ) -> SearchResult:
        """
        Semantic graph search.

        Uses semantic search (vector + BM25) to find relevant graph information.
        Falls back to local keyword matching if the Zep Cloud Search API fails.

        Args:
            graph_id: Graph ID (Standalone Graph)
            query: Search query
            limit: Maximum number of results to return
            scope: Search scope, "edges" or "nodes"

        Returns:
            SearchResult: Search results
        """
        logger.info(f"Graph search: graph_id={graph_id}, query={query[:50]}...")

        # Zep Cloud Search API
        try:
            search_results = self._call_with_retry(
                func=lambda: self.client.graph.search(
                    graph_id=graph_id,
                    query=query,
                    limit=limit,
                    scope=scope,
                    reranker="cross_encoder"
                ),
                operation_name=f"graph search (graph={graph_id})"
            )
            
            facts = []
            edges = []
            nodes = []
            
            # Parse search results
            if hasattr(search_results, 'edges') and search_results.edges:
                for edge in search_results.edges:
                    if hasattr(edge, 'fact') and edge.fact:
                        facts.append(edge.fact)
                    edges.append({
                        "uuid": getattr(edge, 'uuid_', None) or getattr(edge, 'uuid', ''),
                        "name": getattr(edge, 'name', ''),
                        "fact": getattr(edge, 'fact', ''),
                        "source_node_uuid": getattr(edge, 'source_node_uuid', ''),
                        "target_node_uuid": getattr(edge, 'target_node_uuid', ''),
                    })
            
            # Parse node search results
            if hasattr(search_results, 'nodes') and search_results.nodes:
                for node in search_results.nodes:
                    nodes.append({
                        "uuid": getattr(node, 'uuid_', None) or getattr(node, 'uuid', ''),
                        "name": getattr(node, 'name', ''),
                        "labels": getattr(node, 'labels', []),
                        "summary": getattr(node, 'summary', ''),
                    })
                    # Add node summary as a fact
                    if hasattr(node, 'summary') and node.summary:
                        facts.append(f"[{node.name}]: {node.summary}")
            
            logger.info(f"Search complete: found {len(facts)} facts")
            
            return SearchResult(
                facts=facts,
                edges=edges,
                nodes=nodes,
                query=query,
                total_count=len(facts)
            )
            
        except Exception as e:
            logger.warning(f"Zep Search API failed, falling back to local search: {str(e)}")
            # Fallback: keyword matching search
            return self._local_search(graph_id, query, limit, scope)
    
    def _local_search(
        self, 
        graph_id: str, 
        query: str, 
        limit: int = 10,
        scope: str = "edges"
    ) -> SearchResult:
        """
        Local keyword matching search (fallback when Zep Search API fails).

        Gets all edges/nodes, then performs keyword matching.

        Args:
            graph_id: Graph ID
            query: Search query
            limit: Maximum number of results to return
            scope: Search scope

        Returns:
            SearchResult: Search results
        """
        logger.info(f"Local search: query={query[:30]}...")
        
        facts = []
        edges_result = []
        nodes_result = []
        
        # Split query into keywords
        query_lower = query.lower()
        keywords = [w.strip() for w in query_lower.replace(',', ' ').replace(', ', ' ').split() if len(w.strip()) > 1]

        def match_score(text: str) -> int:
            """Calculate how well text matches the query."""
            if not text:
                return 0
            text_lower = text.lower()
            # Exact query match
            if query_lower in text_lower:
                return 100
            # Keyword matching
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 10
            return score
        
        try:
            if scope in ["edges", "both"]:
                # Get all edges and match
                all_edges = self.get_all_edges(graph_id)
                scored_edges = []
                for edge in all_edges:
                    score = match_score(edge.fact) + match_score(edge.name)
                    if score > 0:
                        scored_edges.append((score, edge))
                
                # Sort by relevance score
                scored_edges.sort(key=lambda x: x[0], reverse=True)
                
                for score, edge in scored_edges[:limit]:
                    if edge.fact:
                        facts.append(edge.fact)
                    edges_result.append({
                        "uuid": edge.uuid,
                        "name": edge.name,
                        "fact": edge.fact,
                        "source_node_uuid": edge.source_node_uuid,
                        "target_node_uuid": edge.target_node_uuid,
                    })
            
            if scope in ["nodes", "both"]:
                # Get all nodes and match
                all_nodes = self.get_all_nodes(graph_id)
                scored_nodes = []
                for node in all_nodes:
                    score = match_score(node.name) + match_score(node.summary)
                    if score > 0:
                        scored_nodes.append((score, node))
                
                scored_nodes.sort(key=lambda x: x[0], reverse=True)
                
                for score, node in scored_nodes[:limit]:
                    nodes_result.append({
                        "uuid": node.uuid,
                        "name": node.name,
                        "labels": node.labels,
                        "summary": node.summary,
                    })
                    if node.summary:
                        facts.append(f"[{node.name}]: {node.summary}")
            
            logger.info(f"Local search complete: found {len(facts)} facts")

        except Exception as e:
            logger.error(f"Local search failed: {str(e)}")
        
        return SearchResult(
            facts=facts,
            edges=edges_result,
            nodes=nodes_result,
            query=query,
            total_count=len(facts)
        )
    
    def get_all_nodes(self, graph_id: str) -> List[NodeInfo]:
        """
        Get all nodes from a graph (paginated fetch).

        Args:
            graph_id: Graph ID

        Returns:
            List of NodeInfo objects
        """
        logger.info(f"Fetching all nodes from graph {graph_id}...")

        nodes = fetch_all_nodes(self.client, graph_id)

        result = []
        for node in nodes:
            node_uuid = getattr(node, 'uuid_', None) or getattr(node, 'uuid', None) or ""
            result.append(NodeInfo(
                uuid=str(node_uuid) if node_uuid else "",
                name=node.name or "",
                labels=node.labels or [],
                summary=node.summary or "",
                attributes=node.attributes or {}
            ))

        logger.info(f"Fetched {len(result)} nodes")
        return result

    def get_all_edges(self, graph_id: str, include_temporal: bool = True) -> List[EdgeInfo]:
        """
        Get all edges from a graph (paginated fetch, includes temporal info).

        Args:
            graph_id: Graph ID
            include_temporal: Whether to include temporal info (default True)

        Returns:
            List of EdgeInfo objects (includes created_at, valid_at, invalid_at, expired_at)
        """
        logger.info(f"Fetching all edges from graph {graph_id}...")

        edges = fetch_all_edges(self.client, graph_id)

        result = []
        for edge in edges:
            edge_uuid = getattr(edge, 'uuid_', None) or getattr(edge, 'uuid', None) or ""
            edge_info = EdgeInfo(
                uuid=str(edge_uuid) if edge_uuid else "",
                name=edge.name or "",
                fact=edge.fact or "",
                source_node_uuid=edge.source_node_uuid or "",
                target_node_uuid=edge.target_node_uuid or ""
            )

            # Add temporal info
            if include_temporal:
                edge_info.created_at = getattr(edge, 'created_at', None)
                edge_info.valid_at = getattr(edge, 'valid_at', None)
                edge_info.invalid_at = getattr(edge, 'invalid_at', None)
                edge_info.expired_at = getattr(edge, 'expired_at', None)

            result.append(edge_info)

        logger.info(f"Fetched {len(result)} edges")
        return result

    def get_node_detail(self, node_uuid: str) -> Optional[NodeInfo]:
        """
        Get detailed node information.

        Args:
            node_uuid: Node UUID

        Returns:
            NodeInfo or None
        """
        logger.info(f"Getting node detail: {node_uuid[:8]}...")
        
        try:
            node = self._call_with_retry(
                func=lambda: self.client.graph.node.get(uuid_=node_uuid),
                operation_name=f"get node detail (uuid={node_uuid[:8]}...)"
            )
            
            if not node:
                return None
            
            return NodeInfo(
                uuid=getattr(node, 'uuid_', None) or getattr(node, 'uuid', ''),
                name=node.name or "",
                labels=node.labels or [],
                summary=node.summary or "",
                attributes=node.attributes or {}
            )
        except Exception as e:
            logger.error(f"Failed to get node detail: {str(e)}")
            return None
    
    def get_node_edges(self, graph_id: str, node_uuid: str) -> List[EdgeInfo]:
        """
        Get all edges connected to a node.

        Fetches all graph edges, then filters for those connected to the specified node.

        Args:
            graph_id: Graph ID
            node_uuid: Node UUID

        Returns:
            List of EdgeInfo objects
        """
        logger.info(f"Getting edges for node {node_uuid[:8]}...")
        
        try:
            # Get all graph edges, then filter
            all_edges = self.get_all_edges(graph_id)
            
            result = []
            for edge in all_edges:
                # Check if edge connects to this node (as source or target)
                if edge.source_node_uuid == node_uuid or edge.target_node_uuid == node_uuid:
                    result.append(edge)
            
            logger.info(f"Found {len(result)} edges for node")
            return result

        except Exception as e:
            logger.warning(f"Failed to get node edges: {str(e)}")
            return []
    
    def get_entities_by_type(
        self, 
        graph_id: str, 
        entity_type: str
    ) -> List[NodeInfo]:
        """
        Get entities by type.

        Args:
            graph_id: Graph ID
            entity_type: Entity type (e.g., Student, PublicFigure)

        Returns:
            List of entities matching the specified type
        """
        logger.info(f"Getting entities of type {entity_type}...")
        
        all_nodes = self.get_all_nodes(graph_id)
        
        filtered = []
        for node in all_nodes:
            # Check if labels include this type
            if entity_type in node.labels:
                filtered.append(node)
        
        logger.info(f"Found {len(filtered)} entities of type {entity_type}")
        return filtered
    
    def get_entity_summary(
        self, 
        graph_id: str, 
        entity_name: str
    ) -> Dict[str, Any]:
        """
        Get an entity's relationship summary.

        Searches for all information related to the entity and generates a summary.

        Args:
            graph_id: Graph ID
            entity_name: Entity name

        Returns:
            Entity summary information dict
        """
        logger.info(f"Getting relationship summary for entity {entity_name}...")

        # Search for entity-related information
        search_result = self.search_graph(
            graph_id=graph_id,
            query=entity_name,
            limit=20
        )
        
        # Find the entity node among all nodes
        all_nodes = self.get_all_nodes(graph_id)
        entity_node = None
        for node in all_nodes:
            if node.name.lower() == entity_name.lower():
                entity_node = node
                break
        
        related_edges = []
        if entity_node:
            # Pass graph_id parameter
            related_edges = self.get_node_edges(graph_id, entity_node.uuid)
        
        return {
            "entity_name": entity_name,
            "entity_info": entity_node.to_dict() if entity_node else None,
            "related_facts": search_result.facts,
            "related_edges": [e.to_dict() for e in related_edges],
            "total_relations": len(related_edges)
        }
    
    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        """
        Get graph statistics.

        Args:
            graph_id: Graph ID

        Returns:
            Statistics dictionary
        """
        logger.info(f"Getting statistics for graph {graph_id}...")
        
        nodes = self.get_all_nodes(graph_id)
        edges = self.get_all_edges(graph_id)
        
        # Count entity types
        entity_types = {}
        for node in nodes:
            for label in node.labels:
                if label not in ["Entity", "Node"]:
                    entity_types[label] = entity_types.get(label, 0) + 1

        # Count relationship types
        relation_types = {}
        for edge in edges:
            relation_types[edge.name] = relation_types.get(edge.name, 0) + 1
        
        return {
            "graph_id": graph_id,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_types": entity_types,
            "relation_types": relation_types
        }
    
    def get_simulation_context(
        self, 
        graph_id: str,
        simulation_requirement: str,
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Get simulation context information.

        Searches for all information related to the simulation requirement.

        Args:
            graph_id: Graph ID
            simulation_requirement: Simulation requirement description
            limit: Maximum number of items to return

        Returns:
            Simulation context dictionary
        """
        logger.info(f"Getting simulation context: {simulation_requirement[:50]}...")

        # Search for simulation-related information
        search_result = self.search_graph(
            graph_id=graph_id,
            query=simulation_requirement,
            limit=limit
        )
        
        # Get graph statistics
        stats = self.get_graph_statistics(graph_id)

        # Get all entity nodes
        all_nodes = self.get_all_nodes(graph_id)
        
        # Filter for typed entities (exclude plain Entity nodes)
        entities = []
        for node in all_nodes:
            custom_labels = [l for l in node.labels if l not in ["Entity", "Node"]]
            if custom_labels:
                entities.append({
                    "name": node.name,
                    "type": custom_labels[0],
                    "summary": node.summary
                })
        
        return {
            "simulation_requirement": simulation_requirement,
            "related_facts": search_result.facts,
            "graph_statistics": stats,
            "entities": entities[:limit],  # Limit count
            "total_entities": len(entities)
        }
    
    # ========== Core Tools (High-Level) ==========
    
    def insight_forge(
        self,
        graph_id: str,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_sub_queries: int = 5
    ) -> InsightForgeResult:
        """
        [InsightForge - Deep Analysis]

        A compound function that automatically:
        1. Uses LLM to generate analysis sub-queries
        2. Executes each sub-query as a search
        3. Gets detailed info for related entities
        4. Builds relationship chains
        5. Aggregates all results into a structured output

        Args:
            graph_id: Graph ID
            query: User query
            simulation_requirement: Simulation requirement description
            report_context: Report context (optional, helps generate better sub-queries)
            max_sub_queries: Maximum number of sub-queries

        Returns:
            InsightForgeResult: Deep analysis result
        """
        logger.info(f"InsightForge starting: {query[:50]}...")
        
        result = InsightForgeResult(
            query=query,
            simulation_requirement=simulation_requirement,
            sub_queries=[]
        )
        
        # Step 1: Use LLM to generate sub-queries
        sub_queries = self._generate_sub_queries(
            query=query,
            simulation_requirement=simulation_requirement,
            report_context=report_context,
            max_queries=max_sub_queries
        )
        result.sub_queries = sub_queries
        logger.info(f"Generated {len(sub_queries)} sub-queries")

        # Step 2: Execute each sub-query search
        all_facts = []
        all_edges = []
        seen_facts = set()
        
        for sub_query in sub_queries:
            search_result = self.search_graph(
                graph_id=graph_id,
                query=sub_query,
                limit=15,
                scope="edges"
            )
            
            for fact in search_result.facts:
                if fact not in seen_facts:
                    all_facts.append(fact)
                    seen_facts.add(fact)
            
            all_edges.extend(search_result.edges)
        
        # Also search the original query directly
        main_search = self.search_graph(
            graph_id=graph_id,
            query=query,
            limit=20,
            scope="edges"
        )
        for fact in main_search.facts:
            if fact not in seen_facts:
                all_facts.append(fact)
                seen_facts.add(fact)
        
        result.semantic_facts = all_facts
        result.total_facts = len(all_facts)
        
        # Step 3: Collect entity UUIDs and get detailed entity info
        entity_uuids = set()
        for edge_data in all_edges:
            if isinstance(edge_data, dict):
                source_uuid = edge_data.get('source_node_uuid', '')
                target_uuid = edge_data.get('target_node_uuid', '')
                if source_uuid:
                    entity_uuids.add(source_uuid)
                if target_uuid:
                    entity_uuids.add(target_uuid)
        
        # Get all entity details (no limit, complete output)
        entity_insights = []
        node_map = {}  # For building relationship chains
        
        for uuid in list(entity_uuids):  # Process all entities, no truncation
            if not uuid:
                continue
            try:
                # Get each node's info
                node = self.get_node_detail(uuid)
                if node:
                    node_map[uuid] = node
                    entity_type = next((l for l in node.labels if l not in ["Entity", "Node"]), "entity")
                    
                    # Get all related facts for this entity (no truncation)
                    related_facts = [
                        f for f in all_facts 
                        if node.name.lower() in f.lower()
                    ]
                    
                    entity_insights.append({
                        "uuid": node.uuid,
                        "name": node.name,
                        "type": entity_type,
                        "summary": node.summary,
                        "related_facts": related_facts  # Complete output, no truncation
                    })
            except Exception as e:
                logger.debug(f"Failed to get node {uuid}: {e}")
                continue
        
        result.entity_insights = entity_insights
        result.total_entities = len(entity_insights)
        
        # Step 4: Build all relationship chains (no limit)
        relationship_chains = []
        for edge_data in all_edges:  # Process all edges, no truncation
            if isinstance(edge_data, dict):
                source_uuid = edge_data.get('source_node_uuid', '')
                target_uuid = edge_data.get('target_node_uuid', '')
                relation_name = edge_data.get('name', '')
                
                source_name = node_map.get(source_uuid, NodeInfo('', '', [], '', {})).name or source_uuid[:8]
                target_name = node_map.get(target_uuid, NodeInfo('', '', [], '', {})).name or target_uuid[:8]
                
                chain = f"{source_name} --[{relation_name}]--> {target_name}"
                if chain not in relationship_chains:
                    relationship_chains.append(chain)
        
        result.relationship_chains = relationship_chains
        result.total_relationships = len(relationship_chains)
        
        logger.info(f"InsightForge complete: {result.total_facts} facts, {result.total_entities} entities, {result.total_relationships} relationships")
        return result
    
    def _generate_sub_queries(
        self,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_queries: int = 5
    ) -> List[str]:
        """
        Use LLM to generate analysis sub-queries.

        Falls back to default queries on failure.
        """
        system_prompt = """You are a data analysis expert. Your task is to analyze simulation observations.

Requirements:
1. Each sub-query should target a concrete simulation agent behavior or event
2. Cover multiple dimensions (e.g., actions, interactions, sentiment, trends, relationships, outcomes)
3. Sub-queries should be relevant to the simulation scenario
4. Return JSON format: {"sub_queries": ["Query 1", "Query 2",...]}"""

        user_prompt = f"""Simulation requirement:
{simulation_requirement}

{f"Report context: {report_context[:500]}" if report_context else ""}

Please generate {max_queries} sub-queries for:
{query}

Return as a JSON format list."""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            sub_queries = response.get("sub_queries", [])
            # Ensure string list
            return [str(sq) for sq in sub_queries[:max_queries]]
            
        except Exception as e:
            logger.warning(f"Sub-query generation failed: {str(e)}, using defaults")
            # Fallback: return default queries
            return [
                query,
                f"{query} main participants",
                f"{query} influence and impact",
                f"{query} outcomes and trends"
            ][:max_queries]
    
    def panorama_search(
        self,
        graph_id: str,
        query: str,
        include_expired: bool = True,
        limit: int = 50
    ) -> PanoramaResult:
        """
        [PanoramaSearch - Full-Scope Search]

        Gets a panoramic view, including all historical content and active info:
        1. Get all nodes
        2. Get all edges (including expired/invalidated)
        3. Separate active vs. historical facts

        This tool is suitable for analyzing event timelines and scenario evolution.

        Args:
            graph_id: Graph ID
            query: Search query (for relevance sorting)
            include_expired: Whether to include historical content (default True)
            limit: Maximum number of results per category

        Returns:
            PanoramaResult: Full-scope search results
        """
        logger.info(f"PanoramaSearch: {query[:50]}...")
        
        result = PanoramaResult(query=query)
        
        # Get all nodes
        all_nodes = self.get_all_nodes(graph_id)
        node_map = {n.uuid: n for n in all_nodes}
        result.all_nodes = all_nodes
        result.total_nodes = len(all_nodes)

        # Get all edges (with temporal info)
        all_edges = self.get_all_edges(graph_id, include_temporal=True)
        result.all_edges = all_edges
        result.total_edges = len(all_edges)
        
        # Classify facts as active vs. historical
        active_facts = []
        historical_facts = []
        
        for edge in all_edges:
            if not edge.fact:
                continue
            
            # Add entity names for context
            source_name = node_map.get(edge.source_node_uuid, NodeInfo('', '', [], '', {})).name or edge.source_node_uuid[:8]
            target_name = node_map.get(edge.target_node_uuid, NodeInfo('', '', [], '', {})).name or edge.target_node_uuid[:8]
            
            # Check if expired or invalidated
            is_historical = edge.is_expired or edge.is_invalid
            
            if is_historical:
                # Historical fact, add time range
                valid_at = edge.valid_at or "unknown"
                invalid_at = edge.invalid_at or edge.expired_at or "unknown"
                fact_with_time = f"[{valid_at} - {invalid_at}] {edge.fact}"
                historical_facts.append(fact_with_time)
            else:
                # Active fact
                active_facts.append(edge.fact)
        
        # Sort by query relevance
        query_lower = query.lower()
        keywords = [w.strip() for w in query_lower.replace(',', ' ').replace(', ', ' ').split() if len(w.strip()) > 1]
        
        def relevance_score(fact: str) -> int:
            fact_lower = fact.lower()
            score = 0
            if query_lower in fact_lower:
                score += 100
            for kw in keywords:
                if kw in fact_lower:
                    score += 10
            return score
        
        # Sort by relevance score
        active_facts.sort(key=relevance_score, reverse=True)
        historical_facts.sort(key=relevance_score, reverse=True)
        
        result.active_facts = active_facts[:limit]
        result.historical_facts = historical_facts[:limit] if include_expired else []
        result.active_count = len(active_facts)
        result.historical_count = len(historical_facts)
        
        logger.info(f"PanoramaSearch complete: {result.active_count} active, {result.historical_count} historical facts")
        return result
    
    def quick_search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10
    ) -> SearchResult:
        """
        [QuickSearch - Fast Search]

        Lightweight, fast search tool:
        1. Calls Zep semantic search
        2. Returns results directly
        3. Suitable for simple, targeted queries

        Args:
            graph_id: Graph ID
            query: Search query
            limit: Maximum number of results to return

        Returns:
            SearchResult: Search results
        """
        logger.info(f"QuickSearch: {query[:50]}...")

        # Call the search_graph method
        result = self.search_graph(
            graph_id=graph_id,
            query=query,
            limit=limit,
            scope="edges"
        )
        
        logger.info(f"QuickSearch complete: {result.total_count} results")
        return result
    
    def interview_agents(
        self,
        simulation_id: str,
        interview_requirement: str,
        simulation_requirement: str = "",
        max_agents: int = 5,
        custom_questions: List[str] = None
    ) -> InterviewResult:
        """
        [InterviewAgents - Agent Interview]

        Calls OASIS interview API to interview simulation agents:
        1. Auto-reads persona files to get all simulation agents
        2. Uses LLM to analyze interview requirement and select agents
        3. Uses LLM to generate interview questions
        4. Calls /api/simulation/interview/batch for multi-platform interviews
        5. Aggregates interview results and generates a report

        [Prerequisite] Simulation environment must be running (OASIS environment not closed).

        [Use Cases]
        - Understanding agent roles and event perspectives
        - Gathering opinions and viewpoints
        - Getting simulation agent answers (via LLM simulation)

        Args:
            simulation_id: Simulation ID (for persona file lookup and API calls)
            interview_requirement: Interview requirement description
            simulation_requirement: Simulation requirement (optional)
            max_agents: Maximum number of agents to interview
            custom_questions: Custom interview questions (optional; auto-generated if not provided)

        Returns:
            InterviewResult: Interview results
        """
        from.simulation_runner import SimulationRunner
        
        logger.info(f"InterviewAgents starting (multi-platform API): {interview_requirement[:50]}...")
        
        result = InterviewResult(
            interview_topic=interview_requirement,
            interview_questions=custom_questions or []
        )
        
        # Step 1: Load agent persona files
        profiles = self._load_agent_profiles(simulation_id)
        
        if not profiles:
            logger.warning(f"No persona files found for simulation {simulation_id}")
            result.summary = "No agent persona files found for interview"
            return result
        
        result.total_agents = len(profiles)
        logger.info(f"Loaded {len(profiles)} agent personas")

        # Step 2: Use LLM to select agents for interview (returns agent_id list)
        selected_agents, selected_indices, selection_reasoning = self._select_agents_for_interview(
            profiles=profiles,
            interview_requirement=interview_requirement,
            simulation_requirement=simulation_requirement,
            max_agents=max_agents
        )
        
        result.selected_agents = selected_agents
        result.selection_reasoning = selection_reasoning
        logger.info(f"Selected {len(selected_agents)} agents for interview: {selected_indices}")

        # Step 3: Generate interview questions (if not provided)
        if not result.interview_questions:
            result.interview_questions = self._generate_interview_questions(
                interview_requirement=interview_requirement,
                simulation_requirement=simulation_requirement,
                selected_agents=selected_agents
            )
            logger.info(f"Generated {len(result.interview_questions)} interview questions")

        # Merge interview questions into a single prompt
        combined_prompt = "\n".join([f"{i+1}. {q}" for i, q in enumerate(result.interview_questions)])
        
        # Add prompt prefix to guide Agent reply format
        INTERVIEW_PROMPT_PREFIX = (
            "You are being interviewed. Please respond in character, based on your persona and all past actions. "
            "Answer in plain text.\n"
            "Reply rules:\n"
            "1. Answer directly, do not call any tools\n"
            "2. Do not return JSON format or tool call format\n"
            "3. Do not use Markdown headings (#, ##, ###)\n"
            "4. Answer in sequence, prefix each answer with 'Answer X:' (where X is the question number)\n"
            "5. Put each answer on a new line\n"
            "6. Give substantive answers, 2-3 sentences each\n\n"
        )
        optimized_prompt = f"{INTERVIEW_PROMPT_PREFIX}{combined_prompt}"
        
        # Step 4: Call interview API (multi-platform, interviews on all available platforms)
        try:
            # Build interview request list (multi-platform, interview on all platforms)
            interviews_request = []
            for agent_idx in selected_indices:
                interviews_request.append({
                    "agent_id": agent_idx,
                    "prompt": optimized_prompt  # Optimized prompt
                    # Multi-platform: API interviews on both twitter and reddit platforms
                })
            
            logger.info(f"Calling interview API (multi-platform): {len(interviews_request)} agents")
            
            # Call SimulationRunner interview method (per platform)
            api_result = SimulationRunner.interview_agents_batch(
                simulation_id=simulation_id,
                interviews=interviews_request,
                platform=None,   # Multi-platform: interview on all platforms
                timeout=180.0    # Multi-platform timeout
            )
            
            logger.info(f"Interview API returned: {api_result.get('interviews_count', 0)} results, success={api_result.get('success')}")

            # Check if API call was successful
            if not api_result.get("success", False):
                error_msg = api_result.get("error", "unknown error")
                logger.warning(f"Interview API returned failure: {error_msg}")
                result.summary = f"Interview API call failed: {error_msg}. Please check OASIS simulation environment status."
                return result
            
            # Step 5: Parse API results, build AgentInterview objects
            # Multi-platform mode return format: {"twitter_0": {...}, "reddit_0": {...}, "twitter_1": {...},...}
            api_data = api_result.get("result", {})
            results_dict = api_data.get("results", {}) if isinstance(api_data, dict) else {}
            
            for i, agent_idx in enumerate(selected_indices):
                agent = selected_agents[i]
                agent_name = agent.get("realname", agent.get("username", f"Agent_{agent_idx}"))
                agent_role = agent.get("profession", "unknown")
                agent_bio = agent.get("bio", "")
                
                # Get agent's multi-platform interview results
                twitter_result = results_dict.get(f"twitter_{agent_idx}", {})
                reddit_result = results_dict.get(f"reddit_{agent_idx}", {})
                
                twitter_response = twitter_result.get("response", "")
                reddit_response = reddit_result.get("response", "")

                # Clean up tool-call JSON from responses
                twitter_response = self._clean_tool_call_response(twitter_response)
                reddit_response = self._clean_tool_call_response(reddit_response)

                # Output both platform responses
                twitter_text = twitter_response if twitter_response else "(no response from this platform)"
                reddit_text = reddit_response if reddit_response else "(no response from this platform)"
                response_text = f"[Twitter Platform Response]\n{twitter_text}\n\n[Reddit Platform Response]\n{reddit_text}"

                # Extract key quotes (from both platform responses)
                import re
                combined_responses = f"{twitter_response} {reddit_response}"

                # Clean up text: remove tool calls, Markdown formatting, etc.
                clean_text = re.sub(r'#{1,6}\s+', '', combined_responses)
                clean_text = re.sub(r'\{[^}]*tool_name[^}]*\}', '', clean_text)
                clean_text = re.sub(r'[*_`|>~\-]{2,}', '', clean_text)
                clean_text = re.sub(r' \d+[::]\s*', '', clean_text)
                clean_text = re.sub(r'[[^]]+]', '', clean_text)

                # Strategy 1 (sentence extraction): find meaningful complete sentences
                sentences = re.split(r'[.!?]', clean_text)
                meaningful = [
                    s.strip() for s in sentences
                    if 20 <= len(s.strip()) <= 150
                    and not re.match(r'^[\s\W,,;;::,]+', s.strip())
                    and not s.strip().startswith(('{', ' '))
                ]
                meaningful.sort(key=len, reverse=True)
                key_quotes = [s + "." for s in meaningful[:3]]

                # Strategy 2 (quoted text): extract text in quotation marks
                if not key_quotes:
                    paired = re.findall(r'\u201c([^\u201c\u201d]{15,100})\u201d', clean_text)
                    paired += re.findall(r'\u300c([^\u300c\u300d]{15,100})\u300d', clean_text)
                    key_quotes = [q for q in paired if not re.match(r'^[,,;;::,]', q)][:3]
                
                interview = AgentInterview(
                    agent_name=agent_name,
                    agent_role=agent_role,
                    agent_bio=agent_bio[:1000],  # Limit bio length
                    question=combined_prompt,
                    response=response_text,
                    key_quotes=key_quotes[:5]
                )
                result.interviews.append(interview)
            
            result.interviewed_count = len(result.interviews)
            
        except ValueError as e:
            # Simulation environment not yet running
            logger.warning(f"Interview API call failed (environment not running?): {e}")
            result.summary = f"Interview failed: {str(e)}. Simulation environment may be closed; please ensure the OASIS environment is running."
            return result
        except Exception as e:
            logger.error(f"Interview API call error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            result.summary = "Interview encountered an unexpected error"
            return result
        
        # Step 6: Generate interview summary
        if result.interviews:
            result.summary = self._generate_interview_summary(
                interviews=result.interviews,
                interview_requirement=interview_requirement
            )
        
        logger.info(f"InterviewAgents complete: interviewed {result.interviewed_count} agents (multi-platform)")
        return result
    
    @staticmethod
    def _clean_tool_call_response(response: str) -> str:
        """Clean up agent reply by extracting content from JSON tool-call wrappers."""
        if not response or not response.strip().startswith('{'):
            return response
        text = response.strip()
        if 'tool_name' not in text[:80]:
            return response
        import re as _re
        try:
            data = json.loads(text)
            if isinstance(data, dict) and 'arguments' in data:
                for key in ('content', 'text', 'body', 'message', 'reply'):
                    if key in data['arguments']:
                        return str(data['arguments'][key])
        except (json.JSONDecodeError, KeyError, TypeError):
            match = _re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
            if match:
                return match.group(1).replace('\\n', '\n').replace('\\"', '"')
        return response

    def _load_agent_profiles(self, simulation_id: str) -> List[Dict[str, Any]]:
        """Load simulation agent persona files."""
        import os
        import csv
        
        # Build persona file path
        sim_dir = os.path.join(
            os.path.dirname(__file__), 
            f'../../uploads/simulations/{simulation_id}'
        )
        
        profiles = []
        
        # Read Reddit JSON format
        reddit_profile_path = os.path.join(sim_dir, "reddit_profiles.json")
        if os.path.exists(reddit_profile_path):
            try:
                with open(reddit_profile_path, 'r', encoding='utf-8') as f:
                    profiles = json.load(f)
                logger.info(f"Loaded {len(profiles)} personas from reddit_profiles.json")
                return profiles
            except Exception as e:
                logger.warning(f"Failed to read reddit_profiles.json: {e}")
        
        # Read Twitter CSV format
        twitter_profile_path = os.path.join(sim_dir, "twitter_profiles.csv")
        if os.path.exists(twitter_profile_path):
            try:
                with open(twitter_profile_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Convert CSV format to dict
                        profiles.append({
                            "realname": row.get("name", ""),
                            "username": row.get("username", ""),
                            "bio": row.get("description", ""),
                            "persona": row.get("user_char", ""),
                            "profession": "unknown"
                        })
                logger.info(f"Loaded {len(profiles)} personas from twitter_profiles.csv")
                return profiles
            except Exception as e:
                logger.warning(f"Failed to read twitter_profiles.csv: {e}")
        
        return profiles
    
    def _select_agents_for_interview(
        self,
        profiles: List[Dict[str, Any]],
        interview_requirement: str,
        simulation_requirement: str,
        max_agents: int
    ) -> tuple:
        """
        Use LLM to select agents for interview.

        Returns:
            tuple: (selected_agents, selected_indices, reasoning)
                - selected_agents: List of complete agent info dicts
                - selected_indices: List of agent indices (for API calls)
                - reasoning: Selection rationale string
        """
        
        # Build agent summary list
        agent_summaries = []
        for i, profile in enumerate(profiles):
            summary = {
                "index": i,
                "name": profile.get("realname", profile.get("username", f"Agent_{i}")),
                "profession": profile.get("profession", "unknown"),
                "bio": profile.get("bio", "")[:200],
                "interested_topics": profile.get("interested_topics", [])
            }
            agent_summaries.append(summary)
        
        system_prompt = """You are a professional interview planning expert. Your task is to select the most suitable interview subjects from the simulation agent list based on interview requirements.

Selection criteria:
1. The agent's identity/occupation is relevant to the interview topic
2. The agent may hold unique or valuable perspectives
3. Select diverse viewpoints (e.g., supporters, opponents, neutral parties, professionals, etc.)
4. Prioritize agents directly related to the event

Return JSON format:
{
    "selected_indices": [list of selected agent indices],
    "reasoning": "explanation of selection rationale"
}"""

        user_prompt = f"""Interview requirements:
{interview_requirement}

Simulation background:
{simulation_requirement if simulation_requirement else "Not provided"}

Available agent list ({len(agent_summaries)} agents):
{json.dumps(agent_summaries, ensure_ascii=False, indent=2)}

Please select up to {max_agents} agents most suitable for interviewing, and explain your selection rationale."""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            selected_indices = response.get("selected_indices", [])[:max_agents]
            reasoning = response.get("reasoning", "Automatically selected based on relevance")
            
            # Get complete agent info
            selected_agents = []
            valid_indices = []
            for idx in selected_indices:
                if 0 <= idx < len(profiles):
                    selected_agents.append(profiles[idx])
                    valid_indices.append(idx)
            
            return selected_agents, valid_indices, reasoning
            
        except Exception as e:
            logger.warning(f"LLM agent selection failed, using default selection: {e}")
            # Fallback: select the first N agents
            selected = profiles[:max_agents]
            indices = list(range(min(max_agents, len(profiles))))
            return selected, indices, "Default selection (first N agents)"
    
    def _generate_interview_questions(
        self,
        interview_requirement: str,
        simulation_requirement: str,
        selected_agents: List[Dict[str, Any]]
    ) -> List[str]:
        """Use LLM to generate interview questions."""

        agent_roles = [a.get("profession", "unknown") for a in selected_agents]

        system_prompt = """You are a professional interviewer. Based on interview requirements, generate 3-5 interview questions.

Requirements:
1. Questions should be open-ended and encourage detailed answers
2. Questions should be relevant to the interviewee's role
3. Questions should cover opinions, perspectives, and insights
4. Questions should be suitable for the interview context
5. Each question should be under 50 words
6. Questions should be neutral and not leading

Return JSON format: {"questions": ["Question 1", "Question 2",...]}"""

        user_prompt = f"""Interview requirement: {interview_requirement}

Simulation background: {simulation_requirement if simulation_requirement else "Not provided"}

Interviewee roles: {', '.join(agent_roles)}

Please generate 3-5 interview questions."""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5
            )
            
            return response.get("questions", [f"Regarding {interview_requirement}, what is your perspective?"])

        except Exception as e:
            logger.warning(f"Failed to generate interview questions: {e}")
            return [
                f"Regarding {interview_requirement}, what is your opinion?",
                "How does this affect your group or community?",
                "What outcome do you expect?"
            ]
    
    def _generate_interview_summary(
        self,
        interviews: List[AgentInterview],
        interview_requirement: str
    ) -> str:
        """Generate interview summary."""

        if not interviews:
            return "No interviews completed"

        # Collect all interview content
        interview_texts = []
        for interview in interviews:
            interview_texts.append(f"[{interview.agent_name}({interview.agent_role})]\n{interview.response[:500]}")
        
        system_prompt = """You are a professional journalist. Based on the interview responses, generate an interview summary.

Summary requirements:
1. Highlight the main opinions expressed
2. Note areas of agreement and disagreement
3. Identify key insights
4. Be concise and well-organized
5. Keep it under 1000 words

Format requirements:
- Use plain text with paragraph breaks
- Do not use Markdown headings (#, ##, ###)
- Do not use horizontal rules (---, ***)
- Use quotation marks "" for direct quotes
- Use **Bold** sparingly, do not use other Markdown formatting"""

        user_prompt = f"""Interview topic: {interview_requirement}

Interview content:
{"".join(interview_texts)}

Please generate an interview summary."""

        try:
            summary = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            return summary
            
        except Exception as e:
            logger.warning(f"Failed to generate interview summary: {e}")
            # Fallback: return a simple concatenated summary
            return f"Interviewed {len(interviews)} agents, including: " + ", ".join([i.agent_name for i in interviews])
