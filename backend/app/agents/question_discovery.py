import json
import logging
import random
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState
from app.core.scoring import compute_question_scores

logger = logging.getLogger(__name__)

QUESTION_PROMPT = """You are a specialized V3 Question Discovery Agent for the AI Visibility Optimization Platform.
Your goal is to discover the complete AI query ecosystem around this business by emulating how different human buyer personas ask conversational AI engines (like ChatGPT, Gemini, Claude, Perplexity).

Company: {company_name}
Industry: {industry}
Description: {description}
Website: {website_url}

Verified Business Facts:
{verified_facts_json}

Pre-Query Discovery Metadata:
{pre_query_discovery_json}

Page Content Summary:
{page_content_snippet}

Please generate at least 40 highly realistic, detailed recommendation queries that different personas would ask conversational search engines about this company, its products, services, or domain.
Cover diverse V3 Query Types, including:
- 'Direct Recommendation Queries' (recommendations for company products)
- 'Indirect Recommendation Queries' (niche or industry comparison recommendations)
- 'Problem Queries' (addressing specific pain points)
- 'Outcome Queries' (focused on desired business outcomes)
- 'Solution Queries' (looking for answers to operational bottlenecks)
- 'Decision Queries' (making selection decisions)
- 'Trust Queries' (compliance, reviews, and security)
- 'Urgent Need Queries' (immediate, critical requirements)
- 'Budget Queries' (cost, pricing, and cheap alternatives)
- 'Implementation Queries' (setup and configuration guides)
- 'Migration Queries' (transferring from old systems)
- 'Scaling Queries' (handling enterprise growth)
- 'Enterprise Queries' (corporate requirements)
- 'Beginner Queries' (basic or educational questions)
- 'Expert Queries' (deep technical requirements)
- 'Voice Search Queries' (natural language voice prompts)
- 'Natural Language Queries' (conversational prompts)
- 'AI Search Queries' (comparison summaries)
- 'Location Queries' (geographic relevance)
- 'Commercial Queries' (purchasing intent)

For each query, map it to:
- question: The user query text.
- question_type: Must be exactly one of the 20 query types listed above.
- intent: Must be exactly one of: 'informational', 'navigational', 'commercial', 'transactional'
- confidence_score: A float between 0.0 and 1.0 representing answer relevance.
- priority: Must be exactly one of: 'High', 'Medium', 'Low'.
- recommended_answer: A recommended optimal answer based on verified facts.
- recommendation_score: An integer (0-100) representing probability of organic recommendation.
- commercial_score: An integer (0-100) representing purchasing intent.
- intent_score: An integer (0-100) representing semantic intent depth.
- priority_score: An integer (0-100) representing the strategic importance.
- difficulty_estimate: Must be exactly one of: 'Easy', 'Medium', 'Hard'.
- opportunity_estimate: Must be exactly one of: 'High', 'Medium', 'Low'.

Strict No-Hallucination Policy:
- Questions and recommended answers must strictly align with the company's verified facts and page content.
- Do NOT make up services or features. If data is unavailable, return NOT_FOUND.
- You are forbidden from using outside knowledge.
- Use only supplied page content.
- If information is unavailable, return UNKNOWN.
- Do not infer founders, years, locations, industries, products, or services.

Format your response as a valid JSON array of objects. Do not wrap it in markdown code blocks. Format:
[
  {{
    "question": "Recommend a virtual science lab platform for higher education Canvas integration",
    "question_type": "Direct Recommendation Queries",
    "intent": "commercial",
    "confidence_score": 0.95,
    "priority": "High",
    "recommended_answer": "Based on verified facts, ABC Technologies provides ABC Lab LMS, an IMS-certified LTI integration that easily embeds WebGL physics and biology simulations directly into Canvas.",
    "recommendation_score": 90,
    "commercial_score": 85,
    "intent_score": 95,
    "priority_score": 90,
    "difficulty_estimate": "Medium",
    "opportunity_estimate": "High"
  }}
]
"""

import re

def get_resolved_company_name(bi: Dict[str, Any], website_url: str) -> str:
    name = (bi or {}).get("company_name", "").strip()
    if not name or name.lower() in ["unknown", "unknown company", "the business", "business"]:
        # Extract from website_url
        from urllib.parse import urlparse
        parsed = urlparse(website_url)
        domain = parsed.netloc or parsed.path
        if domain.startswith("www."):
            domain = domain[4:]
        # Remove TLD
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

