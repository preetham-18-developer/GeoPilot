import json
import logging
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

VERIFICATION_PROMPT = """You are a strict Verification Agent for the AI Visibility Optimization Platform.
Your sole job is to audit and verify extracted facts against the source page content.

Source URL: {source_url}
Source Page Markdown Content:
---
{page_content}
---

Raw Fact to Verify:
Category: {fact_category}
Key: {fact_key}
Value: {fact_value}

Strict No-Hallucination Audit:
1. Examine if the raw fact is explicitly supported by the page content.
2. If the fact contains any fabricated, embellished, or missing details not found in the content, you MUST adjust it, or mark it as "NOT FOUND".
3. Find the exact sentence/paragraph in the page content that serves as evidence.
4. Calculate a verification confidence score between 0.0 and 1.0 (1.0 = perfect verbatim match, 0.0 = completely fabricated).
5. You are forbidden from using outside knowledge.
6. Use only supplied page content.
7. If information is unavailable, return UNKNOWN.
8. Do not infer founders, years, locations, industries, products, or services.

Your response must be a valid JSON object. Do not wrap it in markdown code blocks or add text. Format:
{{
  "verified": true, // or false if unsupported
  "fact_category": "product",
  "fact_key": "Cloud CRM Pro pricing",
  "fact_value": "$49/month",
  "evidence_text": "verbatim text snippet from source content",
  "confidence_score": 0.95 // float
}}
"""

class VerificationAgent:
    def __init__(self):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_template(VERIFICATION_PROMPT)

    def verify_fact(self, fact: Dict[str, Any], page_content: str) -> Dict[str, Any]:
        """Audits a single raw fact against its source page content using the LLM."""
        source_url = fact.get("source_url", "")
        fact_category = fact.get("fact_category", "")
        fact_key = fact.get("fact_key", "")
        fact_value = fact.get("fact_value", "")
        
        # Limit context to avoid token limits
        page_content_preview = page_content[:15000]
        
        try:
            formatted_prompt = self.prompt.format_messages(
                source_url=source_url,
                page_content=page_content_preview,
                fact_category=fact_category,
                fact_key=fact_key,
                fact_value=fact_value
            )
            response = self.llm.invoke(formatted_prompt)
            
            # Clean up potential markdown formatting in output
            resp_text = response.content.strip()
            if resp_text.startswith("```json"):
                resp_text = resp_text[7:]
            if resp_text.endswith("```"):
                resp_text = resp_text[:-3]
            resp_text = resp_text.strip()
            
            verification_result = json.loads(resp_text)
            verification_result["source_url"] = source_url
            return verification_result
        except Exception as e:
            logger.error(f"Error verifying fact for url {source_url}: {e}")
            return {
                "verified": False,
                "fact_category": fact_category,
                "fact_key": fact_key,
                "fact_value": fact_value,
                "evidence_text": "NOT FOUND due to parsing error",
                "confidence_score": 0.0,
                "source_url": source_url
            }

def run_verifier(state: AgentState) -> Dict[str, Any]:
    """Node function that runs verification on all extracted raw facts."""
    logger.info("Running Verifier Node...")
    verifier = VerificationAgent()
    project_id = state.get("project_id")
    
    # Create page map for fast lookup
    pages_map = {p["url"]: p["markdown_content"] for p in state.get("crawled_pages", [])}
    raw_facts = state.get("raw_facts", [])
    verified_facts = []
    
    for fact in raw_facts:
        source_url = fact.get("source_url", "")
        page_content = pages_map.get(source_url, "")
        
        if not page_content:
            continue
            
        verification = verifier.verify_fact(fact, page_content)
        
        # Keep only verified facts with a confidence score above 0.70
        if verification.get("verified", False) and verification.get("confidence_score", 0.0) >= 0.70:
            verified_facts.append({
                "page_id": fact.get("page_id"),
                "fact_category": verification.get("fact_category", fact.get("fact_category")),
                "fact_key": verification.get("fact_key", fact.get("fact_key")),
                "fact_value": verification.get("fact_value", fact.get("fact_value")),
                "source_url": source_url,
                "evidence_text": verification.get("evidence_text", ""),
                "confidence_score": verification.get("confidence_score", 0.0)
            })
        else:
            logger.warning(f"Rejected unverified or low-confidence fact: {fact}")
            try:
                from app.core.supabase import supabase_client
                supabase_client.table("extraction_failures").insert({
                    "project_id": project_id,
                    "page_url": source_url,
                    "reason": "Verification Rejected",
                    "agent_name": "Verifier",
                    "error_message": f"Fact category={fact.get('fact_category')}, key={fact.get('fact_key')}, value={fact.get('fact_value')}. Verified={verification.get('verified')}, confidence={verification.get('confidence_score')}"
                }).execute()
            except Exception as db_err:
                logger.error(f"Failed to log verification rejection: {db_err}")
            
    logger.info(f"Verifier finished. Verified {len(verified_facts)}/{len(raw_facts)} facts.")
    return {"verified_facts": verified_facts}
