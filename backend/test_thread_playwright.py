import threading
import queue
import asyncio
import sys

def render_page_in_thread(url):
    res_queue = queue.Queue()
    
    def worker():
        try:
            import asyncio
            import sys
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
            async def main():
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
                    try:
                        context = await browser.new_context(
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            viewport={"width": 1280, "height": 900}
                        )
                        page = await context.new_page()
                        print(f"Navigating to {url} inside thread event loop...")
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        await page.wait_for_timeout(3000)
                        html = await page.content()
                        return html
                    finally:
                        await browser.close()
            
            html = asyncio.run(main())
            res_queue.put(html)
        except Exception as e:
            res_queue.put(e)
            
    t = threading.Thread(target=worker)
    t.start()
    t.join()
    res = res_queue.get()
    if isinstance(res, Exception):
        raise res
    return res

if __name__ == "__main__":
    try:
        html = render_page_in_thread("https://thelibrarycompany.com")
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        print("Successfully rendered page!")
        print("Title:", soup.title.string if soup.title else "No Title")
        print("HTML length:", len(html))
    except Exception as e:
        print("Failed with error:", e)
