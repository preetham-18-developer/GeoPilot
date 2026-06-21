import json
import logging
import random
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState
from app.core.scoring import compute_keyword_scores

logger = logging.getLogger(__name__)

KEYWORD_PROMPT = """You are a highly analytical V3 Keyword Intelligence Agent.
Your mission is to generate a comprehensive semantic keyword list for this business.
Keywords must NEVER be generated independently. They must originate strictly from the recommendation queries, verified business facts, pain points, desired outcomes, industry topics, or competitor gaps.

Company: {company_name}
Industry: {industry}
Description: {description}
Website: {website_url}

Verified Business Facts:
{verified_facts_json}

Pre-Query Discovery Metadata:
{pre_query_discovery_json}

Sample Recommendation Queries:
{questions_snippet}

Please generate at least 50 high-quality seed keywords and key phrases.
Categorize and score each keyword/phrase into:
- keyword: The keyword text.
- keyword_type: Must be exactly one of: 'Primary', 'Commercial', 'Problem', 'Outcome', 'Topic', 'Industry', 'Entity', 'Location', 'Role', 'Voice Search', 'AI Search', 'Long Tail', 'Semantic', 'Authority', 'Trend', 'Opportunity'.
- intent: Must be exactly one of: 'informational', 'navigational', 'commercial', 'transactional'.
- cluster: A descriptive theme cluster name (e.g., 'Canvas LMS Setup', 'Career Coaching Programs', 'Physics Simulations').
- confidence_score: A float between 0.0 and 1.0 representing keyword relevance.
- priority: Must be exactly one of: 'High', 'Medium', 'Low'.
- difficulty_estimate: Must be exactly one of: 'Easy', 'Medium', 'Hard'.
- opportunity_estimate: Must be exactly one of: 'High', 'Medium', 'Low'.
- source: Must be exactly one of: 'Recommendation Queries', 'Verified Facts', 'Knowledge Graph', 'Pain Points', 'Outcomes', 'Industry Topics', 'Authority Sources', 'Competitor Topics'.

Strict Quality & No-Hallucination Rules:
- Keywords must directly connect to the real products, services, and locations of this business. If data is unavailable, return NOT_FOUND.
- Do NOT generate shallow permutations or keyword stuffed text.

Format your response as a valid JSON array of objects. Do not wrap it in markdown code blocks. Format:
[
  {{
    "keyword": "LTI physics virtual labs",
    "keyword_type": "Primary",
    "intent": "commercial",
    "cluster": "LMS Simulations",
    "confidence_score": 0.95,
    "priority": "High",
    "difficulty_estimate": "Medium",
    "opportunity_estimate": "High",
    "source": "Verified Facts"
  }}
]
"""

class KeywordIntelligenceAgent:
    def __init__(self):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_template(KEYWORD_PROMPT)

    def discover_keywords(self, verified_facts: List[Dict[str, Any]], business_intelligence: Dict[str, Any] = None, state_questions: List[Dict[str, Any]] = None, website_url: str = "") -> List[Dict[str, Any]]:
        """Generates V3 seed keywords based on discovery metadata, queries, and facts."""
        try:
            facts_str = json.dumps(verified_facts, indent=2) if verified_facts else "[]"
            bi = business_intelligence or {}
            pre_query = bi.get("pre_query_discovery", {})
            pre_query_str = json.dumps(pre_query, indent=2) if pre_query else "{}"
            
            # Use top 10 questions for snippet context
            q_snippet = ""
            if state_questions:
                q_texts = [q.get("question", "") for q in state_questions[:10] if q.get("question")]
                q_snippet = "\n".join(q_texts)
            
            formatted_prompt = self.prompt.format_messages(
                company_name=bi.get("company_name", "Unknown Company"),
                industry=bi.get("industry", "Unknown Industry"),
                description=bi.get("description", "NOT FOUND"),
                website_url=website_url,
                verified_facts_json=facts_str[:4000],
                pre_query_discovery_json=pre_query_str[:4000],
                questions_snippet=q_snippet[:2000] or "Not available."
            )
            response = self.llm.invoke(formatted_prompt)
            
            resp_text = response.content.strip()
            if resp_text.startswith("```json"):
                resp_text = resp_text[7:]
            if resp_text.endswith("```"):
                resp_text = resp_text[:-3]
            resp_text = resp_text.strip()
            
            return json.loads(resp_text)
        except Exception as e:
            logger.error(f"Error in V3 Keyword Discovery LLM execution: {e}")
            return []

