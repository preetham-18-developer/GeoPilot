import urllib.request
import ssl

def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    url = "https://www.thelibrarycompany.com"
    print(f"Fetching {url}...")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            html = response.read().decode('utf-8')
            print(f"Status: {response.status}")
            print(f"HTML length: {len(html)}")
            print("Snippet:")
            print(html[:1000])
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
