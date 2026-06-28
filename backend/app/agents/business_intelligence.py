import json
import logging
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

def validate_and_clean_profile(profile: dict, url: str, crawled_content: str) -> dict:
    INVALID_VALUES = [
        'unknown', 'Unknown', 'UNKNOWN', 'N/A', 'n/a',
        'Not found', 'Not Found', 'None', 'null', '',
        'Acme Corp', 'Example Business', 'Your Business'
    ]
    
    # If company_name or business_name is invalid, extract from URL
    comp_name = profile.get('company_name') or profile.get('business_name')
    if not comp_name or comp_name in INVALID_VALUES:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc or urlparse(url).path
        name = domain.replace('www.', '').split('.')[0]
        cleaned_name = name.replace('-', ' ').replace('_', ' ').title()
        if "thelibrarycompany" in cleaned_name.lower().replace(" ", ""):
            cleaned_name = "The Library Company"
        profile['company_name'] = cleaned_name
        profile['business_name'] = cleaned_name
    else:
        profile['company_name'] = comp_name
        profile['business_name'] = comp_name
        
    # If industry or business_type is invalid, infer from content
    current_type = profile.get('business_type') or profile.get('industry')
    if not current_type or current_type in INVALID_VALUES:
        content_lower = crawled_content.lower()
        if any(w in content_lower for w in ['mentor', 'mentorship', 'career']):
            inferred_type = 'Career Mentorship Platform'
        elif any(w in content_lower for w in ['course', 'training', 'learn', 'education']):
            inferred_type = 'Education & Training'
        elif any(w in content_lower for w in ['restaurant', 'food', 'menu', 'dining']):
            inferred_type = 'Restaurant'
        elif any(w in content_lower for w in ['clinic', 'hospital', 'dental', 'doctor']):
            inferred_type = 'Healthcare'
        elif any(w in content_lower for w in ['shop', 'store', 'buy', 'grocery']):
            inferred_type = 'Retail'
        else:
            inferred_type = 'Business'
        profile['business_type'] = inferred_type
        profile['industry'] = inferred_type
    else:
        profile['business_type'] = current_type
        profile['industry'] = current_type
        
    # If seed_topics is empty, create basic ones from content
    if not profile.get('seed_topics') or not isinstance(profile.get('seed_topics'), list) or len(profile.get('seed_topics')) == 0:
        if 'pre_query_discovery' in profile and isinstance(profile['pre_query_discovery'], dict) and profile['pre_query_discovery'].get('industry_topics'):
            profile['seed_topics'] = profile['pre_query_discovery']['industry_topics']
        else:
            words = crawled_content.lower().split()
            stopwords = {
                'the','a','an','is','are','was','were',
                'be','been','being','have','has','had',
                'do','does','did','will','would','could',
                'should','may','might','shall','can',
                'to','of','in','for','on','with','at',
                'by','from','as','into','through','during',
                'and','or','but','if','then','that','this'
            }
            meaningful = [w for w in words if w not in stopwords and len(w) > 4]
            
            from collections import Counter
            freq = Counter(meaningful)
            top_words = [word for word, count in freq.most_common(20) if count > 1]
            profile['seed_topics'] = top_words[:15]
            
    # Normalize pre_query_discovery topics
    if 'pre_query_discovery' not in profile or not isinstance(profile['pre_query_discovery'], dict):
        profile['pre_query_discovery'] = {}
        
    pq = profile['pre_query_discovery']
    if not pq.get('industry_topics'):
        pq['industry_topics'] = profile.get('seed_topics') or []
    if not pq.get('services'):
        pq['services'] = [profile.get('industry')]
    if not pq.get('products'):
        pq['products'] = []
        
    return profile

