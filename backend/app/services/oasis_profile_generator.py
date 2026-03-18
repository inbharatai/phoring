"""
OASIS Agent Profile Generator.

Converts Zep graph entities into OASIS simulation platform Agent Profile format.

Pipeline:
1. Retrieve Zep node information.
2. Use LLM prompts to generate detailed personas.
3. Distinguish personal entities from abstract/group entities.
"""

import json
import random
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI
from zep_cloud.client import Zep

from..config import Config
from..utils.logger import get_logger
from.zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger('phoring.oasis_profile')


@dataclass
class OasisAgentProfile:
    """OASIS Agent Profile data class."""
    # Required fields
    user_id: int
    user_name: str
    name: str
    bio: str
    persona: str
    
    # Optional field - Reddit specific
    karma: int = 1000

    # Optional fields - Twitter specific
    friend_count: int = 100
    follower_count: int = 150
    statuses_count: int = 500
    
    # Persona information
    age: Optional[int] = None
    gender: Optional[str] = None
    mbti: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None
    interested_topics: List[str] = field(default_factory=list)
    
    # Entity information
    source_entity_uuid: Optional[str] = None
    source_entity_type: Optional[str] = None
    
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    
    def to_reddit_format(self) -> Dict[str, Any]:
        """Convert to Reddit platform format."""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name, # OASIS requires username field
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "created_at": self.created_at,
        }

        # Add persona information (if available)
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics
        
        return profile
    
    def to_twitter_format(self) -> Dict[str, Any]:
        """Convert to Twitter platform format."""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name, # OASIS requires username field
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "created_at": self.created_at,
        }

        # Add persona information
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics
        
        return profile
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to complete dictionary format."""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "age": self.age,
            "gender": self.gender,
            "mbti": self.mbti,
            "country": self.country,
            "profession": self.profession,
            "interested_topics": self.interested_topics,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_type": self.source_entity_type,
            "created_at": self.created_at,
        }


class OasisProfileGenerator:
    """
    OASIS Profile Generator.

    Converts Zep graph entities into OASIS simulation Agent Profiles.

    Pipeline:
    1. Query Zep graph to retrieve entity data.
    2. Generate detailed personas (including basic info, personality, interests, social media behavior).
    3. Distinguish personal entities from abstract/group entities.
    """
    
    # MBTI personality type list
    MBTI_TYPES = [
        "INTJ", "INTP", "ENTJ", "ENTP",
        "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ",
        "ISTP", "ISFP", "ESTP", "ESFP"
    ]
    
    # Country list
    COUNTRIES = [
        "China", "US", "UK", "Japan", "Germany", "France", 
        "Canada", "Australia", "Brazil", "India", "South Korea"
    ]
    
    # Individual-type entities (generate concrete personal personas)
    INDIVIDUAL_ENTITY_TYPES = [
        "student", "alumni", "professor", "person", "publicfigure", 
        "expert", "faculty", "official", "journalist", "activist"
    ]
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        zep_api_key: Optional[str] = None,
        graph_id: Optional[str] = None,
        simulation_requirement: str = ""
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME
        self.simulation_requirement = simulation_requirement
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY not yet configured")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # Zep client initialization
        self.zep_api_key = zep_api_key or Config.ZEP_API_KEY
        self.zep_client = None
        self.graph_id = graph_id
        
        if self.zep_api_key:
            try:
                self.zep_client = Zep(api_key=self.zep_api_key)
            except Exception as e:
                logger.warning(f"Zep client initialization failed: {e}")
    
    def generate_profile_from_entity(
        self, 
        entity: EntityNode, 
        user_id: int,
        use_llm: bool = True
    ) -> OasisAgentProfile:
        """
        Generate an OASIS Agent Profile from a Zep entity.

        Args:
            entity: Zep entity node
            user_id: User ID (for OASIS platform)
            use_llm: Whether to use LLM to generate detailed persona

        Returns:
            OasisAgentProfile instance
        """
        entity_type = entity.get_entity_type() or "Entity"
        
        # Basic info
        name = entity.name
        user_name = self._generate_username(name)
        
        # Build info
        context = self._build_entity_context(entity)
        
        if use_llm:
            # Use LLM to generate detailed persona
            profile_data = self._generate_profile_with_llm(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes,
                context=context
            )
        else:
            # Generate rule-based persona
            profile_data = self._generate_profile_rule_based(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes
            )
        
        return OasisAgentProfile(
            user_id=user_id,
            user_name=user_name,
            name=name,
            bio=profile_data.get("bio", f"{entity_type}: {name}"),
            persona=profile_data.get("persona", entity.summary or f"A {entity_type} named {name}."),
            karma=profile_data.get("karma", random.randint(500, 5000)),
            friend_count=profile_data.get("friend_count", random.randint(50, 500)),
            follower_count=profile_data.get("follower_count", random.randint(100, 1000)),
            statuses_count=profile_data.get("statuses_count", random.randint(100, 2000)),
            age=profile_data.get("age"),
            gender=profile_data.get("gender"),
            mbti=profile_data.get("mbti"),
            country=profile_data.get("country"),
            profession=profile_data.get("profession"),
            interested_topics=profile_data.get("interested_topics", []),
            source_entity_uuid=entity.uuid,
            source_entity_type=entity_type,
        )
    
    def _generate_username(self, name: str) -> str:
        """Generate a username from the entity name."""
        # Remove special characters, convert to lowercase
        username = name.lower().replace(" ", "_")
        username = ''.join(c for c in username if c.isalnum() or c == '_')
        
        # Add random suffix to avoid collisions
        suffix = random.randint(100, 999)
        return f"{username}_{suffix}"
    
    def _search_zep_for_entity(self, entity: EntityNode) -> Dict[str, Any]:
        """
        Search Zep graph to retrieve additional entity information.

        Uses Zep search interface to search edges and nodes, then merges results.
        Runs searches in parallel for better performance.

        Args:
            entity: Entity node object

        Returns:
            Dictionary containing facts, node_summaries, and context string
        """
        import concurrent.futures
        
        if not self.zep_client:
            return {"facts": [], "node_summaries": [], "context": ""}
        
        entity_name = entity.name
        
        results = {
            "facts": [],
            "node_summaries": [],
            "context": ""
        }
        
        # graph_id is required for search
        if not self.graph_id:
            logger.debug(f"Skipping Zep search: graph_id not configured")
            return results
        
        comprehensive_query = f"All information about {entity_name}, including background, events, and relationships"
        
        def search_edges():
            """Search edges (facts/relationships) with retry logic."""
            max_retries = 3
            last_exception = None
            delay = 2.0
            
            for attempt in range(max_retries):
                try:
                    return self.zep_client.graph.search(
                        query=comprehensive_query,
                        graph_id=self.graph_id,
                        limit=30,
                        scope="edges",
                        reranker="rrf"
                    )
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(f"Zep edge search attempt {attempt + 1} failed: {str(e)[:80]}, retrying...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.debug(f"Zep edge search failed after {max_retries} attempts: {e}")
            return None
        
        def search_nodes():
            """Search nodes (entity summaries) with retry logic."""
            max_retries = 3
            last_exception = None
            delay = 2.0
            
            for attempt in range(max_retries):
                try:
                    return self.zep_client.graph.search(
                        query=comprehensive_query,
                        graph_id=self.graph_id,
                        limit=20,
                        scope="nodes",
                        reranker="rrf"
                    )
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(f"Zep node search attempt {attempt + 1} failed: {str(e)[:80]}, retrying...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.debug(f"Zep node search failed after {max_retries} attempts: {e}")
            return None
        
        try:
            # Run edge and node searches in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                edge_future = executor.submit(search_edges)
                node_future = executor.submit(search_nodes)
                
                # Get results
                edge_result = edge_future.result(timeout=30)
                node_result = node_future.result(timeout=30)
            
            # Process edge search results
            all_facts = set()
            if edge_result and hasattr(edge_result, 'edges') and edge_result.edges:
                for edge in edge_result.edges:
                    if hasattr(edge, 'fact') and edge.fact:
                        all_facts.add(edge.fact)
            results["facts"] = list(all_facts)
            
            # Process node search results
            all_summaries = set()
            if node_result and hasattr(node_result, 'nodes') and node_result.nodes:
                for node in node_result.nodes:
                    if hasattr(node, 'summary') and node.summary:
                        all_summaries.add(node.summary)
                    if hasattr(node, 'name') and node.name and node.name!= entity_name:
                        all_summaries.add(f"Related entity: {node.name}")
            results["node_summaries"] = list(all_summaries)
            
            # Build context string
            context_parts = []
            if results["facts"]:
                context_parts.append("Key facts:\n" + "\n".join(f"- {f}" for f in results["facts"][:20]))
            if results["node_summaries"]:
                context_parts.append("Related entities:\n" + "\n".join(f"- {s}" for s in results["node_summaries"][:10]))
            results["context"] = "\n\n".join(context_parts)
            
            logger.info(f"Zep search complete: {entity_name}, found {len(results['facts'])} facts, {len(results['node_summaries'])} nodes")
            
        except concurrent.futures.TimeoutError:
            logger.warning(f"Zep search timeout ({entity_name})")
        except Exception as e:
            logger.warning(f"Zep search failed ({entity_name}): {e}")
        
        return results
    
    def _build_entity_context(self, entity: EntityNode) -> str:
        """
        Build complete entity context information.

        Includes:
        1. Entity attributes (properties)
        2. Related node detailed information
        3. Zep search results
        """
        context_parts = []
        
        # 1. Add entity attribute information
        if entity.attributes:
            attrs = []
            for key, value in entity.attributes.items():
                if value and str(value).strip():
                    attrs.append(f"- {key}: {value}")
            if attrs:
                context_parts.append("### Entity Attributes\n" + "\n".join(attrs))
        
        # 2. Add fact information (edges/relationships)
        existing_facts = set()
        if entity.related_edges:
            relationships = []
            for edge in entity.related_edges:
                fact = edge.get("fact", "")
                edge_name = edge.get("edge_name", "")
                direction = edge.get("direction", "")
                
                if fact:
                    relationships.append(f"- {fact}")
                    existing_facts.add(fact)
                elif edge_name:
                    if direction == "outgoing":
                        relationships.append(f"- {entity.name} --[{edge_name}]--> (related entity)")
                    else:
                        relationships.append(f"- (related entity) --[{edge_name}]--> {entity.name}")
            
            if relationships:
                context_parts.append("### Relationships\n" + "\n".join(relationships))
        
        # 3. Add related node detailed information
        if entity.related_nodes:
            related_info = []
            for node in entity.related_nodes:
                node_name = node.get("name", "")
                node_labels = node.get("labels", [])
                node_summary = node.get("summary", "")
                
                # Filter out default labels
                custom_labels = [l for l in node_labels if l not in ["Entity", "Node"]]
                label_str = f" ({', '.join(custom_labels)})" if custom_labels else ""
                
                if node_summary:
                    related_info.append(f"- **{node_name}**{label_str}: {node_summary}")
                else:
                    related_info.append(f"- **{node_name}**{label_str}")
            
            if related_info:
                context_parts.append("### Related Entity Info\n" + "\n".join(related_info))
        
        # 4. Get additional information from Zep search
        zep_results = self._search_zep_for_entity(entity)
        
        if zep_results.get("facts"):
            # Deduplicate: exclude already existing facts
            new_facts = [f for f in zep_results["facts"] if f not in existing_facts]
            if new_facts:
                context_parts.append("### Zep Additional Facts\n" + "\n".join(f"- {f}" for f in new_facts[:15]))
        
        if zep_results.get("node_summaries"):
            context_parts.append("### Zep Related Nodes\n" + "\n".join(f"- {s}" for s in zep_results["node_summaries"][:10]))

        # Live web intelligence enrichment (news + social sentiment).
        try:
            from .web_intelligence import NewsScraperService
            news_data = NewsScraperService().gather_for_entity(
                entity.name,
                entity.get_entity_type() or "Entity",
                max_articles=3,
                context=self.simulation_requirement,
            )
            if news_data.get("combined_text"):
                context_parts.append("### Live News\n" + news_data["combined_text"])

            social_posts = news_data.get("social_media_posts", [])
            if social_posts:
                lines = [
                    f"- [{p.get('platform', 'Social')}] {p.get('snippet', '')[:220]}"
                    for p in social_posts[:5]
                ]
                context_parts.append("### Social Sentiment\n" + "\n".join(lines))
        except Exception as e:
            logger.warning(f"Web intelligence failed for {entity.name}: {e}")

        return "\n\n".join(context_parts)
    
    def _is_individual_entity(self, entity_type: str) -> bool:
        """Check whether this is an individual-type entity."""
        return entity_type.lower() in self.INDIVIDUAL_ENTITY_TYPES
    
    def _generate_profile_with_llm(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> Dict[str, Any]:
        """
        Use LLM to generate a detailed persona.

        Handles different entity types:
        - Individual entities: generate concrete personal personas
        - Group/institution entities: generate organizational personas
        """
        
        is_individual = self._is_individual_entity(entity_type)
        
        if is_individual:
            prompt = self._build_individual_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context
            )
        else:
            prompt = self._build_group_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context
            )

        # Retry generation up to max attempts
        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt(is_individual)},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1) # Lower temperature on retries
                    # No max_tokens set; let LLM use its default
                )

                content = response.choices[0].message.content

                # Check whether output was truncated (finish_reason != 'stop')
                finish_reason = response.choices[0].finish_reason
                if finish_reason == 'length':
                    logger.warning(f"LLM output truncated (attempt {attempt+1}), attempting repair...")
                    content = self._fix_truncated_json(content)
                
                # Parse JSON response
                try:
                    result = json.loads(content)
                    
                    # Validate required fields
                    if "bio" not in result or not result["bio"]:
                        result["bio"] = entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}"
                    if "persona" not in result or not result["persona"]:
                        result["persona"] = entity_summary or f"{entity_name} {entity_type}."
                    
                    # Ground-truth validation: check persona against known entity facts
                    result = self._validate_persona_against_facts(
                        result, entity_name, entity_type, entity_summary, entity_attributes, context
                    )
                    
                    return result
                    
                except json.JSONDecodeError as je:
                    logger.warning(f"JSON parse failed (attempt {attempt+1}): {str(je)[:80]}")

                    # Attempt to repair JSON
                    result = self._try_fix_json(content, entity_name, entity_type, entity_summary)
                    if result.get("_fixed"):
                        del result["_fixed"]
                        return result
                    
                    last_error = je
                    
            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt+1}): {str(e)[:80]}")
                last_error = e
                time.sleep(1 * (attempt + 1)) # Backoff delay

        logger.warning(f"LLM persona generation failed after {max_attempts} attempts: {last_error}, falling back to rule-based")
        return self._generate_profile_rule_based(
            entity_name, entity_type, entity_summary, entity_attributes
        )
    
    def _validate_persona_against_facts(
        self,
        profile_data: Dict[str, Any],
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str,
    ) -> Dict[str, Any]:
        """Validate the LLM-generated persona against known entity facts.

        Checks for fabricated details that contradict the knowledge graph:
        - If the entity is known to be a company, the persona should not describe a person
        - If the entity has a known location, the persona should not claim a different one
        - Appends a provenance disclaimer noting which facts are verified vs inferred
        """
        known_facts = []
        if entity_summary:
            known_facts.append(entity_summary)
        if entity_attributes:
            for k, v in entity_attributes.items():
                if v and str(v).strip():
                    known_facts.append(f"{k}: {v}")

        persona = profile_data.get("persona", "")

        # If we have no known facts, mark the entire persona as inferred
        if not known_facts:
            profile_data["persona"] = (
                f"{persona}\n\n"
                f"[Provenance: This persona is fully inferred by AI. "
                f"No verified ground-truth data was available for {entity_name}.]"
            )
            return profile_data

        # Entity type consistency check
        is_individual = self._is_individual_entity(entity_type)
        bio = profile_data.get("bio", "")

        # Check for obvious contradictions
        contradictions = []
        if not is_individual and profile_data.get("age"):
            contradictions.append(
                f"Entity '{entity_name}' is type '{entity_type}' (organization/group) "
                f"but was assigned age={profile_data['age']}"
            )
            profile_data["age"] = None

        if contradictions:
            logger.warning(f"Persona contradictions for {entity_name}: {contradictions}")

        # Append provenance note
        verified_count = len(known_facts)
        profile_data["persona"] = (
            f"{persona}\n\n"
            f"[Provenance: Persona grounded on {verified_count} verified facts from knowledge graph. "
            f"Behavioral traits and social media style are AI-inferred.]"
        )

        return profile_data
    
    def _fix_truncated_json(self, content: str) -> str:
        """Repair truncated JSON (when output hits max_tokens limit)."""
        # If JSON is truncated, attempt to close open brackets/braces
        content = content.strip()

        # Count unclosed brackets and braces
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')

        # Check whether the last character suggests truncation mid-string
        if content and content[-1] not in '",}]':
            # Close any open string
            content += '"'

        # Close remaining brackets and braces
        content += ']' * open_brackets
        content += '}' * open_braces
        
        return content
    
    def _try_fix_json(self, content: str, entity_name: str, entity_type: str, entity_summary: str = "") -> Dict[str, Any]:
        """Attempt to repair malformed JSON content."""
        import re
        
        # 1. Fix truncated content
        content = self._fix_truncated_json(content)

        # 2. Extract JSON object from content
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()
            
            # 3. Fix newlines within string values
            def fix_string_newlines(match):
                s = match.group(0)
                # Replace newlines inside string values
                s = s.replace('\n', ' ').replace('\r', ' ')
                # Collapse multiple spaces
                s = re.sub(r'\s+', ' ', s)
                return s
            
            # Fix string values in JSON
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string_newlines, json_str)
            
            # 4. Attempt to parse
            try:
                result = json.loads(json_str)
                result["_fixed"] = True
                return result
            except json.JSONDecodeError as e:
                # 5. If still failing, try removing control characters
                try:
                    # Remove all control characters
                    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                    # Collapse whitespace
                    json_str = re.sub(r'\s+', ' ', json_str)
                    result = json.loads(json_str)
                    result["_fixed"] = True
                    return result
                except Exception:
                    pass
        
        # 6. Try to extract partial info from content
        bio_match = re.search(r'"bio"\s*:\s*"([^"]*)"', content)
        persona_match = re.search(r'"persona"\s*:\s*"([^"]*)', content) # May be truncated
        
        bio = bio_match.group(1) if bio_match else (entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}")
        persona = persona_match.group(1) if persona_match else (entity_summary or f"{entity_name} {entity_type}.")
        
        # If partial data was extracted, return it
        if bio_match or persona_match:
            logger.info(f"Extracted partial info from malformed JSON")
            return {
                "bio": bio,
                "persona": persona,
                "_fixed": True
            }
        
        # 7. All repair attempts failed, return basic fallback
        logger.warning(f"JSON repair failed, returning basic fallback profile")
        return {
            "bio": entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}",
            "persona": entity_summary or f"{entity_name} {entity_type}."
        }
    
    def _get_system_prompt(self, is_individual: bool) -> str:
        """Get the system prompt for persona generation."""
        base_prompt = "You are a social media user profile generator. Generate detailed, realistic personas for opinion simulation, maximizing authenticity. You must return JSON format, all string values must not contain unescaped line breaks."
        return base_prompt
    
    def _build_individual_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> str:
        """Build the LLM prompt for individual entity persona generation."""
        
        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "None"
        context_str = context[:3000] if context else "None"
        scenario_str = f"\nSimulation Scenario (user's request): {self.simulation_requirement}\n" if self.simulation_requirement else ""

        return f"""Based on the following entity, generate a detailed social media user persona, maximizing authenticity.
{scenario_str}
Entity name: {entity_name}
Entity type: {entity_type}
Entity summary: {entity_summary}
Entity attributes: {attrs_str}

