import sys
sys.path.insert(0, ".")

import asyncio
from supabase import create_client, ClientOptions
from app.core.config import settings

async def main():
    project_id = "fe474724-1bd0-4a81-8154-4ed2d8feeff7"
    user_id = "00000000-0000-4000-a000-000000000001"
    supabase_client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY,
        options=ClientOptions(
            headers={"X-Mock-User": user_id}
        )
    )
    
    # Fetch crawled pages
    pages_resp = supabase_client.table("web_pages").select("*").eq("project_id", project_id).execute()
    if pages_resp.data:
        print("WEB_PAGES COLUMNS:", list(pages_resp.data[0].keys()))
    else:
        print("No pages found in web_pages")
        
    crawled_pages = [{
        "url": p["url"],
        "title": p["title"] or "",
        "content_repr": repr(p.get("content")),
        "word_count": p.get("word_count"),
        "meta_description": p.get("meta_description") or ""
    } for p in pages_resp.data]
    
    # Fetch business profile
    bi_resp = supabase_client.table("business_profiles").select("*").eq("project_id", project_id).execute()
    bi = bi_resp.data[-1] if bi_resp.data else {}
    
    # Let's inspect other tables for project
    facts_resp = supabase_client.table("extracted_facts").select("*").eq("project_id", project_id).execute()
    verified_facts = [{
        "fact_type": f["fact_category"],
        "fact_key": f["fact_key"],
        "fact_value": f["fact_value"],
        "source_url": f["source_url"],
        "evidence": f["evidence_text"]
    } for f in facts_resp.data]
    
    competitors_resp = supabase_client.table("competitors").select("*").eq("project_id", project_id).execute()
    competitors = [{"competitor_name": c["competitor_name"]} for c in competitors_resp.data]
    
    nodes_resp = supabase_client.table("entity_nodes").select("*").eq("project_id", project_id).execute()
    nodes = [{"entity_name": n["entity_name"], "entity_type": n["entity_type"], "properties": n.get("properties", {})} for n in nodes_resp.data]
    
    print("=== CRAWLED PAGES ===")
    for page in crawled_pages:
        print(f"URL: {page['url']}")
        print(f"Title: {page['title']}")
        print(f"Content Repr: {page['content_repr']}")
        print(f"Word Count: {page['word_count']}")
        print(f"Meta Description: {page['meta_description']}")
        print("-" * 50)


        
    print("\nCompetitors:", competitors)
    print("Nodes:", nodes)
    print("Business Profile:", bi)
    print("Facts Count:", len(verified_facts))
    
if __name__ == "__main__":
    asyncio.run(main())
