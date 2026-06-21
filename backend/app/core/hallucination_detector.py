"""
hallucination_detector.py

HallucinationDetector — pure-Python, deterministic verification of AI-generated claims
against crawled page content and verified facts.

NO LLM calls. NO deletions. Only flags.

Flag Levels:
  VERIFIED             — strong word overlap with facts (>=3 words)
  LOW_CONFIDENCE       — weak overlap (1-2 words)
  UNSUPPORTED          — zero overlap with any fact or page
  POSSIBLE_HALLUCINATION — zero overlap AND text contains suspiciously specific
                           unverifiable claims (numbers, proper nouns, certifications)
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", (text or "").lower()).strip()


def _content_words(text: str) -> set:
    """Returns meaningful words (length > 3) from text."""
    return {w for w in _normalize(text).split() if len(w) > 3}


def _overlap_count(claim: str, evidence: str) -> int:
    return len(_content_words(claim) & _content_words(evidence))


def _is_suspiciously_specific(text: str) -> bool:
    """Detects suspiciously specific claims: numbers, % figures, proper-noun-heavy text."""
    patterns = [
        r"\d+[\.,]\d+",       # decimal numbers  e.g. 4.8, 98.7
        r"\d+%",               # percentages
        r"\$\d+",              # dollar amounts
        r"#\d+\s+in",          # ranking claims e.g. "#1 in"
        r"\b(ISO|SOC|HIPAA|GDPR|FERPA)\s*\d*\b",  # specific certifications
        r"\b(awarded|won|ranked|named|certified)\b",  # claim verbs
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _build_evidence_corpus(
    verified_facts: List[Dict[str, Any]],
    crawled_pages: List[Dict[str, Any]],
) -> str:
    """Concatenates all verified fact values and page content for overlap checking."""
    fact_texts = []
    for f in verified_facts:
        val = str(f.get("fact_value", "") or f.get("evidence", "") or "")
        if val:
            fact_texts.append(val)

    page_texts = []
    for p in crawled_pages:
        content = str(p.get("content", "") or p.get("markdown_content", "") or "")
        title = str(p.get("title", "") or "")
        if content:
            page_texts.append(content[:2000])
        if title:
            page_texts.append(title)

    return " ".join(fact_texts + page_texts)


def _flag_item(
    item_text: str,
    corpus: str,
    item_type: str,
) -> Dict[str, Any]:
    """
    Flags a single item against the evidence corpus.
    Returns a structured flag record.
    """
    if not item_text or item_text.strip().upper() in ("NOT FOUND", "NOT_FOUND", "N/A", ""):
        return None  # Skip placeholder values

    overlap = _overlap_count(item_text, corpus)

    if overlap >= 3:
        flag = "VERIFIED"
        confidence = min(100, 60 + overlap * 5)
    elif overlap >= 1:
        flag = "LOW_CONFIDENCE"
        confidence = 30 + overlap * 10
    elif _is_suspiciously_specific(item_text):
        flag = "POSSIBLE_HALLUCINATION"
        confidence = 10
    else:
        flag = "UNSUPPORTED"
        confidence = 20

    # Find best supporting evidence snippet
    supporting_snippet = ""
    if overlap >= 1:
        # Find the sentence in corpus most overlapping with the claim
        sentences = re.split(r"[.!?\n]", corpus)
        best_ov = 0
        for sent in sentences[:200]:  # cap scan
            ov = _overlap_count(item_text, sent)
            if ov > best_ov:
                best_ov = ov
                supporting_snippet = sent.strip()[:200]

    return {
        "item_type": item_type,
        "item_text": item_text[:300],
        "flag_level": flag,
        "overlap_count": overlap,
        "confidence_pct": confidence,
        "supporting_evidence": supporting_snippet,
        "is_suspiciously_specific": _is_suspiciously_specific(item_text),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main Detector
# ─────────────────────────────────────────────────────────────────────────────

class HallucinationDetector:
    """
    Checks every AI-generated claim in the project against the evidence corpus.
    Never deletes. Only flags.
    """

    def detect(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point.
        project_data must contain: business_profile, verified_facts, crawled_pages,
        competitors, questions, keywords, content_opportunities, blogs.
        """
        bp = project_data.get("business_profile", {}) or {}
        verified_facts = project_data.get("verified_facts", []) or []
        crawled_pages = project_data.get("crawled_pages", []) or []
        competitors = project_data.get("competitors", []) or []
        questions = project_data.get("questions", []) or []
        keywords = project_data.get("keywords", []) or []
        content_opportunities = project_data.get("content_opportunities", []) or []
        blogs = project_data.get("blogs", []) or []

        corpus = _build_evidence_corpus(verified_facts, crawled_pages)

        flags: List[Dict[str, Any]] = []

        # ── Business Profile Claims ──────────────────────────────────────────
        for field, itype in [
            ("usp", "USP"),
            ("description", "Description"),
            ("mission", "Mission"),
            ("vision", "Vision"),
        ]:
            val = str(bp.get(field, "") or "")
            flag = _flag_item(val, corpus, itype)
            if flag:
                flags.append(flag)

        # Strengths
        for strength in (bp.get("strengths", []) or []):
            flag = _flag_item(str(strength), corpus, "Strength")
            if flag:
                flags.append(flag)

        # Trust signals
        for sig in (bp.get("trust_signals", []) or []):
            flag = _flag_item(str(sig), corpus, "Trust Signal")
            if flag:
                flags.append(flag)

        # ── Competitors ──────────────────────────────────────────────────────
        for comp in competitors:
            comp_name = str(comp.get("name", comp.get("competitor_name", "")) or "")
            flag = _flag_item(comp_name, corpus, "Competitor Name")
            if flag:
                flags.append(flag)
            comp_desc = str(comp.get("description", "") or "")
            flag2 = _flag_item(comp_desc, corpus, "Competitor Description")
            if flag2:
                flags.append(flag2)

        # ── Questions ────────────────────────────────────────────────────────
        for q in questions[:20]:  # cap at 20 for performance
            q_text = str(q.get("question", q.get("question_text", "")) or "")
            flag = _flag_item(q_text, corpus, "Question")
            if flag:
                flags.append(flag)

        # ── Keywords ─────────────────────────────────────────────────────────
        for kw in keywords[:30]:  # cap at 30
            kw_text = str(kw.get("keyword", kw.get("keyword_text", "")) or "")
            flag = _flag_item(kw_text, corpus, "Keyword")
            if flag:
                flags.append(flag)

        # ── Content Opportunities ────────────────────────────────────────────
        for opp in content_opportunities:
            reason = str(opp.get("reason", "") or "")
            flag = _flag_item(reason, corpus, "Content Opportunity Reason")
            if flag:
                flags.append(flag)

        # ── Blogs ────────────────────────────────────────────────────────────
        for blog in blogs[:10]:
            title = str(blog.get("title", "") or "")
            flag = _flag_item(title, corpus, "Blog Title")
            if flag:
                flags.append(flag)

        # Filter out None values
        flags = [f for f in flags if f is not None]

        # ── Summary Statistics ───────────────────────────────────────────────
        total = len(flags)
        by_level: Dict[str, int] = {}
        for f in flags:
            lvl = f["flag_level"]
            by_level[lvl] = by_level.get(lvl, 0) + 1

        verified_count = by_level.get("VERIFIED", 0)
        low_conf_count = by_level.get("LOW_CONFIDENCE", 0)
        unsupported_count = by_level.get("UNSUPPORTED", 0)
        hallucination_count = by_level.get("POSSIBLE_HALLUCINATION", 0)

        # Hallucination risk score (0-100, lower is better)
        if total > 0:
            risk_score = round(
                ((unsupported_count * 1.0 + hallucination_count * 2.0) / total) * 100,
                1,
            )
        else:
            risk_score = 0.0

        # Overall grounding rate
        grounding_rate = round(
            ((verified_count + low_conf_count * 0.5) / max(total, 1)) * 100, 1
        )

        # Overall status
        if hallucination_count == 0 and unsupported_count == 0:
            status = "clean"
        elif hallucination_count == 0 and unsupported_count <= 3:
            status = "low_risk"
        elif hallucination_count <= 2:
            status = "medium_risk"
        else:
            status = "high_risk"

        return {
            "total_items_checked": total,
            "hallucination_risk_score": risk_score,
            "grounding_rate": grounding_rate,
            "overall_status": status,
            "by_level": {
                "VERIFIED": verified_count,
                "LOW_CONFIDENCE": low_conf_count,
                "UNSUPPORTED": unsupported_count,
                "POSSIBLE_HALLUCINATION": hallucination_count,
            },
            "flags": flags,
            "recommendations": self._build_recommendations(
                hallucination_count, unsupported_count, low_conf_count
            ),
        }

    def _build_recommendations(
        self,
        hallucination_count: int,
        unsupported_count: int,
        low_conf_count: int,
    ) -> List[str]:
        recs = []
        if hallucination_count > 0:
            recs.append(
                f"Review {hallucination_count} POSSIBLE_HALLUCINATION item(s) immediately. "
                "These contain specific claims (numbers, certifications, rankings) with no factual backing."
            )
        if unsupported_count > 0:
            recs.append(
                f"{unsupported_count} UNSUPPORTED item(s) detected. "
                "Add evidence pages or remove/soften these claims."
            )
        if low_conf_count > 0:
            recs.append(
                f"{low_conf_count} LOW_CONFIDENCE item(s) found. "
                "Strengthen these by adding supporting content pages or factual citations."
            )
        if not recs:
            recs.append(
                "No hallucination risks detected. All checked items are grounded in crawled evidence."
            )
        return recs
