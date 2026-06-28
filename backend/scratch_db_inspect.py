import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    try:
        # Get last run
        cur.execute("SELECT * FROM analysis_runs ORDER BY started_at DESC LIMIT 1")
        run = cur.fetchone()
        if not run:
            print("No analysis runs found")
            return
        
        print("=== ANALYSIS RUN ===")
        for k, v in run.items():
            print(f"{k}: {v}")
        print("-" * 50)
        
        project_id = run["project_id"]
        
        # Get project
        cur.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        project = cur.fetchone()
        print("=== PROJECT ===")
        for k, v in project.items():
            print(f"{k}: {v}")
        print("-" * 50)
        
        # Get business profiles
        cur.execute("SELECT * FROM business_profiles WHERE project_id = %s ORDER BY generated_at DESC", (project_id,))
        bps = cur.fetchall()
        print(f"=== BUSINESS PROFILES (Found: {len(bps)}) ===")
        for bp in bps:
            print(f"ID: {bp['id']}")
            print(f"Company Name: {bp['company_name']}")
            print(f"Description: {bp['description']}")
            print(f"Generated At: {bp['generated_at']}")
            print("-" * 30)
            
        # Get competitors
        cur.execute("SELECT * FROM competitors WHERE project_id = %s", (project_id,))
        competitors = cur.fetchall()
        print(f"=== COMPETITORS (Found: {len(competitors)}) ===")
        for c in competitors:
            print(c)
            
        # Get entity nodes
        cur.execute("SELECT * FROM entity_nodes WHERE project_id = %s", (project_id,))
        nodes = cur.fetchall()
        print(f"=== ENTITY NODES (Found: {len(nodes)}) ===")
        for n in nodes:
            print(f"{n['entity_name']} ({n['entity_type']}) - {n['properties']}")
            
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
