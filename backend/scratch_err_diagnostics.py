import os
import sys
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
        
        cur.execute("SELECT * FROM error_diagnostics WHERE project_id = %s", (pid,))
        errs = cur.fetchall()
        print(f"=== ERROR DIAGNOSTICS ({len(errs)}) ===")
        for e in errs:
            print(e)
            
        cur.execute("SELECT * FROM reliability_reports WHERE project_id = %s", (pid,))
        reps = cur.fetchall()
        print(f"=== RELIABILITY REPORTS ({len(reps)}) ===")
        for r in reps:
            print(r)
            
        cur.execute("SELECT * FROM agent_health_logs WHERE project_id = %s", (pid,))
        logs = cur.fetchall()
        print(f"=== AGENT HEALTH LOGS ({len(logs)}) ===")
        for l in logs:
            print(l)
            
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
