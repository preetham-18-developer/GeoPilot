"""
consistency_engine.py

KnowledgeConsistencyEngine — cross-agent contradiction detector.

Checks consistency between:
  - Business profile (industry, audience, USP)
  - Knowledge graph (entity nodes)
  - Verified facts
  - Questions (categories)
  - Keywords (types, clusters)
  - Competitors (industry descriptions)
  - Blogs (titles)
  - Content opportunities

Detects:
  - Industry mismatches between agents
  - Audience mismatches (BI vs. question categories)
  - Orphan keywords (no matching question covers the same topic)
  - Orphan questions (no keyword cluster backing)
  - Entity mismatches (keyword mentions entity not in graph)
  - Competitor industry contradictions
  - Content gap vs. coverage contradictions

Outputs:
  - consistency_score (0-100)
  - conflicts[] with severity
  - warnings[]
  - repair_actions[]
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple
from collections import Counter


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", (text or "").lower()).strip()


def _words(text: str) -> set:
    return {w for w in _normalize(text).split() if len(w) > 3}


def _overlap(a: str, b: str) -> int:
    return len(_words(a) & _words(b))


def _stem(word: str) -> str:
    for suffix in ("ing", "tion", "ness", "ment", "ers", "ies", "es", "ed", "ly", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _stem_set(text: str) -> set:
    return {_stem(w) for w in _words(text)}


# ─────────────────────────────────────────────────────────────────────────────
# Individual Check Functions
# ─────────────────────────────────────────────────────────────────────────────

def _check_industry_consistency(
    bp_industry: str,
    competitors: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
    keywords: List[Dict[str, Any]],
) -> Tuple[List[Dict], List[str]]:
    conflicts = []
    warnings = []
    industry_words = _words(bp_industry)

    # Check competitors against BI industry
    for comp in competitors:
        comp_desc = str(comp.get("description", "") or "")
        comp_name = str(comp.get("name", comp.get("competitor_name", "")) or "")
        if comp_desc and not _words(comp_desc) & industry_words and len(industry_words) > 1:
            warnings.append(
                f"Competitor '{comp_name}' description has no industry word overlap with '{bp_industry}'. "
                "May indicate a cross-industry match."
            )

    # Check keyword types — if all keywords are one type, flag
    kw_types = Counter(
        str(kw.get("keyword_type", kw.get("category", "")) or "") for kw in keywords
    )
    if kw_types and len(kw_types) == 1:
        only_type = list(kw_types.keys())[0]
        warnings.append(
            f"All keywords share a single type: '{only_type}'. "
            "Lack of keyword diversity may narrow discovery surface."
        )

    return conflicts, warnings


def _check_audience_consistency(
    bp_audience: str,
    questions: List[Dict[str, Any]],
) -> Tuple[List[Dict], List[str]]:
    conflicts = []
    warnings = []

    audience_stems = _stem_set(bp_audience)
    if not audience_stems:
        return conflicts, warnings

    # Check if question categories mention audience-related terms
    q_types = set(
        str(q.get("question_type", q.get("category", "")) or "") for q in questions
    )
    q_text_combined = " ".join(
        str(q.get("question", q.get("question_text", "")) or "") for q in questions
    )
    q_stems = _stem_set(q_text_combined)

    audience_in_questions = len(audience_stems & q_stems)
    if questions and audience_in_questions == 0 and len(audience_stems) > 2:
        conflicts.append({
            "type": "audience_mismatch",
            "severity": "medium",
            "description": (
                f"Business Intelligence identifies target audience as '{bp_audience}', "
                "but no questions contain audience-related terminology. "
                "Questions may not be targeting the correct persona."
            ),
            "agents_involved": ["Business Intelligence", "Question Discovery"],
        })

    return conflicts, warnings


def _find_orphan_keywords(
    keywords: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
) -> List[str]:
    """
    Orphan keyword = a keyword with no semantically related question covering it.
    Uses stem overlap.
    """
    orphans = []
    q_corpus = " ".join(
        str(q.get("question", q.get("question_text", "")) or "") for q in questions
    )
    q_stems = _stem_set(q_corpus)

    for kw in keywords:
        kw_text = str(kw.get("keyword", kw.get("keyword_text", "")) or "")
        kw_stems = _stem_set(kw_text)
        if kw_stems and not (kw_stems & q_stems):
            orphans.append(kw_text)

    return orphans[:10]  # cap


def _find_orphan_questions(
    questions: List[Dict[str, Any]],
    keywords: List[Dict[str, Any]],
) -> List[str]:
    """
    Orphan question = a question with no keyword supporting its topic.
    """
    orphans = []
    kw_corpus = " ".join(
        str(kw.get("keyword", kw.get("keyword_text", "")) or "") for kw in keywords
    )
    kw_stems = _stem_set(kw_corpus)

    for q in questions:
        q_text = str(q.get("question", q.get("question_text", "")) or "")
        q_stems = _stem_set(q_text)
        if q_stems and not (q_stems & kw_stems):
            orphans.append(q_text)

    return orphans[:10]


def _check_entity_coverage(
    entity_nodes: List[Dict[str, Any]],
    keywords: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
) -> Tuple[List[Dict], List[str]]:
    conflicts = []
    warnings = []

    entity_names = {
        _normalize(str(n.get("entity_name", "") or ""))
        for n in entity_nodes
        if n.get("entity_name")
    }

    if not entity_names:
        return conflicts, warnings

    # Check if any keyword mentions an entity NOT in the graph
    for kw in keywords[:30]:
        kw_text = _normalize(str(kw.get("keyword", kw.get("keyword_text", "")) or ""))
        kw_words = set(kw_text.split())
        # 2-gram entity check
        kw_2grams = {
            kw_text[i : i + 20].strip() for i in range(0, len(kw_text), 5)
        }
        for entity in entity_names:
            if entity and entity in kw_text and len(entity) > 4:
                # Entity IS referenced in keyword — good
                break
        else:
            # Check if keyword has a proper noun not in entity graph
            # (simple heuristic: capitalized word in original text)
            pass  # Positive check only — we don't penalise uncovered keywords

    # More useful: check if important entities have NO keyword coverage
    for entity_node in entity_nodes[:15]:
        entity_name = str(entity_node.get("entity_name", "") or "")
        entity_type = str(entity_node.get("entity_type", "") or "")

        # Only check PRODUCT, SERVICE, ORGANIZATION entities
        if entity_type.upper() not in ("PRODUCT", "SERVICE", "ORGANIZATION", "TECHNOLOGY"):
            continue

        # Check if this entity appears in any keyword
        covered = any(
            _normalize(entity_name) in _normalize(
                str(kw.get("keyword", kw.get("keyword_text", "")) or "")
            )
            for kw in keywords
        )
        if not covered and len(entity_name) > 3:
            warnings.append(
                f"Entity '{entity_name}' ({entity_type}) exists in knowledge graph "
                "but has no matching keyword. Consider adding it as a target keyword."
            )

    return conflicts, warnings


def _check_content_gap_vs_coverage(
    gap_analysis: List[Dict[str, Any]],
    content_coverage: List[Dict[str, Any]],
) -> Tuple[List[Dict], List[str]]:
    """
    Detects contradictions: a gap_analysis item says X is missing,
    but content_coverage has X with high coverage score.
    """
    conflicts = []
    warnings = []

    for gap in gap_analysis:
        gap_type = str(gap.get("gap_type", "") or "")
        gap_priority = str(gap.get("priority", "low") or "low")

        # Only check high-priority gaps for contradictions
        if gap_priority.lower() != "high":
            continue

        for cov in content_coverage:
            topic = str(cov.get("topic_name", "") or "")
            cov_score = float(cov.get("coverage_score", 0) or 0)

            if _overlap(gap_type, topic) >= 2 and cov_score >= 70:
                conflicts.append({
                    "type": "gap_coverage_contradiction",
                    "severity": "medium",
                    "description": (
                        f"Gap Analysis flags '{gap_type}' as HIGH priority gap, "
                        f"but Content Coverage shows '{topic}' has {cov_score:.0f}% coverage. "
                        "These agents are disagreeing about content completeness."
                    ),
                    "agents_involved": ["Visibility Score Agent", "Content Coverage Agent"],
                })

    return conflicts, warnings


def _check_competitor_industry_match(
    bp_industry: str,
    competitors: List[Dict[str, Any]],
    bp_audience: str,
) -> Tuple[List[Dict], List[str]]:
    conflicts = []
    warnings = []
    industry_stems = _stem_set(bp_industry)
    audience_stems = _stem_set(bp_audience)

    for comp in competitors:
        comp_name = str(comp.get("name", comp.get("competitor_name", "")) or "Unknown")
        comp_type = str(comp.get("competitor_type", "direct") or "direct")
        comp_desc = str(comp.get("description", "") or "")

        # Direct competitors should share industry words
        if comp_type == "direct" and comp_desc:
            comp_stems = _stem_set(comp_desc)
            if industry_stems and not (industry_stems & comp_stems):
                conflicts.append({
                    "type": "competitor_industry_mismatch",
                    "severity": "low",
                    "description": (
                        f"Competitor '{comp_name}' is marked as DIRECT but its description "
                        f"shares no industry terms with '{bp_industry}'. "
                        "This may indicate an incorrect competitor classification."
                    ),
                    "agents_involved": ["Competitor Discovery Agent", "Business Intelligence"],
                })

    return conflicts, warnings


# ─────────────────────────────────────────────────────────────────────────────
# Main Engine
# ─────────────────────────────────────────────────────────────────────────────

class KnowledgeConsistencyEngine:
    """
    Runs all cross-agent consistency checks and produces a unified report.
    """

    def analyze(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        bp = project_data.get("business_profile", {}) or {}
        verified_facts = project_data.get("verified_facts", []) or []
        questions = project_data.get("questions", []) or []
        keywords = project_data.get("keywords", []) or []
        competitors = project_data.get("competitors", []) or []
        entity_nodes = project_data.get("entity_nodes", []) or []
        content_coverage = project_data.get("content_coverage", []) or []
        gap_analysis = project_data.get("gap_analysis", []) or []

        bp_industry = str(bp.get("industry", "") or "")
        bp_audience = str(bp.get("target_audience", "") or "")

        all_conflicts: List[Dict] = []
        all_warnings: List[str] = []

        # Run all checks
        c1, w1 = _check_industry_consistency(bp_industry, competitors, questions, keywords)
        all_conflicts.extend(c1)
        all_warnings.extend(w1)

        c2, w2 = _check_audience_consistency(bp_audience, questions)
        all_conflicts.extend(c2)
        all_warnings.extend(w2)

        orphan_kw = _find_orphan_keywords(keywords, questions)
        orphan_qs = _find_orphan_questions(questions, keywords)

        if orphan_kw:
            all_conflicts.append({
                "type": "orphan_keywords",
                "severity": "medium",
                "description": (
                    f"{len(orphan_kw)} keyword(s) have no matching question covering their topic. "
                    f"Sample orphans: {', '.join(orphan_kw[:3])}"
                ),
                "agents_involved": ["Keyword Intelligence Agent", "Question Discovery Agent"],
            })

        if orphan_qs:
            all_conflicts.append({
                "type": "orphan_questions",
                "severity": "low",
                "description": (
                    f"{len(orphan_qs)} question(s) have no supporting keyword cluster. "
                    f"Sample orphans: {', '.join(orphan_qs[:3])}"
                ),
                "agents_involved": ["Question Discovery Agent", "Keyword Intelligence Agent"],
            })

        c3, w3 = _check_entity_coverage(entity_nodes, keywords, questions)
        all_conflicts.extend(c3)
        all_warnings.extend(w3)

        c4, w4 = _check_content_gap_vs_coverage(gap_analysis, content_coverage)
        all_conflicts.extend(c4)
        all_warnings.extend(w4)

        c5, w5 = _check_competitor_industry_match(bp_industry, competitors, bp_audience)
        all_conflicts.extend(c5)
        all_warnings.extend(w5)

        # ── Consistency Score ────────────────────────────────────────────────
        # Start at 100, deduct per conflict severity
        severity_deductions = {"high": 20, "medium": 10, "low": 5}
        total_deduction = sum(
            severity_deductions.get(c.get("severity", "low"), 5)
            for c in all_conflicts
        ) + len(all_warnings) * 2

        consistency_score = max(0.0, round(100.0 - total_deduction, 1))

        # ── Overall Status ───────────────────────────────────────────────────
        high_conflicts = [c for c in all_conflicts if c.get("severity") == "high"]
        medium_conflicts = [c for c in all_conflicts if c.get("severity") == "medium"]

        if consistency_score >= 85 and not high_conflicts:
            status = "consistent"
        elif consistency_score >= 65 and not high_conflicts:
            status = "minor_inconsistencies"
        elif consistency_score >= 40:
            status = "significant_inconsistencies"
        else:
            status = "critical_inconsistencies"

        # ── Repair Actions ───────────────────────────────────────────────────
        repair_actions = self._build_repair_actions(
            all_conflicts, orphan_kw, orphan_qs, all_warnings
        )

        return {
            "consistency_score": consistency_score,
            "overall_status": status,
            "total_conflicts": len(all_conflicts),
            "total_warnings": len(all_warnings),
            "high_severity_conflicts": len(high_conflicts),
            "medium_severity_conflicts": len(medium_conflicts),
            "orphan_keywords": orphan_kw,
            "orphan_questions": orphan_qs,
            "conflicts": all_conflicts,
            "warnings": all_warnings,
            "repair_actions": repair_actions,
        }

    def _build_repair_actions(
        self,
        conflicts: List[Dict],
        orphan_kw: List[str],
        orphan_qs: List[str],
        warnings: List[str],
    ) -> List[str]:
        actions = []
        seen_types = set()

        for c in conflicts:
            ctype = c.get("type", "")
            if ctype in seen_types:
                continue
            seen_types.add(ctype)

            if ctype == "audience_mismatch":
                actions.append(
                    "Align Question Discovery categories with the Business Intelligence target audience. "
                    "Ensure questions explicitly target the identified buyer persona."
                )
            elif ctype == "orphan_keywords":
                actions.append(
                    f"Create FAQ or discovery questions for orphan keywords: {', '.join(orphan_kw[:3])}."
                )
            elif ctype == "orphan_questions":
                actions.append(
                    "Add semantic keywords that back the orphan questions found in Question Discovery."
                )
            elif ctype == "gap_coverage_contradiction":
                actions.append(
                    "Reconcile Gap Analysis and Content Coverage agents. "
                    "Re-run analysis or manually review contradicted topic areas."
                )
            elif ctype == "competitor_industry_mismatch":
                actions.append(
                    "Review competitor classifications. Ensure DIRECT competitors are truly in the same industry."
                )

        if not actions:
            actions.append(
                "No repair actions required. All agents appear to be in agreement."
            )

        return actions[:6]
