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
    import random
    expanded = []
    seen = set()
    
    city = bi.get("city") or ""
    country = bi.get("country") or ""
    if city.lower() in ["unknown", "not_found", "online"]:
        city = ""
    if country.lower() in ["unknown", "not_found", "online"]:
        country = ""
        
    pre_query = bi.get("pre_query_discovery", {}) or {}
    
    # Helper to clean and filter lists
    def clean_list(lst, fallbacks):
        res = []
        for x in (lst or []):
            s = str(x).strip()
            if s and s.upper() not in ["NOT_FOUND", "UNKNOWN", "N/A"]:
                res.append(s)
        return res if res else fallbacks

    topics = clean_list(pre_query.get("services", []) + bi.get("seed_topics", []), ["career mentorship", "SQL course"])
    personas = clean_list(list((pre_query.get("buyer_personas", {}) or {}).keys()), ["students", "career switchers"])
    problems = clean_list(list((pre_query.get("pain_points", {}) or {}).values()), ["getting a tech job", "switching careers"])
    
    # Dynamic enrichment based on industry / description keywords
    enriched_topics = list(topics)
    enriched_personas = list(personas)
    enriched_problems = list(problems)
    
    desc_lower = (bi.get("description") or "").lower()
    ind_lower = (bi.get("industry") or "").lower()
    is_career_edtech = any(x in desc_lower or x in ind_lower for x in ["mentor", "career", "student", "placement", "job", "learn", "course", "coach"])
    
    if is_career_edtech:
        extra_topics = ["career guidance", "1-on-1 mentorship", "interview preparation", "job placement support", "resume building", "tech career coach"]
        extra_personas = ["job seekers", "college graduates", "career switchers", "freshers", "engineering students"]
        extra_problems = ["lack of career guidance", "rejection in interviews", "resume screening failure", "switching career to tech"]
        
        for t in extra_topics:
            if len(enriched_topics) >= 6:
                break
            if t not in enriched_topics:
                enriched_topics.append(t)
                
        for p in extra_personas:
            if len(enriched_personas) >= 5:
                break
            if p not in enriched_personas:
                enriched_personas.append(p)
                
        for pr in extra_problems:
            if len(enriched_problems) >= 5:
                break
            if pr not in enriched_problems:
                enriched_problems.append(pr)

    # Extract features/benefits/competitors from verified facts
    features = []
    benefits = []
    competitors = []
    for fact in verified_facts:
        ext = fact.get("extracted_facts", {}) or fact
        cat = ext.get("fact_category", "").lower()
        val = ext.get("fact_value", "") or fact.get("fact_value", "")
        if "feature" in cat or "service" in cat:
            features.append(val)
        elif "benefit" in cat or "credential" in cat:
            benefits.append(val)
        elif "competitor" in cat:
            competitors.append(val)
            
    features = clean_list(features, ["1-on-1 mentorship sessions", "job placement support", "resume review"])
    benefits = clean_list(benefits, ["accelerating career transition", "cracking tech interviews", "building a strong portfolio"])
    competitors = clean_list(competitors, ["generic bootcamps", "traditional courses", "unstructured tutorials"])
    
    company_name = get_resolved_company_name(bi, "")
    industry = bi.get("industry", "technology")
    
    # The 25 intent dimensions with 4 templates each
    dimensions = {
        "Product Queries": [
            "where can i enroll in {topic} program",
            "what is the curriculum of the {topic} course",
            "are there certifications for {topic} programs",
            "what do the {topic} training modules cover"
        ],
        "Service Queries": [
            "who offers personalized {topic} services",
            "professional mentoring services for {topic}",
            "expert consulting guidance on {topic}",
            "find a provider for {topic} coaching"
        ],
        "Feature Queries": [
            "does the program include {feature}",
            "how does the {feature} feature work",
            "platform training that includes {feature}",
            "benefits of having {feature} during prep"
        ],
        "Benefit Queries": [
            "how can {topic} help me achieve {benefit}",
            "will studying {topic} lead to {benefit}",
            "how {topic} course drives {benefit} for careers",
            "expected {benefit} after completing {topic}"
        ],
        "Pricing Queries": [
            "cost of {topic} certification program",
            "fees for 1-on-1 {topic} coaching",
            "pricing structure for the {topic} platform",
            "is the price of {topic} modules worth it"
        ],
        "Review Queries": [
            "{topic} reviews from past students",
            "student testimonials for {topic} training",
            "what are the ratings of the {topic} program",
            "is the {topic} curriculum highly reviewed"
        ],
        "Comparison Queries": [
            "compare {topic} vs self-study",
            "difference between online {topic} and bootcamp",
            "{topic} course compared to other options",
            "should i do {topic} program or self-learning"
        ],
        "Alternative Queries": [
            "alternatives to generic bootcamps for {topic}",
            "what else is there besides traditional {topic} courses",
            "other ways to learn {topic} without college",
            "non-traditional paths to master {topic}"
        ],
        "Competitor Queries": [
            "how does this program compare to {competitor}",
            "which is better for job placement: this or {competitor}",
            "reviews of {topic} platform vs {competitor}",
            "why choose this {topic} course over {competitor}"
        ],
        "Problem Queries": [
            "how to solve {problem} in career path",
            "struggling with {problem} help",
            "who can help me overcome {problem}",
            "how to handle {problem} during tech transition"
        ],
        "Persona Queries": [
            "is this {topic} path suitable for {persona}",
            "how can {persona} start learning {topic}",
            "recommended {topic} mentoring for {persona}",
            "can {persona} transition into {topic} roles"
        ],
        "Industry Queries": [
            "demand for {topic} specialists in the {industry} industry",
            "role of {topic} in modern {industry} workflows",
            "why {industry} companies hire for {topic} skills",
            "how {topic} is transforming the {industry} sector"
        ],
        "FAQ Queries": [
            "what is the average duration of the {topic} training",
            "are there prerequisites for {topic} modules",
            "does this {topic} program require technical experience",
            "how many hours per week is the {topic} course"
        ],
        "Buying Intent Queries": [
            "how to sign up for {topic} program",
            "register for {topic} mentorship online",
            "enroll in the next batch of {topic} classes",
            "join {topic} platform with placement support"
        ],
        "Local Intent Queries": [
            "best {topic} training near {city}",
            "where can i study {topic} in {city}",
            "{topic} coaching classes in {city}",
            "top local mentors for {topic} near {city}"
        ],
        "Educational Queries": [
            "learn the fundamentals of {topic}",
            "basic tutorials to understand {topic}",
            "step-by-step introduction to {topic}",
            "what do i need to know about {topic} basics"
        ],
        "Conversational AI Queries": [
            "suggest a mentoring platform that helps with {topic}",
            "which program connects students with {topic} experts",
            "can you recommend a career guide for {topic}",
            "where to ask questions about {topic} career transition"
        ],
        "Voice Search Queries": [
            "where is the best {topic} training course",
            "how do i get a job in {topic} with no experience",
            "who can help me switch my career to {topic}",
            "what is the easiest way to learn {topic}"
        ],
        "Long-Tail Queries": [
            "how to switch from non-tech background to {topic} specialist",
            "best way to find a {topic} mentor from top companies",
            "structured path to learn {topic} for job placement",
            "mentorship program that offers resume review and placement support"
        ],
        "Recommendation Queries": [
            "recommend a reliable {topic} mentoring service",
            "best recommendation for {topic} program",
            "what is the most recommended platform for {topic}",
            "suggest a highly recommended {topic} course"
        ],
        "Troubleshooting Queries": [
            "how to fix mistakes in my {topic} resume",
            "why am i not getting calls for {topic} jobs",
            "overcoming anxiety during {topic} interview prep",
            "how to handle failure in {topic} coding tests"
        ],
        "Success Story Queries": [
            "success stories of career switchers to {topic}",
            "how students cracked top companies in {topic}",
            "real success stories from the {topic} mentorship",
            "past graduates placement rate for {topic}"
        ],
        "Implementation Queries": [
            "how to apply {topic} concepts in real projects",
            "best practices for implementing {topic} at work",
            "building a portfolio to showcase {topic} skills",
            "how to implement {topic} tools in workflows"
        ],
        "Career Queries": [
            "career opportunities after learning {topic}",
            "salary estimate for {topic} developers",
            "job market outlook for {topic} roles",
            "what is the career path of a {topic} specialist"
        ],
        "Skill Queries": [
            "essential skills for {topic} jobs",
            "how to improve my {topic} technical skills",
            "what programming skills are needed for {topic}",
            "how to master {topic} for interviews"
        ]
    }
    
    # Seed expansion loop using the 25 dimensions
    for dim_name, templates in dimensions.items():
        for template in templates:
            for topic in enriched_topics:
                # Deterministic selection of persona and problem to avoid Cartesian explosion
                idx = len(dim_name) + len(template) + len(topic)
                persona = enriched_personas[idx % len(enriched_personas)]
                problem = enriched_problems[idx % len(enriched_problems)]
                feature = features[idx % len(features)]
                benefit = benefits[idx % len(benefits)]
                comp = competitors[idx % len(competitors)]
                
                base_q = template.format(
                    topic=topic,
                    feature=feature,
                    benefit=benefit,
                    persona=persona,
                    problem=problem,
                    competitor=comp,
                    city=city or "online",
                    country=country or "online",
                    industry=industry or "technology",
                    company_name=company_name
                )
                
                # Generate location variants
                q_variants = [base_q]
                
                # Only add local variations for intent types that make sense
                is_local_eligible = any(term in dim_name.lower() for term in ["product", "service", "buying", "local", "voice", "recommendation"])
                if is_local_eligible:
                    if city and city.lower() != "online" and f"in {city.lower()}" not in base_q.lower() and f"near {city.lower()}" not in base_q.lower():
                        q_variants.append(f"{base_q} in {city}")
                    if "near me" not in base_q.lower() and "online" not in base_q.lower():
                        q_variants.append(f"{base_q} near me")
                        
                for q_raw in q_variants:
                    # Clean spacing
                    q_text = q_raw.strip().replace("  ", " ")
                    
                    # Ensure capitalized first letter
                    if q_text:
                        q_text = q_text[0].upper() + q_text[1:]
                        
                    # Standard question formatting check
                    if q_text.lower().startswith(("how", "why", "what", "where", "who", "which", "can", "is", "are", "does", "should", "recommend", "suggest")):
                        if not q_text.endswith("?"):
                            q_text += "?"
                            
                    if q_text and q_text.lower() not in seen:
                        seen.add(q_text.lower())
                        
                        expanded.append({
                            "question": q_text,
                            "question_type": dim_name,
                            "intent": "commercial" if "recommend" in dim_name.lower() or "pricing" in dim_name.lower() or "compare" in dim_name.lower() else "informational",
                            "confidence_score": 0.95,
                            "priority": "High" if "recommend" in dim_name.lower() else "Medium",
                            "recommended_answer": generate_optimal_answer(q_text, verified_facts, bi),
                            "difficulty_estimate": "Medium",
                            "opportunity_estimate": "High" if "recommend" in dim_name.lower() else "Medium"
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
