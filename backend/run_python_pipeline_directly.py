import sys
sys.path.insert(0, ".")

import asyncio
import logging

# Configure logging to console
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from app.agents.graph import run_analysis_pipeline
from app.core.config import settings
from app.core.supabase import _client_ctx
from supabase import create_client, ClientOptions

async def main():
    project_id = "79e4bb3c-de1f-45a3-899c-9a1dbe36b899"
    website_url = "https://www.thelibrarycompany.com/"
    user_id = "f0a29fd8-dc5b-4724-9099-e7e384747daa"
    
    # Create authenticated client to bypass RLS
    client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY,
        options=ClientOptions(
            headers={"X-Mock-User": user_id}
        )
    )
    token = _client_ctx.set(client)
    
    import uuid
    run_id = str(uuid.uuid4())
    client.table("analysis_runs").insert({
        "id": run_id,
        "project_id": project_id,
        "run_type": "full",
        "status": "running"
    }).execute()
    
    print("=== STARTING DIRECT PYTHON PIPELINE RUN ===")
    try:
        await run_analysis_pipeline(project_id, run_id, website_url)
        print("=== PIPELINE RUN COMPLETED SUCCESSFULLY ===")
    except Exception as e:
        print("=== PIPELINE RUN FAILED ===")
        import traceback
        traceback.print_exc()
    finally:
        _client_ctx.reset(token)

if __name__ == "__main__":
    asyncio.run(main())

