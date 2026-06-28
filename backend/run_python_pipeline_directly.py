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
    project_id = "0c181b5f-6deb-4789-a2b0-5de992ae8279"
    run_id = "6536760a-6439-46d3-a9c3-454109036fd7"
    website_url = "https://www.thelibrarycompany.com"
    user_id = "00000000-0000-4000-a000-000000000001"
    
    # Create authenticated client to bypass RLS
    client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY,
        options=ClientOptions(
            headers={"X-Mock-User": user_id}
        )
    )
    token = _client_ctx.set(client)
    
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

