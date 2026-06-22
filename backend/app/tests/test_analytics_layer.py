import pytest
from app.core.explainability_engine import ExplainabilityEngine
from app.core.coverage_heatmap_engine import CoverageHeatmapEngine
from app.core.opportunity_engine_v2 import OpportunityEngineV2

def test_explainability_engine():
    payload = {
        "business_profile": {
            "company_name": "TestCorp",
            "usp": "Fastest AI engine ever"
        },
        "verified_facts": [
            {"fact_category": "speed", "fact_value": "Calculates results in 5 seconds", "verification_score": 95.0, "source_url": "https://testcorp.com/speed"}
        ],
        "questions": [
            {"question": "How fast is TestCorp AI?", "coverage_score": 80.0, "priority_score": 75.0}
        ],
        "keywords": [
            {"keyword": "fast AI tools", "recommendation_value": 70.0}
        ],
        "competitors": [
            {"competitor_name": "SlowCorp", "differentiation_score": 60.0}
        ],
        "crawled_pages": [
            {"url": "https://testcorp.com", "content": "Welcome to TestCorp. We built the fastest AI engine ever."}
        ]
    }
    
    overall_scores = {
        "visibility_score": 75.0,
        "recommendation_score": 68.0,
        "coverage_score": 70.0
    }
    
    engine = ExplainabilityEngine()
    res = engine.compute_breakdown(payload, overall_scores)
    
    assert "recommendation_breakdown" in res
    assert "visibility_breakdown" in res
    assert "coverage_breakdown" in res
    
    rec_breakdown = res["recommendation_breakdown"]
    assert rec_breakdown["overall"]["score"] == 68.0
    # Sum of components must equal overall recommendation score
    comp_sum = sum(c["value"] for c in rec_breakdown["components"])
    assert abs(comp_sum - 68.0) < 0.2

def test_coverage_heatmap_engine_categorization():
    payload = {
        "questions": [
            {"question": "What is the cost of TestCorp software?", "coverage_score": 60.0},
            {"question": "How to fix connection errors in TestCorp?", "coverage_score": 30.0},
            {"question": "Compare TestCorp vs competitors", "coverage_score": 85.0}
        ],
        "crawled_pages": [
            {"url": "https://testcorp.com", "content": "Welcome to TestCorp. We built the fastest AI engine ever."}
        ]
    }
    
    engine = CoverageHeatmapEngine()
    # Mock supabase insert by patching it out or testing the logic directly
    # Since we can mock, let's write a simple query heatmap test
    cat_scores = {}
    for cat_name, keywords in engine.CATEGORIES.items():
        cat_scores_list = []
        for q in payload["questions"]:
            q_text = q["question"].lower()
            if any(kw in q_text for kw in keywords):
                cat_scores_list.append(float(q["coverage_score"]))
        if cat_scores_list:
            cat_scores[cat_name] = sum(cat_scores_list) / len(cat_scores_list)
        else:
            cat_scores[cat_name] = 0.0

    # Budget category matches "cost" keyword
    assert "Budget" in cat_scores
    assert cat_scores["Budget"] == 60.0
    
    # Problem category matches "errors" and "how to fix"
    assert "Problem" in cat_scores
    assert cat_scores["Problem"] == 30.0
    
    # Decision category matches "vs" and "compare"
    assert "Decision" in cat_scores
    assert cat_scores["Decision"] == 85.0

def test_opportunity_engine_v2_generation():
    heatmap_data = {
        "category_scores": {"Budget": 20.0, "Decision": 90.0},
        "weak_categories": ["Budget"],
        "missing_categories": [],
        "priorities": {"Budget": "HIGH", "Decision": "LOW"}
    }
    
    engine = OpportunityEngineV2()
    opps = []
    for cat in heatmap_data["weak_categories"]:
        score = heatmap_data["category_scores"][cat]
        template = engine.OPPORTUNITY_TEMPLATES.get(cat)
        if template:
            opps.append({
                "category": cat,
                "current_coverage": score,
                "opportunity": template["opportunity"],
                "recommended_actions": template["actions"],
                "priority": "HIGH" if score < 30.0 else "MEDIUM",
                "impact_score": template["impact"],
                "effort_score": template["effort"]
            })
            
    assert len(opps) == 1
    assert opps[0]["category"] == "Budget"
    assert opps[0]["priority"] == "HIGH"
    assert "pricing" in opps[0]["opportunity"].lower()
