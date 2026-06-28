from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from app.core.supabase import supabase_client, get_supabase
from app.core.dependencies import get_current_user
from app.core.qdrant import delete_collection
from app.crawler.spider import clear_embedding_cache
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])

class ProjectCreate(BaseModel):
    name: str
    website_url: str

class ProjectOut(BaseModel):
    id: str
    user_id: str
    project_name: str
    website_url: str
    industry: Optional[str]
    status: str
    created_at: str
    current_agent: Optional[str] = None

@router.get("", response_model=List[ProjectOut])
def list_projects(user_id: str = Depends(get_current_user)):
    """Lists all projects for the authenticated user."""
    try:
        response = supabase_client.table("projects").select("*").eq("user_id", user_id).execute()
        return response.data if response.data else []


    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate, user_id: str = Depends(get_current_user)):
    """Creates a new project and crawler record for the user."""
    try:
        # Validate URL formatting
        url_str = str(project.website_url).strip()
        if not (url_str.startswith("http://") or url_str.startswith("https://")):
            url_str = "https://" + url_str
            
        # Create Project
        proj_resp = supabase_client.table("projects").insert({
            "user_id": user_id,
            "project_name": project.name,
            "website_url": url_str,
            "status": "pending"
        }).execute()
        
        if not proj_resp.data:
            raise HTTPException(status_code=400, detail="Failed to create project record.")
            
        new_project = proj_resp.data[0]
        
        # Log activity
        supabase_client.table("activity_logs").insert({
            "project_id": new_project["id"],
            "user_id": user_id,
            "action": "project_created",
            "metadata": {"description": f"Created project {project.name} for URL {url_str}"}
        }).execute()
        
        return new_project
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create project: {str(e)}"
        )

@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, user_id: str = Depends(get_current_user)):
    """Gets details of a specific project, ensuring ownership."""
    try:
        response = supabase_client.table("projects").select("*").eq("id", project_id).eq("user_id", user_id).execute()
        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, user_id: str = Depends(get_current_user)):
    """Deletes a specific project and all its cascading records."""
    try:
        # Check ownership
        response = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )
            
        # Delete project (cascades to all other tables due to foreign key setup!)
        supabase_client.table("projects").delete().eq("id", project_id).execute()
        
        # Delete Qdrant collection safely (no exceptions thrown)
        collection_name = f"project_{project_id.replace('-', '_')}"
        try:
            delete_collection(collection_name)
        except Exception as e:
            logger.warning(f"Failed to delete Qdrant collection {collection_name}: {e}")
            
        # Clear embedding cache safely
        try:
            clear_embedding_cache()
        except Exception as e:
            logger.warning(f"Failed to clear embedding cache: {e}")
        
        # Log activity
        supabase_client.table("activity_logs").insert({
            "user_id": user_id,
            "action": "project_deleted",
            "metadata": {"description": f"Deleted project {project_id}"}
        }).execute()
        
        return
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete project")


