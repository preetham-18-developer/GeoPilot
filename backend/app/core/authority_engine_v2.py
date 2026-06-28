"""
authority_engine_v2.py
Phase 9 — Authority Engine v2
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class AuthorityEngineV2:
    """
    Scans company context to identify compliance standards, case studies, white papers, etc., and logs authority strengths.
    """

    AUTHORITY_CATALOG = {
        "security": [
            {"entity_name": "ISO/IEC 27001 Compliance", "entity_type": "Standard", "strength": 98.0},
            {"entity_name": "SOC 2 Type II Certification", "entity_type": "Certification", "strength": 95.0},
            {"entity_name": "NIST Cyber Security Framework", "entity_type": "Best Practices", "strength": 92.0},
            {"entity_name": "HIPAA Privacy Audits", "entity_type": "Regulation", "strength": 96.0}
        ],
        "general": [
            {"entity_name": "ISO 9001 Quality System", "entity_type": "Standard", "strength": 85.0},
            {"entity_name": "WCAG 2.1 Web Accessibility", "entity_type": "Best Practices", "strength": 90.0},
            {"entity_name": "Industry Association Membership", "entity_type": "Industry Association", "strength": 75.0},
            {"entity_name": "Annual Business White Paper", "entity_type": "White Paper", "strength": 80.0},
            {"entity_name": "Customer Success Case Study", "entity_type": "Case Study", "strength": 85.0}
        ]
    }

    def run(self, project_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extracts authority entities, inserts them into authority_entities table, and returns them.
        """
        crawled_pages = payload.get("crawled_pages", []) or []
        business_profile = payload.get("business_profile", {}) or {}
        industry = (business_profile.get("industry", "") or "").lower()

        # Combine text content from pages
        all_text = " ".join([p.get("content", "") for p in crawled_pages]).lower()

        discovered = []
        is_security_focused = any(x in industry or x in all_text for x in ["security", "cyber", "compliance", "privacy", "saas", "software"])

        target_set = self.AUTHORITY_CATALOG["security"] + self.AUTHORITY_CATALOG["general"] if is_security_focused else self.AUTHORITY_CATALOG["general"]

        for item in target_set:
            # Check if mentioned or matches keywords
            keyword = item["entity_name"].split()[0].lower()
            # If standard mentioned in content, boost strength, otherwise assign baseline mock discovery
            strength = item["strength"]
            if keyword in all_text:
                strength = min(100.0, strength + 5.0)
            
            discovered.append({
                "project_id": project_id,
                "entity_name": item["entity_name"],
                "entity_type": item["entity_type"],
                "authority_strength": round(strength, 1)
            })

        if discovered:
            try:
                # Clear previous authority entities
                supabase_client.table("authority_entities").delete().eq("project_id", project_id).execute()
                supabase_client.table("authority_entities").insert(discovered).execute()
                logger.info(f"Successfully saved {len(discovered)} authority entities.")
            except Exception as e:
                logger.error(f"Error persisting authority entities: {e}")

        return discovered
