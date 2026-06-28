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


@router.get("/citation-report/{project_id}")
def get_citation_report(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches citation reports for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "citation_report")
        if cached is not None:
            return cached

        resp = supabase_client.table("citation_reports")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "citation_report", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching citation reports for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendation-gaps/{project_id}")
def get_recommendation_gaps(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches recommendation gaps for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "recommendation_gaps")
        if cached is not None:
            return cached

        resp = supabase_client.table("recommendation_gaps")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "recommendation_gaps", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching recommendation gaps for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/authority-sources-v2/{project_id}")
def get_authority_sources_v2(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches discovered authority entities for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "authority_sources_v2")
        if cached is not None:
            return cached

        resp = supabase_client.table("authority_entities")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "authority_sources_v2", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching authority entities for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/competitor-recommendations/{project_id}")
def get_competitor_recommendations(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches competitor recommendation matrix rows for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "competitor_recommendations")
        if cached is not None:
            return cached

        resp = supabase_client.table("recommendation_competitor_analysis")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "competitor_recommendations", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching competitor recommendations for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/citation-reasoning/{project_id}")
def get_citation_reasoning(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Computes and returns explainable citation reasoning cards on the fly."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "citation_reasoning")
        if cached is not None:
            return cached

        payload = _get_project_data_payload(project_id)
        from app.core.citation_reasoning_engine import CitationReasoningEngine
        engine = CitationReasoningEngine()
        result = engine.run(project_id, payload)

        set_cached_data(project_id, "citation_reasoning", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing citation reasoning for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/geo-readiness/{project_id}")
def get_geo_readiness(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Computes and returns the weighted GEO readiness score and breakdown."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "geo_readiness")
        if cached is not None:
            return cached

        payload = _get_project_data_payload(project_id)
        from app.core.geo_readiness_engine import GEOReadinessEngine
        engine = GEOReadinessEngine()
        result = engine.run(project_id, payload)

        set_cached_data(project_id, "geo_readiness", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing geo readiness scoring for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/geo-projection/{project_id}")
def get_geo_projection(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Retrieves simulated before/after GEO readiness score projections."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "geo_projection")
        if cached is not None:
            return cached

        resp = supabase_client.table("strategy_simulations")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()

        result = resp.data[0] if (resp.data and len(resp.data) > 0) else None
        if result:
            set_cached_data(project_id, "geo_projection", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching geo projection for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



