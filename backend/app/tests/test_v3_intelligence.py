import pytest
import unittest.mock as mock
from app.agents.state import AgentState
from app.agents.question_discovery import run_question_discovery, QuestionDiscoveryAgent
from app.agents.keyword_intelligence import run_keyword_intelligence, KeywordIntelligenceAgent

class MockResponse:
    def __init__(self, content):
        self.content = content

def test_question_discovery_v3_generation_and_scoring():
    # Setup mock agent state
    state: AgentState = {
        "project_id": "proj-v3",
        "run_id": "run-v3",
        "website_url": "https://acme-crm.com",
        "crawled_pages": [],
        "raw_facts": [],
        "verified_facts": [],
        "business_intelligence": {
            "company_name": "Acme CRM",
            "industry": "Sales Software",
            "description": "Acme provides sales pipeline automation.",
            "pre_query_discovery": {
                "products": ["Acme CRM Pro", "Acme Lead Finder"],
                "services": ["CRM Setup", "API Integration"],
                "industry_topics": ["SaaS CRM", "Lead Management"],
                "technologies": ["Python", "React", "PostgreSQL"],
                "processes": ["lead tracking", "deal closing"],
                "buyer_personas": {
                    "Founder": "Founder: Seeks bootstrap scaling and customer acquisition.",
                    "CEO": "CEO: Aims for revenue growth and market share expansion."
                },
                "pain_points": {
                    "operational": "Manual data entry overhead",
                    "technical": "API sync delays"
                },
                "desired_outcomes": {
                    "reduce_cost": "Minimize admin staff requirements",
                    "increase_revenue": "Close deals 2x faster"
                }
            }
        },
        "questions": [],
        "keywords": [],
        "competitors": [],
        "content_opportunities": [],
        "report": {},
        "qa_report": {},
        "errors": []
    }
    
    # Mock the LLM to return standard seeds
    mock_llm = mock.MagicMock()
    mock_llm.invoke.return_value = MockResponse(
        '['
        '  {'
        '    "question": "Recommend a virtual science lab platform for higher education Canvas integration",'
        '    "question_type": "Direct Recommendation Queries",'
        '    "intent": "commercial",'
        '    "confidence_score": 0.95,'
        '    "priority": "High",'
        '    "recommended_answer": "ABC Technologies provides ABC Lab LMS.",'
        '    "recommendation_score": 90,'
        '    "commercial_score": 85,'
        '    "intent_score": 95,'
        '    "priority_score": 90,'
        '    "difficulty_estimate": "Medium",'
        '    "opportunity_estimate": "High"'
        '  }'
        ']'
    )
    
    # Patch the LLM inside QuestionDiscoveryAgent
    with mock.patch('app.agents.question_discovery.get_llm', return_value=mock_llm):
        result = run_question_discovery(state)
        questions = result.get("questions", [])
        
        # Assert size requirements
        assert len(questions) >= 1000
        
        # Assert scoring properties on first 5 questions
        for q in questions[:5]:
            assert "question" in q
            assert "question_type" in q
            assert "intent" in q
            assert "recommendation_score" in q
            assert "commercial_score" in q
            assert "intent_score" in q
            assert "priority_score" in q
            assert "difficulty_estimate" in q
            assert "opportunity_estimate" in q
            
            # Verify score boundaries
            assert 0 <= q["recommendation_score"] <= 100
            assert 0 <= q["commercial_score"] <= 100
            assert 0 <= q["intent_score"] <= 100
            assert 0 <= q["priority_score"] <= 100
            assert q["difficulty_estimate"] in ["Easy", "Medium", "Hard"]
            assert q["opportunity_estimate"] in ["Low", "Medium", "High"]
            assert q["priority"] in ["Low", "Medium", "High"]

def test_keyword_intelligence_v3_extraction_and_sourcing():
    # Setup mock agent state
    state: AgentState = {
        "project_id": "proj-v3",
        "run_id": "run-v3",
        "website_url": "https://acme-crm.com",
        "crawled_pages": [],
        "raw_facts": [],
        "verified_facts": [],
        "business_intelligence": {
            "company_name": "Acme CRM",
            "industry": "Sales Software",
            "description": "Acme provides sales pipeline automation.",
            "pre_query_discovery": {
                "products": ["Acme CRM Pro"],
                "services": ["CRM Setup"],
                "industry_topics": ["SaaS CRM"],
                "technologies": ["Python"],
                "processes": ["lead tracking"],
                "buyer_personas": {
                    "Founder": "Founder: Seeks bootstrap scaling."
                },
                "pain_points": {
                    "operational": "Manual data entry"
                },
                "desired_outcomes": {
                    "reduce_cost": "Minimize admin staff"
                }
            }
        },
        "questions": [
            {"question": "How to scale sales CRM?", "question_type": "Scaling Queries"}
        ],
        "keywords": [],
        "competitors": [],
        "content_opportunities": [],
        "report": {},
        "qa_report": {},
        "errors": []
    }
    
    # Mock the LLM to return standard seeds
    mock_llm = mock.MagicMock()
    mock_llm.invoke.return_value = MockResponse(
        '['
        '  {'
        '    "keyword": "LTI physics virtual labs",'
        '    "keyword_type": "Primary",'
        '    "intent": "commercial",'
        '    "cluster": "LMS Simulations",'
        '    "confidence_score": 0.95,'
        '    "priority": "High",'
        '    "difficulty_estimate": "Medium",'
        '    "opportunity_estimate": "High",'
        '    "source": "Verified Facts"'
        '  }'
        ']'
    )
    
    # Patch the LLM inside KeywordIntelligenceAgent
    with mock.patch('app.agents.keyword_intelligence.get_llm', return_value=mock_llm):
        result = run_keyword_intelligence(state)
        keywords = result.get("keywords", [])
        
        # Assert size requirements
        assert len(keywords) >= 5000
        
        # Assert scoring and sourcing properties on first 5 keywords
        for kw in keywords[:5]:
            assert "keyword" in kw
            assert "keyword_type" in kw
            assert "intent" in kw
            assert "priority" in kw
            assert "difficulty_estimate" in kw
            assert "opportunity_estimate" in kw
            assert "confidence_score" in kw
            assert "source" in kw
            
            # Verify V3 types list bounds
            assert kw["keyword_type"] in [
                'Primary', 'Commercial', 'Problem', 'Outcome', 'Topic', 'Industry', 
                'Entity', 'Location', 'Role', 'Voice Search', 'AI Search', 'Long Tail', 
                'Semantic', 'Authority', 'Trend', 'Opportunity'
            ]
            
            assert kw["priority"] in ["Low", "Medium", "High"]
            assert kw["difficulty_estimate"] in ["Easy", "Medium", "Hard"]
            assert kw["opportunity_estimate"] in ["Low", "Medium", "High"]
            assert 0.0 <= kw["confidence_score"] <= 1.0
            assert len(kw["source"]) > 0