def run_keyword_intelligence(state: AgentState) -> Dict[str, Any]:
    """Node function that executes keyword intelligence discovery and expands it to 5000+ scored keywords."""
    logger.info("Running V3 Keyword Intelligence Node...")
    agent = KeywordIntelligenceAgent()
    bi = state.get("business_intelligence", {})
    
    seeds = agent.discover_keywords(
        state.get("verified_facts", []),
        business_intelligence=bi,
        state_questions=state.get("questions", []),
        website_url=state.get("website_url", "")
    )
    
    # 1. Fallback seeds if LLM call failed or returned empty list
    if not seeds:
        logger.warning("No seed keywords generated. Using fallback seeds.")
        comp_name = bi.get("company_name", "the business")
        industry = bi.get("industry", "industry solutions")
        seeds = [
            {
                "keyword": f"{comp_name} {industry}",
                "keyword_type": "Primary",
                "intent": "commercial",
                "cluster": "General",
                "confidence_score": 0.90,
                "priority": "High",
                "difficulty_estimate": "Medium",
                "opportunity_estimate": "High",
                "source": "Verified Facts"
            }
        ]

    expanded_keywords = []
    seen_keywords = set()
    
    # 2. Add seeds first
    for seed in seeds:
        kw_text = seed.get("keyword", "").strip()
        if kw_text and kw_text.lower() not in seen_keywords:
            seen_keywords.add(kw_text.lower())
            expanded_keywords.append(seed)
            
    # 3. Pull V3 pre-query discovery entities and terms
    pre_query = bi.get("pre_query_discovery", {}) or {}
    
    # Helper to clean lists of potential NOT_FOUND strings
    def clean_list(lst):
        if not lst:
            return []
        return [str(x).strip() for x in lst if x and str(x).strip().upper() != "NOT_FOUND"]

    products = clean_list(pre_query.get("products", [])) or [bi.get("company_name", "the business")]
    services = clean_list(pre_query.get("services", [])) or [bi.get("industry", "industry solutions")]
    topics = clean_list(pre_query.get("industry_topics", [])) or ["optimization", "solutions"]
    technologies = clean_list(pre_query.get("technologies", [])) or ["AI", "digital tools"]
    processes = clean_list(pre_query.get("processes", [])) or ["operations", "management"]
    regulations = clean_list(pre_query.get("regulations", [])) or ["compliance rules"]
    standards = clean_list(pre_query.get("standards", [])) or ["quality standards"]

    # Personas / Roles
    personas_dict = pre_query.get("buyer_personas", {}) or {}
    personas = [k for k, v in personas_dict.items() if v and str(v).upper() != "NOT_FOUND"]
    if not personas:
        personas = ["CEO", "Manager", "Procurement Officer", "Operations Lead"]

    # Pain points
    pains_dict = pre_query.get("pain_points", {}) or {}
    pain_points = [v for k, v in pains_dict.items() if v and str(v).upper() != "NOT_FOUND"]
    if not pain_points:
        pain_points = ["operational overhead", "efficiency bottlenecks"]

    # Outcomes
    outcomes_dict = pre_query.get("desired_outcomes", {}) or {}
    outcomes = [v for k, v in outcomes_dict.items() if v and str(v).upper() != "NOT_FOUND"]
    if not outcomes:
        outcomes = ["improving workflow efficiency", "reducing operational costs"]

    # Knowledge Graph entities (from state)
    graph_entities = [str(n.get("entity_name", "")) for n in state.get("entity_nodes", [])]
    graph_entities = [e for e in graph_entities if e and e.upper() != "NOT_FOUND"]

    # Semantic Keyword Builder Expansion Rules
    local_rng = random.Random(42) # Thread-safe local random generator
    
    combiner_patterns = [
        ("{product} for {persona}", "Role", "commercial", "Verified Facts | Authority Sources"),
        ("{service} for {persona}", "Role", "commercial", "Verified Facts | Authority Sources"),
        ("{product} {topic}", "Topic", "informational", "Verified Facts | Industry Topics"),
        ("best {product} to {outcome}", "Opportunity", "commercial", "Verified Facts | Outcomes"),
        ("{tech} in {process}", "Long Tail", "informational", "Industry Topics"),
        ("{tech} {standards} compliance", "Authority", "informational", "Industry Topics | Authority Sources"),
        ("{product} complying with {regulations}", "Authority", "informational", "Verified Facts | Authority Sources"),
        ("how to solve {pain_point} with {product}", "Problem", "commercial", "Pain Points | Verified Facts"),
        ("{persona} guides to {topic}", "Semantic", "informational", "Industry Topics | Authority Sources"),
        ("{service} {standards} checklist", "Authority", "informational", "Industry Topics | Authority Sources"),
        ("pricing of {product} for {persona}", "Commercial", "commercial", "Verified Facts | Authority Sources"),
        ("siri search for {product}", "Voice Search", "navigational", "Recommendation Queries"),
        ("alexa find {product}", "Voice Search", "navigational", "Recommendation Queries"),
        ("chatgpt recommended {product}", "AI Search", "commercial", "Recommendation Queries"),
        ("perplexity alternatives for {product}", "AI Search", "commercial", "Recommendation Queries"),
        ("{product} USA local {service}", "Location", "navigational", "Verified Facts"),
        ("latest trends in {topic}", "Trend", "informational", "Industry Topics")
    ]

    if graph_entities:
        combiner_patterns.append(("{entity} {topic}", "Entity", "informational", "Knowledge Graph"))

    # Phase A: Semantic combinator loop
    iterations = 0
    max_iterations = 5000
    while len(expanded_keywords) < 5050 and iterations < max_iterations:
        iterations += 1
        
        pattern, kw_type, kw_intent, kw_source = local_rng.choice(combiner_patterns)
        
        fmt_persona = local_rng.choice(personas)
        fmt_product = local_rng.choice(products)
        fmt_service = local_rng.choice(services)
        fmt_topic = local_rng.choice(topics)
        fmt_tech = local_rng.choice(technologies)
        fmt_proc = local_rng.choice(processes)
        fmt_std = local_rng.choice(standards)
        fmt_reg = local_rng.choice(regulations)
        fmt_pain = local_rng.choice(pain_points)
        fmt_out = local_rng.choice(outcomes)
        fmt_entity = local_rng.choice(graph_entities) if graph_entities else "entity"
        
        try:
            new_kw = pattern.format(
                persona=fmt_persona,
                product=fmt_product,
                service=fmt_service,
                topic=fmt_topic,
                technology=fmt_tech,
                process=fmt_proc,
                standards=fmt_std,
                regulations=fmt_reg,
                pain_point=fmt_pain,
                outcome=fmt_out,
                entity=fmt_entity
            )
            
            new_kw_clean = new_kw.strip().replace("  ", " ")
            if new_kw_clean.lower() not in seen_keywords:
                seen_keywords.add(new_kw_clean.lower())
                
                expanded_keywords.append({
                    "keyword": new_kw_clean,
                    "keyword_type": kw_type,
                    "intent": kw_intent,
                    "cluster": fmt_topic + " Setup" if "setup" in new_kw_clean.lower() or "implement" in new_kw_clean.lower() else fmt_topic + " Solutions",
                    "source": kw_source
                })
        except Exception:
            continue

    # Phase B: Prefix/Suffix Modifier fallback expansion deterministically to ensure 5050+ keywords
    prefixes = [
        "best", "top", "affordable", "custom", "reliable", "secure", "modern", "certified", 
        "professional", "local", "online", "cloud", "free", "enterprise", "strategic",
        "innovative", "popular", "essential", "key", "recommended", "advanced", "standard",
        "official", "expert", "trusted", "quality", "leading", "verified", "direct"
    ]
    
    suffixes = [
        "solutions", "platforms", "services", "tools", "agencies", "firms", "consultants", 
        "features", "benefits", "cost", "pricing", "reviews", "ratings", "alternatives",
        "near me", "USA", "online", "system", "software", "applications", "integration", 
        "setup", "guide", "tutorial", "case study", "best practices", "compliance"
    ]

    if len(expanded_keywords) < 5050:
        logger.info("Combinator permutations exhausted. Running Phase B modifier expansion...")
        base_keywords = list(expanded_keywords)
        
        # We loop deterministically to generate exactly the required amount without collisions
        for p in prefixes:
            if len(expanded_keywords) >= 5050:
                break
            for seed_item in base_keywords:
                if len(expanded_keywords) >= 5050:
                    break
                for s in suffixes:
                    if len(expanded_keywords) >= 5050:
                        break
                    
                    kw_text = seed_item["keyword"]
                    new_kw_clean = f"{p} {kw_text} {s}".strip().replace("  ", " ")
                    if new_kw_clean.lower() not in seen_keywords:
                        seen_keywords.add(new_kw_clean.lower())
                        
                        expanded_keywords.append({
                            "keyword": new_kw_clean,
                            "keyword_type": "Long Tail" if " " in new_kw_clean else "Short Tail",
                            "intent": seed_item["intent"],
                            "cluster": seed_item["cluster"],
                            "source": seed_item["source"]
                        })

    # Ensure EVERY single keyword is scored deterministically
    final_keywords = []
    for item in expanded_keywords:
        scores = compute_keyword_scores(
            item["keyword"],
            item["keyword_type"],
            item["intent"],
            bi,
            state.get("crawled_pages", []),
            state.get("entity_nodes", [])
        )
        item.update(scores)
        final_keywords.append(item)

    logger.info(f"V3 Keyword Intelligence finished. Expanded seeds to {len(final_keywords)} keywords.")
    return {"keywords": final_keywords}
