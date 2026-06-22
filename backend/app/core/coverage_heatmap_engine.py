"""
coverage_heatmap_engine.py
Phase 6 — Coverage Heatmap Engine

Categorizes questions into 20 distinct query categories.
Computes coverage percentages, strong/weak areas, and priorities for each category.
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class CoverageHeatmapEngine:
    """
    Measures search query category coverages based on intent analysis.
    """

    CATEGORIES = {
        "Direct": ["who is", "what is", "about", "profile", "contact", "phone", "email"],
        "Problem": ["error", "fail", "issue", "bug", "broken", "trouble", "solve", "how to fix", "workaround"],
        "Outcome": ["benefit", "result", "roi", "improve", "increase", "grow", "success", "performance", "speed"],
        "Solution": ["software", "tool", "platform", "service", "system", "consultant", "agency", "provider"],
        "Decision": ["vs", "compare", "comparison", "alternative", "best", "review", "rating", "rank"],
        "Voice": ["hey", "can you", "tell me", "please", "recom", "suggest"],
        "Trust": ["certif", "secure", "safe", "compliance", "award", "trust", "guarantee", "policy"],
        "Urgent": ["fast", "quick", "instant", "immediate", "now", "emergency", "rapid"],
        "Budget": ["cost", "price", "pricing", "cheap", "affordable", "free", "discount", "expense"],
        "Beginner": ["easy", "beginner", "start", "tutorial", "guide", "introduction", "basic", "simple", "learn"],
        "Expert": ["advanced", "expert", "pro", "architecture", "custom", "detailed", "developer", "spec"],
        "Enterprise": ["enterprise", "scale", "large", "corporate", "multi-tenant", "security", "organizations"],
        "Location": ["near me", "in", "at", "local", "usa", "city", "regional", "office", "headquarters"],
        "AI Search": ["how does", "summarize", "explain", "ai", "chatgpt", "gemini", "claude"],
        "Role-Based": ["for developers", "for marketers", "for managers", "for admin", "role", "for business"],
        "Scenario-Based": ["when", "if", "during", "in case", "how to handle", "scenario"],
        "Need-Based": ["need", "want", "require", "demand", "looking for", "necessary"],
        "Pain Point": ["annoying", "frustrated", "slow", "expensive", "hard", "complex", "pain", "struggle"],
        "Natural Language": ["who", "what", "why", "where", "how", "when", "which"],
        "Conversational": ["conversation", "talk", "chat", "explain to a", "explain like", "tell me"]
    }

    def run(self, project_id: str, current_run_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Groups questions into categories, computes coverages, determines priorities,
        inserts records into query_coverage_heatmaps, and returns the result.
        """
        questions = payload.get("questions", []) or []
        crawled_pages = payload.get("crawled_pages", []) or []
        
        category_scores = {}
        
        # 1. Evaluate coverage for each of the 20 categories
        for cat_name, keywords in self.CATEGORIES.items():
            cat_scores = []
            
            # Map questions to this category
            for q in questions:
                q_text = q.get("question", "").lower()
                # Check if any keyword matches
                if any(kw in q_text for kw in keywords):
                    cat_scores.append(float(q.get("coverage_score", 0.0)))
                    
            if cat_scores:
                # Average coverage of questions in this category
                avg_score = sum(cat_scores) / len(cat_scores)
                category_scores[cat_name] = round(avg_score, 1)
            else:
                # Fallback baseline: check keyword matches in crawled pages
                match_count = 0
                pages_content = " ".join(p.get("content", "") or "" for p in crawled_pages).lower()
                for kw in keywords:
                    if kw in pages_content:
                        match_count += 1
                baseline = min(45.0, match_count * 15.0)
                category_scores[cat_name] = round(baseline, 1)

        # 2. Classify categories based on coverage thresholds
        missing = []
        weak = []
        strong = []
        priorities = {}
        
        for cat_name, score in category_scores.items():
            if score == 0.0:
                missing.append(cat_name)
                priorities[cat_name] = "HIGH"
            elif score < 50.0:
                weak.append(cat_name)
                priorities[cat_name] = "HIGH" if score < 30.0 else "MEDIUM"
            else:
                if score >= 80.0:
                    strong.append(cat_name)
                priorities[cat_name] = "LOW"

        # 3. Build and insert db row
        result = {
            "project_id": project_id,
            "run_id": current_run_id,
            "category_scores": category_scores,
            "missing_categories": missing,
            "weak_categories": weak,
            "strong_categories": strong,
            "priorities": priorities
        }
        
        try:
            supabase_client.table("query_coverage_heatmaps").insert(result).execute()
            logger.info(f"Successfully recorded query coverage heatmap for project {project_id}.")
        except Exception as e:
            logger.error(f"Error persisting query coverage heatmap: {e}")
            
        return result
