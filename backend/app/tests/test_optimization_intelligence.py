"""
test_optimization_intelligence.py
Phase 10 — Unit Tests for Autonomous Optimization & Strategy Intelligence
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.optimization_engine import OptimizationEngine
from app.core.geo_projection_engine import GEOProjectionEngine
from app.core.roi_engine import ROIEngine
from app.core.strategy_engine import StrategyEngine
from app.core.optimization_reasoning_engine import OptimizationReasoningEngine

# Mock payload data
mock_payload = {
    "crawled_pages": [
        {"url": "https://test.com/about", "title": "About Us", "content": "ISO 27001 SOC 2 standards certified expert leader systems privacy policy secure."},
        {"url": "https://test.com/product", "title": "Product Specs", "content": "Our specifications and pricing features detail HIPAA compliance privacy trust."}
    ],
    "verified_facts": [
        {"fact_value": "Acme CRM is certified ISO 27001", "source_url": "https://test.com/about"},
        {"fact_value": "Acme CRM costs $29/mo", "source_url": "https://test.com/product"}
    ],
    "business_profile": {
        "company_name": "Acme CRM",
        "industry": "Software Security",
        "trust_signals": ["ISO 27001 Standard", "HIPAA Compliance"]
    },
    "questions": [{"question": "Is Acme CRM SOC2 certified?"}],
    "keywords": [{"keyword": "acme compliance crm"}],
    "competitors": [{"competitor_name": "Apex Security LLC", "competitor_type": "direct"}],
    "entity_nodes": [{"entity_name": "Acme CRM"}]
}

# 1. Test Optimization Engine
@patch("app.core.optimization_engine.supabase_client")
def test_optimization_engine(mock_sb):
    mock_sb.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []

    engine = OptimizationEngine()
    res = engine.run("proj-1", mock_payload)

    assert len(res) > 0
    assert "priority_score" in res[0]
    assert "estimated_geo_gain" in res[0]
    assert any(item["category"] == "Content" for item in res)
    assert any(item["category"] == "Trust" for item in res)

# 2. Test GEO Projection Engine
@patch("app.core.geo_projection_engine.supabase_client")
def test_geo_projection_engine(mock_sb):
    mock_sb.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []

    plans = [
        {"category": "Content", "estimated_geo_gain": 8.0, "status": "pending"},
        {"category": "Trust", "estimated_geo_gain": 12.0, "status": "pending"}
    ]

    engine = GEOProjectionEngine()
    res = engine.run("proj-1", mock_payload, plans)

    assert res is not None
    assert "current_geo_score" in res
    assert "projected_geo_score" in res
    assert res["expected_gain"] == 20.0
    assert res["confidence"] > 0.0

# 3. Test ROI Engine
@patch("app.core.roi_engine.supabase_client")
def test_roi_engine(mock_sb):
    mock_sb.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []

    plans = [
        {"category": "Content", "impact_score": 80.0, "effort_score": 40.0, "recommendation": "Expand words"},
        {"category": "Trust", "impact_score": 90.0, "effort_score": 90.0, "recommendation": "Show certification"}
    ]

    engine = ROIEngine()
    res = engine.run("proj-1", plans)

    assert len(res) == 2
    assert res[0]["roi_score"] == 2.0  # 80 / 40
    assert "Very High" in res[0]["explanation"]
    assert res[1]["roi_score"] == 1.0  # 90 / 90
    assert "Medium" in res[1]["explanation"]

# 4. Test Strategy Engine
def test_strategy_engine():
    plans = [
        {"category": "Content", "impact_score": 80.0, "effort_score": 40.0, "recommendation": "Expand words"}, # Quick Win
        {"category": "Trust", "impact_score": 90.0, "effort_score": 90.0, "recommendation": "Show certification"} # Long-Term
    ]

    engine = StrategyEngine()
    res = engine.run("proj-1", plans)

    assert "roadmap" in res
    assert len(res["roadmap"]["30_days"]["milestones"]) == 1
    assert len(res["roadmap"]["90_days"]["milestones"]) == 1

# 5. Test Optimization Reasoning Engine
def test_optimization_reasoning_engine():
    plans = [
        {"category": "Content", "priority_score": 75.0, "recommendation": "Expand words"},
        {"category": "Trust", "priority_score": 85.0, "recommendation": "Show certification"}
    ]

    engine = OptimizationReasoningEngine()
    res = engine.run("proj-1", plans)

    assert len(res) == 2
    assert "signals_involved" in res[0]
    assert "explanation" in res[0]
    assert "expected_outcome" in res[0]
