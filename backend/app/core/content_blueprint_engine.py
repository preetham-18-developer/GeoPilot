"""
content_blueprint_engine.py
Phase 7 — Content Blueprint Engine

Generates highly targeted specifications for new content pieces (Blogs, FAQ, Guides, etc.).
Assigns schemas, keywords, questions, internal link pointers, impact, and effort scores.
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class ContentBlueprintEngine:
    """
    Generates action-ready content blueprints mapping keywords, FAQs, and link structures.
    """

    BLUEPRINT_TEMPLATES = {
        "Budget": {
            "page_type": "Comparison",
            "title_tmpl": "Cost and Pricing Comparison Guide for {industry} Solutions",
            "slug": "pricing-comparison-guide",
            "intent": "commercial",
            "schema": "Product",
            "impact": 92, "effort": 28,
            "benefit": "Captures transactional queries related to software licensing costs and plan pricing details."
        },
        "Trust": {
            "page_type": "Case Study",
            "title_tmpl": "How {company_name} Assisted Clients in Achieving Security Compliance",
            "slug": "customer-security-compliance-case-study",
            "intent": "commercial",
            "schema": "NewsArticle",
            "impact": 88, "effort": 35,
            "benefit": "Strengthens brand trust signals and user conversion rates through verified client performance stats."
        },
        "Problem": {
            "page_type": "FAQ",
            "title_tmpl": "Common Troubleshooting and Solution FAQs for {industry}",
            "slug": "technical-faq-troubleshooting",
            "intent": "informational",
            "schema": "FAQPage",
            "impact": 85, "effort": 20,
            "benefit": "Captures problem-related voice searches, reducing support ticket volume by answering technical FAQs directly."
        },
        "Beginner": {
            "page_type": "Tutorial",
            "title_tmpl": "Step-by-Step Introduction and Beginner's Guide to {industry}",
            "slug": "beginners-guide-introduction",
            "intent": "informational",
            "schema": "HowTo",
            "impact": 80, "effort": 30,
            "benefit": "Builds top-of-funnel brand visibility for users exploring basic introductory concepts."
        },
        "Expert": {
            "page_type": "Guide",
            "title_tmpl": "Advanced System Architecture and Expert Guide for {industry}",
            "slug": "advanced-system-architecture-guide",
            "intent": "informational",
            "schema": "TechArticle",
            "impact": 82, "effort": 45,
            "benefit": "Establishes technical authority and expert content credentials in developer search lists."
        },
        "Decision": {
            "page_type": "Comparison",
            "title_tmpl": "Acme SaaS vs Competitors: Features, Parity, and Differentiation",
            "slug": "competitor-feature-matrix-comparison",
            "intent": "commercial",
            "schema": "Product",
            "impact": 95, "effort": 38,
            "benefit": "Helps clients capture decision-stage comparisons when comparing your product with competitors."
        }
    }

    def run(self, project_id: str, current_run_id: str, payload: Dict[str, Any], heatmap_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Translates weak intent heatmap categories into content blueprints,
        persists them in content_blueprints table, and returns them.
        """
        weak_cats = heatmap_data.get("weak_categories", []) or []
        missing_cats = heatmap_data.get("missing_categories", []) or []
        target_cats = list(set(weak_cats + missing_cats))

        if not target_cats:
            # Fallback to default categories if site is already strong
            target_cats = ["Budget", "Trust", "Problem"]

        keywords = payload.get("keywords", []) or []
        questions = payload.get("questions", []) or []
        crawled_pages = payload.get("crawled_pages", []) or []
        business_profile = payload.get("business_profile", {}) or {}

        company_name = business_profile.get("company_name", "Brand Solutions")
        industry = business_profile.get("industry", "Technology")

        blueprints = []
        for cat in target_cats[:4]: # Limit to top 4 blueprints per run
            template = self.BLUEPRINT_TEMPLATES.get(cat)
            if not template:
                # Default fallback template for other categories
                template = {
                    "page_type": "Blog",
                    "title_tmpl": f"Optimizing {{industry}} Services: A Complete Guide",
                    "slug": f"optimizing-{cat.lower().replace(' ', '-')}-guide",
                    "intent": "informational",
                    "schema": "Article",
                    "impact": 75, "effort": 25,
                    "benefit": f"Improves coverage for conversational search queries categorized under {cat}."
                }

            title = template["title_tmpl"].format(company_name=company_name, industry=industry)
            
            # Map keywords/questions
            bp_kws = [k.get("keyword", "") for k in keywords if cat.lower() in k.get("keyword", "").lower()][:4]
            if not bp_kws:
                bp_kws = [k.get("keyword", "") for k in keywords[:3]]

            bp_qs = [q.get("question", "") for q in questions if cat.lower() in q.get("question", "").lower()][:3]
            if not bp_qs:
                bp_qs = [q.get("question", "") for q in questions[:2]]

            # Map internal links
            suggested_links = []
            for p in crawled_pages[:2]:
                suggested_links.append(p.get("url", ""))

            priority = "HIGH" if template["impact"] - template["effort"] > 50 else "MEDIUM"
            
            bp = {
                "project_id": project_id,
                "run_id": current_run_id,
                "page_type": template["page_type"],
                "title": title,
                "slug": template["slug"],
                "target_intent": template["intent"],
                "questions": bp_qs,
                "keywords": bp_kws,
                "entities": [company_name, industry],
                "suggested_internal_links": suggested_links,
                "schema_type": template["schema"],
                "priority": priority,
                "impact_score": template["impact"],
                "effort_score": template["effort"],
                "expected_benefit": template["benefit"]
            }
            blueprints.append(bp)

        if blueprints:
            try:
                supabase_client.table("content_blueprints").insert(blueprints).execute()
                logger.info(f"Persisted {len(blueprints)} content blueprints for project {project_id}.")
            except Exception as e:
                logger.error(f"Error persisting content blueprints: {e}")

        return blueprints
