import logging
from typing import Dict, Any
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

def compile_report(state: AgentState) -> Dict[str, Any]:
    """Node function that compiles the full state into a structured report."""
    logger.info("Compiling Final Analysis Report...")
    
    bi = state.get("business_intelligence", {})
    verified_facts = state.get("verified_facts", [])
    questions = state.get("questions", [])
    keywords = state.get("keywords", [])
    competitors = state.get("competitors", [])
    
    # Get SWOT fields with fallbacks for tests
    swot_data = bi.get("swot", {}) if isinstance(bi.get("swot"), dict) else {}
    strengths = bi.get("strengths") or swot_data.get("strengths", [])
    weaknesses = bi.get("weaknesses") or swot_data.get("weaknesses", [])
    opportunities = bi.get("opportunities") or swot_data.get("opportunities", [])
    threats = bi.get("risks") or swot_data.get("threats", [])

    report_content = {
        "industry": bi.get("industry", "Unknown"),
        "executive_summary": bi.get("description", bi.get("executive_summary", "NOT FOUND")),
        "business_overview": bi.get("business_overview") or f"Mission: {bi.get('mission', 'NOT FOUND')}\nVision: {bi.get('vision', 'NOT FOUND')}\nUSP: {bi.get('usp', 'NOT FOUND')}",
        "product_analysis": bi.get("product_analysis") or f"USP: {bi.get('usp', 'NOT FOUND')}",
        "service_analysis": bi.get("service_analysis") or f"Target Audience: {bi.get('target_audience', 'NOT FOUND')}",
        "trust_analysis": bi.get("trust_analysis", "Verified Facts and Audited Credentials"),
        "swot": {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
            "threats": threats
        },
        "ai_visibility_analysis": bi.get("ai_visibility_analysis") or f"GEO Targets: {', '.join(opportunities) if opportunities else 'NOT FOUND'}",
        "total_verified_facts": len(verified_facts),
        "total_questions_discovered": len(questions),
        "total_keywords_strategized": len(keywords),
        "total_competitors_discovered": len(competitors)
    }
    
    logger.info("Report Compiled Successfully.")
    return {"report": report_content}
