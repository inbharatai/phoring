"""Ontology generation service.

Interface 1 in the pipeline: analyzes source content and simulation requirements
to produce entity and relationship type definitions.
"""

import json
from typing import Dict, Any, List, Optional
from..utils.llm_client import LLMClient


# Ontology generation system prompt (sent to LLM - intentionally mixed language)
ONTOLOGY_SYSTEM_PROMPT = """ knowledge graph. task analyze textcontent simulation requirement, **Swarm Intelligence Prediction Engine** entitytype relationtype.

**: mustoutput JSON formatdata, do notoutput othercontent.**

## coretask 

 Build **Swarm Intelligence Prediction Engine **.: 
- eachentity socialmedia,, spreadinfo " " " "
- entity influence, repost, comment, respond
- simulationopinionevent reaction infospreadpath

therefore, **entitymust exists, **: 

** **: 
- concrete personal(,, opinion,,)
- company, (including)
- organizationinstitution(,, NGO,)
- government, institution
- mediainstitution(,, media,)
- socialmediaplatform 
- group (,, group)

** **: 
- abstract ( "opinion", " ", "trend")
- / ( " ", " ")
- opinion/attitude( " ", " ")

## outputformat

pleaseoutputJSON format, include: 

```json
{
    "entity_types": [
        {
            "name": "entitytype (, PascalCase)",
            "description": " description(, 100character)",
            "attributes": [
                {
                    "name": "attribute (, snake_case)",
                    "type": "text",
                    "description": "attributedescription"
                }
            ],
            "examples": ["exampleentity1", "exampleentity2"]
        }
    ],
    "edge_types": [
        {
            "name": "relationtype (, UPPER_SNAKE_CASE)",
            "description": " description(, 100character)",
            "source_targets": [
                {"source": " entitytype", "target": " entitytype"}
            ],
            "attributes": []
        }
    ],
    "analysis_summary": " textcontent briefanalyze ()"
}
```

## (!)

### 1. entitytype - must 

**count: must 10entitytype**

**layer (must includeconcretetype type)**: 

 10entitytypemustinclude layer: 

A. ** type(mustinclude, listlast2)**: 
   - `Person`: type. personal other concrete type,.
   - `Organization`: organizationinstitution type. organization other concrete organizationtype,.

B. **concretetype(8, textcontent)**: 
   - text mainrole, concrete type
   -: iftext event, `Student`, `Professor`, `University`
   -: iftext event, `Company`, `CEO`, `Employee`

** type**: 
- text, " ", " ", " "
- if typematch, `Person`
-, organization, `Organization`

**concretetype **: 
- text roletype
- eachconcretetype, avoid 
- description must type type 

### 2. relationtype 

- count: 6-10
- relation 
- Ensurerelation source_targets definition entitytype

### 3. attribute 

- eachentitytype1-3 attribute
- **note**: attribute `name`, `uuid`, `group_id`, `created_at`, `summary`()
- recommended: `full_name`, `title`, `role`, `position`, `location`, `description` 

## entitytypereference

**personal (concrete)**: 
- Student: 
- Professor: / 
- Journalist: 
- Celebrity: / 
- Executive: 
- Official: government 
- Lawyer: 
- Doctor: 

**personal ()**: 
- Person: ( concretetype)

**organization (concrete)**: 
- University: 
- Company: company 
- GovernmentAgency: governmentinstitution
- MediaOutlet: mediainstitution
- Hospital: 
- School: 
- NGO: governmentorganization

**organization ()**: 
- Organization: organizationinstitution( concretetype)

## relationtypereference

- WORKS_FOR: 
- STUDIES_AT: 
- AFFILIATED_WITH: 
- REPRESENTS: 
- REGULATES: 
- REPORTS_ON: 
- COMMENTS_ON: comment
- RESPONDS_TO: respond
- SUPPORTS: 
- OPPOSES: 
- COLLABORATES_WITH: 
- COMPETES_WITH: 
"""


