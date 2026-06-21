import asyncio
import logging
import hashlib
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Any, Optional

import httpx
from bs4 import BeautifulSoup

embedding_model = None

def get_embedding_model():
    global embedding_model
    if embedding_model is None:
        try:
            from fastembed import TextEmbedding
            embedding_model = TextEmbedding()
            logging.getLogger(__name__).info("Local fastembed model loaded successfully.")
        except Exception as e:
            logging.getLogger(__name__).error(f"Error loading fastembed model: {e}")
            embedding_model = None
    return embedding_model

try:
    from qdrant_client.http import models as qdrant_models
    from app.core.qdrant import qdrant_client, init_collection
    QDRANT_AVAILABLE = True
except Exception:
    QDRANT_AVAILABLE = False

from app.core.config import settings
from app.core.supabase import supabase_client
from app.crawler.parser import parse_html_content

logger = logging.getLogger(__name__)

MAX_PAGES = 20
MAX_DEPTH = 3
CONCURRENT_LIMIT = 3

# JavaScript render wait time (ms) — ensures SPA content loads
JS_WAIT_MS = 2500


class WebsiteSpider:
    """
    Domain-locked async spider with JavaScript rendering support via Playwright.
    Falls back to plain httpx for non-JS pages if Playwright is unavailable.
    """

    def __init__(self, project_id: str, website_url: str):
        self.project_id = project_id
        self.website_url = website_url.rstrip("/")
        self.parsed_start_url = urlparse(website_url)

        # Strict domain locking — strip www. prefix
        raw_netloc = self.parsed_start_url.netloc.lower()
        self.domain = raw_netloc[4:] if raw_netloc.startswith("www.") else raw_netloc
        self.base_url = f"{self.parsed_start_url.scheme}://{self.parsed_start_url.netloc}"

        self.visited_urls: set = set()
        self.pages_count = 0
        self.semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)

        if QDRANT_AVAILABLE:
            self.collection_name = f"project_{project_id.replace('-', '_')}"
            try:
                init_collection(self.collection_name, vector_size=384)
            except Exception as e:
                logger.warning(f"Qdrant collection init skipped: {e}")

    # -------------------------------------------------------------------------
    # Domain Locking
    # -------------------------------------------------------------------------
    def is_internal_url(self, url: str) -> bool:
        """Returns True ONLY if URL belongs to the exact locked domain."""
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        # Strict exact match — no subdomains, no similar names
        return netloc == self.domain or parsed.netloc == ""

    def clean_url(self, url: str) -> str:
        """Strips query params and fragments for deduplication."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    def _log_failure(self, url: str, reason: str, error_msg: str):
        try:
            supabase_client.table("extraction_failures").insert({
                "project_id": self.project_id,
                "page_url": url,
                "reason": reason,
                "agent_name": "Crawler",
                "error_message": error_msg[:500]
            }).execute()
        except Exception as e:
            logger.error(f"Failed to log crawler failure: {e}")

    # -------------------------------------------------------------------------
    # Sitemap Discovery
    # -------------------------------------------------------------------------
    async def _fetch_sitemap_urls(self) -> List[str]:
        """Fetch URLs from sitemap.xml if available — reliable for SPAs."""
        sitemap_urls = []
        for sitemap_path in ["/sitemap.xml", "/sitemap_index.xml"]:
            try:
                async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=10) as client:
                    r = await client.get(
                        f"{self.parsed_start_url.scheme}://{self.parsed_start_url.netloc}{sitemap_path}",
                        headers={"User-Agent": "AIVOP-Crawler/2.0"}
                    )
                    if r.status_code == 200 and "xml" in r.headers.get("content-type", ""):
                        soup = BeautifulSoup(r.text, "xml")
                        locs = soup.find_all("loc")
                        for loc in locs:
                            url = loc.get_text().strip()
                            cleaned = self.clean_url(url)
                            if self.is_internal_url(cleaned):
                                sitemap_urls.append(cleaned)
                        logger.info(f"Sitemap discovered {len(sitemap_urls)} URLs from {sitemap_path}")
                        break
            except Exception as e:
                logger.warning(f"Sitemap fetch failed for {sitemap_path}: {e}")
        return list(dict.fromkeys(sitemap_urls))  # deduplicate, preserve order

    # -------------------------------------------------------------------------
    # JavaScript Rendering via Playwright
    # -------------------------------------------------------------------------
    async def _render_with_playwright(self, url: str) -> str:
        """
        Renders a URL using Playwright Chromium to execute JavaScript.
        Returns the fully-rendered HTML after JS execution.
        Uses domcontentloaded + explicit wait instead of networkidle to avoid
        timeouts on SPAs that have continuous background network activity.
        """
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                try:
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        viewport={"width": 1280, "height": 900}
                    )
                    page = await context.new_page()
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    # Wait for JS framework to render content (React/Vue/Angular hydration)
                    await page.wait_for_timeout(JS_WAIT_MS)
                    html = await page.content()
                    return html
                finally:
                    await browser.close()
        except Exception as e:
            logger.error(f"Playwright render failed for {url}: {e}")
            return ""

    # -------------------------------------------------------------------------
    # Plain HTTP Fetch (fallback)
    # -------------------------------------------------------------------------
    async def _fetch_plain(self, url: str) -> str:
        """Plain httpx fetch for non-SPA pages or fallback."""
        try:
            async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=15) as client:
                r = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
                if r.status_code == 200 and "text/html" in r.headers.get("content-type", ""):
                    return r.text
                else:
                    self._log_failure(url, f"HTTP {r.status_code}", f"Content-Type: {r.headers.get('content-type', '')}")
        except Exception as e:
            logger.error(f"HTTP fetch failed for {url}: {e}")
            self._log_failure(url, "Fetch Exception", str(e))
        return ""

    # -------------------------------------------------------------------------
    # Is SPA Detection
    # -------------------------------------------------------------------------
    def _is_spa_page(self, html: str) -> bool:
        """Heuristic: if body has very little text content it's likely an SPA shell."""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "head"]):
            tag.decompose()
        body_text = soup.get_text(separator=" ", strip=True)
        return len(body_text.split()) < 50

    # -------------------------------------------------------------------------
    # Content Extraction from Rendered HTML
    # -------------------------------------------------------------------------
    def _extract_text_from_html(self, html: str, url: str) -> Dict[str, Any]:
        """
        Robust content extraction that:
        1. Grabs meta tags
        2. Grabs structured JSON-LD
        3. Grabs all visible text elements
        """
        soup = BeautifulSoup(html, "html.parser")

        # Extract JSON-LD structured data
        structured_data = []
        for ld in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(ld.get_text().strip())
                if isinstance(data, list):
                    structured_data.extend(data)
                else:
                    structured_data.append(data)
            except Exception:
                pass

        # Extract title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Extract meta description (multiple fallbacks)
        meta_desc = ""
        for attr in [{"name": "description"}, {"property": "og:description"}, {"name": "twitter:description"}]:
            tag = soup.find("meta", attrs=attr)
            if tag and tag.get("content"):
                meta_desc = tag.get("content").strip()
                break

        # Remove non-content elements
        for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
            tag.decompose()

        # Extract all text in document order with semantic markers
        body_lines = []
        content_tags = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "blockquote", "span", "div"])

        seen_texts = set()
        for elem in content_tags:
            # Skip deeply nested duplicates
            text = elem.get_text(separator=" ", strip=True)
            if not text or len(text) < 10:
                continue
            # Deduplicate
            if text in seen_texts:
                continue
            seen_texts.add(text)

            tag_name = elem.name
            if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                level = int(tag_name[1])
                body_lines.append(f"\n{'#' * level} {text}\n")
            elif tag_name == "li":
                body_lines.append(f"* {text}")
            elif tag_name in ["td", "th"]:
                body_lines.append(f"| {text}")
            else:
                body_lines.append(text)

        markdown_content = "\n".join(body_lines).strip()

        # Also inject structured JSON-LD content as text if present
        if structured_data:
            import json
            ld_text = json.dumps(structured_data, indent=2)
            markdown_content = f"{markdown_content}\n\n[STRUCTURED DATA]\n{ld_text}"

        return {
            "url": url,
            "title": title,
            "meta_description": meta_desc,
            "markdown_content": markdown_content,
            "structured_data": structured_data,
        }

    # -------------------------------------------------------------------------
    # Qdrant Indexing
    # -------------------------------------------------------------------------
    def _chunk_text(self, text: str, chunk_size: int = 600, overlap: int = 100) -> List[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        return chunks

    def _index_in_qdrant(self, page_id: str, url: str, markdown_content: str):
        model = get_embedding_model()
        if not QDRANT_AVAILABLE or not model or not markdown_content:
            return
        try:
            chunks = self._chunk_text(markdown_content)
            if not chunks:
                return
            embeddings = list(model.embed(chunks))
            points = [
                qdrant_models.PointStruct(
                    id=hash(f"{page_id}_{idx}") & 0xFFFFFFFFFFFFFFFF,
                    vector=list(vec),
                    payload={"page_id": page_id, "url": url, "chunk_index": idx, "content": chunk}
                )
                for idx, (chunk, vec) in enumerate(zip(chunks, embeddings))
            ]
            if points:
                qdrant_client.upsert(collection_name=self.collection_name, points=points)
                logger.info(f"Indexed {len(points)} chunks in Qdrant for {url}")
        except Exception as e:
            logger.error(f"Qdrant indexing failed for {url}: {e}")

    # -------------------------------------------------------------------------
    # Supabase Persistence
    # -------------------------------------------------------------------------
    async def _save_page(self, url: str, parsed: Dict[str, Any]) -> Optional[str]:
        """Saves a crawled page to Supabase and returns the page ID."""
        content = parsed["markdown_content"]
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        word_count = len(content.split())

        try:
            page_resp = supabase_client.table("web_pages").insert({
                "project_id": self.project_id,
                "url": url,
                "title": parsed["title"],
                "meta_description": parsed["meta_description"],
                "page_type": "html",
                "content": content,
                "crawl_date": "now()",
                "word_count": word_count,
                "language": "en",
                "status_code": 200,
                "hash": content_hash
            }).execute()

            if page_resp.data:
                return page_resp.data[0]["id"]
        except Exception as e:
            logger.error(f"Failed to save page {url} to Supabase: {e}")
        return None

    # -------------------------------------------------------------------------
    # Main Crawl Entry
    # -------------------------------------------------------------------------
    async def start(self) -> int:
        """
        Main crawl orchestration:
        1. Fetch sitemap URLs
        2. Use Playwright to render each page (JS-aware)
        3. Fall back to httpx if Playwright unavailable
        4. Save to Supabase and Qdrant
        Returns number of pages successfully crawled.
        """
        logger.info(f"Starting crawl for: {self.website_url}")
        supabase_client.table("projects").update({"status": "crawling"}).eq("id", self.project_id).execute()

        # Check if Playwright is available
        playwright_available = False
        try:
            from playwright.async_api import async_playwright
            playwright_available = True
            logger.info("Playwright available — will render JavaScript.")
        except ImportError:
            logger.warning("Playwright not available — falling back to plain HTTP (SPAs may yield empty content).")

        # Step 1: Discover URLs from sitemap
        sitemap_urls = await self._fetch_sitemap_urls()

        # Step 2: Seed queue with sitemap URLs first, then the start URL
        queue = []
        if sitemap_urls:
            # Normalize: ensure www. domains map to canonical form
            normalized = []
            for u in sitemap_urls:
                parsed = urlparse(u)
                netloc = parsed.netloc.lower()
                # Use https:// version without www. for strict domain locking
                canonical = f"https://{netloc}{parsed.path}".rstrip("/")
                if self.is_internal_url(canonical):
                    normalized.append(canonical)
            queue = [(u, 1) for u in list(dict.fromkeys(normalized))[:MAX_PAGES]]
            logger.info(f"Seeded {len(queue)} URLs from sitemap.")
        else:
            # Fall back to BFS from start URL
            queue = [(self.clean_url(self.website_url), 1)]
            logger.info("No sitemap found — starting BFS from root URL.")

        # Step 3: Process queue
        while queue and self.pages_count < MAX_PAGES:
            batch = []
            while queue and len(batch) < CONCURRENT_LIMIT:
                batch.append(queue.pop(0))

            tasks = [self._process_url(url, depth, queue, playwright_available) for url, depth in batch]
            await asyncio.gather(*tasks)

        supabase_client.table("projects").update({"status": "completed"}).eq("id", self.project_id).execute()
        logger.info(f"Crawl complete. Processed {self.pages_count} pages from {self.website_url}.")
        return self.pages_count

    async def _process_url(self, url: str, depth: int, queue: List, playwright_available: bool):
        """Process a single URL: fetch → render → extract → save → discover links."""
        async with self.semaphore:
            if url in self.visited_urls or self.pages_count >= MAX_PAGES or depth > MAX_DEPTH:
                return

            # DOMAIN LOCK — reject anything not on the locked domain
            if not self.is_internal_url(url):
                logger.warning(f"Domain-lock rejected: {url}")
                return

            self.visited_urls.add(url)
            self.pages_count += 1
            logger.info(f"Processing ({self.pages_count}/{MAX_PAGES}) depth={depth}: {url}")

            # Fetch HTML
            html = ""
            if playwright_available:
                html = await self._render_with_playwright(url)
            if not html:
                html = await self._fetch_plain(url)
            if not html:
                logger.warning(f"No content returned for: {url}")
                return

            # If plain fetch got SPA shell, try Playwright
            if playwright_available and self._is_spa_page(html):
                logger.info(f"SPA detected at {url} — rendering with Playwright...")
                rendered = await self._render_with_playwright(url)
                if rendered:
                    html = rendered

            # Extract content
            parsed = self._extract_text_from_html(html, url)
            word_count = len(parsed["markdown_content"].split())
            logger.info(f"Extracted {word_count} words from {url}")

            if word_count < 10:
                logger.warning(f"Minimal content extracted from {url} — possible JS-only page or blocked.")
                self._log_failure(url, "Minimal Content", f"Only {word_count} words extracted after rendering.")

            # Save to Supabase
            page_id = await self._save_page(url, parsed)

            # Index in Qdrant
            if page_id and parsed["markdown_content"]:
                self._index_in_qdrant(page_id, url, parsed["markdown_content"])

            # Discover child links (for BFS fallback or additional pages)
            if depth < MAX_DEPTH:
                soup = BeautifulSoup(html, "html.parser")
                for anchor in soup.find_all("a", href=True):
                    href = anchor.get("href", "")
                    absolute = urljoin(url, href)
                    cleaned = self.clean_url(absolute)
                    if self.is_internal_url(cleaned) and cleaned not in self.visited_urls:
                        queue.append((cleaned, depth + 1))
