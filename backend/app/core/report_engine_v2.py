"""
report_engine_v2.py

Generates highly accurate, comprehensive Markdown reports incorporating all
discovered intelligence across 13 required sections, formatting stats and tables.
"""

import logging
from typing import Dict, Any
from app.core.supabase import supabase_client
from app.routers.analysis_reliability import _get_project_data_payload

logger = logging.getLogger(__name__)

class ReportEngineV2:
    def __init__(self):
        pass

    def generate_markdown(self, project_id: str) -> str:
        """
        Gathers all project data from the database and compiles it into a rich markdown report.
        """
        logger.info(f"[ReportEngineV2] Compiling report for project {project_id}...")
        
        # 1. Fetch project payload
        payload = _get_project_data_payload(project_id)
        
        # 2. Fetch project metadata
        proj_resp = supabase_client.table("projects").select("*").eq("id", project_id).execute()
        project = proj_resp.data[0] if (proj_resp.data and len(proj_resp.data) > 0) else {}
        website_url = project.get("website_url", "N/A")
        
        # 3. Fetch visibility scores & historical metrics
        metrics_resp = supabase_client.table("historical_metrics")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        metrics = metrics_resp.data[0] if (metrics_resp.data and len(metrics_resp.data) > 0) else {}
        
        # 4. Fetch reliability metrics
        rel_resp = supabase_client.table("reliability_reports")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        rel_report = rel_resp.data[0] if (rel_resp.data and len(rel_resp.data) > 0) else {}
        
        # 5. Fetch citation reports
        cit_resp = supabase_client.table("citation_reports")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()
        citations = cit_resp.data or []
        
        # 6. Fetch optimization plans
        opt_resp = supabase_client.table("optimization_plans")\
            .select("*")\
            .eq("project_id", project_id)\
            .execute()
        plans = opt_resp.data or []
        
        # 7. Unpack payload
        bp = payload.get("business_profile", {}) or {}
        verified_facts = payload.get("verified_facts", []) or []
        questions = payload.get("questions", []) or []
        keywords = payload.get("keywords", []) or []
        competitors = payload.get("competitors", []) or []
        content_opportunities = payload.get("content_opportunities", []) or []
        crawled_pages = payload.get("crawled_pages", []) or []
        gap_analysis = payload.get("gap_analysis", []) or []
        
        # Retrieve SWOT lists
        strengths = bp.get("strengths", []) or []
        weaknesses = bp.get("weaknesses", []) or []
        opportunities = bp.get("opportunities", []) or []
        risks = bp.get("risks", []) or []
        
        # Build Markdown sections
        
        # Section 1: Executive Summary
        md = f"""# Executive Summary
**Overall Visibility Score**: {metrics.get('visibility_score', 0.0)}%
* **Crawled Pages**: {len(crawled_pages)}
* **Verified Facts**: {len(verified_facts)}
* **AI Questions**: {len(questions)}
* **Target Keywords**: {len(keywords)}

**Company Overview**:
{bp.get('description', 'No overview description generated.')}

---

"""

        # Section 2: Business Profile
        md += f"""# Business Profile
| Attribute | Detail |
| :--- | :--- |
| **Company Name** | {bp.get('company_name', 'N/A')} |
| **Industry** | {bp.get('industry', 'N/A')} |
| **Mission** | {bp.get('mission', 'N/A')} |
| **Vision** | {bp.get('vision', 'N/A')} |
| **Unique Selling Proposition (USP)** | {bp.get('usp', 'N/A')} |
| **Target Audience** | {bp.get('target_audience', 'N/A')} |
| **Business Model** | {bp.get('business_model', 'N/A')} |

---

"""

        # Section 3: Verified Facts
        md += f"""# Verified Facts (Count: {len(verified_facts)})
| Category | Key | Value | Verbatim Evidence | Confidence |
| :--- | :--- | :--- | :--- | :--- |
"""
        if verified_facts:
            for vf in verified_facts:
                cat = vf.get("fact_type", "general")
                key = vf.get("fact_key", "")
                val = vf.get("fact_value", "")
                ev = vf.get("evidence", "").replace("\n", " ")
                conf = f"{int(vf.get('confidence_score', 1.0) * 100)}%"
                md += f"| {cat} | {key} | {val} | {ev} | {conf} |\n"
        else:
            md += "| N/A | N/A | No verified facts found | N/A | N/A |\n"
            
        md += "\n---\n\n"

        # Section 4: SWOT
        md += f"""# SWOT (Strengths: {len(strengths)}, Weaknesses: {len(weaknesses)}, Opportunities: {len(opportunities)}, Threats: {len(risks)})
### Strengths
{chr(10).join(f'* {s}' for s in strengths) if strengths else '* None recorded.'}

### Weaknesses
{chr(10).join(f'* {w}' for w in weaknesses) if weaknesses else '* None recorded.'}

### Opportunities
{chr(10).join(f'* {o}' for o in opportunities) if opportunities else '* None recorded.'}

### Threats & Risks
{chr(10).join(f'* {r}' for r in risks) if risks else '* None recorded.'}

---

"""

        # Section 5: Questions
        md += f"""# Questions (Count: {len(questions)})
| Question | Category | Intent | Priority | Recommended Answer |
| :--- | :--- | :--- | :--- | :--- |
"""
        if questions:
            for q in questions:
                q_text = q.get("question", "")
                q_type = q.get("question_type", "General")
                q_intent = q.get("intent", "informational")
                q_priority = q.get("priority", "Medium")
                q_ans = q.get("recommended_answer", "").replace("\n", " ")
                md += f"| {q_text} | {q_type} | {q_intent} | {q_priority} | {q_ans} |\n"
        else:
            md += "| No questions discovered | N/A | N/A | N/A | N/A |\n"
            
        md += "\n---\n\n"

        # Section 6: Keywords
        md += f"""# Keywords (Count: {len(keywords)})
| Keyword | Type | Intent | Theme/Cluster | Priority | Difficulty | Opportunity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""
        if keywords:
            for kw in keywords:
                k_text = kw.get("keyword", "")
                k_type = kw.get("keyword_type", "Semantic")
                k_intent = kw.get("intent", "informational")
                k_cluster = kw.get("cluster", "General")
                k_priority = kw.get("priority", "Medium")
                k_diff = kw.get("difficulty_estimate", "Medium")
                k_opp = kw.get("opportunity_estimate", "Medium")
                md += f"| {k_text} | {k_type} | {k_intent} | {k_cluster} | {k_priority} | {k_diff} | {k_opp} |\n"
        else:
            md += "| No keywords strategized | N/A | N/A | N/A | N/A | N/A | N/A |\n"
            
        md += "\n---\n\n"

        # Section 7: Competitors
        md += f"""# Competitors (Count: {len(competitors)})
