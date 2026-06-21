import json
import logging
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

FACT_EXTRACTION_PROMPT = """You are an expert Fact Extraction Agent for the AI Visibility Optimization Platform.
Your mission is to extract key business facts from the provided website page text.

Page URL: {page_url}
Page Title: {page_title}
Page Content:
---
{content}
---

Extract key facts if present. For each fact, map it to:
1. fact_category: Category (e.g. 'company_name', 'description', 'product', 'service', 'pricing', 'testimonial', 'certification', 'award', 'location', 'contact', 'social_link', 'faq', 'case_study', 'blog_topic')
2. fact_key: A short descriptive key representing what the fact is (e.g. 'Cloud CRM Pro pricing', 'main_office_address', 'CEO_name')
3. fact_value: The actual fact value (e.g. '$49/month', 'ABC Technologies', '123 Main St, New York')
4. evidence_text: The verbatim sentence or short paragraph from the Page Content that proves this fact.
5. confidence_score: A float between 0.0 and 1.0 showing how clearly stated the fact is.

Strict No-Hallucination Policy:
- ONLY extract facts that are explicitly stated in the text.
- Do NOT make up products, pricing, reviews, or links.
- If no facts are found on this page, return an empty list.

Your response must be a valid JSON array of objects. Do not wrap it in markdown code blocks or add text. Format:
[
  {{
    "fact_category": "product",
    "fact_key": "Cloud CRM Pro pricing",
    "fact_value": "$49/month",
    "evidence_text": "Our Cloud CRM Pro subscription is priced at $49/month.",
    "confidence_score": 1.0
  }}
]
"""

class FactExtractorAgent:
    def __init__(self, project_id: str = None):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_template(FACT_EXTRACTION_PROMPT)
        self.project_id = project_id

    def extract_facts_from_page(self, page: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Invokes the LLM to extract structured facts from a single page."""
        url = page.get("url", "")
        title = page.get("title", "")
        content = page.get("markdown_content", "")
        page_id = page.get("id", None)
        
        if not content.strip():
            return []
            
        # Limit content size to avoid context exhaustion on very large single pages
        content_preview = content[:15000]
        
        try:
            formatted_prompt = self.prompt.format_messages(
                page_url=url,
                page_title=title,
                content=content_preview
            )
            response = self.llm.invoke(formatted_prompt)
            
            # Clean up potential markdown formatting in output
            resp_text = response.content.strip()
            if resp_text.startswith("```json"):
                resp_text = resp_text[7:]
            if resp_text.endswith("```"):
                resp_text = resp_text[:-3]
            resp_text = resp_text.strip()
            
            facts = json.loads(resp_text)
            validated_facts = []
            for fact in facts:
                evidence = fact.get("evidence_text", "").strip()
                if not evidence or evidence == "NOT_FOUND":
                    continue
                fact["source_url"] = url
                fact["page_id"] = page_id
                validated_facts.append(fact)
            return validated_facts
        except Exception as e:
            logger.error(f"Error extracting facts from page {url}: {e}")
            try:
                from app.core.supabase import supabase_client
                supabase_client.table("extraction_failures").insert({
                    "project_id": self.project_id or "",
                    "page_url": url,
                    "reason": "Extraction Parse Error",
                    "agent_name": "Fact Extractor",
                    "error_message": str(e)
                }).execute()
            except Exception as db_err:
                logger.error(f"Failed to log extraction failure: {db_err}")
            return []

def run_fact_extractor(state: AgentState) -> Dict[str, Any]:
    """Node function to run fact extraction across all crawled pages."""
    logger.info("Running Fact Extractor Node...")
    project_id = state.get("project_id")
    extractor = FactExtractorAgent(project_id=project_id)
    raw_facts = []
    
    # Extract facts page-by-page (or a representative sample if too many pages)
    pages = state.get("crawled_pages", [])
    for page in pages[:15]:  # Limit to top 15 pages for rate-limit and speed efficiency
        facts = extractor.extract_facts_from_page(page)
        raw_facts.extend(facts)
        
    logger.info(f"Fact Extractor finished. Extracted {len(raw_facts)} raw facts.")
    return {"raw_facts": raw_facts}