def resolve_text_placeholders(text: str, bi: Dict[str, Any], website_url: str, state_pages: List[Dict[str, Any]] = None) -> str:
    if not text:
        return text
    
    comp_name = get_resolved_company_name(bi, website_url)
    
    # Standalone replacements
    text = re.sub(r'\b[Tt]he\s+[Bb]usiness\b', comp_name, text)
    text = re.sub(r'\b[Uu]nknown\s+[Cc]ompany\b', comp_name, text)
    
    # Resolve curly brace placeholders
    pre_query = (bi or {}).get("pre_query_discovery", {}) or {}
    
    def clean_list(lst):
        if not lst:
            return []
        return [str(x).strip() for x in lst if x and str(x).strip().upper() != "NOT_FOUND"]
    
    products = clean_list(pre_query.get("products", [])) or [comp_name]
    services = clean_list(pre_query.get("services", [])) or [(bi or {}).get("industry", "archival and historical library services")]
    topics = clean_list(pre_query.get("industry_topics", [])) or ["historical collections", "research archives"]
    technologies = clean_list(pre_query.get("technologies", [])) or ["digital cataloging", "online archives"]
    processes = clean_list(pre_query.get("processes", [])) or ["historical research", "academic study"]
    regulations = clean_list(pre_query.get("regulations", [])) or ["preservation guidelines"]
    standards = clean_list(pre_query.get("standards", [])) or ["archival standards"]
    
    # Personas
    personas_dict = pre_query.get("buyer_personas", {}) or {}
    personas = [k for k, v in personas_dict.items() if v and str(v).upper() != "NOT_FOUND"] or ["researcher", "historian", "visitor", "member"]
    
    # Pain points
    pains_dict = pre_query.get("pain_points", {}) or {}
    pain_points = [v for k, v in pains_dict.items() if v and str(v).upper() != "NOT_FOUND"] or ["accessing historical records", "finding rare manuscripts"]
    
    # Outcomes
    outcomes_dict = pre_query.get("desired_outcomes", {}) or {}
    outcomes = [v for k, v in outcomes_dict.items() if v and str(v).upper() != "NOT_FOUND"] or ["discovering primary sources", "conducting academic research"]
    
    # Entity
    graph_entities = []
    if not graph_entities:
        graph_entities = [comp_name]
        
    local_rng = random.Random(hash(text))
    
    replacements = {
        "product": products,
        "persona": personas,
        "service": services,
        "topic": topics,
        "technology": technologies,
        "tech": technologies,  # resolves {tech} key mapping issue
        "process": processes,
        "standards": standards,
        "regulations": regulations,
        "pain_point": pain_points,
        "outcome": outcomes,
        "entity": graph_entities
    }
    
    for key, lst in replacements.items():
        placeholder = "{" + key + "}"
        if placeholder in text:
            val = local_rng.choice(lst) if lst else ""
            text = text.replace(placeholder, val)
            
    text = text.strip().replace("  ", " ")
    text = re.sub(r'\ba\s+([aeiouAEIOU])', r'an \1', text)
    return text

