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

QUESTION_SYSTEM_PROMPT = """You generate realistic search queries.
Real people type these into Google, ChatGPT, Gemini.
Questions must sound completely natural and human.
NEVER use fill-in-the-blank templates.
Think like a real person with a real problem.
Return JSON array only."""

QUESTION_USER_PROMPT = """Business: {services}
Location: India

For this specific topic: {topic}

Think: who would search for this topic?
What problem do they have?
How would they actually type it into Google or ChatGPT?

Generate 30 natural questions.

EXAMPLE of good questions for 'sql weekend batch':
- 'sql course with weekend classes hyderabad'
- 'where can i learn sql on saturdays and sundays'
- 'best sql training that fits working schedule'
- 'sql weekend batch near me with placement'
- 'which institute has sql classes on weekends'
- 'i work on weekdays can i still learn sql'
- 'sql course for working professionals weekend'
- 'recommend sql training weekend batch india'

Notice:
- Short and natural
- No company name
- No template patterns
- Sounds like a real person typed it
- Specific to the topic

Generate 30 questions like these for: {topic}

Return JSON:
[{{"question": string, "category": string}}]

Categories to use:
DIRECT, PROBLEM, COMPARISON, VOICE, AI_RECOMMENDATION"""

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
                
            services = clean_list(pre_query.get("services", [])) or [bi.get("industry", "Career mentorship platform")]
            seed_topics = bi.get("seed_topics", [])
            if not seed_topics:
                seed_topics = ["career mentorship", "SQL course", "job placement"]
            
            all_questions = []
            
            from concurrent.futures import ThreadPoolExecutor
            
            def run_for_topic(topic):
                try:
                    formatted_prompt = self.prompt.format_messages(
                        services=", ".join(services),
                        topic=topic
                    )
                    response = self.llm.invoke(formatted_prompt)
                    resp_text = response.content.strip()
                    if resp_text.startswith("```json"):
                        resp_text = resp_text[7:]
                    if resp_text.endswith("```"):
                        resp_text = resp_text[:-3]
                    resp_text = resp_text.strip()
                    
                    try:
                        raw_qs = json.loads(resp_text)
                    except Exception:
                        # Fallback parsing in case JSON is slightly malformed
                        # Find the first [ and last ]
                        start_idx = resp_text.find('[')
                        end_idx = resp_text.rfind(']')
                        if start_idx != -1 and end_idx != -1:
                            raw_qs = json.loads(resp_text[start_idx:end_idx+1])
                        else:
                            raise
                            
                    topic_qs = []
                    for item in raw_qs:
                        mapped = self.map_category_to_db(item, bi, verified_facts)
                        if mapped:
                            topic_qs.append(mapped)
                    return topic_qs
                except Exception as ex:
                    logger.error(f"Error generating questions for topic '{topic}': {ex}")
                    raise ex

            with ThreadPoolExecutor(max_workers=5) as executor:
                results = executor.map(run_for_topic, seed_topics)
                
            for res in results:
                all_questions.extend(res)
                
            return all_questions
        except Exception as e:
            logger.error(f"Error in V3 Question Discovery LLM execution: {e}")
            raise e

    def map_category_to_db(self, llm_q: Dict[str, Any], bi: Dict[str, Any], verified_facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        question = llm_q.get("question", "").strip()
        if not question:
            return None
            
        category = str(llm_q.get("category", "DIRECT")).upper()
        
        db_intent = "informational"
        if category in ["COMPARISON", "AI_RECOMMENDATION"]:
            db_intent = "commercial"
        elif category == "DIRECT":
            db_intent = "navigational"
            
        db_type = "Natural Language Queries"
        if category == "VOICE":
            db_type = "Voice Search Queries"
        elif category == "PROBLEM":
            db_type = "Problem Queries"
        elif category == "COMPARISON":
            db_type = "Indirect Recommendation Queries"
        elif category == "AI_RECOMMENDATION":
            db_type = "AI Search Queries"
        elif category == "DIRECT":
            db_type = "Direct Recommendation Queries"
            
        return {
            "question": question,
            "question_type": db_type,
            "intent": db_intent,
            "confidence_score": 0.95,
            "priority": "High" if category == "AI_RECOMMENDATION" else "Medium",
            "recommended_answer": generate_optimal_answer(question, verified_facts, bi),
            "difficulty_estimate": "Medium",
            "opportunity_estimate": "High" if category == "AI_RECOMMENDATION" else "Medium"
        }

def expand_questions_with_ai(
    seeds: List[Dict[str, Any]],
    bi: Dict[str, Any],
    verified_facts: List[Dict[str, Any]],
    llm
) -> List[Dict[str, Any]]:
    
    pre_query = bi.get("pre_query_discovery", {}) or {}
    seed_topics = bi.get("seed_topics", [])
    
    def clean_list(lst, fallbacks):
        res = []
        for x in (lst or []):
            s = str(x).strip()
            if s and s.upper() not in ["NOT_FOUND","UNKNOWN","N/A",""]:
                res.append(s)
        return res if res else fallbacks
    
    raw_topics = clean_list(
        seed_topics,
        ["career mentorship", "sql training", "job placement support"]
    )
    
    REJECT_WORDS = {
        'passion', 'helping', 'companies', 'careers', 'students', 'platform',
        'solutions', 'services', 'learning', 'growth', 'support', 'guidance',
        'quality', 'optimization', 'business optimization', 'digital transformation',
        'operational efficiency', 'professional consulting', 'industry standards'
    }

    def is_generic(topic: str) -> bool:
        t = topic.lower().strip().rstrip('.')
        if t in REJECT_WORDS:
            return True
        return any(bad in t for bad in ('optimization', 'solution', 'platform'))

    seed_topics_cleaned = [str(t).strip().rstrip('.') for t in raw_topics]
    topics = [t for t in seed_topics_cleaned if len(t.split()) >= 2 and not is_generic(t)]
    
    FALLBACK_TOPICS = [
        "career mentorship program", 
        "sql training placement",
        "tech career guidance"
    ]
    
    if not topics:
        topics = FALLBACK_TOPICS
        logger.warning(f"[TOPIC-SOURCE] Using FALLBACK topics — profiler returned nothing usable.")
    else:
        logger.info(f"[TOPIC-SOURCE] Using REAL seed topics: {topics}")
    
    city = bi.get("city", "")
    if city.lower() in ["unknown", "not_found", "online", ""]:
        city = ""
    country = bi.get("country", "India")
    business_type = bi.get("industry", "education platform")
    
    all_questions = list(seeds)
    seen = set(q.get("question","").lower() for q in seeds)
    
    # Process 1 topic at a time, requesting 15 questions per topic to avoid API timeout/chokes
    for idx, topic in enumerate(topics):
        system_prompt = """You generate realistic search queries 
real people type into Google, ChatGPT, Gemini, or Perplexity.

ABSOLUTE RULES:
1. Never include company name
2. Never include URLs or domains  
3. No marketing language whatsoever
4. Must sound like a real human typed it naturally
5. Short informal phrases are better than long formal ones
6. Return valid JSON array only. No explanation."""

        location_str = f"{city}, {country}" if city else country
        
        user_prompt = f"""Business type: {business_type}
Location: {location_str}

Generate 15 natural search questions for this topic:
- {topic}

Generate as these 3 real people:

PERSON 1 — College student (5 questions):
Short, informal, uses slang occasionally.
Examples:
"sql course with weekend batches hyderabad"
"best 1 on 1 mentor for product management"

PERSON 2 — Career changer 28-35 years (5 questions):
Worried about transition, practical minded.
Examples:  
"how to switch career to tech at 30"
"career change into data analyst india"

PERSON 3 — Someone asking ChatGPT/Voice search (5 questions):
Direct/spoken recommendation request.
Examples:
"recommend mentorship platform for freshers india"
"best sql course near me with placement"

STRICT RULES FOR EVERY QUESTION:
- Must reference the topic above
- Must be different from all other questions
- 3-12 words only
- No company names
- No template patterns like "Best recommendation for X program"

Return JSON:
[{{
  "question": "natural question text here",
  "question_type": "Student Queries|Career Queries|AI Search Queries|Voice Search Queries",
  "intent": "informational|commercial"
}}]"""

        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            logger.info(f"[AI-CALL-RAW] batch={idx}, prompt_topics=[{topic!r}]")
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            logger.info(f"[AI-CALL-RAW] raw_response={response.content[:2000]}")
            
            resp_text = response.content.strip()
            resp_text = re.sub(r'```json\s*', '', resp_text)
            resp_text = re.sub(r'```\s*', '', resp_text)
            resp_text = resp_text.strip()
            
            start = resp_text.find('[')
            end = resp_text.rfind(']') + 1
            if start != -1 and end > start:
                resp_text = resp_text[start:end]
            
            batch_qs = json.loads(resp_text)
            
            for q in batch_qs:
                q_text = q.get("question", "").strip()
                if not q_text or len(q_text.split()) < 3:
                    continue
                if q_text.lower() in seen:
                    continue
                if q_text.lower() in REJECT_WORDS:
                    continue
                seen.add(q_text.lower())
                all_questions.append({
                    "question": q_text,
                    "question_type": q.get(
                        "question_type", 
                        "Natural Language Queries"
                    ),
                    "intent": q.get("intent", "informational"),
                    "confidence_score": 0.90,
                    "priority": "High" if any(
                        w in q_text.lower() 
                        for w in ["recommend","suggest","best","which"]
                    ) else "Medium",
                    "recommended_answer": "",
                    "difficulty_estimate": "Medium",
                    "opportunity_estimate": "Medium"
                })
                
        except Exception as e:
            logger.error(f"Batch {idx+1} failed: {e}", exc_info=True)
            raise
    
    logger.info(f"AI expansion: {len(all_questions)} questions")
    return all_questions

from collections import Counter

def detect_templating(rows: List[str], threshold: float = 0.35) -> bool:
    """Returns True if templating/padding is detected."""
    if len(rows) < 15:
        return False
    bigrams = Counter()
    IGNORE_BIGRAMS = {
        ('how', 'to'),
        ('near', 'me'),
        ('in', 'india'),
        ('to', 'find'),
        ('way', 'to'),
        ('is', 'best'),
        ('best', 'for'),
        ('best', 'way')
    }
    for r in rows:
        words = str(r).lower().split()
        for bg in zip(words, words[1:]):
            if bg not in IGNORE_BIGRAMS:
                bigrams[bg] += 1
    if not bigrams:
        return False
    top_bigram, count = bigrams.most_common(1)[0]
    ratio = count / len(rows)
    if ratio > threshold:
        logger.error(f"[GARBAGE-DETECTED] '{top_bigram}' appears in {ratio:.0%} of rows. "
                      f"This smells like template padding, not AI generation. Blocking save.")
        return True
    return False

def run_question_discovery(state: AgentState) -> Dict[str, Any]:
    logger.info("Running V3 Question Discovery Node (Complete Refactor)...")
    
    bi = state.get("business_intelligence", {})
    
    # GUARD: Never run with unknown/empty profile
    business_name = bi.get('company_name') or bi.get('business_name', '')
    business_type = bi.get('industry') or bi.get('business_type', '')
    seed_topics = bi.get('seed_topics', [])
    if not seed_topics:
        seed_topics = bi.get('pre_query_discovery', {}).get('industry_topics', []) or []
    
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
        logger.error(
            "NVIDIA returned 0 seed questions. "
            "Check API key. Cannot continue without seeds."
        )
        raise ValueError(
            "Question generator returned 0 questions. "
            "NVIDIA API call failed silently."
        )

    # 2. Expand seeds naturally without hardcoded placeholders to 1500+ candidates
    from langchain_core.messages import SystemMessage, HumanMessage
    agent2 = QuestionDiscoveryAgent()
    expanded_candidates = expand_questions_with_ai(
        seeds, bi, verified_facts, agent2.llm
    )

    # 3. Apply strict validations & filters (URLs, company name, length, adjectives counts)
    filtered = quality_filter_questions(expanded_candidates, bi, state.get("website_url", ""))
    diverse_questions = check_word_diversity(filtered)

    logger.info(
        f"Final question count: {len(diverse_questions)}"
    )

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

    if detect_templating([q["question"] for q in final_questions]):
        raise ValueError("Templating detected in output — refusing to save garbage CSV.")

    logger.info(f"Question Discovery finished. Expanded diverse seeds to {len(final_questions)} questions.")
    return {"questions": final_questions}
