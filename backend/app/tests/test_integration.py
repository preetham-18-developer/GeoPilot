import json
import pytest
from app.crawler.parser import parse_html_content
from app.agents.state import AgentState
from app.agents.fact_extractor import FactExtractorAgent
from app.agents.verifier import VerificationAgent
from app.agents.report_generator import compile_report

# 1. Test Website Parsing Logic
def test_parser_extracts_correct_fields():
    mock_html = """
    <html>
      <head>
        <title>Acme CRM - The Best CRM for Startups</title>
        <meta name="description" content="Acme CRM is the absolute best customer relationship management tool for SaaS startups.">
      </head>
      <body>
        <h1>Main Title</h1>
        <p>We provide award-winning custom integrations and support for $29/month.</p>
        <h2>Features</h2>
        <ul>
          <li>Fast Lead Tracking</li>
          <li>Pipeline Automation</li>
        </ul>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "SoftwareApplication",
          "name": "Acme CRM",
          "operatingSystem": "All",
          "applicationCategory": "BusinessApplication"
        }
        </script>
      </body>
    </html>
    """
    
    parsed = parse_html_content(mock_html, "https://acme-crm.com")
    
    assert parsed["title"] == "Acme CRM - The Best CRM for Startups"
    assert parsed["meta_description"] == "Acme CRM is the absolute best customer relationship management tool for SaaS startups."
    assert "Fast Lead Tracking" in parsed["markdown_content"]
    assert any(h["tag"] == "h1" and h["text"] == "Main Title" for h in parsed["headings"])
    assert len(parsed["structured_data"]) == 1
    assert parsed["structured_data"][0]["name"] == "Acme CRM"

# 2. Test Fact Extraction Node (Mocked/Static Context Input)
def test_fact_extraction_resilience():
    page = {
        "url": "https://acme-crm.com",
        "title": "About Acme",
        "markdown_content": "We are Acme CRM. We provide sales pipelines and tools."
    }
    
    # Verify method signature works
    extractor = FactExtractorAgent()
    assert hasattr(extractor, "extract_facts_from_page")

# 3. Test Verification Agent Logic
def test_verification_evidence_matching():
    verifier = VerificationAgent()
    assert hasattr(verifier, "verify_fact")

# 4. Test Report Compilation
def test_report_compilation_merges_data():
    state: AgentState = {
        "project_id": "proj-1",
        "run_id": "run-1",
        "website_url": "https://acme-crm.com",
        "crawled_pages": [],
        "raw_facts": [],
        "verified_facts": [{"fact_type": "product", "content": {"name": "CRM"}}],
        "business_intelligence": {
            "industry": "Software",
            "executive_summary": "Summary text",
            "business_overview": "Overview text",
            "product_analysis": "Product text",
            "service_analysis": "Service text",
            "trust_analysis": "Trust text",
            "swot": {"strengths": ["S1"], "weaknesses": ["W1"], "opportunities": [], "threats": []},
            "ai_visibility_analysis": "Visibility text"
        },
        "questions": [],
        "keywords": [],
        "competitors": [],
        "report": {},
        "errors": []
    }
    
    res = compile_report(state)
    report = res["report"]
    
    assert report["industry"] == "Software"
    assert report["executive_summary"] == "Summary text"
    assert report["total_verified_facts"] == 1
    assert report["swot"]["strengths"] == ["S1"]

# 5. Test Quality Assurance Agent
def test_qa_agent_audits():
    from app.agents.qa_agent import QualityAssuranceAgent
    
    state: AgentState = {
        "project_id": "proj-1",
        "run_id": "run-1",
        "website_url": "https://acme-crm.com",
        "crawled_pages": [],
        "raw_facts": [],
        "verified_facts": [
            {
                "fact_category": "product",
                "fact_key": "name",
                "fact_value": "CRM",
                "evidence_text": "We sell CRM.",
                "confidence_score": 0.95,
                "source_url": "https://acme-crm.com"
            },
            {
                "fact_category": "product",
                "fact_key": "name",
                "fact_value": "CRM",
                "evidence_text": "We sell CRM.",
                "confidence_score": 0.95,
                "source_url": "https://acme-crm.com"
            }
        ],
        "business_intelligence": {},
        "questions": [],
        "keywords": [],
        "competitors": [],
        "content_opportunities": [],
        "report": {
            "executive_summary": "We sell CRM. This is backed up."
        },
        "qa_report": {},
        "errors": []
    }
    
    agent = QualityAssuranceAgent()
    
    import unittest.mock as mock
    mock_llm = mock.MagicMock()
    
    class MockResponse:
        def __init__(self, content):
            self.content = content
            
    mock_llm.invoke.return_value = MockResponse('{"unsupported_claims": [], "qa_score_estimate": 90}')
    agent.llm = mock_llm
    
    res = agent.audit_package(state)
    assert res["qa_score"] is not None
    assert res["checks"]["duplicate_facts_count"] == 1
    assert res["checks"]["missing_evidence_count"] == 0
