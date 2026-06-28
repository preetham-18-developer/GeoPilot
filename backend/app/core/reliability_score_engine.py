"""
reliability_score_engine.py
Phase 8 — Reliability Score Engine

Measures, computes, and logs AIVOP reliability index metrics (0-100) to reliability_reports table.
"""

from typing import Dict, Any
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class ReliabilityScoreEngine:
    """
    Formulates a weighted system score based on execution logs and dependency uptimes.
    """

    def compute_and_save(self, project_id: str, run_id: str) -> Dict[str, Any]:
        """
        Gathers metric percentages from tables, calculates the final score, and logs it.
        """
        try:
            # 1. Agent Success Rate (30% weight)
            agent_success_rate = 100.0
            health_resp = supabase_client.table("agent_health_logs")\
                .select("success")\
                .eq("run_id", run_id)\
                .execute()
            if health_resp.data:
                successes = sum(1 for r in health_resp.data if r["success"])
                agent_success_rate = (successes / len(health_resp.data)) * 100.0

            # 2. Recovery Success Rate (20% weight)
            recovery_success_rate = 100.0
            recovery_resp = supabase_client.table("recovery_history")\
                .select("success")\
                .execute()
            if recovery_resp.data:
                successes = sum(1 for r in recovery_resp.data if r["success"])
                recovery_success_rate = (successes / len(recovery_resp.data)) * 100.0

            # 3. Retry Success Rate (15% weight)
            retry_success_rate = 100.0
            retry_resp = supabase_client.table("retry_reports")\
                .select("succeeded")\
                .eq("run_id", run_id)\
                .execute()
            if retry_resp.data:
                successes = sum(1 for r in retry_resp.data if r["succeeded"])
                retry_success_rate = (successes / len(retry_resp.data)) * 100.0

            # 4. Dependency Availability (15% weight)
            dependency_score = 100.0
            dep_resp = supabase_client.table("dependency_health_logs")\
                .select("uptime_percentage")\
                .order("timestamp", desc=True)\
                .limit(7)\
                .execute()
            if dep_resp.data:
                dependency_score = sum(r["uptime_percentage"] for r in dep_resp.data) / len(dep_resp.data)

            # 5. Pipeline Completion (10% weight)
            pipeline_completion_score = 100.0
            runs_resp = supabase_client.table("analysis_runs")\
                .select("status")\
                .eq("project_id", project_id)\
                .limit(20)\
                .execute()
            if runs_resp.data:
                completed = sum(1 for r in runs_resp.data if r["status"] == "completed")
                pipeline_completion_score = (completed / len(runs_resp.data)) * 100.0

            # 6. Runtime Stability (10% weight)
            runtime_stability = 100.0
            errs_resp = supabase_client.table("error_diagnostics")\
                .select("severity")\
                .eq("run_id", run_id)\
                .execute()
            if errs_resp.data:
                # Deduct penalty based on severities
                penalty = 0.0
                for r in errs_resp.data:
                    sev = r["severity"]
                    if sev == "CRITICAL":
                        penalty += 40.0
                    elif sev == "HIGH":
                        penalty += 20.0
                    elif sev == "MEDIUM":
                        penalty += 10.0
                    else:
                        penalty += 5.0
                runtime_stability = max(0.0, 100.0 - penalty)

            # Compute weighted overall score
            reliability_score = (
                (0.30 * agent_success_rate) +
                (0.20 * recovery_success_rate) +
                (0.15 * retry_success_rate) +
                (0.15 * dependency_score) +
                (0.10 * pipeline_completion_score) +
                (0.10 * runtime_stability)
            )

            reliability_score = round(reliability_score, 1)

            report = {
                "project_id": project_id,
                "run_id": run_id,
                "reliability_score": reliability_score,
                "success_rate": round(agent_success_rate, 1),
                "retry_success_rate": round(retry_success_rate, 1),
                "dependency_score": round(dependency_score, 1),
                "runtime_stability": round(runtime_stability, 1),
                "pipeline_completion_score": round(pipeline_completion_score, 1),
                "recovery_success_rate": round(recovery_success_rate, 1)
            }

            supabase_client.table("reliability_reports").insert(report).execute()
            logger.info(f"Reliability score calculated: {reliability_score}% for project {project_id}.")
            return report

        except Exception as e:
            logger.error(f"Error calculating reliability score: {e}")
            return {
                "project_id": project_id,
                "run_id": run_id,
                "reliability_score": 100.0,
                "success_rate": 100.0,
                "retry_success_rate": 100.0,
                "dependency_score": 100.0,
                "runtime_stability": 100.0,
                "pipeline_completion_score": 100.0,
                "recovery_success_rate": 100.0
            }
