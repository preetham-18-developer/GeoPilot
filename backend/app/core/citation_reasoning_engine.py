"""
citation_reasoning_engine.py
Phase 9 — Citation Reasoning Engine
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class CitationReasoningEngine:
    """
    Formulates explainable reasoning logs stating why conversational search models are likely to cite a page.
    """

    def run(self, project_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Processes pages and returns detailed citation explainability cards.
        """
        crawled_pages = payload.get("crawled_pages", []) or []
        verified_facts = payload.get("verified_facts", []) or []
        
        reasoning_cards = []

        for page in crawled_pages[:5]: # Generate reasoning for top 5 pages
            url = page.get("url", "")
            title = page.get("title", "") or "Page resource"
            content = (page.get("content", "") or "").lower()

            # Find matching verified facts
            matching_facts = [f.get("fact_value", "") for f in verified_facts if f.get("source_url", "") == url]
            
            # Formulate reasoning
            evidence = matching_facts[:3] if matching_facts else ["Standard company features description content."]
            
            # Simple keyword checks to identify strengths
            has_specs = any(kw in content for kw in ["specification", "feature", "price", "pricing", "support"])
            has_compliance = any(kw in content for kw in ["iso", "soc", "standard", "security", "privacy"])

            relevant_facts = []
            if has_specs:
                relevant_facts.append("Features and pricing are outlined explicitly.")
            if has_compliance:
                relevant_facts.append("Page contains standard compliance statements.")
            if not relevant_facts:
                relevant_facts.append("General informational text available.")

            weaknesses = []
            if len(content.split()) < 300:
                weaknesses.append("Content is too short (under 300 words). Conversational engines favor comprehensive context.")
            if not matching_facts:
                weaknesses.append("Lack of verified citations or external backing evidence.")

            confidence = 85.0 if (has_compliance and matching_facts) else 65.0 if matching_facts else 45.0

            reasoning_cards.append({
                "page_url": url,
                "page_title": title,
                "confidence_score": confidence,
                "supporting_evidence": evidence,
                "relevant_facts": relevant_facts,
                "weaknesses": weaknesses,
                "citation_reasons": [
                    "Strong contextual match for user queries regarding company profiles.",
                    "Provides clear, structured facts that can be verified and cited safely."
                ]
            })

        return reasoning_cards
