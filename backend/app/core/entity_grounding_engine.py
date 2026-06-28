"""
entity_grounding_engine.py

A pure-Python entity grounding engine that validates AI-generated facts and profiles 
against the crawled website content. Computes a Grounding Score and checks for domain confusion.
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """Normalize text by converting to lowercase, removing punctuation, and collapsing whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return " ".join(text.split())

class EntityGroundingEngine:
    def __init__(self):
        pass

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the grounding validation on the generated final state.
        Returns:
            Dict containing:
                - grounding_score: float (0.0 to 100.0)
                - domain_confusion: str ("YES" or "NO")
                - status: str ("PASSED" or "FAILED_GROUNDING")
                - details: Dict of checked categories and their results
        """
        website_url = state.get("website_url", "")
        crawled_pages = state.get("crawled_pages", [])
        verified_facts = state.get("verified_facts", [])
        bi = state.get("business_intelligence", {}) or {}
        questions = state.get("questions", [])
        keywords = state.get("keywords", [])
        
        # 1. Compile normalized corpus of crawled pages
        page_contents = []
        page_map = {} # url -> normalized_content
        
        for page in crawled_pages:
            url = page.get("url", "")
            title = page.get("title", "") or ""
            content = page.get("markdown_content", "") or ""
            
            norm_content = normalize_text(title + " " + content)
            page_contents.append(norm_content)
            if url:
                page_map[url] = norm_content
                
        corpus = " ".join(page_contents)
        
        # 2. Check for Domain Confusion (historic library references on EdTech domain)
        domain_confusion = "NO"
        is_target_domain = "thelibrarycompany.com" in website_url.lower()
        
        # forbidden historic terms
        forbidden_terms = [
            "philadelphia", "benjamin franklin", "franklin", "1731", 
            "rare books", "historic library", "historic archive", 
            "revolutionary war", "american philosophical society"
        ]
        
        # Gather all text outputs to scan for domain confusion
        all_output_texts = []
        all_output_texts.append(bi.get("company_name", ""))
        all_output_texts.append(bi.get("industry", ""))
        all_output_texts.append(bi.get("description", ""))
        all_output_texts.append(bi.get("mission", ""))
        all_output_texts.append(bi.get("vision", ""))
        all_output_texts.append(bi.get("usp", ""))
        all_output_texts.extend(bi.get("strengths", []))
        all_output_texts.extend(bi.get("weaknesses", []))
        all_output_texts.extend(bi.get("opportunities", []))
        all_output_texts.extend(bi.get("risks", []))
        all_output_texts.extend(bi.get("trust_signals", []))
        
        pre_query = bi.get("pre_query_discovery", {}) or {}
        all_output_texts.extend(pre_query.get("products", []))
        all_output_texts.extend(pre_query.get("services", []))
        all_output_texts.extend(pre_query.get("technologies", []))
        
        for q in questions:
            all_output_texts.append(q.get("question", ""))
            all_output_texts.append(q.get("recommended_answer", ""))
            
        for kw in keywords:
            all_output_texts.append(kw.get("keyword", ""))
            
        for fact in verified_facts:
            all_output_texts.append(fact.get("fact_value", ""))
            all_output_texts.append(fact.get("evidence_text", ""))
            
        combined_outputs_text = " ".join(all_output_texts).lower()
        
        if is_target_domain:
            for term in forbidden_terms:
                if term in combined_outputs_text:
                    logger.warning(f"[EntityGroundingEngine] Critical domain confusion detected! Text contains forbidden term: '{term}'")
                    domain_confusion = "YES"
                    
        # 3. Grounding checks for entities and facts
        total_checks = 0
        successful_checks = 0
        checks_details = []
        
        def add_check(item_name: str, item_value: str, matched: bool, detail: str = ""):
            nonlocal total_checks, successful_checks
            total_checks += 1
            if matched:
                successful_checks += 1
            checks_details.append({
                "item": item_name,
                "value": item_value,
                "matched": matched,
                "detail": detail
            })
            
        # A. Check Company Name
        company_name = bi.get("company_name", "")
        if company_name and company_name.upper() not in ("UNKNOWN", "UNKNOWN COMPANY"):
            norm_comp = normalize_text(company_name)
            # Support partial match or substring match
            is_matched = norm_comp in corpus or any(part in corpus for part in norm_comp.split() if len(part) > 3)
            add_check("Company Name", company_name, is_matched, "Checked against crawled corpus")
            
        # B. Check Products in Business Intelligence Profile
        products = pre_query.get("products", [])
        for p in products:
            if p and p.upper() != "NOT_FOUND":
                norm_p = normalize_text(p)
                is_matched = norm_p in corpus or any(part in corpus for part in norm_p.split() if len(part) > 3)
                add_check(f"Product: {p}", p, is_matched, "Checked against crawled corpus")
                
        # C. Check Services in Business Intelligence Profile
        services = pre_query.get("services", [])
        for s in services:
            if s and s.upper() != "NOT_FOUND":
                norm_s = normalize_text(s)
                is_matched = norm_s in corpus or any(part in corpus for part in norm_s.split() if len(part) > 3)
                add_check(f"Service: {s}", s, is_matched, "Checked against crawled corpus")
                
        # D. Check Facts (value and evidence verification)
        for idx, fact in enumerate(verified_facts):
            fact_val = fact.get("fact_value", "")
            evidence = fact.get("evidence_text", "")
            source_url = fact.get("source_url", "")
            category = fact.get("fact_category", "general")
            
            # Check fact value exists in the overall corpus
            if fact_val:
                norm_val = normalize_text(fact_val)
                # Try full value match, fallback to token overlap if long
                val_matched = norm_val in corpus
                if not val_matched and len(norm_val.split()) > 3:
                    val_matched = any(part in corpus for part in norm_val.split() if len(part) > 3)
                add_check(f"Fact Value #{idx} (cat: {category})", fact_val, val_matched, "Checked value against corpus")
                
            # Verify evidence text matches verbatim page content
            if evidence:
                norm_ev = normalize_text(evidence)
                ev_matched = False
                
                # Check specific page first if source_url is available
                if source_url and source_url in page_map:
                    page_content = page_map[source_url]
                    ev_matched = norm_ev in page_content
                    detail_str = f"Checked evidence against page: {source_url}"
                else:
                    ev_matched = norm_ev in corpus
                    detail_str = "Checked evidence against overall corpus"
                    
                add_check(f"Fact Evidence #{idx}", evidence[:60] + "...", ev_matched, detail_str)
            else:
                # Missing evidence text is a grounding failure
                add_check(f"Fact Evidence #{idx}", "MISSING", False, "No evidence text supplied for verified fact")
                
        # 4. Compute grounding score
        if domain_confusion == "YES":
            grounding_score = 0.0
            status = "FAILED_GROUNDING"
            logger.error("[EntityGroundingEngine] Grounding check FAILED due to critical Domain Confusion.")
        else:
            if total_checks > 0:
                grounding_score = (successful_checks / total_checks) * 100.0
            else:
                grounding_score = 100.0
                
            status = "PASSED" if grounding_score >= 80.0 else "FAILED_GROUNDING"
            
        logger.info(f"[EntityGroundingEngine] Run completed. Score: {grounding_score:.2f}%. Status: {status}. Total Checks: {total_checks}, Passed: {successful_checks}")
        
        return {
            "grounding_score": grounding_score,
            "domain_confusion": domain_confusion,
            "status": status,
            "details": {
                "total_checks": total_checks,
                "successful_checks": successful_checks,
                "checks": checks_details
            }
        }
