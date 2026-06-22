"""
opportunity_engine_v2.py
Phase 6 — Opportunity Engine V2

Processes query categories with weak coverage (< 50%) from the heatmap
and generates high-impact, actionable recommended opportunities in content_opportunities_v2.
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class OpportunityEngineV2:
    """
    Translates query coverage heatmap weaknesses into concrete content and structural opportunities.
    """

    OPPORTUNITY_TEMPLATES = {
        "Direct": {
            "opportunity": "Optimize primary brand landing page structure.",
            "actions": ["Add corporate details to the home page.", "Create a dedicated Contact page with full company details."],
            "impact": 80, "effort": 15
        },
        "Problem": {
            "opportunity": "Build a technical troubleshooting knowledge hub.",
            "actions": ["Draft guides addressing common product errors.", "Add troubleshooting steps to FAQs."],
            "impact": 85, "effort": 30
        },
        "Outcome": {
            "opportunity": "Publish brand case studies and success metrics.",
            "actions": ["Add customer ROI metrics to the home page.", "Publish detailed client success stories."],
            "impact": 90, "effort": 40
        },
        "Solution": {
            "opportunity": "Clarify system solution features and details.",
            "actions": ["Define product features clearly on the primary services page.", "Add a features comparison matrix."],
            "impact": 85, "effort": 25
        },
        "Decision": {
            "opportunity": "Build comparison pages relative to major competitors.",
            "actions": ["Draft comparison blogs detailing service differences.", "Publish an alternative solutions overview chart."],
            "impact": 92, "effort": 35
        },
        "Voice": {
            "opportunity": "Adopt natural, conversational phrasing in copy.",
            "actions": ["Re-phrase technical specs into simple sentences.", "Answer questions using short, direct statements."],
            "impact": 78, "effort": 20
        },
        "Trust": {
            "opportunity": "Incorporate security standards and compliance factors.",
            "actions": ["Add security certifications badges to the page footer.", "Draft a comprehensive privacy policy page."],
            "impact": 88, "effort": 20
        },
        "Urgent": {
            "opportunity": "Highlight quick-start guides and rapid setups.",
            "actions": ["Publish a 5-minute quick start setup guide.", "Add instant quote forms to the landing page."],
            "impact": 75, "effort": 25
        },
        "Budget": {
            "opportunity": "Publish explicit product pricing tables.",
            "actions": ["Create a pricing/fees details page.", "Add cost-related FAQs to the site.", "Publish budget-friendly plan breakdowns."],
            "impact": 92, "effort": 28
        },
        "Beginner": {
            "opportunity": "Develop basic step-by-step introduction content.",
            "actions": ["Draft simple introduction articles.", "Add beginner-friendly terms glossary."],
            "impact": 80, "effort": 30
        },
        "Expert": {
            "opportunity": "Publish technical whitepapers and deep dives.",
            "actions": ["Write expert developer guides.", "Share system architecture diagrams in blogs."],
            "impact": 82, "effort": 45
        },
        "Enterprise": {
            "opportunity": "Draft enterprise-scale features guidelines.",
            "actions": ["Create an Enterprise Solution page detailing multi-tenant details.", "Outline corporate SLA specifications."],
            "impact": 95, "effort": 50
        },
        "Location": {
            "opportunity": "Optimize pages for regional search queries.",
            "actions": ["Add physical office address citations.", "Create local service landing pages."],
            "impact": 85, "effort": 20
        },
        "AI Search": {
            "opportunity": "Format facts for AI recommendation extraction.",
            "actions": ["Structure product specs in simple HTML table blocks.", "Avoid complex jargon in service claims."],
            "impact": 88, "effort": 25
        },
        "Role-Based": {
            "opportunity": "Develop role-specific landing guides.",
            "actions": ["Create guides tailored for managers.", "Create feature outlines for developers."],
            "impact": 85, "effort": 35
        },
        "Scenario-Based": {
            "opportunity": "Draft scenario guides answering situational queries.",
            "actions": ["Add 'how-to' scenario breakdowns.", "Write guides addressing recovery plans during outages."],
            "impact": 80, "effort": 35
        },
        "Need-Based": {
            "opportunity": "Highlight customized pricing and feature selections.",
            "actions": ["Build interactive product calculators.", "Implement service selection guides."],
            "impact": 82, "effort": 30
        },
        "Pain Point": {
            "opportunity": "Highlight solutions addressing direct customer pain points.",
            "actions": ["Draft copy focusing on speed and cost reduction benefits.", "Address complex setup mitigations explicitly."],
            "impact": 88, "effort": 25
        },
        "Natural Language": {
            "opportunity": "Refine headers to match conversational queries.",
            "actions": ["Rephrase headers as full questions (Who, What, How).", "Write direct answer blocks below headers."],
            "impact": 84, "effort": 15
        },
        "Conversational": {
            "opportunity": "Incorporate conversational keywords in body copy.",
            "actions": ["Answer FAQs in friendly, conversational sentences.", "Draft conversational blog outlines."],
            "impact": 78, "effort": 20
        }
    }

    def run(self, project_id: str, current_run_id: str, heatmap_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Processes query coverage scores, extracts weak and missing categories,
        and generates actionable items into content_opportunities_v2.
        """
        weak_cats = heatmap_data.get("weak_categories", []) or []
        missing_cats = heatmap_data.get("missing_categories", []) or []
        category_scores = heatmap_data.get("category_scores", {}) or {}
        
        target_categories = list(set(weak_cats + missing_cats))
        opportunities = []
        
        for cat in target_categories:
            score = float(category_scores.get(cat, 0.0))
            template = self.OPPORTUNITY_TEMPLATES.get(cat)
            if not template:
                continue
                
            priority = "HIGH" if score < 30.0 else "MEDIUM"
            opp = {
                "project_id": project_id,
                "run_id": current_run_id,
                "category": cat,
                "current_coverage": score,
                "opportunity": template["opportunity"],
                "recommended_actions": template["actions"],
                "priority": priority,
                "impact_score": template["impact"],
                "effort_score": template["effort"]
            }
            opportunities.append(opp)

        if opportunities:
            try:
                supabase_client.table("content_opportunities_v2").insert(opportunities).execute()
                logger.info(f"Generated {len(opportunities)} V2 content opportunities for project {project_id}.")
            except Exception as e:
                logger.error(f"Error persisting content opportunities v2: {e}")
                
        return opportunities
