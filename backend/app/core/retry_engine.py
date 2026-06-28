"""
retry_engine.py
Phase 8 — Retry Engine

Centralized backoff manager. Prevents infinite loops and manages retry attempts for external services.
"""

from typing import Callable, Any, Dict
import time
import logging
from app.core.supabase import supabase_client
from app.core.error_classifier import ErrorClassifier

logger = logging.getLogger(__name__)

class RetryEngine:
    """
    Applies backoffs, registers retry attempts, and manages degraded fallbacks.
    """

    def __init__(self):
        self.classifier = ErrorClassifier()

    def execute_with_retry(
        self,
        project_id: str,
        run_id: str,
        agent_name: str,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Executes func(*args, **kwargs) with retry attempts, backoffs, and fallback hooks.
        """
        # Determine service classification from agent name / error type
        max_attempts = 1
        backoff_seconds = 1.0
        exponential = False

        # Identify target service/agent policies
        if "gemini" in agent_name.lower() or "llm" in agent_name.lower():
            max_attempts = 3 # 1 initial + 2 retries
            backoff_seconds = 10.0
            exponential = True
        elif "supabase" in agent_name.lower() or "database" in agent_name.lower():
            max_attempts = 4 # 1 initial + 3 retries
            backoff_seconds = 5.0
            exponential = False
        elif "playwright" in agent_name.lower() or "crawler" in agent_name.lower():
            max_attempts = 2 # 1 initial + 1 browser restart
            backoff_seconds = 2.0
            exponential = False
        else:
            # General defaults
            max_attempts = 3
            backoff_seconds = 3.0

        last_exception = None

        for attempt in range(1, max_attempts + 1):
            try:
                # Call node logic
                result = func(*args, **kwargs)
                
                # If we had a previous failure but now succeeded, log success
                if attempt > 1:
                    logger.info(f"Retry attempt {attempt} succeeded for {agent_name}.")
                    self._log_retry(project_id, run_id, agent_name, attempt, True, "Succeeded")
                return result
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt} failed for agent {agent_name}. Error: {e}")

                # Classify error
                diag = self.classifier.classify_and_log(project_id, run_id, agent_name, e)
                
                # Check if retryable
                if not diag["retryable"] or attempt == max_attempts:
                    self._log_retry(project_id, run_id, agent_name, attempt, False, str(e))
                    break

                # Record retry attempt
                self._log_retry(project_id, run_id, agent_name, attempt, False, str(e), diag["error_type"])

                # Wait backoff
                current_sleep = backoff_seconds * (attempt if exponential else 1)
                logger.info(f"Sleeping {current_sleep} seconds before next retry of {agent_name}...")
                time.sleep(current_sleep)

        # Retries exhausted. Trigger fallback default from fallback_engine
        logger.error(f"All retry attempts exhausted for {agent_name}. Invoking fallbacks...")
        from app.core.fallback_engine import FallbackEngine
        fb = FallbackEngine()
        return fb.get_fallback_default(project_id, run_id, agent_name, last_exception)

    def _log_retry(
        self,
        project_id: str,
        run_id: str,
        agent_name: str,
        attempt: int,
        succeeded: bool,
        error_msg: str,
        error_type: str = "UNKNOWN"
    ):
        try:
            supabase_client.table("retry_reports").insert({
                "project_id": project_id,
                "run_id": run_id,
                "agent_name": agent_name,
                "attempt_number": attempt,
                "error_message": error_msg,
                "error_type": error_type,
                "succeeded": succeeded
            }).execute()
        except Exception as db_err:
            logger.error(f"Error saving retry log: {db_err}")
