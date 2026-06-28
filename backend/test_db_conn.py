import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL", "https://wnjnebqwgrjfsmbkgiua.supabase.co")
supabase_key = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Induam5lYnF3Z3JqZnNtYmtnaXVhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk3MTQwMzksImV4cCI6MjA5NTI5MDAzOX0.T60uDBZGi2xXl4HONMnU9VNqfpFLuv7f_E50wRyM2Wg")

print(f"Connecting to URL: {supabase_url}")
print(f"Key preview: {supabase_key[:20]}...{supabase_key[-20:]}")

try:
    client = create_client(supabase_url, supabase_key)
    
    # Let's list projects
    p_resp = client.table("projects").select("*").execute()
    print(f"Projects count: {len(p_resp.data)}")
    for p in p_resp.data:
        print(f"Project: {p.get('id')} | Name: {p.get('project_name')} | Status: {p.get('status')}")
        
    # Let's count questions
    q_resp = client.table("questions").select("id", count="exact").limit(1).execute()
    print(f"Questions count: {q_resp.count}")
    
    # Let's count keywords
    k_resp = client.table("keywords").select("id", count="exact").limit(1).execute()
    print(f"Keywords count: {k_resp.count}")
    
    # Let's count verified_facts
    vf_resp = client.table("verified_facts").select("id", count="exact").limit(1).execute()
    print(f"Verified facts count: {vf_resp.count}")
    
except Exception as e:
    print(f"ERROR: {e}")
