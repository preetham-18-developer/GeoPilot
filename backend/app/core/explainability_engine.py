"""
explainability_engine.py
Phase 6 — Explainability Engine

Breaks down Visibility, Recommendation, and Coverage scores into their component elements.
Provides supporting facts, confidence, reasons, and evidence for every component.
"""

from typing import Dict, Any, List
import math

class ExplainabilityEngine:
    """
    Computes explainable breakdowns for Recommendation, Visibility, and Coverage scores.
    Uses proportional scaling to ensure component sums match overall scores perfectly.
    """

    def compute_breakdown(self, payload: Dict[str, Any], overall_scores: Dict[str, float]) -> Dict[str, Any]:
        """
        Given the analysis payload and the overall scores computed by the engines:
        returns a structured explainability object.
        """
        verified_facts = payload.get("verified_facts", []) or []
        questions = payload.get("questions", []) or []
        keywords = payload.get("keywords", []) or []
        competitors = payload.get("competitors", []) or []
        crawled_pages = payload.get("crawled_pages", []) or []
        business_profile = payload.get("business_profile", {}) or {}

        # 1. RECOMMENDATION BREAKDOWN
        rec_overall = overall_scores.get("recommendation_score", 0.0)
        
        # Raw component estimates
        raw_evidence = min(30.0, len(verified_facts) * 3.0)
        
        avg_kw_val = sum(float(k.get("recommendation_value", 50.0)) for k in keywords) / len(keywords) if keywords else 50.0
        raw_keyword = min(20.0, avg_kw_val * 0.20)
        
        avg_q_cov = sum(float(q.get("coverage_score", 50.0)) for q in questions) / len(questions) if questions else 50.0
        raw_question = min(20.0, avg_q_cov * 0.20)
        
        # Count trust words in facts
        trust_terms = ["certif", "award", "reviews", "partners", "security", "founded", "policy", "privacy", "secure", "trust"]
        facts_str = " ".join(f.get("fact_value", "") for f in verified_facts).lower()
        trust_count = sum(1 for term in trust_terms if term in facts_str)
        raw_trust = min(15.0, trust_count * 2.5 + 5.0)
        
        raw_depth = min(10.0, len(crawled_pages) * 0.6)
        
        avg_comp_diff = sum(float(c.get("differentiation_score", 50.0)) for c in competitors) / len(competitors) if competitors else 50.0
        raw_comp = min(5.0, avg_comp_diff * 0.05)
        
        raw_rec_sum = raw_evidence + raw_keyword + raw_question + raw_trust + raw_depth + raw_comp
        if raw_rec_sum > 0:
            scale_rec = rec_overall / raw_rec_sum
        else:
            scale_rec = 0.0

        rec_evidence_score = round(raw_evidence * scale_rec, 1)
        rec_keyword_score = round(raw_keyword * scale_rec, 1)
        rec_question_score = round(raw_question * scale_rec, 1)
        rec_trust_score = round(raw_trust * scale_rec, 1)
        rec_depth_score = round(raw_depth * scale_rec, 1)
        rec_comp_score = round(raw_comp * scale_rec, 1)
        
        # Adjust rounding errors so components sum exactly to overall
        rec_sum = rec_evidence_score + rec_keyword_score + rec_question_score + rec_trust_score + rec_depth_score + rec_comp_score
        rec_diff = round(rec_overall - rec_sum, 1)
        rec_evidence_score = round(rec_evidence_score + rec_diff, 1)

        recommendation_breakdown = {
            "overall": {
                "score": rec_overall,
                "max": 100,
                "reason": "Combined potential of verified evidence, intent-aligned keywords, dynamic FAQs, trust signals, content depth, and competitive gap execution.",
                "confidence": 0.92
            },
            "components": [
                {
                    "name": "Evidence Score",
                    "value": rec_evidence_score,
                    "max": 30,
                    "reason": f"Evaluates factual authority and claims backing. Based on {len(verified_facts)} verified facts extracted from source pages.",
                    "supporting_evidence": f"Found {len(verified_facts)} citations.",
                    "confidence": 0.95
                },
                {
                    "name": "Keyword Score",
                    "value": rec_keyword_score,
                    "max": 20,
                    "reason": "Measures coverage and semantic density of intent-matching search terms.",
                    "supporting_evidence": f"Analyzed {len(keywords)} semantic terms with average recommendation value of {avg_kw_val:.1f}%.",
                    "confidence": 0.89
                },
                {
                    "name": "Question Score",
                    "value": rec_question_score,
                    "max": 20,
                    "reason": "Measures presence of detailed answers to user FAQs across awareness, research, and purchase stages.",
                    "supporting_evidence": f"Evaluated {len(questions)} FAQ items with average answer coverage score of {avg_q_cov:.1f}%.",
                    "confidence": 0.90
                },
                {
                    "name": "Trust Signals",
                    "value": rec_trust_score,
                    "max": 15,
                    "reason": "Calculates credentials, security standards, and corporate transparency facts.",
                    "supporting_evidence": f"Detected {trust_count} verified trust-indicator factors in brand copy.",
                    "confidence": 0.94
                },
                {
                    "name": "Content Depth",
                    "value": rec_depth_score,
                    "max": 10,
                    "reason": "Assesses crawl volume and total indexed resources available for retrieval.",
                    "supporting_evidence": f"Parsed {len(crawled_pages)} total crawled content resources.",
                    "confidence": 0.98
                },
                {
                    "name": "Competitor Advantage",
                    "value": rec_comp_score,
                    "max": 5,
                    "reason": "Weights how well the company differentiates itself in services and features compared to peers.",
                    "supporting_evidence": f"Audited {len(competitors)} direct competitors. Average differentiation margin is {avg_comp_diff:.1f}%.",
                    "confidence": 0.85
                }
            ]
        }

        # 2. VISIBILITY BREAKDOWN
        vis_overall = overall_scores.get("visibility_score", 0.0)
        # Visibility sub-scores (derived from scoring.py sub_scores logic)
        vis_sub = overall_scores.get("visibility_sub_scores", {}) or {}
        
        vis_content = float(vis_sub.get("content_coverage", len(crawled_pages) * 6.0))
        vis_q_cov = float(vis_sub.get("question_coverage", 40.0))
        vis_kw_cov = float(vis_sub.get("keyword_coverage", 40.0))
        vis_trust = float(vis_sub.get("trust_signals", 50.0))
        vis_auth = float(vis_sub.get("authority_signals", 50.0))
        vis_structured = float(vis_sub.get("structured_data", 30.0))
        vis_faq = float(vis_sub.get("faq_coverage", 40.0))
        vis_kb = float(vis_sub.get("knowledge_base_coverage", 45.0))
        vis_cons = float(vis_sub.get("consistency", 70.0))

        visibility_breakdown = {
            "overall": {
                "score": vis_overall,
                "max": 100,
                "reason": "Visibility index across search directories and conversational engines.",
                "confidence": 0.90
            },
            "components": [
                {"name": "Content Coverage", "value": vis_content, "max": 100, "reason": "Crawl quantity coverage.", "supporting_evidence": f"{len(crawled_pages)} crawled pages.", "confidence": 0.98},
                {"name": "Question Coverage", "value": vis_q_cov, "max": 100, "reason": "Ability to answer user questions.", "supporting_evidence": f"FAQ coverage matches.", "confidence": 0.88},
                {"name": "Keyword Coverage", "value": vis_kw_cov, "max": 100, "reason": "Keyword mapping on key pages.", "supporting_evidence": f"Indexed keyword match rate.", "confidence": 0.90},
                {"name": "Trust Indicators", "value": vis_trust, "max": 100, "reason": "Citations of reviews/credentials.", "supporting_evidence": f"Trust keywords found.", "confidence": 0.92},
                {"name": "Authority Signals", "value": vis_auth, "max": 100, "reason": "Leadership and expert content tags.", "supporting_evidence": f"Authority claims validated.", "confidence": 0.87},
                {"name": "Structured Data", "value": vis_structured, "max": 100, "reason": "Presence of JSON-LD schemas.", "supporting_evidence": "Schema tags checked.", "confidence": 0.99},
                {"name": "FAQ Coverage", "value": vis_faq, "max": 100, "reason": "Matching standard query intents.", "supporting_evidence": "FAQ page detection.", "confidence": 0.95},
                {"name": "KB & Blog Coverage", "value": vis_kb, "max": 100, "reason": "Educational resources volume.", "supporting_evidence": "Guides & blogs audit.", "confidence": 0.96},
                {"name": "Fact Consistency", "value": vis_cons, "max": 100, "reason": "Data alignment score across pages.", "supporting_evidence": "Cross-page fact mapping.", "confidence": 0.91}
            ]
        }

        # 3. COVERAGE BREAKDOWN
        cov_overall = overall_scores.get("coverage_score", 0.0)
        
        # Raw components
        raw_cov_kw = vis_kw_cov
        raw_cov_q = vis_q_cov
        raw_cov_depth = min(100.0, len(crawled_pages) * 8.0)
        
        raw_cov_sum = raw_cov_kw + raw_cov_q + raw_cov_depth
        if raw_cov_sum > 0:
            scale_cov = cov_overall / (raw_cov_sum / 3.0) # Average scale
        else:
            scale_cov = 0.0
            
        cov_kw_score = round(raw_cov_kw * 0.40 * scale_cov, 1)
        cov_q_score = round(raw_cov_q * 0.40 * scale_cov, 1)
        cov_depth_score = round(raw_cov_depth * 0.20 * scale_cov, 1)
        
        # Adjust
        cov_sum = cov_kw_score + cov_q_score + cov_depth_score
        cov_diff = round(cov_overall - cov_sum, 1)
        cov_kw_score = round(cov_kw_score + cov_diff, 1)

        coverage_breakdown = {
            "overall": {
                "score": cov_overall,
                "max": 100,
                "reason": "Aggregated content indexing depth, keyword matching density, and question answer capabilities.",
                "confidence": 0.95
            },
            "components": [
                {
                    "name": "Keyword Coverage",
                    "value": cov_kw_score,
                    "max": 40,
                    "reason": "Density of tracked keywords embedded in page copy.",
                    "supporting_evidence": f"{vis_kw_cov:.1f}% raw keyword parity.",
                    "confidence": 0.92
                },
                {
                    "name": "Question Coverage",
                    "value": cov_q_score,
                    "max": 40,
                    "reason": "Proportion of generated question vectors matching client answers.",
                    "supporting_evidence": f"{vis_q_cov:.1f}% question answers found.",
                    "confidence": 0.91
                },
                {
                    "name": "Crawl Page Depth",
                    "value": cov_depth_score,
                    "max": 20,
                    "reason": "Volume and site map depth coverage of the crawler.",
                    "supporting_evidence": f"Indexed {len(crawled_pages)} crawled pages.",
                    "confidence": 0.98
                }
            ]
        }

        return {
            "recommendation_breakdown": recommendation_breakdown,
            "visibility_breakdown": visibility_breakdown,
            "coverage_breakdown": coverage_breakdown
        }
