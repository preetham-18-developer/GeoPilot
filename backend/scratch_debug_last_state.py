import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.core.grounding_engine_v2 import GroundingEngineV2
from app.core.domain_identity_validator import DomainIdentityValidator

DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
        
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT id FROM projects ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            print("No project found")
            return
        pid = row["id"]
        print(f"Project ID: {pid}")
        
        # Get crawled pages
        cur.execute("SELECT * FROM web_pages WHERE project_id = %s", (pid,))
        db_pages = cur.fetchall()
        crawled_pages = [{
            "id": page["id"],
            "url": page["url"],
            "title": page["title"] or "",
            "meta_description": page["meta_description"] or "",
            "markdown_content": page["content"] or page["meta_description"] or ""
        } for page in db_pages]
        print(f"Crawled pages: {len(crawled_pages)}")
        
        # Get last completed checkpoint state
        cur.execute("SELECT * FROM execution_checkpoints WHERE project_id = %s AND status = 'completed' ORDER BY created_at DESC LIMIT 1", (pid,))
        cp = cur.fetchone()
        if not cp:
            print("No completed checkpoint found")
            return
            
        state = cp["resume_data"]
        if isinstance(state, str):
            state = json.loads(state)
            
        # Put crawled_pages back in
        state["crawled_pages"] = crawled_pages
        
        # Print business intelligence profile values
        bi = state.get("business_intelligence", {})
        print("\n=== BUSINESS INTELLIGENCE PROFILE ===")
        print(f"Company name: {bi.get('company_name')}")
        print(f"Description: {bi.get('description')}")
        print(f"Mission: {bi.get('mission')}")
        print(f"Vision: {bi.get('vision')}")
        print(f"USP: {bi.get('usp')}")
        print(f"Target Audience: {bi.get('target_audience')}")
        print(f"Pre-query Products: {bi.get('pre_query_discovery', {}).get('products')}")
        print(f"Pre-query Services: {bi.get('pre_query_discovery', {}).get('services')}")
        print(f"Pre-query Founders: {bi.get('pre_query_discovery', {}).get('founders')}")
        
        # Run validators
        print("\n=== RUNNING VALIDATORS ===")
        dv = DomainIdentityValidator()
        identity_res = dv.validate(pid, state)
        print(f"Identity Score: {identity_res['identity_match_score']}%")
        print(f"Identity Conflicts: {identity_res['identity_conflicts']}")
        
        engine = GroundingEngineV2()
        result = engine.run(state, identity_res)
        print(f"Grounding Score: {result['grounding_score']}%")
        print(f"Domain Conflicts: {result['details']['domain_conflicts']}")
        print(f"Status: {result['status']}")
        
        print("\n=== INDIVIDUAL CHECKS ===")
        for check in result["details"]["checks"]:
            print(f"- [{check['status']}] {check['category']}: {check['entity']}")
            print(f"  Evidence: {check['evidence_snippet']}")
            
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
