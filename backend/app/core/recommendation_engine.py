"""
recommendation_engine.py

RecommendationEngineV2 — deterministic, multi-signal recommendation confidence engine.

NO LLM calls. NO randomness. All scores derived from stored project data.

For each simulated user query, calculates:
  - fact_match_score       : How many verified facts back a recommendation
  - keyword_coverage_score : % of query words found in top keywords
  - question_alignment_score : Best matching question's recommendation_score
  - trust_signal_score     : Trust signal presence vs expected minimum
  - content_depth_score    : Content coverage score for the matched topic
  - competitor_threat_score: Average similarity of direct competitors (inverted)

Final recommendation_score = deterministic weighted average of all signals.
Every signal is exposed to the user for full explainability.
"""

from __future__ import annotations
import re
import math
from typing import List, Dict, Any, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", (text or "").lower()).strip()


def _words(text: str) -> set:
    return {w for w in _normalize(text).split() if len(w) > 2}


def _overlap(a: str, b: str) -> int:
    return len(_words(a) & _words(b))


def _overlap_ratio(query: str, text: str) -> float:
    qw = _words(query)
    if not qw:
        return 0.0
    hits = len(qw & _words(text))
    return hits / len(qw)


# ─────────────────────────────────────────────────────────────────────────────
# Query Template Generator
# ─────────────────────────────────────────────────────────────────────────────

def _generate_queries(
    company_name: str,
    industry: str,
    usp: str,
    target_audience: str,
    services: List[str],
    products: List[str],
) -> List[Dict[str, str]]:
    """
    Generates 5 realistic user query templates from business profile.
    Each query has a type label for categorisation in the UI.
    """
    service_str = services[0] if services else industry
    product_str = products[0] if products else industry

    queries = [
        {
            "query": f"Best {industry} company for {target_audience}",
            "query_type": "Discovery",
        },
        {
            "query": f"Who provides {service_str}?",
            "query_type": "Service Discovery",
        },
        {
            "query": f"Top {industry} solutions with {usp[:60] if usp else 'proven results'}",
            "query_type": "Competitive Comparison",
        },
        {
            "query": f"Affordable {product_str} for small businesses",
            "query_type": "Commercial Intent",
        },
        {
            "query": f"Which {industry} provider should I choose?",
            "query_type": "Decision Support",
        },
    ]
    return queries


# ─────────────────────────────────────────────────────────────────────────────
# Signal Calculators
# ─────────────────────────────────────────────────────────────────────────────

def _fact_match_score(query: str, verified_facts: List[Dict[str, Any]]) -> Tuple[float, List[str]]:
    """Returns (score 0-100, list of supporting evidence strings)."""
    evidence = []
    total_match = 0.0

    for fact in verified_facts:
        fact_val = str(fact.get("fact_value", "") or fact.get("evidence", "") or "")
        ratio = _overlap_ratio(query, fact_val)
        if ratio >= 0.3:
            evidence.append(fact_val[:200])
            total_match += ratio

    score = min(100.0, total_match * 30)
    return round(score, 1), evidence[:5]


def _keyword_coverage_score(
    query: str, keywords: List[Dict[str, Any]]
) -> Tuple[float, List[str]]:
    """Returns (score 0-100, matching keyword texts)."""
    qwords = _words(query)
    if not qwords:
        return 0.0, []

    matched_kw = []
    matched_words: set = set()

    for kw in keywords:
        kw_text = str(kw.get("keyword", kw.get("keyword_text", "")) or "")
        kw_words = _words(kw_text)
        hits = qwords & kw_words
        if hits:
            matched_kw.append(kw_text)
            matched_words |= hits

    coverage = len(matched_words) / len(qwords)
    score = min(100.0, coverage * 100)
    return round(score, 1), matched_kw[:6]


