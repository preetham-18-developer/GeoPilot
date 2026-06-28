"""
execution_engine.py
Phase 11 — Execution Task Engine
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class ExecutionEngine:
    """
    Converts strategic optimization plan recommendations into structured actionable execution tasks.
    """

    def run(self, project_id: str, plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes optimization plans, converts them to tasks, writes them to execution_tasks, and returns them.
        """
        tasks = []

        # Map plan category to explicit task titles, priority, and descriptions
        for plan in plans:
            category = plan.get("category", "General")
            recommendation = plan.get("recommendation", "")
            impact = plan.get("impact_score", 50.0)
            effort = plan.get("effort_score", 50.0)
            priority_score = plan.get("priority_score", 50.0)

            # Determine priority text
            if priority_score >= 80.0:
                priority = "CRITICAL"
            elif priority_score >= 65.0:
                priority = "HIGH"
            elif priority_score >= 45.0:
                priority = "MEDIUM"
            else:
                priority = "LOW"

            title = f"Optimize {category} - {category} GEO Improvements"
            description = (
                f"Implement strategic recommendation to: '{recommendation}'. "
                f"This optimization directly influences the '{category}' signal categories in Generative Engines, "
                f"bringing an estimated GEO readiness score gain of +{plan.get('estimated_geo_gain', 5.0)}%."
            )

            tasks.append({
                "project_id": project_id,
                "category": category,
                "title": title,
                "description": description,
                "priority": priority,
                "effort_score": effort,
                "impact_score": impact,
                "status": "pending"
            })

        try:
            # Clear previous execution tasks
            supabase_client.table("execution_tasks").delete().eq("project_id", project_id).execute()
            resp = supabase_client.table("execution_tasks").insert(tasks).execute()
            logger.info(f"Successfully saved {len(tasks)} execution tasks.")
            return resp.data or tasks
        except Exception as e:
            logger.error(f"Error persisting execution tasks: {e}")
            return tasks
