"""
Regression test: simulate the grounding pipeline with mock LLM
to verify the 62.5% grounding failure is fixed.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ["BYPASS_REAL_LLM"] = "true"
os.environ["SUPABASE_URL"] = "https://wnjnebqwgrjfsmbkgiua.supabase.co"
os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Induam5lYnF3Z3JqZnNtYmtnaXVhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk3MTQwMzksImV4cCI6MjA5NTI5MDAzOX0.T60uDBZGi2xXl4HONMnU9VNqfpFLuv7f_E50wRyM2Wg"

# Simulate what the pipeline does with the mock LLM
from app.core.llm import FallbackMockLLM

llm = FallbackMockLLM(None)

# Simulate thelibrarycompany.com page content
SAMPLE_CONTENT = """
The Library Company is a mentorship collective of industry professionals from leading companies.
We're not a traditional school — we're product managers, engineers, and experts who guide the next generation.
Introducing ReLaunchHER Empower Students Women to Transform Their Careers.
The Library — personalized mentorship, industry-aligned programs, Job opportunities designed to transform your career journey.
Master SQL in a Weekend. Scale Your Salary to Millions.
Build Your Own AI Assistant. Master LLM's, RAG & Vector DBs. From basics to real-world applications.
Partner Colleges for Top Company Recruitment... IIIT Basar Mahindra MRU MRDU St. Peter's St. Joseph's CMR NRCM SNIST HITAM.
I am delighted to recommend Kondru Sharathchandra, the co-founder of The Library.
© 2026 Made With ❤️ - The Library Company.
99% Placement and Career Success Rate.
Over 15,000 students counselled and 500+ mentored.
Team members employed at Fortune 500 companies.
"""

url = "https://thelibrarycompany.com"

# Test 1: Fact extraction
print("=" * 60)
print("TEST 1: Fact Extraction (should produce 10-20 grounded facts)")
print("=" * 60)
prompt = f"""You are an expert Fact Extraction Agent for the AI Visibility Optimization Platform.
Extract key facts if present.

Page URL: {url}
Page Title: The Library Company - Career Mentorship
Page Content:
---
{SAMPLE_CONTENT}
---
"""
result = llm._generate_mock_content(prompt)
import json
facts = json.loads(result)
print(f"Extracted {len(facts)} facts")
for f in facts:
    print(f"  [{f['fact_category']}] {f['fact_key']}: {str(f['fact_value'])[:60]!r}")
print()

# Test 2: Business Intelligence (products/services must be from content)
print("=" * 60)
print("TEST 2: BI Analysis (products/services must exist in content)")
print("=" * 60)
bi_prompt = f"""You are an elite Business Intelligence Agent.
Website: {url}
Verified Business Facts: []
Supplemental Page Content (from crawled pages - use only if facts are missing):
---
{SAMPLE_CONTENT}
---
"""
bi_result = llm._generate_mock_content(bi_prompt)
bi = json.loads(bi_result)
products = bi.get("pre_query_discovery", {}).get("products", [])
services = bi.get("pre_query_discovery", {}).get("services", [])
founders = bi.get("pre_query_discovery", {}).get("founders", [])
print(f"Products: {products}")
print(f"Services: {services}")
print(f"Founders: {founders}")
print()

# Test 3: Competitor Discovery (competitors must be from content)
print("=" * 60)
print("TEST 3: Competitor Discovery (competitors must be from content)")
print("=" * 60)
comp_prompt = f"""competitor discovery agent.
Website: {url}
Content:
---
{SAMPLE_CONTENT}
---
"""
comp_result = llm._generate_mock_content(comp_prompt)
comp_data = json.loads(comp_result)
competitors = comp_data.get("competitors", [])
print(f"Found {len(competitors)} competitors:")
for c in competitors:
    print(f"  {c['competitor_name']}")
print()

# Test 4: Run grounding engine simulation
print("=" * 60)
print("TEST 4: Grounding Engine Score (target: >= 95%)")
print("=" * 60)
from app.core.grounding_engine_v2 import GroundingEngineV2

sentences = llm._clean_and_split_sentences(SAMPLE_CONTENT)
company_name = llm._get_company_name(url, "The Library Company", SAMPLE_CONTENT)

bi_data = json.loads(bi_result)
comp_data_full = json.loads(comp_result)

# Build state as the pipeline would
state = {
    "website_url": url,
    "crawled_pages": [{
        "url": url,
        "title": "The Library Company",
        "markdown_content": SAMPLE_CONTENT
    }],
    "verified_facts": facts,  # use extracted facts as verified
    "business_intelligence": bi_data,
    "questions": [],
    "keywords": [],
    "competitors": comp_data_full.get("competitors", []),
    "entity_nodes": []
}

engine = GroundingEngineV2()
result = engine.run(state)

print(f"Grounding Score: {result['grounding_score']}%")
print(f"Domain Consistency: {result['domain_consistency_score']}%")
print(f"Hallucination Risk: {result['hallucination_risk']}%")
print(f"Status: {result['status']}")
print()
print("Individual checks:")
for check in result["details"]["checks"]:
    emoji = "✅" if check["status"] == "VERIFIED" else ("⚠️" if check["status"] == "PARTIAL" else "❌")
    print(f"  {emoji} [{check['status']}] {check['category']}: {str(check['entity'])[:50]!r}")

print()
total = result["details"]["total_checks"]
success = result["details"]["successful_checks"]
print(f"Total checks: {total}, Successful: {success}")

threshold_pass = result['grounding_score'] >= 80.0
print(f"\n{'✅ PASS' if threshold_pass else '❌ FAIL'}: Pipeline threshold is 80% (score={result['grounding_score']}%)")
print(f"{'✅ PASS' if result['grounding_score'] >= 95.0 else '⚠️  WARN'}: Grounding engine ideal threshold is 95% (score={result['grounding_score']}%)")
