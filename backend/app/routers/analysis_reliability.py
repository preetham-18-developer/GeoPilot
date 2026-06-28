from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from app.core.quality_auditor import QuestionQualityAuditor, KeywordQualityAuditor
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.core.supabase import supabase_client
from app.core.dependencies import get_current_user
from app.crawler.spider import WebsiteSpider
from app.agents.graph import run_analysis_pipeline
from app.core.recommendation_engine import RecommendationEngineV2
from app.core.hallucination_detector import HallucinationDetector
from app.core.consistency_engine import KnowledgeConsistencyEngine
from app.core.reality_checker import RealityChecker
from app.core.benchmark_engine import CompetitorBenchmarkEngine
from app.core.historical_tracker import HistoricalTracker
from app.core.cache import get_cached_data, set_cached_data, invalidate_project_cache
from app.core.explainability_engine import ExplainabilityEngine
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/validation/{project_id}")
def get_validation_report(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Runs QuestionQualityAuditor and KeywordQualityAuditor against all stored data
    for a project and returns a structured validation report with scores, warnings,
    and actionable suggestions. No LLM calls - pure deterministic analysis.
    """
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Fetch all questions for this project (no pagination - auditor needs full set)
        q_resp = supabase_client.table("questions").select(
            "id, question, question_type, recommended_answer, intent, confidence_score, priority, "
            "recommendation_score, commercial_score, intent_score, priority_score, "
            "difficulty_estimate, opportunity_estimate"
        ).eq("project_id", project_id).execute()

        questions_raw = q_resp.data or []

        # Normalize to auditor-expected format
        questions_for_audit = [
            {
                "question": q.get("question", ""),
                "question_type": q.get("question_type", ""),
                "recommended_answer": q.get("recommended_answer", ""),
                "intent": q.get("intent", ""),
                "confidence_score": float(q.get("confidence_score", 1.0)),
                "priority": q.get("priority", "Medium"),
            }
            for q in questions_raw
        ]

        # Fetch all keywords for this project
        kw_resp = supabase_client.table("keywords").select(
            "id, keyword, keyword_type, intent, cluster, priority, confidence_score, "
            "difficulty_estimate, opportunity_estimate, source"
        ).eq("project_id", project_id).execute()

        keywords_raw = kw_resp.data or []

        keywords_for_audit = [
            {
                "keyword": kw.get("keyword", ""),
                "keyword_type": kw.get("keyword_type", ""),
                "intent": kw.get("intent", ""),
                "cluster": kw.get("cluster", ""),
                "priority": kw.get("priority", "Medium"),
                "confidence_score": float(kw.get("confidence_score", 1.0)),
            }
            for kw in keywords_raw
        ]

        # Run auditors
        q_auditor = QuestionQualityAuditor()
        kw_auditor = KeywordQualityAuditor()

        question_report = q_auditor.audit(questions_for_audit)
        keyword_report = kw_auditor.audit(keywords_for_audit)

        # Compute combined health score (weighted average)
        combined_score = round(
            (question_report["quality_score"] * 0.5 + keyword_report["quality_score"] * 0.5),
            1
        )

        # Determine overall status
        if combined_score >= 80:
            overall_status = "healthy"
        elif combined_score >= 60:
            overall_status = "warning"
        else:
            overall_status = "critical"

        return {
            "project_id": project_id,
            "overall_status": overall_status,
            "combined_quality_score": combined_score,
            "question_audit": question_report,
            "keyword_audit": keyword_report,
            "total_warnings": len(question_report["warnings"]) + len(keyword_report["warnings"]),
            "total_suggestions": len(question_report["suggestions"]) + len(keyword_report["suggestions"]),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running validation for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


def _get_project_data_payload(project_id: str) -> dict:
    try:
        bp_resp = supabase_client.table("business_profiles").select("*").eq("project_id", project_id).order("generated_at", desc=True).limit(1).execute()
        business_profile = bp_resp.data[0] if bp_resp.data else {}
    except Exception as e:
        logger.warning(f"Error fetching business profile: {e}")
        business_profile = {}

    try:
        facts_resp = supabase_client.table("verified_facts").select(
            "*, extracted_facts!inner(*)"
        ).eq("extracted_facts.project_id", project_id).execute()
        verified_facts = []
        for f in (facts_resp.data if facts_resp.data else []):
            ext = f.get("extracted_facts", {})
            verified_facts.append({
                "id": f.get("id"),
                "fact_type": ext.get("fact_category", "general"),
                "fact_value": ext.get("fact_value", ""),
                "fact_key": ext.get("fact_key", ""),
                "evidence": ext.get("evidence_text", ""),
                "confidence_score": float(f.get("verification_score", 100.0) / 100.0),
                "source_url": ext.get("source_url", "")
            })
    except Exception as e:
        logger.warning(f"Error fetching verified facts: {e}")
        verified_facts = []

    try:
        q_resp = supabase_client.table("questions").select("*").eq("project_id", project_id).execute()
        questions = q_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching questions: {e}")
        questions = []

    try:
        kw_resp = supabase_client.table("keywords").select("*").eq("project_id", project_id).execute()
        keywords = kw_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching keywords: {e}")
        keywords = []

    try:
        comp_resp = supabase_client.table("competitors").select("*").eq("project_id", project_id).execute()
        competitors = []
        for comp in (comp_resp.data if comp_resp.data else []):
            competitors.append({
                "id": comp.get("id"),
                "name": comp.get("competitor_name", ""),
                "competitor_name": comp.get("competitor_name", ""),
                "website_url": comp.get("website", ""),
                "competitor_type": comp.get("competitor_type", "direct"),
                "strengths": comp.get("strengths", []),
                "weaknesses": comp.get("weaknesses", []),
                "market_gaps": comp.get("content_gaps", []),
                "description": comp.get("description", ""),
                "unique_features": comp.get("unique_features", []),
                "reason_selected": comp.get("reason_selected", []),
                "similarity_score": comp.get("similarity_score", 50),
                "industry_match": comp.get("industry_match", ""),
                "audience_match": comp.get("audience_match", ""),
                "service_match": comp.get("service_match", "")
            })
    except Exception as e:
        logger.warning(f"Error fetching competitors: {e}")
        competitors = []

    try:
        cov_resp = supabase_client.table("content_coverage").select("*").eq("project_id", project_id).execute()
        content_coverage = cov_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching content coverage: {e}")
        content_coverage = []

    try:
        pages_resp = supabase_client.table("web_pages").select("url, title, content").eq("project_id", project_id).execute()
        crawled_pages = []
        for p in (pages_resp.data if pages_resp.data else []):
            crawled_pages.append({
                "url": p.get("url", ""),
                "title": p.get("title", ""),
                "content": p.get("content", "")
            })
    except Exception as e:
        logger.warning(f"Error fetching crawled pages: {e}")
        crawled_pages = []

    try:
        opps_resp = supabase_client.table("content_opportunities").select("*").eq("project_id", project_id).execute()
        content_opportunities = opps_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching content opportunities: {e}")
        content_opportunities = []

    try:
        blogs_resp = supabase_client.table("blogs").select("*").eq("project_id", project_id).execute()
        blogs = blogs_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching blogs: {e}")
        blogs = []

    try:
        nodes_resp = supabase_client.table("entity_nodes").select("*").eq("project_id", project_id).execute()
        entity_nodes = nodes_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching entity nodes: {e}")
        entity_nodes = []

    try:
        gap_resp = supabase_client.table("gap_analysis").select("*").eq("project_id", project_id).execute()
        gap_analysis = gap_resp.data or []
    except Exception as e:
        logger.warning(f"Error fetching gap analysis: {e}")
        gap_analysis = []

    return {
        "business_profile": business_profile,
        "verified_facts": verified_facts,
        "questions": questions,
        "keywords": keywords,
        "competitors": competitors,
        "content_coverage": content_coverage,
        "crawled_pages": crawled_pages,
        "content_opportunities": content_opportunities,
        "blogs": blogs,
        "entity_nodes": entity_nodes,
        "gap_analysis": gap_analysis
    }



@router.get("/recommendation-intelligence/{project_id}")
def get_recommendation_intelligence(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Runs recommendation confidence engine and returns V2 report, saving simulations."""
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Cache check (30 min TTL — heavy computation)
        cached = get_cached_data(project_id, "recommendation_intelligence")
        if cached is not None:
            return cached

        project_data = _get_project_data_payload(project_id)
        engine = RecommendationEngineV2()
        result = engine.run(project_data)

        # Persistence: Delete old simulations first
        try:
            supabase_client.table("recommendation_simulations_v2").delete().eq("project_id", project_id).execute()
        except Exception as db_err:
            logger.warning(f"Error cleaning up old recommendation simulations: {db_err}")

        # Insert new simulations
        sims_to_insert = []
        for sim in result.get("simulations", []):
            sims_to_insert.append({
                "project_id": project_id,
                "query": sim["query"],
                "recommendation_score": sim["recommendation_score"],
                "confidence": sim["confidence"],
                "evidence": sim["evidence"],
                "weaknesses": sim["weaknesses"],
                "missing_requirements": sim["missing_requirements"],
                "improvement_actions": sim["improvement_actions"],
                "competitor_advantages": sim["competitor_threats"],
                "signal_breakdown": sim["signal_breakdown"]
            })
        if sims_to_insert:
            try:
                supabase_client.table("recommendation_simulations_v2").insert(sims_to_insert).execute()
            except Exception as db_err:
                logger.error(f"Error storing recommendation simulations: {db_err}")

        set_cached_data(project_id, "recommendation_intelligence", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendation intelligence for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hallucination-report/{project_id}")
def get_hallucination_report(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Runs the hallucination detector on demand and returns the flag breakdown."""
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Cache check (30 min TTL — heavy computation)
        cached = get_cached_data(project_id, "hallucination_report")
        if cached is not None:
            return cached

        project_data = _get_project_data_payload(project_id)
        detector = HallucinationDetector()
        result = detector.detect(project_data)

        # Persistence: Delete old hallucination reports
        try:
            supabase_client.table("hallucination_reports").delete().eq("project_id", project_id).execute()
        except Exception as db_err:
            logger.warning(f"Error cleaning up old hallucination reports: {db_err}")

        # Insert new reports
        reports_to_insert = []
        for f in result.get("flags", []):
            reports_to_insert.append({
                "project_id": project_id,
                "item_type": f["item_type"],
                "item_text": f["item_text"],
                "flag_level": f["flag_level"],
                "supporting_evidence": f.get("supporting_evidence", "")
            })
        if reports_to_insert:
            try:
                supabase_client.table("hallucination_reports").insert(reports_to_insert).execute()
            except Exception as db_err:
                logger.error(f"Error storing hallucination reports: {db_err}")

        set_cached_data(project_id, "hallucination_report", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating hallucination report for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consistency-report/{project_id}")
def get_consistency_report(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Runs the cross-agent knowledge consistency engine and returns the contradictions/repair actions."""
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Cache check (30 min TTL — heavy computation)
        cached = get_cached_data(project_id, "consistency_report")
        if cached is not None:
            return cached

        project_data = _get_project_data_payload(project_id)
        engine = KnowledgeConsistencyEngine()
        result = engine.analyze(project_data)

        # Persistence: Delete old consistency reports
        try:
            supabase_client.table("knowledge_consistency_reports").delete().eq("project_id", project_id).execute()
        except Exception as db_err:
            logger.warning(f"Error cleaning up old knowledge consistency reports: {db_err}")

        # Insert new report
        try:
            supabase_client.table("knowledge_consistency_reports").insert({
                "project_id": project_id,
                "consistency_score": result["consistency_score"],
                "conflicts": result["conflicts"],
                "warnings": result["warnings"],
                "repair_actions": result["repair_actions"]
            }).execute()
        except Exception as db_err:
            logger.error(f"Error storing knowledge consistency report: {db_err}")

        set_cached_data(project_id, "consistency_report", result, ttl=1800)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating consistency report for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# BATCH 4.5 — REALITY CHECKER ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

class VerifyCheckRequest(BaseModel):
    chatgpt_mentions: str  # 'YES', 'NO', 'PARTIAL'
    gemini_mentions: str
    perplexity_mentions: str


@router.get("/reality-check/{project_id}")
def get_reality_checks(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Returns stored reality checks for a project, generating them if none exist."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        existing = supabase_client.table("reality_checks").select("*").eq("project_id", project_id).execute()
        if existing.data:
            return {"reality_checks": existing.data, "source": "stored"}

        # Generate fresh if none stored
        project_data = _get_project_data_payload(project_id)
        checker = RealityChecker()
        generated = checker.generate_queries(project_data)

        rows = [{**q, "project_id": project_id} for q in generated]
        try:
            supabase_client.table("reality_checks").insert(rows).execute()
        except Exception as db_err:
            logger.error(f"Error storing reality checks: {db_err}")

        stored = supabase_client.table("reality_checks").select("*").eq("project_id", project_id).execute()
        return {"reality_checks": stored.data or rows, "source": "generated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching reality checks for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reality-check/{project_id}/generate")
def generate_reality_checks(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Force regenerates 20 reality checks, replacing any existing ones."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        # Delete old
        try:
            supabase_client.table("reality_checks").delete().eq("project_id", project_id).execute()
        except Exception as db_err:
            logger.warning(f"Error cleaning old reality checks: {db_err}")

        project_data = _get_project_data_payload(project_id)
        checker = RealityChecker()
        generated = checker.generate_queries(project_data)

        rows = [{**q, "project_id": project_id} for q in generated]
        supabase_client.table("reality_checks").insert(rows).execute()

        stored = supabase_client.table("reality_checks").select("*").eq("project_id", project_id).execute()
        return {"reality_checks": stored.data or rows, "total": len(rows)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating reality checks for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/reality-check/{project_id}/verify/{check_id}")
def verify_reality_check(
    project_id: str,
    check_id: str,
    payload: VerifyCheckRequest,
    user_id: str = Depends(get_current_user)
):
    """Updates manual verification status for a single reality check row."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        allowed_values = {"YES", "NO", "PARTIAL"}
        for field, val in [
            ("chatgpt_mentions", payload.chatgpt_mentions),
            ("gemini_mentions", payload.gemini_mentions),
            ("perplexity_mentions", payload.perplexity_mentions),
        ]:
            if val.upper() not in allowed_values:
                raise HTTPException(status_code=422, detail=f"{field} must be YES, NO, or PARTIAL")

        update_resp = supabase_client.table("reality_checks").update({
            "chatgpt_mentions": payload.chatgpt_mentions.upper(),
            "gemini_mentions": payload.gemini_mentions.upper(),
            "perplexity_mentions": payload.perplexity_mentions.upper(),
            "is_verified": True,
        }).eq("id", check_id).eq("project_id", project_id).execute()

        return {"updated": bool(update_resp.data), "check_id": check_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying reality check {check_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reality-check/metrics/{project_id}")
def get_reality_check_metrics(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Calculates Accuracy, Precision, Recall, and Calibration Error from verified reality checks."""
    try:
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")

        checks_resp = supabase_client.table("reality_checks").select("*").eq("project_id", project_id).execute()
        checks = checks_resp.data or []

        checker = RealityChecker()
        metrics = checker.calculate_metrics(checks)
        metrics["total_checks"] = len(checks)
        metrics["verified_checks"] = sum(1 for c in checks if c.get("is_verified"))
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating reality check metrics for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# BATCH 4.5 — COMPETITOR BENCHMARK ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/reliability/{project_id}")
def get_reliability_report(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Fetches the latest reliability report, agent health, and recovery history for a project."""
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found or unauthorized access")
            
        # Fetch latest reliability report
        report_resp = supabase_client.table("reliability_reports")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        report = report_resp.data[0] if report_resp.data else {
            "reliability_score": 100.0,
            "success_rate": 100.0,
            "retry_success_rate": 100.0,
            "dependency_score": 100.0,
            "runtime_stability": 100.0,
            "pipeline_completion_score": 100.0,
            "recovery_success_rate": 100.0
        }
        
        # Fetch agent health logs for the latest run
        run_resp = supabase_client.table("analysis_runs")\
            .select("id")\
            .eq("project_id", project_id)\
            .order("started_at", desc=True)\
            .limit(1)\
            .execute()
            
        health_logs = []
        recovery_logs = []
        if run_resp.data:
            latest_run_id = run_resp.data[0]["id"]
            h_resp = supabase_client.table("agent_health_logs")\
                .select("*")\
                .eq("run_id", latest_run_id)\
                .order("created_at", desc=False)\
                .execute()
            health_logs = h_resp.data or []
            
            r_resp = supabase_client.table("recovery_history")\
                .select("*")\
                .eq("run_id", latest_run_id)\
                .order("timestamp", desc=True)\
                .execute()
            recovery_logs = r_resp.data or []
            
        return {
            "reliability_report": report,
            "agent_health_logs": health_logs,
            "recovery_history": recovery_logs
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching reliability report for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


