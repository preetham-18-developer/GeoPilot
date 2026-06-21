import logging
import asyncio
import time
from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.fact_extractor import run_fact_extractor
from app.agents.verifier import run_verifier
from app.agents.business_intelligence import run_business_intelligence
from app.agents.question_discovery import run_question_discovery
from app.agents.keyword_intelligence import run_keyword_intelligence
from app.agents.competitor_discovery import run_competitor_discovery
from app.agents.content_agent import run_content_agent
from app.agents.report_generator import compile_report
from app.agents.qa_agent import run_qa_agent
from app.agents.entity_graph import run_entity_graph
from app.agents.recommendation_sim import run_recommendation_sim
from app.agents.content_coverage import run_content_coverage
from app.agents.visibility_score import run_visibility_scoring
from app.core.supabase import supabase_client
from app.core.recommendation_engine import RecommendationEngineV2
from app.core.hallucination_detector import HallucinationDetector
from app.core.consistency_engine import KnowledgeConsistencyEngine
from app.core.historical_tracker import HistoricalTracker
from app.core.cache import invalidate_project_cache

logger = logging.getLogger(__name__)

def update_status(project_id: str, run_id: str, status: str, current_agent: str = None):
    """Helper to update status and current_agent in both projects and analysis_runs tables."""
    try:
        supabase_client.table("analysis_runs").update({
            "status": status,
            "current_agent": current_agent
        }).eq("id", run_id).execute()
        
        supabase_client.table("projects").update({
            "status": status,
            "current_agent": current_agent
        }).eq("id", project_id).execute()
    except Exception as e:
        logger.error(f"Error updating run/project status for {project_id}/{run_id}: {e}")

def log_agent_run(project_id: str, agent_name: str, status: str, input_tokens: int = 0, output_tokens: int = 0, processing_time: float = 0.0, error_message: str = None):
    """Helper to record agent run metrics in agent_runs table."""
    try:
        supabase_client.table("agent_runs").insert({
            "project_id": project_id,
            "agent_name": agent_name,
            "status": status,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "processing_time": processing_time,
            "error_message": error_message
        }).execute()
    except Exception as e:
        logger.error(f"Error logging agent run for {agent_name}: {e}")

# Timing and token tracking wrappers for LangGraph nodes
def fact_extractor_node(state: AgentState):
    update_status(state["project_id"], state["run_id"], "extracting", "Fact Extractor")
    start = time.time()
    try:
        res = run_fact_extractor(state)
        duration = time.time() - start
        log_agent_run(state["project_id"], "Extraction", "completed", input_tokens=2200, output_tokens=800, processing_time=duration)
        return res
    except Exception as e:
        duration = time.time() - start
        log_agent_run(state["project_id"], "Extraction", "failed", input_tokens=2200, output_tokens=0, processing_time=duration, error_message=str(e))
        raise

def verifier_node(state: AgentState):
    update_status(state["project_id"], state["run_id"], "verifying", "Verifier")
    start = time.time()
    try:
        res = run_verifier(state)
        duration = time.time() - start
        log_agent_run(state["project_id"], "Verification", "completed", input_tokens=3500, output_tokens=1000, processing_time=duration)
        return res
    except Exception as e:
        duration = time.time() - start
        log_agent_run(state["project_id"], "Verification", "failed", input_tokens=3500, output_tokens=0, processing_time=duration, error_message=str(e))
        raise

def business_intelligence_node(state: AgentState):
    update_status(state["project_id"], state["run_id"], "analyzing", "Business Intelligence")
    start = time.time()
    try:
        res = run_business_intelligence(state)
        duration = time.time() - start
        log_agent_run(state["project_id"], "Business Intelligence", "completed", input_tokens=1800, output_tokens=600, processing_time=duration)
        return res
    except Exception as e:
        duration = time.time() - start
        log_agent_run(state["project_id"], "Business Intelligence", "failed", input_tokens=1800, output_tokens=0, processing_time=duration, error_message=str(e))
        raise

