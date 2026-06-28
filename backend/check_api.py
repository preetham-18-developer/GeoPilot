import httpx

project_id = "ac859c4b-51d5-44fa-adbb-3ed93d86b458"
url = f"http://localhost:8000/api/v1/projects/{project_id}/questions?page=1&limit=5"
headers = {"Authorization": "Bearer mock-00000000-0000-4000-a000-000000000001"}

try:
    resp = httpx.get(url, headers=headers)
    print("Questions Status Code:", resp.status_code)
    print("Questions Response Snippet:", resp.text[:300])
    
    url_kw = f"http://localhost:8000/api/v1/projects/{project_id}/keywords?page=1&limit=5"
    resp_kw = httpx.get(url_kw, headers=headers)
    print("Keywords Status Code:", resp_kw.status_code)
    print("Keywords Response Snippet:", resp_kw.text[:300])
except Exception as e:
    print("Error:", e)
