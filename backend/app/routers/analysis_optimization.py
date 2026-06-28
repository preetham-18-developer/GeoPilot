from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from app.core.quality_auditor import QuestionQualityAuditor, KeywordQualityAuditor
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.core.supabase import supabase_client
from app.core.dependencies import get_current_user
from app.crawler.spider import WebsiteSpider
from app.agents.graph import run_analysis_pipeline
from app.core.recommendation_engine import RecommendationEngineV2
from app.core.hallucination_detector import HallucinationDetector
from app.core.consistency_engine import KnowledgeConsistencyEngine
from app.core.reality_checker import RealityChecker
from app.core.benchmark_engine import CompetitorBenchmarkEngine
from app.core.historical_tracker import HistoricalTracker
from app.core.cache import get_cached_data, set_cached_data, invalidate_project_cache
from app.core.explainability_engine import ExplainabilityEngine
import logging
from app.routers.analysis_reliability import _get_project_data_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


class OptimizationHistoryInput(BaseModel):
    recommendation: str
    status: str # 'executed', 'ignored'

@router.get("/optimization-plan/{project_id}")
def get_optimization_plan(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Retrieves autonomous optimization plans for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "optimization_plan")
        if cached is not None:
            return cached

        resp = supabase_client.table("optimization_plans")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("priority_score", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "optimization_plan", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching optimization plans for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/roi-report/{project_id}")
def get_roi_report(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Retrieves ROI analyses for strategic recommendations."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "roi_report")
        if cached is not None:
            return cached

        resp = supabase_client.table("roi_reports")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("roi_score", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "roi_report", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ROI reports for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategy-roadmap/{project_id}")
def get_strategy_roadmap(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Generates the 30-60-90 day strategic optimization roadmap."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "strategy_roadmap")
        if cached is not None:
            return cached

        # Fetch active plans to pass to the engine
        plans_resp = supabase_client.table("optimization_plans")\
            .select("*")\
            .eq("project_id", project_id)\
            .execute()
        plans = plans_resp.data or []

        from app.core.strategy_engine import StrategyEngine
        engine = StrategyEngine()
        result = engine.run(project_id, plans)

        set_cached_data(project_id, "strategy_roadmap", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating strategy roadmap for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimization-reasoning/{project_id}")
def get_optimization_reasoning(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Generates explainability cards explaining why each recommendation matters."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "optimization_reasoning")
        if cached is not None:
            return cached

        # Fetch plans
        plans_resp = supabase_client.table("optimization_plans")\
            .select("*")\
            .eq("project_id", project_id)\
            .execute()
        plans = plans_resp.data or []

        from app.core.optimization_reasoning_engine import OptimizationReasoningEngine
        engine = OptimizationReasoningEngine()
        result = engine.run(project_id, plans)

        set_cached_data(project_id, "optimization_reasoning", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating optimization reasoning for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimization-history/{project_id}")
def accept_and_add_to_history(
    project_id: str,
    input_data: OptimizationHistoryInput,
    user_id: str = Depends(get_current_user)
):
    """Accepts an optimization action item, updates its status, and logs it in history."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        # 1. Update optimization_plans status
        supabase_client.table("optimization_plans")\
            .update({"status": "accepted" if input_data.status == "executed" else "completed"})\
            .eq("project_id", project_id)\
            .eq("recommendation", input_data.recommendation)\
            .execute()

        # 2. Insert into optimization_history
        history_resp = supabase_client.table("optimization_history").insert({
            "project_id": project_id,
            "recommendation": input_data.recommendation,
            "status": input_data.status
        }).execute()

        # 3. Invalidate relevant caches
        invalidate_project_cache(project_id)

        # Re-run projection simulation based on newly accepted items
        payload = _get_project_data_payload(project_id)
        plans_resp = supabase_client.table("optimization_plans")\
            .select("*")\
            .eq("project_id", project_id)\
            .execute()
        plans = plans_resp.data or []

        from app.core.geo_projection_engine import GEOProjectionEngine
        proj_eng = GEOProjectionEngine()
        proj_eng.run(project_id, payload, plans)

        return {"status": "success", "data": history_resp.data[0] if (history_resp.data and len(history_resp.data) > 0) else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging optimization history for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# PHASE 11: AUTONOMOUS GEO EXECUTION ENDPOINTS
# =========================================================================


