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

class RunOut(BaseModel):
    id: str
    project_id: str
    status: str
    started_at: str
    completed_at: Optional[str]
    error_message: Optional[str]
    current_agent: Optional[str] = None

async def execute_bg_analysis(project_id: str, run_id: str, website_url: str):
    """Background task orchestrating crawler spider and agent pipeline."""
    try:
        # Step 0: Clean up previous web_pages data for this project
        logger.info(f"Cleaning up previous web_pages for project {project_id}...")
        try:
            supabase_client.table("web_pages").delete().eq("project_id", project_id).execute()
        except Exception as e:
            logger.warning(f"web_pages cleanup warning: {e}")
        
        # Step 1: Run Crawler
        logger.info(f"Triggering asynchronous crawl for project {project_id}...")
        
        # Update run & project status to 'crawling'
        supabase_client.table("analysis_runs").update({
            "status": "crawling",
            "current_agent": "Crawler"
        }).eq("id", run_id).execute()
        
        supabase_client.table("projects").update({
            "status": "crawling",
            "current_agent": "Crawler"
        }).eq("id", project_id).execute()
        
        spider = WebsiteSpider(project_id, website_url)
        pages_crawled = await spider.start()
        logger.info(f"Crawl completed. Crawled {pages_crawled} pages.")
        
        # Step 2: Trigger Agent Network
        await run_analysis_pipeline(project_id, run_id, website_url)
        
    except Exception as e:
        logger.error(f"Error in background execution for project {project_id}: {e}")
        supabase_client.table("analysis_runs").update({
            "status": "failed",
            "error_message": str(e),
            "completed_at": "now()",
            "current_agent": None
        }).eq("id", run_id).execute()
        supabase_client.table("projects").update({
            "status": "failed",
            "current_agent": None
        }).eq("id", project_id).execute()


