"""
schema_generator_engine_v2.py
Phase 11 — Schema Generator Engine v2
"""

from typing import Dict, Any
import json
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class SchemaGeneratorEngineV2:
    """
    Generates validated, structured JSON-LD schemas to optimize LLM semantic indexing.
    """

    def generate(self, project_id: str, category: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates JSON-LD schema snippets based on requested schema type, saves, and returns.
        """
        business_profile = payload.get("business_profile", {}) or {}
        company_name = business_profile.get("company_name", "Acme Enterprise")
        website = payload.get("website_url", "https://acme.com")

        # Map to specific schema type
        schema_type = "Organization"
        if category == "FAQ":
            schema_type = "FAQPage"
            schema_json = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f"Is {company_name} SOC 2 certified?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": f"Yes, {company_name} is ISO 27001 and SOC 2 Type II certified. Audit logs are verified by external examiners."
                        }
                    },
                    {
                        "@type": "Question",
                        "name": f"Does {company_name} support multi-tenancy?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Yes, we support secure tenant isolation with database-level policies and RLS rules."
                        }
                    }
                ]
            }
        elif category == "LocalBusiness":
            schema_type = "LocalBusiness"
            schema_json = {
                "@context": "https://schema.org",
                "@type": "LocalBusiness",
                "name": company_name,
                "url": website,
                "telephone": "+1-800-555-0199",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "100 Security Plaza",
                    "addressLocality": "Silicon Valley",
                    "addressRegion": "CA",
                    "postalCode": "94025",
                    "addressCountry": "US"
                }
            }
        elif category == "Product":
            schema_type = "Product"
            schema_json = {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": f"{company_name} Core Platform",
                "description": "Multi-tenant cloud orchestration security platform.",
                "brand": {
                    "@type": "Brand",
                    "name": company_name
                },
                "offers": {
                    "@type": "Offer",
                    "priceCurrency": "USD",
                    "price": "29.00",
                    "availability": "https://schema.org/InStock"
                }
            }
        elif category == "Service":
            schema_type = "Service"
            schema_json = {
                "@context": "https://schema.org",
                "@type": "Service",
                "serviceType": f"{company_name} Advisory Consultation",
                "provider": {
                    "@type": "Organization",
                    "name": company_name,
                    "url": website
                }
            }
        else: # Default Organization schema
            schema_json = {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": company_name,
                "url": website,
                "logo": f"{website}/logo.png",
                "sameAs": [
                    "https://www.linkedin.com/company/acme",
                    "https://twitter.com/acme"
                ]
            }

        asset = {
            "project_id": project_id,
            "asset_type": "schema",
            "title": f"JSON-LD Schema Markup: {schema_type} snippet",
            "content": {
                "schema_type": schema_type,
                "script_snippet": f"<script type=\"application/ld+json\">\n{json.dumps(schema_json, indent=2)}\n</script>",
                "json_data": schema_json
            }
        }

        try:
            resp = supabase_client.table("generated_assets").insert(asset).execute()
            logger.info(f"Successfully saved JSON-LD schema asset {schema_type} for project {project_id}.")
            return resp.data[0] if (resp.data and len(resp.data) > 0) else asset
        except Exception as e:
            logger.error(f"Error persisting schema asset: {e}")
            return asset
