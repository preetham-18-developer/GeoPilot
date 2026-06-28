"""
citation_engine.py
Phase 9 — Citation Probability Engine
"""

from typing import Dict, Any, List, Optional
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class CitationEngine:
    """
    Computes a page-level citation probability index (0-100) based on page contents.
    """

    def run(self, project_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Calculates citation probability for crawled pages, saves them to citation_reports, and returns them.
        """
        crawled_pages = payload.get("crawled_pages", []) or []
        verified_facts = payload.get("verified_facts", []) or []
        business_profile = payload.get("business_profile", {}) or {}

        company_name = (business_profile.get("company_name", "") or "Brand").lower()
        industry = (business_profile.get("industry", "") or "").lower()

        reports = []
        # Analyze up to 10 crawled pages
        for page in crawled_pages[:10]:
            url = page.get("url", "")
            title = page.get("title", "") or "Resource page"
            content = (page.get("content", "") or "").lower()

            # 1. Content Depth (target > 500 words is excellent)
            words = content.split()
            word_count = len(words)
            content_depth = min(100.0, (word_count / 5.0)) # 500 words = 100%

            # 2. Evidence Density (verified facts backing this page URL)
            facts_on_page = sum(1 for f in verified_facts if f.get("source_url", "") == url)
            evidence_density = min(100.0, 20.0 + facts_on_page * 25.0)

            # 3. FAQ Coverage
            faq_terms = ["faq", "frequently asked questions", "q&a", "q: ", "a: "]
            faq_matches = sum(1 for term in faq_terms if term in content)
            faq_coverage = min(100.0, 10.0 + faq_matches * 30.0)

            # 4. Structured Data (JSON-LD schema indicators)
            schema_terms = ["application/ld+json", "@context", "schema.org", "@type"]
            schema_matches = sum(1 for term in schema_terms if term in content)
            structured_data = min(100.0, 15.0 + schema_matches * 25.0)

            # 5. Authority References
            auth_terms = ["iso", "nist", "hipaa", "soc", "standard", "compliance", "verified", "certified", "research", "audit"]
            auth_matches = sum(1 for term in auth_terms if term in content)
            authority_score = min(100.0, 30.0 + auth_matches * 15.0)

            # 6. Trust Signals
            trust_terms = ["secure", "privacy policy", "terms of service", "guarantee", "reviews", "partners", "trust"]
            trust_matches = sum(1 for term in trust_terms if term in content)
            trust_score = min(100.0, 35.0 + trust_matches * 15.0)

            # 7. Internal Links index
            internal_links_in = min(100.0, 40.0 + (word_count / 15.0)) # Mock/proxy link weight

            # Calculate overall citation probability
            citation_prob = (
                (0.20 * content_depth) +
                (0.20 * evidence_density) +
                (0.15 * faq_coverage) +
                (0.15 * structured_data) +
                (0.10 * authority_score) +
                (0.10 * trust_score) +
                (0.10 * internal_links_in)
            )

            report = {
                "project_id": project_id,
                "page_url": url,
                "citation_probability": round(citation_prob, 1),
                "authority_score": round(authority_score, 1),
                "trust_score": round(trust_score, 1),
                "evidence_density": round(evidence_density, 1),
                "confidence": round(min(100.0, 60.0 + facts_on_page * 10.0), 1)
            }
            reports.append(report)

        if reports:
            try:
                # Clear previous reports
                supabase_client.table("citation_reports").delete().eq("project_id", project_id).execute()
                supabase_client.table("citation_reports").insert(reports).execute()
                logger.info(f"Successfully saved {len(reports)} citation reports.")
            except Exception as e:
                logger.error(f"Error persisting citation reports: {e}")

        return reports
