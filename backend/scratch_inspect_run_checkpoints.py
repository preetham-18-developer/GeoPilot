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
        
        cur.execute("SELECT * FROM execution_checkpoints WHERE project_id = %s", (pid,))
        checkpoints = cur.fetchall()
        print(f"=== CHECKPOINTS FOUND: {len(checkpoints)} ===")
        for cp in checkpoints:
            print(f"Node: {cp['node_name']}, Status: {cp['status']}, Created At: {cp['created_at']}")
            # State size
            state_data = cp.get("resume_data")
            if state_data:
                if isinstance(state_data, str):
                    print(f"  State size (chars): {len(state_data)}")
                else:
                    print(f"  State keys: {list(state_data.keys())}")
                    
        # Let's inspect the last completed checkpoint
        cur.execute("SELECT * FROM execution_checkpoints WHERE project_id = %s AND status = 'completed' ORDER BY created_at DESC LIMIT 1", (pid,))
        last_cp = cur.fetchone()
        if last_cp:
            print("\n=== LAST COMPLETED CHECKPOINT STATE ===")
            state = last_cp["resume_data"]
            if isinstance(state, str):
                state = json.loads(state)
            
            # Print specific keys
            print("website_url:", state.get("website_url"))
            print("business_intelligence keys:", list(state.get("business_intelligence", {}).keys()))
            print("company_name:", state.get("business_intelligence", {}).get("company_name"))
            print("crawled_pages count:", len(state.get("crawled_pages", [])))
            print("competitors:", state.get("competitors"))
            print("entity_nodes:", state.get("entity_nodes"))
            print("raw_facts count:", len(state.get("raw_facts", [])))
            print("verified_facts count:", len(state.get("verified_facts", [])))
            
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
