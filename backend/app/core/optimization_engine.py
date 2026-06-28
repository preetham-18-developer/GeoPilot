"""
optimization_engine.py
Phase 10 — Optimization Plan Engine
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class OptimizationEngine:
    """
    Generates prioritized GEO optimization recommendations across 11 distinct categories,
    computes impact, effort, priority, and estimated GEO gains, and persists them.
    """

    def run(self, project_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Runs the optimization analysis, saves plans to database, and returns them.
        """
        crawled_pages = payload.get("crawled_pages", []) or []
        verified_facts = payload.get("verified_facts", []) or []
        business_profile = payload.get("business_profile", {}) or {}
        questions = payload.get("questions", []) or []
        keywords = payload.get("keywords", []) or []
        competitors = payload.get("competitors", []) or []
        entity_nodes = payload.get("entity_nodes", []) or []

        plans = []

        # Helper to check if string contains standard keywords
        trust_signals = business_profile.get("trust_signals", []) if isinstance(business_profile, dict) else []
        has_compliance = any(
            any(kw in str(item).lower() for kw in ["iso", "soc", "nist", "hipaa", "standard", "compliance"])
            for item in trust_signals
        )

        # 1. Content Optimization
        avg_word_count = sum(len(p.get("markdown_content", "").split()) for p in crawled_pages) / max(1, len(crawled_pages))
        if avg_word_count < 400:
            plans.append({
                "project_id": project_id,
                "category": "Content",
                "recommendation": "Expand shallow pages to over 600 words of comprehensive technical context.",
                "impact_score": 80.0,
                "effort_score": 60.0,
                "estimated_geo_gain": 8.0,
                "status": "pending"
            })
        else:
            plans.append({
                "project_id": project_id,
                "category": "Content",
                "recommendation": "Produce detailed case studies and technical implementation blueprints.",
                "impact_score": 65.0,
                "effort_score": 50.0,
                "estimated_geo_gain": 4.5,
                "status": "pending"
            })

        # 2. Trust Optimization
        if len(trust_signals) < 3:
            plans.append({
                "project_id": project_id,
                "category": "Trust",
                "recommendation": "Display trust certifications, customer testimonials, and explicit privacy policies on home pages.",
                "impact_score": 90.0,
                "effort_score": 40.0,
                "estimated_geo_gain": 12.0,
                "status": "pending"
            })
        else:
            plans.append({
                "project_id": project_id,
                "category": "Trust",
                "recommendation": "Include third-party security verification badges and user rating widgets (e.g. G2, Trustpilot).",
                "impact_score": 70.0,
                "effort_score": 30.0,
                "estimated_geo_gain": 6.0,
                "status": "pending"
            })

        # 3. Authority Optimization
        if not has_compliance:
            plans.append({
                "project_id": project_id,
                "category": "Authority",
                "recommendation": "Undergo third-party security/compliance audits (ISO 27001, SOC 2 Type II, GDPR) and list credentials.",
                "impact_score": 95.0,
                "effort_score": 85.0,
                "estimated_geo_gain": 15.0,
                "status": "pending"
            })
        else:
            plans.append({
                "project_id": project_id,
                "category": "Authority",
                "recommendation": "Publish detailed verification compliance white papers citing standards enforcement.",
                "impact_score": 75.0,
                "effort_score": 55.0,
                "estimated_geo_gain": 7.0,
                "status": "pending"
            })

        # 4. Schema Markup Optimization
        all_text = " ".join([p.get("markdown_content", "") for p in crawled_pages]).lower()
        has_schema = "application/ld+json" in all_text
        if not has_schema:
            plans.append({
                "project_id": project_id,
                "category": "Schema",
                "recommendation": "Embed structured JSON-LD Schema markups detailing Organization, Product, FAQ, and Case Studies.",
                "impact_score": 85.0,
                "effort_score": 25.0,
                "estimated_geo_gain": 10.0,
                "status": "pending"
            })
        else:
            plans.append({
                "project_id": project_id,
                "category": "Schema",
                "recommendation": "Validate structured schema markup and add reciprocal 'sameAs' social authority references.",
                "impact_score": 60.0,
                "effort_score": 20.0,
                "estimated_geo_gain": 4.0,
                "status": "pending"
            })

        # 5. Internal Links
        if len(crawled_pages) < 8:
            plans.append({
                "project_id": project_id,
                "category": "Internal Links",
                "recommendation": "Build a comprehensive internal site navigation structure pointing link equity to core service pages.",
                "impact_score": 70.0,
                "effort_score": 35.0,
                "estimated_geo_gain": 5.5,
                "status": "pending"
            })
        else:
            plans.append({
                "project_id": project_id,
                "category": "Internal Links",
                "recommendation": "Audit internal linking anchor text ratios to feature exact-match semantic concepts.",
                "impact_score": 55.0,
                "effort_score": 25.0,
                "estimated_geo_gain": 3.0,
                "status": "pending"
            })

        # 6. FAQ Optimization
        if len(questions) < 12:
            plans.append({
                "project_id": project_id,
                "category": "FAQ",
                "recommendation": "Publish structured FAQ panels matching informational search queries on key landing pages.",
                "impact_score": 80.0,
                "effort_score": 30.0,
                "estimated_geo_gain": 8.0,
                "status": "pending"
            })
        else:
            plans.append({
                "project_id": project_id,
                "category": "FAQ",
                "recommendation": "Expand question answering layouts with direct, conversational answers suitable for AI indexing.",
                "impact_score": 65.0,
                "effort_score": 25.0,
                "estimated_geo_gain": 5.0,
                "status": "pending"
            })

        # 7. Questions Coverage
        plans.append({
            "project_id": project_id,
            "category": "Questions",
            "recommendation": "Refactor header H2/H3 tags to explicitly pose conversational search questions.",
            "impact_score": 75.0,
            "effort_score": 30.0,
            "estimated_geo_gain": 7.5,
            "status": "pending"
        })

        # 8. Keywords Optimization
        plans.append({
            "project_id": project_id,
            "category": "Keywords",
            "recommendation": "Integrate high-relevance semantic long-tail keywords in first-paragraph and conclusion sections.",
            "impact_score": 70.0,
            "effort_score": 35.0,
            "estimated_geo_gain": 6.5,
            "status": "pending"
        })

        # 9. Entities Integration
        if len(entity_nodes) < 12:
            plans.append({
                "project_id": project_id,
                "category": "Entities",
                "recommendation": "Inject explicit co-occurrences of industry entities (competitors, standards, partners) in content bodies.",
                "impact_score": 65.0,
                "effort_score": 45.0,
                "estimated_geo_gain": 6.0,
                "status": "pending"
            })
        else:
            plans.append({
                "project_id": project_id,
                "category": "Entities",
                "recommendation": "Strengthen entity graph links by specifying exact industry association and category descriptions.",
                "impact_score": 50.0,
                "effort_score": 35.0,
                "estimated_geo_gain": 3.5,
                "status": "pending"
            })

        # 10. Evidence Grounding
        if len(verified_facts) < 10:
            plans.append({
                "project_id": project_id,
                "category": "Evidence",
                "recommendation": "Compile list pages referencing verified performance numbers, client statistics, and peer benchmark tests.",
                "impact_score": 90.0,
                "effort_score": 55.0,
                "estimated_geo_gain": 11.0,
                "status": "pending"
            })
        else:
            plans.append({
                "project_id": project_id,
                "category": "Evidence",
                "recommendation": "Consolidate fact sheets with direct link references to authoritative audits or external documents.",
                "impact_score": 75.0,
                "effort_score": 45.0,
                "estimated_geo_gain": 6.5,
                "status": "pending"
            })

        # 11. Competitors Comparison
        if len(competitors) > 0:
            plans.append({
                "project_id": project_id,
                "category": "Competitors",
                "recommendation": "Create comprehensive direct comparison landing pages detailing feature-by-feature audits against competitors.",
                "impact_score": 80.0,
                "effort_score": 60.0,
                "estimated_geo_gain": 9.0,
                "status": "pending"
            })
        else:
            plans.append({
                "project_id": project_id,
                "category": "Competitors",
                "recommendation": "Publish differentiation statements and USP benchmarks addressing top competitors in the niche.",
                "impact_score": 65.0,
                "effort_score": 40.0,
                "estimated_geo_gain": 5.0,
                "status": "pending"
            })

        # Calculate priority score: (Impact * 0.7) + ((100 - Effort) * 0.3)
        for plan in plans:
            impact = plan["impact_score"]
            effort = plan["effort_score"]
            plan["priority_score"] = round((impact * 0.7) + ((100.0 - effort) * 0.3), 1)

        try:
            # Clear previous optimization plans for this project
            supabase_client.table("optimization_plans").delete().eq("project_id", project_id).execute()
            supabase_client.table("optimization_plans").insert(plans).execute()
            logger.info(f"Successfully saved {len(plans)} optimization plans.")
        except Exception as e:
            logger.error(f"Error persisting optimization plans: {e}")

        return plans