class OntologyGenerator:
    """Ontology generator.

    Analyzes text content and generates entity and relation type definitions.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
    
    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate ontology definition.

        Args:
            document_texts: List of document text strings.
            simulation_requirement: Simulation requirement description.
            additional_context: Optional additional context.

        Returns:
            Ontology definition dict (entity_types, edge_types).
        """
        # Build user message
        user_message = self._build_user_message(
            document_texts, 
            simulation_requirement,
            additional_context
        )
        
        messages = [
            {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        # Call LLM
        result = self.llm_client.chat_json(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )
        
        # Validate and process
        result = self._validate_and_process(result)
        
        return result
    
    # Maximum text length for LLM input (50k characters)
    MAX_TEXT_LENGTH_FOR_LLM = 50000
    
    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str]
    ) -> str:
        """Build user message for the LLM."""
        
        # Merge text from all documents
        combined_text = "\n\n---\n\n".join(document_texts)
        original_length = len(combined_text)
        
        # If text exceeds limit, truncate (too much content affects LLM quality and graph building)
        if len(combined_text) > self.MAX_TEXT_LENGTH_FOR_LLM:
            from ..utils.logger import get_logger
            _logger = get_logger('phoring.ontology')
            _logger.warning(
                f"Document text truncated from {original_length:,} to "
                f"{self.MAX_TEXT_LENGTH_FOR_LLM:,} chars for ontology generation. "
                f"Content beyond the limit will NOT be analyzed for entity extraction."
            )
            combined_text = combined_text[:self.MAX_TEXT_LENGTH_FOR_LLM]
            combined_text += (
                f"\n\n[WARNING: Document was truncated. Original length: {original_length:,} chars. "
                f"Only the first {self.MAX_TEXT_LENGTH_FOR_LLM:,} chars were analyzed. "
                f"Entities mentioned only in the truncated portion may be missing.]"
            )
        
        message = f"""## Simulation Requirement

{simulation_requirement}

## Document Content

{combined_text}
"""
        
        if additional_context:
            message += f"""
## Additional Context

{additional_context}
"""
        
        message += """
Please analyze the above content and design entity types and relation types suitable for social media opinion simulation.

**Requirements**:
1. Output exactly 10 entity types
2. Prioritize domain-specific types that accurately represent the entities in the document
3. Include Person and Organization as fallback types ONLY if no more specific type covers those entities
   - For example, if the document is about Indian stock markets, use types like Investor, Trader, Broker, 
     Regulator, ListedCompany rather than generic Person/Organization
   - If the document mentions specific professions or roles, create types for those roles
4. Entity types must be actionable social media participants, not abstract concepts
5. Do NOT use name, uuid, group_id etc. as attributes; use full_name, org_name, etc. instead
6. All entity types should be relevant to the document's domain — avoid generic types when specific ones fit better
"""
        
        return message
    
    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and process the ontology result."""
        
        # Ensure required fields exist
        if "entity_types" not in result:
            result["entity_types"] = []
        if "edge_types" not in result:
            result["edge_types"] = []
        if "analysis_summary" not in result:
            result["analysis_summary"] = ""
        
        # Validate entity types
        for entity in result["entity_types"]:
            if "attributes" not in entity:
                entity["attributes"] = []
            if "examples" not in entity:
                entity["examples"] = []
            # Ensure description is within 100 characters
            if len(entity.get("description", "")) > 100:
                entity["description"] = entity["description"][:97] + "..."
        
        # Validate relation types
        for edge in result["edge_types"]:
            if "source_targets" not in edge:
                edge["source_targets"] = []
            if "attributes" not in edge:
                edge["attributes"] = []
            if len(edge.get("description", "")) > 100:
                edge["description"] = edge["description"][:97] + "..."
        
        # Zep API limit: max 10 custom entity types, 10 custom edge types
        MAX_ENTITY_TYPES = 10
        MAX_EDGE_TYPES = 10
        
        # Fallback type definitions
        person_fallback = {
            "name": "Person",
            "description": "Any individual person not fitting other specific person types.",
            "attributes": [
                {"name": "full_name", "type": "text", "description": "Full name of the person"},
                {"name": "role", "type": "text", "description": "Role or occupation"}
            ],
            "examples": ["ordinary citizen", "anonymous netizen"]
        }
        
        organization_fallback = {
            "name": "Organization",
            "description": "Any organization not fitting other specific organization types.",
            "attributes": [
                {"name": "org_name", "type": "text", "description": "Name of the organization"},
                {"name": "org_type", "type": "text", "description": "Type of organization"}
            ],
            "examples": ["small business", "community group"]
        }
        
        # Check whether fallback types already exist — only add if NO individual or org types exist
        entity_names = {e["name"] for e in result["entity_types"]}
        entity_descs_lower = " ".join(
            e.get("description", "").lower() for e in result["entity_types"]
        )
        
        # Check if any individual-type entities exist (even under domain-specific names)
        has_individual_type = "Person" in entity_names or any(
            keyword in entity_descs_lower
            for keyword in ["individual", "person", "trader", "investor", "analyst",
                          "journalist", "official", "expert", "citizen", "user"]
        )
        # Check if any org-type entities exist
        has_org_type = "Organization" in entity_names or any(
            keyword in entity_descs_lower
            for keyword in ["organization", "company", "institution", "agency",
                          "corporation", "firm", "enterprise", "exchange"]
        )
        
        # Add fallback types only if the domain truly lacks coverage
        fallbacks_to_add = []
        if not has_individual_type:
            fallbacks_to_add.append(person_fallback)
        if not has_org_type:
            fallbacks_to_add.append(organization_fallback)
        
        if fallbacks_to_add:
            current_count = len(result["entity_types"])
            needed_slots = len(fallbacks_to_add)
            
            # If adding fallbacks would exceed 10, remove excess types
            if current_count + needed_slots > MAX_ENTITY_TYPES:
                # Determine how many to remove
                to_remove = current_count + needed_slots - MAX_ENTITY_TYPES
                # Remove from the end (least important concrete types)
                result["entity_types"] = result["entity_types"][:-to_remove]
            
            # Add fallback types
            result["entity_types"].extend(fallbacks_to_add)
        
        # Ensure type counts do not exceed limits
        if len(result["entity_types"]) > MAX_ENTITY_TYPES:
            result["entity_types"] = result["entity_types"][:MAX_ENTITY_TYPES]
        
        if len(result["edge_types"]) > MAX_EDGE_TYPES:
            result["edge_types"] = result["edge_types"][:MAX_EDGE_TYPES]
        
        return result
    

