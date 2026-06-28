"""
test_reliability_intelligence.py
Phase 8 — Unit Tests for Reliability & Self-Healing Engines
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.core.checkpoint_engine import CheckpointEngine
from app.core.idempotency_engine import IdempotencyEngine
from app.core.dependency_monitor import DependencyMonitor
from app.core.error_classifier import ErrorClassifier
from app.core.retry_engine import RetryEngine
from app.core.reliability_score_engine import ReliabilityScoreEngine
from app.core.timeline_engine import TimelineEngine

# 1. Test Checkpoint Engine
@patch("app.core.checkpoint_engine.supabase_client")
def test_checkpoint_engine(mock_sb):
    # Mock supabase select for existing checkpoint
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "chk-123"}]

    engine = CheckpointEngine()
    res = engine.save_checkpoint(
        run_id="run-1",
        project_id="proj-1",
        node_name="fact_extractor",
        status="completed",
        state_data={"test_var": "abc"}
    )
    
    assert res is not None
    assert res["id"] == "chk-123"

# 2. Test Idempotency Engine
@patch("app.core.idempotency_engine.supabase_client")
def test_idempotency_engine(mock_sb):
    # Mock questions search
    mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": "q-1"}]
    
    engine = IdempotencyEngine()
    
    # Check already processed in state
    assert engine.already_processed("proj-1", "question_discovery", {"questions": [{"q": 1}]}) is True
    
    # Check already processed in DB
    assert engine.already_processed("proj-1", "question_discovery", {}) is True

# 3. Test Dependency Monitor
@patch("app.core.dependency_monitor.supabase_client")
def test_dependency_monitor(mock_sb):
    mock_sb.table.return_value.select.return_value.limit.return_value.execute.return_value.data = []
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []

    monitor = DependencyMonitor()
    res = monitor.check_all()
    
    assert len(res) > 0
    assert any(d["service_name"] == "Supabase" for d in res)
    assert any(d["service_name"] == "Gemini" for d in res)

# 4. Test Error Classifier
@patch("app.core.error_classifier.supabase_client")
def test_error_classifier(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "err-1"}]
    
    classifier = ErrorClassifier()
    
    # Try rate limit exception
    exc = Exception("API quota limit reached or rate limit exceeded")
    diag = classifier.classify_and_log("proj-1", "run-1", "fact_extractor", exc)
    
    assert diag["error_type"] == "RATE_LIMIT"
    assert diag["severity"] == "HIGH"
    assert diag["retryable"] is True

# 5. Test Retry Engine
@patch("app.core.retry_engine.supabase_client")
def test_retry_engine_success(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []
    
    engine = RetryEngine()
    
    mock_func = MagicMock(return_value="success_state")
    
    res = engine.execute_with_retry(
        project_id="proj-1",
        run_id="run-1",
        agent_name="gemini_llm",
        func=mock_func
    )
    
    assert res == "success_state"
    mock_func.assert_called_once()

# 6. Test Reliability Score Engine
@patch("app.core.reliability_score_engine.supabase_client")
def test_reliability_score_engine(mock_sb):
    # Mock success responses
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"success": True}]
    mock_sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [{"uptime_percentage": 100.0}]
    mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"status": "completed"}]
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []
    
    engine = ReliabilityScoreEngine()
    res = engine.compute_and_save("proj-1", "run-1")
    
    assert res is not None
    assert "reliability_score" in res
    assert res["reliability_score"] > 50.0

# 7. Test Timeline Engine
@patch("app.core.timeline_engine.supabase_client")
def test_timeline_engine(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "time-1"}]
    
    engine = TimelineEngine()
    started = datetime.now(timezone.utc)
    completed = datetime.now(timezone.utc)
    
    res = engine.record_node_duration(
        run_id="run-1",
        node_name="fact_extractor",
        started_at=started,
        completed_at=completed,
        duration_ms=1200
    )
    
    assert res is not None
    assert res["id"] == "time-1"
