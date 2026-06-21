import json
import logging
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

CONTENT_AGENT_PROMPT = """You are a Content Strategy Agent specializing in GEO (Generative Engine Optimization) and AIO (AI Optimization).
Your mission is to analyze verified business facts and recommend high-impact content opportunities that can establish domain authority and drive recommendations within AI search engines.

Company details and facts:
{verified_facts_json}

Identify at least 3 content opportunities (pages/guides/blogs) that this company should publish.
For each opportunity, provide:
1. Title: A descriptive, search-optimized title.
2. Content Type: Must be exactly one of: 'Blog', 'Landing Page', 'FAQ Page', 'Guide', 'Comparison Page', 'Case Study', 'Knowledge Base'.
3. Priority: Must be exactly one of: 'high', 'medium', 'low'.
4. Reason: Why this content is needed, and how it leverages the verified facts to satisfy AI user intents.

Format your response as a valid JSON array of objects. Do not wrap it in markdown code blocks. Format:
[
  {{
    "title": "Deep Dive into Multi-Cloud CRM Security",
    "content_type": "Guide",
    "priority": "high",
    "reason": "Leverages verified security certifications to establish brand trust for informational AI queries."
  }}
]
"""

class ContentAgent:
    def __init__(self):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_template(CONTENT_AGENT_PROMPT)

    def generate_recommendations(self, verified_facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generates structured content recommendations."""
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
            logger.error(f"Error in Content Agent: {e}")
            return []

def run_content_agent(state: AgentState) -> Dict[str, Any]:
    """Node function that executes content recommendations generation."""
    logger.info("Running Content Agent Node...")
    agent = ContentAgent()
    opportunities = agent.generate_recommendations(state.get("verified_facts", []))
    logger.info(f"Content Agent finished. Generated {len(opportunities)} opportunities.")
    return {"content_opportunities": opportunities}
