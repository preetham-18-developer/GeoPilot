import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT id FROM projects ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return
        pid = row["id"]
        
        cur.execute("SELECT * FROM execution_checkpoints WHERE project_id = %s AND status = 'completed' ORDER BY created_at DESC LIMIT 1", (pid,))
        cp = cur.fetchone()
        if cp:
            state = cp["resume_data"]
            if isinstance(state, str):
                state = json.loads(state)
            
            bi = state.get("business_intelligence", {})
            print("=== ACTUAL BI PRE_QUERY_DISCOVERY ===")
            print(json.dumps(bi.get("pre_query_discovery", {}), indent=2))
            
            print("\n=== ACTUAL COMPETITORS ===")
            print(json.dumps(state.get("competitors", []), indent=2))
            
            print("\n=== ACTUAL ENTITY NODES ===")
            print(json.dumps(state.get("entity_nodes", []), indent=2))
            
            # Print any other pre_query fields
            print("\n=== ACTUAL BI FIELDS ===")
            for k in ['company_name', 'description', 'mission', 'vision', 'usp', 'target_audience']:
                print(f"{k}: {bi.get(k)}")
                
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
