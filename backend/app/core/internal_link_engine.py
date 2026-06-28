"""
internal_link_engine.py
Phase 7 — Internal Linking Engine

Evaluates keyword overlaps and page structures to suggest high-value internal links
specifying anchor texts, link strength, and entity relevance parameters.
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class InternalLinkEngine:
    """
    Computes parent/child link routing pathways based on semantic title and keyword matches.
    """

    def run(self, project_id: str, current_run_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scans crawled pages to suggest linking maps, inserts them into internal_link_maps, and returns the list.
        """
        crawled_pages = payload.get("crawled_pages", []) or []
        keywords = payload.get("keywords", []) or []
        
        if len(crawled_pages) < 2:
            logger.info("Not enough pages crawled to map internal linking structures.")
            return []

        # Find home/landing page
        parent_page = crawled_pages[0].get("url", "/")
        for p in crawled_pages:
            url_lower = p.get("url", "").lower()
            if url_lower.endswith("/") or "index" in url_lower or "home" in url_lower:
                parent_page = p.get("url", "")
                break

        link_maps = []
        
        # Suggest parent-to-child links for detailed pages
        detailed_pages = [p for p in crawled_pages if p.get("url", "") != parent_page]
        
        # Limit suggestions to top 5 links
        for page in detailed_pages[:5]:
            child_url = page.get("url", "")
            title = page.get("title", "") or "Content Guide"
            
            # Anchor text: find a matching keyword from database or use the page title
            anchor = title
            for k in keywords:
                kw = k.get("keyword", "")
                if kw.lower() in title.lower():
                    anchor = kw.title()
                    break

            # Calculate deterministic link strength & entity relevance
            overlap_words = len(set(title.lower().split()).intersection(set(anchor.lower().split())))
            strength = min(98, 45 + overlap_words * 15)
            entity_rel = min(95, 40 + overlap_words * 12)

            # Suggest related pages (crawled pages other than parent and child)
            related = [p.get("url", "") for p in crawled_pages if p.get("url", "") not in [parent_page, child_url]][:2]

            item = {
                "project_id": project_id,
                "run_id": current_run_id,
                "parent_page": parent_page,
                "child_page": child_url,
                "related_pages": related,
                "anchor_text": anchor,
                "link_strength": int(strength),
                "entity_relevance": int(entity_rel)
            }
            link_maps.append(item)

        if link_maps:
            try:
                supabase_client.table("internal_link_maps").insert(link_maps).execute()
                logger.info(f"Persisted {len(link_maps)} internal link maps for project {project_id}.")
            except Exception as e:
                logger.error(f"Error persisting internal link maps: {e}")

        return link_maps
