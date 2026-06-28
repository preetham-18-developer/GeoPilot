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


@router.get("/questions/{project_id}")
def get_analysis_questions(
    project_id: str,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    question_type: Optional[str] = None,
    sort_by: str = "priority_score",
    sort_order: str = "desc",
    user_id: str = Depends(get_current_user)
):
    """Retrieves paginated, filtered, and searched questions for a project."""
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Cache lookup — keyed by all filter/sort/page parameters
        # Only use cache for the default un-filtered first page (common dashboard load)
        if not search and not question_type and page == 1 and page_size == 10 and sort_by == "priority_score" and sort_order == "desc":
            cached = get_cached_data(project_id, "questions_page1")
            if cached is not None:
                return cached
            
        # Build base query with exact count
        query = supabase_client.table("questions").select("*", count="exact").eq("project_id", project_id)
        
        if question_type and question_type != "All":
            query = query.eq("question_type", question_type)
            
        if search:
            query = query.ilike("question", f"%{search}%")
            
        # Map sort key if needed (default to priority_score)
        valid_sorts = {
            "question": "question",
            "question_text": "question",
            "category": "question_type",
            "question_type": "question_type",
            "intent": "intent",
            "confidence_score": "confidence_score",
            "priority": "priority_score",
            "priority_score": "priority_score",
            "recommendation_score": "recommendation_score",
            "commercial_score": "commercial_score",
            "intent_score": "intent_score",
            "difficulty_estimate": "difficulty_estimate",
            "opportunity_estimate": "opportunity_estimate"
        }
        db_sort_by = valid_sorts.get(sort_by, "priority_score")
        
        # Apply sorting
        desc = (sort_order.lower() == "desc")
        query = query.order(db_sort_by, desc=desc)
        
        # Pagination range
        start = (page - 1) * page_size
        end = start + page_size - 1
        
        resp = query.range(start, end).execute()
        
        mapped_questions = []
        for q in (resp.data if resp.data else []):
            mapped_questions.append({
                "id": q["id"],
                "category": q.get("question_type", "General"),
                "question_text": q.get("question", ""),
                "recommended_answer": q.get("recommended_answer", ""),
                "intent": q.get("intent", ""),
                "confidence_score": q.get("confidence_score", 1.0),
                "priority": q.get("priority", "Medium"),
                "recommendation_score": q.get("recommendation_score", 0.0),
                "commercial_score": q.get("commercial_score", 0.0),
                "intent_score": q.get("intent_score", 0.0),
                "priority_score": q.get("priority_score", 0.0),
                "difficulty_estimate": q.get("difficulty_estimate", "Medium"),
                "opportunity_estimate": q.get("opportunity_estimate", "Medium")
            })
            
        result = {
            "questions": mapped_questions,
            "total_count": resp.count or 0,
            "page": page,
            "page_size": page_size
        }
        # Cache the default first page only
        if not search and not question_type and page == 1 and page_size == 10 and sort_by == "priority_score" and sort_order == "desc":
            set_cached_data(project_id, "questions_page1", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching questions: {e}")
        raise HTTPException(status_code=500, detail="Database error")