def _question_alignment_score(
    query: str, questions: List[Dict[str, Any]]
) -> Tuple[float, str]:
    """Returns (best match score 0-100, best matching question text)."""
    best_score = 0.0
    best_q = ""

    for q in questions:
        q_text = str(q.get("question", q.get("question_text", "")) or "")
        ratio = _overlap_ratio(query, q_text)
        rec_score = float(q.get("recommendation_score", 0) or 0)
        # Blend: semantic similarity × declared recommendation score
        combined = (ratio * 50) + (rec_score * 0.5)
        if combined > best_score:
            best_score = combined
            best_q = q_text

    return round(min(100.0, best_score), 1), best_q


def _trust_signal_score(
    trust_signals: List[str],
    verified_facts: List[Dict[str, Any]],
) -> Tuple[float, List[str], List[str]]:
    """
    Returns (score 0-100, present trust signals, missing trust signal categories).
    Minimum expected: 3 trust signals (certifications, reviews, awards).
    """
    EXPECTED_CATEGORIES = [
        ("certification", ["certif", "iso", "soc", "hipaa", "gdpr", "accredit"]),
        ("reviews/ratings", ["review", "rating", "star", "g2", "trustpilot"]),
        ("security", ["secure", "ssl", "encrypt", "privacy", "https"]),
        ("authority", ["award", "leader", "founded", "years", "experience"]),
        ("case_studies", ["case study", "success story", "client"]),
    ]

    facts_str = " ".join(
        str(f.get("fact_value", "") or "") for f in verified_facts
    ).lower()
    signals_str = " ".join(trust_signals).lower()
    combined = facts_str + " " + signals_str

    present = []
    missing = []
    for cat_name, terms in EXPECTED_CATEGORIES:
        if any(t in combined for t in terms):
            present.append(cat_name)
        else:
            missing.append(cat_name)

    score = min(100.0, (len(present) / len(EXPECTED_CATEGORIES)) * 100)
    return round(score, 1), present, missing


def _content_depth_score(
    query: str, content_coverage: List[Dict[str, Any]]
) -> Tuple[float, str]:
    """Returns (best matching coverage score 0-100, matched topic name)."""
    best_score = 0.0
    best_topic = "N/A"

    for cov in content_coverage:
        topic = str(cov.get("topic_name", "") or "")
        ratio = _overlap_ratio(query, topic)
        cov_score = float(cov.get("coverage_score", 0) or 0)
        weighted = (ratio * 50) + (cov_score * 0.5)
        if weighted > best_score:
            best_score = weighted
            best_topic = topic

    return round(min(100.0, best_score), 1), best_topic


def _competitor_threat_score(
    competitors: List[Dict[str, Any]],
) -> Tuple[float, List[Dict[str, str]]]:
    """
    Returns (threat score 0-100, list of competitor threat items).
    Higher competitor similarity = higher threat (inverted for client score).
    """
    direct = [c for c in competitors if c.get("competitor_type", "direct") == "direct"]
    if not direct:
        return 0.0, []

    avg_sim = sum(
        float(c.get("similarity_score", 50) or 50) for c in direct
    ) / len(direct)

    threat_list = []
    for c in direct[:3]:
        name = str(c.get("name", c.get("competitor_name", "Unknown")) or "Unknown")
        sim = float(c.get("similarity_score", 50) or 50)
        strengths = c.get("strengths", [])
        top_strength = strengths[0] if strengths else "Comparable capabilities"
        threat_list.append({
            "competitor": name,
            "similarity": f"{int(sim)}%",
            "advantage": str(top_strength),
        })

    return round(min(100.0, avg_sim), 1), threat_list


# ─────────────────────────────────────────────────────────────────────────────
# Improvement Action Generator
# ─────────────────────────────────────────────────────────────────────────────

