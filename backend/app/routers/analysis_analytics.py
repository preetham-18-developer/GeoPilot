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


@router.get("/competitor-benchmark/{project_id}")
def get_competitor_benchmark(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Runs CompetitorBenchmarkEngine on-demand and returns gap matrix + rankings."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        # Cache check (30 min TTL — heavy computation)
        cached = get_cached_data(project_id, "benchmark_report")
        if cached is not None:
            return cached

        project_data = _get_project_data_payload(project_id)
        engine = CompetitorBenchmarkEngine()
        result = engine.run(project_data)

        # Persist latest benchmark report
        try:
            supabase_client.table("benchmark_reports").delete().eq("project_id", project_id).execute()
            supabase_client.table("benchmark_reports").insert({
                "project_id": project_id,
                "percentile_score": result["percentile_score"],
                "relative_position": result["relative_position"],
                "total_players": result["total_players"],
                "client_overall_score": result["client_overall_score"],
                "gap_matrix": result["gap_matrix"],
                "strengths_rank": result["strengths_rank"],
                "weaknesses_rank": result["weaknesses_rank"],
                "threats_rank": result["threats_rank"],
                "opportunities_rank": result["opportunities_rank"],
            }).execute()
        except Exception as db_err:
            logger.error(f"Error persisting benchmark report: {db_err}")

        set_cached_data(project_id, "benchmark_report", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running competitor benchmark for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# BATCH 4.5 — HISTORICAL METRICS ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/historical-metrics/{project_id}")
def get_historical_metrics(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Returns all historical run metrics, trends, velocity, and regression alerts for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        # Cache check (1 hour TTL — read-only historical data)
        cached = get_cached_data(project_id, "historical_metrics")
        if cached is not None:
            return cached

        rows_resp = supabase_client.table("historical_metrics").select("*").eq(
            "project_id", project_id
        ).order("created_at", desc=False).execute()

        tracker = HistoricalTracker()
        result = tracker.calculate_trends(rows_resp.data or [])
        set_cached_data(project_id, "historical_metrics", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching historical metrics for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 6 — ADVANCED DIAGNOSTICS & EXPLAINABILITY ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/analytics/{project_id}")
def get_advanced_analytics(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Returns longitudinal analytics, before-vs-after comparison cards, and explainability breakdowns."""
    try:
        # Auth check
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "analytics")
        if cached is not None:
            return cached

        # 1. Fetch historical metrics rows
        rows_resp = supabase_client.table("historical_metrics")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=False)\
            .execute()
            
        rows = rows_resp.data or []
        
        # 2. Run historical trend analysis
        tracker = HistoricalTracker()
        trends_analysis = tracker.calculate_trends(rows)
        
        # 3. Compute Before vs After engine details
        before_after_cards = []
        explainability = {}
        
        if len(rows) >= 1:
            latest = rows[-1]
            prev = rows[-2] if len(rows) >= 2 else None
            
            # Fetch question counts (current & previous)
            curr_q_res = supabase_client.table("questions").select("id", count="exact").eq("project_id", project_id).execute()
            curr_q_count = curr_q_res.count or 0
            prev_q_count = 0
            if prev:
                prev_q_res = supabase_client.table("questions").select("id", count="exact")\
                    .eq("project_id", project_id)\
                    .lt("created_at", latest.get("created_at"))\
                    .execute()
                prev_q_count = prev_q_res.count or 0
                
            # Fetch keyword counts (current & previous)
            curr_kw_res = supabase_client.table("keywords").select("id", count="exact").eq("project_id", project_id).execute()
            curr_kw_count = curr_kw_res.count or 0
            prev_kw_count = 0
            if prev:
                prev_kw_res = supabase_client.table("keywords").select("id", count="exact")\
                    .eq("project_id", project_id)\
                    .lt("created_at", latest.get("created_at"))\
                    .execute()
                prev_kw_count = prev_kw_res.count or 0
                
            # Generate deltas
            comparison_metrics = [
                ("Questions", prev_q_count, curr_q_count, True),
                ("Keywords", prev_kw_count, curr_kw_count, True),
                ("Visibility", prev.get("visibility_score", 0.0) if prev else 0.0, latest.get("visibility_score", 0.0), True),
                ("Recommendation", prev.get("recommendation_score", 0.0) if prev else 0.0, latest.get("recommendation_score", 0.0), True),
                ("Coverage", prev.get("coverage_score", 0.0) if prev else 0.0, latest.get("coverage_score", 0.0), True),
                ("Grounding", prev.get("grounding_score", 100.0) if prev else 100.0, latest.get("grounding_score", 100.0), True),
                ("Consistency", prev.get("consistency_score", 100.0) if prev else 100.0, latest.get("consistency_score", 100.0), True),
            ]
            
            for name, p_val, c_val, is_higher_better in comparison_metrics:
                p_val = float(p_val or 0.0)
                c_val = float(c_val or 0.0)
                
                abs_change = c_val - p_val
                pct_change = ((abs_change / p_val) * 100.0) if p_val > 0 else 0.0
                
                if abs_change > 0.01:
                    status = "Improved" if is_higher_better else "Regressed"
                elif abs_change < -0.01:
                    status = "Regressed" if is_higher_better else "Improved"
                else:
                    status = "Stable"
                    
                before_after_cards.append({
                    "metric_name": name,
                    "previous_value": round(p_val, 1) if name not in ["Questions", "Keywords"] else int(p_val),
                    "current_value": round(c_val, 1) if name not in ["Questions", "Keywords"] else int(c_val),
                    "absolute_change": round(abs_change, 1) if name not in ["Questions", "Keywords"] else int(abs_change),
                    "percentage_change": round(pct_change, 1),
                    "status": status
                })
                
            # 4. Fetch payload for Explainability Engine
            bp_res = supabase_client.table("business_profiles").select("*").eq("project_id", project_id).limit(1).execute()
            bp = bp_res.data[0] if bp_res.data else {}
            
            vf_res = supabase_client.table("verified_facts")\
                .select("verification_score, extracted_fact_id, extracted_facts(fact_category, fact_key, fact_value, evidence_text, source_url)")\
                .execute()
                
            verified_facts = []
            for row in vf_res.data or []:
                ext = row.get("extracted_facts") or {}
                verified_facts.append({
                    "fact_category": ext.get("fact_category", "general"),
                    "fact_value": ext.get("fact_value", ""),
                    "fact_key": ext.get("fact_key", ""),
                    "evidence_text": ext.get("evidence_text", ""),
                    "verification_score": row.get("verification_score", 100.0),
                    "source_url": ext.get("source_url", "")
                })

            q_res = supabase_client.table("questions").select("*").eq("project_id", project_id).execute()
            kw_res = supabase_client.table("keywords").select("*").eq("project_id", project_id).execute()
            comp_res = supabase_client.table("competitors").select("*").eq("project_id", project_id).execute()
            page_res = supabase_client.table("web_pages").select("url, title, content").eq("project_id", project_id).execute()

            project_payload = {
                "business_profile": bp,
                "verified_facts": verified_facts,
                "questions": q_res.data or [],
                "keywords": kw_res.data or [],
                "competitors": comp_res.data or [],
                "crawled_pages": page_res.data or []
            }
            
            # Subscores helper
            vis_overall_score = float(latest.get("visibility_score") or 0.0)
            vis_coverage_score = float(latest.get("coverage_score") or 0.0)
            
            # Estimate visibility sub scores
            vis_faq = 90.0 if any("faq" in (p.get("url", "") or "").lower() for p in (page_res.data or [])) else 40.0
            vis_kb = 85.0 if any(any(term in (p.get("url", "") or "").lower() for term in ["guide", "kb", "knowledge", "blog"]) for p in (page_res.data or [])) else 45.0
            vis_structured = 95.0 if any("ld+json" in (p.get("content", "") or "").lower() or "schema.org" in (p.get("content", "") or "").lower() for p in (page_res.data or [])) else 30.0
            
            current_overall_scores = {
                "visibility_score": vis_overall_score,
                "recommendation_score": float(latest.get("recommendation_score") or 0.0),
                "coverage_score": vis_coverage_score,
                "visibility_sub_scores": {
                    "content_coverage": vis_coverage_score,
                    "question_coverage": vis_coverage_score * 0.9,
                    "keyword_coverage": vis_coverage_score * 0.85,
                    "trust_signals": vis_overall_score * 0.95,
                    "authority_signals": vis_overall_score * 0.9,
                    "structured_data": vis_structured,
                    "faq_coverage": vis_faq,
                    "knowledge_base_coverage": vis_kb,
                    "consistency": float(latest.get("consistency_score") or 80.0)
                }
            }

            exp_eng = ExplainabilityEngine()
            explainability = exp_eng.compute_breakdown(project_payload, current_overall_scores)

        result = {
            "trends": trends_analysis,
            "before_after_cards": before_after_cards,
            "explainability": explainability
        }

        set_cached_data(project_id, "analytics", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error compiling advanced analytics for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regressions/{project_id}")
def get_regressions(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches list of regression alerts for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "regressions")
        if cached is not None:
            return cached

        resp = supabase_client.table("regression_reports")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "regressions", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching regressions for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/root-causes/{project_id}")
def get_root_causes(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches list of metric root causes for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "root_causes")
        if cached is not None:
            return cached

        resp = supabase_client.table("root_cause_reports")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "root_causes", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching root causes for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heatmap/{project_id}")
def get_heatmap(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches query coverage heatmap for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "heatmap")
        if cached is not None:
            return cached

        resp = supabase_client.table("query_coverage_heatmaps")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()

        result = resp.data[0] if resp.data else {}
        set_cached_data(project_id, "heatmap", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching heatmap for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/opportunities/{project_id}")
def get_opportunities_v2(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches V2 opportunities for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "opportunities_v2")
        if cached is not None:
            return cached

        resp = supabase_client.table("content_opportunities_v2")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "opportunities_v2", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching V2 opportunities for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topic-clusters/{project_id}")
def get_topic_clusters(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches topic clusters for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "topic_clusters")
        if cached is not None:
            return cached

        resp = supabase_client.table("topic_clusters")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "topic_clusters", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching topic clusters for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content-blueprints/{project_id}")
def get_content_blueprints(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches content blueprints for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "content_blueprints")
        if cached is not None:
            return cached

        resp = supabase_client.table("content_blueprints")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "content_blueprints", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching content blueprints for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/authority-sources/{project_id}")
def get_authority_sources(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches authority sources for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "authority_sources")
        if cached is not None:
            return cached

        resp = supabase_client.table("authority_sources")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "authority_sources", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching authority sources for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faq-clusters/{project_id}")
def get_faq_clusters(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches FAQ clusters for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "faq_clusters")
        if cached is not None:
            return cached

        resp = supabase_client.table("faq_clusters")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "faq_clusters", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching FAQ clusters for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content-gaps/{project_id}")
def get_content_gaps(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches content gap reports v2 for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "content_gap_reports_v2")
        if cached is not None:
            return cached

        resp = supabase_client.table("content_gap_reports_v2")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "content_gap_reports_v2", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching content gaps for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/internal-links/{project_id}")
def get_internal_links(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches internal link maps for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "internal_link_maps")
        if cached is not None:
            return cached

        resp = supabase_client.table("internal_link_maps")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "internal_link_maps", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching internal link maps for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema-recommendations/{project_id}")
def get_schema_recommendations(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches schema recommendations for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "schema_recommendations")
        if cached is not None:
            return cached

        resp = supabase_client.table("schema_recommendations")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "schema_recommendations", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching schema recommendations for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/citation-predictions/{project_id}")
def get_citation_predictions(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches citation predictions for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "citation_predictions")
        if cached is not None:
            return cached

        resp = supabase_client.table("citation_predictions")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "citation_predictions", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching citation predictions for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Phase 8: Reliability & Self-Healing API Routes


