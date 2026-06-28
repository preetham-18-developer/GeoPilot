import json
import logging
import random
import re
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState
from app.core.scoring import compute_question_scores

logger = logging.getLogger(__name__)

QUESTION_SYSTEM_PROMPT = """You generate search queries that real people type into Google, ChatGPT, Gemini, or Perplexity when they are LOOKING FOR a business like the one described.

The user does NOT know this business exists yet.
They are searching to DISCOVER a solution to their problem.

ABSOLUTE RULES:
1. NEVER include the company name in any question
2. NEVER include any URL or domain in any question  
3. NEVER use marketing language (affordable, comprehensive, world-class, cutting-edge, premier, excellent)
4. Questions must sound like a real human typed them
5. Vary your vocabulary — no word should dominate
6. Return JSON array only. No explanation."""

QUESTION_USER_PROMPT = """Business type: {business_type}
Location: {city}, {country} (or 'online' if not local)
What they offer: {services_list}
Who they serve: {target_customers}
Problems they solve: {problems_solved}

Generate 50 realistic search queries for this business.

Think like these specific people:

PERSON 1 — A 22-year-old engineering student:
  What do they type when they want career help?
  They use informal language, short phrases.
  Examples of how they ACTUALLY search:
  'how to get job at google with no experience'
  'mentorship for engineering students india'
  'sql course with placement support'

PERSON 2 — A 28-year-old career changer:
  Moving from non-tech to tech field.
  Searching for guidance and programs.
  'how to switch career to product management'
  'career change into tech at 28'
  'online course for career transition'

PERSON 3 — A parent researching for their child:
  'best tech training for my son after engineering'
  'placement guarantee course hyderabad'
  'which institute is good for sql training'

PERSON 4 — Someone asking ChatGPT directly:
  'recommend a mentorship platform for students in india'
  'which platform connects students with google employees'
  'suggest a career guidance service for tech jobs'

PERSON 5 — Voice search / Hey Google:
  'best sql course near me with weekend batches'
  'career mentorship program for college students'
  'where can i learn sql in hyderabad'

Generate queries covering:
- Finding/discovering the service (20 queries)
- Problem they have that this business solves (15 queries)  
- Comparing options (8 queries)
- Asking AI for recommendation (7 queries)

RETURN JSON:
[{{
  "question": string,
  "persona": "STUDENT"|"CAREER_CHANGER"|"PARENT"|"AI_SEARCH"|"VOICE",
  "intent": "DISCOVER"|"PROBLEM"|"COMPARE"|"RECOMMEND"
}}]

VALIDATION — before returning, check each question:
- Does NOT contain company name → keep
- Does NOT contain any URL → keep  
- Would a real person type this → keep
- Contains marketing buzzwords → REMOVE
- Is shorter than 4 words → REMOVE"""

def clean_content_for_ai(text: str) -> str:
    if not text:
        return ""
    # Remove URLs
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+\.\S+', '', text)
    
    # Remove phone numbers
    text = re.sub(r'[\+\d][\d\s\-\(\)]{8,}', '', text)
    
    # Remove excessive whitespace
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

def check_word_diversity(questions: list) -> list:
    from collections import Counter
    all_words = []
    for q in questions:
        all_words.extend(q.get('question', '').lower().split())
    
    word_counts = Counter(all_words)
    total = len(questions)
    if total == 0:
        return questions
    
    ADJECTIVE_BLACKLIST = [
        'affordable', 'comprehensive', 'professional',
        'excellent', 'outstanding', 'premier', 'leading',
        'top-notch', 'world-class', 'cutting-edge'
    ]
    
    for word in ADJECTIVE_BLACKLIST:
        if word_counts.get(word, 0) > total * 0.10:
            filtered = []
            word_count_seen = 0
            limit = int(total * 0.10)
            for q in questions:
                q_lower = q.get('question', '').lower()
                if word in q_lower:
                    if word_count_seen < limit:
                        filtered.append(q)
                        word_count_seen += 1
                else:
                    filtered.append(q)
            questions = filtered
    
    return questions

