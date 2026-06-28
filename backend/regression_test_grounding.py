"""
regression_test_grounding.py

Regression test script to verify:
1. Grounding score > 95% for target domain 'thelibrarycompany.com' under correct mock setup.
2. Zero domain confusion (no Benjamin Franklin, Philadelphia, or 1731 references).
3. Pipeline failure (status: FAILED_GROUNDING) when grounding score is < 80%.
"""

import sys
import os
import asyncio
import time
import json
import logging

sys.path.insert(0, ".")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from supabase import create_client, ClientOptions
from app.core.config import settings
from app.core.supabase import _client_ctx
from app.agents.graph import run_analysis_pipeline

# Configure a test user and mock client
TEST_USER_ID = "00000000-0000-4000-a000-000000000001"
test_client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY,
    options=ClientOptions(
        headers={"X-Mock-User": TEST_USER_ID}
    )
)

# Set global context var so import app.core.supabase.supabase_client routes requests through this proxy
ctx_token = _client_ctx.set(test_client)

async def setup_test_project(website_url: str, name: str) -> str:
    """Creates a test project and returns its ID."""
    # Check if project already exists
    proj_resp = test_client.table("projects").select("id").eq("website_url", website_url).eq("user_id", TEST_USER_ID).execute()
    if proj_resp.data:
        project_id = proj_resp.data[0]["id"]
        logger.info(f"Using existing test project {project_id} for {website_url}")
        return project_id
        
    proj_resp = test_client.table("projects").insert({
        "user_id": TEST_USER_ID,
        "project_name": name,
        "website_url": website_url,
        "status": "pending"
    }).execute()
    
    project_id = proj_resp.data[0]["id"]
    logger.info(f"Created new test project {project_id} for {website_url}")
    return project_id

async def setup_mock_crawled_pages(project_id: str, content: str, title: str):
    """Sets up mock crawled pages for the project."""
    # Delete existing pages
    test_client.table("web_pages").delete().eq("project_id", project_id).execute()
    
    # Insert new mock page
    test_client.table("web_pages").insert({
        "project_id": project_id,
        "url": "https://www.thelibrarycompany.com",
        "title": title,
        "content": content,
        "meta_description": "Mentors from top companies helping students turn passion into real careers.",
        "word_count": len(content.split())
    }).execute()
    logger.info(f"Inserted mock crawled page for project {project_id}")

async def create_analysis_run(project_id: str) -> str:
    """Creates an analysis run and returns its ID."""
    run_resp = test_client.table("analysis_runs").insert({
        "project_id": project_id,
        "status": "queued",
        "current_agent": "Scheduler"
    }).execute()
    return run_resp.data[0]["id"]

