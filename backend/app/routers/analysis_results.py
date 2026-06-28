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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/results/{project_id}")
def get_analysis_results(project_id: str, user_id: str = Depends(get_current_user)):
    """Retrieves all compiled factual, FAQ, keyword, competitor intelligence, content opportunities, and agent runs for a project."""
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Cache check
        cached = get_cached_data(project_id, "analysis_results")
        if cached is not None:
            return cached
            
        # Fetch verified facts (joining with extracted_facts to get actual contents)
        facts_resp = supabase_client.table("verified_facts").select(
            "*, extracted_facts!inner(*)"
        ).eq("extracted_facts.project_id", project_id).execute()
        
        mapped_facts = []
        for f in (facts_resp.data if facts_resp.data else []):
            ext = f.get("extracted_facts", {})
            mapped_facts.append({
                "id": f["id"],
                "fact_type": ext.get("fact_category", "general"),
                "content": {ext.get("fact_key", "detail"): ext.get("fact_value", "")},
                "evidence": ext.get("evidence_text", ""),
                "confidence_score": float(f.get("verification_score", 100.0) / 100.0),
                "source_url": ext.get("source_url", "")
            })
        
        # Count and get categories for questions
        q_count_resp = supabase_client.table("questions").select("question_type", count="exact").eq("project_id", project_id).execute()
        questions_count = q_count_resp.count or 0
        questions_categories = sorted(list({q["question_type"] for q in (q_count_resp.data or []) if q.get("question_type")}))
        
        # Count and get categories for keywords
        kw_count_resp = supabase_client.table("keywords").select("keyword_type", count="exact").eq("project_id", project_id).execute()
        keywords_count = kw_count_resp.count or 0
        keywords_categories = sorted(list({kw["keyword_type"] for kw in (kw_count_resp.data or []) if kw.get("keyword_type")}))
        keyword_clusters_count = max(1, keywords_count // 10) if keywords_count > 0 else 0
        
        # Fetch competitors
        competitors_resp = supabase_client.table("competitors").select("*").eq("project_id", project_id).execute()
        mapped_competitors = []
        for comp in (competitors_resp.data if competitors_resp.data else []):
            mapped_competitors.append({
                "id": comp["id"],
                "name": comp.get("competitor_name", ""),
                "website_url": comp.get("website", ""),
                "competitor_type": comp.get("competitor_type", "direct"),
                "strengths": comp.get("strengths", []),
                "weaknesses": comp.get("weaknesses", []),
                "market_gaps": comp.get("content_gaps", []),
                "description": comp.get("description", "NOT_FOUND"),
                "unique_features": comp.get("unique_features", []),
                "reason_selected": comp.get("reason_selected", []),
                "similarity_score": comp.get("similarity_score", 50),
                "industry_match": comp.get("industry_match", "NOT_FOUND"),
                "audience_match": comp.get("audience_match", "NOT_FOUND"),
                "service_match": comp.get("service_match", "NOT_FOUND")
            })
            
        # Fetch content opportunities
        opps_resp = supabase_client.table("content_opportunities").select("*").eq("project_id", project_id).execute()
        
        # Fetch agent runs
        runs_resp = supabase_client.table("agent_runs").select("*").eq("project_id", project_id).order("created_at", desc=True).execute()
        
        # Fetch QA Report
        qa_resp = supabase_client.table("qa_reports").select("*").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
        qa_report = qa_resp.data[0] if qa_resp.data else None
 
        # Fetch Business Profile
        bi_resp = supabase_client.table("business_profiles").select("*").eq("project_id", project_id).order("generated_at", desc=True).limit(1).execute()
        business_profile = bi_resp.data[0] if bi_resp.data else None
 
        # Fetch Competitor Feature Matrix
        matrix_resp = supabase_client.table("competitor_feature_matrix").select("*").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
        competitor_feature_matrix = matrix_resp.data[0]["features"] if matrix_resp.data else None
 
        # Fetch Gap Analysis
        gap_resp = supabase_client.table("gap_analysis").select("*").eq("project_id", project_id).execute()
 
        # Fetch AI Visibility Score
        score_resp = supabase_client.table("ai_visibility_tracking").select("*").eq("project_id", project_id).order("tracked_at", desc=True).limit(1).execute()
        ai_visibility_score = score_resp.data[0]["details"] if score_resp.data else None
 
        # Fetch Recommendation Simulations
        sims_resp = supabase_client.table("recommendation_simulations").select("*").eq("project_id", project_id).execute()
 
        # Fetch Entity Nodes & Relationships
        nodes_resp = supabase_client.table("entity_nodes").select("*").eq("project_id", project_id).execute()
        rels_resp = supabase_client.table("entity_relationships").select("*").eq("project_id", project_id).execute()
 
        # Fetch Content Coverage
        cov_resp = supabase_client.table("content_coverage").select("*").eq("project_id", project_id).execute()
 
        # Fetch Extraction Failures
        failures_resp = supabase_client.table("extraction_failures").select("*").eq("project_id", project_id).order("created_at", desc=True).execute()
        
        result = {
            "verified_facts": mapped_facts,
            "questions_count": questions_count,
            "questions_categories": questions_categories,
            "keywords_count": keywords_count,
            "keywords_categories": keywords_categories,
            "keyword_clusters_count": keyword_clusters_count,
            "competitors": mapped_competitors,
            "content_opportunities": opps_resp.data if opps_resp.data else [],
            "agent_runs": runs_resp.data if runs_resp.data else [],
            "qa_report": qa_report,
            "business_profile": business_profile,
            "competitor_feature_matrix": competitor_feature_matrix,
            "gap_analysis": gap_resp.data if gap_resp.data else [],
            "ai_visibility_score": ai_visibility_score,
            "recommendation_simulations": sims_resp.data if sims_resp.data else [],
            "entity_nodes": nodes_resp.data if nodes_resp.data else [],
            "entity_relationships": rels_resp.data if rels_resp.data else [],
            "content_coverage": cov_resp.data if cov_resp.data else [],
            "extraction_failures": failures_resp.data if failures_resp.data else []
        }
        set_cached_data(project_id, "analysis_results", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching results for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")