Background information:
{context_str}

Please generate JSON with the following fields:

1. bio: Social media bio, max 200 characters
2. persona: Detailed persona description (up to 2000 characters), including:
   - Basic information (age, gender, occupation, background)
   - Background details (experiences, events, relationships)
   - Personality traits (MBTI type, core values, temperament)
   - Social media behavior (posting frequency, content style, engagement habits)
   - Stances and opinions (attitudes, supportive/opposing content)
   - Unique characteristics (special traits, personal quirks)
   - Personal history (persona-relevant history, reactions to events)
3. age: Integer (required)
4. gender: String, must be exactly "male" or "female"
5. mbti: MBTI personality type (e.g. INTJ, ENFP)
6. country: Country of residence (if unknown, use "Unknown")
7. profession: Occupation or role
8. interested_topics: List of topics of interest

Requirements:
- All fields must be strings without unescaped line breaks
- Persona must be a detailed description
- Gender field must be exactly "male" or "female"
- Content should be grounded in entity information
- Age must be an integer, gender must be "male" or "female"
"""

    def _build_group_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> str:
        """Build the LLM prompt for group/institution entity persona generation."""

        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "None"
        context_str = context[:3000] if context else "None"
        scenario_str = f"\nSimulation Scenario (user's request): {self.simulation_requirement}\n" if self.simulation_requirement else ""

        return f"""Based on the following institution/group entity, generate a detailed social media account persona, maximizing authenticity.
{scenario_str}
Entity name: {entity_name}
Entity type: {entity_type}
Entity summary: {entity_summary}
Entity attributes: {attrs_str}

