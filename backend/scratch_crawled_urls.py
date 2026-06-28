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
            print("No projects")
            return
        pid = row["id"]
        
        cur.execute("SELECT url, title, length(content) as content_len FROM web_pages WHERE project_id = %s", (pid,))
        pages = cur.fetchall()
        print(f"Crawled pages for project {pid}:")
        for p in pages:
            print(f"- URL: {p['url']}")
            print(f"  Title: {p['title']}")
            print(f"  Length: {p['content_len']}")
            
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
