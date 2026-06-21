import json
import logging
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

QA_AGENT_PROMPT = """You are an elite Quality Assurance Agent for the AI Visibility Optimization Platform.
Your sole job is to act as the final validation layer before intelligence reports reach the customer dashboard.

You must review the business description and a list of verified facts:

Business Description:
{business_description}

Verified Facts:
{verified_facts_json}

Your task is to analyze the package and verify if there are any unsupported claims, low confidence declarations, or mismatched business logic (e.g., SWOT opportunities not aligning with verified facts).

Run a strict validation check:
1. Are there any claims in the description or opportunities that cannot be backed up by the verified facts list?
2. Estimate an overall data confidence score between 0 and 100 based on validation.

Your response must be a valid JSON object. Do not wrap it in markdown code blocks. Format:
{{
  "unsupported_claims": ["List of any claims made that lack evidence, or empty if none"],
  "qa_score_estimate": 95 // integer 0-100
}}
"""

class QualityAssuranceAgent:
    def __init__(self):
        self.llm = get_llm()
        self.prompt = ChatPromptTemplate.from_template(QA_AGENT_PROMPT)

    def audit_package(self, state: AgentState) -> Dict[str, Any]:
        """Hybrid QA validation: programmatic audits combined with LLM validation."""
        verified_facts = state.get("verified_facts", [])
        report = state.get("report", {})
        
        # 1. Programmatic Checks
        missing_evidence = 0
        low_confidence = 0
        seen_keys = set()
        duplicates = 0
        
        for fact in verified_facts:
            # Check missing evidence text
            if not fact.get("evidence_text") or fact["evidence_text"].strip() == "" or fact["evidence_text"].upper() == "NOT FOUND":
                missing_evidence += 1
            
            # Check low confidence (verification confidence under 70%)
            # Note: verified_facts confidence_score is float (0.0 to 1.0)
            if fact.get("confidence_score", 0.0) < 0.70:
                low_confidence += 1
                
            # Check duplicate facts
            key = (fact.get("fact_category"), fact.get("fact_key"), fact.get("fact_value"))
            if key in seen_keys:
                duplicates += 1
            else:
                seen_keys.add(key)

        # 2. LLM Checks for Unsupported Claims
        unsupported_claims = []
        llm_score = 100
        
        try:
            facts_str = json.dumps(verified_facts, indent=2)
            desc_str = report.get("executive_summary", "No description compiled")
            
            formatted_prompt = self.prompt.format_messages(
                business_description=desc_str,
                verified_facts_json=facts_str
            )
            response = self.llm.invoke(formatted_prompt)
            
            resp_text = response.content.strip()
            if resp_text.startswith("```json"):
                resp_text = resp_text[7:]
            if resp_text.endswith("```"):
                resp_text = resp_text[:-3]
            resp_text = resp_text.strip()
            
            llm_result = json.loads(resp_text)
            unsupported_claims = llm_result.get("unsupported_claims", [])
            llm_score = llm_result.get("qa_score_estimate", 100)
        except Exception as e:
            logger.error(f"Error in QA LLM audit: {e}")
            
        # 3. Compile final cumulative QA score
        # Deduct score for programmatic failures
        deductions = (missing_evidence * 10) + (duplicates * 5) + (low_confidence * 10) + (len(unsupported_claims) * 15)
        final_qa_score = max(0, min(100, llm_score - deductions))
        
        # Approval Status Rule
        # Run is flagged for review if final score is below 80, or if there are unsupported claims
        approval_status = "approved"
        if final_qa_score < 70 or len(unsupported_claims) > 0 or missing_evidence > 0:
            approval_status = "flagged"
            
        return {
            "approval_status": approval_status,
            "qa_score": final_qa_score,
            "checks": {
                "missing_evidence_count": missing_evidence,
                "duplicate_facts_count": duplicates,
                "low_confidence_facts_count": low_confidence,
                "unsupported_claims": unsupported_claims
            }
        }

def run_qa_agent(state: AgentState) -> Dict[str, Any]:
    """Node function that executes Quality Assurance checks."""
    logger.info("Running QA Agent Node...")
    agent = QualityAssuranceAgent()
    qa_report = agent.audit_package(state)
    logger.info(f"QA Agent finished. Status: {qa_report['approval_status']}, Score: {qa_report['qa_score']}")
    return {"qa_report": qa_report}
