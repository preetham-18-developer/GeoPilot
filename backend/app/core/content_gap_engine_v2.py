"""
content_gap_engine_v2.py
Phase 7 — Content Gap Engine V2

Performs structural content audits to identify missing topics, FAQ nodes, authority certifications,
and core trust layouts (Comparison, Case Study, Resource pages).
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class ContentGapEngineV2:
    """
    Identifies high-level content structure gaps and projects impact/effort values.
    """

    def run(self, project_id: str, current_run_id: str, payload: Dict[str, Any], heatmap_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audits project databases to discover missing elements, logs content_gap_reports_v2,
        and returns the report dict.
        """
        crawled_pages = payload.get("crawled_pages", []) or []
        verified_facts = payload.get("verified_facts", []) or []
        keywords = payload.get("keywords", []) or []
        business_profile = payload.get("business_profile", {}) or {}

        urls = [p.get("url", "").lower() for p in crawled_pages]

        # 1. Audit Trust & Structural Pages
        missing_trust = []
        if not any("about" in url for url in urls):
            missing_trust.append("About Us Page")
        if not any("privacy" in url or "terms" in url for url in urls):
            missing_trust.append("Privacy Policy / Terms of Service Page")
        if not any("security" in url or "compliance" in url for url in urls):
            missing_trust.append("Security & Compliance Page")

        missing_case_studies = []
        if not any("case-stud" in url or "success" in url or "customer" in url for url in urls):
            missing_case_studies.append("Dedicated Case Studies Index")
            missing_case_studies.append("Factual Customer ROI Metrics")

        missing_comparison = []
        if not any("vs" in url or "compar" in url or "alternative" in url for url in urls):
            missing_comparison.append("Competitor Feature Matrix Page")
            missing_comparison.append("Alternative Product Analysis Page")

        missing_resources = []
        if not any("blog" in url or "resource" in url or "guide" in url or "kb" in url for url in urls):
            missing_resources.append("Educational Knowledge Base / Blog Hub")

        # 2. Audit Missing Topics from Keyword Clusters & Heatmaps
        missing_topics = heatmap_data.get("missing_categories", []) or []
        if not missing_topics:
            # Fallback check on keyword coverage
            uncovered_kws = [k.get("keyword", "") for k in keywords if float(k.get("coverage_score", 0.0)) == 0.0]
            missing_topics = uncovered_kws[:3]

        # 3. Audit Missing FAQ Areas
        missing_faqs = []
        if not any("faq" in url for url in urls):
            missing_faqs.append("System FAQ Center")
        
        # Check weak heatmap categories for FAQ missing areas
        weak_cats = heatmap_data.get("weak_categories", []) or []
        for cat in weak_cats:
            missing_faqs.append(f"{cat} FAQ Intent Mapping")

        # 4. Audit Missing Authority Signals
        missing_authority = []
        trust_signals = business_profile.get("trust_signals", []) or []
        if not trust_signals:
            missing_authority.append("Verified Regulatory Certifications")
        if len(verified_facts) < 5:
            missing_authority.append("Factual Claims Citations References")

        # 5. Compute scores
        gap_count = len(missing_trust) + len(missing_case_studies) + len(missing_comparison) + len(missing_topics)
        impact_score = min(98, 40 + gap_count * 12)
        
        # Effort calculation based on complexity of missing items
        effort = 15
        if missing_comparison:
            effort += 20
        if missing_case_studies:
            effort += 15
        if missing_topics:
            effort += 15
        effort_score = min(95, effort)
        
        recommendation_val = round((impact_score * 0.70) + ((100 - effort_score) * 0.30), 1)

        result = {
            "project_id": project_id,
            "run_id": current_run_id,
            "missing_topics": missing_topics,
            "missing_faq_areas": missing_faqs[:3],
            "missing_authority_signals": missing_authority,
            "missing_trust_pages": missing_trust,
            "missing_case_studies": missing_case_studies,
            "missing_comparison_pages": missing_comparison,
            "missing_resource_pages": missing_resources,
            "impact_score": int(impact_score),
            "effort_score": int(effort_score),
            "recommendation_value": float(recommendation_val)
        }

        try:
            supabase_client.table("content_gap_reports_v2").insert(result).execute()
            logger.info(f"Persisted content gap report V2 for project {project_id}.")
        except Exception as e:
            logger.error(f"Error persisting content gap report V2: {e}")

        return result