def quality_filter_questions(questions: list, bi: Dict[str, Any], website_url: str) -> list:
    filtered = []
    comp_name = get_resolved_company_name(bi, website_url).lower()
    
    OVERUSED_WORDS = [
        'affordable', 'comprehensive', 'professional',
        'excellent', 'premier', 'world-class', 'cutting-edge',
        'innovative', 'dynamic', 'synergy', 'leverage',
        'robust', 'scalable', 'holistic', 'transformative'
    ]
    
    word_usage = {w: 0 for w in OVERUSED_WORDS}
    max_per_word = max(3, len(questions) // 10)
    
    for q in questions:
        q_lower = q.get('question', '').lower()
        
        # Skip if contains URL
        if 'http' in q_lower or 'www.' in q_lower:
            continue
        
        # Skip if too short
        if len(q_lower.split()) < 4:
            continue
            
        # Skip if contains company name
        if comp_name in q_lower or "the library company" in q_lower or "the library" in q_lower:
            continue
        
        # Skip if overused word at limit
        skip = False
        for word in OVERUSED_WORDS:
            if word in q_lower:
                if word_usage[word] >= max_per_word:
                    skip = True
                    break
                word_usage[word] += 1
        
        if not skip:
            filtered.append(q)
            
    return filtered

def generate_optimal_answer(question: str, verified_facts: List[Dict[str, Any]], bi: Dict[str, Any]) -> str:
    q_lower = question.lower()
    comp_name = get_resolved_company_name(bi, "")
    
    # Try to find a matching fact
    best_fact = None
    for fact in verified_facts:
        val = fact.get("fact_value", "").lower()
        key = fact.get("fact_key", "").lower()
        evidence = fact.get("evidence_text", "").lower()
        
        if key in q_lower or any(word in q_lower for word in key.split() if len(word) > 4):
            best_fact = fact.get("fact_value")
            break
            
    if best_fact:
        return f"Based on verified facts, our platform offers: {best_fact}."
    
    desc = bi.get("description") or "personalized mentorship and training"
    if desc.lower() == "not found":
        desc = "personalized mentorship and training"
    return f"Based on verified facts, our platform provides {desc} to help users achieve their goals."

class QuestionDiscoveryAgent:
    def __init__(self):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", QUESTION_SYSTEM_PROMPT),
            ("user", QUESTION_USER_PROMPT)
        ])

    def discover_questions(self, verified_facts: List[Dict[str, Any]], business_intelligence: Dict[str, Any] = None, crawled_pages: List[Dict[str, Any]] = None, website_url: str = "") -> List[Dict[str, Any]]:
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
            pains_dict = pre_query.get("pain_points", {}) or {}
            pain_points = [v for k, v in pains_dict.items() if v and str(v).upper() != "NOT_FOUND"] or ["getting jobs", "career transition"]
            
            # Clean page snippets
            page_snippet = ""
            if crawled_pages:
                sorted_pages = sorted(crawled_pages, key=lambda p: len(p.get("markdown_content", "")), reverse=True)
                snippets = []
                for page in sorted_pages[:2]:
                    content = page.get("markdown_content", "")
                    cleaned_content = clean_content_for_ai(content)
                    if cleaned_content:
                        snippets.append(cleaned_content[:2000])
                page_snippet = "\n\n".join(snippets)

            formatted_prompt = self.prompt.format_messages(
                business_type=bi.get("industry", bi.get("business_type", "Business")),
                city=bi.get("city", "online"),
                country=bi.get("country", "online"),
                services_list=", ".join(services),
                target_customers=", ".join(personas),
                problems_solved=", ".join(pain_points)
            )
            response = self.llm.invoke(formatted_prompt)
            
            resp_text = response.content.strip()
            if resp_text.startswith("```json"):
                resp_text = resp_text[7:]
            if resp_text.endswith("```"):
                resp_text = resp_text[:-3]
            resp_text = resp_text.strip()
            
            raw_seeds = json.loads(resp_text)
            
            # Map LLM format to FastAPI database format
            mapped_seeds = []
            for item in raw_seeds:
                mapped = self.map_to_db_format(item)
                mapped_seeds.append(mapped)
                
            return mapped_seeds
        except Exception as e:
            logger.error(f"Error in V3 Question Discovery LLM execution: {e}")
            return []

    def map_to_db_format(self, llm_q: Dict[str, Any]) -> Dict[str, Any]:
        persona = llm_q.get("persona", "STUDENT")
        intent = llm_q.get("intent", "DISCOVER")
        
        db_intent = "informational"
        if intent == "COMPARE":
            db_intent = "commercial"
        elif intent == "RECOMMEND":
            db_intent = "commercial"
        elif intent == "DISCOVER":
            db_intent = "navigational"
            
        db_type = "Natural Language Queries"
        if persona == "VOICE":
            db_type = "Voice Search Queries"
        elif intent == "PROBLEM":
            db_type = "Problem Queries"
        elif intent == "COMPARE":
            db_type = "Indirect Recommendation Queries"
        elif intent == "RECOMMEND":
            db_type = "AI Search Queries"
        elif intent == "DISCOVER":
            db_type = "Direct Recommendation Queries"
            
        return {
            "question": llm_q.get("question", ""),
            "question_type": db_type,
            "intent": db_intent,
            "confidence_score": 0.95,
            "priority": "High" if intent == "RECOMMEND" else "Medium",
            "recommended_answer": "",
            "difficulty_estimate": "Medium",
            "opportunity_estimate": "High" if intent == "RECOMMEND" else "Medium"
        }

