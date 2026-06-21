import json
import logging
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState
from app.core.scoring import compute_competitor_scores

logger = logging.getLogger(__name__)

COMPETITOR_PROMPT = """You are a Competitor Discovery Agent.
Your mission is to analyze this business's category and facts, discover exactly 10 direct and indirect competitors, and identify visibility gaps.

Business Information:
{verified_facts_json}

For each of the 10 competitors, provide:
- competitor_name: Brand/business name.
- website: Competitor website URL.
- competitor_type: Must be exactly 'direct' or 'indirect'.
- description: A brief description of the competitor.
- strengths: An array of key strengths.
- weaknesses: An array of key weaknesses.
- unique_features: An array of features unique to this competitor.
- content_gaps: An array of content areas where they outperform the client.
- reason_selected: An array of reasons why this competitor was selected (e.g. 'Similar target audience').
- similarity_score: An integer from 0 to 100 representing similarity.
- industry_match: Brief explanation of how their industry matches the client.
- audience_match: Brief explanation of how their target audience matches the client.
- service_match: Brief explanation of how their services match the client.
- confidence_score: A float between 0.0 and 1.0 representing confidence.

You must also output a "feature_matrix" comparing the client with these competitors on a set of 5-8 relevant features. For example:
- Features like 'Online Collections', 'Membership Program', 'Mentorship', 'Certification', 'Research Services', 'Consulting'.
- For each feature, indicate if the Client provides it ('Yes' or 'No') and what each competitor provides.
- Automatically identify 'unique_competitor_features' and 'missing_client_features' based on the matrix.

Strict No-Hallucination Policy:
- ONLY suggest real competitors matching the industry.
- Return "NOT_FOUND" for any details that are unavailable. Do not guess.

Format your response as a valid JSON object with keys "competitors" (array of 10 objects) and "feature_matrix" (object). Do not wrap it in markdown code blocks. Format:
{{
  "competitors": [
    {{
      "competitor_name": "Acme CRM Inc",
      "website": "https://acmecrm.com",
      "competitor_type": "direct",
      "description": "Acme CRM provides SaaS-based client management.",
      "strengths": ["Strong enterprise integration", "Large market share"],
      "weaknesses": ["Extremely high price points", "Outdated mobile application"],
      "unique_features": ["AI lead prediction"],
      "content_gaps": ["Lacks beginner guide about CRM integration"],
      "reason_selected": ["Similar target audience", "Similar service offerings"],
      "similarity_score": 91,
      "industry_match": "SaaS CRM domain matches client product category",
      "audience_match": "Both target sales teams and startups",
      "service_match": "Both offer customer database and email marketing tools",
      "confidence_score": 0.95
    }}
  ],
  "feature_matrix": {{
    "features": [
      {{
        "feature_name": "Online Collections",
        "client_value": "Yes",
        "competitor_values": {{
          "Acme CRM Inc": "No"
        }}
      }}
    ],
    "unique_competitor_features": ["AI lead prediction"],
    "missing_client_features": ["AI lead prediction"]
  }}
}}
"""

class CompetitorDiscoveryAgent:
    def __init__(self):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_template(COMPETITOR_PROMPT)

    def discover_competitors(self, verified_facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates competitor profiles, gaps, and content optimization recommendations."""
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
            logger.error(f"Error in Competitor Discovery: {e}")
            return {"competitors": [], "feature_matrix": {"features": [], "unique_competitor_features": [], "missing_client_features": []}}

def run_competitor_discovery(state: AgentState) -> Dict[str, Any]:
    """Node function that executes competitor discovery and post-processes scores deterministically."""
    logger.info("Running Competitor Discovery Node...")
    agent = CompetitorDiscoveryAgent()
    res = agent.discover_competitors(state.get("verified_facts", []))
    
    competitors = res.get("competitors", [])
    feature_matrix = res.get("feature_matrix", {})
    bi = state.get("business_intelligence", {})
    
    # Calculate deterministic similarity and match scores
    for comp in competitors:
        try:
            scores = compute_competitor_scores(comp, feature_matrix, bi)
            comp.update(scores)
        except Exception as e:
            logger.warning(f"Error computing competitor scores for {comp.get('competitor_name', 'Unknown')}: {e}")
            
    logger.info(f"Competitor Discovery finished. Discovered and scored {len(competitors)} competitors.")
    return {"competitors": competitors, "competitor_feature_matrix": feature_matrix}
