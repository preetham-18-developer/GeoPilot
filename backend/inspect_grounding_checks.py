import sys
sys.path.insert(0, ".")

def test_inspect():
    edtech_content = (
        "© 2026 Made With ❤️ - The Library Company. "
        "About The Library A mentorship collective of industry professionals from leading companies. "
        "We're not a traditional school—we're product managers, engineers, and experts who guide the next generation to connect passion with profession. "
        "Introducing ReLaunchHER Empower Students Women to Transform Their Careers. "
        "The Library — personalized mentorship, industry-aligned programs, Job opportunities designed to transform your career journey. "
        "Master SQL in a Weekend. Scale Your Salary to Millions. "
        "Build Your Own AI Assistant. Master LLM's, RAG & Vector DBs. From basics to real-world applications. "
        "Partner Colleges for Top Company Recruitment ... IIIT Basar Mahindra MRU MRDU St. Peter's St. Joseph's CMR NRCM SNIST HITAM. "
        "I am delighted to recommend Kondru sharathchandra, the co-founder of The Library, who has been a guiding light in my personal and professional journey. "
        "Lattice Program. Lattice Framework. Personalized Mentorship. Master SQL in a Weekend Workshop. Build Your Own AI Assistant Workshop."
    )
    
    # 1. Test EdTech case
    state_edtech = {
        "website_url": "https://www.thelibrarycompany.com",
        "crawled_pages": [
            {
                "url": "https://www.thelibrarycompany.com",
                "title": "The Library Company",
                "content": edtech_content
            }
        ],
        "verified_facts": [],
        "business_intelligence": {
            "company_name": "The Library Company",
            "pre_query_discovery": {
                "products": ["ReLaunchHER", "Lattice"],
                "services": ["Master SQL", "AI Assistant", "Personalized Mentorship"],
                "founders": ["Kondru Sharathchandra"]
            }
        },
        "competitors": [{"competitor_name": "Mahindra"}],
        "keywords": [{"keyword": "relaunchher"}],
        "questions": [{"question": "What is ReLaunchHER?"}],
        "entity_nodes": [
            {"entity_name": "The Library Company", "entity_type": "Organization"},
            {"entity_name": "Kondru Sharathchandra", "entity_type": "Person", "properties": {"role": "Co-founder"}}
        ]
    }
    
    # 2. Test Empty case
    state_empty = {
        "website_url": "https://www.thelibrarycompany-empty.com",
        "crawled_pages": [
            {
                "url": "https://www.thelibrarycompany-empty.com",
                "title": "Error Page",
                "content": "404 Not Found"
            }
        ],
        "business_intelligence": {
            "company_name": "The Library Company",
            "pre_query_discovery": {
                "products": ["ReLaunchHER"],
                "services": ["Master SQL"]
            }
        },
        "questions": [{"question": "What is ReLaunchHER?"}],
        "keywords": [{"keyword": "relaunchher"}]
    }
    
    from app.core.grounding_engine_v2 import GroundingEngineV2
    engine = GroundingEngineV2()
    
    # We edit the engine's run method to skip questions and keywords in entities_to_check
    # Let's inspect what happens:
    print("--- RUNNING EDTECH SITE ---")
    res_edtech = engine.run(state_edtech)
    print("Score:", res_edtech["grounding_score"])
    print("Status:", res_edtech["status"])
    
    print("\n--- RUNNING EMPTY SITE ---")
    res_empty = engine.run(state_empty)
    print("Score:", res_empty["grounding_score"])
    print("Status:", res_empty["status"])

if __name__ == "__main__":
    test_inspect()
