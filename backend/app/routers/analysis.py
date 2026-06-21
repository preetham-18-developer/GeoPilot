from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.core.supabase import supabase_client
from app.core.dependencies import get_current_user
from app.crawler.spider import WebsiteSpider
from app.agents.graph import run_analysis_pipeline
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
        
        # Update run status to 'crawling'
        supabase_client.table("analysis_runs").update({"status": "crawling"}).eq("id", run_id).execute()
        
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
            "completed_at": "now()"
        }).eq("id", run_id).execute()


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
            "status": "pending"
        }).execute()
        
        if not run_resp.data:
            raise HTTPException(status_code=500, detail="Failed to create run record")
            
        run = run_resp.data[0]
        
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
            "error_message": run_data["error_message"]
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
        
        # Fetch questions (FAQs)
        questions_resp = supabase_client.table("questions").select("*").eq("project_id", project_id).execute()
        mapped_questions = []
        for q in (questions_resp.data if questions_resp.data else []):
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
        
        # Fetch keywords
        keywords_resp = supabase_client.table("keywords").select("*").eq("project_id", project_id).execute()
        mapped_keywords = []
        for kw in (keywords_resp.data if keywords_resp.data else []):
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
        
        return {
            "verified_facts": mapped_facts,
            "questions": mapped_questions,
            "keywords": mapped_keywords,
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching results for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")
