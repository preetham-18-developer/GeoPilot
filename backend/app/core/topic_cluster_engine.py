"""
topic_cluster_engine.py
Phase 7 — Topic Cluster Engine

Builds Parent Topics, Subtopics, Supporting Questions, Supporting Keywords,
Entity Relationships, Intent Types, and Priority Scores.
"""

from typing import Dict, Any, List
import logging
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class TopicClusterEngine:
    """
    Groups keywords and questions into structured topic clusters deterministically.
    """

    def run(self, project_id: str, current_run_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Processes keywords, questions, and entity maps to compile topic clusters,
        persists them in topic_clusters table, and returns the result.
        """
        keywords = payload.get("keywords", []) or []
        questions = payload.get("questions", []) or []
        entity_relationships = payload.get("entity_relationships", []) or []
        business_profile = payload.get("business_profile", {}) or {}

        # 1. Determine Parent Topics based on business profile or highest value keywords
        company_name = business_profile.get("company_name", "Brand Solutions")
        industry = business_profile.get("industry", "Technology")
        
        # Fallback if no keywords
        if not keywords:
            logger.info("No keywords available for topic clustering.")
            return []

        # Find unique keyword clusters
        clusters_map = {}
        for kw in keywords:
            cluster_name = kw.get("cluster", "General")
            if cluster_name not in clusters_map:
                clusters_map[cluster_name] = []
            clusters_map[cluster_name].append(kw)

        # Build Topic Clusters
        topic_clusters = []
        
        # Generate parent topics dynamically
        parent_topics = [
            f"{company_name} {industry} Core",
            f"Optimized {industry} Services"
        ]

        # Limit to top clusters
        for i, (cluster_name, kw_list) in enumerate(list(clusters_map.items())[:4]):
            parent_topic = parent_topics[i % len(parent_topics)]
            
            # Subtopics are unique keyword terms or child clusters
            subtopics = list(set(k.get("keyword", "") for k in kw_list[:3]))
            
            # Supporting Keywords
            supporting_kws = [k.get("keyword", "") for k in kw_list]
            
            # Supporting Questions (questions that contain the cluster name or subtopic terms)
            supporting_qs = []
            for q in questions:
                q_text = q.get("question", "").lower()
                if cluster_name.lower() in q_text or any(sub.lower() in q_text for sub in subtopics):
                    supporting_qs.append(q.get("question", ""))
            
            # Limit to top 5 questions
            supporting_qs = list(set(supporting_qs))[:5]
            
            # Intent types
            intents = list(set(k.get("intent", "informational") for k in kw_list))
            
            # Average Priority Score
            scores = [float(k.get("recommendation_value", 50.0)) for k in kw_list]
            priority_score = sum(scores) / len(scores) if scores else 50.0
            
            # Entity relationships matches
            relationships = []
            for rel in entity_relationships:
                source = rel.get("source_entity", "").lower()
                target = rel.get("target_entity", "").lower()
                if any(sub.lower() in source or sub.lower() in target for sub in subtopics):
                    relationships.append(f"{rel.get('source_entity')} -> {rel.get('relationship_type')} -> {rel.get('target_entity')}")
            
            cluster_entry = {
                "project_id": project_id,
                "run_id": current_run_id,
                "parent_topic": parent_topic,
                "subtopics": subtopics,
                "supporting_questions": supporting_qs,
                "supporting_keywords": supporting_kws[:10], # Limit list size
                "entity_relationships": list(set(relationships))[:5],
                "intent_types": intents,
                "priority_score": round(priority_score, 1)
            }
            topic_clusters.append(cluster_entry)

        if topic_clusters:
            try:
                supabase_client.table("topic_clusters").insert(topic_clusters).execute()
                logger.info(f"Persisted {len(topic_clusters)} topic clusters for project {project_id}.")
            except Exception as e:
                logger.error(f"Error persisting topic clusters: {e}")

        return topic_clusters
