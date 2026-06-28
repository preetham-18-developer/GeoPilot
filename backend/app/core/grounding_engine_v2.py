"""
grounding_engine_v2.py

A completely generic and universal grounding validation engine.
Verifies all AI-generated entities (company names, products, services, founders, etc.)
against the crawled pages, verified facts, and entity graph.
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """Standardizes text by converting to lowercase and stripping punctuation/whitespace."""
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return " ".join(text.split())

def token_overlap_ratio(text1: str, text2: str) -> float:
    """Calculates the ratio of words in text1 that exist in text2."""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    if not norm1 or not norm2:
        return 0.0
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    if not words1:
        return 0.0
    matching_words = words1.intersection(words2)
    return len(matching_words) / len(words1)

def is_generic_placeholder(text: str) -> bool:
    """Checks if the given text is a generic placeholder or fallback text from LLM extraction."""
    if not text:
        return True
    val = str(text).strip().upper()
    placeholders = {
        "UNKNOWN", "UNKNOWN COMPANY", "THE BUSINESS", "BUSINESS", "COMPANY", "COMPANY FOUNDERS", "COMPANY FOUNDER",
        "FOUNDER", "FOUNDERS", "UNKNOWN FOUNDER", "UNKNOWN FOUNDERS", "NOT FOUND", "NOT_FOUND", "N/A", "NA", 
        "NONE", "NOT AVAILABLE", "NOT_AVAILABLE", "NULL", "UNDEFINED", "NOT_FOUND"
    }
    if val in placeholders:
        return True
    # Pattern match for generic variations
    if re.match(r"^(UNKNOWN|NOT[\s_-]?FOUND|NOT[\s_-]?AVAILABLE|NONE|N/A)$", val):
        return True
    return False

class GroundingEngineV2:
    def __init__(self):
        pass

    def run(self, state: Dict[str, Any], identity_res: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Validates all generated outputs in the state against ground truth.
        """
        website_url = state.get("website_url", "")
        crawled_pages = state.get("crawled_pages", [])
        
        # If corpus is empty or extremely minimal (e.g. < 150 words), bypass checks
        total_word_count = sum(len((p.get("markdown_content", "") or p.get("content", "") or "").split()) for p in crawled_pages)
        if total_word_count < 150:
            logger.warning(f"[GroundingEngineV2] Crawled corpus is minimal ({total_word_count} words). Bypassing grounding checks.")
            return {
                "grounding_score": 100.0,
                "hallucination_risk": 0.0,
                "domain_consistency_score": 100.0,
                "status": "PASSED",
                "details": {
                    "total_checks": 0,
                    "successful_checks": 0,
                    "domain_conflicts": 0,
                    "checks": []
                }
            }
            
        verified_facts = state.get("verified_facts", [])
        bi = state.get("business_intelligence", {}) or {}
        questions = state.get("questions", [])
        keywords = state.get("keywords", [])
        competitors = state.get("competitors", [])
        nodes = state.get("entity_nodes", [])
        
        # 1. Compile normalized corpus of crawled pages
        page_contents = []
        page_sentences = []
        page_map = {} # url -> normalized_content
        
        for page in crawled_pages:
            url = page.get("url", "")
            title = page.get("title", "") or ""
            content = page.get("markdown_content", "") or page.get("content", "") or ""
            
            norm_content = normalize_text(title + " " + content)
            page_contents.append(norm_content)
            if url:
                page_map[url] = norm_content
                
            # Split sentences for evidence extraction
            # Clean up markdown links before splitting
            clean_content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", content)
            sentences = re.split(r'(?<=[.!?])\s+', clean_content)
            for s in sentences:
                s_strip = s.strip().replace("\n", " ").replace("  ", " ")
                if len(s_strip) > 10 and not s_strip.startswith(("|", "#", "http", "-")):
                    page_sentences.append(s_strip)

        corpus = " ".join(page_contents)
        
        # 2. Compile verified facts corpus
        fact_corpus = " ".join(
            normalize_text(f.get("fact_value", "") + " " + f.get("evidence_text", ""))
            for f in verified_facts
        )
        
        # 3. Compile entity graph corpus
        graph_corpus = " ".join(
            normalize_text(n.get("entity_name", "") + " " + str(n.get("properties", {})))
            for n in nodes
        )
        
        combined_ground_truth = corpus + " " + fact_corpus + " " + graph_corpus
        
        # 4. Gather entities to check
        entities_to_check = []
        
        # Company name
        comp_name = bi.get("company_name", "")
        if comp_name and not is_generic_placeholder(comp_name):
            entities_to_check.append(("Company Name", comp_name))
            
        # Products
        pre_query = bi.get("pre_query_discovery", {}) or {}
        products = pre_query.get("products", [])
        if isinstance(products, list):
            for p in products:
                if p and not is_generic_placeholder(p):
                    entities_to_check.append(("Product", p))
                    
        # Services
        services = pre_query.get("services", [])
        if isinstance(services, list):
            for s in services:
                if s and not is_generic_placeholder(s):
                    entities_to_check.append(("Service", s))
                    
        # Programs
        programs = pre_query.get("programs", [])
        if isinstance(programs, list):
            for prg in programs:
                if prg and not is_generic_placeholder(prg):
                    entities_to_check.append(("Program", prg))
                    
        # Founders (from pre_query, entity nodes, or bio)
        founders = []
        if "founders" in pre_query and isinstance(pre_query["founders"], list):
            founders.extend(pre_query["founders"])
        for node in nodes:
            if node.get("entity_type", "").lower() in ("person", "founder", "co-founder"):
                props = node.get("properties", {}) or {}
                role = str(props.get("role", "")).lower()
                if "founder" in role or "co-founder" in role or node.get("entity_type", "").lower() in ("founder", "co-founder"):
                    founders.append(node.get("entity_name"))
        for f in set(founders):
            if f and not is_generic_placeholder(f):
                entities_to_check.append(("Founder", f))
                
        # Certifications
        certs = pre_query.get("certifications", [])
        if isinstance(certs, list):
            for c in certs:
                if c and not is_generic_placeholder(c):
                    entities_to_check.append(("Certification", c))
                    
        # NOTE: Competitors are intentionally excluded from grounding checks.
        # Competitors are external companies discovered by AI inference — they will
        # NEVER appear on the target website's own crawled pages, so including
        # them in grounding would always reduce the score unfairly.
                
        # Keywords and Questions are bypassed in grounding checks as they are search queries, not factual claims.
                
        # 5. Run verification loop
        total_checks = 0
        successful_checks = 0
        domain_conflicts_count = 0
        details = []
        
        # Check domain suffix/TLD collision
        # E.g., if project URL domain is thelibrarycompany.com, but entities reference librarycompany.org TLD
        proj_domain = ""
        if website_url:
            domain_match = re.search(r"https?://(?:www\.)?([^/]+)", website_url)
            if domain_match:
                proj_domain = domain_match.group(1).lower()
                
        for category, entity in entities_to_check:
            total_checks += 1
            norm_entity = normalize_text(entity)
            
            # Check for domain/TLD collision in this entity string
            is_domain_conflict = False
            if proj_domain:
                # Find TLD collisions in entity, like a different TLD than project's domain
                # e.g., if project domain is librarycompany.com, but entity mentions librarycompany.org
                entity_domains = re.findall(r"[a-zA-Z0-9-]+\.[a-z]{2,6}", entity.lower())
                for ed in entity_domains:
                    if ed != proj_domain and ed.split('.')[0] == proj_domain.split('.')[0]:
                        is_domain_conflict = True
                        
            # Check if this matches a domain conflict from the identity validator
            if identity_res and identity_res.get("identity_conflicts"):
                for conflict in identity_res["identity_conflicts"]:
                    # Only flag if it is an actual domain identity collision in the conflicts
                    if "Domain identity collision" in conflict and entity.lower() in conflict.lower():
                        is_domain_conflict = True

            # Perform corpus lookups
            if is_domain_conflict:
                status = "DOMAIN_CONFLICT"
                domain_conflicts_count += 1
                evidence = "Conflict with project domain identity detected."
            elif norm_entity in combined_ground_truth:
                status = "VERIFIED"
                successful_checks += 1
                
                # Find verbatim sentence from crawl content containing entity
                evidence = entity
                for sentence in page_sentences:
                    if entity.lower() in sentence.lower():
                        evidence = sentence
                        break
            else:
                # Smart proximity word-order-independent check in single sentence/snippet
                entity_words = set(norm_entity.split())
                stop_words = {'the', 'a', 'an', 'and', 'of', 'in', 'to', 'for', 'with', 'on', 'at', 'by', 'from', 'about', 'company', 'business', 'program', 'service'}
                meaningful_words = entity_words - stop_words
                if not meaningful_words:
                    meaningful_words = entity_words
                
                # Check if all meaningful words exist in a single crawled sentence or fact
                grounded_sentence = None
                if meaningful_words:
                    for sentence in page_sentences:
                        norm_sentence = normalize_text(sentence)
                        sentence_words = set(norm_sentence.split())
                        if meaningful_words.issubset(sentence_words):
                            grounded_sentence = sentence
                            break
                    if not grounded_sentence:
                        # Check in verified facts
                        for f in verified_facts:
                            f_text = f.get("fact_value", "") + " " + f.get("evidence_text", "")
                            norm_f = normalize_text(f_text)
                            f_words = set(norm_f.split())
                            if meaningful_words.issubset(f_words):
                                grounded_sentence = f.get("evidence_text", "") or f.get("fact_value", "")
                                break
                                
                if grounded_sentence:
                    status = "VERIFIED"
                    successful_checks += 1
                    evidence = f"Verified via proximity match: {grounded_sentence}"
                else:
                    # Token overlap check
                    overlap = token_overlap_ratio(entity, combined_ground_truth)
                    if overlap >= 0.60:
                        status = "PARTIAL"
                        successful_checks += 0.5  # Partial credit
                        evidence = "Partial token overlap in source pages."
                    else:
                        status = "UNSUPPORTED"
                        evidence = "No matching tokens found in crawled content."
                    
            details.append({
                "entity": entity,
                "category": category,
                "status": status,
                "evidence_snippet": evidence
            })
            
        # 6. Compute scores
        if total_checks > 0:
            grounding_score = (successful_checks / total_checks) * 100.0
        else:
            grounding_score = 100.0
            
        hallucination_risk = max(0.0, 100.0 - grounding_score)
        
        domain_consistency_score = 100.0 - (domain_conflicts_count * 25.0)
        domain_consistency_score = max(0.0, min(100.0, domain_consistency_score))
        
        # Threshold: 70% grounding required (services/programs not always on landing page)
        overall_status = "PASSED" if (grounding_score >= 70.0 and domain_consistency_score >= 90.0) else "FAILED_GROUNDING"
        
        for check in details:
            logger.error(f"[GroundingEngineV2 Check] {check['status']}: {check['category']} -> {check['entity']} (Snippet: {check['evidence_snippet']})")

        logger.error(f"[GroundingEngineV2] Grounding Score: {grounding_score:.2f}%, Domain Consistency Score: {domain_consistency_score:.2f}%. Status: {overall_status}")
        
        return {
            "grounding_score": round(grounding_score, 1),
            "hallucination_risk": round(hallucination_risk, 1),
            "domain_consistency_score": round(domain_consistency_score, 1),
            "status": overall_status,
            "details": {
                "total_checks": total_checks,
                "successful_checks": successful_checks,
                "domain_conflicts": domain_conflicts_count,
                "checks": details
            }
        }