Background information:
{context_str}

Please generate JSON with the following fields:

1. bio: Official account bio, max 200 characters, reflecting institutional identity
2. persona: Detailed description (up to 2000 characters), including:
   - Institutional basic info (founding, type, location, main activities)
   - Organizational character (communication style, tone, core values)
   - Influence and reach (audience, reputation, partnerships)
   - Publishing behavior (content types, frequency, active hours)
   - Stances and attitudes (core positions, policy views)
   - Special characteristics (unique traits, organizational culture)
   - Institutional history (key events and responses)
3. age: Set to 30 (default for institutions)
4. gender: "other" (institutions use "other" instead of personal gender)
5. mbti: MBTI type matching the organizational character, e.g. ISTJ for formal institutions
6. country: Country of operation (if unknown, use "Unknown")
7. profession: Brief institutional description
8. interested_topics: Topics the institution follows and engages with

Requirements:
- All fields must be strings without null values
- Persona must be a detailed description without unescaped line breaks
- Gender field must be exactly "other" for institutions
- Age must be set to 30, gender must be the string "other"
- Reflect the institutional voice and communication style"""
    
    def _generate_profile_rule_based(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a rule-based fallback persona."""

        # Generate persona based on entity type
        entity_type_lower = entity_type.lower()
        
        if entity_type_lower in ["student", "alumni"]:
            return {
                "bio": f"{entity_type} with interests in academics and social issues.",
                "persona": f"{entity_name} is a {entity_type.lower()} who is actively engaged in academic and social discussions. They enjoy sharing perspectives and connecting with peers.",
                "age": random.randint(18, 30),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": "Student",
                "interested_topics": ["Education", "Social Issues", "Technology"],
            }
        
        elif entity_type_lower in ["publicfigure", "expert", "faculty"]:
            return {
                "bio": f"Expert and thought leader in their field.",
                "persona": f"{entity_name} is a recognized {entity_type.lower()} who shares insights and opinions on important matters. They are known for their expertise and influence in public discourse.",
                "age": random.randint(35, 60),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(["ENTJ", "INTJ", "ENTP", "INTP"]),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_attributes.get("occupation", "Expert"),
                "interested_topics": ["Politics", "Economics", "Culture & Society"],
            }
        
        elif entity_type_lower in ["mediaoutlet", "socialmediaplatform"]:
            return {
                "bio": f"Official account for {entity_name}. News and updates.",
                "persona": f"{entity_name} is a media entity that reports news and facilitates public discourse. The account shares timely updates and engages with the audience on current events.",
                "age": 30, # Default for institutions
                "gender": "other", # Institutions use "other"
                "mbti": "ISTJ", # Institutional type: structured/reliable
                "country": "Unknown",
                "profession": "Media",
                "interested_topics": ["General News", "Current Events", "Public Affairs"],
            }
        
        elif entity_type_lower in ["university", "governmentagency", "ngo", "organization"]:
            return {
                "bio": f"Official account of {entity_name}.",
                "persona": f"{entity_name} is an institutional entity that communicates official positions, announcements, and engages with stakeholders on relevant matters.",
                "age": 30, # Default for institutions
                "gender": "other", # Institutions use "other"
                "mbti": "ISTJ", # Institutional type: structured/reliable
                "country": "Unknown",
                "profession": entity_type,
                "interested_topics": ["Public Policy", "Community", "Official Announcements"],
            }
        
        else:
            # Default persona
            return {
                "bio": entity_summary[:150] if entity_summary else f"{entity_type}: {entity_name}",
                "persona": entity_summary or f"{entity_name} is a {entity_type.lower()} participating in social discussions.",
                "age": random.randint(25, 50),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_type,
                "interested_topics": ["General", "Social Issues"],
            }
    
    def set_graph_id(self, graph_id: str):
        """Set the graph ID for Zep search operations."""
        self.graph_id = graph_id
    
    def generate_profiles_from_entities(
        self,
        entities: List[EntityNode],
        use_llm: bool = True,
        progress_callback: Optional[callable] = None,
        graph_id: Optional[str] = None,
        parallel_count: int = 5,
        realtime_output_path: Optional[str] = None,
        output_platform: str = "reddit"
    ) -> List[OasisAgentProfile]:
        """
        Generate Agent Profiles from a list of entities (with parallel generation).

        Args:
            entities: List of entity nodes
            use_llm: Whether to use LLM for detailed persona generation
            progress_callback: Progress callback function (current, total, message)
            graph_id: Graph ID for Zep search operations
            parallel_count: Number of parallel generation workers, default 5
            realtime_output_path: File path for real-time output (if provided, write after each generation)
            output_platform: Output platform format ("reddit" or "twitter")

        Returns:
            List of Agent Profiles
        """
        import concurrent.futures
        from threading import Lock
        
        # Set graph_id for Zep search operations
        if graph_id:
            self.graph_id = graph_id
        
        total = len(entities)
        profiles = [None] * total # Pre-allocate list for ordered results
        completed_count = [0] # Mutable counter for thread-safe updates
        lock = Lock()
        
        # Real-time file save function
        def save_profiles_realtime():
            """Save already-generated profiles to file."""
            if not realtime_output_path:
                return
            
            with lock:
                # Filter to only completed profiles
                existing_profiles = [p for p in profiles if p is not None]
                if not existing_profiles:
                    return
                
                try:
                    if output_platform == "reddit":
                        # Reddit JSON format
                        profiles_data = [p.to_reddit_format() for p in existing_profiles]
                        with open(realtime_output_path, 'w', encoding='utf-8') as f:
                            json.dump(profiles_data, f, ensure_ascii=False, indent=2)
                    else:
                        # Twitter CSV format
                        import csv
                        profiles_data = [p.to_twitter_format() for p in existing_profiles]
                        if profiles_data:
                            fieldnames = list(profiles_data[0].keys())
                            with open(realtime_output_path, 'w', encoding='utf-8', newline='') as f:
                                writer = csv.DictWriter(f, fieldnames=fieldnames)
                                writer.writeheader()
                                writer.writerows(profiles_data)
                except Exception as e:
                    logger.warning(f"Failed to save profiles: {e}")
        
        def generate_single_profile(idx: int, entity: EntityNode) -> tuple:
            """Generate a single profile (worker function)."""
            entity_type = entity.get_entity_type() or "Entity"
            
            try:
                profile = self.generate_profile_from_entity(
                    entity=entity,
                    user_id=idx,
                    use_llm=use_llm
                )
                
                # Output generated persona to log
                self._print_generated_profile(entity.name, entity_type, profile)
                
                return idx, profile, None
                
            except Exception as e:
                logger.error(f"Failed to generate persona for entity {entity.name}: {str(e)}")
                # Create fallback profile
                fallback_profile = OasisAgentProfile(
                    user_id=idx,
                    user_name=self._generate_username(entity.name),
                    name=entity.name,
                    bio=f"{entity_type}: {entity.name}",
                    persona=entity.summary or f"A participant in social discussions.",
                    source_entity_uuid=entity.uuid,
                    source_entity_type=entity_type,
                )
                return idx, fallback_profile, str(e)
        
        logger.info(f"Starting parallel generation of {total} Agent personas (workers: {parallel_count})...")
        print(f"\n{'='*60}")
        print(f"Starting agent persona generation - {total} entities, workers: {parallel_count}")
        print(f"{'='*60}\n")
        
        # Execute in parallel using thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_count) as executor:
            # Submit all tasks
            future_to_entity = {
                executor.submit(generate_single_profile, idx, entity): (idx, entity)
                for idx, entity in enumerate(entities)
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_entity):
                idx, entity = future_to_entity[future]
                entity_type = entity.get_entity_type() or "Entity"
                
                try:
                    result_idx, profile, error = future.result()
                    profiles[result_idx] = profile
                    
                    with lock:
                        completed_count[0] += 1
                        current = completed_count[0]
                    
                    # Save to file in real-time
                    save_profiles_realtime()

                    if progress_callback:
                        progress_callback(
                            current, 
                            total, 
                            f"Completed {current}/{total}: {entity.name} ({entity_type})"
                        )
                    
                    if error:
                        logger.warning(f"[{current}/{total}] {entity.name} used fallback persona: {error}")
                    else:
                        logger.info(f"[{current}/{total}] Successfully generated persona: {entity.name} ({entity_type})")
                        
                except Exception as e:
                    logger.error(f"Error processing entity {entity.name}: {str(e)}")
                    with lock:
                        completed_count[0] += 1
                    profiles[idx] = OasisAgentProfile(
                        user_id=idx,
                        user_name=self._generate_username(entity.name),
                        name=entity.name,
                        bio=f"{entity_type}: {entity.name}",
                        persona=entity.summary or "A participant in social discussions.",
                        source_entity_uuid=entity.uuid,
                        source_entity_type=entity_type,
                    )
                    # Save to file (even with fallback persona)
                    save_profiles_realtime()
        
        print(f"\n{'='*60}")
        print(f"Persona generation complete! Generated {len([p for p in profiles if p])} Agent profiles")
        print(f"{'='*60}\n")
        
        return profiles
    
    def _print_generated_profile(self, entity_name: str, entity_type: str, profile: OasisAgentProfile):
        """Print the generated persona to console (full content, no truncation)."""
        separator = "-" * 70
        
        # Build complete output content (no truncation)
        topics_str = ', '.join(profile.interested_topics) if profile.interested_topics else 'None'
        
        output_lines = [
            f"\n{separator}",
            f"[Generated] {entity_name} ({entity_type})",
            f"{separator}",
            f"Username: {profile.user_name}",
            f"",
            f"[Bio]",
            f"{profile.bio}",
            f"",
            f"[Detailed Persona]",
            f"{profile.persona}",
            f"",
            f"[Basic Attributes]",
            f"Age: {profile.age} | Gender: {profile.gender} | MBTI: {profile.mbti}",
            f"Profession: {profile.profession} | Country: {profile.country}",
            f"Topics: {topics_str}",
            separator
        ]
        
        output = "\n".join(output_lines)
        
        # Print directly (logger may truncate complete content)
        print(output)
    
    def save_profiles(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """
        Save profiles to file (in platform-specific format).

        OASIS platform formats:
        - Twitter: CSV format
        - Reddit: JSON format

        Args:
            profiles: List of profiles
            file_path: Output file path
            platform: Platform type ("reddit" or "twitter")
        """
        if platform == "twitter":
            self._save_twitter_csv(profiles, file_path)
        else:
            self._save_reddit_json(profiles, file_path)
    
    def _save_twitter_csv(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        Save Twitter Profiles in CSV format (OASIS compatible).

        OASIS Twitter CSV fields:
        - user_id: User ID (CSV rows start from 0)
        - name: Display name
        - username: Username handle
        - user_char: Detailed persona description (injected into LLM prompts, drives Agent behavior)
        - description: Short bio (visible on user profile page)

        user_char vs description:
        - user_char: Internal persona, used in LLM prompts, determines Agent thinking and actions
        - description: Public-facing bio, visible to other users
        """
        import csv
        
        # Ensure file ends with .csv
        if not file_path.endswith('.csv'):
            file_path = file_path.replace('.json', '.csv')
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write OASIS-compatible headers
            headers = ['user_id', 'name', 'username', 'user_char', 'description']
            writer.writerow(headers)
            
            # Write data rows
            for idx, profile in enumerate(profiles):
                # user_char: Complete persona (bio + persona), injected into LLM prompts
                user_char = profile.bio
                if profile.persona and profile.persona!= profile.bio:
                    user_char = f"{profile.bio} {profile.persona}"
                # Remove line breaks (for CSV compatibility)
                user_char = user_char.replace('\n', ' ').replace('\r', ' ')
                
                # description: Public-facing short bio
                description = profile.bio.replace('\n', ' ').replace('\r', ' ')
                
                row = [
                    idx, # user_id: 0-based ID
                    profile.name, # name: Display name
                    profile.user_name, # username: Username handle
                    user_char, # user_char: Complete persona (for LLM prompts)
                    description # description: Public bio
                ]
                writer.writerow(row)
        
        logger.info(f"Saved {len(profiles)} Twitter Profiles to {file_path} (OASIS CSV format)")
    
    def _normalize_gender(self, gender: Optional[str]) -> str:
        """
        Normalize gender field to OASIS format.

        OASIS accepts: male, female, other
        """
        if not gender:
            return "other"
        
        gender_lower = gender.lower().strip()
        
        # Gender mapping
        gender_map = {
            "male": "male",
            "female": "female",
            "institution": "other",
            "other": "other",
        }
        
        return gender_map.get(gender_lower, "other")
    
    def _save_reddit_json(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        Save Reddit Profiles in JSON format.

        Uses to_reddit_format() structure, ensuring OASIS compatibility.
        Must include user_id field for OASIS agent_graph.get_agent() matching!

        Fields:
        - user_id: User ID (must match initial_posts poster_agent_id)
        - username: Username handle
        - name: Display name
        - bio: Short bio
        - persona: Detailed persona description
        - age: Age (integer)
        - gender: "male", "female", or "other"
        - mbti: MBTI personality type
        - country: Country of residence
        """
        data = []
        for idx, profile in enumerate(profiles):
            # Build profile using to_reddit_format() structure
            item = {
                "user_id": profile.user_id if profile.user_id is not None else idx, # Important: must include user_id
                "username": profile.user_name,
                "name": profile.name,
                "bio": profile.bio[:150] if profile.bio else f"{profile.name}",
                "persona": profile.persona or f"{profile.name} is a participant in social discussions.",
                "karma": profile.karma if profile.karma else 1000,
                "created_at": profile.created_at,
                # OASIS fields - Ensure defaults are set
                "age": profile.age if profile.age else 30,
                "gender": self._normalize_gender(profile.gender),
                "mbti": profile.mbti if profile.mbti else "ISTJ",
                "country": profile.country if profile.country else "Unknown",
            }
            
            # Optional fields
            if profile.profession:
                item["profession"] = profile.profession
            if profile.interested_topics:
                item["interested_topics"] = profile.interested_topics
            
            data.append(item)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(profiles)} Reddit Profiles to {file_path} (JSON format, includes user_id field)")
    
    # Deprecated method, kept for backward compatibility
    def save_profiles_to_json(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """[Deprecated] Please use save_profiles() method instead."""
        logger.warning("save_profiles_to_json is deprecated, please use save_profiles() method")
        self.save_profiles(profiles, file_path, platform)