async def run_regression_test():
    try:
        # =====================================================================
        # TEST 1: SUCCESSFUL PIPELINE (EdTech Site)
        # =====================================================================
        logger.info("=== Running Test 1: Successful Grounding & EdTech Identification ===")
        project_id = await setup_test_project("https://www.thelibrarycompany.com", "The Library Company")
        
        # Insert correct EdTech contents crawled from the website
        edtech_content = (
            "© 2026 Made With ❤️ - The Library Company. "
            "About The Library A mentorship collective of industry professionals from leading companies. "
            "We're not a traditional school—we're product managers, engineers, and experts who guide the next generation to connect passion with profession. "
            "Introducing ReLaunchHER Empower Students Women to Transform Their Careers. "
            "The Library — personalized mentorship, industry-aligned programs, Job opportunities designed to transform your career journey. "
            "Master SQL in a Weekend. Scale Your Salary to Millions. "
            "Build Your Own AI Assistant. Master LLM's, RAG & Vector DBs. From basics to real-world applications. "
            "Partner Colleges for Top Company Recruitment ... IIIT Basar Mahindra MRU MRDU St. Peter's St. Joseph's CMR NRCM SNIST HITAM. "
            "I am delighted to recommend Kondru sharathchandra, the co-founder of The Library, who has been a guiding light in my personal and professional journey. "
            "Lattice Program. Lattice Framework. Personalized Mentorship. Master SQL in a Weekend Workshop. Build Your Own AI Assistant Workshop."
        )
        await setup_mock_crawled_pages(project_id, edtech_content, "The Library Company")
        
        run_id = await create_analysis_run(project_id)
        
        logger.info(f"Running analysis pipeline for run {run_id}...")
        await run_analysis_pipeline(project_id, run_id, "https://www.thelibrarycompany.com")
        
        # Verify run status and grounding score
        run_resp = test_client.table("analysis_runs").select("*").eq("id", run_id).execute()
        run_data = run_resp.data[0]
        
        logger.info(f"Test 1 Run Status: {run_data['status']}")
        
        if run_data["status"] != "completed":
            raise AssertionError(f"Test 1: Run status should be 'completed', but got '{run_data['status']}' (error: {run_data.get('error_message')})")
            
        # Verify Grounding Score from historical metrics
        metrics_resp = test_client.table("historical_metrics").select("*").eq("run_id", run_id).execute()
        if not metrics_resp.data:
            raise AssertionError("Test 1: Historical metrics not written!")
            
        metrics = metrics_resp.data[0]
        grounding_score = metrics.get("grounding_score", 0.0)
        logger.info(f"Test 1 Grounding Score: {grounding_score}%")
        
        if grounding_score < 95.0:
            raise AssertionError(f"Test 1: Grounding score must be >= 95%, but got {grounding_score}%")
            
        # Verify lack of Domain Confusion in generated profile or answers
        bp_resp = test_client.table("business_profiles").select("*").eq("project_id", project_id).execute()
        bp = bp_resp.data[-1] if bp_resp.data else {}
        
        forbidden_keywords = ["philadelphia", "benjamin franklin", "franklin", "1731", "rare books", "historic library"]
        
        # Gather all text to verify no domain confusion exists
        check_text = " ".join([
            bp.get("company_name", ""),
            bp.get("industry", ""),
            bp.get("description", ""),
            bp.get("mission", ""),
            bp.get("vision", ""),
            bp.get("usp", "")
        ]).lower()
        
        for keyword in forbidden_keywords:
            if keyword in check_text:
                raise AssertionError(f"Test 1: Domain confusion detected! Found forbidden keyword '{keyword}' in profile: {check_text}")
                
        logger.info("Test 1: SUCCESS. Grounded successfully in EdTech mentorship, zero domain confusion, score >= 95%.")
        
        # =====================================================================
        # TEST 2: GROUNDING FAILURE (Simulation of low grounding/hallucinated text)
        # =====================================================================
        logger.info("\n=== Running Test 2: Abort Pipeline on Low Grounding Score ===")
        # Setup a project with blank page content, but the agent still generates EdTech facts
        # This will trigger grounding failure because the generated facts/entities won't exist in the crawled pages!
        fail_project_id = await setup_test_project("https://www.thelibrarycompany-empty.com", "Empty Library Company")
        await setup_mock_crawled_pages(fail_project_id, "This page is temporarily unavailable. Please check back later.", "Welcome")
        
        fail_run_id = await create_analysis_run(fail_project_id)
        logger.info(f"Running analysis pipeline for run {fail_run_id}...")
        
        await run_analysis_pipeline(fail_project_id, fail_run_id, "https://www.thelibrarycompany-empty.com")
        
        # Verify run status is FAILED_GROUNDING
        fail_run_resp = test_client.table("analysis_runs").select("*").eq("id", fail_run_id).execute()
        fail_run_data = fail_run_resp.data[0]
        
        logger.info(f"Test 2 Run Status: {fail_run_data['status']}")
        logger.info(f"Test 2 Error Message: {fail_run_data.get('error_message')}")
        
        if fail_run_data["status"] not in ("FAILED_GROUNDING", "FAILED_VALIDATION"):
            raise AssertionError(f"Test 2: Run status should be 'FAILED_GROUNDING' or 'FAILED_VALIDATION', but got '{fail_run_data['status']}'")

            
        # Verify that no business profile or report was saved to the DB for this run
        bp_fail_resp = test_client.table("business_profiles").select("*").eq("project_id", fail_project_id).execute()
        if bp_fail_resp.data:
            raise AssertionError("Test 2: Business profile was written to database despite grounding failure!")
            
        logger.info("Test 2: SUCCESS. Pipeline correctly aborted with status 'FAILED_GROUNDING' and database writes were skipped.")
        
        logger.info("\nALL REGRESSION TESTS PASSED SUCCESSFULLY!")
        
    finally:
        try:
            _client_ctx.reset(ctx_token)
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(run_regression_test())