| Competitor | Type | Similarity | Strengths | Weaknesses | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
        if competitors:
            for c in competitors:
                c_name = c.get("name") or c.get("competitor_name", "")
                c_type = c.get("competitor_type", "indirect")
                c_sim = f"{c.get('similarity_score', 50)}%"
                c_strengths = ", ".join(c.get("strengths", [])) if isinstance(c.get("strengths"), list) else str(c.get("strengths", ""))
                c_weaknesses = ", ".join(c.get("weaknesses", [])) if isinstance(c.get("weaknesses"), list) else str(c.get("weaknesses", ""))
                c_desc = c.get("description", "").replace("\n", " ")
                md += f"| {c_name} | {c_type} | {c_sim} | {c_strengths} | {c_weaknesses} | {c_desc} |\n"
        else:
            md += "| No competitors discovered | N/A | N/A | N/A | N/A | N/A |\n"
            
        md += "\n---\n\n"

        # Section 8: Content Opportunities
        md += f"""# Content Opportunities (Count: {len(content_opportunities)})
| Topic Title | Content Type | Priority | Impact Score | Effort Score | Expected Benefit |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
        if content_opportunities:
            for o in content_opportunities:
                title = o.get("title", "")
                c_type = o.get("content_type", "Blog")
                priority = o.get("priority", "medium")
                impact = o.get("impact_score", 50)
                effort = o.get("effort_score", 50)
                benefit = o.get("expected_benefit", "N/A").replace("\n", " ")
                md += f"| {title} | {c_type} | {priority} | {impact} | {effort} | {benefit} |\n"
        else:
            md += "| No content opportunities identified | N/A | N/A | N/A | N/A | N/A |\n"
            
        md += "\n---\n\n"

        # Section 9: GEO Readiness
        md += f"""# GEO Readiness (Score: {metrics.get('visibility_score', 0.0)}%)
