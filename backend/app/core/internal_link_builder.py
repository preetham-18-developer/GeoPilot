"""
internal_link_builder.py
Phase 11 — Internal Link Builder Engine
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class InternalLinkBuilder:
    """
    Constructs semantic internal link recommendations between crawled pages and targets.
    """

    def build_links(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Builds internal link placements, saves to generated_assets, and returns the asset.
        """
        crawled_pages = payload.get("crawled_pages", []) or []
        
        # Default link targets
        parent_url = payload.get("website_url", "https://acme.com")
        blog_urls = [p.get("url", "") for p in crawled_pages if "blog" in p.get("url", "").lower()]
        product_urls = [p.get("url", "") for p in crawled_pages if "product" in p.get("url", "").lower() or "service" in p.get("url", "").lower()]

        if not blog_urls:
            blog_urls = [f"{parent_url}/blog/security-standards"]
        if not product_urls:
            product_urls = [f"{parent_url}/products/cloud-firewall"]

        link_placements = []

        # Connect Blog pages to Product landing pages with keyword anchors
        for blog in blog_urls[:3]:
            for prod in product_urls[:2]:
                link_placements.append({
                    "source_page": blog,
                    "target_page": prod,
                    "anchor_text": "enterprise cloud security certifications",
                    "placement_context": f"...to learn more about our operational audit details, review our {prod} specs...",
                    "link_strength": "High"
                })

        # Add link pointers to home page
        for prod in product_urls[:2]:
            link_placements.append({
                "source_page": parent_url,
                "target_page": prod,
                "anchor_text": "cloud security service features",
                "placement_context": f"...explore our full list of {prod} options on our homepage...",
                "link_strength": "Medium"
            })

        asset = {
            "project_id": project_id,
            "asset_type": "internal_link",
            "title": "Internal Link Map: Semantic Navigation Structure",
            "content": {
                "link_placements": link_placements,
                "count": len(link_placements),
                "summary": f"Generated {len(link_placements)} link mappings pointing semantic anchor text from content blogs to transactional product pages."
            }
        }

        try:
            resp = supabase_client.table("generated_assets").insert(asset).execute()
            logger.info(f"Successfully saved Internal Link Map asset for project {project_id}.")
            return resp.data[0] if (resp.data and len(resp.data) > 0) else asset
        except Exception as e:
            logger.error(f"Error persisting internal link asset: {e}")
            return asset
