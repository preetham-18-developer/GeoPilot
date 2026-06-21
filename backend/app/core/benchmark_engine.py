"""
benchmark_engine.py

CompetitorBenchmarkEngine — deterministic relative performance analysis
comparing a client against all stored competitors across 7 dimensions.

NO LLM calls. NO randomness.

Dimensions scored 0–100:
  keyword_coverage    — keyword count × overlap vs competitor keyword proxy
  question_coverage   — question count relative to competitor proxy
  trust_signals       — trust signal categories present vs competitors
  content_depth       — average content_coverage score
  entity_richness     — entity node count
  faq_coverage        — questions with recommended_answer present
  authority_signals   — verified fact confidence vs competitor proxy
"""

from __future__ import annotations
import re
from typing import List, Dict, Any
from collections import Counter


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", (text or "").lower()).strip()


def _words(text: str) -> set:
    return {w for w in _normalize(text).split() if len(w) > 2}


TRUST_CATEGORIES = [
    ("certification", ["certif", "iso", "soc", "hipaa", "gdpr", "accredit"]),
    ("reviews", ["review", "rating", "star", "g2", "trustpilot", "testimonial"]),
    ("security", ["secure", "ssl", "encrypt", "privacy", "https"]),
    ("authority", ["award", "leader", "founded", "years", "experience"]),
    ("case_studies", ["case study", "success story", "client"]),
]


def _trust_signal_count(bp: Dict[str, Any], verified_facts: List[Dict]) -> int:
    """Count trust signal categories present."""
    facts_str = " ".join(
        str(f.get("fact_value", "") or f.get("evidence", "") or "") for f in verified_facts
    ).lower()
    signals_str = " ".join(bp.get("trust_signals", []) or []).lower()
    combined = facts_str + " " + signals_str

    present = sum(1 for _, terms in TRUST_CATEGORIES if any(t in combined for t in terms))
    return present


def _competitor_trust_proxy(comp: Dict[str, Any]) -> int:
    """Proxy trust signal count for a competitor from its description + strengths."""
    text = " ".join([
        str(comp.get("description", "") or ""),
        " ".join(comp.get("strengths", []) or [])
    ]).lower()
    return sum(1 for _, terms in TRUST_CATEGORIES if any(t in text for t in terms))


