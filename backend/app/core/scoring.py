import hashlib
import re
from typing import Dict, Any, List, Tuple

def _deterministic_hash(text: str) -> int:
    """Returns a deterministic integer hash between 0 and 99 for a given text."""
    return int(hashlib.md5(text.lower().encode('utf-8')).hexdigest(), 16) % 100

def _get_overlap_count(text1: str, text2: str) -> int:
    """Returns the count of overlapping words between two strings (case-insensitive, minimum word length 3)."""
    words1 = set(w.lower() for w in re.findall(r'\w+', text1) if len(w) >= 3)
    words2 = set(w.lower() for w in re.findall(r'\w+', text2) if len(w) >= 3)
    return len(words1.intersection(words2))

# =========================================================================
# QUESTIONS SCORING
# =========================================================================
def compute_question_scores(
    question: str,
    question_type: str,
    intent: str,
    business_info: Dict[str, Any],
    crawled_pages: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Computes deterministic scores for questions based on content analysis.
    """
    q_lower = question.lower()
    
    # 1. Commercial Intent Score (0-100)
    commercial_terms = [
        "buy", "price", "pricing", "cost", "quote", "discount", "license", "package", 
        "alternative", "vs", "compare", "comparison", "review", "reviews", "ratings", 
        "best value", "vendor", "provider", "near me", "service", "certified", "solutions"
    ]
    term_matches = sum(1 for term in commercial_terms if term in q_lower)
    
    intent_base = 30
    if intent == "transactional":
        intent_base = 90
    elif intent == "commercial":
        intent_base = 80
    elif intent == "navigational":
        intent_base = 50
    elif intent == "informational":
        intent_base = 35
        
    commercial_score = min(100, intent_base + (term_matches * 5))
    
    # 2. Recommendation Potential (0-100)
    # Check alignment with company USP, name, products, and services
    company_name = business_info.get("company_name", "").lower()
    usp = business_info.get("usp", "").lower()
    pre_query = business_info.get("pre_query_discovery", {})
    products = pre_query.get("products", [])
    services = pre_query.get("services", [])
    
    rec_matches = 0
    if company_name and company_name in q_lower:
        rec_matches += 3
    for p in products:
        if p.lower() in q_lower:
            rec_matches += 2
    for s in services:
        if s.lower() in q_lower:
            rec_matches += 2
    if usp:
        rec_matches += _get_overlap_count(question, usp)
        
    recommendation_score = min(100, 45 + (rec_matches * 10))
    
    # 3. Natural Language Quality (0-100)
    # Penalize non-sentence traits: missing capitalization, bad length, lack of punctuation, duplicate spaces
    nlq_score = 100
    if len(question) > 0 and not question[0].isupper():
        nlq_score -= 10
    if not question.endswith("?"):
        nlq_score -= 10
    words = question.split()
    if len(words) < 4:
        nlq_score -= 20
    elif len(words) > 25:
        nlq_score -= 15
    if "  " in question:
        nlq_score -= 10
    nlq_score = max(30, nlq_score)
    
    # 4. Coverage Score (0-100)
    # How well does client content cover the terms in the question?
    coverage_matches = 0
    for page in crawled_pages:
        title = page.get("title", "") or ""
        meta = page.get("meta_description", "") or ""
        content = page.get("content", "") or ""
        
        # Word overlap count with page title & content
        overlap_title = _get_overlap_count(question, title)
        overlap_content = _get_overlap_count(question, content[:1000])
        
        if overlap_title >= 2:
            coverage_matches += 15
        elif overlap_content >= 3:
            coverage_matches += 5
            
    coverage_score = min(100, coverage_matches)
    
    # 5. Business Alignment (0-100)
    # Overlap with target audience description
    target_audience = business_info.get("target_audience", "").lower()
    alignment_overlap = _get_overlap_count(question, target_audience)
    business_alignment = min(100, 40 + (alignment_overlap * 12))
    
    # 6. Priority Score (0-100)
    # Weighted average of commercial, recommendation, alignment, and quality
    priority_score = int(
        (0.35 * commercial_score) + 
        (0.25 * recommendation_score) + 
        (0.20 * business_alignment) + 
        (0.20 * nlq_score)
    )
    
    # Map to priority levels
    priority_val = "High" if priority_score >= 75 else "Medium" if priority_score >= 50 else "Low"
    diff_val = "Hard" if recommendation_score >= 75 else "Medium" if recommendation_score >= 50 else "Easy"
    opp_val = "High" if priority_score >= 70 else "Medium" if priority_score >= 45 else "Low"
    
    # Deterministic confidence score (0.85 to 1.0)
    hash_val = _deterministic_hash(question)
    confidence_score = round(0.85 + (hash_val * 0.0015), 2)
    
    return {
        "commercial_score": float(commercial_score),
        "recommendation_score": float(recommendation_score),
        "intent_score": float(nlq_score), # Maps to natural language quality / intent score
        "coverage_score": float(coverage_score),
        "business_alignment": float(business_alignment),
        "priority_score": float(priority_score),
        "priority": priority_val,
        "difficulty_estimate": diff_val,
        "opportunity_estimate": opp_val,
        "confidence_score": confidence_score
    }

# =========================================================================
# KEYWORDS SCORING
# =========================================================================
def compute_keyword_scores(
    keyword: str,
    keyword_type: str,
    intent: str,
    business_info: Dict[str, Any],
    crawled_pages: List[Dict[str, Any]],
    entity_nodes: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Computes deterministic scores for keywords based on content analysis.
    """
    kw_lower = keyword.lower()
    words = kw_lower.split()
    
    # 1. Difficulty Estimate (0-100)
    # Shorter keywords are harder, commercial intent is harder
    word_count = len(words)
    base_diff = max(10, 100 - (word_count * 12))
    
    if intent in ["commercial", "transactional"]:
        base_diff = min(100, base_diff + 15)
    elif intent == "navigational":
        base_diff = min(100, base_diff + 5)
    
    difficulty_score = base_diff
    diff_val = "Hard" if difficulty_score >= 70 else "Medium" if difficulty_score >= 40 else "Easy"
    
    # 2. Commercial Intent (0-100)
    commercial_suffixes = [
        "solutions", "platforms", "services", "tools", "agencies", "firms", "consultants", 
        "features", "benefits", "cost", "pricing", "reviews", "ratings", "alternatives",
        "near me", "usa", "online", "system", "software", "applications", "integration", 
        "setup", "guide", "tutorial", "case study", "best practices", "compliance"
    ]
    suffix_matches = sum(1 for suffix in commercial_suffixes if suffix in kw_lower)
    
    intent_base = 30
    if intent == "transactional":
        intent_base = 90
    elif intent == "commercial":
        intent_base = 80
        
    commercial_intent = min(100, intent_base + (suffix_matches * 8))
    
    # 3. Opportunity Estimate
    opp_score = commercial_intent * (1.0 - (difficulty_score / 150.0))
    opp_val = "High" if opp_score >= 60 else "Medium" if opp_score >= 35 else "Low"
    
    # 4. Coverage Score (0-100)
    # Search for verbatim occurrences in page contents/titles
    page_hits = 0
    for page in crawled_pages:
        title = (page.get("title", "") or "").lower()
        content = (page.get("content", "") or "").lower()
        if kw_lower in title:
            page_hits += 25
        elif kw_lower in content[:2000]:
            page_hits += 8
            
    coverage_score = min(100, page_hits)
    
    # 5. Entity Relevance (0-100)
    # Check if keyword contains names from entity graph
    entity_matches = 0
    company_name = business_info.get("company_name", "").lower()
    if company_name and company_name in kw_lower:
        entity_matches += 3
        
    for node in entity_nodes:
        entity_name = (node.get("entity_name", "") or "").lower()
        if entity_name and entity_name in kw_lower:
            entity_matches += 1
            
    entity_relevance = min(100, 30 + (entity_matches * 15))
    
    # 6. Recommendation Value (0-100)
    recommendation_value = int((0.40 * commercial_intent) + (0.40 * entity_relevance) + (0.20 * (100 - difficulty_score)))
    priority_val = "High" if recommendation_value >= 75 else "Medium" if recommendation_value >= 50 else "Low"
    
    # Deterministic confidence score (0.80 to 1.0)
    hash_val = _deterministic_hash(keyword)
    confidence_score = round(0.80 + (hash_val * 0.002), 2)
    
    return {
        "difficulty_estimate": diff_val,
        "commercial_intent": float(commercial_intent),
        "opportunity_estimate": opp_val,
        "coverage_score": float(coverage_score),
        "entity_relevance": float(entity_relevance),
        "recommendation_value": float(recommendation_value),
        "confidence_score": confidence_score,
        "priority": priority_val
    }

# =========================================================================
# COMPETITORS SCORING
# =========================================================================
def compute_competitor_scores(
    competitor: Dict[str, Any],
    feature_matrix: Dict[str, Any],
    business_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes deterministic metrics for competitors.
    """
    comp_name = competitor.get("competitor_name", "")
    comp_type = competitor.get("competitor_type", "direct")
    
    # 1. Similarity Score based on feature matrix overlaps
    matching_features = 0
    total_features = 0
    
    features = feature_matrix.get("features", [])
    for f in features:
        feature_name = f.get("feature_name", "")
        client_val = f.get("client_value", "No")
        comp_values = f.get("competitor_values", {})
        comp_val = comp_values.get(comp_name, "No")
        
        total_features += 1
        if client_val == comp_val:
            matching_features += 1
            
    if total_features > 0:
        base_sim = (matching_features / total_features) * 100
    else:
        # Default fallback
        base_sim = 60.0
        
    if comp_type == "direct":
        base_sim = min(100.0, base_sim + 10)
    else:
        base_sim = max(10.0, base_sim - 15)
        
    similarity_score = int(base_sim)
    
    # 2. Audience Match (score and deterministic text)
    # Check word overlaps between client target audience and competitor's description/type
    client_audience = business_info.get("target_audience", "").lower()
    comp_desc = competitor.get("description", "").lower()
    audience_overlap = _get_overlap_count(client_audience, comp_desc)
    
    audience_score = min(100, 40 + (audience_overlap * 15))
    if comp_type == "direct":
        audience_score = min(100, audience_score + 10)
        
    audience_match_text = f"High audience overlap ({audience_score}%) - targets similar customer segments." if audience_score >= 70 else \
                          f"Moderate audience overlap ({audience_score}%) - overlapping industry niches." if audience_score >= 45 else \
                          f"Low audience overlap ({audience_score}%) - distinct market demographic focus."
                          
    # 3. Service Match
    # Percent of 'Yes' features shared in matrix
    yes_shared = 0
    client_yes = 0
    for f in features:
        client_val = f.get("client_value", "No")
        comp_values = f.get("competitor_values", {})
        comp_val = comp_values.get(comp_name, "No")
        
        if client_val == "Yes":
            client_yes += 1
            if comp_val == "Yes":
                yes_shared += 1
                
    if client_yes > 0:
        service_score = int((yes_shared / client_yes) * 100)
    else:
        service_score = 50
        
    service_match_text = f"Strong service parity ({service_score}%) - competes directly on core functionality." if service_score >= 75 else \
                         f"Moderate service alignment ({service_score}%) - shares core product areas with extensions." if service_score >= 40 else \
                         f"Alternative service structure ({service_score}%) - different delivery mechanisms."
                         
    # 4. Industry Match
    client_industry = business_info.get("industry", "").lower()
    industry_match_score = min(100, 50 + (_get_overlap_count(client_industry, comp_desc) * 20))
    industry_match_text = f"Perfect industry category fit ({industry_match_score}%) within {business_info.get('industry', 'Unknown')}." if industry_match_score >= 80 else \
                          f"Aligned industry category fit ({industry_match_score}%) within related verticals." if industry_match_score >= 50 else \
                          f"Adjacent industry vertical ({industry_match_score}%) with partial overlap."
                          
    # 5. Differentiation Score
    # Based on client-unique features and competitor weaknesses vs strengths count
    client_uniq = len(feature_matrix.get("unique_competitor_features", []))
    client_missing = len(feature_matrix.get("missing_client_features", []))
    strengths_count = len(competitor.get("strengths", []))
    weaknesses_count = len(competitor.get("weaknesses", []))
    
    diff_score = 50 + (client_uniq * 8) - (client_missing * 6) + (weaknesses_count * 5) - (strengths_count * 3)
    differentiation_score = max(0, min(100, int(diff_score)))
    
    # Confidence score (0.80 to 1.0) deterministically
    hash_val = _deterministic_hash(comp_name)
    confidence_score = round(0.80 + (hash_val * 0.002), 2)
    
    return {
        "similarity_score": similarity_score,
        "audience_match": audience_match_text,
        "service_match": service_match_text,
        "industry_match": industry_match_text,
        "differentiation_score": differentiation_score,
        "confidence_score": confidence_score
    }

# =========================================================================
# VISIBILITY SCORING
# =========================================================================
def compute_visibility_scores(
    raw_scores: Dict[str, Any],
    crawled_pages: List[Dict[str, Any]],
    verified_facts: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
    keywords: List[Dict[str, Any]],
    business_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes deterministic AI Visibility Scores based on audited facts and content metrics.
    """
    # 1. Content Coverage (0-100)
    page_count = len(crawled_pages)
    content_coverage = min(100, page_count * 6) # E.g., 17 pages covers it
    
    # 2. Question Coverage (0-100)
    # Percent of questions with coverage_score >= 50
    if questions:
        covered_qs = sum(1 for q in questions if q.get("coverage_score", 0.0) >= 50.0)
        question_coverage = int((covered_qs / len(questions)) * 100)
    else:
        question_coverage = 30
        
    # 3. Keyword Coverage (0-100)
    # Percent of keywords with coverage_score >= 50
    if keywords:
        covered_kws = sum(1 for k in keywords if k.get("coverage_score", 0.0) >= 50.0)
        keyword_coverage = int((covered_kws / len(keywords)) * 100)
    else:
        keyword_coverage = 30
        
    # 4. Trust Signals (0-100)
    trust_terms = ["certif", "award", "reviews", "partners", "security", "founded", "policy", "privacy", "secure", "trust"]
    trust_count = 0
    facts_str = " ".join(f.get("fact_value", "") for f in verified_facts).lower()
    for term in trust_terms:
        if term in facts_str:
            trust_count += 1
    trust_signals = min(100, 30 + (trust_count * 15))
    
    # 5. Authority Signals (0-100)
    authority_terms = ["leader", "expert", "experience", "years", "founded", "about us", "team", "white paper", "case study"]
    auth_count = 0
    for term in authority_terms:
        if term in facts_str:
            auth_count += 1
    authority_signals = min(100, 35 + (auth_count * 12))
    
    # 6. Structured Data (0-100)
    # Check if schema/JSON-LD mentions are in pages
    schema_present = False
    for p in crawled_pages:
        html = (p.get("content", "") or "").lower()
        if "ld+json" in html or "schema.org" in html:
            schema_present = True
            break
    structured_data = 95 if schema_present else 30
    
    # 7. FAQ Coverage (0-100)
    faq_present = any("faq" in (p.get("url", "") or "").lower() for p in crawled_pages)
    faq_coverage = 90 if faq_present else 40
    
    # 8. Knowledge Base Coverage
    kb_present = any(any(term in (p.get("url", "") or "").lower() for term in ["guide", "kb", "knowledge", "blog"]) for p in crawled_pages)
    kb_coverage = 85 if kb_present else 45
    
    # 9. Consistency
    consistency = 85 if len(verified_facts) >= 5 else 60
    
    # Calculate Overall Score (Average of all sub_scores)
    sub_scores = {
        "content_coverage": content_coverage,
        "question_coverage": question_coverage,
        "keyword_coverage": keyword_coverage,
        "trust_signals": trust_signals,
        "authority_signals": authority_signals,
        "structured_data": structured_data,
        "faq_coverage": faq_coverage,
        "knowledge_base_coverage": kb_coverage,
        "consistency": consistency
    }
    
    overall_score = round(sum(sub_scores.values()) / len(sub_scores), 1)
    
    return {
        "overall_score": overall_score,
        "sub_scores": sub_scores,
        "recommendations": raw_scores.get("recommendations", [
            "Implement structured JSON-LD schema markup on key landing pages",
            "Build an FAQ section to capture conversational voice queries"
        ])
    }