def _build_improvement_actions(
    missing_trust: List[str],
    kw_coverage: float,
    q_alignment: float,
    content_depth: float,
    fact_score: float,
) -> List[str]:
    actions = []

    if fact_score < 40:
        actions.append(
            "Expand content with more verifiable, fact-dense pages to increase factual evidence coverage."
        )
    if kw_coverage < 50:
        actions.append(
            "Add more long-tail keyword pages targeting the specific query terms identified."
        )
    if q_alignment < 40:
        actions.append(
            "Create FAQ content directly answering user discovery queries in natural language."
        )
    if content_depth < 50:
        actions.append(
            "Deepen topical content coverage for this subject area with guides, case studies, or knowledge base articles."
        )
    if "certification" in missing_trust:
        actions.append(
            "Add visible certification badges and structured schema markup for Organization and LocalBusiness."
        )
    if "reviews/ratings" in missing_trust:
        actions.append(
            "Embed verified customer reviews and ratings on the homepage and key service pages."
        )
    if "case_studies" in missing_trust:
        actions.append(
            "Publish at least 2 client case studies with measurable outcomes to strengthen authority signals."
        )
    if "security" in missing_trust:
        actions.append(
            "Display SSL badge, privacy policy link, and security compliance mention prominently."
        )

    return actions[:5] if actions else ["Content appears well optimized for this query."]


# ─────────────────────────────────────────────────────────────────────────────
# Main Engine
# ─────────────────────────────────────────────────────────────────────────────

