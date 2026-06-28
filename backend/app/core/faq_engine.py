"""
faq_engine.py
Phase 7 — FAQ Engine

Generates structured Q&A clusters and schema.org JSON-LD FAQPage structures
based on verified business profile claims and discovered questions.
"""

from typing import Dict, Any, List
import json
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class FAQEngine:
    """
    Builds FAQ answer templates and compiles search engine schemas.
    """

    def run(self, project_id: str, current_run_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Processes discovered questions, compiles answer scripts and JSON-LD schema blocks,
        inserts them into faq_clusters, and returns them.
        """
        questions = payload.get("questions", []) or []
        business_profile = payload.get("business_profile", {}) or {}
        verified_facts = payload.get("verified_facts", []) or []

        company_name = business_profile.get("company_name", "Brand Solutions")
        usp = business_profile.get("usp", "leading technical services")

        if not questions:
            logger.info("No questions discovered. Skipping FAQ clustering.")
            return []

        # Find questions matching high priority or conversational intent
        target_qs = []
        for q in questions:
            q_text = q.get("question", "")
            q_type = q.get("question_type", "general")
            # Select top items
            if q.get("priority", "Medium") in ["High", "Medium"] or q_type in ["AI Search", "Conversational"]:
                target_qs.append(q)

        # Limit to top 5 FAQs per run
        target_qs = target_qs[:5]
        if not target_qs:
            target_qs = questions[:3]

        faq_entries = []
        for q in target_qs:
            q_text = q.get("question", "")
            intent = q.get("intent", "informational")
            priority = q.get("priority", "Medium")
            
            # Formulate answer outline based on verified facts if keyword matches, else business profile
            answer = f"{company_name} provides specialized services as a key USP. For detailed guides, visit our contact resource pages."
            
            # Find relevant verified facts
            relevant_facts = []
            q_lower = q_text.lower()
            for fact in verified_facts:
                fact_val = fact.get("fact_value", "")
                fact_key = fact.get("fact_key", "").lower()
                if fact_key in q_lower or any(term in fact_val.lower() for term in q_lower.split() if len(term) >= 4):
                    relevant_facts.append(fact_val)
                    
            if relevant_facts:
                answer = f"{company_name} ensures compliance and quality: " + ". ".join(relevant_facts[:2]) + "."
            elif usp:
                answer = f"{company_name} is optimized for: {usp}. We design systems tailored to our client requirements."

            # Construct JSON-LD schema
            schema_json = {
                "@context": "https://schema.org",
                "@type": "Question",
                "name": q_text,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": answer
                }
            }

            item = {
                "project_id": project_id,
                "run_id": current_run_id,
                "question": q_text,
                "answer_outline": answer,
                "intent": intent,
                "priority": priority,
                "schema_markup": schema_json
            }
            faq_entries.append(item)

        if faq_entries:
            try:
                supabase_client.table("faq_clusters").insert(faq_entries).execute()
                logger.info(f"Persisted {len(faq_entries)} FAQ clusters for project {project_id}.")
            except Exception as e:
                logger.error(f"Error persisting FAQ clusters: {e}")

        return faq_entries
