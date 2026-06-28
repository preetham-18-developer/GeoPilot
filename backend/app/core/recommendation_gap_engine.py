"""
recommendation_gap_engine.py
Phase 9 — Recommendation Gap Engine
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class RecommendationGapEngine:
    """
    Identifies gaps in content, authority, trust, and evidence preventing conversational AI search engines from recommending a company.
    """

    def run(self, project_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Determines missing signals, writes them to recommendation_gaps table, and returns the lists.
        """
        questions = payload.get("questions", []) or []
        verified_facts = payload.get("verified_facts", []) or []
        business_profile = payload.get("business_profile", {}) or {}
        content_coverage = payload.get("content_coverage", []) or []
        entity_nodes = payload.get("entity_nodes", []) or []

        gaps = []

        # 1. Check Missing FAQs
        if len(questions) < 15:
            gaps.append({
                "project_id": project_id,
                "category": "FAQ",
                "severity": "MEDIUM",
                "missing_signal": "Insufficient FAQ Coverage",
                "explanation": f"Only {len(questions)} target conversational discovery questions found. Conversational engines require direct Q&A answering patterns.",
                "repair_action": "Expand discovery questions list and publish dedicated Accordion/FAQ panels covering transactional and informational intents."
            })

        # 2. Check Trust Signals
        trust_signals = business_profile.get("trust_signals", []) or []
        if not trust_signals:
            gaps.append({
                "project_id": project_id,
                "category": "Trust Signal",
                "severity": "CRITICAL",
                "missing_signal": "No Trust Verification Signs",
                "explanation": "No verified trust signals (SSL, review badges, guarantees, privacy policy links) found on the company profile.",
                "repair_action": "Publish clear privacy guidelines, customer success stories, and display security/service badges on the home page."
            })

        # 3. Check Authority Sources
        # Fetch authority references count from database or content
        has_compliance = any(
            any(kw in str(item).lower() for kw in ["iso", "soc", "nist", "hipaa", "standard", "compliance"])
            for item in trust_signals
        )
        if not has_compliance:
            gaps.append({
                "project_id": project_id,
                "category": "Authority Source",
                "severity": "HIGH",
                "missing_signal": "Missing Compliance Certification",
                "explanation": "No information security or standard compliance audits (e.g. ISO 27001, SOC 2) found in company profile.",
                "repair_action": "Undergo third-party audit credentials mapping or prominently cite standards compliance documentation."
            })

        # 4. Check Content Coverage
        low_coverage_topics = [c for c in content_coverage if c.get("coverage_score", 100.0) < 60.0]
        if low_coverage_topics:
            gaps.append({
                "project_id": project_id,
                "category": "Content Coverage",
                "severity": "HIGH",
                "missing_signal": "Shallow Topic Coverage",
                "explanation": f"Discovered {len(low_coverage_topics)} core categories with coverage scores below 60%.",
                "repair_action": "Publish deep-dive authority articles, guides, and comparison tables for the flagged topics."
            })

        # 5. Check Entity Graph
        if len(entity_nodes) < 10:
            gaps.append({
                "project_id": project_id,
                "category": "Entity Graph",
                "severity": "MEDIUM",
                "missing_signal": "Weak Semantic Entity Graph",
                "explanation": "Entity graph relationships are weak. Conversational models might struggle to map the company to key industry concepts.",
                "repair_action": "Embed descriptive structured schema markup specifying exact company properties and industry connections."
            })

        # 6. Check Evidence
        if len(verified_facts) < 8:
            gaps.append({
                "project_id": project_id,
                "category": "Evidence",
                "severity": "CRITICAL",
                "missing_signal": "Deficient Fact Grounding",
                "explanation": f"Only {len(verified_facts)} verified ground truth facts are mapped. Large language models penalize lack of evidence.",
                "repair_action": "Create fact lists with citations, referencing industry audits, client numbers, and product benchmark reports."
            })

        # Fallback safeguard if all criteria were technically healthy
        if not gaps:
            gaps.append({
                "project_id": project_id,
                "category": "Evidence",
                "severity": "LOW",
                "missing_signal": "Refining Fact Citations",
                "explanation": "All major signals are healthy. Minor enhancements on facts citation links are recommended.",
                "repair_action": "Verify and validate link consistency periodically to avoid dead citation links."
            })

        try:
            # Clear previous recommendation gaps
            supabase_client.table("recommendation_gaps").delete().eq("project_id", project_id).execute()
            supabase_client.table("recommendation_gaps").insert(gaps).execute()
            logger.info(f"Successfully saved {len(gaps)} recommendation gaps.")
        except Exception as e:
            logger.error(f"Error persisting recommendation gaps: {e}")

        return gaps
