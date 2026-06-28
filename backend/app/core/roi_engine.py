"""
roi_engine.py
Phase 10 — ROI Engine
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class ROIEngine:
    """
    Calculates ROI scores (Impact / Effort) and maps them to categories and explanations.
    """

    def run(self, project_id: str, plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculates ROI reports, saves them to public.roi_reports, and returns them.
        """
        reports = []

        for plan in plans:
            impact = plan.get("impact_score", 50.0)
            effort = plan.get("effort_score", 50.0)
            category = plan.get("category", "General")
            recommendation = plan.get("recommendation", "")

            # ROI Score = Impact / Effort
            roi_val = round(impact / max(1.0, effort), 2)

            # Ranks: Very High, High, Medium, Low
            if roi_val >= 2.0:
                rank = "Very High"
                explanation = f"Implementing this {category} fix gives a Very High Return on Investment since the implementation effort ({effort}) is extremely low relative to its high optimization impact ({impact})."
            elif roi_val >= 1.5:
                rank = "High"
                explanation = f"Implementing this {category} fix gives a High Return on Investment. Effort is moderate ({effort}) but it delivers substantial value ({impact}) toward Generative Engine optimization."
            elif roi_val >= 1.0:
                rank = "Medium"
                explanation = f"Implementing this {category} fix gives a Medium Return on Investment. The effort ({effort}) maps proportionally to the estimated optimization impact ({impact})."
            else:
                rank = "Low"
                explanation = f"Implementing this {category} fix gives a Low Return on Investment. It requires significant technical resources or compliance audit cycles ({effort}) relative to its initial impact ({impact})."

            reports.append({
                "project_id": project_id,
                "category": category,
                "effort": effort,
                "impact": impact,
                "roi_score": roi_val,
                "explanation": f"[{rank}] {explanation} Action item: {recommendation}"
            })

        try:
            # Clear previous ROI reports
            supabase_client.table("roi_reports").delete().eq("project_id", project_id).execute()
            supabase_client.table("roi_reports").insert(reports).execute()
            logger.info(f"Successfully saved {len(reports)} ROI reports.")
        except Exception as e:
            logger.error(f"Error persisting ROI reports: {e}")

        return reports
