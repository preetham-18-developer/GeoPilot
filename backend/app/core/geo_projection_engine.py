"""
geo_projection_engine.py
Phase 10 — GEO Projection Engine
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client
from app.core.geo_readiness_engine import GEOReadinessEngine

logger = logging.getLogger(__name__)

class GEOProjectionEngine:
    """
    Simulates before vs after GEO readiness scores, projected gains, and confidence ratings.
    """

    def run(self, project_id: str, payload: Dict[str, Any], plans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Runs the GEO projection simulations, saves the simulation, and returns it.
        """
        # 1. Compute current GEO score
        geo_readiness_engine = GEOReadinessEngine()
        current_readiness = geo_readiness_engine.run(project_id, payload)
        current_score = current_readiness.get("geo_readiness_score", 50.0)

        # 2. Compute projected score based on pending plans
        # Find sum of estimated_geo_gain for pending recommendations
        pending_plans = [p for p in plans if p.get("status", "pending") != "completed"]
        estimated_total_gain = sum(p.get("estimated_geo_gain", 0.0) for p in pending_plans)

        projected_score = min(100.0, current_score + estimated_total_gain)
        expected_gain = round(projected_score - current_score, 1)

        # 3. Confidence score: Function of crawled page count and evidence density
        crawled_pages = payload.get("crawled_pages", []) or []
        verified_facts = payload.get("verified_facts", []) or []
        
        # Scale confidence based on facts and pages
        page_factor = min(1.0, len(crawled_pages) / 10.0) # Max confidence at 10+ pages
        fact_factor = min(1.0, len(verified_facts) / 15.0) # Max confidence at 15+ facts
        confidence_val = round(60.0 + (page_factor * 20.0) + (fact_factor * 20.0), 1)

        simulation = {
            "project_id": project_id,
            "current_geo_score": current_score,
            "projected_geo_score": projected_score,
            "expected_gain": expected_gain,
            "confidence": confidence_val
        }

        try:
            # Clear previous strategy simulations
            supabase_client.table("strategy_simulations").delete().eq("project_id", project_id).execute()
            supabase_client.table("strategy_simulations").insert(simulation).execute()
            logger.info(f"Successfully saved GEO strategy simulation for project {project_id}.")
        except Exception as e:
            logger.error(f"Error persisting strategy simulation: {e}")

        return simulation
