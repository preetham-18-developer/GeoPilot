from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    project_id: str
    run_id: str
    website_url: str
    crawled_pages: List[Dict[str, Any]]
    raw_facts: List[Dict[str, Any]]
    verified_facts: List[Dict[str, Any]]
    business_intelligence: Dict[str, Any]
    questions: List[Dict[str, Any]]
    keywords: List[Dict[str, Any]]
    competitors: List[Dict[str, Any]]
    content_opportunities: List[Dict[str, Any]]
    report: Dict[str, Any]
    qa_report: Dict[str, Any]
    errors: List[str]
    entity_nodes: List[Dict[str, Any]]
    entity_relationships: List[Dict[str, Any]]
    recommendation_simulations: List[Dict[str, Any]]
    content_coverage: List[Dict[str, Any]]
    ai_visibility_score: Dict[str, Any]
    gap_analysis: List[Dict[str, Any]]
    competitor_feature_matrix: Dict[str, Any]
