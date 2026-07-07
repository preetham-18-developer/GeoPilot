"""
retry_engine.py
Phase 8 — Retry Engine

Centralized backoff manager. Prevents infinite loops and manages retry attempts for external services.
"""

from typing import Callable, Any, Dict, Set
import time
import logging
from app.core.supabase import supabase_client
from app.core.error_classifier import ErrorClassifier

logger = logging.getLogger(__name__)

# FIX A — Explicit allowlist of every agent node that calls self.llm.invoke().
# Do NOT rely on substring matching of node names — that silently mis-routes any
# new node whose name doesn't happen to contain 'llm' or 'gemini'.
# To add a new LLM-calling node: add its exact node_name string here.
LLM_AGENT_NODES: Set[str] = {
    "fact_extractor",
    "verifier",
    "business_intelligence_agent",
    "entity_graph",
    "question_discovery",
    "keyword_intelligence",
    "competitor_discovery",
    "content_coverage_eval",
    "visibility_scoring",
    "content_agent",
    "recommendation_sim",
    "report_compiler",
    "qa_agent",
}

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
        # Determine retry policy.
        # FIX A — Use explicit node-name set, not fragile substring matching.
        max_attempts = 1
        backoff_seconds = 1.0
        exponential = False

        if agent_name in LLM_AGENT_NODES:
            # LLM calls: real NVIDIA responses can take 3-7+ minutes.
            # 3 attempts × up to ~7 min each, exponential backoff starting at 30s.
            max_attempts = 3          # 1 initial + 2 retries
            backoff_seconds = 30.0    # 30s → 60s between attempts (exponential)
            exponential = True
            logger.info(f"[RETRY-POLICY] node={agent_name} → LLM policy "
                        f"(max_attempts={max_attempts}, backoff={backoff_seconds}s, exponential={exponential})")
        elif "supabase" in agent_name.lower() or "database" in agent_name.lower():
            max_attempts = 4          # 1 initial + 3 retries
            backoff_seconds = 5.0
            exponential = False
        elif "playwright" in agent_name.lower() or "crawler" in agent_name.lower():
            max_attempts = 2          # 1 initial + 1 browser restart
            backoff_seconds = 2.0
            exponential = False
        else:
            # General defaults for non-LLM, non-DB, non-crawler nodes
            max_attempts = 3
            backoff_seconds = 3.0

        last_exception = None
        attempts_made = 0

        for attempt in range(1, max_attempts + 1):
            attempts_made = attempt
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

        # Retries exhausted. Trigger fallback default from fallback_engine.
        # FIX B — Log loudly so fallback output is NEVER silently indistinguishable
        # from real LLM output in the DB or in log files.
        last_diag = self.classifier.classify_and_log(project_id, run_id, agent_name, last_exception) \
            if last_exception else {"error_type": "UNKNOWN", "retryable": False}
        logger.warning(
            f"[FALLBACK-FIRED] node={agent_name} "
            f"reason={last_diag.get('error_type', 'UNKNOWN')} "
            f"retryable={last_diag.get('retryable', False)} "
            f"attempts_made={attempts_made} "
            f"raw_error={str(last_exception)[:300]!r}"
        )
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
