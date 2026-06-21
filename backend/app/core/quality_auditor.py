"""
quality_auditor.py

Pure-Python, deterministic quality auditors for Questions and Keywords.
No LLM calls. No random offsets. Uses structural heuristics only.
"""

from __future__ import annotations
import re
import math
from typing import List, Dict, Any, Tuple
from collections import Counter


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Lowercase and strip punctuation for comparison."""
    return re.sub(r"[^a-z0-9\s]", "", text.lower()).strip()


def _word_set(text: str) -> set:
    return set(_normalize(text).split())


def _jaccard(a: str, b: str) -> float:
    """Jaccard similarity between two strings."""
    sa, sb = _word_set(a), _word_set(b)
    if not sa and not sb:
        return 1.0
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)


def _stem(word: str) -> str:
    """Minimal suffix-stripping stemmer (avoids NLTK dependency)."""
    word = word.lower()
    for suffix in ("ing", "tion", "ness", "ment", "ers", "es", "ed", "ly", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _stem_set(text: str) -> set:
    return {_stem(w) for w in _normalize(text).split() if len(w) > 3}


# ──────────────────────────────────────────────────────────────────────────────
# Question Quality Auditor
# ──────────────────────────────────────────────────────────────────────────────

class QuestionQualityAuditor:
    """
    Audits a list of question records for:
      1. Duplicate / near-duplicate questions
      2. Template over-use (same structural pattern repeated)
      3. Semantic diversity across categories
      4. Missing recommended_answer fields
      5. Confidence score distribution health
    """

    SIMILARITY_THRESHOLD = 0.72   # Jaccard ≥ this → flagged as near-duplicate
    MAX_TEMPLATE_REUSE = 0.30     # If >30% share same prefix pattern → flagged
    MIN_DIVERSITY_RATIO = 0.60    # Unique category proportion threshold

    def audit(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not questions:
            return self._empty_report()

        texts = [q.get("question", q.get("question_text", "")) for q in questions]
        categories = [q.get("question_type", q.get("category", "")) for q in questions]

        duplicates = self._find_duplicates(texts)
        template_violations = self._find_template_overuse(texts)
        diversity = self._diversity_score(categories)
        missing_answers = self._count_missing_answers(questions)
        confidence_health = self._confidence_distribution(questions)
        uniqueness_score = self._uniqueness_score(texts)

        warnings: List[str] = []
        suggestions: List[str] = []

        if duplicates["count"] > 0:
            warnings.append(
                f"{duplicates['count']} near-duplicate question pairs detected "
                f"(Jaccard >= {self.SIMILARITY_THRESHOLD:.0%})"
            )
            suggestions.append(
                "De-duplicate questions by merging similar phrasing variants."
            )

        if template_violations:
            warnings.append(
                f"Template over-use detected: pattern '{template_violations[0]}' "
                f"accounts for >={self.MAX_TEMPLATE_REUSE:.0%} of all questions."
            )
            suggestions.append(
                "Diversify question phrasing to avoid repetitive patterns."
            )

        if diversity["ratio"] < self.MIN_DIVERSITY_RATIO:
            warnings.append(
                f"Low category diversity: only {diversity['unique_categories']} unique "
                f"categories across {diversity['total']} questions."
            )
            suggestions.append(
                "Expand question generation to cover underrepresented categories."
            )

        if missing_answers > 0:
            warnings.append(
                f"{missing_answers} questions are missing a recommended_answer field."
            )
            suggestions.append(
                "Ensure every question has an optimized answer context for LLM coverage."
            )

        if confidence_health["low_confidence_count"] > 0:
            warnings.append(
                f"{confidence_health['low_confidence_count']} questions have "
                f"confidence < 60%."
            )
            suggestions.append(
                "Review low-confidence questions; consider re-running the extractor."
            )

        # Compute overall quality score (0–100)
        penalty = (
            min(duplicates["count"] * 3, 30)
            + (10 if template_violations else 0)
            + (10 if diversity["ratio"] < self.MIN_DIVERSITY_RATIO else 0)
            + min(missing_answers * 2, 20)
            + min(confidence_health["low_confidence_count"] * 2, 20)
        )
        quality_score = max(0, 100 - penalty)

        return {
            "total_questions": len(questions),
            "quality_score": quality_score,
            "uniqueness_score": uniqueness_score,
            "duplicate_pairs": duplicates["pairs"],
            "duplicate_count": duplicates["count"],
            "template_violations": template_violations,
            "category_diversity": diversity,
            "missing_answers": missing_answers,
            "confidence_health": confidence_health,
            "warnings": warnings,
            "suggestions": suggestions,
        }

    def _find_duplicates(self, texts: List[str]) -> Dict[str, Any]:
        pairs: List[Tuple[int, int, float]] = []
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                sim = _jaccard(texts[i], texts[j])
                if sim >= self.SIMILARITY_THRESHOLD:
                    pairs.append((i, j, round(sim, 3)))
        return {"count": len(pairs), "pairs": pairs[:20]}  # cap at 20 for payload

    def _find_template_overuse(self, texts: List[str]) -> List[str]:
        """Detect over-used 3-word prefix patterns."""
        patterns: Counter = Counter()
        for t in texts:
            words = _normalize(t).split()
            if len(words) >= 3:
                prefix = " ".join(words[:3])
                patterns[prefix] += 1

        violations = []
        total = len(texts)
        for pattern, count in patterns.most_common(5):
            if total > 0 and count / total >= self.MAX_TEMPLATE_REUSE:
                violations.append(pattern)
        return violations

    def _diversity_score(self, categories: List[str]) -> Dict[str, Any]:
        unique = set(c for c in categories if c)
        dist = Counter(categories)
        return {
            "total": len(categories),
            "unique_categories": len(unique),
            "ratio": round(len(unique) / max(len(categories), 1), 3),
            "distribution": dict(dist.most_common()),
        }

    def _count_missing_answers(self, questions: List[Dict[str, Any]]) -> int:
        return sum(
            1 for q in questions
            if not (q.get("recommended_answer") or "").strip()
        )

    def _confidence_distribution(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        scores = [float(q.get("confidence_score", 1.0)) for q in questions]
        if not scores:
            return {"mean": 1.0, "low_confidence_count": 0, "below_threshold": 0.6}
        mean = sum(scores) / len(scores)
        low = sum(1 for s in scores if s < 0.6)
        return {
            "mean": round(mean, 3),
            "low_confidence_count": low,
            "below_threshold": 0.6,
        }

    def _uniqueness_score(self, texts: List[str]) -> int:
        """
        Score 0–100: measures how unique each question is across the full set.
        Uses pairwise Jaccard on stem sets for efficiency.
        """
        if len(texts) <= 1:
            return 100

        total_sim = 0.0
        comparisons = 0
        stems = [_stem_set(t) for t in texts]

        # Sample to keep O(n) for large sets
        sample_size = min(len(texts), 30)
        indices = list(range(sample_size))

        for i in indices:
            for j in indices:
                if i >= j:
                    continue
                sa, sb = stems[i], stems[j]
                union = sa | sb
                sim = len(sa & sb) / len(union) if union else 0.0
                total_sim += sim
                comparisons += 1

        if comparisons == 0:
            return 100

        avg_sim = total_sim / comparisons
        return max(0, round(100 - avg_sim * 100))

    def _empty_report(self) -> Dict[str, Any]:
        return {
            "total_questions": 0,
            "quality_score": 100,
            "uniqueness_score": 100,
            "duplicate_pairs": [],
            "duplicate_count": 0,
            "template_violations": [],
            "category_diversity": {"total": 0, "unique_categories": 0, "ratio": 1.0, "distribution": {}},
            "missing_answers": 0,
            "confidence_health": {"mean": 1.0, "low_confidence_count": 0, "below_threshold": 0.6},
            "warnings": [],
            "suggestions": [],
        }


# ──────────────────────────────────────────────────────────────────────────────
# Keyword Quality Auditor
# ──────────────────────────────────────────────────────────────────────────────

class KeywordQualityAuditor:
    """
    Audits a list of keyword records for:
      1. Duplicate stems (over-indexing on same root)
      2. Single-category saturation
      3. Search intent coverage gaps
      4. Missing cluster assignments
      5. Priority / confidence health
    """

    MAX_STEM_DUPLICATION = 0.25      # >25% share same stem root → issue
    MAX_CATEGORY_SATURATION = 0.50   # >50% in one category → flagged
    INTENTS = {"informational", "transactional", "navigational", "commercial"}
    MIN_INTENT_COVERAGE = 2          # At least 2 different intents expected

    def audit(self, keywords: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not keywords:
            return self._empty_report()

        texts = [kw.get("keyword", kw.get("keyword_text", "")) for kw in keywords]
        categories = [kw.get("keyword_type", kw.get("category", "")) for kw in keywords]
        intents = [kw.get("intent", kw.get("search_intent", "")) for kw in keywords]
        clusters = [kw.get("cluster", kw.get("clustering_theme", "")) for kw in keywords]

        stem_duplication = self._stem_duplication(texts)
        category_saturation = self._category_saturation(categories)
        intent_coverage = self._intent_coverage(intents)
        missing_clusters = sum(1 for c in clusters if not c or c.lower() in ("", "general", "none"))
        priority_health = self._priority_health(keywords)
        uniqueness_score = self._uniqueness_score(texts)

        warnings: List[str] = []
        suggestions: List[str] = []

        if stem_duplication["rate"] > self.MAX_STEM_DUPLICATION:
            warnings.append(
                f"High stem duplication: {stem_duplication['rate']:.0%} of keywords share "
                f"the same root. Top duplicate stems: {', '.join(stem_duplication['top_stems'][:3])}"
            )
            suggestions.append(
                "Consolidate keyword variants sharing the same stem into single canonical entries."
            )

        if category_saturation["saturated"]:
            warnings.append(
                f"Category saturation: '{category_saturation['top_category']}' represents "
                f"{category_saturation['rate']:.0%} of all keywords."
            )
            suggestions.append(
                "Diversify keyword generation across more category types."
            )

        if intent_coverage["unique_count"] < self.MIN_INTENT_COVERAGE:
            warnings.append(
                f"Low search intent diversity: only {intent_coverage['unique_count']} unique "
                f"intents detected ({', '.join(intent_coverage['present'])})."
            )
            missing = self.INTENTS - set(intent_coverage["present"])
            if missing:
                suggestions.append(
                    f"Expand to cover missing search intents: {', '.join(missing)}."
                )

        if missing_clusters > 0:
            warnings.append(
                f"{missing_clusters} keywords have no cluster theme assigned."
            )
            suggestions.append(
                "Assign clustering themes to all keywords to enable topical grouping."
            )

        if priority_health["low_priority_count"] > len(keywords) * 0.5:
            warnings.append(
                "More than 50% of keywords are marked as Low priority."
            )
            suggestions.append(
                "Review priority scoring to ensure High/Medium keywords are properly surfaced."
            )

        penalty = (
            min(int(stem_duplication["rate"] * 40), 30)
            + (10 if category_saturation["saturated"] else 0)
            + (15 if intent_coverage["unique_count"] < self.MIN_INTENT_COVERAGE else 0)
            + min(missing_clusters * 2, 15)
        )
        quality_score = max(0, 100 - penalty)

        return {
            "total_keywords": len(keywords),
            "quality_score": quality_score,
            "uniqueness_score": uniqueness_score,
            "stem_duplication": stem_duplication,
            "category_saturation": category_saturation,
            "intent_coverage": intent_coverage,
            "missing_clusters": missing_clusters,
            "priority_health": priority_health,
            "warnings": warnings,
            "suggestions": suggestions,
        }

    def _stem_duplication(self, texts: List[str]) -> Dict[str, Any]:
        stem_counts: Counter = Counter()
        for t in texts:
            for w in _normalize(t).split():
                if len(w) > 3:
                    stem_counts[_stem(w)] += 1

        total = len(texts)
        duplicated = sum(1 for t in texts if any(
            stem_counts[_stem(w)] > 1
            for w in _normalize(t).split() if len(w) > 3
        ))
        rate = duplicated / total if total else 0.0
        top_stems = [s for s, _ in stem_counts.most_common(5) if stem_counts[s] > 1]
        return {
            "rate": round(rate, 3),
            "duplicated_count": duplicated,
            "top_stems": top_stems,
        }

    def _category_saturation(self, categories: List[str]) -> Dict[str, Any]:
        if not categories:
            return {"saturated": False, "top_category": "", "rate": 0.0, "distribution": {}}
        dist = Counter(c for c in categories if c)
        total = len(categories)
        top_cat, top_count = dist.most_common(1)[0] if dist else ("", 0)
        rate = top_count / total if total else 0.0
        return {
            "saturated": rate > self.MAX_CATEGORY_SATURATION,
            "top_category": top_cat,
            "rate": round(rate, 3),
            "distribution": dict(dist.most_common()),
        }

    def _intent_coverage(self, intents: List[str]) -> Dict[str, Any]:
        present = {i.lower() for i in intents if i and i.lower() in self.INTENTS}
        missing = self.INTENTS - present
        return {
            "present": sorted(present),
            "missing": sorted(missing),
            "unique_count": len(present),
        }

    def _priority_health(self, keywords: List[Dict[str, Any]]) -> Dict[str, Any]:
        priorities = Counter(kw.get("priority", "Medium") for kw in keywords)
        return {
            "high_count": priorities.get("High", 0),
            "medium_count": priorities.get("Medium", 0),
            "low_count": priorities.get("Low", 0),
            "low_priority_count": priorities.get("Low", 0),
            "distribution": dict(priorities),
        }

    def _uniqueness_score(self, texts: List[str]) -> int:
        if len(texts) <= 1:
            return 100
        exact_set: set = set()
        duplicates = 0
        for t in texts:
            norm = _normalize(t)
            if norm in exact_set:
                duplicates += 1
            else:
                exact_set.add(norm)
        return max(0, round(100 - (duplicates / len(texts)) * 100))

    def _empty_report(self) -> Dict[str, Any]:
        return {
            "total_keywords": 0,
            "quality_score": 100,
            "uniqueness_score": 100,
            "stem_duplication": {"rate": 0.0, "duplicated_count": 0, "top_stems": []},
            "category_saturation": {"saturated": False, "top_category": "", "rate": 0.0, "distribution": {}},
            "intent_coverage": {"present": [], "missing": [], "unique_count": 0},
            "missing_clusters": 0,
            "priority_health": {"high_count": 0, "medium_count": 0, "low_count": 0, "low_priority_count": 0, "distribution": {}},
            "warnings": [],
            "suggestions": [],
        }
