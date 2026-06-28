import asyncio
from app.core.supabase import supabase_client

def inspect():
    # Fetch projects
    p_resp = supabase_client.table("projects").select("*").execute()
    print("=== PROJECTS ===")
    for p in p_resp.data:
        print(f"ID: {p['id']} | Name: {p['project_name']} | URL: {p['website_url']} | Status: {p['status']}")
    
    # Fetch analysis runs
    r_resp = supabase_client.table("analysis_runs").select("*").execute()
    print("\n=== RUNS ===")
    for r in r_resp.data:
        print(f"ID: {r['id']} | Project ID: {r['project_id']} | Status: {r['status']}")

inspect()