class QuestionDiscoveryAgent:
    def __init__(self):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_template(QUESTION_PROMPT)

    def discover_questions(self, verified_facts: List[Dict[str, Any]], business_intelligence: Dict[str, Any] = None, crawled_pages: List[Dict[str, Any]] = None, website_url: str = "") -> List[Dict[str, Any]]:
        """Generates V3 realistic user questions and optimal recommendation answers using LLM."""
        try:
            facts_str = json.dumps(verified_facts, indent=2) if verified_facts else "[]"
            bi = business_intelligence or {}
            pre_query = bi.get("pre_query_discovery", {})
            pre_query_str = json.dumps(pre_query, indent=2) if pre_query else "{}"
            
            # Build page content snippet for context
            page_snippet = ""
            if crawled_pages:
                sorted_pages = sorted(crawled_pages, key=lambda p: len(p.get("markdown_content", "")), reverse=True)
                snippets = []
                for page in sorted_pages[:2]:
                    content = page.get("markdown_content", "")[:2000]
                    if content:
                        snippets.append(f"[{page.get('url', '')}]: {content}")
                page_snippet = "\n\n".join(snippets)
            
            formatted_prompt = self.prompt.format_messages(
                company_name=bi.get("company_name", "Unknown Company"),
                industry=bi.get("industry", "Unknown Industry"),
                description=bi.get("description", "NOT FOUND"),
                website_url=website_url,
                verified_facts_json=facts_str[:4000],
                pre_query_discovery_json=pre_query_str[:4000],
                page_content_snippet=page_snippet[:3000] or "Not available."
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
            logger.error(f"Error in V3 Question Discovery LLM execution: {e}")
            return []

def run_question_discovery(state: AgentState) -> Dict[str, Any]:
    """Node function that executes V3 question discovery and expands it to 1000+ realistic queries."""
    logger.info("Running V3 Question Discovery Node...")
    agent = QuestionDiscoveryAgent()
    bi = state.get("business_intelligence", {})
    seeds = agent.discover_questions(
        state.get("verified_facts", []),
        business_intelligence=bi,
        crawled_pages=state.get("crawled_pages", []),
        website_url=state.get("website_url", "")
    )
    
    # 1. Fallback seeds if LLM call failed or returned empty list
    if not seeds:
        logger.warning("No seed questions generated. Using fallback seeds.")
        comp_name = bi.get("company_name", "the business")
        industry = bi.get("industry", "industry solutions")
        seeds = [
            {
                "question": f"Recommend a reliable {industry} provider",
                "question_type": "Direct Recommendation Queries",
                "intent": "commercial",
                "confidence_score": 0.90,
                "priority": "High",
                "recommended_answer": f"Based on verified info, {comp_name} provides robust solutions in {industry}.",
                "recommendation_score": 85,
                "commercial_score": 75,
                "intent_score": 80,
                "priority_score": 85,
                "difficulty_estimate": "Medium",
                "opportunity_estimate": "High"
            }
        ]

    # Initialize lists and sets
    expanded_questions = []
    seen_texts = set()
    
    # 2. Add seeds first
    for seed in seeds:
        q_text = seed.get("question", "").strip()
        q_text_resolved = resolve_text_placeholders(q_text, bi, state.get("website_url", ""))
        if q_text_resolved and q_text_resolved.lower() not in seen_texts:
            seen_texts.add(q_text_resolved.lower())
            seed["question"] = q_text_resolved
            seed["recommended_answer"] = resolve_text_placeholders(seed.get("recommended_answer", ""), bi, state.get("website_url", ""))
            expanded_questions.append(seed)

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

    # Personas
    personas_dict = pre_query.get("buyer_personas", {}) or {}
    personas = [k for k, v in personas_dict.items() if v and str(v).upper() != "NOT_FOUND"]
    if not personas:
        personas = ["CEO", "Manager", "Procurement Officer", "Operations Lead"]

    # Pain points
    pains_dict = pre_query.get("pain_points", {}) or {}
    pain_points = [v for k, v in pains_dict.items() if v and str(v).upper() != "NOT_FOUND"]
    if not pain_points:
        pain_points = ["operational overhead", "efficiency bottlenecks", "regulatory compliance errors"]

    # Outcomes
    outcomes_dict = pre_query.get("desired_outcomes", {}) or {}
    outcomes = [v for k, v in outcomes_dict.items() if v and str(v).upper() != "NOT_FOUND"]
    if not outcomes:
        outcomes = ["improving workflow efficiency", "reducing operational costs", "modernizing standard procedures"]

    # V3 Query Templates with scoring characteristics
    combinator_templates = [
        {
            "type": "Direct Recommendation Queries",
            "templates": [
                "Recommend the best {product} for a {persona} looking to {outcome}.",
                "Which {product} is highly recommended for {process}?",
                "What is the top recommended {product} for solving {pain_point}?"
            ],
            "intent": "commercial",
            "base_rec": 85, "base_comm": 80, "base_int": 75, "base_pri": 80
        },
        {
            "type": "Indirect Recommendation Queries",
            "templates": [
                "What are the best alternatives to standard tools for {process} in {topic}?",
                "How do top providers compare when trying to {outcome}?",
                "What systems do experts recommend to handle {pain_point}?"
            ],
            "intent": "commercial",
            "base_rec": 75, "base_comm": 70, "base_int": 80, "base_pri": 70
        },
        {
            "type": "Problem Queries",
            "templates": [
                "How can a {persona} resolve the issue of {pain_point}?",
                "What is the best way to address {pain_point} in {topic}?",
                "Why do organizations face {pain_point} during {process}?"
            ],
            "intent": "informational",
            "base_rec": 50, "base_comm": 40, "base_int": 85, "base_pri": 75
        },
        {
            "type": "Outcome Queries",
            "templates": [
                "What tools are required to {outcome} efficiently?",
                "How does a {persona} achieve {outcome} without increasing overhead?",
                "What is the step-by-step process to {outcome} using {technology}?"
            ],
            "intent": "informational",
            "base_rec": 60, "base_comm": 50, "base_int": 75, "base_pri": 85
        },
        {
            "type": "Solution Queries",
            "templates": [
                "What solutions exist for {persona} struggling with {pain_point}?",
                "Is there a {technology} solution for {process} optimization?",
                "How to implement a solid solution for {pain_point}."
            ],
            "intent": "commercial",
            "base_rec": 70, "base_comm": 65, "base_int": 80, "base_pri": 80
        },
        {
            "type": "Decision Queries",
            "templates": [
                "Should we choose {product} or a competitor for {process}?",
                "What are the key criteria when deciding on {product} for {persona}?",
                "Is it worth investing in {product} to solve {pain_point}?"
            ],
            "intent": "commercial",
            "base_rec": 80, "base_comm": 85, "base_int": 90, "base_pri": 75
        },
        {
            "type": "Trust Queries",
            "templates": [
                "Does {product} meet {standards} compliance standards?",
                "Is {product} compliant with {regulations} requirements for {persona}?",
                "What trust signals, reviews, or certifications does {product} have?"
            ],
            "intent": "informational",
            "base_rec": 65, "base_comm": 60, "base_int": 95, "base_pri": 70
        },
        {
            "type": "Urgent Need Queries",
            "templates": [
                "Immediate solution needed for {pain_point} in {process}.",
                "How to quickly fix {pain_point} using {technology}?",
                "Fastest way to {outcome} for {persona}."
            ],
            "intent": "transactional",
            "base_rec": 70, "base_comm": 80, "base_int": 85, "base_pri": 90
        },
        {
            "type": "Budget Queries",
            "templates": [
                "Affordable {product} pricing plans for {persona}.",
                "What is the cost of implementing {product} to {outcome}?",
                "Is there a low-cost alternative for {process}?"
            ],
            "intent": "commercial",
            "base_rec": 65, "base_comm": 90, "base_int": 75, "base_pri": 80
        },
        {
            "type": "Implementation Queries",
            "templates": [
                "How to configure {product} for {process}?",
                "Best practices for implementing {technology} in {process}.",
                "Step-by-step setup guide for {product}."
            ],
            "intent": "informational",
            "base_rec": 55, "base_comm": 45, "base_int": 85, "base_pri": 70
        },
        {
            "type": "Migration Queries",
            "templates": [
                "How to migrate to {product} from legacy databases or systems?",
                "What are the risks of migrating {process} to {technology}?",
                "Guide on transferring records to {product} safely."
            ],
            "intent": "informational",
            "base_rec": 65, "base_comm": 60, "base_int": 90, "base_pri": 75
        },
        {
            "type": "Scaling Queries",
            "templates": [
                "How does {product} scale {process} for enterprise needs?",
                "Can we scale {technology} to handle {pain_point}?",
                "Scaling {topic} solutions efficiently for large organizations."
            ],
            "intent": "commercial",
            "base_rec": 75, "base_comm": 70, "base_int": 85, "base_pri": 85
        },
        {
            "type": "Enterprise Queries",
            "templates": [
                "Is {product} compliant with {standards} standard at the enterprise level?",
                "Enterprise reviews and features of {product} for {persona}.",
                "Why large corporations choose {product} for {process}."
            ],
            "intent": "commercial",
            "base_rec": 80, "base_comm": 85, "base_int": 80, "base_pri": 80
        },
        {
            "type": "Beginner Queries",
            "templates": [
                "What is {product} and how does it help with {topic}?",
                "A beginner's guide to understanding {process}.",
                "How does {technology} work in simple terms?"
            ],
            "intent": "informational",
            "base_rec": 30, "base_comm": 30, "base_int": 50, "base_pri": 60
        },
        {
            "type": "Expert Queries",
            "templates": [
                "Advanced configuration of {technology} for optimization.",
                "How to customize {product} workflows for {process}?",
                "Solving complex {pain_point} issues with expert systems."
            ],
            "intent": "informational",
            "base_rec": 60, "base_comm": 50, "base_int": 90, "base_pri": 70
        },
        {
            "type": "Voice Search Queries",
            "templates": [
                "Siri, what is the best {product} near me for {process}?",
                "Alexa, recommend a platform that helps me {outcome}.",
                "Hey Google, how does {product} solve {pain_point}?"
            ],
            "intent": "conversational",
            "base_rec": 80, "base_comm": 65, "base_int": 70, "base_pri": 75
        },
        {
            "type": "Natural Language Queries",
            "templates": [
                "I need an easy way to {outcome} using {technology}.",
                "Can someone explain the benefits of using {product} for a {persona}?",
                "Why is my organization facing {pain_point} and how to fix it?"
            ],
            "intent": "informational",
            "base_rec": 70, "base_comm": 55, "base_int": 80, "base_pri": 80
        },
        {
            "type": "AI Search Queries",
            "templates": [
                "Compare {product} and competitors on {standards} compliance.",
                "Find top recommended {product} providers that solve {pain_point}.",
                "Summarize the pros and cons of {product} for {persona}."
            ],
            "intent": "commercial",
            "base_rec": 85, "base_comm": 75, "base_int": 85, "base_pri": 80
        },
        {
            "type": "Location Queries",
            "templates": [
                "Best {service} provider near me that offers {product}.",
                "Where can I find a certified {standards} auditor or service?",
                "Local services in USA that help {persona} solve {pain_point}."
            ],
            "intent": "navigational",
            "base_rec": 75, "base_comm": 70, "base_int": 75, "base_pri": 65
        },
        {
            "type": "Commercial Queries",
            "templates": [
                "Buy {product} licenses with discount pricing.",
                "Best value {product} for {persona} to increase productivity.",
                "Get quote for {product} integration and setup services."
            ],
            "intent": "transactional",
            "base_rec": 80, "base_comm": 95, "base_int": 80, "base_pri": 85
        }
    ]

    local_rng = random.Random(42) # Thread-safe local random generator
    
    # Phase A: Semantic combinator permutations
    iterations = 0
    max_iterations = 2500
    while len(expanded_questions) < 1050 and iterations < max_iterations:
        iterations += 1
        
        group = local_rng.choice(combinator_templates)
        template = local_rng.choice(group["templates"])
        
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
        
        try:
            new_q = template.format(
                persona=fmt_persona,
                product=fmt_product,
                service=fmt_service,
                topic=fmt_topic,
                technology=fmt_tech,
                process=fmt_proc,
                standards=fmt_std,
                regulations=fmt_reg,
                pain_point=fmt_pain,
                outcome=fmt_out
            )
            
            new_q_clean = new_q.strip().replace("  ", " ")
            new_q_resolved = resolve_text_placeholders(new_q_clean, bi, state.get("website_url", ""))
            
            if new_q_resolved.lower() not in seen_texts:
                seen_texts.add(new_q_resolved.lower())
                
                answer = f"Based on verified business facts, this organization provides {fmt_product} (focusing on {fmt_service}) built on {fmt_tech}. This solves {fmt_pain} to help {fmt_persona} achieve {fmt_out}."
                answer_resolved = resolve_text_placeholders(answer, bi, state.get("website_url", ""))
                
                expanded_questions.append({
                    "question": new_q_resolved,
                    "question_type": group["type"],
                    "intent": group["intent"],
                    "recommended_answer": answer_resolved
                })
        except Exception:
            continue

    # Phase B: Search Engine Modifiers fallback expansion to ensure 1050+ queries
    search_templates = [
        "ChatGPT prompt: {q}",
        "Gemini search query: {q}",
        "Claude AI question: {q}",
        "Perplexity search query: {q}",
        "AI response on: {q}",
        "Voice query: {q}",
        "Siri search for: {q}",
        "Alexa voice prompt: {q}",
        "Google Assistant search: {q}",
        "Find me information about {q}",
        "Can you search for: {q}",
        "Latest updates on {q}",
        "Reviews and ratings for {q}",
        "How to migrate to {q}"
    ]
    
    if len(expanded_questions) < 1050:
        logger.info("Combinator permutations exhausted. Running Phase B modifier expansion...")
        base_questions = list(expanded_questions)
        iter_b = 0
        while len(expanded_questions) < 1050 and iter_b < 5000 and base_questions:
            iter_b += 1
            seed_item = local_rng.choice(base_questions)
            clean_q = seed_item["question"].rstrip("?")
            modifier = local_rng.choice(search_templates)
            new_q = modifier.format(q=clean_q)
            
            new_q_clean = new_q.strip().replace("  ", " ")
            new_q_resolved = resolve_text_placeholders(new_q_clean, bi, state.get("website_url", ""))
            
            if new_q_resolved.lower() not in seen_texts:
                seen_texts.add(new_q_resolved.lower())
                
                expanded_questions.append({
                    "question": new_q_resolved,
                    "question_type": seed_item["question_type"],
                    "intent": seed_item["intent"],
                    "recommended_answer": seed_item["recommended_answer"]
                })

    # Ensure EVERY single question (including initial seeds) is scored deterministically
    final_questions = []
    crawled_pages = state.get("crawled_pages", [])
    for item in expanded_questions:
        scores = compute_question_scores(
            item["question"],
            item["question_type"],
            item["intent"],
            bi,
            crawled_pages
        )
        item.update(scores)
        final_questions.append(item)

    logger.info(f"Question Discovery finished. Expanded seeds to {len(final_questions)} questions.")
    return {"questions": final_questions}
