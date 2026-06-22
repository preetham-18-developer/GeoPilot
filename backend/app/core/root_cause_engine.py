"""
root_cause_engine.py
Phase 6 — Root Cause Engine

Analyzes the exact reasons behind score changes between consecutive runs.
Traces issues to affected agent modules and recommends concrete repair procedures.
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class RootCauseEngine:
    """
    Identifies root causes of metric changes and maps them to responsible LangGraph agents.
    """

    def run(self, project_id: str, current_run_id: str, current_scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Calculates changes between current and previous run metrics, generates explainable root causes,
        persists reports in root_cause_reports, and returns them.
        """
        reports = []
        try:
            # 1. Fetch previous run row
            resp = supabase_client.table("historical_metrics")\
                .select("*")\
                .eq("project_id", project_id)\
                .order("created_at", desc=True)\
                .limit(2)\
                .execute()
                
            if not resp.data or len(resp.data) < 2:
                logger.info("Not enough historical runs to compute root causes.")
                return []
                
            prev = resp.data[1]
            
            # Helper to check score details
            prev_vis = float(prev.get("visibility_score") or 0.0)
            curr_vis = float(current_scores.get("visibility_score") or 0.0)
            vis_delta = curr_vis - prev_vis

            prev_rec = float(prev.get("recommendation_score") or 0.0)
            curr_rec = float(current_scores.get("recommendation_score") or 0.0)
            rec_delta = curr_rec - prev_rec

            prev_cons = float(prev.get("consistency_score") or 0.0)
            curr_cons = float(current_scores.get("consistency_score") or 0.0)
            cons_delta = curr_cons - prev_cons

            prev_hal = float(prev.get("hallucination_score") or 100.0)
            curr_hal = float(current_scores.get("hallucination_score") or 100.0)
            hal_delta = curr_hal - prev_hal # Inverted. A drop in hallucination_score = increase in hallucination risk.

            # We trace and report any negative changes
            root_causes = []

            # 1. Trace Visibility Drop
            if vis_delta < -0.1:
                severity = "HIGH" if vis_delta <= -10.0 else "MEDIUM" if vis_delta <= -4.0 else "LOW"
                cause = "FAQ coverage decreased."
                affected_agents = ["Question Discovery Agent", "Crawler Agent"]
                repairs = [
                    "Implement a schema-compliant FAQ page containing direct conversational answers.",
                    "Verify the crawler is successfully parsing structured body tags."
                ]
                
                # Check page difference if possible
                prev_pages = float(prev.get("coverage_score") or 0.0)
                curr_pages = float(current_scores.get("coverage_score") or 0.0)
                if curr_pages < prev_pages:
                    cause = "Fewer crawlable content pages parsed by the spider."
                    affected_agents = ["Crawler Agent"]
                    repairs = [
                        "Check for broken links or redirects in your sitemap.",
                        "Confirm the server is not blocking the crawler's User-Agent."
                    ]
                    
                root_causes.append({
                    "metric_name": "Visibility Score",
                    "score_change": round(vis_delta, 1),
                    "severity": severity,
                    "cause": cause,
                    "affected_agents": affected_agents,
                    "repair_suggestions": repairs
                })

            # 2. Trace Recommendation Drop
            if rec_delta < -0.1:
                severity = "HIGH" if rec_delta <= -10.0 else "MEDIUM" if rec_delta <= -4.0 else "LOW"
                cause = "Commercial keyword coverage dropped."
                affected_agents = ["Keyword Agent", "Competitor Agent"]
                repairs = [
                    "Optimize top service pages for commercial search intents (cost, features, compare).",
                    "Add detailed product differentiation matrices to resolve competitor overlap."
                ]
                
                # Check keyword quality difference
                prev_kw_q = float(prev.get("keyword_quality") or 0.0)
                curr_kw_q = float(current_scores.get("keyword_quality") or 0.0)
                if curr_kw_q < prev_kw_q:
                    cause = "Average recommendation value of tracked keywords deteriorated."
                    affected_agents = ["Keyword Agent"]
                    repairs = [
                        "Perform long-tail keyword research focusing on specific buyer personas.",
                        "Re-cluster keywords under high-relevance intent categories."
                    ]
                    
                root_causes.append({
                    "metric_name": "Recommendation Score",
                    "score_change": round(rec_delta, 1),
                    "severity": severity,
                    "cause": cause,
                    "affected_agents": affected_agents,
                    "repair_suggestions": repairs
                })

            # 3. Trace Consistency Drop
            if cons_delta < -0.1:
                severity = "HIGH" if cons_delta <= -10.0 else "MEDIUM" if cons_delta <= -4.0 else "LOW"
                root_causes.append({
                    "metric_name": "Consistency Score",
                    "score_change": round(cons_delta, 1),
                    "severity": severity,
                    "cause": "Contradiction between Business Intelligence findings and the extracted Entity Graph.",
                    "affected_agents": ["Extraction Agent", "Business Intelligence Agent", "Verification Agent"],
                    "repair_suggestions": [
                        "Audit page copy to ensure product names, pricing, and specs are identical across references.",
                        "Re-verify contradictory node linkages in the Entity editor."
                    ]
                })

            # 4. Trace Hallucination Score Drop (Risk Increase)
            if hal_delta < -0.1:
                severity = "HIGH" if hal_delta <= -10.0 else "MEDIUM" if hal_delta <= -4.0 else "LOW"
                root_causes.append({
                    "metric_name": "Hallucination Risk",
                    "score_change": round(abs(hal_delta), 1), # Store positive value representing the risk change
                    "severity": severity,
                    "cause": "Generated content contains unsupported claims or ungrounded statistics.",
                    "affected_agents": ["Content Agent", "Verification Agent"],
                    "repair_suggestions": [
                        "Attach explicit URL source citations to all product benefit claims.",
                        "Remove highly promotional superlatives not backed by technical specifications."
                    ]
                })

            # Save in database
            if root_causes:
                insert_payload = []
                for rc in root_causes:
                    item = {
                        "project_id": project_id,
                        "run_id": current_run_id,
                        "metric_name": rc["metric_name"],
                        "score_change": rc["score_change"],
                        "severity": rc["severity"],
                        "cause": rc["cause"],
                        "affected_agents": rc["affected_agents"],
                        "repair_suggestions": rc["repair_suggestions"]
                    }
                    insert_payload.append(item)
                    reports.append(item)
                    
                supabase_client.table("root_cause_reports").insert(insert_payload).execute()
                logger.info(f"Persisted {len(insert_payload)} root cause reports for project {project_id}.")

        except Exception as e:
            logger.error(f"Error running root cause engine: {e}")
            
        return reports
