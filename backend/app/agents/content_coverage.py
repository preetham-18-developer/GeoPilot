import json
import logging
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

COVERAGE_PROMPT = """You are a Content Coverage Agent.
Your job is to analyze the crawled content topics and verify if they cover key services/products comprehensively.

Verified Facts:
{verified_facts_json}

Please identify the 2-3 major service or product topics offered by this business. For each topic, evaluate:
1. topic_name: The name of the product/service (e.g. 'Research Library Services').
2. coverage_score: A float between 0.0 and 100.0 representing topical completeness.
3. question_coverage: An array of key customer questions that are covered by the current website content.
4. keyword_coverage: An array of target keywords that are covered by the current content.
5. faq_coverage: An array of FAQ points covered.
6. content_depth: Must be exactly one of: 'Shallow', 'Detailed', 'Exhaustive'.
7. missing_content_areas: An array of specific content pages or topics that are missing (e.g. 'Beginner Guide', 'FAQ Page', 'Pricing Information').

Strict No-Hallucination Policy:
- ONLY base the coverage scores and lists on facts explicitly found in verified facts.
- Do NOT fabricate covered keywords or questions. If none are found, return empty lists.

Format your response as a valid JSON array of objects. Do not wrap it in markdown code blocks. Format:
[
  {{
    "topic_name": "Research Library Services",
    "coverage_score": 82.0,
    "question_coverage": ["What are the library hours?", "How to apply for a fellowship?"],
    "keyword_coverage": ["historical archives", "philadelphia fellowships"],
    "faq_coverage": ["fellowship application instructions"],
    "content_depth": "Detailed",
    "missing_content_areas": ["Beginner Guide", "Comparison Guide", "FAQ Page", "Pricing Information"]
  }}
]
"""

class ContentCoverageAgent:
    def __init__(self):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_template(COVERAGE_PROMPT)

    def analyze_coverage(self, verified_facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluates topical coverage against facts."""
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
            logger.error(f"Error in Content Coverage Analysis: {e}")
            return []

def run_content_coverage(state: AgentState) -> Dict[str, Any]:
    """Node function that executes content coverage evaluation."""
    logger.info("Running Content Coverage Node...")
    agent = ContentCoverageAgent()
    coverage = agent.analyze_coverage(state.get("verified_facts", []))
    logger.info(f"Content Coverage finished. Evaluated {len(coverage)} topics.")
    return {"content_coverage": coverage}
