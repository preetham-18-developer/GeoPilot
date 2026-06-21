"""
reality_checker.py

RealityChecker — deterministic evaluation engine comparing platform recommendation scores
against manual search engine verification results (ChatGPT, Gemini, Perplexity).

NO LLM calls. NO randomness.
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple
from app.core.recommendation_engine import RecommendationEngineV2

def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", (text or "").lower()).strip()

def _words(text: str) -> set:
    return {w for w in _normalize(text).split() if len(w) > 2}

class RealityChecker:
    """
    Generates realistic query sets and analyzes verification accuracy, precision, recall, and calibration.
    """

    def generate_queries(self, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates 20 distinct natural language queries using business profile metadata.
        Computes expected confidence score and evidence for each.
        """
        bp = project_data.get("business_profile", {}) or {}
        company_name = bp.get("company_name", "the business")
        industry = bp.get("industry", "industry solutions")
        usp = bp.get("usp", "quality services")
        audience = bp.get("target_audience", "customers")
        
        pre_query = bp.get("pre_query_discovery", {}) or {}
        services = pre_query.get("services", []) or []
        products = pre_query.get("products", []) or []
        
        # Build list of services/products with fallback to industry
        topics = []
        if services:
            topics.extend(services)
        if products:
            topics.extend(products)
        if not topics:
            topics.append(industry)
            
        # Pad topics to ensure we have enough diversity
        while len(topics) < 5:
            topics.append(f"{industry} specialized services")

        templates = [
            "Best {topic} company near me",
            "Top-rated {topic} provider for {audience}",
            "Who offers {topic} with {usp_short}?",
            "Which {industry} platform should I use?",
            "Affordable {topic} tools",
            "Leading {industry} experts for {audience}",
            "Recommended {topic} consulting",
            "Where to hire {topic} professionals",
            "Who are the top competitors to {company} in {industry}?",
            "Is {company} a good choice for {topic}?",
            "Highest rated {topic} in the market",
            "Most reliable {topic} with compliance support",
            "Who is best at {topic} for {audience}?",
            "Who provides commercial {topic}?",
            "Top choice for {topic} integrations",
            "Who specializes in {topic} and {usp_short}?",
            "What is the top {industry} firm?",
            "Who should I choose for {topic}?",
            "Best value {topic} for enterprises",
            "Who leads {industry} solutions?"
        ]

        queries = []
        engine = RecommendationEngineV2()
        
        for i, temp in enumerate(templates[:20]):
            topic = topics[i % len(topics)]
            usp_words = usp.split()
            usp_short = " ".join(usp_words[:4]) if len(usp_words) > 4 else usp
            
            query = temp.format(
                topic=topic,
                audience=audience if audience else "businesses",
                industry=industry,
                usp_short=usp_short if usp_short else "great results",
                company=company_name
            )
            
            # Use recommendation engine core logic to get expected score/confidence
            # We mock the single query run
            fact_matches = []
            verified_facts = project_data.get("verified_facts", []) or []
            qwords = _words(query)
            
            for fact in verified_facts:
                val = str(fact.get("fact_value", "") or fact.get("evidence", "") or "")
                hits = qwords & _words(val)
                if len(hits) >= 2:
                    fact_matches.append(val[:150])
            
            # Simple simulation of score
            expected_confidence = 30.0
            if fact_matches:
                expected_confidence += min(40.0, len(fact_matches) * 15.0)
            if bp.get("trust_signals"):
                expected_confidence += min(30.0, len(bp.get("trust_signals", [])) * 6.0)
            
            expected_confidence = min(100.0, round(expected_confidence, 1))

            queries.append({
                "query": query,
                "expected_confidence": expected_confidence,
                "evidence": fact_matches[:3],
                "chatgpt_mentions": "NO",
                "gemini_mentions": "NO",
                "perplexity_mentions": "NO",
                "is_verified": False
            })

        return queries

    def calculate_metrics(self, checked_queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates Accuracy, Precision, Recall, and Calibration Error.
        Only runs on queries where is_verified = True.
        """
        verified = [q for q in checked_queries if q.get("is_verified")]
        if not verified:
            return {
                "total_verified": 0,
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "calibration_error": 0.0
            }

        tp = 0
        fp = 0
        tn = 0
        fn = 0
        abs_calibration_diff = 0.0

        for q in verified:
            # Reality check ground truth: YES or PARTIAL on any client means recommended
            cg = q.get("chatgpt_mentions", "NO")
            gm = q.get("gemini_mentions", "NO")
            px = q.get("perplexity_mentions", "NO")
            
            actual_rec = 1 if (cg in ("YES", "PARTIAL") or gm in ("YES", "PARTIAL") or px in ("YES", "PARTIAL")) else 0
            
            # Platform prediction: predicted recommended if expected_confidence >= 50%
            conf = float(q.get("expected_confidence", 0) or 0)
            pred_rec = 1 if conf >= 50.0 else 0

            if actual_rec == 1 and pred_rec == 1:
                tp += 1
            elif actual_rec == 0 and pred_rec == 1:
                fp += 1
            elif actual_rec == 0 and pred_rec == 0:
                tn += 1
            elif actual_rec == 1 and pred_rec == 0:
                fn += 1

            abs_calibration_diff += abs((conf / 100.0) - actual_rec)

        total = len(verified)
        accuracy = round(((tp + tn) / total) * 100.0, 1)
        precision = round((tp / (tp + fp)) * 100.0, 1) if (tp + fp) > 0 else 0.0
        recall = round((tp / (tp + fn)) * 100.0, 1) if (tp + fn) > 0 else 0.0
        calibration_error = round((abs_calibration_diff / total) * 100.0, 1)

        return {
            "total_verified": total,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "calibration_error": calibration_error
        }
