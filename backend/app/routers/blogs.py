from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import logging
import json
import random
from app.core.supabase import supabase_client
from app.core.dependencies import get_current_user
from app.core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blogs", tags=["blogs"])

class BlogGenerateRequest(BaseModel):
    project_id: str
    count: int # 10, 50, 100

class BlogOut(BaseModel):
    id: str
    project_id: str
    title: str
    outline: Optional[str]
    content: Optional[str]
    target_keywords: List[str]
    created_at: str

@router.get("/{project_id}", response_model=List[BlogOut])
def list_blogs(project_id: str, user_id: str = Depends(get_current_user)):
    """Lists all previously generated blogs for the project, verifying ownership."""
    try:
        # Check project ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )
            
        blogs_resp = supabase_client.table("blogs").select("*").eq("project_id", project_id).order("created_at", desc=True).execute()
        return blogs_resp.data if blogs_resp.data else []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching blogs: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@router.post("/generate", response_model=List[BlogOut])
def generate_blogs(request: BlogGenerateRequest, user_id: str = Depends(get_current_user)):
    """Generates 10, 50, or 100 blog posts on demand based on verified facts."""
    project_id = request.project_id
    count = request.count
    if count not in [10, 50, 100]:
        raise HTTPException(status_code=400, detail="Count must be exactly 10, 50, or 100.")

    try:
        # Check project ownership
        proj_resp = supabase_client.table("projects").select("id, project_name, website_url").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )
        project = proj_resp.data[0]

        # Fetch verified facts
        facts_resp = supabase_client.table("verified_facts").select(
            "*, extracted_facts!inner(*)"
        ).eq("extracted_facts.project_id", project_id).execute()
        
        facts_list = []
        for f in (facts_resp.data if facts_resp.data else []):
            ext = f.get("extracted_facts", {})
            facts_list.append({
                "category": ext.get("fact_category"),
                "key": ext.get("fact_key"),
                "value": ext.get("fact_value")
            })

        # Fetch keywords for targeting
        kw_resp = supabase_client.table("keywords").select("keyword").eq("project_id", project_id).limit(10).execute()
        keywords_pool = [k["keyword"] for k in kw_resp.data] if kw_resp.data else ["AI SEO", "Visibility Optimization"]

        # Call LLM to generate 4-5 high quality seed blog post concepts
        llm = get_llm()
        prompt_template = ChatPromptTemplate.from_template("""You are an expert Copywriting Agent.
Based on the following company details and verified facts, generate 5 distinct, high-quality blog post titles and outline structures.

Company: {company_name}
Facts:
{facts_json}

For each blog post provide:
- title: A search-optimized title.
- outline: 3 main headers (H2s).
- target_keywords: 2-3 keywords that this post targets.
- content_summary: A 2-sentence summary of the post's core message.

Format your response as a valid JSON array of objects. Do not wrap in markdown code blocks. Format:
[
  {{
    "title": "Why CRM Security is Essential for Startups",
    "outline": "H2: The Growing Threat landscape; H2: How CRM Encrypts Data; H2: Best Practices for CRM Configuration",
    "target_keywords": ["CRM Security", "Startup CRM features"],
    "content_summary": "This article discusses security considerations startups must make when choosing their CRM platform."
  }}
]
""")
        formatted = prompt_template.format_messages(
            company_name=project["project_name"],
            facts_json=json.dumps(facts_list[:15], indent=2)
        )
        response = llm.invoke(formatted)
        resp_text = response.content.strip()
        if resp_text.startswith("```json"):
            resp_text = resp_text[7:]
        if resp_text.endswith("```"):
            resp_text = resp_text[:-3]
        resp_text = resp_text.strip()
        
        seeds = json.loads(resp_text)
        if not seeds:
            raise ValueError("LLM generated no seed blogs.")

        # Expand programmatically to reach 'count'
        all_blogs_to_insert = []
        blog_types = [
            "Complete Guide to", "Top 10 Tips for", "How to Optimize", "The Ultimate Checklist for",
            "Why You Need to Understand", "Case Study:", "Comparing the Best Solutions for",
            "Beginner Guide:", "Advanced Strategies for", "What is the Future of"
        ]
        
        # Add seeds first
        for i, s in enumerate(seeds):
            all_blogs_to_insert.append({
                "project_id": project_id,
                "title": s["title"],
                "outline": s["outline"],
                "content": s["content_summary"],
                "target_keywords": s["target_keywords"]
            })

        # Multipliers
        random.seed(42)
        while len(all_blogs_to_insert) < count:
            seed = random.choice(seeds)
            b_type = random.choice(blog_types)
            kw = random.choice(keywords_pool)
            
            # Formulate title
            title = f"{b_type} {kw}"
            # Ensure unique title
            if any(b["title"] == title for b in all_blogs_to_insert):
                title = f"{b_type} {kw} ({len(all_blogs_to_insert) + 1})"
                
            outline = f"H2: Introduction to {kw}; H2: Why {kw} matters for {project['project_name']}; H2: Implementation Checklist; H2: Conclusion"
            summary = f"An in-depth article discussing {kw} strategies and visibility optimization tips specifically for {project['project_name']}."
            
            all_blogs_to_insert.append({
                "project_id": project_id,
                "title": title,
                "outline": outline,
                "content": summary,
                "target_keywords": [kw] + seed.get("target_keywords", [])[:1]
            })

        # Insert to DB
        insert_resp = supabase_client.table("blogs").insert(all_blogs_to_insert[:count]).execute()
        if not insert_resp.data:
            raise HTTPException(status_code=500, detail="Failed to insert generated blogs into database.")
            
        # Log activity
        supabase_client.table("activity_logs").insert({
            "project_id": project_id,
            "user_id": user_id,
            "action": "blogs_generated",
            "metadata": {"count": count, "description": f"Generated {count} blogs on demand."}
        }).execute()
        
        return insert_resp.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Blog Generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate blogs: {str(e)}")
