"""
timeline_engine.py
Phase 8 — Timeline Engine

Tracks and logs node execution durations to the execution_timelines table.
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class TimelineEngine:
    """
    Records and tracks execution timelines for agent nodes.
    """

    def record_node_duration(
        self,
        run_id: str,
        node_name: str,
        started_at: datetime,
        completed_at: datetime,
        duration_ms: int
    ) -> Optional[Dict[str, Any]]:
        """
        Logs a node's start time, completion time, and calculated duration in milliseconds.
        """
        try:
            # Ensure dates are string serialized correctly
            started_str = started_at.isoformat() if isinstance(started_at, datetime) else started_at
            completed_str = completed_at.isoformat() if isinstance(completed_at, datetime) else completed_at

            timeline_payload = {
                "run_id": run_id,
                "node_name": node_name,
                "started_at": started_str,
                "completed_at": completed_str,
                "duration_ms": int(duration_ms)
            }

            resp = supabase_client.table("execution_timelines").insert(timeline_payload).execute()
            logger.info(f"Recorded timeline for node {node_name} under run {run_id} ({duration_ms} ms).")
            return resp.data[0] if resp.data else None
        except Exception as e:
            logger.error(f"Error recording timeline for node {node_name} under run {run_id}: {e}")
            return None

    def get_run_timeline(self, run_id: str) -> list:
        """
        Retrieves the timeline entries for a specific run.
        """
        try:
            resp = supabase_client.table("execution_timelines")\
                .select("*")\
                .eq("run_id", run_id)\
                .order("started_at", desc=False)\
                .execute()
            return resp.data or []
        except Exception as e:
            logger.error(f"Error getting timeline for run {run_id}: {e}")
            return []
