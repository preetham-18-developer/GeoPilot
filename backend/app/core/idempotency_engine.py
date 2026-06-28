"""
idempotency_engine.py
Phase 8 — Idempotency Engine

Inspects state payloads and Supabase tables to bypass duplicate runs and save API costs.
"""

from typing import Dict, Any
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class IdempotencyEngine:
    """
    Validates execution states to prevent duplicating expensive agent node actions.
    """

    def already_processed(self, project_id: str, node_name: str, state: Dict[str, Any]) -> bool:
        """
        Determines whether the node output is already populated in either the state or database.
        """
        try:
            # Check node-specific variables
            if node_name == "question_discovery":
                # Check state
                if state.get("questions") and len(state["questions"]) > 0:
                    logger.info("Idempotency match: questions already populated in state.")
                    return True
                # Check DB
                db_resp = supabase_client.table("questions").select("id").eq("project_id", project_id).limit(1).execute()
                if db_resp.data:
                    logger.info("Idempotency match: questions already exist in database.")
                    return True

            elif node_name == "keyword_intelligence":
                if state.get("keywords") and len(state["keywords"]) > 0:
                    logger.info("Idempotency match: keywords already populated in state.")
                    return True
                db_resp = supabase_client.table("keywords").select("id").eq("project_id", project_id).limit(1).execute()
                if db_resp.data:
                    logger.info("Idempotency match: keywords already exist in database.")
                    return True

            elif node_name == "competitor_discovery":
                if state.get("competitors") and len(state["competitors"]) > 0:
                    logger.info("Idempotency match: competitors already populated in state.")
                    return True
                db_resp = supabase_client.table("competitors").select("id").eq("project_id", project_id).limit(1).execute()
                if db_resp.data:
                    logger.info("Idempotency match: competitors already exist in database.")
                    return True

            elif node_name == "report_compiler":
                if state.get("report") and len(state["report"]) > 0:
                    logger.info("Idempotency match: report already compiled in state.")
                    return True
                db_resp = supabase_client.table("reports").select("id").eq("project_id", project_id).limit(1).execute()
                if db_resp.data:
                    logger.info("Idempotency match: report already exists in database.")
                    return True

            return False
        except Exception as e:
            logger.warning(f"Error checking idempotency for node {node_name}: {e}")
            return False