class RecommendationEngineV2:
    """
    Deterministic multi-signal recommendation confidence engine.

    Weights (sum to 1.0):
      fact_match           0.30  — factual grounding is most critical
      keyword_coverage     0.20  — keyword presence drives discoverability
      question_alignment   0.20  — question coverage proves conversational readiness
      trust_signals        0.15  — trust/authority signals are key for LLM citations
      content_depth        0.10  — topical depth signals expertise
      competitor_threat    0.05  — competitor parity (inverted: lower threat = better)
    """

    WEIGHTS = {
        "fact_match": 0.30,
        "keyword_coverage": 0.20,
        "question_alignment": 0.20,
        "trust_signals": 0.15,
        "content_depth": 0.10,
        "competitor_advantage": 0.05,
    }

    def run(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point. Accepts a dict of all project data fetched from Supabase.
        Returns the full V2 recommendation intelligence report.
        """
        bp = project_data.get("business_profile", {}) or {}
        verified_facts = project_data.get("verified_facts", []) or []
        questions = project_data.get("questions", []) or []
        keywords = project_data.get("keywords", []) or []
        competitors = project_data.get("competitors", []) or []
        content_coverage = project_data.get("content_coverage", []) or []

        company_name = str(bp.get("company_name", "Unknown") or "Unknown")
        industry = str(bp.get("industry", "General") or "General")
        usp = str(bp.get("usp", "") or "")
        target_audience = str(bp.get("target_audience", "") or "")
        trust_signals = bp.get("trust_signals", []) or []

        pre_query = bp.get("pre_query_discovery", {}) or {}
        services = pre_query.get("services", []) or []
        products = pre_query.get("products", []) or []

        # Generate 5 query templates
        queries = _generate_queries(
            company_name, industry, usp, target_audience, services, products
        )

        # Calculate trust signal score once (shared across all queries)
        trust_score, trust_present, trust_missing = _trust_signal_score(
            trust_signals, verified_facts
        )

        # Calculate competitor threat once (shared)
        comp_threat, competitor_threats = _competitor_threat_score(competitors)
        # Invert: higher competitor similarity = lower client advantage
        comp_advantage_score = max(0.0, 100.0 - comp_threat)

        simulations = []
        scores_for_avg = []

        for q_item in queries:
            query = q_item["query"]
            q_type = q_item["query_type"]

            fact_score, evidence = _fact_match_score(query, verified_facts)
            kw_score, matched_kw = _keyword_coverage_score(query, keywords)
            q_score, best_q = _question_alignment_score(query, questions)
            depth_score, matched_topic = _content_depth_score(query, content_coverage)

            # Weighted recommendation score
            rec_score = round(
                self.WEIGHTS["fact_match"] * fact_score
                + self.WEIGHTS["keyword_coverage"] * kw_score
                + self.WEIGHTS["question_alignment"] * q_score
                + self.WEIGHTS["trust_signals"] * trust_score
                + self.WEIGHTS["content_depth"] * depth_score
                + self.WEIGHTS["competitor_advantage"] * comp_advantage_score,
                1,
            )

            # Confidence = how many signals have data (0-100)
            signals_with_data = sum([
                fact_score > 0,
                kw_score > 0,
                q_score > 0,
                trust_score > 0,
                depth_score > 0,
                bool(verified_facts),
            ])
            confidence = round((signals_with_data / 6) * 100, 1)

            # Weaknesses = signals below 40
            weaknesses = []
            if fact_score < 40:
                weaknesses.append(
                    f"Low factual evidence coverage ({fact_score:.0f}/100) — few verified facts match this query."
                )
            if kw_score < 40:
                weaknesses.append(
                    f"Low keyword coverage ({kw_score:.0f}/100) — query terms not found in keyword set."
                )
            if q_score < 40:
                weaknesses.append(
                    f"Low question alignment ({q_score:.0f}/100) — no FAQ-style content addresses this query."
                )
            if depth_score < 40:
                weaknesses.append(
                    f"Shallow content depth ({depth_score:.0f}/100) for topic '{matched_topic}'."
                )

            # Missing requirements
            missing_reqs = []
            if trust_missing:
                missing_reqs.extend(
                    [f"Missing trust signal category: {t}" for t in trust_missing]
                )
            if not evidence:
                missing_reqs.append("No verifiable facts directly support this query.")
            if not matched_kw:
                missing_reqs.append("No keywords cover this query's terminology.")

            improvement_actions = _build_improvement_actions(
                trust_missing, kw_score, q_score, depth_score, fact_score
            )

            scores_for_avg.append(rec_score)

            simulations.append({
                "query": query,
                "query_type": q_type,
                "recommendation_score": rec_score,
                "confidence": confidence,
                "evidence": evidence,
                "weaknesses": weaknesses,
                "missing_requirements": missing_reqs,
                "improvement_actions": improvement_actions,
                "competitor_threats": competitor_threats,
                "matched_topic": matched_topic,
                "best_matching_question": best_q,
                "matched_keywords": matched_kw,
                "signal_breakdown": {
                    "fact_match": {"score": fact_score, "weight": "30%", "label": "Factual Evidence"},
                    "keyword_coverage": {"score": kw_score, "weight": "20%", "label": "Keyword Coverage"},
                    "question_alignment": {"score": q_score, "weight": "20%", "label": "Question Alignment"},
                    "trust_signals": {"score": trust_score, "weight": "15%", "label": "Trust Signals"},
                    "content_depth": {"score": depth_score, "weight": "10%", "label": "Content Depth"},
                    "competitor_advantage": {"score": comp_advantage_score, "weight": "5%", "label": "Competitor Advantage"},
                },
            })

        # Overall report
        overall_score = round(sum(scores_for_avg) / len(scores_for_avg), 1) if scores_for_avg else 0.0
        overall_confidence = round(
            sum(s["confidence"] for s in simulations) / len(simulations), 1
        ) if simulations else 0.0

        if overall_score >= 70:
            recommendation_status = "likely_recommended"
        elif overall_score >= 45:
            recommendation_status = "partially_recommended"
        else:
            recommendation_status = "unlikely_recommended"

        # Aggregate all improvement actions, deduplicated
        all_actions: List[str] = []
        seen: set = set()
        for s in simulations:
            for a in s["improvement_actions"]:
                if a not in seen:
                    all_actions.append(a)
                    seen.add(a)

        return {
            "overall_recommendation_score": overall_score,
            "overall_confidence": overall_confidence,
            "recommendation_status": recommendation_status,
            "trust_signals_present": trust_present,
            "trust_signals_missing": trust_missing,
            "competitor_threats": competitor_threats,
            "top_improvement_actions": all_actions[:6],
            "simulations": simulations,
        }
