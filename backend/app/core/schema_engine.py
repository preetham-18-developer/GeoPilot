"""
schema_engine.py
Phase 7 — Schema Recommendation Engine

Inspects crawled page types and content copy to recommend search engine schemas
(FAQ, Article, Product, Organization) compiling ready-to-inject JSON-LD codes.
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class SchemaRecommendationEngine:
    """
    Evaluates pages and formats JSON-LD structured data block recommendations.
    """

    def run(self, project_id: str, current_run_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Runs schema audit over pages, inserts recommendations to schema_recommendations, and returns the list.
        """
        crawled_pages = payload.get("crawled_pages", []) or []
        business_profile = payload.get("business_profile", {}) or {}
        
        company_name = business_profile.get("company_name", "Brand Solutions")
        website_url = business_profile.get("website_url", "https://example.com")

        recs = []
        for page in crawled_pages[:6]: # Limit to top 6 pages
            url = page.get("url", "")
            url_lower = url.lower()
            title = page.get("title", "") or "Content Resource"
            
            schema_type = "Article"
            schema_json = {}
            
            # Match schema based on URL characteristics
            if url_lower.endswith("/") or "home" in url_lower or "index" in url_lower:
                schema_type = "Organization"
                schema_json = {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": company_name,
                    "url": website_url,
                    "logo": f"{website_url}/logo.png",
                    "sameAs": [
                        "https://www.linkedin.com/company/" + company_name.lower().replace(" ", "")
                    ]
                }
            elif "faq" in url_lower:
                schema_type = "FAQ"
                schema_json = {
                    "@context": "https://schema.org",
                    "@type": "FAQPage",
                    "mainEntity": [
                        {
                            "@type": "Question",
                            "name": f"What services does {company_name} provide?",
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": f"{company_name} offers customized software and operations support services."
                            }
                        }
                    ]
                }
            elif "product" in url_lower or "pricing" in url_lower or "service" in url_lower:
                schema_type = "Product"
                schema_json = {
                    "@context": "https://schema.org",
                    "@type": "Product",
                    "name": title,
                    "description": page.get("meta_description", f"Specialized services offered by {company_name}."),
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "USD",
                        "availability": "https://schema.org/InStock"
                    }
                }
            elif "guide" in url_lower or "how" in url_lower:
                schema_type = "HowTo"
                schema_json = {
                    "@context": "https://schema.org",
                    "@type": "HowTo",
                    "name": title,
                    "step": [
                        {
                            "@type": "HowToStep",
                            "text": "Review your system integration configurations."
                        }
                    ]
                }
            else:
                schema_type = "Article"
                schema_json = {
                    "@context": "https://schema.org",
                    "@type": "Article",
                    "headline": title,
                    "author": {
                        "@type": "Organization",
                        "name": company_name
                    },
                    "publisher": {
                        "@type": "Organization",
                        "name": company_name
                    }
                }

            recs.append({
                "project_id": project_id,
                "run_id": current_run_id,
                "page_url": url,
                "page_title": title,
                "recommended_schema": schema_type,
                "injected_status": False,
                "schema_json": schema_json
            })

        if recs:
            try:
                supabase_client.table("schema_recommendations").insert(recs).execute()
                logger.info(f"Persisted {len(recs)} schema recommendations for project {project_id}.")
            except Exception as e:
                logger.error(f"Error persisting schema recommendations: {e}")

        return recs
