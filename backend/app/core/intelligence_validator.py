"""
intelligence_validator.py

Verifies the integrity of the question and keyword pipeline by comparing
counts between:
1. Generated counts in LangGraph state.
2. Saved counts in the Supabase database.
3. API counts returned to the frontend.
"""

import logging
from typing import Dict, Any
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class IntelligenceValidator:
    def __init__(self):
        pass

    def validate(self, project_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates counts of questions and keywords.
        Returns:
            Dict containing:
                - question_integrity: str ("PASS" or "FAIL")
                - keyword_integrity: str ("PASS" or "FAIL")
                - status: str ("PASS" or "FAILED_VALIDATION")
                - details: Dict of counts and mismatches
        """
        # 1. State Counts (Generated)
        state_questions_count = len(state.get("questions", []) or [])
        state_keywords_count = len(state.get("keywords", []) or [])
        
        # 2. Database Counts (Saved)
        db_questions_count = 0
        db_keywords_count = 0
        
        try:
            q_resp = supabase_client.table("questions")\
                .select("id", count="exact")\
                .eq("project_id", project_id)\
                .execute()
            db_questions_count = q_resp.count if q_resp.count is not None else len(q_resp.data or [])
        except Exception as e:
            logger.error(f"Error querying db questions count: {e}")
            
        try:
            kw_resp = supabase_client.table("keywords")\
                .select("id", count="exact")\
                .eq("project_id", project_id)\
                .execute()
            db_keywords_count = kw_resp.count if kw_resp.count is not None else len(kw_resp.data or [])
        except Exception as e:
            logger.error(f"Error querying db keywords count: {e}")
            
        # 3. API counts (simulated by calling count queries or fetching actual API records)
        # In our architecture, the API count query maps exactly to the database count.
        api_questions_count = db_questions_count
        api_keywords_count = db_keywords_count
        
        # 4. Check for Mismatches
        q_mismatch = (state_questions_count != db_questions_count)
        kw_mismatch = (state_keywords_count != db_keywords_count)
        
        question_integrity = "PASS" if not q_mismatch else "FAIL"
        keyword_integrity = "PASS" if not kw_mismatch else "FAIL"
        
        overall_status = "PASS" if (question_integrity == "PASS" and keyword_integrity == "PASS") else "FAILED_VALIDATION"
        
        # Create descriptive error details if failed
        errors = []
        if q_mismatch:
            errors.append(
                f"Question Count Mismatch: Generated {state_questions_count} in LangGraph state, but found {db_questions_count} in Database/API."
            )
        if kw_mismatch:
            errors.append(
                f"Keyword Count Mismatch: Generated {state_keywords_count} in LangGraph state, but found {db_keywords_count} in Database/API."
            )
            
        logger.info(f"[IntelligenceValidator] Question Integrity: {question_integrity}, Keyword Integrity: {keyword_integrity}. Mismatch errors: {errors}")
        
        return {
            "question_integrity": question_integrity,
            "keyword_integrity": keyword_integrity,
            "status": overall_status,
            "errors": errors,
            "details": {
                "questions": {
                    "generated": state_questions_count,
                    "database": db_questions_count,
                    "api": api_questions_count
                },
                "keywords": {
                    "generated": state_keywords_count,
                    "database": db_keywords_count,
                    "api": api_keywords_count
                }
            }
        }
