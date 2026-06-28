import os
import sys
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load env variables
load_dotenv()

from app.core.grounding_engine_v2 import GroundingEngineV2
from app.core.domain_identity_validator import DomainIdentityValidator

PROJECT_ID = None  # None will fetch the latest project from projects table
DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    print(f"Connecting to database via PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    try:
        # 1. Fetch project
        pid = PROJECT_ID
        if not pid:
            cur.execute("SELECT id FROM projects ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            if not row:
                print("No projects found in database.")
                return
            pid = row["id"]
        
        cur.execute("SELECT * FROM projects WHERE id = %s", (pid,))
        project = cur.fetchone()
        if not project:
            print("Project not found.")
            return
        print(f"Loaded project: {project['project_name']} ({project['website_url']}) ID: {project['id']}")
        
        # 2. Fetch crawled pages
        cur.execute("SELECT * FROM web_pages WHERE project_id = %s", (pid,))
        crawled_pages = cur.fetchall()
        print(f"Loaded {len(crawled_pages)} crawled pages.")
        
        # 3. Fetch business profile
        cur.execute("SELECT * FROM business_profiles WHERE project_id = %s ORDER BY generated_at DESC LIMIT 1", (pid,))
        bp = cur.fetchone() or {}
        if not bp:
            print("WARNING: No business profile found!")
        
        # 4. Fetch competitors
        cur.execute("SELECT * FROM competitors WHERE project_id = %s", (pid,))
        competitors = cur.fetchall()
        
        # 5. Fetch entity nodes
        cur.execute("SELECT * FROM entity_nodes WHERE project_id = %s", (pid,))
        entity_nodes = cur.fetchall()
        
        # 6. Fetch verified facts
        # We join verified_facts with extracted_facts to get their values
        cur.execute("""
            SELECT ef.*, vf.verification_score, vf.verification_status 
            FROM verified_facts vf 
            JOIN extracted_facts ef ON vf.extracted_fact_id = ef.id 
            WHERE ef.project_id = %s
        """, (pid,))
        raw_verified_facts = cur.fetchall()
        
        verified_facts = []
        for vf in raw_verified_facts:
            verified_facts.append({
                "fact_category": vf.get("fact_category", "general"),
                "fact_value": vf.get("fact_value", ""),
                "evidence_text": vf.get("evidence_text", ""),
                "confidence_score": float(vf.get("confidence_score") or 1.0),
                "source_url": vf.get("source_url", "")
            })
        print(f"Loaded {len(verified_facts)} verified facts.")
        
        # Construct state payload
        state = {
            "website_url": project["website_url"],
            "crawled_pages": crawled_pages,
            "verified_facts": verified_facts,
            "business_intelligence": {
                "company_name": bp.get("company_name") or "",
                "industry": bp.get("industry") or "",
                "description": bp.get("description") or "",
                "mission": bp.get("mission") or "",
                "vision": bp.get("vision") or "",
                "usp": bp.get("usp") or "",
                "target_audience": bp.get("target_audience") or "",
                "strengths": bp.get("strengths") or "",
                "weaknesses": bp.get("weaknesses") or "",
                "opportunities": bp.get("opportunities") or "",
                "risks": bp.get("risks") or "",
                "trust_signals": bp.get("trust_signals") or "",
                "business_model": bp.get("business_model") or "",
                "ai_visibility_opportunities": bp.get("ai_visibility_opportunities") or "",
                "pre_query_discovery": {
                    "products": ["Lattice Program", "ReLaunchHER Program"] if "Lattice" in str(list(bp.values())) else [],
                    "services": [],
                    "programs": ["Lattice Program", "ReLaunchHER Program"] if "Lattice" in str(list(bp.values())) else [],
                    "founders": [],
                    "certifications": []
                }
            },
            "competitors": competitors,
            "entity_nodes": entity_nodes,
            "questions": [],
            "keywords": []
        }
        
        # Run validators
        identity_validator = DomainIdentityValidator()
        identity_res = identity_validator.validate(pid, state)
        
        grounding_engine = GroundingEngineV2()
        grounding_res = grounding_engine.run(state, identity_res)
        
        print("\n=== IDENTITY CHECK RESULTS ===")
        print(f"Identity Match Score: {identity_res['identity_match_score']}%")
        print(f"Conflicts: {identity_res.get('identity_conflicts', [])}")
        
        print("\n=== GROUNDING CHECK RESULTS ===")
        print(f"Grounding Score: {grounding_res['grounding_score']}%")
        print(f"Domain Consistency Score: {grounding_res['domain_consistency_score']}%")
        print(f"Status: {grounding_res['status']}")
        
        print("\nDetailed Grounding Verification:")
        for check in grounding_res["details"]["checks"]:
            print(f"- [{check['status']}] {check['category']} -> {check['entity']}")
            if check['status'] != "VERIFIED":
                print(f"  Evidence/Snippet: {check['evidence_snippet']}")

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
