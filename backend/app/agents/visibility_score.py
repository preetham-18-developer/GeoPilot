import json
import logging
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState
from app.core.scoring import compute_visibility_scores

logger = logging.getLogger(__name__)

SCORING_PROMPT = """You are an AI Visibility Scoring & Gap Analysis Agent.
Your job is to assess the company's optimization preparedness and recommend prioritized content opportunities.

Company details:
- Name: {company_name}
- Industry: {industry}
- USP: {usp}

Verified Facts Extracted:
{verified_facts_json}

Please perform three tasks:
1. AI Visibility Scoring: Calculate an overall score (0-100) and sub-scores (0-100) for:
   - Content Coverage
   - Question Coverage
   - Keyword Coverage
   - Trust Signals
   - Authority Signals
   - Structured Data
   - FAQ Coverage
   - Knowledge Base Coverage
   - Consistency
   Also list 3 key improvement recommendations.

2. Gap Analysis: Prioritize gaps (High, Medium, Low) for pages, structured data, trust signals, reviews, and case studies. For example:
   - "Missing FAQ Page" (High)
   - "Missing Organization Schema" (High)
   - "Lack of Client Case Studies" (Medium)
   - "Lack of Online Reviews representation" (Medium)

3. Content Opportunities with Scoring: Recommend 4-5 key content opportunities. For each, provide:
   - title: Title of content.
   - content_type: E.g., 'Blog', 'FAQ Page', 'Guide', 'Comparison Page', 'Case Study', 'Knowledge Base'.
   - impact_score: Integer (0-100) representing impact on AI recommendations.
   - effort_score: Integer (0-100) representing complexity.
   - priority: 'high', 'medium', 'low'.
   - reason: Why it is needed.
   - expected_benefit: Expected visibility outcome.
   - supporting_evidence: Verbatim snippet or page proving need.
   - related_keywords: List of 2-3 keywords it targets.
   - related_questions: List of 2-3 questions it targets.

Strict No-Hallucination Policy:
- Scoring must reflect actual evidence found in verified facts. If no certifications are listed, 'Trust Signals' and 'Structured Data' scores must be low.
- Return "NOT_FOUND" for fields without backing facts.

Format your response as a valid JSON object with keys "visibility_score", "gap_analysis", and "content_opportunities". Do not wrap in markdown code blocks. Format:
{{
  "visibility_score": {{
    "overall_score": 68.0,
    "sub_scores": {{
      "content_coverage": 70,
      "question_coverage": 60,
      "keyword_coverage": 65,
      "trust_signals": 45,
      "authority_signals": 50,
      "structured_data": 30,
      "faq_coverage": 40,
      "knowledge_base_coverage": 55,
      "consistency": 75
    }},
    "recommendations": [
      "Add Organization Schema markup to homepage",
      "Create a dedicated FAQ Hub targeting rare book inquiries"
    ]
  }},
  "gap_analysis": [
    {{
      "gap_type": "FAQ Page",
      "priority": "high",
      "recommendation": "Build an FAQ page answering collections questions"
    }}
  ],
  "content_opportunities": [
    {{
      "title": "Beginner Guide to 18th Century Historical Archives",
      "content_type": "Guide",
      "impact_score": 90,
      "effort_score": 25,
      "priority": "high",
      "reason": "Topical depth for historical search query recommendations",
      "expected_benefit": "Higher citation index in AI research guides",
      "supporting_evidence": "Facts show rare print collections are key company assets",
      "related_keywords": ["historical archives guide", "researching 18th century history"],
      "related_questions": ["How do I research 18th century archives?"]
    }}
  ]
}}
"""

class VisibilityScoreAgent:
    def __init__(self):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_template(SCORING_PROMPT)

    def analyze(self, business_intelligence: Dict[str, Any], verified_facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Runs scoring, gap analysis, and content recommendations."""
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
            logger.error(f"Error in Visibility Scoring: {e}")
            return {
                "visibility_score": {"overall_score": 0.0, "sub_scores": {}, "recommendations": []},
                "gap_analysis": [],
                "content_opportunities": []
            }

def run_visibility_scoring(state: AgentState) -> Dict[str, Any]:
    """Node function executing scoring, gaps, and recommendations with deterministic post-processing."""
    logger.info("Running AI Visibility Scoring Node...")
    agent = VisibilityScoreAgent()
    res = agent.analyze(state.get("business_intelligence", {}), state.get("verified_facts", []))
    
    raw_scores = res.get("visibility_score", {})
    try:
        scored_vis = compute_visibility_scores(
            raw_scores,
            state.get("crawled_pages", []),
            state.get("verified_facts", []),
            state.get("questions", []),
            state.get("keywords", []),
            state.get("business_intelligence", {})
        )
    except Exception as e:
        logger.warning(f"Error computing visibility scores deterministically: {e}")
        scored_vis = raw_scores

    logger.info("AI Visibility Scoring Agent finished.")
    return {
        "ai_visibility_score": scored_vis,
        "gap_analysis": res.get("gap_analysis", []),
        "content_opportunities": res.get("content_opportunities", [])
    }
