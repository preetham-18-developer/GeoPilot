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


@router.get("/keywords/{project_id}")
def get_analysis_keywords(
    project_id: str,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    keyword_type: Optional[str] = None,
    sort_by: str = "keyword",
    sort_order: str = "asc",
    user_id: str = Depends(get_current_user)
):
    """Retrieves paginated, filtered, and searched keywords for a project."""
    try:
        # Verify ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Cache lookup — keyed on default un-filtered first page load
        if not search and not keyword_type and page == 1 and page_size == 10 and sort_by == "keyword" and sort_order == "asc":
            cached = get_cached_data(project_id, "keywords_page1")
            if cached is not None:
                return cached

        # Build base query with exact count
        query = supabase_client.table("keywords").select("*", count="exact").eq("project_id", project_id)
        
        if keyword_type and keyword_type != "All":
            query = query.eq("keyword_type", keyword_type)
            
        if search:
            query = query.ilike("keyword", f"%{search}%")
            
        # Map sort key if needed (default to keyword)
        valid_sorts = {
            "keyword": "keyword",
            "keyword_text": "keyword",
            "category": "keyword_type",
            "keyword_type": "keyword_type",
            "search_intent": "intent",
            "intent": "intent",
            "clustering_theme": "cluster",
            "cluster": "cluster",
            "confidence_score": "confidence_score",
            "priority": "priority",
            "difficulty_estimate": "difficulty_estimate",
            "opportunity_estimate": "opportunity_estimate",
            "source": "source"
        }
        db_sort_by = valid_sorts.get(sort_by, "keyword")
        
        # Apply sorting
        desc = (sort_order.lower() == "desc")
        query = query.order(db_sort_by, desc=desc)
        
        # Pagination range
        start = (page - 1) * page_size
        end = start + page_size - 1
        
        resp = query.range(start, end).execute()
        
        mapped_keywords = []
        for kw in (resp.data if resp.data else []):
            mapped_keywords.append({
                "id": kw["id"],
                "keyword_text": kw.get("keyword", ""),
                "category": kw.get("keyword_type", "General"),
                "search_intent": kw.get("intent", ""),
                "clustering_theme": kw.get("cluster", "General"),
                "priority": kw.get("priority", "Medium"),
                "difficulty_estimate": kw.get("difficulty_estimate", "Medium"),
                "opportunity_estimate": kw.get("opportunity_estimate", "Medium"),
                "source": kw.get("source", "Recommendation Queries")
            })
            
        result = {
            "keywords": mapped_keywords,
            "total_count": resp.count or 0,
            "page": page,
            "page_size": page_size
        }
        # Cache the default first page only
        if not search and not keyword_type and page == 1 and page_size == 10 and sort_by == "keyword" and sort_order == "asc":
            set_cached_data(project_id, "keywords_page1", result, ttl=3600)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching keywords: {e}")
        raise HTTPException(status_code=500, detail="Database error")



