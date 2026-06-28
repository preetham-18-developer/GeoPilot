"""
authority_source_engine.py
Phase 7 — Authority Source Engine

Maintains, filters, and recommends high-authority citation sources (ISO, NIST, HIPAA, W3C)
based on the project's target industry and cluster topics.
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class AuthoritySourceEngine:
    """
    Recommends deterministic authority standards, regulations, and source references for citations.
    """

    CATALOG = {
        "cybersecurity": [
            {"source_type": "Standard", "title": "ISO/IEC 27001 Information Security Management", "org": "ISO", "rel": 95.0, "auth": 98.0, "purpose": "Proves compliance with international information security controls."},
            {"source_type": "Regulation", "title": "NIST Special Publication 800-53", "org": "NIST", "rel": 90.0, "auth": 96.0, "purpose": "Provides security and privacy controls for federal information systems."},
            {"source_type": "Certification", "title": "SOC 2 Type II Auditing Standards", "org": "AICPA", "rel": 92.0, "auth": 95.0, "purpose": "Assures control guidelines for security, availability, and processing integrity."}
        ],
        "healthcare": [
            {"source_type": "Regulation", "title": "HIPAA Security and Privacy Rules", "org": "US Department of Health & Human Services", "rel": 98.0, "auth": 99.0, "purpose": "Mandates strict administrative and technical protections for ePHI data."},
            {"source_type": "Standard", "title": "ISO 13485 Quality Management for Medical Devices", "org": "ISO", "rel": 90.0, "auth": 95.0, "purpose": "Establishes regulatory compliance requirements for health device technologies."}
        ],
        "finance": [
            {"source_type": "Standard", "title": "PCI-DSS v4.0 Compliance Security Standard", "org": "PCI Security Standards Council", "rel": 96.0, "auth": 98.0, "purpose": "Standardizes security metrics for merchant payment processing channels."},
            {"source_type": "Regulation", "title": "Sarbanes-Oxley Act Section 404", "org": "SEC", "rel": 85.0, "auth": 95.0, "purpose": "Establishes auditing rules to prevent corporate financial auditing fraud."}
        ],
        "general": [
            {"source_type": "Standard", "title": "ISO 9001 Quality Management Systems", "org": "ISO", "rel": 85.0, "auth": 95.0, "purpose": "Validates corporate operational consistency and customer satisfaction indices."},
            {"source_type": "Standard", "title": "Web Content Accessibility Guidelines (WCAG 2.1)", "org": "W3C", "rel": 90.0, "auth": 96.0, "purpose": "Asserts accessibility compliance levels for modern web applications."}
        ]
    }

    def run(self, project_id: str, current_run_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Determines the project industry, loads matching authority reference resources,
        inserts them into authority_sources table, and returns them.
        """
        business_profile = payload.get("business_profile", {}) or {}
        industry = (business_profile.get("industry", "") or "").lower()
        
        # Determine industry key
        ind_key = "general"
        if any(term in industry for term in ["security", "cyber", "saas", "software"]):
            ind_key = "cybersecurity"
        elif any(term in industry for term in ["health", "medical", "clinic"]):
            ind_key = "healthcare"
        elif any(term in industry for term in ["finance", "bank", "pay", "credit"]):
            ind_key = "finance"

        sources = self.CATALOG.get(ind_key, self.CATALOG["general"])
        
        # Format inserts
        insert_payload = []
        for src in sources:
            item = {
                "project_id": project_id,
                "run_id": current_run_id,
                "topic": "System Security & Compliance" if ind_key == "cybersecurity" else "Industry Standards",
                "source_type": src["source_type"],
                "title": src["title"],
                "organization": src["org"],
                "relevance_score": src["rel"],
                "authority_score": src["auth"],
                "citation_purpose": src["purpose"]
            }
            insert_payload.append(item)

        if insert_payload:
            try:
                supabase_client.table("authority_sources").insert(insert_payload).execute()
                logger.info(f"Persisted {len(insert_payload)} authority sources for project {project_id}.")
            except Exception as e:
                logger.error(f"Error persisting authority sources: {e}")

        return insert_payload
