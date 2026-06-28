import sys
sys.path.insert(0, ".")

import asyncio
from supabase import create_client, ClientOptions
from app.core.config import settings
from app.core.entity_grounding_engine import EntityGroundingEngine

async def main():
    user_id = "00000000-0000-4000-a000-000000000001"
    client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY,
        options=ClientOptions(
            headers={"X-Mock-User": user_id}
        )
    )
    
    # Get the latest analysis run overall
    run_resp = client.table("analysis_runs").select("*").order("started_at", desc=True).limit(1).execute()
    if not run_resp.data:
        print("No runs found in DB")
        return
    run = run_resp.data[0]
    project_id = run["project_id"]
    run_id = run["id"]
    print("Latest Run ID:", run_id)
    print("Project ID:", project_id)
    
    # Get project info
    proj_resp = client.table("projects").select("*").eq("id", project_id).execute()
    if not proj_resp.data:
        print("Project not found for run")
        return
    project = proj_resp.data[0]
    
    # Fetch web pages
    pages_resp = client.table("web_pages").select("*").eq("project_id", project_id).execute()
    crawled_pages = [{
        "id": p["id"],
        "url": p["url"],
        "title": p["title"] or "",
        "meta_description": p["meta_description"] or "",
        "markdown_content": p["content"] or ""
    } for p in pages_resp.data]
    
    # Fetch verified facts
    facts_resp = client.table("extracted_facts").select("*").eq("project_id", project_id).execute()
    verified_facts = [{
        "fact_category": f["fact_category"],
        "fact_key": f["fact_key"],
        "fact_value": f["fact_value"],
        "source_url": f["source_url"],
        "evidence_text": f["evidence_text"]
    } for f in facts_resp.data]
    
    # Fetch business profile
    bi_resp = client.table("business_profiles").select("*").eq("project_id", project_id).order("generated_at", desc=True).limit(1).execute()
    bi = bi_resp.data[0] if bi_resp.data else {}
    
    # Construct mock state
    state = {
        "website_url": "https://www.thelibrarycompany.com",
        "crawled_pages": crawled_pages,
        "verified_facts": verified_facts,
        "business_intelligence": bi,
        "questions": [],
        "keywords": []
    }
    
    engine = EntityGroundingEngine()
    res = engine.run(state)
    print("=== GROUNDING CHECK ===")
    print(f"Score: {res['grounding_score']}%")
    print(f"Passed checks: {res['details']['successful_checks']}/{res['details']['total_checks']}")
    print("\nFAILED CHECKS:")
    for check in res["details"]["checks"]:
        if not check["matched"]:
            print(f"- Item: {check['item']}")
            print(f"  Value: {check['value']}")
            print(f"  Detail: {check['detail']}")

if __name__ == "__main__":
    asyncio.run(main())
