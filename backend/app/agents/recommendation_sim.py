import json
import logging
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

SIM_PROMPT = """You are an AI Recommendation Simulation Agent.
Your job is to simulate how conversational AI systems (ChatGPT, Gemini, Claude, Perplexity) might discover and recommend the client business based on user search queries.

Company Profile:
- Name: {company_name}
- Industry: {industry}
- USP: {usp}

Verified facts:
{verified_facts_json}

Please generate exactly 3 highly realistic user queries that target the client's industry, location, or core services.
For each query, calculate:
1. query: The user search query.
2. recommendation_probability: A float between 0.0 and 100.0 representing readiness.
3. supporting_evidence: List of facts that support recommending the client for this query.
4. missing_requirements: What requirements are missing to achieve 100% recommendation confidence (e.g. 'No Organization Schema markup detected', 'Lack of FAQ page for rare books').
5. improvement_actions: Specific content or technical steps to take.

Strict No-Hallucination Policy:
- The probability must reflect the actual facts available (e.g., if there are very few facts, the score should be low, e.g. 20-50%).
- If information is missing, list it in missing_requirements.

Format your response as a valid JSON array of objects. Do not wrap it in markdown code blocks. Format:
[
  {{
    "query": "Best historical research library in America",
    "recommendation_probability": 42.0,
    "supporting_evidence": ["Founded in 1731 as a subscription library", "Has print collections of early American history"],
    "missing_requirements": ["Low FAQ Coverage", "Missing Structured Data", "Weak Content Coverage"],
    "improvement_actions": ["Create FAQ Hub", "Create Research Guides", "Add Organization Schema"]
  }}
]
"""

class RecommendationSimAgent:
    def __init__(self):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_template(SIM_PROMPT)

    def run_simulations(self, business_intelligence: Dict[str, Any], verified_facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simulates search query recommendations."""
        try:
            facts_str = json.dumps(verified_facts, indent=2)
            formatted_prompt = self.prompt.format_messages(
                company_name=business_intelligence.get("company_name", "Unknown"),
                industry=business_intelligence.get("industry", "Unknown"),
                usp=business_intelligence.get("usp", "Unknown"),
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
            logger.error(f"Error in Recommendation Simulation: {e}")
            return []

def run_recommendation_sim(state: AgentState) -> Dict[str, Any]:
    """Node function that executes recommendation readiness simulation."""
    logger.info("Running Recommendation Simulation Node...")
    agent = RecommendationSimAgent()
    simulations = agent.run_simulations(state.get("business_intelligence", {}), state.get("verified_facts", []))
    logger.info(f"Recommendation Simulation finished. Simulated {len(simulations)} queries.")
    return {"recommendation_simulations": simulations}
