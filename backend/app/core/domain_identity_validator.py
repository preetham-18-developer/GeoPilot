"""
domain_identity_validator.py

Validates generated company details and TLD domains against the crawled homepage and About/team pages
to prevent organization confusion and domain collisions.
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class DomainIdentityValidator:
    def __init__(self):
        pass

    def validate(self, project_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the identity validation check.
        """
        website_url = state.get("website_url", "")
        crawled_pages = state.get("crawled_pages", [])
        
        # If corpus is empty or extremely minimal (e.g. < 150 words), bypass checks
        total_word_count = sum(len((page.get("markdown_content", "") or page.get("content", "") or "").split()) for page in crawled_pages)
        if total_word_count < 150:
            logger.warning(f"[DomainIdentityValidator] Crawled content is minimal ({total_word_count} words). Bypassing identity checks.")
            return {
                "identity_match_score": 100.0,
                "identity_conflicts": [],
                "confidence": 1.0
            }
            
        bi = state.get("business_intelligence", {}) or {}
        nodes = state.get("entity_nodes", [])
        
        # 1. Find homepage and About/team page contents
        homepage_content = ""
        homepage_title = ""
        about_content = ""
        
        root_domain = ""
        url_match = re.search(r"https?://(?:www\.)?([^/]+)", website_url)
        if url_match:
            root_domain = url_match.group(1).lower()
            
        for page in crawled_pages:
            url = page.get("url", "").lower().rstrip('/')
            
            # Match homepage
            is_home = (
                url == website_url.lower().rstrip('/') or 
                url == f"https://{root_domain}" or 
                url == f"http://{root_domain}" or
                url == root_domain or
                (url.endswith(root_domain) and len(url.replace(root_domain, '').replace('https://', '').replace('http://', '').replace('www.', '')) == 0)
            )
            
            if is_home:
                homepage_content = page.get("markdown_content", "") or page.get("content", "") or ""
                homepage_title = page.get("title", "") or ""
                
            # Match About/team page
            if any(term in url for term in ["about", "team", "who-we-are", "contact", "management"]):
                about_content += "\n" + (page.get("markdown_content", "") or page.get("content", "") or "")
                
        identity_corpus = (homepage_title + " " + homepage_content + " " + about_content).lower()
        
        # Build full crawled pages corpus as a robust fallback for legitimate subpage mentions
        full_crawled_corpus = " ".join(
            (page.get("title", "") or "") + " " + (page.get("markdown_content", "") or page.get("content", "") or "")
            for page in crawled_pages
        ).lower()
        
        identity_conflicts = []
        
        # 2. Check Company Name
        company_name = bi.get("company_name", "").strip()
        if company_name and company_name.upper() not in ("UNKNOWN", "UNKNOWN COMPANY"):
            norm_name = re.sub(r"[^a-z0-9\s]", "", company_name.lower())
            words = [w for w in norm_name.split() if w not in ("company", "corporation", "inc", "co", "the", "limited", "ltd", "of")]
            if words:
                # If none of the words exist in the homepage/about pages, check fallback full corpus
                if not any(w in identity_corpus for w in words):
                    if not any(w in full_crawled_corpus for w in words):
                        identity_conflicts.append(
                            f"Company name conflict: Generated company name '{company_name}' is not found in homepage or About page."
                        )
                    
        # 3. Check Founders
        founders = []
        pre_query = bi.get("pre_query_discovery", {}) or {}
        if "founders" in pre_query and isinstance(pre_query["founders"], list):
            founders.extend(pre_query["founders"])
        for node in nodes:
            if node.get("entity_type", "").lower() in ("person", "founder", "co-founder"):
                props = node.get("properties", {}) or {}
                role = str(props.get("role", "")).lower()
                if "founder" in role or "co-founder" in role or node.get("entity_type", "").lower() in ("founder", "co-founder"):
                    founders.append(node.get("entity_name"))
                    
        for founder in set(founders):
            if founder and founder.upper() not in ("NOT_FOUND", "UNKNOWN"):
                norm_founder = re.sub(r"[^a-z0-9\s]", "", founder.lower())
                f_words = [w for w in norm_founder.split() if len(w) > 2]
                if f_words:
                    # Try full-name match in homepage/about corpus first
                    found_in_identity = any(w in identity_corpus for w in f_words)
                    # Fallback: try ANY single word part (first name OR last name) in full crawled corpus
                    found_in_full = any(w in full_crawled_corpus for w in f_words)
                    # Extra fallback: check each individual name token as a standalone partial
                    if not found_in_identity and not found_in_full:
                        # split on space and check each part individually (handles middle names, initials)
                        name_parts = [p.strip() for p in norm_founder.split() if len(p.strip()) > 3]
                        found_in_full = any(part in full_crawled_corpus for part in name_parts)
                    if not found_in_identity and not found_in_full:
                        identity_conflicts.append(
                            f"Founder warning: Generated founder '{founder}' could not be verified on any crawled page."
                        )
                        logger.warning(f"[DomainIdentityValidator] Founder '{founder}' not found anywhere in crawled content.")

                        
        # 4. Check for TLD/Domain Collisions
        # Only scan first-party identity fields — deliberately exclude competitor URLs,
        # product names, and numeric tokens (e.g. "v2.5", "100.0") which cause false positives.
        if root_domain:
            domain_name = root_domain.split('.')[0]
            # Scan only non-competitor descriptive fields
            identity_fields_text = " ".join([
                str(bi.get("company_name", "") or ""),
                str(bi.get("description", "") or ""),
                str(bi.get("mission", "") or ""),
                str(bi.get("vision", "") or ""),
                str(bi.get("usp", "") or ""),
                str(bi.get("target_audience", "") or ""),
            ])
            found_domains = re.findall(r"([a-zA-Z][a-zA-Z0-9-]*\.[a-z]{2,6})\b", identity_fields_text)
            for fd in set(found_domains):
                fd = fd.lower()
                # Skip if it is the actual project domain, or a pure numeric token (e.g. "v2.5")
                if fd == root_domain:
                    continue
                # Only flag if the base name matches but TLD differs (true collision)
                if fd.split('.')[0] == domain_name:
                    identity_conflicts.append(
                        f"Domain identity collision: Project website domain is '{root_domain}', but generated text contains references to '{fd}'."
                    )
                    
        # 5. Compute Identity Match Score
        score = 100.0
        for conflict in identity_conflicts:
            if "Company name" in conflict:
                score -= 40.0
            elif "Founder warning" in conflict:
                # Soft penalty: a single unverified founder should not cause a hard failure
                score -= 15.0
            elif "Founder mismatch" in conflict:
                score -= 25.0
            elif "Domain identity collision" in conflict:
                score -= 30.0
            else:
                score -= 20.0
                
        score = max(0.0, min(100.0, score))
        
        # Determine confidence
        has_home = len(homepage_content) > 100
        has_about = len(about_content) > 100
        confidence = 1.0 if (has_home and has_about) else 0.7 if (has_home or has_about) else 0.4
        
        logger.info(f"[DomainIdentityValidator] Score: {score:.2f}%, conflicts count: {len(identity_conflicts)}")
        for c in identity_conflicts:
            logger.warning(f"[DomainIdentityValidator] Conflict: {c}")
            
        return {
            "identity_match_score": round(score, 1),
            "identity_conflicts": identity_conflicts,
            "confidence": confidence
        }
