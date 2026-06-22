"""
regression_engine.py
Phase 6 — Regression Detection Engine

Compares the current run scores against the previous run scores.
Detects drops and generates alerts with severity, reasons, impacts, and recommended fixes.
"""

from typing import Dict, Any, List, Optional
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class RegressionEngine:
    """
    Detects metric regressions by comparing current scores against the project's previous run.
    """

    METRIC_REPAIR_MAP = {
        "Visibility Score": {
            "reason": "Lower coverage of primary keywords or missing structured JSON-LD data.",
            "impact": "Decreased brand visibility in conversational LLM results (ChatGPT/Gemini).",
            "fix": "Implement structured JSON-LD schemas and check crawl logs for failed pages."
        },
        "Recommendation Score": {
            "reason": "Decline in USP grounding or loss of service page references.",
            "impact": "AI search engines are less likely to select your business as a top recommendation.",
            "fix": "Add detailed customer case studies and link testimonials to source URLs."
        },
        "Grounding Score": {
            "reason": "New facts were added that cannot be verified by page contents.",
            "impact": "Increased possibility of AI search hallucinating false facts about your services.",
            "fix": "Review extracted facts and remove claims not explicitly backed by page copy."
        },
        "Consistency Score": {
            "reason": "Conflicting claims detected between pages or with the knowledge graph.",
            "impact": "AI recommendation systems lose confidence in your data due to conflicting messages.",
            "fix": "Synchronize services, pricing, and specs across all main pages."
        },
        "Hallucination Risk": {
            "reason": "AI crawler discovered content that contains unverified claims.",
            "impact": "Higher risk of brand reputation damage due to AI presenting inaccurate information.",
            "fix": "Re-verify claims in the compliance editor and update underlying source articles."
        },
        "Content Coverage": {
            "reason": "Average index coverage of site pages has declined.",
            "impact": "LLM search engines lack deep context to pull from, leading to generic summaries.",
            "fix": "Publish missing educational guides and expand on thin content pages."
        },
        "Question Quality": {
            "reason": "Fewer questions are answered in depth in the current site structure.",
            "impact": "Lost organic reach for users querying informational search phrases.",
            "fix": "Build a comprehensive FAQ page answering commercial intent queries."
        },
        "Keyword Quality": {
            "reason": "Tracking shifts toward low-intent, highly competitive keywords.",
            "impact": "Lower conversion potential from AI search referrals.",
            "fix": "Refocus content optimization on high-intent long-tail keywords."
        }
    }

    def run(self, project_id: str, current_run_id: str, current_scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Retrieves the previous run metrics from historical_metrics, calculates changes,
        logs regressions into regression_reports, and returns the warnings.
        """
        warnings = []
        try:
            # 1. Fetch the previous run metrics
            resp = supabase_client.table("historical_metrics")\
                .select("*")\
                .eq("project_id", project_id)\
                .order("created_at", desc=True)\
                .limit(2)\
                .execute()
            
            # Since we just inserted the current run in graph.py, the previous run will be the second item
            if not resp.data or len(resp.data) < 2:
                logger.info("Not enough historical runs to detect regressions.")
                return []
                
            prev = resp.data[1]  # The previous run row
            
            # Map DB fields to metric display names
            metrics_mapping = [
                ("Visibility Score", prev.get("visibility_score", 0.0), current_scores.get("visibility_score", 0.0), True),
                ("Recommendation Score", prev.get("recommendation_score", 0.0), current_scores.get("recommendation_score", 0.0), True),
                ("Grounding Score", prev.get("grounding_score", 100.0), current_scores.get("grounding_score", 100.0), True),
                ("Consistency Score", prev.get("consistency_score", 100.0), current_scores.get("consistency_score", 100.0), True),
                # Note: Hallucination Risk is inverted. The risk value is 100 - score.
                ("Hallucination Risk", 100.0 - prev.get("hallucination_score", 100.0), 100.0 - current_scores.get("hallucination_score", 100.0), False),
                ("Content Coverage", prev.get("coverage_score", 0.0), current_scores.get("coverage_score", 0.0), True),
                ("Question Quality", prev.get("question_quality", 0.0), current_scores.get("question_quality", 0.0), True),
                ("Keyword Quality", prev.get("keyword_quality", 0.0), current_scores.get("keyword_quality", 0.0), True),
            ]

            regression_inserts = []
            for name, prev_val, curr_val, is_higher_better in metrics_mapping:
                prev_val = float(prev_val or 0.0)
                curr_val = float(curr_val or 0.0)
                
                # Check for drop
                if is_higher_better:
                    drop = prev_val - curr_val
                else:
                    # For Hallucination Risk, a HIGHER value is worse, so check if current > previous
                    drop = curr_val - prev_val

                if drop > 0.1: # Significant drop
                    severity = "HIGH" if drop >= 15.0 else "MEDIUM" if drop >= 5.0 else "LOW"
                    metadata = self.METRIC_REPAIR_MAP.get(name, {
                        "reason": f"{name} deteriorated in this run.",
                        "impact": f"Reduced effectiveness of {name} strategy.",
                        "fix": "Investigate source text changes and re-run analysis."
                    })
                    
                    rep = {
                        "project_id": project_id,
                        "run_id": current_run_id,
                        "metric_name": name,
                        "previous_value": round(prev_val, 1),
                        "current_value": round(curr_val, 1),
                        "drop_value": round(drop, 1),
                        "severity": severity,
                        "reason": metadata["reason"],
                        "impact": metadata["impact"],
                        "recommended_fix": metadata["fix"]
                    }
                    regression_inserts.append(rep)
                    warnings.append(rep)

            if regression_inserts:
                supabase_client.table("regression_reports").insert(regression_inserts).execute()
                logger.info(f"Inserted {len(regression_inserts)} regression reports for project {project_id}.")
                
        except Exception as e:
            logger.error(f"Error running regression engine: {e}")
            
        return warnings
