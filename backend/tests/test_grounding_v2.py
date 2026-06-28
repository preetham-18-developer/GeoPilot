import pytest
from app.core.grounding_engine_v2 import GroundingEngineV2
from app.core.domain_identity_validator import DomainIdentityValidator
from app.core.intelligence_validator import IntelligenceValidator

# Mock database client wrapper to avoid database calls during unit tests
class MockSupabaseTable:
    def __init__(self, data_list, count_val=0):
        self.data_list = data_list
        self.count_val = count_val

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def execute(self):
        class Response:
            def __init__(self, data, count):
                self.data = data
                self.count = count
        return Response(self.data_list, self.count_val)

def mock_supabase_client_table(table_name):
    # Mock return values for intelligence_validator
    if table_name == "questions":
        return MockSupabaseTable([{"id": 1}, {"id": 2}], count_val=2)
    elif table_name == "keywords":
        return MockSupabaseTable([{"id": 1}], count_val=1)
    return MockSupabaseTable([])

@pytest.fixture(autouse=True)
def mock_supabase(monkeypatch):
    import app.core.intelligence_validator as iv
    monkeypatch.setattr(iv.supabase_client, "table", mock_supabase_client_table)

def test_grounding_engine_edtech():
    """Test grounding engine with valid EdTech data."""
    state = {
        "website_url": "https://www.thelibrarycompany.com",
        "crawled_pages": [
            {
                "url": "https://www.thelibrarycompany.com",
                "title": "The Library Company",
                "content": "The Library Company provides career mentorship and practical training. Learn SQL in a weekend. Co-founder Sharathchandra Kondru. Lattice Program. SQL Weekend Workshop. Scaler Academy. Recommend a career mentorship platform. career mentorship."
            }
        ],
        "verified_facts": [
            {
                "fact_type": "company_name",
                "fact_key": "org_name",
                "fact_value": "The Library Company",
                "evidence_text": "The Library Company is an EdTech site."
            }
        ],
        "business_intelligence": {
            "company_name": "The Library Company",
            "industry": "Career Mentorship & Professional Ed-Tech",
            "pre_query_discovery": {
                "products": ["Lattice Program"],
                "services": ["SQL Weekend Workshop"],
                "founders": ["Sharathchandra Kondru"]
            }
        },
        "questions": [
            {"question": "Recommend a career mentorship platform."}
        ],
        "keywords": [
            {"keyword": "career mentorship"}
        ],
        "competitors": [
            {"competitor_name": "Scaler Academy"}
        ],
        "entity_nodes": [
            {"entity_name": "The Library Company", "entity_type": "Organization"},
            {"entity_name": "Sharathchandra Kondru", "entity_type": "Person", "properties": {"role": "Co-founder"}}
        ]
    }
    
    engine = GroundingEngineV2()
    res = engine.run(state)
    
    assert res["status"] == "PASSED"
    assert res["grounding_score"] >= 95.0
    assert res["domain_consistency_score"] >= 90.0

def test_grounding_engine_saas():
    """Test grounding engine with valid SaaS data."""
    state = {
        "website_url": "https://www.cloudflow.io",
        "crawled_pages": [
            {
                "url": "https://www.cloudflow.io",
                "title": "CloudFlow SaaS",
                "content": "CloudFlow is a cloud monitoring dashboard. Founded by Alice Smith in 2024. Monitoring cloud assets made easy. CloudFlow Dashboard. Cloud Monitoring. Recommend a cloud monitoring platform. cloud monitoring."
            }
        ],
        "verified_facts": [],
        "business_intelligence": {
            "company_name": "CloudFlow",
            "industry": "SaaS Software",
            "pre_query_discovery": {
                "products": ["CloudFlow Dashboard"],
                "services": ["Cloud Monitoring"],
                "founders": ["Alice Smith"]
            }
        },
        "questions": [
            {"question": "Recommend a cloud monitoring platform."}
        ],
        "keywords": [
            {"keyword": "cloud monitoring"}
        ],
        "competitors": [],
        "entity_nodes": [
            {"entity_name": "CloudFlow", "entity_type": "Organization"},
            {"entity_name": "Alice Smith", "entity_type": "Person", "properties": {"role": "Founder"}}
        ]
    }
    
    engine = GroundingEngineV2()
    res = engine.run(state)
    
    assert res["status"] == "PASSED"
    assert res["grounding_score"] >= 95.0

