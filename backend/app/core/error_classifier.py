"""
error_classifier.py
Phase 8 — Error Intelligence & Classifier Engine

Analyzes traceback messages to identify and classify failures, mapping root causes and recovery actions.
"""

from typing import Dict, Any
import logging
import traceback
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class ErrorClassifier:
    """
    Classifies exception tracebacks and logs them in error_diagnostics table.
    """

    def classify_and_log(
        self,
        project_id: str,
        run_id: str,
        agent_name: str,
        exception: Exception
    ) -> Dict[str, Any]:
        """
        Parses traceback and error details to save diagnostics report.
        """
        error_msg = str(exception)
        tb_str = "".join(traceback.format_exception(None, exception, exception.__traceback__))

        # Initialize defaults
        error_type = "UNKNOWN"
        severity = "MEDIUM"
        root_cause = "An unclassified exception occurred."
        recovery_action = "Check traceback diagnostics and logs."
        retryable = False

        msg_lower = error_msg.lower()

        # 1. Rate Limit / Quota check
        if any(term in msg_lower for term in ["quota", "rate", "429", "limit exceeded"]):
            error_type = "RATE_LIMIT"
            severity = "HIGH"
            root_cause = "API resource allocation exhausted (Gemini API quota exceeded)."
            recovery_action = "Wait for quota refresh or upgrade API tier."
            retryable = True

        # 2. Timeout check
        elif any(term in msg_lower for term in ["timeout", "timed out", "deadline"]):
            error_type = "TIMEOUT"
            severity = "MEDIUM"
            root_cause = "Network response time exceeded service connection limits."
            recovery_action = "Retry pipeline execution."
            retryable = True

        # 3. Connection / Network check
        elif any(term in msg_lower for term in ["connection", "host", "socket", "network"]):
            error_type = "NETWORK"
            severity = "HIGH"
            root_cause = "Failed to establish a network connection with external host."
            recovery_action = "Verify internet access and service online status."
            retryable = True

        # 4. Database check
        elif any(term in msg_lower for term in ["supabase", "postgres", "sql", "foreign key", "relation"]):
            error_type = "DATABASE"
            severity = "HIGH"
            root_cause = "Supabase PostgreSQL client query failed or encountered schema lock."
            recovery_action = "Check Supabase project status and connection pools."
            retryable = True

        # 5. Auth check
        elif any(term in msg_lower for term in ["auth", "key", "token", "permission", "credential"]):
            error_type = "AUTH"
            severity = "CRITICAL"
            root_cause = "Authentication token invalid or unauthorized key used."
            recovery_action = "Renew credentials or reconfigure environment keys."
            retryable = False

        # 6. Parser / Format check
        elif any(term in msg_lower for term in ["json", "format", "parse", "serialize"]):
            error_type = "PARSER"
            severity = "LOW"
            root_cause = "Failed to deserialize agent output string into expected JSON schema."
            recovery_action = "Adapt LLM output parameters or fix data templates."
            retryable = False

        # 7. Qdrant / Vector DB check
        elif any(term in msg_lower for term in ["qdrant", "vector", "lock", "collection"]):
            error_type = "VECTOR_DB"
            severity = "HIGH"
            root_cause = "Qdrant vector collection locked or client connection failed."
            recovery_action = "Clear locked vector context or restart Qdrant container."
            retryable = True

        # 8. Memory check
        elif any(term in msg_lower for term in ["memory", "ram", "heap"]):
            error_type = "MEMORY"
            severity = "CRITICAL"
            root_cause = "Worker process ran out of physical memory."
            recovery_action = "Scale worker container memory limits."
            retryable = False

        # 9. Cache check
        elif any(term in msg_lower for term in ["redis", "cache", "expire"]):
            error_type = "CACHE"
            severity = "MEDIUM"
            root_cause = "Redis cache client failed to connect or write key value."
            recovery_action = "Verify Redis connection or verify fallback in-memory cache."
            retryable = True

        diagnostic_report = {
            "run_id": run_id,
            "project_id": project_id,
            "agent_name": agent_name,
            "error_type": error_type,
            "severity": severity,
            "root_cause": root_cause,
            "traceback": tb_str,
            "recovery_action": recovery_action,
            "retryable": retryable
        }

        try:
            supabase_client.table("error_diagnostics").insert(diagnostic_report).execute()
            logger.info(f"Persisted error diagnostic report for {agent_name} under run {run_id}.")
        except Exception as db_err:
            logger.error(f"Error persisting diagnostics report: {db_err}")

        return diagnostic_report
