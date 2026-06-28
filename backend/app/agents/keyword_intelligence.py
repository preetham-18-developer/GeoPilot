import json
import logging
import random
import re
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState
from app.core.scoring import compute_keyword_scores

logger = logging.getLogger(__name__)

KEYWORD_SYSTEM_PROMPT = """You extract SEO keywords from business information.
Keywords are short phrases people type into Google.
They are 1-5 words. Natural. Specific. No marketing language.
Return JSON array only. No markdown, no code blocks."""

KEYWORD_USER_PROMPT = """Business: {business_type} in {location}
Services: {services}
Target customers: {customers}

Generate 200 SEO keywords.

Think about what people type when:
1. Searching for this type of service
2. Looking for a course or program like this
3. Trying to solve a specific problem
4. Looking for providers in this location

Format: short, natural phrases people actually type.

BAD keywords (never generate these):
- 'affordable professional mentorship solutions'
- 'comprehensive career development programs'  
- 'world-class SQL training excellence'

GOOD keywords (generate like these):
- 'sql course india'
- 'career mentorship students'
- 'tech job placement help'
- 'weekend programming course'
- '1 on 1 coding mentor'
- 'women tech career program'

Return JSON:
[{{
  "keyword": string,
  "type": "PRIMARY"|"LONGTAIL"|"LOCAL"|"QUESTION"
}}]"""

def clean_content_for_ai(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r'\S+@\S+\.\S+', '', text)
    text = re.sub(r'[\+\d][\d\s\-\(\)]{8,}', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_resolved_company_name(bi: Dict[str, Any], website_url: str) -> str:
    name = (bi or {}).get("company_name", "").strip()
    if not name or name.lower() in ["unknown", "unknown company", "the business", "business"]:
        from urllib.parse import urlparse
        parsed = urlparse(website_url)
        domain = parsed.netloc or parsed.path
        if domain.startswith("www."):
            domain = domain[4:]
        parts = domain.split(".")
        if len(parts) > 1:
            name = parts[-2]
        else:
            name = parts[0]
        
        name = name.replace("-", " ").replace("_", " ")
        if "thelibrarycompany" in name.lower() or "librarycompany" in name.lower():
            name = "The Library Company"
        else:
            name = name.title()
    return name

def extract_keywords_from_questions(questions: List[Dict[str, Any]]) -> List[str]:
    candidates = []
    question_words = {"where", "what", "how", "which", "can", "is", "are", "why", "who", "should", "does", "do", "would"}
    stop_words = {"a", "the", "an", "in", "of", "to", "for", "with", "on", "at", "by", "from", "about"}
    
    for q_item in questions:
        q_text = q_item.get("question", "").lower()
        q_clean = re.sub(r'[^\w\s]', '', q_text)
        words = q_clean.split()
        
        filtered_words = [w for w in words if w not in question_words and w not in stop_words]
        
        n = len(filtered_words)
        for length in range(2, min(5, n + 1)):
            for i in range(n - length + 1):
                phrase = " ".join(filtered_words[i:i+length])
                candidates.append(phrase)
                
    return candidates

class KeywordIntelligenceAgent:
    def __init__(self):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", KEYWORD_SYSTEM_PROMPT),
            ("user", KEYWORD_USER_PROMPT)
        ])

    def discover_keywords(self, verified_facts: List[Dict[str, Any]], business_intelligence: Dict[str, Any] = None, state_questions: List[Dict[str, Any]] = None, website_url: str = "") -> List[Dict[str, Any]]:
        try:
            bi = business_intelligence or {}
            pre_query = bi.get("pre_query_discovery", {}) or {}
            
            def clean_list(lst):
                if not lst:
                    return []
                return [str(x).strip() for x in lst if x and str(x).strip().upper() != "NOT_FOUND"]
                
            services = clean_list(pre_query.get("services", [])) or [bi.get("industry", "industry solutions")]
            personas_dict = pre_query.get("buyer_personas", {}) or {}
            personas = [k for k, v in personas_dict.items() if v and str(v).upper() != "NOT_FOUND"] or ["student", "job seeker"]
            
            formatted_prompt = self.prompt.format_messages(
                business_type=bi.get("industry", bi.get("business_type", "Business")),
                location=f"{bi.get('city', 'online')}, {bi.get('country', 'online')}",
                services=", ".join(services),
                customers=", ".join(personas)
            )
            response = self.llm.invoke(formatted_prompt)
            
            resp_text = response.content.strip()
            if resp_text.startswith("```json"):
                resp_text = resp_text[7:]
            if resp_text.endswith("```"):
                resp_text = resp_text[:-3]
            resp_text = resp_text.strip()
            
            raw_kws = json.loads(resp_text)
            
            mapped_kws = []
            for item in raw_kws:
                mapped = self.map_to_db_format(item, bi)
                mapped_kws.append(mapped)
                
            return mapped_kws
        except Exception as e:
            logger.error(f"Error in V3 Keyword Discovery LLM execution: {e}")
            return []

    def map_to_db_format(self, llm_kw: Dict[str, Any], bi: Dict[str, Any]) -> Dict[str, Any]:
        kw = llm_kw.get("keyword", "").strip()
        kw_type = llm_kw.get("type", "PRIMARY").upper()
        
        db_type = "Primary"
        db_intent = "informational"
        
        if kw_type == "PRIMARY":
            db_type = "Primary"
            db_intent = "commercial"
        elif kw_type == "LONGTAIL":
            db_type = "Long Tail"
            db_intent = "informational"
        elif kw_type == "LOCAL":
            db_type = "Location"
            db_intent = "navigational"
        elif kw_type == "QUESTION":
            db_type = "Voice Search"
            db_intent = "informational"
            
        return {
            "keyword": kw,
            "keyword_type": db_type,
            "intent": db_intent,
            "cluster": bi.get("industry", "General") + " Solutions",
            "confidence_score": 0.95,
            "priority": "Medium",
            "difficulty_estimate": "Medium",
            "opportunity_estimate": "High",
            "source": "Verified Facts"
        }

