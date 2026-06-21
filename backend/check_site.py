import httpx
import asyncio

async def check():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
        paths = ["/sitemap.xml", "/robots.txt", "/manifest.json", "/about", "/services", "/contact", "/api"]
        for path in paths:
            try:
                r = await client.get(f"https://thelibrarycompany.com{path}", headers=headers, timeout=10)
                ct = r.headers.get("content-type", "")
                print(f"{path}: {r.status_code} ({len(r.text)} bytes) | {ct[:50]}")
                if r.status_code == 200 and len(r.text) < 2000:
                    print("  CONTENT:", r.text[:500])
                elif r.status_code == 200:
                    print("  PREVIEW:", r.text[:300])
            except Exception as e:
                print(f"{path}: ERROR - {e}")

asyncio.run(check())