class CompetitorBenchmarkEngine:
    """
    Benchmarks the client project against each stored competitor.
    Returns percentile score, relative position, gap matrix, and 4 ranked dimension lists.
    """

    DIMENSIONS = [
        "keyword_coverage",
        "question_coverage",
        "trust_signals",
        "content_depth",
        "entity_richness",
        "faq_coverage",
        "authority_signals",
    ]

    def run(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        bp = project_data.get("business_profile", {}) or {}
        verified_facts = project_data.get("verified_facts", []) or []
        questions = project_data.get("questions", []) or []
        keywords = project_data.get("keywords", []) or []
        competitors = project_data.get("competitors", []) or []
        content_coverage = project_data.get("content_coverage", []) or []
        entity_nodes = project_data.get("entity_nodes", []) or []

        # ── Client Scores ────────────────────────────────────────────────────

        client_keyword_coverage = min(100.0, (len(keywords) / 50.0) * 100.0)

        client_question_coverage = min(100.0, (len(questions) / 30.0) * 100.0)

        trust_count = _trust_signal_count(bp, verified_facts)
        client_trust = min(100.0, (trust_count / 5.0) * 100.0)

        avg_cov = (
            sum(float(c.get("coverage_score", 0) or 0) for c in content_coverage)
            / max(len(content_coverage), 1)
        )
        client_content_depth = min(100.0, round(avg_cov, 1))

        client_entity_richness = min(100.0, (len(entity_nodes) / 20.0) * 100.0)

        faq_answered = sum(1 for q in questions if q.get("recommended_answer"))
        client_faq_coverage = min(100.0, (faq_answered / max(len(questions), 1)) * 100.0)

        high_conf_facts = sum(
            1 for f in verified_facts
            if float(f.get("confidence_score", 0) or 0) >= 0.8
        )
        client_authority = min(100.0, (high_conf_facts / 10.0) * 100.0)

        client_scores = {
            "keyword_coverage": round(client_keyword_coverage, 1),
            "question_coverage": round(client_question_coverage, 1),
            "trust_signals": round(client_trust, 1),
            "content_depth": round(client_content_depth, 1),
            "entity_richness": round(client_entity_richness, 1),
            "faq_coverage": round(client_faq_coverage, 1),
            "authority_signals": round(client_authority, 1),
        }

        # ── Competitor Scores ────────────────────────────────────────────────
        competitor_score_list = []
        for comp in competitors[:10]:
            comp_name = comp.get("name", comp.get("competitor_name", "Unknown"))
            sim = float(comp.get("similarity_score", 50) or 50)

            # Keyword proxy: competitor similarity drives keyword overlap assumption
            comp_kw = min(100.0, sim * 0.8 + (len(comp.get("strengths", [])) * 2))
            # Question proxy from description word count
            desc_words = len(_words(comp.get("description", "") or ""))
            comp_q = min(100.0, desc_words * 2.5)
            comp_trust = min(100.0, _competitor_trust_proxy(comp) * 20.0)
            comp_depth = min(100.0, sim * 0.6)
            comp_entity = min(100.0, sim * 0.5)
            comp_faq = min(100.0, comp_q * 0.7)
            comp_auth = min(100.0, comp_trust * 0.75)

            comp_scores = {
                "keyword_coverage": round(comp_kw, 1),
                "question_coverage": round(comp_q, 1),
                "trust_signals": round(comp_trust, 1),
                "content_depth": round(comp_depth, 1),
                "entity_richness": round(comp_entity, 1),
                "faq_coverage": round(comp_faq, 1),
                "authority_signals": round(comp_auth, 1),
            }

            competitor_score_list.append({
                "name": str(comp_name),
                "competitor_type": comp.get("competitor_type", "direct"),
                "scores": comp_scores,
                "overall": round(sum(comp_scores.values()) / len(comp_scores), 1),
            })

        # ── Overall Scores & Percentile ──────────────────────────────────────
        client_overall = round(sum(client_scores.values()) / len(client_scores), 1)

        all_overalls = [client_overall] + [c["overall"] for c in competitor_score_list]
        all_overalls_sorted = sorted(all_overalls, reverse=True)
        client_rank = all_overalls_sorted.index(client_overall) + 1
        total_players = len(all_overalls)

        # Percentile: how many competitors the client beats
        beats_count = sum(1 for c in competitor_score_list if client_overall > c["overall"])
        percentile = round((beats_count / max(len(competitor_score_list), 1)) * 100.0, 1)

        # ── Gap Matrix ───────────────────────────────────────────────────────
        gap_matrix = []
        for dim in self.DIMENSIONS:
            client_val = client_scores[dim]
            comp_vals = [c["scores"][dim] for c in competitor_score_list]
            avg_comp = round(sum(comp_vals) / max(len(comp_vals), 1), 1)
            best_comp = round(max(comp_vals), 1) if comp_vals else 0.0
            gap = round(client_val - avg_comp, 1)
            gap_from_best = round(client_val - best_comp, 1)

            gap_matrix.append({
                "dimension": dim.replace("_", " ").title(),
                "client_score": client_val,
                "avg_competitor_score": avg_comp,
                "best_competitor_score": best_comp,
                "gap_from_avg": gap,
                "gap_from_best": gap_from_best,
                "status": (
                    "strength" if gap > 5 else
                    "parity" if abs(gap) <= 5 else
                    "weakness"
                ),
            })

        # ── Ranked Lists ─────────────────────────────────────────────────────
        strengths_rank = sorted(
            [m for m in gap_matrix if m["status"] == "strength"],
            key=lambda x: -x["gap_from_avg"]
        )
        weaknesses_rank = sorted(
            [m for m in gap_matrix if m["status"] == "weakness"],
            key=lambda x: x["gap_from_avg"]
        )
        threats_rank = sorted(
            competitor_score_list,
            key=lambda x: -x["overall"]
        )[:3]
        opportunities_rank = sorted(
            weaknesses_rank,
            key=lambda x: x["gap_from_avg"]
        )

        return {
            "client_overall_score": client_overall,
            "percentile_score": percentile,
            "relative_position": client_rank,
            "total_players": total_players,
            "client_scores": client_scores,
            "competitor_scores": competitor_score_list,
            "gap_matrix": gap_matrix,
            "strengths_rank": strengths_rank,
            "weaknesses_rank": weaknesses_rank,
            "threats_rank": threats_rank,
            "opportunities_rank": opportunities_rank,
        }
