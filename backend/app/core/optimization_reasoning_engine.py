"""
optimization_reasoning_engine.py
Phase 10 — Optimization Reasoning Engine
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class OptimizationReasoningEngine:
    """
    Formulates explainable reasoning logs stating why specific optimization recommendations
    were generated and what signals they target.
    """

    def run(self, project_id: str, plans: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Processes optimization plans and returns detailed explanation cards.
        """
        if not plans:
            try:
                resp = supabase_client.table("optimization_plans")\
                    .select("*")\
                    .eq("project_id", project_id)\
                    .execute()
                plans = resp.data or []
            except Exception as e:
                logger.error(f"Error fetching plans for reasoning engine: {e}")
                plans = []

        reasonings = []

        # Explainers mapping for each category to its targeted signals and reasons
        explainers = {
            "Content": {
                "signals": ["Content", "Keywords", "Authority"],
                "reason": "Search engines prioritize comprehensive, rich, and contextually detailed documents. Short content is flagged as shallow and has low recommendation index probability.",
                "outcome": "Improved contextual understanding by ChatGPT/Gemini, increasing inclusion in long-form answer citations."
            },
            "Trust": {
                "signals": ["Trust", "Evidence"],
                "reason": "AI engines audit the presence of trust validations (SSL, privacy policies, service badges, customer ratings) to ensure compliance and source safety.",
                "outcome": "Mitigates citation risk penalties, converting AI crawlers to trust the source domain."
            },
            "Authority": {
                "signals": ["Authority", "Evidence", "Trust"],
                "reason": "Conversational models dynamically reference certifications (ISO, SOC 2, GDPR) when resolving transactional and technical comparison queries.",
                "outcome": "Positions the brand as a verified industry authority, boosting recommendation probability on direct security queries."
            },
            "Schema": {
                "signals": ["Schema", "Entities", "Content"],
                "reason": "Structured JSON-LD schemas explicitly define page entities, organization attributes, and FAQ relationships in a format readable by AI crawlers.",
                "outcome": "Dramatically reduces entity recognition errors and guarantees semantic graph indexing accuracy."
            },
            "Internal Links": {
                "signals": ["Content", "Entities", "Internal Links"],
                "reason": "Clear anchor links distribute authority equity across the domain, helping engines follow keyword trails and associate related concepts.",
                "outcome": "Enhances crawling indexing footprint and links informational content to product landing pages."
            },
            "FAQ": {
                "signals": ["FAQ", "Questions", "Keywords"],
                "reason": "Direct Q&A layouts match conversational search intents, making FAQ answers ideal snippets for Perplexity and Gemini response boxes.",
                "outcome": "Secures direct snippet citation placements on conversational comparison terms."
            },
            "Questions": {
                "signals": ["Questions", "Keywords"],
                "reason": "Posing direct discovery questions in headers aligns headers metadata directly with conversational voice searches.",
                "outcome": "Higher search ranking on voice-search questions."
            },
            "Keywords": {
                "signals": ["Keywords", "Entities"],
                "reason": "Placing high-relevance semantic terms in paragraphs signals deep content alignment with targeted search queries.",
                "outcome": "Better index semantic relevancy score."
            },
            "Entities": {
                "signals": ["Entities", "Authority"],
                "reason": "Mentioning recognized entity terms links your company to established industry terms inside LLM semantic spaces.",
                "outcome": "Improves domain category associations in search engine embeddings."
            },
            "Evidence": {
                "signals": ["Evidence", "Trust", "Authority"],
                "reason": "Large language models actively verify factual grounding. Claims without numbers or citation links are labeled low confidence.",
                "outcome": "Prevents hallucination risk penalties and increases citation trust scores."
            },
            "Competitors": {
                "signals": ["Competitors", "Content", "Questions"],
                "reason": "Comparison tables addressing direct competitors close gaps that model systems audit when deciding which product to recommend.",
                "outcome": "Enables conversational models to present your USP side-by-side with industry leaders."
            }
        }

        for plan in plans:
            category = plan.get("category", "General")
            recommendation = plan.get("recommendation", "")
            priority = plan.get("priority_score", 50.0)

            exp = explainers.get(category, {
                "signals": ["General"],
                "reason": "Refining this signal boosts overall brand presence in generative engine indices.",
                "outcome": "Incremental optimization of citation search footprints."
            })

            reasonings.append({
                "category": category,
                "recommendation": recommendation,
                "priority_score": priority,
                "signals_involved": exp["signals"],
                "explanation": exp["reason"],
                "expected_outcome": exp["outcome"]
            })

        return reasonings
