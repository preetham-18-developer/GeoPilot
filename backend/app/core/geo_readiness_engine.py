"""
geo_readiness_engine.py
Phase 9 — GEO Readiness Score Engine
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class GEOReadinessEngine:
    """
    Computes a weighted GEO Readiness Score (0-100) and maps it to a health status classification.
    """

    def run(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the GEO readiness calculations across all compliance metrics.
        """
        questions = payload.get("questions", []) or []
        keywords = payload.get("keywords", []) or []
        verified_facts = payload.get("verified_facts", []) or []
        business_profile = payload.get("business_profile", {}) or []
        crawled_pages = payload.get("crawled_pages", []) or []

        # 1. Evidence Score (25% weight)
        evidence_count = len(verified_facts)
        evidence_score = min(100.0, (evidence_count / 15.0) * 100.0) # 15 verified facts = 100%

        # 2. Authority Score (20% weight)
        # Scan if there are compliance/certifications indicators
        trust_signals = business_profile.get("trust_signals", []) if isinstance(business_profile, dict) else []
        has_compliance = any(
            any(kw in str(item).lower() for kw in ["iso", "soc", "nist", "hipaa", "standard", "compliance"])
            for item in trust_signals
        )
        authority_score = 95.0 if has_compliance else 50.0

        # 3. Questions Score (15% weight)
        questions_score = min(100.0, (len(questions) / 20.0) * 100.0) # 20 questions = 100%

        # 4. Keywords Score (15% weight)
        keywords_score = min(100.0, (len(keywords) / 30.0) * 100.0) # 30 keywords = 100%

        # 5. Trust Signals Score (10% weight)
        trust_score = min(100.0, 30.0 + len(trust_signals) * 20.0)

        # 6. Internal Links Score (10% weight)
        links_score = min(100.0, (len(crawled_pages) / 10.0) * 100.0) # 10 pages = 100%

        # 7. Structured Data Score (5% weight)
        # Check if structured json-ld schema tags are found in crawled page content
        all_text = " ".join([p.get("content", "") for p in crawled_pages]).lower()
        has_schema = "application/ld+json" in all_text
        schema_score = 100.0 if has_schema else 40.0

        # Compute weighted final score
        geo_score = (
            (0.25 * evidence_score) +
            (0.20 * authority_score) +
            (0.15 * questions_score) +
            (0.15 * keywords_score) +
            (0.10 * trust_score) +
            (0.10 * links_score) +
            (0.05 * schema_score)
        )

        geo_score = round(geo_score, 1)

        # Determine readiness status
        if geo_score >= 90:
            status = "Excellent"
        elif geo_score >= 75:
            status = "Healthy"
        elif geo_score >= 60:
            status = "Warning"
        else:
            status = "Critical"

        result = {
            "project_id": project_id,
            "geo_readiness_score": geo_score,
            "status": status,
            "breakdown": {
                "evidence_density": round(evidence_score, 1),
                "authority_strength": round(authority_score, 1),
                "question_coverage": round(questions_score, 1),
                "keyword_intelligence": round(keywords_score, 1),
                "trust_compliance": round(trust_score, 1),
                "internal_linking": round(links_score, 1),
                "structured_data": round(schema_score, 1)
            }
        }

        return result
