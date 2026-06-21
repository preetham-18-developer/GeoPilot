import httpx
import asyncio

PROJECT_ID = "7ce5d95f-898d-4322-962c-9b93854b8d21"
# Get the user_id from project
import sys
sys.path.insert(0, ".")

async def trigger_analysis():
    # First check what user owns the project
    from app.core.supabase import supabase_client
    proj = supabase_client.table("projects").select("id, user_id, website_url, status").eq("id", PROJECT_ID).execute()
    if proj.data:
        p = proj.data[0]
        user_id = p["user_id"]
        print(f"Project: {p['website_url']}, Status: {p['status']}, User: {user_id}")
        
        # Trigger analysis using the real user_id as mock token
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"http://localhost:8000/api/v1/analysis/run/{PROJECT_ID}",
                headers={"Authorization": f"Bearer mock-{user_id}"},
                timeout=30
            )
            print(f"Analysis trigger: {r.status_code}")
            print(r.json())
    else:
        print("Project not found!")

asyncio.run(trigger_analysis())
