"""
test_geo_intelligence.py
Phase 9 — Unit Tests for GEO Citation & Recommendation Intelligence Layer
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.citation_engine import CitationEngine
from app.core.authority_engine_v2 import AuthorityEngineV2
from app.core.recommendation_gap_engine import RecommendationGapEngine
from app.core.competitor_recommendation_engine import CompetitorRecommendationEngine
from app.core.citation_reasoning_engine import CitationReasoningEngine
from app.core.geo_readiness_engine import GEOReadinessEngine

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
    "content_coverage": [{"topic_name": "Information Security Compliance", "coverage_score": 85.0}],
    "entity_nodes": [{"entity_name": "Acme CRM"}]
}

# 1. Test Citation Engine
@patch("app.core.citation_engine.supabase_client")
def test_citation_engine(mock_sb):
    mock_sb.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []
    
    engine = CitationEngine()
    res = engine.run("proj-1", mock_payload)
    
    assert len(res) > 0
    assert "citation_probability" in res[0]
    assert res[0]["citation_probability"] > 0

# 2. Test Authority Engine v2
@patch("app.core.authority_engine_v2.supabase_client")
def test_authority_engine_v2(mock_sb):
    mock_sb.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []
    
    engine = AuthorityEngineV2()
    res = engine.run("proj-1", mock_payload)
    
    assert len(res) > 0
    assert "authority_strength" in res[0]
    assert any(item["entity_name"] == "ISO/IEC 27001 Compliance" for item in res)

# 3. Test Recommendation Gap Engine
@patch("app.core.recommendation_gap_engine.supabase_client")
def test_recommendation_gap_engine(mock_sb):
    mock_sb.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []
    
    engine = RecommendationGapEngine()
    res = engine.run("proj-1", mock_payload)
    
    assert len(res) > 0
    assert "missing_signal" in res[0]
    assert any(item["category"] == "FAQ" for item in res)

# 4. Test Competitor Recommendation Engine
@patch("app.core.competitor_recommendation_engine.supabase_client")
def test_competitor_recommendation_engine(mock_sb):
    mock_sb.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = []
    
    engine = CompetitorRecommendationEngine()
    res = engine.run("proj-1", mock_payload)
    
    assert len(res) > 0
    assert "competitor" in res[0]
    assert "trust_difference" in res[0]

# 5. Test Citation Reasoning Engine
def test_citation_reasoning_engine():
    engine = CitationReasoningEngine()
    res = engine.run("proj-1", mock_payload)
    
    assert len(res) > 0
    assert "confidence_score" in res[0]
    assert "supporting_evidence" in res[0]
    assert "citation_reasons" in res[0]

# 6. Test GEO Readiness Engine
def test_geo_readiness_engine():
    engine = GEOReadinessEngine()
    res = engine.run("proj-1", mock_payload)
    
    assert res is not None
    assert "geo_readiness_score" in res
    assert "status" in res
    assert "breakdown" in res
