import sys
sys.path.insert(0, ".")

import asyncio
from supabase import create_client, ClientOptions
from app.core.config import settings

async def main():
    user_id = "00000000-0000-4000-a000-000000000001"
    supabase_client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY,
        options=ClientOptions(
            headers={"X-Mock-User": user_id}
        )
    )
    
    print("=== LATEST RUNS ===")
    try:
        runs_res = supabase_client.table("analysis_runs").select("*").order("started_at", desc=True).limit(10).execute()
        for run in (runs_res.data or []):
            print(f"Run ID: {run.get('id')}")
            print(f"Project ID: {run.get('project_id')}")
            print(f"Status: {run.get('status')}")
            print(f"Error Message: {run.get('error_message')}")
            print(f"Started At: {run.get('started_at')}")
            print("-" * 50)
    except Exception as e:
        print("Error fetching runs:", e)
        
    print("\n=== LATEST PROJECTS ===")
    try:
        proj_res = supabase_client.table("projects").select("*").limit(10).execute()
        for proj in (proj_res.data or []):
            print(f"Project ID: {proj.get('id')}")
            print(f"Name: {proj.get('project_name') or proj.get('name')}")
            print(f"Website: {proj.get('website_url') or proj.get('websiteUrl')}")
            print(f"Status: {proj.get('status')}")
            print("-" * 50)
    except Exception as e:
        print("Error fetching projects:", e)

if __name__ == "__main__":
    asyncio.run(main())


