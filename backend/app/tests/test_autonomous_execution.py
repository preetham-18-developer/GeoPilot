"""
test_autonomous_execution.py
Phase 11 — Unit Tests for Autonomous GEO Execution Layer
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.execution_engine import ExecutionEngine
from app.core.page_generator_engine import PageGeneratorEngine
from app.core.schema_generator_engine_v2 import SchemaGeneratorEngineV2
from app.core.internal_link_builder import InternalLinkBuilder
from app.core.authority_builder_engine import AuthorityBuilderEngine
from app.core.execution_learning_engine import ExecutionLearningEngine

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

# 1. Test Execution Task Engine
@patch("app.core.execution_engine.supabase_client")
def test_execution_engine(mock_sb):
    mock_sb.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []

    plans = [
        {"category": "Content", "impact_score": 80.0, "effort_score": 40.0, "priority_score": 75.0, "recommendation": "Expand words"},
        {"category": "Trust", "impact_score": 90.0, "effort_score": 90.0, "priority_score": 85.0, "recommendation": "Show certification"}
    ]

    engine = ExecutionEngine()
    res = engine.run("proj-1", plans)

    assert len(res) == 2
    assert "priority" in res[0]
    assert res[0]["priority"] == "HIGH"
    assert res[1]["priority"] == "CRITICAL"
    assert "description" in res[0]

# 2. Test Page Generator Engine
@patch("app.core.page_generator_engine.supabase_client")
def test_page_generator_engine(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []

    engine = PageGeneratorEngine()
    res = engine.generate("proj-1", "Content", mock_payload)

    assert res is not None
    assert "asset_type" in res
    assert res["asset_type"] == "landing_page"
    assert "body_content" in res["content"]
    assert "# Acme CRM" in res["content"]["body_content"]

# 3. Test Schema Generator Engine v2
@patch("app.core.schema_generator_engine_v2.supabase_client")
def test_schema_generator_engine_v2(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []

    engine = SchemaGeneratorEngineV2()
    res = engine.generate("proj-1", "FAQ", mock_payload)

    assert res is not None
    assert res["asset_type"] == "schema"
    assert "script_snippet" in res["content"]
    assert "<script type=\"application/ld+json\">" in res["content"]["script_snippet"]

# 4. Test Internal Link Builder
@patch("app.core.internal_link_builder.supabase_client")
def test_internal_link_builder(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []

    engine = InternalLinkBuilder()
    res = engine.build_links("proj-1", mock_payload)

    assert res is not None
    assert res["asset_type"] == "internal_link"
    assert "link_placements" in res["content"]
    assert len(res["content"]["link_placements"]) > 0

# 5. Test Authority Builder Engine
@patch("app.core.authority_builder_engine.supabase_client")
def test_authority_builder_engine(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []

    engine = AuthorityBuilderEngine()
    res = engine.generate("proj-1", "Case Study", mock_payload)

    assert res is not None
    assert res["asset_type"] == "case_study"
    assert "references_count" in res["content"]

# 6. Test Execution Learning Engine
@patch("app.core.execution_learning_engine.supabase_client")
def test_execution_learning_engine(mock_sb):
    # Mock task fetch, execution result insert, and learning memory fetch/update
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"category": "Authority", "title": "Audit compliance"}]
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

    engine = ExecutionLearningEngine()
    res = engine.record_completion("proj-1", "task-123", mock_payload)

    assert res is not None
    assert "before_score" in res
    assert "after_score" in res
    assert res["gain"] == 12.0