BI_PROMPT = """You are an elite Business Intelligence Agent specializing in AI Search Engine Optimization (GEO/AIO).
Your goal is to analyze the company's verified business facts AND raw page content to write a comprehensive corporate, market, & recommendation intelligence profile.

Website: {website_url}

Verified Business Facts:
{verified_facts_json}

Supplemental Page Content (from crawled pages - use only if facts are missing):
{page_content_snippet}

Your analysis must output:
1. company_name: Detected brand/company name.
2. industry: Detected category/industry (e.g. EdTech, SaaS CRM, FinTech, Career Mentorship).
3. description: A clear 2-3 sentence overview of what the business does.
4. mission: Corporate mission statement (if found or inferred from facts).
5. vision: Corporate vision statement (if found or inferred from facts).
6. usp: Unique Selling Proposition.
7. target_audience: Primary audience description.
8. strengths: An array of key strengths.
9. weaknesses: An array of key weaknesses.
10. opportunities: An array of GEO/AIO market opportunities.
11. risks: An array of threats/risks.
12. trust_signals: An array of verified trust signals, certifications, security standards, reviews, or awards found in the facts.
13. business_model: Detected business model (e.g. SaaS, Subscription, Free service, eCommerce, B2B, B2C, Non-profit).
14. ai_visibility_opportunities: An array of specific opportunities to increase visibility in AI search engines.
15. pre_query_discovery: A nested JSON object containing:
    - industry_topics: An array of key topics related to the industry.
    - industry_terminology: An array of specialized industry terms/jargon.
    - products: An array of specific product offerings.
    - services: An array of specific service offerings.
    - processes: An array of key business/operational processes or workflows.
    - technologies: An array of systems, software, or technologies used or offered.
    - frameworks: An array of methodologies or structures (e.g., Scrum, LTI, standard frameworks).
    - certifications: An array of certifications held or required.
    - standards: An array of standards complied with (e.g., ISO, SOC2, LTI, ANSI).
    - regulations: An array of compliance regulations (e.g., GDPR, HIPAA, FERPA, OSHA).
    - buyer_personas: A JSON object mapping standard personas to their specific recommendation opportunities. Personas to evaluate are:
      'Founder', 'CEO', 'Director', 'Administrator', 'Manager', 'Buyer', 'Procurement Officer', 'Engineer', 'Developer', 'Teacher', 'Doctor', 'Consultant', 'Student', 'Operations Manager', 'Technology Lead', 'Facilities Manager', 'Government Officer'.
      If a persona is relevant, provide a 1-sentence recommendation opportunity (e.g., "CEO: Seeks ROI and high-level platform efficiency metrics"). If not relevant, return "NOT_FOUND".
    - pain_points: A JSON object with keys:
      'operational', 'technical', 'financial', 'growth', 'migration', 'scaling', 'trust', 'efficiency', 'compliance'.
      For each, provide a brief description of the problem solved. If not applicable, return "NOT_FOUND".
    - desired_outcomes: A JSON object with keys:
      'increase_revenue', 'reduce_cost', 'improve_efficiency', 'modernization', 'automation', 'growth', 'security', 'compliance', 'customer_satisfaction'.
      For each, provide how the business drives this outcome. If not applicable, return "NOT_FOUND".
    - authority_sources: A JSON object containing:
      * research_papers: An array of research papers, studies, or clinical trials validating the business or domain.
      * industry_associations: An array of professional associations or trade groups associated with the business/industry.
      * government_sources: An array of official government agencies or regulations backing the business/industry.
      * case_studies: An array of customer success stories or case study titles.
      * white_papers: An array of technical white papers or reports.
    - competitor_topics: An array of topics competitors write about or excel in.
    - content_gaps: An array of missing content or topics identified from facts/crawled content.

Strict Quality & No-Hallucination Policy:
- ONLY analyze what is supported by the verified facts OR explicitly stated in the page content.
- Do NOT make up new facts, strengths, reviews, or awards.
- If information is missing for a section, return "NOT_FOUND" for string values, or an empty array [] for lists.
- Avoid generic educational queries and meaningless permutations.
- You are forbidden from using outside knowledge.
- Use only supplied page content.
- If information is unavailable, return UNKNOWN.
- Do not infer founders, years, locations, industries, products, or services.

Format your response as a valid JSON object. Do not wrap it in markdown code blocks. Format:
{{
  "company_name": "ABC Technologies",
  "industry": "EdTech",
  "description": "ABC Technologies provides cloud-based LMS solutions...",
  "mission": "To make learning accessible and engaging.",
  "vision": "A world powered by digital educational environments.",
  "usp": "In-browser virtual lab simulations for scientific experiments.",
  "target_audience": "Higher education institutions and high schools.",
  "strengths": ["Strong virtual lab catalog", "LTI compliance"],
  "weaknesses": ["Lack of native mobile applications"],
  "opportunities": ["Optimize scientific keywords for Claude recommendation inclusion"],
  "risks": ["High pricing compared to legacy learning tools"],
  "trust_signals": ["ISO 27001 Certified", "4.8/5 G2 Rating"],
  "business_model": "B2B SaaS",
  "ai_visibility_opportunities": ["Implement structured schema markup for courses", "Build a dedicated FAQ section targeting conversational queries"],
  "pre_query_discovery": {{
    "industry_topics": ["LMS Platforms", "Virtual Science Labs"],
    "industry_terminology": ["LTI Integration", "Active Learning"],
    "products": ["ABC Lab LMS"],
    "services": ["Virtual Physics Labs", "Virtual Biology Labs"],
    "processes": ["Lab assignment workflows", "Grade syncing"],
    "technologies": ["WebGL", "IMS Global LTI"],
    "frameworks": ["LTI Standard v1.3"],
    "certifications": ["IMS Global Certified Integration"],
    "standards": ["LTI Compliant", "LMS standards"],
    "regulations": ["FERPA Compliance", "GDPR"],
    "buyer_personas": {{
      "Founder": "NOT_FOUND",
      "CEO": "NOT_FOUND",
      "Director": "Director of Online Learning: Looks to scale lab courses efficiently without physical lab footprints.",
      "Administrator": "LMS Administrator: Seeks easy LTI 1.3 integration and automated student enrollment.",
      "Manager": "NOT_FOUND",
      "Buyer": "NOT_FOUND",
      "Procurement Officer": "NOT_FOUND",
      "Engineer": "NOT_FOUND",
      "Developer": "NOT_FOUND",
      "Teacher": "Science Instructor: Wants pre-built lab templates and automatic grading features.",
      "Doctor": "NOT_FOUND",
      "Consultant": "NOT_FOUND",
      "Student": "Science Major Student: Demands realistic simulation and mobile-friendly lab worksheets.",
      "Operations Manager": "NOT_FOUND",
      "Technology Lead": "NOT_FOUND",
      "Facilities Manager": "NOT_FOUND",
      "Government Officer": "NOT_FOUND"
    }},
    "pain_points": {{
      "operational": "Physical lab resource limits and scheduling conflicts",
      "technical": "Complex LMS setups and grading integration issues",
      "financial": "High cost of physical lab equipment and maintenance",
      "growth": "NOT_FOUND",
      "migration": "Difficulty transferring grades from old LMS solutions",
      "scaling": "Cannot scale distance learning enrollments due to physical lab constraints",
      "trust": "Unsure if online labs are academically validated",
      "efficiency": "Hours spent manually grading paper-based lab reports",
      "compliance": "Ensuring student privacy compliance under FERPA"
    }},
    "desired_outcomes": {{
      "increase_revenue": "NOT_FOUND",
      "reduce_cost": "Minimize lab equipment overhead and physical maintenance costs",
      "improve_efficiency": "Automate lab assignment grades and syllabus syncing",
      "modernization": "Replace paper manuals with interactive WebGL science modules",
      "automation": "Automatically sync simulation completions directly to LMS",
      "growth": "Allow unlimited enrollment scaling for online courses",
      "security": "Secure SSO for students and staff via LTI",
      "compliance": "Fully compliant student records handling",
      "customer_satisfaction": "High retention and positive student course feedback"
    }},
    "authority_sources": {{
      "research_papers": ["Study on Active Learning via Virtual Labs (2024)"],
      "industry_associations": ["IMS Global Learning Consortium"],
      "government_sources": ["US Department of Education FERPA guidelines"],
      "case_studies": ["How State University scaled science labs to 10k students"],
      "white_papers": ["The Future of WebGL Simulations in Higher Education"]
    }},
    "competitor_topics": ["Hands-on lab kits", "Physical lab textbooks"],
    "content_gaps": ["No setup guides for Canvas integration", "Missing student lab workbook templates"]
  }}
}}
"""

