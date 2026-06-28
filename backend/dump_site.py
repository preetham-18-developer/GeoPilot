import httpx
from bs4 import BeautifulSoup

def dump_page(url):
    print(f"=== FETCHING {url} ===")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = httpx.get(url, headers=headers, follow_redirects=True, verify=False)
        print(f"Status: {r.status_code}")
        print(f"Final URL: {r.url}")
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Title
        print(f"Title tag: {soup.title.string if soup.title else 'None'}")
        
        # Meta description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        print(f"Meta Description: {desc_tag.get('content') if desc_tag else 'None'}")
        
        # H1 heading
        h1_tag = soup.find("h1")
        print(f"H1: {h1_tag.get_text(strip=True) if h1_tag else 'None'}")
        
        # Body preview (first 500 chars of visible text)
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        print(f"Text Preview: {text[:1000]}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    print()

dump_page("https://www.thelibrarycompany.com")
dump_page("https://www.thelibrarycompany.com/about")
dump_page("https://www.thelibrarycompany.com/services")
dump_page("https://www.thelibrarycompany.com/contact")