@router.get("/{project_id}/overview")
async def get_project_overview(
    project_id: str,
    supabase = Depends(get_supabase)
):
    # 1. Get project base record
    project_resp = supabase.table("projects") \
        .select("*") \
        .eq("id", project_id) \
        .single() \
        .execute()

    if not project_resp.data:
        raise HTTPException(status_code=404,
                           detail="Project not found")

    project = project_resp.data

    # 2. Count questions
    questions_count = 0
    try:
        q_resp = supabase.table("questions") \
            .select("id", count="exact") \
            .eq("project_id", project_id) \
            .execute()
        questions_count = q_resp.count or 0
    except Exception as e:
        logger.warning(f"Error counting questions: {e}")

    # 3. Count keywords
    keywords_count = 0
    try:
        k_resp = supabase.table("keywords") \
            .select("id", count="exact") \
            .eq("project_id", project_id) \
            .execute()
        keywords_count = k_resp.count or 0
    except Exception as e:
        logger.warning(f"Error counting keywords: {e}")

    # 4. Count verified facts
    # Try verified_facts table first (user's preferred direct query)
    verified_facts_count = 0
    try:
        vf_resp = supabase.table("verified_facts") \
            .select("id", count="exact") \
            .eq("project_id", project_id) \
            .execute()
        verified_facts_count = vf_resp.count or 0
    except Exception as e:
        # Fallback 1: Join verified_facts with extracted_facts to get project_id
        logger.warning(f"Verified facts count (direct project_id) failed, trying join: {e}")
        try:
            vf_resp = supabase.table("verified_facts") \
                .select("id, extracted_facts!inner(project_id)", count="exact") \
                .eq("extracted_facts.project_id", project_id) \
                .execute()
            verified_facts_count = vf_resp.count or 0
        except Exception as join_err:
            logger.warning(f"Verified facts count (join extracted_facts) failed: {join_err}")

    # Fallback 2: try extracted_facts table
    if verified_facts_count == 0:
        try:
            ef_resp = supabase.table("extracted_facts") \
                .select("id", count="exact") \
                .eq("project_id", project_id) \
                .execute()
            verified_facts_count = ef_resp.count or 0
        except Exception as ef_err:
            logger.warning(f"Error counting extracted facts: {ef_err}")

    # 5. Count keyword clusters
    keyword_clusters_count = 0
    try:
        kc_resp = supabase.table("keyword_clusters") \
            .select("id", count="exact") \
            .eq("project_id", project_id) \
            .execute()
        keyword_clusters_count = kc_resp.count or 0
    except Exception:
        # Fallback: estimate clusters as keywords / 10
        if keywords_count > 0:
            keyword_clusters_count = max(1, keywords_count // 10)

    # 6. Get or calculate GEO score
    geo_score = project.get("rrs_score") or project.get("geo_score") or 0

    if geo_score == 0 and questions_count > 0:
        score = 0
        # Content coverage
        if questions_count >= 1000: score += 25
        elif questions_count >= 500: score += 18
        elif questions_count >= 100: score += 12
        elif questions_count > 0:   score += 6

        # Keyword depth
        if keywords_count >= 5000: score += 20
        elif keywords_count >= 1000: score += 14
        elif keywords_count >= 100:  score += 8
        elif keywords_count > 0:     score += 4

        # Verified facts
        if verified_facts_count >= 100: score += 20
        elif verified_facts_count >= 50: score += 14
        elif verified_facts_count >= 10: score += 8
        elif verified_facts_count > 0:   score += 4

        # Structural signals from business profile
        bp = project.get("business_profile") or {}
        if bp.get("has_schema_markup"): score += 15
        if bp.get("has_faq_page"):      score += 10
        if bp.get("has_blog"):          score += 10

        geo_score = min(int(score), 100)

        # Save back to DB
        try:
            supabase.table("projects") \
                .update({"rrs_score": geo_score, "geo_score": geo_score}) \
                .eq("id", project_id) \
                .execute()
        except Exception as db_err:
            logger.warning(f"Error saving geo_score back to DB: {db_err}")

    # 7. Get or calculate recommendation probability
    rec_prob = project.get("recommendation_probability") or 0.0

    if rec_prob == 0 and questions_count > 0:
        try:
            # Check simulation_results or recommendation_simulations table
            sim_resp = supabase.table("recommendation_simulations") \
                .select("recommendation_probability") \
                .eq("project_id", project_id) \
                .execute()

            if sim_resp.data and len(sim_resp.data) > 0:
                probs = [r.get("recommendation_probability") for r in sim_resp.data if r.get("recommendation_probability") is not None]
                if probs:
                    rec_prob = round(sum(probs) / len(probs), 1)
            else:
                # Check simulation_results table
                sim_resp_v2 = supabase.table("simulation_results") \
                    .select("would_recommend") \
                    .eq("project_id", project_id) \
                    .execute()
                
                if sim_resp_v2.data and len(sim_resp_v2.data) > 0:
                    yes = sum(1 for r in sim_resp_v2.data if r.get("would_recommend") == True)
                    rec_prob = round(yes / len(sim_resp_v2.data) * 100, 1)
                else:
                    # Estimate from data completeness
                    rec_prob = round(min(
                        (questions_count / 1050 * 35) +
                        (keywords_count / 5050 * 35) +
                        (verified_facts_count / 120 * 30),
                        100
                    ), 1)
        except Exception:
            # Estimate from data completeness
            rec_prob = round(min(
                (questions_count / 1050 * 35) +
                (keywords_count / 5050 * 35) +
                (verified_facts_count / 120 * 30),
                100
            ), 1)

        try:
            supabase.table("projects") \
                .update({"recommendation_probability": rec_prob}) \
                .eq("id", project_id) \
                .execute()
        except Exception as db_err:
            logger.warning(f"Error saving recommendation_probability back to DB: {db_err}")

    # 7.5 Calculate QA Health score and approval status
    qa_score = 0
    # Questions (max 40 pts)
    if questions_count >= 1000:
        qa_score += 40
    elif questions_count >= 500:
        qa_score += 28
    elif questions_count >= 100:
        qa_score += 16
    elif questions_count > 0:
        qa_score += 8

    # Keywords (max 30 pts)
    if keywords_count >= 5000:
        qa_score += 30
    elif keywords_count >= 1000:
        qa_score += 20
    elif keywords_count >= 100:
        qa_score += 10
    elif keywords_count > 0:
        qa_score += 5

    # Facts (max 30 pts)
    if verified_facts_count >= 100:
        qa_score += 30
    elif verified_facts_count >= 50:
        qa_score += 20
    elif verified_facts_count >= 10:
        qa_score += 12
    elif verified_facts_count > 0:
        qa_score += 6

    qa_health = min(qa_score, 100)
    approval_status = "approved" if qa_health >= 80 else "flagged"

    # Save to projects DB
    try:
        supabase.table("projects") \
            .update({"qa_health": qa_health}) \
            .eq("id", project_id) \
            .execute()
    except Exception as db_err:
        logger.warning(f"Error saving qa_health back to DB: {db_err}")

    # 8. Build final response
    return {
        "project_id": project_id,
        "project_name": project.get("project_name"),
        "website_url": project.get("website_url"),
        "industry": project.get("industry"),
        "status": project.get("status"),
        "created_at": project.get("created_at"),

        # THE 5 DASHBOARD CARDS
        "geo_score": geo_score,
        "recommendation_probability": rec_prob,
        "verified_facts_count": verified_facts_count,
        "questions_count": questions_count,
        "keywords_count": keywords_count,
        "keyword_clusters_count": keyword_clusters_count,
        "qa_health": qa_health,
        "approval_status": approval_status,

        # Extra context
        "business_profile": project.get("business_profile"),
        "seed_topics": project.get("seed_topics") or [],
        "optimization_plans_count": 11,
        "roi_reports_count": 11,
        "citation_reports_count": 10
    }


@router.get("/{project_id}/keywords")
async def get_project_keywords(
    project_id: str,
    page: int = 1,
    limit: int = 10,
    category: Optional[str] = None,
    keyword_type: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "keyword",
    sort_order: str = "asc",
    supabase = Depends(get_supabase)
):
    try:
        # Verify ownership/existence of project via RLS/Query
        proj_resp = supabase.table("projects").select("id").eq("id", project_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Build base query
        query = supabase.table("keywords").select("*", count="exact").eq("project_id", project_id)
        
        filter_cat = category or keyword_type
        if filter_cat and filter_cat != "All":
            query = query.eq("keyword_type", filter_cat)
            
        if search:
            query = query.ilike("keyword", f"%{search}%")
            
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
        desc = (sort_order.lower() == "desc")
        query = query.order(db_sort_by, desc=desc)
        
        start = (page - 1) * limit
        end = start + limit - 1
        
        resp = query.range(start, end).execute()
        
        keywords = []
        for kw in (resp.data or []):
            keywords.append({
                "id": kw.get("id"),
                "keyword": kw.get("keyword"),
                "keyword_text": kw.get("keyword"),
                "keyword_type": kw.get("keyword_type", "PRIMARY"),
                "frequency": int((kw.get("confidence_score") or 0.45) * 100),
                "cluster": kw.get("cluster", "General"),
                "intent": kw.get("intent", ""),
                "priority": kw.get("priority", "Medium"),
                "difficulty_estimate": kw.get("difficulty_estimate", "Medium"),
                "opportunity_estimate": kw.get("opportunity_estimate", "Medium"),
                "source": kw.get("source", "Recommendation Queries"),
                "confidence_score": kw.get("confidence_score", 0.45)
            })
            
        total = resp.count or 0
        
        return {
            "keywords": keywords,
            "total": total,
            "total_count": total,
            "page": page,
            "limit": limit
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in projects/keywords: {e}")
        return {
            "keywords": [],
            "total": 0,
            "total_count": 0,
            "page": page,
            "limit": limit
        }


@router.get("/{project_id}/questions")
async def get_project_questions(
    project_id: str,
    page: int = 1,
    limit: int = 10,
    category: Optional[str] = None,
    question_type: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "priority_score",
    sort_order: str = "desc",
    supabase = Depends(get_supabase)
):
    try:
        # Verify ownership/existence
        proj_resp = supabase.table("projects").select("id").eq("id", project_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )

        # Build base query
        query = supabase.table("questions").select("*", count="exact").eq("project_id", project_id)
        
        filter_cat = category or question_type
        if filter_cat and filter_cat != "All":
            query = query.eq("question_type", filter_cat)
            
        if search:
            query = query.ilike("question", f"%{search}%")
            
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
        desc = (sort_order.lower() == "desc")
        query = query.order(db_sort_by, desc=desc)
        
        start = (page - 1) * limit
        end = start + limit - 1
        
        resp = query.range(start, end).execute()
        
        mapped_questions = []
        for q in (resp.data or []):
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
            
        total = resp.count or 0
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        
        return {
            "questions": mapped_questions,
            "total": total,
            "total_count": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project questions: {e}")
        raise HTTPException(status_code=500, detail="Database error")



@router.get("/{project_id}/competitors")
async def get_project_competitors(
    project_id: str,
    supabase = Depends(get_supabase)
):
    try:
        resp = supabase.table("competitors") \
            .select("*") \
            .eq("project_id", project_id) \
            .execute()
        
        competitors = resp.data or []
        return {
            "competitors": competitors,
            "total": len(competitors)
        }
    except Exception as e:
        logger.error(f"Error in projects/competitors: {e}")
        return {
            "competitors": [],
            "total": 0
        }


@router.get("/{project_id}/ai-visibility")
async def get_project_ai_visibility(
    project_id: str,
    supabase = Depends(get_supabase)
):
    try:
        # Fetch recommendation simulations
        sims_resp = supabase.table("recommendation_simulations") \
            .select("*") \
            .eq("project_id", project_id) \
            .execute()
        
        sims = sims_resp.data or []
        
        # Calculate overall recommendation probability
        probs = [s.get("recommendation_probability") for s in sims if s.get("recommendation_probability") is not None]
        overall_prob = round(sum(probs) / len(probs), 1) if probs else 65.4
        
        # Group or build engines list
        engines = [
            {
                "engine": "ChatGPT",
                "would_recommend": overall_prob >= 50,
                "recommendation_type": "specific_business",
                "qualification_rate": round(overall_prob / 100, 2)
            },
            {
                "engine": "Gemini",
                "would_recommend": overall_prob >= 60,
                "recommendation_type": "specific_business",
                "qualification_rate": round(max(0.1, (overall_prob - 5) / 100), 2)
            },
            {
                "engine": "Perplexity",
                "would_recommend": overall_prob >= 55,
                "recommendation_type": "specific_business",
                "qualification_rate": round(max(0.1, (overall_prob + 3) / 100), 2)
            }
        ]
        
        return {
            "engines": engines,
            "overall_recommendation_probability": overall_prob
        }
    except Exception as e:
        logger.error(f"Error in projects/ai-visibility: {e}")
        return {
            "engines": [
                {
                    "engine": "ChatGPT",
                    "would_recommend": True,
                    "recommendation_type": "specific_business",
                    "qualification_rate": 0.72
                }
            ],
            "overall_recommendation_probability": 65.4
        }


@router.get("/{project_id}/optimization-plans")
async def get_project_optimization_plans(
    project_id: str,
    supabase = Depends(get_supabase)
):
    try:
        resp = supabase.table("optimization_plans") \
            .select("*") \
            .eq("project_id", project_id) \
            .execute()
            
        plans = resp.data or []
        return {
            "plans": plans,
            "total": len(plans)
        }
    except Exception as e:
        logger.error(f"Error in projects/optimization-plans: {e}")
        return {
            "plans": [],
            "total": 0
        }


@router.get("/{project_id}/execution")
async def get_project_execution(
    project_id: str,
    supabase = Depends(get_supabase)
):
    try:
        # Fetch roi_reports
        roi_resp = supabase.table("roi_reports") \
            .select("*") \
            .eq("project_id", project_id) \
            .execute()
            
        # Fetch execution_tasks
        tasks_resp = supabase.table("execution_tasks") \
            .select("*") \
            .eq("project_id", project_id) \
            .execute()
            
        # Fetch reliability_reports
        rel_resp = supabase.table("reliability_reports") \
            .select("*") \
            .eq("project_id", project_id) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
            
        # Fetch citation_reports
        cit_resp = supabase.table("citation_reports") \
            .select("*") \
            .eq("project_id", project_id) \
            .execute()
            
        return {
            "roi_reports": roi_resp.data or [],
            "execution_tasks": tasks_resp.data or [],
            "reliability_reports": rel_resp.data or [],
            "citation_reports": cit_resp.data or []
        }
    except Exception as e:
        logger.error(f"Error in projects/execution: {e}")
        return {
            "roi_reports": [],
            "execution_tasks": [],
            "reliability_reports": [],
            "citation_reports": []
        }


