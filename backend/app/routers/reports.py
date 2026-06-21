from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from typing import List, Dict, Any, Optional
from app.core.supabase import supabase_client
from app.core.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/{project_id}")
def list_reports(project_id: str, user_id: str = Depends(get_current_user)):
    """Lists all generated intelligence reports for a project."""
    try:
        # Check ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )
            
        reports = supabase_client.table("reports").select("id, report_title, generated_at").eq("project_id", project_id).execute()
        
        mapped_reports = []
        for r in (reports.data if reports.data else []):
            mapped_reports.append({
                "id": r["id"],
                "title": r.get("report_title", ""),
                "created_at": r.get("generated_at", "")
            })
        return mapped_reports
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@router.get("/{project_id}/latest")
def get_latest_report(project_id: str, user_id: str = Depends(get_current_user)):
    """Retrieves the latest generated package report for the project."""
    try:
        # Check ownership
        proj_resp = supabase_client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute()
        if not proj_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Project not found or unauthorized access"
            )
            
        reports = supabase_client.table("reports").select("*").eq("project_id", project_id).order("generated_at", desc=True).limit(1).execute()
        if not reports.data:
            raise HTTPException(
                status_code=404,
                detail="No reports found for this project. Please run an analysis first."
            )
        r = reports.data[0]
        return {
            "id": r["id"],
            "project_id": r["project_id"],
            "title": r.get("report_title", ""),
            "content": r.get("report_content", {}),
            "created_at": r.get("generated_at", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latest report: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@router.get("/download/{report_id}/{format}")
def download_report(report_id: str, format: str, user_id: str = Depends(get_current_user)):
    """Exports and downloads the report in Markdown, JSON, or Text representation."""
    try:
        # Check project ownership of the report
        response = supabase_client.table("reports").select(
            "*, projects!inner(user_id, website_url)"
        ).eq("id", report_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )
            
        report_data = response.data[0]
        if report_data["projects"]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
            
        content = report_data["report_content"]
        website_url = report_data["projects"]["website_url"]
        
        if format.lower() == "json":
            return content
            
        # Export as clean formatted Markdown
        markdown_output = f"""# AI Visibility Optimization Report
**Target Website**: {website_url}
**Industry**: {content.get('industry', 'Other')}
**Verified Facts Analyzed**: {content.get('total_verified_facts', 0)}
**AI Questions Discovered**: {content.get('total_questions_discovered', 0)}
**Keywords Clusters**: {content.get('total_keywords_strategized', 0)}

---

## 1. Executive Summary
{content.get('executive_summary', '')}

## 2. Business Overview
{content.get('business_overview', '')}

## 3. Product Analysis
{content.get('product_analysis', '')}

## 4. Service Analysis
{content.get('service_analysis', '')}

## 5. Trust & Authority Analysis
{content.get('trust_analysis', '')}

## 6. SWOT Matrix
* **Strengths**: {", ".join(content.get('swot', {}).get('strengths', []))}
* **Weaknesses**: {", ".join(content.get('swot', {}).get('weaknesses', []))}
* **Opportunities**: {", ".join(content.get('swot', {}).get('opportunities', []))}
* **Threats**: {", ".join(content.get('swot', {}).get('threats', []))}

## 7. AI Recommendation Engines Visibility Gaps
{content.get('ai_visibility_analysis', '')}
"""
        
        return PlainTextResponse(markdown_output.strip())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        raise HTTPException(status_code=500, detail="Failed to compile download file")
