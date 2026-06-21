from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from app.core.supabase import supabase_client
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
