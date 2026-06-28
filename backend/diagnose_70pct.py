"""
PRECISE diagnostic: reproduce 70% score + TLD conflict = 1 with a real URL scenario.
Run from backend/ with: .\\venv\\Scripts\\python.exe diagnose_70pct.py
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["BYPASS_REAL_LLM"] = "true"
os.environ["SUPABASE_URL"] = "https://wnjnebqwgrjfsmbkgiua.supabase.co"
os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Induam5lYnF3Z3JqZnNtYmtnaXVhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk3MTQwMzksImV4cCI6MjA5NTI5MDAzOX0.T60uDBZGi2xXl4HONMnU9VNqfpFLuv7f_E50wRyM2Wg"

from app.core.llm import FallbackMockLLM
from app.core.grounding_engine_v2 import GroundingEngineV2
from app.core.domain_identity_validator import DomainIdentityValidator

llm = FallbackMockLLM(None)

# Simulate the actual thelibrarycompany.com crawled content
# (what Playwright would return from the real site)
SAMPLE_CONTENT = """
The Library Company is a mentorship collective of industry professionals from leading companies.
We are not a traditional school. We are product managers, engineers, and experts who guide the next generation.
Introducing ReLaunchHER Empower Students Women to Transform Their Careers.
The Library provides personalized mentorship, industry-aligned programs, and Job opportunities designed to transform your career journey.
Master SQL in a Weekend. Scale Your Salary to Millions.
Build Your Own AI Assistant. Master LLMs, RAG and Vector DBs. From basics to real-world applications.
Partner Colleges for Top Company Recruitment. IIIT Basar Mahindra MRU MRDU St Peters St Josephs CMR NRCM SNIST HITAM.
I am delighted to recommend Kondru Sharathchandra, the co-founder of The Library.
2026 Made With love - The Library Company.
99 percent Placement and Career Success Rate.
Over 15000 students counselled and 500 plus mentored.
Team members employed at Fortune 500 companies.
"""

url = "https://thelibrarycompany.com"
sentences = llm._clean_and_split_sentences(SAMPLE_CONTENT)
company_name = llm._get_company_name(url, "The Library Company - Career Mentorship", SAMPLE_CONTENT)

print(f"Company name detected: {company_name!r}")
print(f"Sentences extracted: {len(sentences)}")
print()

# Build BI output
bi_prompt = f"You are an elite Business Intelligence Agent.\nWebsite: {url}\nVerified Business Facts: []\nSupplemental Page Content (from crawled pages - use only if facts are missing):\n---\n{SAMPLE_CONTENT}\n---"
bi_result = llm._generate_mock_content(bi_prompt)
bi = json.loads(bi_result)

print("=== BI Output ===")
print(f"company_name: {bi.get('company_name')!r}")
print(f"description: {bi.get('description','')[:80]!r}")
print(f"mission: {bi.get('mission','')[:80]!r}")
print(f"vision: {bi.get('vision','')[:80]!r}")
print(f"usp: {bi.get('usp','')[:80]!r}")
print(f"target_audience: {bi.get('target_audience','')[:80]!r}")
print()

pqd = bi.get("pre_query_discovery", {})
print(f"products: {pqd.get('products', [])}")
print(f"services: {pqd.get('services', [])}")
print(f"founders: {pqd.get('founders', [])}")
print()

# Build competitors output
comp_prompt = f"competitor discovery agent.\nWebsite: {url}\nContent:\n---\n{SAMPLE_CONTENT}\n---"
comp_result = llm._generate_mock_content(comp_prompt)
comp_data = json.loads(comp_result)
competitors = comp_data.get("competitors", [])
print(f"Competitors found: {[c['competitor_name'] for c in competitors]}")
print()

# Build entity graph
graph_prompt = f"entity graph agent.\nWebsite: {url}\nContent:\n---\n{SAMPLE_CONTENT}\n---"
graph_result = llm._generate_mock_content(graph_prompt)
graph_data = json.loads(graph_result)
nodes = graph_data.get("nodes", [])
print(f"Entity nodes: {[(n['entity_name'], n['entity_type']) for n in nodes]}")
print()

# Build facts
facts_prompt = f"You are an expert Fact Extraction Agent for the AI Visibility Optimization Platform.\nExtract key facts if present.\nPage URL: {url}\nPage Title: The Library Company\nPage Content:\n---\n{SAMPLE_CONTENT}\n---"
facts_result = llm._generate_mock_content(facts_prompt)
facts = json.loads(facts_result)
print(f"Facts extracted: {len(facts)}")
print()

# =========================
# CHECK: TLD conflict scan on BI identity fields
# =========================
print("=== TLD CONFLICT SCAN (domain_identity_validator logic) ===")
root_domain = "thelibrarycompany.com"
domain_name = root_domain.split('.')[0]  # "thelibrarycompany"

identity_fields_text = " ".join([
    str(bi.get("company_name", "") or ""),
    str(bi.get("description", "") or ""),
    str(bi.get("mission", "") or ""),
    str(bi.get("vision", "") or ""),
    str(bi.get("usp", "") or ""),
    str(bi.get("target_audience", "") or ""),
])
print(f"Identity fields text: {identity_fields_text[:200]!r}")
found_domains = re.findall(r"([a-zA-Z][a-zA-Z0-9-]*\.[a-z]{2,6})\b", identity_fields_text)
print(f"Domain patterns found in BI fields: {found_domains}")
for fd in set(found_domains):
    fd_l = fd.lower()
    if fd_l == root_domain:
        print(f"  {fd} → SAME as project domain (OK)")
    elif fd_l.split('.')[0] == domain_name:
        print(f"  ❌ TLD COLLISION: {fd} base matches project domain {root_domain}")
    else:
        print(f"  {fd} → different base name (OK, no conflict)")
print()

# =========================
# CHECK: grounding engine entity domain scan
# =========================
print("=== GROUNDING ENGINE ENTITY DOMAIN SCAN ===")
entities_to_check = []
comp_name_bi = bi.get("company_name", "")
if comp_name_bi:
    entities_to_check.append(("Company Name", comp_name_bi))
for p in pqd.get("products", []):
    entities_to_check.append(("Product", p))
for s in pqd.get("services", []):
    entities_to_check.append(("Service", s))
for f in pqd.get("founders", []):
    entities_to_check.append(("Founder", f))
for c in competitors:
    entities_to_check.append(("Competitor", c["competitor_name"]))

for category, entity in entities_to_check:
    entity_domains = re.findall(r"[a-zA-Z0-9-]+\.[a-z]{2,6}", entity.lower())
    for ed in entity_domains:
        if ed != root_domain and ed.split('.')[0] == root_domain.split('.')[0]:
            print(f"  ❌ ENTITY TLD CONFLICT: [{category}] {entity!r} contains {ed!r}")

print("  (done scanning entities)")
print()

# =========================
# RUN FULL GROUNDING ENGINE
# =========================
print("=== FULL GROUNDING + IDENTITY VALIDATOR RUN ===")
state = {
    "website_url": url,
    "crawled_pages": [{
        "url": url,
        "title": "The Library Company - Career Mentorship",
        "markdown_content": SAMPLE_CONTENT
    }],
    "verified_facts": facts,
    "business_intelligence": bi,
    "questions": [],
    "keywords": [],
    "competitors": competitors,
    "entity_nodes": nodes
}

dv = DomainIdentityValidator()
identity_res = dv.validate("test-project", state)
print(f"Identity Score: {identity_res['identity_match_score']}%")
print(f"Identity Conflicts: {identity_res['identity_conflicts']}")
print()

engine = GroundingEngineV2()
result = engine.run(state, identity_res)
print(f"Grounding Score: {result['grounding_score']}%")
print(f"Domain Conflicts: {result['details']['domain_conflicts']}")
print(f"Status: {result['status']}")
print()
print("Individual checks:")
for check in result["details"]["checks"]:
    emoji = "✅" if check["status"] == "VERIFIED" else ("⚠️" if check["status"] == "PARTIAL" else ("🔴" if check["status"] == "DOMAIN_CONFLICT" else "❌"))
    print(f"  {emoji} [{check['status']}] {check['category']}: {str(check['entity'])[:60]!r}")