@router.post("/run/{project_id}", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED)
def trigger_analysis(
    project_id: str, 
    background_tasks: BackgroundTasks, 
    user_id: str = Depends(get_current_user)
):
    """Triggers an automated crawler and agent intelligence analysis run in the background."""
    try:
        # Ensure project exists and belongs to user
        proj_resp = supabase_client.table("projects").select("*").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )
            
        project = proj_resp.data[0]
        
        # Create Analysis Run record
        run_resp = supabase_client.table("analysis_runs").insert({
            "project_id": project_id,
            "status": "queued",
            "current_agent": "Scheduler"
        }).execute()
        
        if not run_resp.data:
            raise HTTPException(status_code=500, detail="Failed to create run record")
            
        run = run_resp.data[0]
        
        # Update Project status to queued
        supabase_client.table("projects").update({
            "status": "queued",
            "current_agent": "Scheduler"
        }).eq("id", project_id).execute()
        
        # Schedule background crawler and agents
        background_tasks.add_task(
            execute_bg_analysis, 
            project_id=project_id, 
            run_id=run["id"], 
            website_url=project["website_url"]
        )
        
        # Log activity
        supabase_client.table("activity_logs").insert({
            "project_id": project_id,
            "user_id": user_id,
            "action": "analysis_triggered",
            "metadata": {"description": f"Triggered analysis run {run['id']} for URL {project['website_url']}"}
        }).execute()
        
        return run
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{run_id}", response_model=RunOut)
def get_run_status(run_id: str, user_id: str = Depends(get_current_user)):
    """Retrieves the real-time execution status of a specific analysis run."""
    try:
        # Check authorization by ensuring the project belongs to the user
        response = supabase_client.table("analysis_runs").select(
            "*, projects!inner(user_id)"
        ).eq("id", run_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Analysis run not found"
            )
            
        run_data = response.data[0]
        # Check ownership
        if run_data["projects"]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
            
        # Clean response fields (remove inner join data)
        return {
            "id": run_data["id"],
            "project_id": run_data["project_id"],
            "status": run_data["status"],
            "started_at": run_data["started_at"],
            "completed_at": run_data["completed_at"],
            "error_message": run_data["error_message"],
            "current_agent": run_data.get("current_agent")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking run status {run_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")

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

@router.get("/questions/{project_id}")
def get_analysis_questions(
    project_id: str,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    question_type: Optional[str] = None,
    sort_by: str = "priority_score",
    sort_order: str = "desc",
    user_id: str = Depends(get_current_user)
):
    """Retrieves paginated, filtered, and searched questions for a project."""
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Cache lookup — keyed by all filter/sort/page parameters
        # Only use cache for the default un-filtered first page (common dashboard load)
        if not search and not question_type and page == 1 and page_size == 10 and sort_by == "priority_score" and sort_order == "desc":
            cached = get_cached_data(project_id, "questions_page1")
            if cached is not None:
                return cached
            
        # Build base query with exact count
        query = supabase_client.table("questions").select("*", count="exact").eq("project_id", project_id)
        
        if question_type and question_type != "All":
            query = query.eq("question_type", question_type)
            
        if search:
            query = query.ilike("question", f"%{search}%")
            
        # Map sort key if needed (default to priority_score)
        valid_sorts = {
            "question": "question",
            "question_text": "question",
            "category": "question_type",
            "question_type": "question_type",
            "intent": "intent",
            "confidence_score": "confidence_score",
            "priority": "priority_score",
            "priority_score": "priority_score",
            "recommendation_score": "recommendation_score",
            "commercial_score": "commercial_score",
            "intent_score": "intent_score",
            "difficulty_estimate": "difficulty_estimate",
            "opportunity_estimate": "opportunity_estimate"
        }
        db_sort_by = valid_sorts.get(sort_by, "priority_score")
        
        # Apply sorting
        desc = (sort_order.lower() == "desc")
        query = query.order(db_sort_by, desc=desc)
        
        # Pagination range
        start = (page - 1) * page_size
        end = start + page_size - 1
        
        resp = query.range(start, end).execute()
        
        mapped_questions = []
        for q in (resp.data if resp.data else []):
            mapped_questions.append({
                "id": q["id"],
                "category": q.get("question_type", "General"),
                "question_text": q.get("question", ""),
                "recommended_answer": q.get("recommended_answer", ""),
                "intent": q.get("intent", ""),
                "confidence_score": q.get("confidence_score", 1.0),
                "priority": q.get("priority", "Medium"),
                "recommendation_score": q.get("recommendation_score", 0.0),
                "commercial_score": q.get("commercial_score", 0.0),
                "intent_score": q.get("intent_score", 0.0),
                "priority_score": q.get("priority_score", 0.0),
                "difficulty_estimate": q.get("difficulty_estimate", "Medium"),
                "opportunity_estimate": q.get("opportunity_estimate", "Medium")
            })
            
        result = {
            "questions": mapped_questions,
            "total_count": resp.count or 0,
            "page": page,
            "page_size": page_size
        }
        # Cache the default first page only
        if not search and not question_type and page == 1 and page_size == 10 and sort_by == "priority_score" and sort_order == "desc":
            set_cached_data(project_id, "questions_page1", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching questions: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@router.get("/keywords/{project_id}")
def get_analysis_keywords(
    project_id: str,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    keyword_type: Optional[str] = None,
    sort_by: str = "keyword",
    sort_order: str = "asc",
    user_id: str = Depends(get_current_user)
):
    """Retrieves paginated, filtered, and searched keywords for a project."""
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Cache lookup — keyed on default un-filtered first page load
        if not search and not keyword_type and page == 1 and page_size == 10 and sort_by == "keyword" and sort_order == "asc":
            cached = get_cached_data(project_id, "keywords_page1")
            if cached is not None:
                return cached

        # Build base query with exact count
        query = supabase_client.table("keywords").select("*", count="exact").eq("project_id", project_id)
        
        if keyword_type and keyword_type != "All":
            query = query.eq("keyword_type", keyword_type)
            
        if search:
            query = query.ilike("keyword", f"%{search}%")
            
        # Map sort key if needed (default to keyword)
        valid_sorts = {
            "keyword": "keyword",
            "keyword_text": "keyword",
            "category": "keyword_type",
            "keyword_type": "keyword_type",
            "search_intent": "intent",
            "intent": "intent",
            "clustering_theme": "cluster",
            "cluster": "cluster",
            "confidence_score": "confidence_score",
            "priority": "priority",
            "difficulty_estimate": "difficulty_estimate",
            "opportunity_estimate": "opportunity_estimate",
            "source": "source"
        }
        db_sort_by = valid_sorts.get(sort_by, "keyword")
        
        # Apply sorting
        desc = (sort_order.lower() == "desc")
        query = query.order(db_sort_by, desc=desc)
        
        # Pagination range
        start = (page - 1) * page_size
        end = start + page_size - 1
        
        resp = query.range(start, end).execute()
        
        mapped_keywords = []
        for kw in (resp.data if resp.data else []):
            mapped_keywords.append({
                "id": kw["id"],
                "keyword_text": kw.get("keyword", ""),
                "category": kw.get("keyword_type", "General"),
                "search_intent": kw.get("intent", ""),
                "clustering_theme": kw.get("cluster", "General"),
                "priority": kw.get("priority", "Medium"),
                "difficulty_estimate": kw.get("difficulty_estimate", "Medium"),
                "opportunity_estimate": kw.get("opportunity_estimate", "Medium"),
                "source": kw.get("source", "Recommendation Queries")
            })
            
        result = {
            "keywords": mapped_keywords,
            "total_count": resp.count or 0,
            "page": page,
            "page_size": page_size
        }
        # Cache the default first page only
        if not search and not keyword_type and page == 1 and page_size == 10 and sort_by == "keyword" and sort_order == "asc":
            set_cached_data(project_id, "keywords_page1", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching keywords: {e}")
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/validation/{project_id}")
def get_validation_report(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Runs QuestionQualityAuditor and KeywordQualityAuditor against all stored data
    for a project and returns a structured validation report with scores, warnings,
    and actionable suggestions. No LLM calls - pure deterministic analysis.
    """
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Fetch all questions for this project (no pagination - auditor needs full set)
        q_resp = supabase_client.table("questions").select(
            "id, question, question_type, recommended_answer, intent, confidence_score, priority, "
            "recommendation_score, commercial_score, intent_score, priority_score, "
            "difficulty_estimate, opportunity_estimate"
        ).eq("project_id", project_id).execute()

        questions_raw = q_resp.data or []

        # Normalize to auditor-expected format
        questions_for_audit = [
            {
                "question": q.get("question", ""),
                "question_type": q.get("question_type", ""),
                "recommended_answer": q.get("recommended_answer", ""),
                "intent": q.get("intent", ""),
                "confidence_score": float(q.get("confidence_score", 1.0)),
                "priority": q.get("priority", "Medium"),
            }
            for q in questions_raw
        ]

        # Fetch all keywords for this project
        kw_resp = supabase_client.table("keywords").select(
            "id, keyword, keyword_type, intent, cluster, priority, confidence_score, "
            "difficulty_estimate, opportunity_estimate, source"
        ).eq("project_id", project_id).execute()

        keywords_raw = kw_resp.data or []

        keywords_for_audit = [
            {
                "keyword": kw.get("keyword", ""),
                "keyword_type": kw.get("keyword_type", ""),
                "intent": kw.get("intent", ""),
                "cluster": kw.get("cluster", ""),
                "priority": kw.get("priority", "Medium"),
                "confidence_score": float(kw.get("confidence_score", 1.0)),
            }
            for kw in keywords_raw
        ]

        # Run auditors
        q_auditor = QuestionQualityAuditor()
        kw_auditor = KeywordQualityAuditor()

        question_report = q_auditor.audit(questions_for_audit)
        keyword_report = kw_auditor.audit(keywords_for_audit)

        # Compute combined health score (weighted average)
        combined_score = round(
            (question_report["quality_score"] * 0.5 + keyword_report["quality_score"] * 0.5),
            1
        )

        # Determine overall status
        if combined_score >= 80:
            overall_status = "healthy"
        elif combined_score >= 60:
            overall_status = "warning"
        else:
            overall_status = "critical"

        return {
            "project_id": project_id,
            "overall_status": overall_status,
            "combined_quality_score": combined_score,
            "question_audit": question_report,
            "keyword_audit": keyword_report,
            "total_warnings": len(question_report["warnings"]) + len(keyword_report["warnings"]),
            "total_suggestions": len(question_report["suggestions"]) + len(keyword_report["suggestions"]),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running validation for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


def _get_project_data_payload(project_id: str) -> dict:
    try:
        bp_resp = supabase_client.table("business_profiles").select("*").eq("project_id", project_id).order("generated_at", desc=True).limit(1).execute()
        business_profile = bp_resp.data[0] if bp_resp.data else {}
    except Exception as e:
        logger.warning(f"Error fetching business profile: {e}")
        business_profile = {}

    try:
        facts_resp = supabase_client.table("verified_facts").select(
            "*, extracted_facts!inner(*)"
        ).eq("extracted_facts.project_id", project_id).execute()
        verified_facts = []
        for f in (facts_resp.data if facts_resp.data else []):
            ext = f.get("extracted_facts", {})
            verified_facts.append({
                "id": f.get("id"),
                "fact_type": ext.get("fact_category", "general"),
                "fact_value": ext.get("fact_value", ""),
                "fact_key": ext.get("fact_key", ""),
                "evidence": ext.get("evidence_text", ""),
                "confidence_score": float(f.get("verification_score", 100.0) / 100.0),
                "source_url": ext.get("source_url", "")
            })
    except Exception as e:
        logger.warning(f"Error fetching verified facts: {e}")
        verified_facts = []

    try:
        q_resp = supabase_client.table("questions").select("*").eq("project_id", project_id).execute()
        questions = q_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching questions: {e}")
        questions = []

    try:
        kw_resp = supabase_client.table("keywords").select("*").eq("project_id", project_id).execute()
        keywords = kw_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching keywords: {e}")
        keywords = []

    try:
        comp_resp = supabase_client.table("competitors").select("*").eq("project_id", project_id).execute()
        competitors = []
        for comp in (comp_resp.data if comp_resp.data else []):
            competitors.append({
                "id": comp.get("id"),
                "name": comp.get("competitor_name", ""),
                "competitor_name": comp.get("competitor_name", ""),
                "website_url": comp.get("website", ""),
                "competitor_type": comp.get("competitor_type", "direct"),
                "strengths": comp.get("strengths", []),
                "weaknesses": comp.get("weaknesses", []),
                "market_gaps": comp.get("content_gaps", []),
                "description": comp.get("description", ""),
                "unique_features": comp.get("unique_features", []),
                "reason_selected": comp.get("reason_selected", []),
                "similarity_score": comp.get("similarity_score", 50),
                "industry_match": comp.get("industry_match", ""),
                "audience_match": comp.get("audience_match", ""),
                "service_match": comp.get("service_match", "")
            })
    except Exception as e:
        logger.warning(f"Error fetching competitors: {e}")
        competitors = []

    try:
        cov_resp = supabase_client.table("content_coverage").select("*").eq("project_id", project_id).execute()
        content_coverage = cov_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching content coverage: {e}")
        content_coverage = []

    try:
        pages_resp = supabase_client.table("web_pages").select("url, title, content").eq("project_id", project_id).execute()
        crawled_pages = []
        for p in (pages_resp.data if pages_resp.data else []):
            crawled_pages.append({
                "url": p.get("url", ""),
                "title": p.get("title", ""),
                "content": p.get("content", "")
            })
    except Exception as e:
        logger.warning(f"Error fetching crawled pages: {e}")
        crawled_pages = []

    try:
        opps_resp = supabase_client.table("content_opportunities").select("*").eq("project_id", project_id).execute()
        content_opportunities = opps_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching content opportunities: {e}")
        content_opportunities = []

    try:
        blogs_resp = supabase_client.table("blogs").select("*").eq("project_id", project_id).execute()
        blogs = blogs_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching blogs: {e}")
        blogs = []

    try:
        nodes_resp = supabase_client.table("entity_nodes").select("*").eq("project_id", project_id).execute()
        entity_nodes = nodes_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching entity nodes: {e}")
        entity_nodes = []

    try:
        gap_resp = supabase_client.table("gap_analysis").select("*").eq("project_id", project_id).execute()
        gap_analysis = gap_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching gap analysis: {e}")
        gap_analysis = []

    return {
        "business_profile": business_profile,
        "verified_facts": verified_facts,
        "questions": questions,
        "keywords": keywords,
        "competitors": competitors,
        "content_coverage": content_coverage,
        "crawled_pages": crawled_pages,
        "content_opportunities": content_opportunities,
        "blogs": blogs,
        "entity_nodes": entity_nodes,
        "gap_analysis": gap_analysis
    }


@router.get("/recommendation-intelligence/{project_id}")
def get_recommendation_intelligence(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Runs recommendation confidence engine and returns V2 report, saving simulations."""
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Cache check (30 min TTL — heavy computation)
        cached = get_cached_data(project_id, "recommendation_intelligence")
        if cached is not None:
            return cached

        project_data = _get_project_data_payload(project_id)
        engine = RecommendationEngineV2()
        result = engine.run(project_data)

        # Persistence: Delete old simulations first
        try:
            supabase_client.table("recommendation_simulations_v2").delete().eq("project_id", project_id).execute()
        except Exception as db_err:
            logger.warning(f"Error cleaning up old recommendation simulations: {db_err}")

        # Insert new simulations
        sims_to_insert = []
        for sim in result.get("simulations", []):
            sims_to_insert.append({
                "project_id": project_id,
                "query": sim["query"],
                "recommendation_score": sim["recommendation_score"],
                "confidence": sim["confidence"],
                "evidence": sim["evidence"],
                "weaknesses": sim["weaknesses"],
                "missing_requirements": sim["missing_requirements"],
                "improvement_actions": sim["improvement_actions"],
                "competitor_advantages": sim["competitor_threats"],
                "signal_breakdown": sim["signal_breakdown"]
            })
        if sims_to_insert:
            try:
                supabase_client.table("recommendation_simulations_v2").insert(sims_to_insert).execute()
            except Exception as db_err:
                logger.error(f"Error storing recommendation simulations: {db_err}")

        set_cached_data(project_id, "recommendation_intelligence", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendation intelligence for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hallucination-report/{project_id}")
def get_hallucination_report(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Runs the hallucination detector on demand and returns the flag breakdown."""
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Cache check (30 min TTL — heavy computation)
        cached = get_cached_data(project_id, "hallucination_report")
        if cached is not None:
            return cached

        project_data = _get_project_data_payload(project_id)
        detector = HallucinationDetector()
        result = detector.detect(project_data)

        # Persistence: Delete old hallucination reports
        try:
            supabase_client.table("hallucination_reports").delete().eq("project_id", project_id).execute()
        except Exception as db_err:
            logger.warning(f"Error cleaning up old hallucination reports: {db_err}")

        # Insert new reports
        reports_to_insert = []
        for f in result.get("flags", []):
            reports_to_insert.append({
                "project_id": project_id,
                "item_type": f["item_type"],
                "item_text": f["item_text"],
                "flag_level": f["flag_level"],
                "supporting_evidence": f.get("supporting_evidence", "")
            })
        if reports_to_insert:
            try:
                supabase_client.table("hallucination_reports").insert(reports_to_insert).execute()
            except Exception as db_err:
                logger.error(f"Error storing hallucination reports: {db_err}")

        set_cached_data(project_id, "hallucination_report", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating hallucination report for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consistency-report/{project_id}")
def get_consistency_report(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Runs the cross-agent knowledge consistency engine and returns the contradictions/repair actions."""
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Cache check (30 min TTL — heavy computation)
        cached = get_cached_data(project_id, "consistency_report")
        if cached is not None:
            return cached

        project_data = _get_project_data_payload(project_id)
        engine = KnowledgeConsistencyEngine()
        result = engine.analyze(project_data)

        # Persistence: Delete old consistency reports
        try:
            supabase_client.table("knowledge_consistency_reports").delete().eq("project_id", project_id).execute()
        except Exception as db_err:
            logger.warning(f"Error cleaning up old knowledge consistency reports: {db_err}")

        # Insert new report
        try:
            supabase_client.table("knowledge_consistency_reports").insert({
                "project_id": project_id,
                "consistency_score": result["consistency_score"],
                "conflicts": result["conflicts"],
                "warnings": result["warnings"],
                "repair_actions": result["repair_actions"]
            }).execute()
        except Exception as db_err:
            logger.error(f"Error storing knowledge consistency report: {db_err}")

        set_cached_data(project_id, "consistency_report", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating consistency report for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# BATCH 4.5 — REALITY CHECKER ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

class VerifyCheckRequest(BaseModel):
    chatgpt_mentions: str  # 'YES', 'NO', 'PARTIAL'
    gemini_mentions: str
    perplexity_mentions: str


@router.get("/reality-check/{project_id}")
def get_reality_checks(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Returns stored reality checks for a project, generating them if none exist."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        existing = supabase_client.table("reality_checks").select("*").eq("project_id", project_id).execute()
        if existing.data:
            return {"reality_checks": existing.data, "source": "stored"}

        # Generate fresh if none stored
        project_data = _get_project_data_payload(project_id)
        checker = RealityChecker()
        generated = checker.generate_queries(project_data)

        rows = [{**q, "project_id": project_id} for q in generated]
        try:
            supabase_client.table("reality_checks").insert(rows).execute()
        except Exception as db_err:
            logger.error(f"Error storing reality checks: {db_err}")

        stored = supabase_client.table("reality_checks").select("*").eq("project_id", project_id).execute()
        return {"reality_checks": stored.data or rows, "source": "generated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching reality checks for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reality-check/{project_id}/generate")
def generate_reality_checks(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Force regenerates 20 reality checks, replacing any existing ones."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        # Delete old
        try:
            supabase_client.table("reality_checks").delete().eq("project_id", project_id).execute()
        except Exception as db_err:
            logger.warning(f"Error cleaning old reality checks: {db_err}")

        project_data = _get_project_data_payload(project_id)
        checker = RealityChecker()
        generated = checker.generate_queries(project_data)

        rows = [{**q, "project_id": project_id} for q in generated]
        supabase_client.table("reality_checks").insert(rows).execute()

        stored = supabase_client.table("reality_checks").select("*").eq("project_id", project_id).execute()
        return {"reality_checks": stored.data or rows, "total": len(rows)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating reality checks for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/reality-check/{project_id}/verify/{check_id}")
def verify_reality_check(
    project_id: str,
    check_id: str,
    payload: VerifyCheckRequest,
    user_id: str = Depends(get_current_user)
):
    """Updates manual verification status for a single reality check row."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        allowed_values = {"YES", "NO", "PARTIAL"}
        for field, val in [
            ("chatgpt_mentions", payload.chatgpt_mentions),
            ("gemini_mentions", payload.gemini_mentions),
            ("perplexity_mentions", payload.perplexity_mentions),
        ]:
            if val.upper() not in allowed_values:
                raise HTTPException(status_code=422, detail=f"{field} must be YES, NO, or PARTIAL")

        update_resp = supabase_client.table("reality_checks").update({
            "chatgpt_mentions": payload.chatgpt_mentions.upper(),
            "gemini_mentions": payload.gemini_mentions.upper(),
            "perplexity_mentions": payload.perplexity_mentions.upper(),
            "is_verified": True,
        }).eq("id", check_id).eq("project_id", project_id).execute()

        return {"updated": bool(update_resp.data), "check_id": check_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying reality check {check_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reality-check/metrics/{project_id}")
def get_reality_check_metrics(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Calculates Accuracy, Precision, Recall, and Calibration Error from verified reality checks."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        checks_resp = supabase_client.table("reality_checks").select("*").eq("project_id", project_id).execute()
        checks = checks_resp.data or []

        checker = RealityChecker()
        metrics = checker.calculate_metrics(checks)
        metrics["total_checks"] = len(checks)
        metrics["verified_checks"] = sum(1 for c in checks if c.get("is_verified"))
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating reality check metrics for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# BATCH 4.5 — COMPETITOR BENCHMARK ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

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
