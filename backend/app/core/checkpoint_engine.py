"""
checkpoint_engine.py
Phase 8 — Checkpoint Engine

Provides methods to save, load, and trace pipeline execution checkpoints to enable run resume capability.
"""

from typing import Dict, Any, List, Optional
import logging
import hashlib
import json
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class CheckpointEngine:
    """
    Manages database serialization and loading of pipeline state checkpoints.
    """

    def save_checkpoint(
        self,
        run_id: str,
        project_id: str,
        node_name: str,
        status: str,
        state_data: Dict[str, Any],
        retry_count: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Saves or updates a node's progress and payload state data in execution_checkpoints.
        """
        try:
            # Generate state payload hash to detect changes
            state_str = json.dumps(state_data, sort_keys=True, default=str)
            payload_hash = hashlib.sha256(state_str.encode("utf-8")).hexdigest()

            # Clean state data: remove extremely large elements if necessary, but keep structure
            serialized_state = {k: v for k, v in state_data.items() if k not in ["crawled_pages"]}

            # Check if checkpoint already exists for this run + node
            exist_resp = supabase_client.table("execution_checkpoints")\
                .select("id")\
                .eq("run_id", run_id)\
                .eq("node_name", node_name)\
                .execute()

            checkpoint_payload = {
                "run_id": run_id,
                "project_id": project_id,
                "node_name": node_name,
                "status": status,
                "retry_count": retry_count,
                "payload_hash": payload_hash,
                "resume_data": serialized_state,
                "completed_at": "now()" if status == "completed" else None
            }

            if exist_resp.data:
                checkpoint_id = exist_resp.data[0]["id"]
                resp = supabase_client.table("execution_checkpoints")\
                    .update(checkpoint_payload)\
                    .eq("id", checkpoint_id)\
                    .execute()
            else:
                resp = supabase_client.table("execution_checkpoints")\
                    .insert(checkpoint_payload)\
                    .execute()

            logger.info(f"Saved checkpoint for node {node_name} under run {run_id} (status: {status}).")
            return resp.data[0] if resp.data else None
        except Exception as e:
            logger.error(f"Error saving checkpoint for node {node_name}: {e}")
            return None

    def load_checkpoint(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads the latest successful checkpoint state data for a run.
        """
        try:
            resp = supabase_client.table("execution_checkpoints")\
                .select("*")\
                .eq("run_id", run_id)\
                .eq("status", "completed")\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()

            return resp.data[0] if resp.data else None
        except Exception as e:
            logger.error(f"Error loading checkpoint for run {run_id}: {e}")
            return None

    def has_completed_node(self, run_id: str, node_name: str) -> bool:
        """
        Determines whether a node has successfully completed for a run.
        """
        try:
            resp = supabase_client.table("execution_checkpoints")\
                .select("id")\
                .eq("run_id", run_id)\
                .eq("node_name", node_name)\
                .eq("status", "completed")\
                .execute()
            return len(resp.data) > 0
        except Exception as e:
            logger.error(f"Error checking node status {node_name}: {e}")
            return False

    def get_completed_nodes(self, run_id: str) -> List[str]:
        """
        Returns a list of completed node names for the given run.
        """
        try:
            resp = supabase_client.table("execution_checkpoints")\
                .select("node_name")\
                .eq("run_id", run_id)\
                .eq("status", "completed")\
                .execute()
            return [r["node_name"] for r in (resp.data or [])]
        except Exception as e:
            logger.error(f"Error fetching completed nodes for run {run_id}: {e}")
            return []