def run_keyword_intelligence(state: AgentState) -> Dict[str, Any]:
    logger.info("Running V3 Keyword Intelligence Node (Complete Refactor)...")
    agent = KeywordIntelligenceAgent()
    bi = state.get("business_intelligence", {})
    website_url = state.get("website_url", "")
    comp_name = get_resolved_company_name(bi, website_url).lower()
    
    seeds = agent.discover_keywords(
        state.get("verified_facts", []),
        business_intelligence=bi,
        state_questions=state.get("questions", []),
        website_url=website_url
    )
    
    # 1. Extract raw keyword candidates from questions (Step 1)
    extracted_candidates = extract_keywords_from_questions(state.get("questions", []))
    
    # 2. Get locations and core topics
    city = bi.get("city") or ""
    country = bi.get("country") or ""
    if city.lower() in ["unknown", "not_found", "online"]:
        city = ""
    if country.lower() in ["unknown", "not_found", "online"]:
        country = ""
        
    pre_query = bi.get("pre_query_discovery", {}) or {}
    def clean_list(lst):
        if not lst:
            return []
        return [str(x).strip() for x in lst if x and str(x).strip().upper() != "NOT_FOUND"]
    
    services = clean_list(pre_query.get("services", [])) or [bi.get("industry", "industry solutions")]
    topics = clean_list(pre_query.get("industry_topics", [])) or ["optimization", "solutions"]
    
    core_topics = list(set(services + topics + [bi.get("industry", "solutions")]))
    
    # Add seeds to candidates
    seed_texts = [s["keyword"] for s in seeds]
    candidate_list = seed_texts + extracted_candidates
    
    # Step 2: Generate location variants
    location_variants = []
    for topic in core_topics:
        t_clean = topic.strip().lower()
        location_variants.append(t_clean)
        location_variants.append(f"{t_clean} near me")
        if city:
            location_variants.append(f"{t_clean} {city.lower()}")
            location_variants.append(f"{t_clean} in {city.lower()}")
            location_variants.append(f"best {t_clean} {city.lower()}")
            
    # Step 3: Generate intent variants
    intent_variants = []
    for topic in core_topics:
        t_clean = topic.strip().lower()
        intent_variants.extend([
            f"{t_clean} course",
            f"{t_clean} program",
            f"{t_clean} training",
            f"{t_clean} platform",
            f"{t_clean} online",
            f"learn {t_clean}",
            f"{t_clean} for beginners",
            f"{t_clean} with placement"
        ])
        
    all_candidates = candidate_list + location_variants + intent_variants
    
    # Step 4: Apply strict filters
    seen_keywords = set()
    final_expanded = []
    
    # Build list of words present in seed topics to check relevance
    seed_topic_words = set()
    for topic in core_topics:
        for word in topic.lower().split():
            if len(word) > 3:
                seed_topic_words.add(word)
                
    ADJECTIVE_BLACKLIST = {
        'affordable', 'comprehensive', 'professional',
        'excellent', 'outstanding', 'premier', 'leading',
        'top-notch', 'world-class', 'cutting-edge', 'great', 'best'
    }
    
    for kw in all_candidates:
        kw_clean = kw.strip().replace("  ", " ").lower()
        
        # Word count constraint (1-5 words)
        words = kw_clean.split()
        if not (1 <= len(words) <= 5):
            continue
            
        # Check duplicate
        if kw_clean in seen_keywords:
            continue
            
        # Discard company name
        if comp_name in kw_clean or "the library company" in kw_clean or "the library" in kw_clean:
            continue
            
        # Discard URLs/domains
        if "http" in kw_clean or "www." in kw_clean or ".com" in kw_clean:
            continue
            
        # Discard pure adjectives
        if all(w in ADJECTIVE_BLACKLIST for w in words):
            continue
            
        # Discard if doesn't contain a word matching target topics
        if seed_topic_words and not any(w in seed_topic_words for w in words):
            continue
            
        seen_keywords.add(kw_clean)
        
        # Map back to structured object
        # Classify keyword_type dynamically
        kw_type = "Primary"
        kw_intent = "informational"
        
        if "near me" in kw_clean or (city and city.lower() in kw_clean):
            kw_type = "Location"
            kw_intent = "navigational"
        elif "course" in kw_clean or "program" in kw_clean or "training" in kw_clean or "pricing" in kw_clean:
            kw_type = "Commercial"
            kw_intent = "commercial"
        elif len(words) >= 4:
            kw_type = "Long Tail"
            kw_intent = "informational"
            
        final_expanded.append({
            "keyword": kw.title() if len(words) <= 3 else kw[0].upper() + kw[1:] if kw else "",
            "keyword_type": kw_type,
            "intent": kw_intent,
            "cluster": bi.get("industry", "General") + " Solutions",
            "source": "Recommendation Queries" if kw in extracted_candidates else "Verified Facts"
        })
        
    # Scale to 5000+ keywords or ensure substantial list
    # If list is below 5000, we add long tail permutations
    if len(final_expanded) < 5000:
        logger.info(f"Adding semantic permutations to reach target volume (current: {len(final_expanded)})...")
        extra_suffixes = ["for career support", "with placement help", "for students", "for tech jobs", "classes near me"]
        base_list = list(final_expanded)
        
        for kw_item in base_list:
            if len(final_expanded) >= 5050:
                break
            for suffix in extra_suffixes:
                if len(final_expanded) >= 5050:
                    break
                    
                new_kw = f"{kw_item['keyword']} {suffix}"
                new_words = new_kw.split()
                if len(new_words) <= 5 and new_kw.lower() not in seen_keywords:
                    seen_keywords.add(new_kw.lower())
                    final_expanded.append({
                        "keyword": new_kw,
                        "keyword_type": "Long Tail",
                        "intent": "informational",
                        "cluster": kw_item["cluster"],
                        "source": "Recommendation Queries"
                    })

    # Ensure EVERY single keyword is scored deterministically
    final_scored_keywords = []
    crawled_pages = state.get("crawled_pages", [])
    entity_nodes = state.get("entity_nodes", [])
    
    for item in final_expanded:
        scores = compute_keyword_scores(
            item["keyword"],
            item["keyword_type"],
            item["intent"],
            bi,
            crawled_pages,
            entity_nodes
        )
        item.update(scores)
        final_scored_keywords.append(item)
        
    logger.info(f"V3 Keyword Intelligence finished. Scored {len(final_scored_keywords)} diverse keywords.")
    return {"keywords": final_scored_keywords}