def question_discovery_node(state: AgentState):
    update_status(state["project_id"], state["run_id"], "analyzing", "Question Discovery")
    start = time.time()
    try:
        res = run_question_discovery(state)
        duration = time.time() - start
        log_agent_run(state["project_id"], "Question Discovery", "completed", input_tokens=1600, output_tokens=500, processing_time=duration)
        return res
    except Exception as e:
        duration = time.time() - start
        log_agent_run(state["project_id"], "Question Discovery", "failed", input_tokens=1600, output_tokens=0, processing_time=duration, error_message=str(e))
        raise

def keyword_intelligence_node(state: AgentState):
    update_status(state["project_id"], state["run_id"], "analyzing", "Keyword Agent")
    start = time.time()
    try:
        res = run_keyword_intelligence(state)
        duration = time.time() - start
        log_agent_run(state["project_id"], "Keyword Agent", "completed", input_tokens=1400, output_tokens=400, processing_time=duration)
        return res
    except Exception as e:
        duration = time.time() - start
        log_agent_run(state["project_id"], "Keyword Agent", "failed", input_tokens=1400, output_tokens=0, processing_time=duration, error_message=str(e))
        raise

def competitor_discovery_node(state: AgentState):
    update_status(state["project_id"], state["run_id"], "analyzing", "Competitor Agent")
    start = time.time()
    try:
        res = run_competitor_discovery(state)
        duration = time.time() - start
        log_agent_run(state["project_id"], "Competitor Agent", "completed", input_tokens=1500, output_tokens=450, processing_time=duration)
        return res
    except Exception as e:
        duration = time.time() - start
        log_agent_run(state["project_id"], "Competitor Agent", "failed", input_tokens=1500, output_tokens=0, processing_time=duration, error_message=str(e))
        raise

def content_agent_node(state: AgentState):
    update_status(state["project_id"], state["run_id"], "analyzing", "Content Agent")
    start = time.time()
    try:
        res = run_content_agent(state)
        duration = time.time() - start
        log_agent_run(state["project_id"], "Content Agent", "completed", input_tokens=1700, output_tokens=550, processing_time=duration)
        return res
    except Exception as e:
        duration = time.time() - start
        log_agent_run(state["project_id"], "Content Agent", "failed", input_tokens=1700, output_tokens=0, processing_time=duration, error_message=str(e))
        raise

def report_compiler_node(state: AgentState):
    update_status(state["project_id"], state["run_id"], "compiling", "Report Compiler")
    start = time.time()
    try:
        res = compile_report(state)
        duration = time.time() - start
        # Report compiler is local format formatting, count as completed
        return res
    except Exception:
        raise

def qa_agent_node(state: AgentState):
    update_status(state["project_id"], state["run_id"], "compiling", "Quality Assurance")
    start = time.time()
    try:
        res = run_qa_agent(state)
        duration = time.time() - start
        log_agent_run(state["project_id"], "Quality Assurance", "completed", input_tokens=4000, output_tokens=300, processing_time=duration)
        return res
    except Exception as e:
        duration = time.time() - start
        log_agent_run(state["project_id"], "Quality Assurance", "failed", input_tokens=4000, output_tokens=0, processing_time=duration, error_message=str(e))
        raise

def entity_graph_node(state: AgentState):
    update_status(state["project_id"], state["run_id"], "analyzing", "Entity Graph")
    start = time.time()
    try:
        res = run_entity_graph(state)
        duration = time.time() - start
        log_agent_run(state["project_id"], "Entity Graph", "completed", input_tokens=1500, output_tokens=400, processing_time=duration)
        return res
    except Exception as e:
        duration = time.time() - start
        log_agent_run(state["project_id"], "Entity Graph", "failed", input_tokens=1500, output_tokens=0, processing_time=duration, error_message=str(e))
        raise

def recommendation_sim_node(state: AgentState):
    update_status(state["project_id"], state["run_id"], "analyzing", "Recommendation Sim")
    start = time.time()
    try:
        res = run_recommendation_sim(state)
        duration = time.time() - start
        log_agent_run(state["project_id"], "Recommendation Sim", "completed", input_tokens=1800, output_tokens=500, processing_time=duration)
        return res
    except Exception as e:
        duration = time.time() - start
        log_agent_run(state["project_id"], "Recommendation Sim", "failed", input_tokens=1800, output_tokens=0, processing_time=duration, error_message=str(e))
        raise

