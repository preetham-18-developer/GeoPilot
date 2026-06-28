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
        
        cur.execute("SELECT * FROM web_pages WHERE project_id = %s LIMIT 1", (pid,))
        page = cur.fetchone()
        if page:
            print("Keys in web_pages:", list(page.keys()))
            for k, v in page.items():
                print(f"{k}: {repr(v)[:200]}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
