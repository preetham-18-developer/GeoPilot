import asyncio

async def test_playwright():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1280, "height": 900}
            )
            page = await context.new_page()
            print("Navigating to thelibrarycompany.com/about...")
            await page.goto("https://thelibrarycompany.com/about", wait_until="networkidle", timeout=30000)

            await page.wait_for_timeout(3000)
            
            # Get rendered content
            html = await page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract title
            title = soup.title.string if soup.title else "No title"
            print(f"Title: {title}")
            
            # Remove noise
            for tag in soup(["script", "style", "noscript", "svg"]):
                tag.decompose()
            
            # Get text
            body_text = []
            for elem in soup.find_all(["h1", "h2", "h3", "p", "li"]):
                text = elem.get_text(separator=" ", strip=True)
                if text and len(text) > 10:
                    body_text.append(text)
            
            content = "\n".join(body_text[:50])  # First 50 elements
            word_count = len(content.split())
            print(f"\nWord count: {word_count}")
            print(f"\n=== CONTENT PREVIEW ===")
            print(content[:3000])
            
        finally:
            await browser.close()

asyncio.run(test_playwright())