def content_coverage_node(state: AgentState):
    update_status(state["project_id"], state["run_id"], "analyzing", "Content Coverage")
    start = time.time()
    try:
        res = run_content_coverage(state)
        duration = time.time() - start
        log_agent_run(state["project_id"], "Content Coverage", "completed", input_tokens=1600, output_tokens=450, processing_time=duration)
        return res
    except Exception as e:
        duration = time.time() - start
        log_agent_run(state["project_id"], "Content Coverage", "failed", input_tokens=1600, output_tokens=0, processing_time=duration, error_message=str(e))
        raise

def visibility_scoring_node(state: AgentState):
    update_status(state["project_id"], state["run_id"], "analyzing", "Visibility Score")
    start = time.time()
    try:
        res = run_visibility_scoring(state)
        duration = time.time() - start
        log_agent_run(state["project_id"], "Visibility Score", "completed", input_tokens=2000, output_tokens=600, processing_time=duration)
        return res
    except Exception as e:
        duration = time.time() - start
        log_agent_run(state["project_id"], "Visibility Score", "failed", input_tokens=2000, output_tokens=0, processing_time=duration, error_message=str(e))
        raise

# Initialize the state graph builder
workflow = StateGraph(AgentState)

# Register Wrapped Nodes
workflow.add_node("fact_extractor", fact_extractor_node)
workflow.add_node("verifier", verifier_node)
workflow.add_node("business_intelligence_agent", business_intelligence_node)
workflow.add_node("entity_graph", entity_graph_node)
workflow.add_node("question_discovery", question_discovery_node)
workflow.add_node("keyword_intelligence", keyword_intelligence_node)
workflow.add_node("competitor_discovery", competitor_discovery_node)
workflow.add_node("content_coverage_eval", content_coverage_node)
workflow.add_node("visibility_scoring", visibility_scoring_node)
workflow.add_node("content_agent", content_agent_node)
workflow.add_node("recommendation_sim", recommendation_sim_node)
workflow.add_node("report_compiler", report_compiler_node)
workflow.add_node("qa_agent", qa_agent_node)

# Build execution flow
workflow.set_entry_point("fact_extractor")
workflow.add_edge("fact_extractor", "verifier")
workflow.add_edge("verifier", "business_intelligence_agent")
workflow.add_edge("business_intelligence_agent", "entity_graph")
workflow.add_edge("entity_graph", "question_discovery")
workflow.add_edge("question_discovery", "keyword_intelligence")
workflow.add_edge("keyword_intelligence", "competitor_discovery")
workflow.add_edge("competitor_discovery", "content_coverage_eval")
workflow.add_edge("content_coverage_eval", "visibility_scoring")
workflow.add_edge("visibility_scoring", "content_agent")
workflow.add_edge("content_agent", "recommendation_sim")
workflow.add_edge("recommendation_sim", "report_compiler")
workflow.add_edge("report_compiler", "qa_agent")
workflow.add_edge("qa_agent", END)

# Compile graph
app_graph = workflow.compile()

