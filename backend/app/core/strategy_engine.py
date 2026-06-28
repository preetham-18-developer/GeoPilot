"""
strategy_engine.py
Phase 10 — Strategy Roadmap Engine
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class StrategyEngine:
    """
    Groups recommendations into Quick Wins, Medium Wins, and Long-Term Wins
    to formulate a 30-60-90 Day strategic roadmap.
    """

    def run(self, project_id: str, plans: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Classifies optimization plans into roadmap milestones.
        """
        if not plans:
            try:
                resp = supabase_client.table("optimization_plans")\
                    .select("*")\
                    .eq("project_id", project_id)\
                    .execute()
                plans = resp.data or []
            except Exception as e:
                logger.error(f"Error fetching plans for strategy roadmap: {e}")
                plans = []

        quick_wins = []
        medium_wins = []
        long_term_wins = []

        for plan in plans:
            impact = plan.get("impact_score", 50.0)
            effort = plan.get("effort_score", 50.0)

            # Define classification
            # Quick Wins: Effort <= 45 and Impact >= 60
            if effort <= 45 and impact >= 60:
                quick_wins.append(plan)
            # Long-Term Wins: Effort > 70
            elif effort > 70:
                long_term_wins.append(plan)
            # Medium Wins: everything else
            else:
                medium_wins.append(plan)

        result = {
            "project_id": project_id,
            "roadmap": {
                "30_days": {
                    "title": "30-Day Quick Wins (High Impact, Low Effort)",
                    "milestones": quick_wins
                },
                "60_days": {
                    "title": "60-Day Core Milestones (Medium Effort)",
                    "milestones": medium_wins
                },
                "90_days": {
                    "title": "90-Day Long-Term Strategic Goals (High Effort)",
                    "milestones": long_term_wins
                }
            }
        }

        return result