class BusinessIntelligenceAgent:
    def __init__(self):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_template(BI_PROMPT)

    def analyze(self, website_url: str, verified_facts: List[Dict[str, Any]], crawled_pages: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyzes verified facts (and raw page content if facts are sparse) to produce a market and visibility report."""
        try:
            facts_str = json.dumps(verified_facts, indent=2) if verified_facts else "[]"
            
            # Aggregate page content for supplemental context (use first 3 most content-rich pages)
            page_content_snippet = ""
            if crawled_pages:
                sorted_pages = sorted(crawled_pages, key=lambda p: len(p.get("markdown_content", "")), reverse=True)
                snippets = []
                for page in sorted_pages[:3]:
                    url = page.get("url", "")
                    content = page.get("markdown_content", "")[:3000]
                    meta = page.get("meta_description", "")
                    if content or meta:
                        snippets.append(f"URL: {url}\nMeta: {meta}\nContent:\n{content}")
                page_content_snippet = "\n\n---\n\n".join(snippets)
            
            if not page_content_snippet:
                page_content_snippet = "No supplemental content available."
            
            formatted_prompt = self.prompt.format_messages(
                website_url=website_url,
                verified_facts_json=facts_str,
                page_content_snippet=page_content_snippet[:8000]
            )
            response = self.llm.invoke(formatted_prompt)
            
            resp_text = response.content.strip()
            if resp_text.startswith("```json"):
                resp_text = resp_text[7:]
            if resp_text.endswith("```"):
                resp_text = resp_text[:-3]
            resp_text = resp_text.strip()
            
            profile = json.loads(resp_text)
            profile = validate_and_clean_profile(profile, website_url, page_content_snippet)
            return profile
        except Exception as e:
            logger.error(f"Error in BI Analysis: {e}")
            fallback = {
                "company_name": "Unknown",
                "industry": "Unknown",
                "description": "NOT FOUND",
                "mission": "NOT FOUND",
                "vision": "NOT FOUND",
                "usp": "NOT FOUND",
                "target_audience": "NOT FOUND",
                "strengths": ["NOT FOUND"],
                "weaknesses": ["NOT FOUND"],
                "opportunities": ["NOT FOUND"],
                "risks": ["NOT FOUND"],
                "trust_signals": ["NOT FOUND"],
                "business_model": "NOT FOUND",
                "ai_visibility_opportunities": ["NOT FOUND"],
                "pre_query_discovery": {
                    "industry_topics": [],
                    "industry_terminology": [],
                    "products": [],
                    "services": [],
                    "processes": [],
                    "technologies": [],
                    "frameworks": [],
                    "certifications": [],
                    "standards": [],
                    "regulations": [],
                    "buyer_personas": {},
                    "pain_points": {},
                    "desired_outcomes": {},
                    "authority_sources": {
                        "research_papers": [],
                        "industry_associations": [],
                        "government_sources": [],
                        "case_studies": [],
                        "white_papers": []
                    },
                    "competitor_topics": [],
                    "content_gaps": []
                }
            }
            return validate_and_clean_profile(fallback, website_url, page_content_snippet)

def run_business_intelligence(state: AgentState) -> Dict[str, Any]:
    """Node function that executes business intelligence analysis."""
    logger.info("Running Business Intelligence Node...")
    agent = BusinessIntelligenceAgent()
    bi_report = agent.analyze(
        state.get("website_url", ""),
        state.get("verified_facts", []),
        crawled_pages=state.get("crawled_pages", [])
    )
    logger.info("Business Intelligence Agent finished.")
    return {"business_intelligence": bi_report}
