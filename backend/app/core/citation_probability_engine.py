"""
citation_probability_engine.py
Phase 7 — Citation Probability Engine

Predicts the citation likelihood of crawled pages in conversational search answers
by weighting authority, trust signals, entity occurrences, text depth, and verified facts.
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class CitationProbabilityEngine:
    """
    Computes a deterministic citation probability index for crawled website pages.
    """

    def run(self, project_id: str, current_run_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Runs calculations over crawled pages, inserts findings into citation_predictions, and returns the list.
        """
        crawled_pages = payload.get("crawled_pages", []) or []
        verified_facts = payload.get("verified_facts", []) or []
        business_profile = payload.get("business_profile", {}) or {}

        company_name = (business_profile.get("company_name", "") or "Brand").lower()
        industry = (business_profile.get("industry", "") or "").lower()

        predictions = []
        for page in crawled_pages[:8]: # Limit to top 8 crawled pages
            url = page.get("url", "")
            title = page.get("title", "") or "Index Resource"
            content = (page.get("content", "") or "").lower()
            
            # 1. Authority Score
            auth_terms = ["leader", "expert", "founded", "experience", "certification", "industry", "years"]
            auth_matches = sum(1 for term in auth_terms if term in content)
            authority_score = min(100.0, 30.0 + auth_matches * 10.0)

            # 2. Trust Score
            trust_terms = ["secure", "privacy", "trust", "guarantee", "reviews", "partners", "policy"]
            trust_matches = sum(1 for term in trust_terms if term in content)
            trust_score = min(100.0, 35.0 + trust_matches * 10.0)

            # 3. Entity Strength
            entity_count = content.count(company_name)
            if industry:
                entity_count += content.count(industry)
            entity_strength = min(100.0, 20.0 + entity_count * 8.0)

            # 4. Content Depth (based on word count)
            # Find word count of content
            words = content.split()
            content_depth = min(100.0, (len(words) / 3.0)) # Scale: 300 words = 100% depth index

            # 5. Evidence Score (count verified facts matching this URL)
            facts_count = sum(1 for f in verified_facts if f.get("source_url", "") == url)
            evidence_score = min(100.0, 25.0 + facts_count * 20.0)

            # Calculate Overall Citation Probability
            prob = (0.30 * authority_score) + \
                   (0.25 * trust_score) + \
                   (0.15 * entity_strength) + \
                   (0.15 * content_depth) + \
                   (0.15 * evidence_score)
            
            predictions.append({
                "project_id": project_id,
                "run_id": current_run_id,
                "page_url": url,
                "page_title": title,
                "citation_probability": round(prob, 1),
                "authority_score": round(authority_score, 1),
                "trust_score": round(trust_score, 1),
                "entity_strength": round(entity_strength, 1),
                "content_depth": round(content_depth, 1),
                "evidence_score": round(evidence_score, 1)
            })

        if predictions:
            try:
                supabase_client.table("citation_predictions").insert(predictions).execute()
                logger.info(f"Persisted {len(predictions)} citation predictions for project {project_id}.")
            except Exception as e:
                logger.error(f"Error persisting citation predictions: {e}")

        return predictions
