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


@router.get("/dependencies")
def get_dependency_status(user_id: str = Depends(get_current_user)):
    """Triggers dependency monitor ping and returns real-time status of external services."""
    try:
        from app.core.dependency_monitor import DependencyMonitor
        monitor = DependencyMonitor()
        return monitor.check_all()
    except Exception as e:
        logger.error(f"Error executing dependency check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/errors/{project_id}")
def get_error_diagnostics(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches classified failures history for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")
            
        resp = supabase_client.table("error_diagnostics")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("timestamp", desc=True)\
            .execute()
        return resp.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching diagnostics for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/timeline/{run_id}")
def get_run_timeline(
    run_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches node duration timeline for a run."""
    try:
        run_check = supabase_client.table("analysis_runs")\
            .select("*, projects!inner(user_id)")\
            .eq("id", run_id)\
            .execute()
        if not run_check.data or run_check.data[0]["projects"]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized run access")
            
        resp = supabase_client.table("execution_timelines")\
            .select("*")\
            .eq("run_id", run_id)\
            .order("started_at", desc=False)\
            .execute()
        return resp.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching timeline for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/checkpoints/{run_id}")
def get_run_checkpoints(
    run_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches node checkpoints list for a run."""
    try:
        run_check = supabase_client.table("analysis_runs")\
            .select("*, projects!inner(user_id)")\
            .eq("id", run_id)\
            .execute()
        if not run_check.data or run_check.data[0]["projects"]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized run access")
            
        resp = supabase_client.table("execution_checkpoints")\
            .select("*")\
            .eq("run_id", run_id)\
            .order("created_at", desc=False)\
            .execute()
        return resp.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching checkpoints for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resume/{run_id}")
def resume_failed_run(
    run_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Resumes execution of a failed pipeline run from the last failed checkpoint."""
    try:
        run_check = supabase_client.table("analysis_runs")\
            .select("*, projects!inner(user_id, website_url)")\
            .eq("id", run_id)\
            .execute()
        if not run_check.data:
            raise HTTPException(status_code=404, detail="Run not found")
        
        run_data = run_check.data[0]
        if run_data["projects"]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
            
        project_id = run_data["project_id"]
        website_url = run_data["projects"]["website_url"]
        
        # Reset run status to queued
        supabase_client.table("analysis_runs").update({
            "status": "queued",
            "error_message": None,
            "current_agent": "Resumer"
        }).eq("id", run_id).execute()
        
        supabase_client.table("projects").update({
            "status": "queued",
            "current_agent": "Resumer"
        }).eq("id", project_id).execute()
        
        # Trigger the pipeline background task directly (skips crawler since we are resuming agents)
        background_tasks.add_task(
            run_analysis_pipeline,
            project_id=project_id,
            run_id=run_id,
            website_url=website_url
        )
        
        # Log activity
        supabase_client.table("activity_logs").insert({
            "project_id": project_id,
            "user_id": user_id,
            "action": "run_resumed",
            "metadata": {"description": f"Resumed analysis run {run_id} from checkpoints"}
        }).execute()
        
        return {"status": "resumed", "run_id": run_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Phase 9: GEO Citation & Recommendation Intelligence Routes


@router.get("/execution/tasks/{project_id}")
def get_execution_tasks(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Retrieves autonomous execution tasks in the project queue."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "execution_tasks")
        if cached is not None:
            return cached

        resp = supabase_client.table("execution_tasks")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "execution_tasks", result, ttl=600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching execution tasks for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generated-assets/{project_id}")
def get_generated_assets(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Retrieves all generated content and schema assets for a project."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "generated_assets")
        if cached is not None:
            return cached

        resp = supabase_client.table("generated_assets")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "generated_assets", result, ttl=600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching generated assets for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution/results/{project_id}")
def get_execution_results(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Retrieves before/after scores of completed task optimizations."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "execution_results")
        if cached is not None:
            return cached

        resp = supabase_client.table("execution_results")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "execution_results", result, ttl=600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching execution results for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning-memory/{project_id}")
def get_learning_memory(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Retrieves success rate metrics and optimization trends from the local learning memory."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        cached = get_cached_data(project_id, "learning_memory")
        if cached is not None:
            return cached

        resp = supabase_client.table("learning_memory")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("average_gain", desc=True)\
            .execute()

        result = resp.data or []
        set_cached_data(project_id, "learning_memory", result, ttl=600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching learning memory for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execution/accept/{task_id}")
def accept_execution_task(
    task_id: str,
    user_id: str = Depends(get_current_user)
):
    """Accepts an optimization task and runs the asset generator engines in the background."""
    try:
        # Check task existence and user project ownership
        task_resp = supabase_client.table("execution_tasks").select("*, projects!inner(user_id)").eq("id", task_id).execute()
        if not task_resp.data:
            raise HTTPException(status_code=404, detail="Task not found")
        task = task_resp.data[0]
        if task["projects"]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
            
        project_id = task["project_id"]
        category = task["category"]

        # Update task status to running
        supabase_client.table("execution_tasks")\
            .update({"status": "running"})\
            .eq("id", task_id)\
            .execute()

        # Invalidate project caches
        invalidate_project_cache(project_id)

        # Retrieve project payload for asset generation engines
        payload = _get_project_data_payload(project_id)

        # Generate assets depending on category
        generated = []
        if category in ["Content", "Competitors", "FAQ"]:
            from app.core.page_generator_engine import PageGeneratorEngine
            pg = PageGeneratorEngine()
            generated.append(pg.generate(project_id, category, payload))

            if category == "FAQ":
                from app.core.schema_generator_engine_v2 import SchemaGeneratorEngineV2
                sg = SchemaGeneratorEngineV2()
                generated.append(sg.generate(project_id, "FAQ", payload))

        elif category in ["Schema", "Trust"]:
            from app.core.schema_generator_engine_v2 import SchemaGeneratorEngineV2
            sg = SchemaGeneratorEngineV2()
            generated.append(sg.generate(project_id, "Product" if category == "Trust" else "Organization", payload))

        elif category == "Internal Links":
            from app.core.internal_link_builder import InternalLinkBuilder
            il = InternalLinkBuilder()
            generated.append(il.build_links(project_id, payload))

        elif category in ["Authority", "Evidence"]:
            from app.core.authority_builder_engine import AuthorityBuilderEngine
            ab = AuthorityBuilderEngine()
            generated.append(ab.generate(project_id, "Case Study", payload))
            generated.append(ab.generate(project_id, "Authority Page", payload))

        else:
            # Fallback default Organization schema
            from app.core.schema_generator_engine_v2 import SchemaGeneratorEngineV2
            sg = SchemaGeneratorEngineV2()
            generated.append(sg.generate(project_id, "Organization", payload))

        return {"status": "success", "task_id": task_id, "generated_assets": generated}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting and running task {task_id}: {e}")
        # Reset task status to failed on exceptions
        supabase_client.table("execution_tasks")\
            .update({"status": "failed"})\
            .eq("id", task_id)\
            .execute()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execution/complete/{task_id}")
def complete_execution_task(
    task_id: str,
    user_id: str = Depends(get_current_user)
):
    """Marks a running task as completed, computes actual score gains, and logs learning memory trends."""
    try:
        # Check task existence and user project ownership
        task_resp = supabase_client.table("execution_tasks").select("*, projects!inner(user_id)").eq("id", task_id).execute()
        if not task_resp.data:
            raise HTTPException(status_code=404, detail="Task not found")
        task = task_resp.data[0]
        if task["projects"]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
            
        project_id = task["project_id"]

        # Update task status to completed
        supabase_client.table("execution_tasks")\
            .update({"status": "completed"})\
            .eq("id", task_id)\
            .execute()

        # Invalidate project caches
        invalidate_project_cache(project_id)

        # Retrieve project payload for computing gains
        payload = _get_project_data_payload(project_id)

        from app.core.execution_learning_engine import ExecutionLearningEngine
        ele = ExecutionLearningEngine()
        metrics = ele.record_completion(project_id, task_id, payload)

        return {"status": "success", "task_id": task_id, "metrics": metrics}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))