| Signal Category | Score | Details / Status |
| :--- | :--- | :--- |
| **Content Coverage** | {metrics.get('coverage_score', 0.0)}% | Evaluated topic clusters and content gaps |
| **Grounding Score** | {metrics.get('grounding_score', 0.0)}% | Factual source validation against crawl data |
| **Consistency Score** | {metrics.get('consistency_score', 0.0)}% | Cross-agent data alignment and resolution |

---

"""

        # Section 10: Recommendation Intelligence
        md += f"""# Recommendation Intelligence (Overall Score: {metrics.get('recommendation_score', 0.0)}%)
| Simulated Query | Recommendation Probability | Key Supporting Evidence | Missing Requirements | Action Items |
| :--- | :--- | :--- | :--- | :--- |
"""
        # Load from recommendation_simulations
        sims_resp = supabase_client.table("recommendation_simulations").select("*").eq("project_id", project_id).execute()
        sims = sims_resp.data if sims_resp.data else []
        if sims:
            for s in sims:
                query = s.get("query", "")
                prob = f"{s.get('recommendation_probability', 50.0)}%"
                evidence = ", ".join(s.get("supporting_evidence", [])) if isinstance(s.get("supporting_evidence"), list) else str(s.get("supporting_evidence", ""))
                reqs = ", ".join(s.get("missing_requirements", [])) if isinstance(s.get("missing_requirements"), list) else str(s.get("missing_requirements", ""))
                actions = ", ".join(s.get("improvement_actions", [])) if isinstance(s.get("improvement_actions"), list) else str(s.get("improvement_actions", ""))
                md += f"| {query} | {prob} | {evidence[:80]}... | {reqs[:80]}... | {actions[:80]}... |\n"
        else:
            md += "| No simulations recorded | N/A | N/A | N/A | N/A |\n"
            
        md += "\n---\n\n"

        # Section 11: Reliability Metrics
        md += f"""# Reliability Metrics (Reliability Score: {rel_report.get('reliability_score', 100.0)}%)
| Reliability Indicator | Value | Target |
| :--- | :--- | :--- |
| **Overall Score** | {rel_report.get('reliability_score', 100.0)}% | 90% |
| **Pipeline Success Rate** | {rel_report.get('success_rate', 100.0)}% | 95% |
| **Retry Success Rate** | {rel_report.get('retry_success_rate', 100.0)}% | 90% |
| **Dependency Score** | {rel_report.get('dependency_score', 100.0)}% | 95% |
| **Runtime Stability** | {rel_report.get('runtime_stability', 100.0)}% | 90% |

---

"""

        # Section 12: Citation Analysis
        md += f"""# Citation Analysis (Discovered Citations: {len(citations)})
| Platform | Target Query | Grounding Proof | Citation Probability | Actionable Suggestions |
| :--- | :--- | :--- | :--- | :--- |
"""
        if citations:
            for cit in citations:
                platform = cit.get("platform", "AI Search")
                query = cit.get("query_text", "")
                proof = cit.get("grounding_evidence", "").replace("\n", " ")
                prob = f"{cit.get('citation_probability', 50)}%"
                action = cit.get("recomm_action", "")
                md += f"| {platform} | {query} | {proof[:80]}... | {prob} | {action} |\n"
        else:
            md += "| No citation data found | N/A | N/A | N/A | N/A |\n"
            
        md += "\n---\n\n"

        # Section 13: Optimization Roadmap
        md += f"""# Optimization Roadmap (Plan Count: {len(plans)})
| Category | Priority | Recommended Action / Opportunity | Status | Impact Score | Effort Score |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
        if plans:
            for p in plans:
                cat = p.get("category", "SEO")
                priority = p.get("priority", "MEDIUM")
                action = p.get("recommendation", "").replace("\n", " ")
                status = p.get("status", "pending")
                impact = p.get("impact_score", 50)
                effort = p.get("effort_score", 50)
                md += f"| {cat} | {priority} | {action} | {status} | {impact} | {effort} |\n"
        else:
            md += "| No optimization roadmaps defined | N/A | N/A | N/A | N/A | N/A |\n"
            
        return md.strip()