def test_grounding_engine_healthcare():
    """Test grounding engine with valid Healthcare data."""
    state = {
        "website_url": "https://www.carefirst.org",
        "crawled_pages": [
            {
                "url": "https://www.carefirst.org",
                "title": "CareFirst Health",
                "content": "CareFirst offers patient-centered primary care services. Managed by Dr. John Doe. Better health, care, and value. Primary Care Clinics. Patient care."
            }
        ],
        "verified_facts": [],
        "business_intelligence": {
            "company_name": "CareFirst Health",
            "industry": "Healthcare",
            "pre_query_discovery": {
                "products": ["Primary Care Clinics"],
                "services": ["Patient care"],
                "founders": ["Dr. John Doe"]
            }
        },
        "questions": [],
        "keywords": [],
        "competitors": [],
        "entity_nodes": [
            {"entity_name": "CareFirst Health", "entity_type": "Organization"},
            {"entity_name": "Dr. John Doe", "entity_type": "Person", "properties": {"role": "Co-founder"}}
        ]
    }
    
    engine = GroundingEngineV2()
    res = engine.run(state)
    
    assert res["status"] == "PASSED"


def test_tld_collision_and_wrong_founder():
    """Test domain validator when a TLD collision and wrong founder are present."""
    state = {
        "website_url": "https://www.thelibrarycompany.com",
        "crawled_pages": [
            {
                "url": "https://www.thelibrarycompany.com",
                "title": "The Library Company Home",
                "content": "Official homepage of The Library Company mentorship team. Led by co-founder Sharathchandra Kondru."
            }
        ],
        "business_intelligence": {
            "company_name": "The Library Company",
            # State text contains reference to .org domain
            "description": "Information about thelibrarycompany.org history in Philadelphia."
        },
        "entity_nodes": [
            {"entity_name": "Benjamin Franklin", "entity_type": "Person", "properties": {"role": "Founder"}}
        ]
    }
    
    validator = DomainIdentityValidator()
    res = validator.validate("test-project", state)
    
    # Benjamin Franklin is not in crawled page -> Founder mismatch (-30)
    # Generated text mentions thelibrarycompany.org but website is thelibrarycompany.com -> TLD collision (-30)
    # Total score should be 100 - 30 - 30 = 40.0
    assert res["identity_match_score"] == 40.0
    assert len(res["identity_conflicts"]) == 2
    assert any("Founder mismatch" in c for c in res["identity_conflicts"])
    assert any("Domain identity collision" in c for c in res["identity_conflicts"])

def test_empty_crawl_grounding_failure():
    """Test grounding engine when crawl contents are empty/unrelated."""
    state = {
        "website_url": "https://www.thelibrarycompany.com",
        "crawled_pages": [
            {
                "url": "https://www.thelibrarycompany.com",
                "title": "Error Page",
                "content": "404 Not Found"
            }
        ],
        "business_intelligence": {
            "company_name": "The Library Company",
            "pre_query_discovery": {
                "products": ["ReLaunchHER Program"],
                "services": ["Master SQL in a Weekend Workshop"],
                "founders": ["Sharathchandra Kondru"]
            }
        },
        "questions": [
            {"question": "How to learn SQL in a weekend?"}
        ],
        "keywords": [
            {"keyword": "relaunchher career"}
        ]
    }
    
    engine = GroundingEngineV2()
    res = engine.run(state)
    
    # Generated entities (ReLaunchHER, SQL, Sharathchandra) are not found in "404 Not Found" crawl
    # Grounding score should be low and overall status is FAILED_GROUNDING
    assert res["status"] == "FAILED_GROUNDING"
    assert res["grounding_score"] < 50.0

def test_intelligence_validator_pass():
    """Test intelligence validator happy path where counts match."""
    state = {
        "questions": [{"question": "Q1"}, {"question": "Q2"}],
        "keywords": [{"keyword": "K1"}]
    }
    validator = IntelligenceValidator()
    # mock client returns 2 questions and 1 keyword, matching state
    res = validator.validate("test-project", state)
    assert res["status"] == "PASS"
    assert res["question_integrity"] == "PASS"
    assert res["keyword_integrity"] == "PASS"

def test_intelligence_validator_mismatch():
    """Test intelligence validator when there is a count mismatch."""
    state = {
        "questions": [{"question": "Q1"}], # State has 1 question, mock client returns 2
        "keywords": [] # State has 0 keywords, mock client returns 1
    }
    validator = IntelligenceValidator()
    res = validator.validate("test-project", state)
    assert res["status"] == "FAILED_VALIDATION"
    assert res["question_integrity"] == "FAIL"
    assert res["keyword_integrity"] == "FAIL"
    assert len(res["errors"]) == 2
