import json
import logging
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

ENTITY_PROMPT = """You are an Entity & Knowledge Graph Agent.
Your mission is to read verified business facts, extract important business entities, and build a relationship knowledge graph.

Verified Business Facts:
{verified_facts_json}

Please extract:
1. entity_nodes: A list of nodes. For each node, provide:
   - entity_name: Name of the entity.
   - entity_type: Must be exactly one of: 'Company', 'Product', 'Service', 'Location', 'Author', 'Partner', 'Technology', 'Industry', 'Certification'
   - properties: A flat JSON object containing key-value pairs (e.g. "founding_year": 1731, "city": "Philadelphia"). If none, return empty object.

2. entity_relationships: A list of relationships. For each relationship, provide:
   - source_entity_name: Name of the source entity node.
   - target_entity_name: Name of the target entity node.
   - relationship_type: The predicate (e.g. 'OFFERS', 'LOCATED_IN', 'PROVIDES', 'PARTNERS_WITH', 'BUILT_WITH', 'CERTIFIED_IN').

Strict No-Hallucination Policy:
- ONLY extract entities and relationships that are explicitly mentioned in verified facts.
- Do NOT guess connections. Return "NOT_FOUND" if unavailable.

Format your response as a valid JSON object. Do not wrap it in markdown code blocks. Format:
{{
  "entity_nodes": [
    {{
      "entity_name": "The Library Company",
      "entity_type": "Company",
      "properties": {{
        "description": "Historical research library"
      }}
    }},
    {{
      "entity_name": "Research Library Services",
      "entity_type": "Service",
      "properties": {{}}
    }},
    {{
      "entity_name": "Philadelphia",
      "entity_type": "Location",
      "properties": {{}}
    }}
  ],
  "entity_relationships": [
    {{
      "source_entity_name": "The Library Company",
      "target_entity_name": "Research Library Services",
      "relationship_type": "OFFERS"
    }},
    {{
      "source_entity_name": "The Library Company",
      "target_entity_name": "Philadelphia",
      "relationship_type": "LOCATED_IN"
    }}
  ]
}}
"""

class EntityGraphAgent:
    def __init__(self):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_template(ENTITY_PROMPT)

    def extract_graph(self, verified_facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extracts nodes and relationships from verified facts."""
        try:
            facts_str = json.dumps(verified_facts, indent=2)
            formatted_prompt = self.prompt.format_messages(
                verified_facts_json=facts_str
            )
            response = self.llm.invoke(formatted_prompt)
            
            resp_text = response.content.strip()
            if resp_text.startswith("```json"):
                resp_text = resp_text[7:]
            if resp_text.endswith("```"):
                resp_text = resp_text[:-3]
            resp_text = resp_text.strip()
            
            return json.loads(resp_text)
        except Exception as e:
            logger.error(f"Error in Entity Graph Extraction: {e}")
            return {"entity_nodes": [], "entity_relationships": []}

def run_entity_graph(state: AgentState) -> Dict[str, Any]:
    """Node function that executes entity knowledge graph extraction."""
    logger.info("Running Entity & Knowledge Graph Node...")
    agent = EntityGraphAgent()
    graph_res = agent.extract_graph(state.get("verified_facts", []))
    logger.info(f"Entity Graph finished. Extracted {len(graph_res.get('entity_nodes', []))} nodes and {len(graph_res.get('entity_relationships', []))} relationships.")
    return {
        "entity_nodes": graph_res.get("entity_nodes", []),
        "entity_relationships": graph_res.get("entity_relationships", [])
    }