async def run_analysis_pipeline(project_id: str, run_id: str, website_url: str):
    """
    Orchestrates the entire background agent execution run:
    1. Cleans up any previous analysis data for this project.
    2. Fetches crawled pages for the project's active website from web_pages.
    3. Runs the LangGraph multi-agent network.
    4. Saves raw facts, verified facts, business profiles, questions, keywords, competitors,
       content opportunities, and reports in Supabase.
    """
    logger.info(f"Triggering background Agent Pipeline for run {run_id}...")
    
    # Update analysis_runs table status to 'extracting'
    update_status(project_id, run_id, "extracting", "Fact Extractor")
    
    start_run_time = time.time()
    
    try:
        # 0. Clean up stale analysis data from previous runs for this project
        # Respects FK constraint: verified_facts → extracted_facts
        logger.info(f"Cleaning up stale analysis data for project {project_id}...")
        
        # First: delete verified_facts linked to this project's extracted_facts (FK constraint)
        try:
            from app.core.supabase import supabase_client as sb
            sb.rpc("delete_verified_facts_for_project", {"p_project_id": project_id}).execute()
        except Exception:
            # Fallback: raw SQL via postgrest if RPC not available
            try:
                supabase_client.table("verified_facts").delete().in_(
                    "extracted_fact_id",
                    [f["id"] for f in (supabase_client.table("extracted_facts").select("id").eq("project_id", project_id).execute().data or [])]
                ).execute()
            except Exception as e:
                logger.warning(f"verified_facts cleanup warning: {e}")
        
        # Tables that have project_id column — clean in FK-safe order
        cleanup_tables = [
            "extracted_facts",       # After verified_facts (FK dependency)
            "business_profiles",
            "questions",
            "keywords",
            "competitors",
            "competitor_feature_matrix",
            "content_opportunities",
            "gap_analysis",
            "ai_visibility_tracking",
            "recommendation_simulations",
            "entity_nodes",
            "entity_relationships",
            "content_coverage",
            "reports",
            "qa_reports",
            "extraction_failures",
        ]
        for table in cleanup_tables:
            try:
                supabase_client.table(table).delete().eq("project_id", project_id).execute()
            except Exception as e:
                logger.warning(f"Cleanup warning for {table}: {e}")
            
        logger.info("Cleanup complete. Fetching crawled pages...")


        # 1. Fetch crawled page contents from Supabase web_pages table
        # Only fetch pages with content (word_count > 0) to filter empty SPA shells
        pages_resp = supabase_client.table("web_pages").select(
            "id, url, title, content, meta_description, word_count"
        ).eq("project_id", project_id).execute()
        
        if not pages_resp.data:
            raise ValueError(f"No crawled page contents found in web_pages for project {project_id}")
            
        crawled_pages = []
        empty_pages = 0
        for page in pages_resp.data:
            content = page.get("content", "") or ""
            meta = page.get("meta_description", "") or ""
            # Include page if it has content OR meta description
            effective_content = content if content.strip() else meta
            if effective_content.strip():
                crawled_pages.append({
                    "id": page["id"],
                    "url": page["url"],
                    "title": page["title"] or "",
                    "meta_description": meta,
                    "markdown_content": effective_content
                })
            else:
                empty_pages += 1
                
        logger.info(f"Loaded {len(crawled_pages)} pages with content, {empty_pages} empty pages skipped.")
        
        if not crawled_pages:
            raise ValueError(f"All {empty_pages} crawled pages are empty (likely SPA rendering failed). Check Playwright setup.")
            
        # 2. Setup Initial State
        initial_state: AgentState = {
            "project_id": project_id,
            "run_id": run_id,
            "website_url": website_url,
            "crawled_pages": crawled_pages,
            "raw_facts": [],
            "verified_facts": [],
            "business_intelligence": {},
            "questions": [],
            "keywords": [],
            "competitors": [],
            "content_opportunities": [],
            "report": {},
            "qa_report": {},
            "errors": [],
            "entity_nodes": [],
            "entity_relationships": [],
            "recommendation_simulations": [],
            "content_coverage": [],
            "ai_visibility_score": {},
            "gap_analysis": [],
            "competitor_feature_matrix": {}
        }
        
        # 3. Run the LangGraph
        from app.core.supabase import _client_ctx
        try:
            current_client = _client_ctx.get()
        except LookupError:
            from app.core.supabase import _global_client
            current_client = _global_client

        def run_with_ctx(c, state):
            t = _client_ctx.set(c)
            try:
                return app_graph.invoke(state)
            finally:
                _client_ctx.reset(t)

        loop = asyncio.get_event_loop()
        final_state = await loop.run_in_executor(None, lambda: run_with_ctx(current_client, initial_state))

        
        # 4. Save results to Database
        # A. Save raw extracted facts
        raw_facts = final_state.get("raw_facts", [])
        fact_id_map = {}
        if raw_facts:
            facts_to_insert = [
                {
                    "project_id": project_id,
                    "page_id": f.get("page_id"),
                    "fact_category": f.get("fact_category", "general"),
                    "fact_key": f.get("fact_key", ""),
                    "fact_value": f.get("fact_value", ""),
                    "source_url": f.get("source_url", ""),
                    "evidence_text": f.get("evidence_text", ""),
                    "confidence_score": f.get("confidence_score", 1.0)
                }
                for f in raw_facts
            ]
            fact_resp = supabase_client.table("extracted_facts").insert(facts_to_insert).execute()
            if fact_resp.data:
                for db_fact in fact_resp.data:
                    k = (db_fact["fact_category"], db_fact["fact_key"], db_fact["fact_value"], db_fact["source_url"])
                    fact_id_map[k] = db_fact["id"]

        # B. Save verified facts
        verified_facts = final_state.get("verified_facts", [])
        if verified_facts:
            v_facts_to_insert = []
            for vf in verified_facts:
                k = (vf["fact_category"], vf["fact_key"], vf["fact_value"], vf["source_url"])
                extracted_id = fact_id_map.get(k)
                if extracted_id:
                    v_facts_to_insert.append({
                        "extracted_fact_id": extracted_id,
                        "verification_status": "verified",
                        "verification_score": float(vf.get("confidence_score", 1.0) * 100),
                        "verified_by": "Verification Agent",
                        "verified_at": "now()"
                    })
            if v_facts_to_insert:
                supabase_client.table("verified_facts").insert(v_facts_to_insert).execute()
            
        # C. Save business profiles
        bi_report = final_state.get("business_intelligence", {})
        if bi_report:
            supabase_client.table("business_profiles").insert({
                "project_id": project_id,
                "company_name": bi_report.get("company_name", "Unknown"),
                "industry": bi_report.get("industry", "Unknown"),
                "description": bi_report.get("description", "NOT FOUND"),
                "mission": bi_report.get("mission", "NOT FOUND"),
                "vision": bi_report.get("vision", "NOT FOUND"),
                "usp": bi_report.get("usp", "NOT FOUND"),
                "target_audience": bi_report.get("target_audience", "NOT FOUND"),
                "strengths": bi_report.get("strengths", []),
                "weaknesses": bi_report.get("weaknesses", []),
                "opportunities": bi_report.get("opportunities", []),
                "risks": bi_report.get("risks", []),
                "trust_signals": bi_report.get("trust_signals", []),
                "business_model": bi_report.get("business_model", "NOT_FOUND"),
                "ai_visibility_opportunities": bi_report.get("ai_visibility_opportunities", [])
            }).execute()
            
        # D. Save questions
        questions = final_state.get("questions", [])
        if questions:
            q_to_insert = [
                {
                    "project_id": project_id,
                    "question": q["question"],
                    "question_type": q["question_type"],
                    "intent": q.get("intent", "informational"),
                    "confidence_score": q.get("confidence_score", 1.0),
                    "priority": q.get("priority", "Medium"),
                    "recommended_answer": q.get("recommended_answer", ""),
                    "recommendation_score": q.get("recommendation_score", 0.0),
                    "commercial_score": q.get("commercial_score", 0.0),
                    "intent_score": q.get("intent_score", 0.0),
                    "priority_score": q.get("priority_score", 0.0),
                    "difficulty_estimate": q.get("difficulty_estimate", "Medium"),
                    "opportunity_estimate": q.get("opportunity_estimate", "Medium")
                }
                for q in questions
            ]
            supabase_client.table("questions").insert(q_to_insert).execute()
            
        # E. Save keywords
        keywords = final_state.get("keywords", [])
        if keywords:
            kw_to_insert = [
                {
                    "project_id": project_id,
                    "keyword": kw["keyword"],
                    "keyword_type": kw["keyword_type"],
                    "intent": kw.get("intent", "informational"),
                    "cluster": kw.get("cluster", "General"),
                    "confidence_score": kw.get("confidence_score", 1.0),
                    "priority": kw.get("priority", "Medium"),
                    "difficulty_estimate": kw.get("difficulty_estimate", "Medium"),
                    "opportunity_estimate": kw.get("opportunity_estimate", "Medium"),
                    "source": kw.get("source", "Recommendation Queries")
                }
                for kw in keywords
            ]
            supabase_client.table("keywords").insert(kw_to_insert).execute()
            
        # F. Save competitors & Feature Matrix
        competitors = final_state.get("competitors", [])
        if competitors:
            comp_to_insert = [
                {
                    "project_id": project_id,
                    "competitor_name": comp["competitor_name"],
                    "website": comp.get("website", ""),
                    "competitor_type": comp["competitor_type"],
                    "strengths": comp.get("strengths", []),
                    "weaknesses": comp.get("weaknesses", []),
                    "confidence_score": comp.get("confidence_score", 1.0),
                    "description": comp.get("description", "NOT_FOUND"),
                    "unique_features": comp.get("unique_features", []),
                    "content_gaps": comp.get("content_gaps", []),
                    "reason_selected": comp.get("reason_selected", []),
                    "similarity_score": int(comp.get("similarity_score", 50)),
                    "industry_match": comp.get("industry_match", "NOT_FOUND"),
                    "audience_match": comp.get("audience_match", "NOT_FOUND"),
                    "service_match": comp.get("service_match", "NOT_FOUND")
                }
                for comp in competitors
            ]
            supabase_client.table("competitors").insert(comp_to_insert).execute()
            
        matrix = final_state.get("competitor_feature_matrix", {})
        if matrix:
            supabase_client.table("competitor_feature_matrix").insert({
                "project_id": project_id,
                "features": matrix
            }).execute()
            
        # G. Save content opportunities with scoring
        content_opps = final_state.get("content_opportunities", [])
        if content_opps:
            opps_to_insert = [
                {
                    "project_id": project_id,
                    "title": o["title"],
                    "content_type": o["content_type"],
                    "priority": o.get("priority", "medium"),
                    "reason": o.get("reason", ""),
                    "impact_score": int(o.get("impact_score", 50)),
                    "effort_score": int(o.get("effort_score", 50)),
                    "expected_benefit": o.get("expected_benefit", "NOT_FOUND"),
                    "supporting_evidence": o.get("supporting_evidence", "NOT_FOUND"),
                    "related_keywords": o.get("related_keywords", []),
                    "related_questions": o.get("related_questions", [])
                }
                for o in content_opps
            ]
            supabase_client.table("content_opportunities").insert(opps_to_insert).execute()
            
        # G1. Save Gap Analysis
        gap_analysis = final_state.get("gap_analysis", [])
        if gap_analysis:
            gaps_to_insert = [
                {
                    "project_id": project_id,
                    "gap_type": g.get("gap_type", "General"),
                    "priority": g.get("priority", "medium"),
                    "recommendation": g.get("recommendation", "NOT_FOUND")
                }
                for g in gap_analysis
            ]
            supabase_client.table("gap_analysis").insert(gaps_to_insert).execute()

        # G2. Save AI Visibility score
        vis_score = final_state.get("ai_visibility_score", {})
        if vis_score:
            supabase_client.table("ai_visibility_tracking").insert({
                "project_id": project_id,
                "score": float(vis_score.get("overall_score", 0.0)),
                "details": vis_score
            }).execute()

        # G3. Save Recommendation Simulations
        simulations = final_state.get("recommendation_simulations", [])
        if simulations:
            sims_to_insert = [
                {
                    "project_id": project_id,
                    "query": s["query"],
                    "recommendation_probability": float(s.get("recommendation_probability", 50.0)),
                    "supporting_evidence": s.get("supporting_evidence", []),
                    "missing_requirements": s.get("missing_requirements", []),
                    "improvement_actions": s.get("improvement_actions", [])
                }
                for s in simulations
            ]
            supabase_client.table("recommendation_simulations").insert(sims_to_insert).execute()

        # G4. Save Entity Nodes & Relationships
        nodes = final_state.get("entity_nodes", [])
        relationships = final_state.get("entity_relationships", [])
        node_name_to_id = {}
        if nodes:
            nodes_to_insert = [
                {
                    "project_id": project_id,
                    "entity_name": n["entity_name"],
                    "entity_type": n["entity_type"],
                    "properties": n.get("properties", {})
                }
                for n in nodes
            ]
            nodes_resp = supabase_client.table("entity_nodes").insert(nodes_to_insert).execute()
            if nodes_resp.data:
                for db_node in nodes_resp.data:
                    node_name_to_id[db_node["entity_name"]] = db_node["id"]
                    
        if relationships and node_name_to_id:
            rels_to_insert = []
            for r in relationships:
                src_id = node_name_to_id.get(r["source_entity_name"])
                tgt_id = node_name_to_id.get(r["target_entity_name"])
                if src_id and tgt_id:
                    rels_to_insert.append({
                        "project_id": project_id,
                        "source_node_id": src_id,
                        "target_node_id": tgt_id,
                        "relationship_type": r["relationship_type"]
                    })
            if rels_to_insert:
                supabase_client.table("entity_relationships").insert(rels_to_insert).execute()

        # G5. Save Content Coverage
        coverage = final_state.get("content_coverage", [])
        if coverage:
            cov_to_insert = [
                {
                    "project_id": project_id,
                    "topic_name": c["topic_name"],
                    "coverage_score": float(c.get("coverage_score", 0.0)),
                    "question_coverage": c.get("question_coverage", []),
                    "keyword_coverage": c.get("keyword_coverage", []),
                    "faq_coverage": c.get("faq_coverage", []),
                    "content_depth": c.get("content_depth", "Shallow"),
                    "missing_content_areas": c.get("missing_content_areas", [])
                }
                for c in coverage
            ]
            supabase_client.table("content_coverage").insert(cov_to_insert).execute()

        # H. Save completed Report
        report_data = final_state.get("report", {})
        if report_data:
            supabase_client.table("reports").insert({
                "project_id": project_id,
                "report_type": "full",
                "report_title": f"AI Visibility Optimization Package - {website_url}",
                "report_content": report_data,
                "generated_by": "Report Compiler"
            }).execute()
            
        # I. Save QA Report
        qa_report = final_state.get("qa_report", {})
        if qa_report:
            supabase_client.table("qa_reports").insert({
                "project_id": project_id,
                "run_id": run_id,
                "approval_status": qa_report.get("approval_status", "flagged"),
                "qa_score": float(qa_report.get("qa_score", 0.0)),
                "checks": qa_report.get("checks", {})
            }).execute()

        # I1. Record Longitudinal Historical Metrics
        try:
            logger.info("Computing longitudinal historical metrics...")
            bp_bi = final_state.get("business_intelligence", {}) or {}
            bp = {
                "company_name": bp_bi.get("company_name", "Unknown"),
                "industry": bp_bi.get("industry", "Unknown"),
                "description": bp_bi.get("description", "NOT FOUND"),
                "mission": bp_bi.get("mission", "NOT FOUND"),
                "vision": bp_bi.get("vision", "NOT FOUND"),
                "usp": bp_bi.get("usp", "NOT FOUND"),
                "target_audience": bp_bi.get("target_audience", "NOT FOUND"),
                "strengths": bp_bi.get("strengths", []),
                "weaknesses": bp_bi.get("weaknesses", []),
                "opportunities": bp_bi.get("opportunities", []),
                "risks": bp_bi.get("risks", []),
                "trust_signals": bp_bi.get("trust_signals", []),
                "business_model": bp_bi.get("business_model", "NOT_FOUND"),
                "ai_visibility_opportunities": bp_bi.get("ai_visibility_opportunities", []),
                "pre_query_discovery": bp_bi.get("pre_query_discovery", {})
            }

            verified_facts_raw = final_state.get("verified_facts", []) or []
            verified_facts = []
            for vf in verified_facts_raw:
                verified_facts.append({
                    "fact_type": vf.get("fact_category", "general"),
                    "fact_value": vf.get("fact_value", ""),
                    "fact_key": vf.get("fact_key", ""),
                    "evidence": vf.get("evidence_text", ""),
                    "confidence_score": float(vf.get("confidence_score", 1.0)),
                    "source_url": vf.get("source_url", "")
                })

            project_data_payload = {
                "business_profile": bp,
                "verified_facts": verified_facts,
                "questions": final_state.get("questions", []) or [],
                "keywords": final_state.get("keywords", []) or [],
                "competitors": final_state.get("competitors", []) or [],
                "content_coverage": final_state.get("content_coverage", []) or [],
                "crawled_pages": final_state.get("crawled_pages", []) or [],
                "content_opportunities": final_state.get("content_opportunities", []) or [],
                "entity_nodes": final_state.get("entity_nodes", []) or [],
                "gap_analysis": final_state.get("gap_analysis", []) or []
            }

            vis_score = final_state.get("ai_visibility_score", {}) or {}
            visibility_val = float(vis_score.get("overall_score", 0.0))

            sub_scores = vis_score.get("sub_scores", {}) or {}
            coverage_val = float(sub_scores.get("content_coverage", 0.0))

            try:
                rec_engine = RecommendationEngineV2()
                rec_res = rec_engine.run(project_data_payload)
                recommendation_val = float(rec_res.get("overall_recommendation_score", 0.0))
            except Exception as rec_err:
                logger.warning(f"Error computing recommendation score for history: {rec_err}")
                recommendation_val = 0.0

            try:
                det = HallucinationDetector()
                det_res = det.detect(project_data_payload)
                risk_score = float(det_res.get("hallucination_risk_score", 0.0))
                hallucination_val = max(0.0, 100.0 - risk_score)
            except Exception as det_err:
                logger.warning(f"Error computing hallucination score for history: {det_err}")
                hallucination_val = 100.0

            try:
                cons_engine = KnowledgeConsistencyEngine()
                cons_res = cons_engine.run(project_data_payload)
                consistency_val = float(cons_res.get("consistency_score", 0.0))
            except Exception as cons_err:
                logger.warning(f"Error computing consistency score for history: {cons_err}")
                consistency_val = 100.0

            supabase_client.table("historical_metrics").insert({
                "project_id": project_id,
                "run_id": run_id,
                "visibility_score": round(visibility_val, 1),
                "recommendation_score": round(recommendation_val, 1),
                "hallucination_score": round(hallucination_val, 1),
                "consistency_score": round(consistency_val, 1),
                "coverage_score": round(coverage_val, 1)
            }).execute()
            logger.info(f"Successfully recorded historical metrics for project {project_id}, run {run_id}.")
        except Exception as hist_err:
            logger.error(f"Failed to save historical metrics: {hist_err}")

        # J. Update Project category/industry and status
        industry = bi_report.get("industry", "Other")
        supabase_client.table("projects").update({
            "industry": industry,
            "status": "completed",
            "current_agent": None
        }).eq("id", project_id).execute()
        
        # 5. Mark Run completed
        total_duration = time.time() - start_run_time
        supabase_client.table("analysis_runs").update({
            "status": "completed",
            "completed_at": "now()",
            "processing_time": total_duration,
            "tokens_used": 13700, # Cumulative estimate
            "current_agent": None
        }).eq("id", run_id).execute()

        # Invalidate project cache keys so that endpoints fetch fresh completed results
        try:
            invalidate_project_cache(project_id)
        except Exception as cache_err:
            logger.warning(f"Error invalidating cache after pipeline completion: {cache_err}")
        
        logger.info(f"Pipeline finished successfully for run {run_id}.")
        
    except Exception as e:
        logger.error(f"Error executing agent pipeline: {e}")
        total_duration = time.time() - start_run_time
        supabase_client.table("analysis_runs").update({
            "status": "failed",
            "error_message": str(e),
            "completed_at": "now()",
            "processing_time": total_duration,
            "current_agent": None
        }).eq("id", run_id).execute()
        supabase_client.table("projects").update({
            "status": "failed",
            "current_agent": None
        }).eq("id", project_id).execute()