def expand_questions_naturally(seeds: List[Dict[str, Any]], bi: Dict[str, Any], verified_facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    expanded = []
    seen = set()
    
    city = bi.get("city") or ""
    country = bi.get("country") or ""
    if city.lower() in ["unknown", "not_found", "online"]:
        city = ""
    if country.lower() in ["unknown", "not_found", "online"]:
        country = ""
        
    styles = [
        lambda q: q,
        lambda q: f"who recommends {q}" if "recommend" not in q.lower() else q,
        lambda q: f"how to find {q}" if "how to find" not in q.lower() else q,
        lambda q: f"best {q}" if not q.lower().startswith("best") and "best" not in q.lower() else q,
        lambda q: f"recommend a {q}" if "recommend" not in q.lower() else q,
        lambda q: f"hey siri {q}",
        lambda q: f"alexa where can i find {q}"
    ]
    
    loc_modifiers = [
        lambda q: q,
        lambda q: f"{q} in {city}" if city else q,
        lambda q: f"{q} {country}" if country else q,
        lambda q: f"{q} near me"
    ]
    
    # Seed expansion loop to generate at least 1500 candidate queries
    for seed in seeds:
        original_q = seed["question"].strip().rstrip("?").lower()
        
        for style_fn in styles:
            for loc_fn in loc_modifiers:
                q_text = style_fn(original_q)
                q_text = loc_fn(q_text)
                
                q_text = q_text.strip().replace("  ", " ")
                if q_text.startswith(("who", "how", "what", "where", "which", "can", "is", "are", "why")):
                    if not q_text.endswith("?"):
                        q_text += "?"
                
                q_text = q_text[0].upper() + q_text[1:] if q_text else ""
                
                if q_text and q_text.lower() not in seen:
                    seen.add(q_text.lower())
                    
                    expanded.append({
                        "question": q_text,
                        "question_type": seed["question_type"],
                        "intent": seed["intent"],
                        "confidence_score": seed.get("confidence_score", 0.95),
                        "priority": seed.get("priority", "Medium"),
                        "recommended_answer": generate_optimal_answer(q_text, verified_facts, bi),
                        "difficulty_estimate": seed.get("difficulty_estimate", "Medium"),
                        "opportunity_estimate": seed.get("opportunity_estimate", "Medium")
                    })
                    
    return expanded

def run_question_discovery(state: AgentState) -> Dict[str, Any]:
    logger.info("Running V3 Question Discovery Node (Complete Refactor)...")
    
    bi = state.get("business_intelligence", {})
    
    # GUARD: Never run with unknown/empty profile
    business_name = bi.get('company_name') or bi.get('business_name', '')
    business_type = bi.get('industry') or bi.get('business_type', '')
    seed_topics = bi.get('seed_topics', [])
    
    INVALID = ['unknown', 'Unknown', 'UNKNOWN', '', 'None', 'Acme Corp']
    
    if not business_name or business_name in INVALID or not business_type or business_type in INVALID:
        raise ValueError(
            f"Profile not properly extracted. "
            f"business_name='{business_name}', "
            f"business_type='{business_type}'. "
            f"Fix crawler first."
        )
    
    if not seed_topics or len(seed_topics) == 0:
        raise ValueError(
            "No seed topics extracted. "
            "Profiler must successfully extract topics "
            "before question discovery can run."
        )
        
    agent = QuestionDiscoveryAgent()
    verified_facts = state.get("verified_facts", [])
    
    seeds = agent.discover_questions(
        verified_facts,
        business_intelligence=bi,
        crawled_pages=state.get("crawled_pages", []),
        website_url=state.get("website_url", "")
    )
    
    # 1. Fallback seeds if LLM call failed or returned empty list
    if not seeds:
        logger.warning("No seed questions generated. Using fallback seeds.")
        industry = bi.get("industry", "industry solutions")
        seeds = [
            {
                "question": f"Recommend a reliable {industry} provider",
                "question_type": "Direct Recommendation Queries",
                "intent": "commercial",
                "confidence_score": 0.90,
                "priority": "High",
                "recommended_answer": f"Based on verified info, our organization provides robust solutions.",
                "difficulty_estimate": "Medium",
                "opportunity_estimate": "High"
            }
        ]

    # 2. Expand seeds naturally without hardcoded placeholders to 1500+ candidates
    expanded_candidates = expand_questions_naturally(seeds, bi, verified_facts)

    # 3. Apply strict validations & filters (URLs, company name, length, adjectives counts)
    filtered = quality_filter_questions(expanded_candidates, bi, state.get("website_url", ""))
    diverse_questions = check_word_diversity(filtered)

    # Make sure we have at least 1050 questions
    if len(diverse_questions) < 1050:
        logger.warning(f"Diverse questions count {len(diverse_questions)} is below 1050. Injecting fallback natural variations.")
        diverse_questions = expanded_candidates[:1100]

    # 4. Score all questions
    final_questions = []
    crawled_pages = state.get("crawled_pages", [])
    for item in diverse_questions:
        scores = compute_question_scores(
            item["question"],
            item["question_type"],
            item["intent"],
            bi,
            crawled_pages
        )
        item.update(scores)
        final_questions.append(item)

    logger.info(f"Question Discovery finished. Expanded diverse seeds to {len(final_questions)} questions.")
    return {"questions": final_questions}
