"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE, authHeader } from "../lib/config";


interface ContentIntelligenceTabProps {
  projectId: string;
  userId: string;
}

export default function ContentIntelligenceTab({ projectId, userId }: ContentIntelligenceTabProps) {
  const [topicClusters, setTopicClusters] = useState<any[]>([]);
  const [blueprints, setBlueprints] = useState<any[]>([]);
  const [authSources, setAuthSources] = useState<any[]>([]);
  const [faqClusters, setFaqClusters] = useState<any[]>([]);
  const [gaps, setGaps] = useState<any[]>([]);
  const [links, setLinks] = useState<any[]>([]);
  const [schemas, setSchemas] = useState<any[]>([]);
  const [citations, setCitations] = useState<any[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [subTab, setSubTab] = useState("clusters");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const headers = authHeader(userId);
      
      const [
        clustersRes,
        blueprintsRes,
        authRes,
        faqRes,
        gapsRes,
        linksRes,
        schemasRes,
        citationsRes
      ] = await Promise.all([
        fetch(`${API_BASE}/analysis/topic-clusters/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/content-blueprints/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/authority-sources/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/faq-clusters/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/content-gaps/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/internal-links/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/schema-recommendations/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/citation-predictions/${projectId}`, { headers }),
      ]);

      if (
        !clustersRes.ok ||
        !blueprintsRes.ok ||
        !authRes.ok ||
        !faqRes.ok ||
        !gapsRes.ok ||
        !linksRes.ok ||
        !schemasRes.ok ||
        !citationsRes.ok
      ) {
        throw new Error("Failed to load one or more Content Intelligence components.");
      }

      setTopicClusters(await clustersRes.json());
      setBlueprints(await blueprintsRes.json());
      setAuthSources(await authRes.json());
      setFaqClusters(await faqRes.json());
      setGaps(await gapsRes.json());
      setLinks(await linksRes.json());
      setSchemas(await schemasRes.json());
      setCitations(await citationsRes.json());
    } catch (err: any) {
      setError(err.message || "Failed to fetch Content Intelligence data.");
    } finally {
      setLoading(false);
    }
  }, [projectId, userId]);

  useEffect(() => {
    if (projectId) {
      fetchData();
    }
  }, [projectId, fetchData]);

  if (loading) {
    return (
      <div className="card flex-center" style={{ padding: "4rem" }}>
        <div className="spinner"></div>
        <p style={{ color: "var(--text-muted)", marginTop: "1rem" }}>
          Generating GEO content assets, linking paths, and citation forecasts...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ borderLeft: "4px solid var(--accent-red)", padding: "1.5rem" }}>
        <p style={{ color: "var(--accent-red)", fontWeight: 600 }}>⚠️ {error}</p>
        <button className="btn btn-secondary" style={{ marginTop: "1rem" }} onClick={fetchData}>
          Retry
        </button>
      </div>
    );
  }

  // Helper colors
  const getScoreColor = (score: number) => {
    if (score >= 75) return "var(--accent-green)";
    if (score >= 50) return "var(--accent-amber)";
    return "var(--accent-red)";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* Overview Block */}
      <div
        className="card glow-border"
        style={{
          background: "linear-gradient(135deg, rgba(0, 229, 255, 0.05) 0%, rgba(98, 0, 234, 0.02) 100%)",
          borderLeft: "4px solid var(--secondary)",
        }}
      >
        <h2 style={{ fontSize: "1.75rem", margin: 0 }}>🎯 Content Intelligence &amp; GEO Engine</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.95rem", margin: "0.25rem 0 0 0" }}>
          Supercharge your page structure, faq mappings, external citations, and internal flow to align directly with generative engine matching requirements.
        </p>
      </div>

      {/* Sub tabs */}
      <div className="tabs-bar" style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "1rem" }}>
        {[
          { key: "clusters", label: "Topic Clusters" },
          { key: "blueprints", label: "Blueprints" },
          { key: "gaps", label: "Audits & Gaps" },
          { key: "links", label: "Internal Linking" },
          { key: "faq", label: "FAQ Outline" },
          { key: "schema", label: "Structured Markup" },
          { key: "authority", label: "Citations Mapping" },
          { key: "citation_prob", label: "Likelihood Predictions" },
        ].map((t) => (
          <button
            key={t.key}
            className={`tab-btn ${subTab === t.key ? "active" : ""}`}
            onClick={() => setSubTab(t.key)}
            style={{
              padding: "0.5rem 1rem",
              fontSize: "0.85rem",
              borderRadius: "6px",
              background: subTab === t.key ? "var(--secondary)" : "rgba(255,255,255,0.02)",
              color: subTab === t.key ? "#fff" : "var(--text-muted)",
              border: "none",
              cursor: "pointer",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Sub Tab Panels */}
      <div className="tab-content" style={{ marginTop: "1rem" }}>
        {/* 1. Topic Clusters */}
        {subTab === "clusters" && (
          <div className="space-y-4">
            <h3 style={{ fontSize: "1.3rem", color: "var(--text-main)", marginBottom: "1rem" }}>📚 Semantic Topic Clusters</h3>
            {topicClusters.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>No topic clusters available. Run pipeline to extract.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                {topicClusters.map((cluster, i) => (
                  <div key={i} className="card glow-border" style={{ borderLeft: `4px solid ${getScoreColor(cluster.priority_score)}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                      <h4 style={{ fontSize: "1.15rem", margin: 0, color: "var(--text-main)" }}>{cluster.parent_topic}</h4>
                      <div>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginRight: "1rem" }}>Priority:</span>
                        <strong style={{ color: getScoreColor(cluster.priority_score), fontSize: "1.2rem" }}>{cluster.priority_score}/100</strong>
                      </div>
                    </div>

                    <div className="grid-2" style={{ gap: "1.5rem", marginBottom: "1rem" }}>
                      <div>
                        <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--secondary)", marginBottom: "0.4rem" }}>🔑 Subtopics:</strong>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                          {cluster.subtopics.map((s: string, idx: number) => (
                            <span key={idx} className="badge badge-info">{s}</span>
                          ))}
                        </div>
                      </div>

                      <div>
                        <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--accent-amber)", marginBottom: "0.4rem" }}>🎯 Intent Types:</strong>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                          {cluster.intent_types.map((int: string, idx: number) => (
                            <span key={idx} className="badge badge-warning" style={{ textTransform: "capitalize" }}>{int}</span>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div style={{ marginTop: "1rem", borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
                      <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--text-light)", marginBottom: "0.5rem" }}>❓ Discovered Queries Mapped:</strong>
                      <ul style={{ paddingLeft: "1.2rem", color: "var(--text-muted)", fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                        {cluster.supporting_questions.map((q: string, idx: number) => (
                          <li key={idx}>&ldquo;{q}&rdquo;</li>
                        ))}
                      </ul>
                    </div>

                    {cluster.entity_relationships && cluster.entity_relationships.length > 0 && (
                      <div style={{ marginTop: "1rem", borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
                        <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--accent-green)", marginBottom: "0.5rem" }}>🔗 Entity Relationships Graph:</strong>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                          {cluster.entity_relationships.map((rel: string, idx: number) => (
                            <span key={idx} style={{ background: "rgba(0, 255, 136, 0.05)", border: "1px solid rgba(0, 255, 136, 0.2)", borderRadius: "6px", padding: "0.3rem 0.6rem", fontSize: "0.8rem", color: "var(--accent-green)" }}>
                              {rel}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 2. Blueprints */}
        {subTab === "blueprints" && (
          <div className="space-y-4">
            <h3 style={{ fontSize: "1.3rem", color: "var(--text-main)", marginBottom: "1rem" }}>📐 Content Strategy Blueprints</h3>
            {blueprints.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>No blueprints available. Run pipeline to extract.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                {blueprints.map((bp, i) => (
                  <div key={i} className="card glow-border" style={{ borderLeft: bp.priority === "HIGH" ? "4px solid var(--accent-green)" : "4px solid var(--accent-amber)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                      <div>
                        <span className="badge badge-info" style={{ marginRight: "0.5rem" }}>{bp.page_type}</span>
                        <span className={`badge ${bp.priority === "HIGH" ? "badge-success" : "badge-warning"}`}>{bp.priority} Priority</span>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginRight: "1rem" }}>Impact: <strong style={{ color: "var(--accent-green)" }}>{bp.impact_score}</strong></span>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Effort: <strong style={{ color: "var(--accent-red)" }}>{bp.effort_score}</strong></span>
                      </div>
                    </div>

                    <h4 style={{ fontSize: "1.2rem", margin: "0 0 0.5rem 0", color: "#fff" }}>{bp.title}</h4>
                    <p style={{ fontSize: "0.85rem", color: "var(--text-dark)", fontFamily: "monospace", margin: "0 0 1rem 0" }}>slug: /{bp.slug}</p>

                    <div className="grid-2" style={{ gap: "1.5rem", background: "rgba(255,255,255,0.02)", padding: "1rem", borderRadius: "8px", border: "1px solid var(--border-color)", marginBottom: "1rem" }}>
                      <div>
                        <strong style={{ display: "block", fontSize: "0.8rem", color: "var(--secondary)", marginBottom: "0.25rem" }}>🎯 Intent Category:</strong>
                        <span style={{ fontSize: "0.9rem", color: "var(--text-light)", textTransform: "uppercase", fontWeight: 700 }}>{bp.target_intent}</span>
                      </div>
                      <div>
                        <strong style={{ display: "block", fontSize: "0.8rem", color: "var(--secondary)", marginBottom: "0.25rem" }}>🏷️ Suggested Schema Markup:</strong>
                        <span style={{ fontSize: "0.9rem", color: "var(--text-light)", fontWeight: 700 }}>{bp.schema_type}</span>
                      </div>
                    </div>

                    <div style={{ marginBottom: "1rem" }}>
                      <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--text-light)", marginBottom: "0.25rem" }}>💡 Expected Benefit:</strong>
                      <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)", lineHeight: 1.4 }}>{bp.expected_benefit}</p>
                    </div>

                    <div className="grid-2" style={{ gap: "1.5rem", borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
                      <div>
                        <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--text-light)", marginBottom: "0.4rem" }}>🔑 Target Keywords:</strong>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                          {bp.keywords.map((k: string, idx: number) => (
                            <span key={idx} className="badge badge-info" style={{ fontSize: "0.75rem" }}>{k}</span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--text-light)", marginBottom: "0.4rem" }}>❓ Mapped FAQs:</strong>
                        <ul style={{ paddingLeft: "1.2rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                          {bp.questions.map((q: string, idx: number) => (
                            <li key={idx}>{q}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 3. Gaps */}
        {subTab === "gaps" && (
          <div className="space-y-4">
            <h3 style={{ fontSize: "1.3rem", color: "var(--text-main)", marginBottom: "1rem" }}>🔍 Structural Content Audits</h3>
            {gaps.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>No gap analysis report compiled. Run pipeline to extract.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                {gaps.map((report, i) => (
                  <div key={i} className="card glow-border" style={{ borderLeft: `4px solid ${getScoreColor(report.recommendation_value)}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem", flexWrap: "wrap", gap: "1rem" }}>
                      <div>
                        <h4 style={{ fontSize: "1.25rem", margin: 0, color: "var(--text-main)" }}>Site-Wide Content Gap Audit</h4>
                        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: "0.15rem 0 0 0" }}>Identifies critical page layouts and authority missing structures.</p>
                      </div>
                      <div style={{ display: "flex", gap: "2rem" }}>
                        <div style={{ textAlign: "right" }}>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>Impact Score</span>
                          <strong style={{ color: "var(--accent-green)", fontSize: "1.5rem" }}>{report.impact_score}</strong>
                        </div>
                        <div style={{ textAlign: "right" }}>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>Recommendation Value</span>
                          <strong style={{ color: getScoreColor(report.recommendation_value), fontSize: "1.5rem" }}>{report.recommendation_value}%</strong>
                        </div>
                      </div>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                      {report.missing_trust_pages.length > 0 && (
                        <div style={{ padding: "0.8rem", background: "rgba(255, 75, 75, 0.03)", borderLeft: "3px solid var(--accent-red)", borderRadius: "6px" }}>
                          <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--accent-red)", marginBottom: "0.3rem" }}>🚨 Missing Trust Pages:</strong>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                            {report.missing_trust_pages.map((p: string, idx: number) => (
                              <span key={idx} className="badge badge-danger">{p}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {report.missing_case_studies.length > 0 && (
                        <div style={{ padding: "0.8rem", background: "rgba(255, 152, 0, 0.03)", borderLeft: "3px solid var(--accent-amber)", borderRadius: "6px" }}>
                          <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--accent-amber)", marginBottom: "0.3rem" }}>⚠️ Missing Evidence &amp; Case Studies:</strong>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                            {report.missing_case_studies.map((p: string, idx: number) => (
                              <span key={idx} className="badge badge-warning">{p}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {report.missing_comparison_pages.length > 0 && (
                        <div style={{ padding: "0.8rem", background: "rgba(33, 150, 243, 0.03)", borderLeft: "3px solid var(--secondary)", borderRadius: "6px" }}>
                          <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--secondary)", marginBottom: "0.3rem" }}>⚖️ Missing Comparisons:</strong>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                            {report.missing_comparison_pages.map((p: string, idx: number) => (
                              <span key={idx} className="badge badge-info">{p}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {report.missing_authority_signals.length > 0 && (
                        <div style={{ padding: "0.8rem", background: "rgba(255, 75, 75, 0.03)", borderLeft: "3px solid var(--accent-red)", borderRadius: "6px" }}>
                          <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--accent-red)", marginBottom: "0.3rem" }}>🛡️ Missing Compliance / Trust Badging:</strong>
                          <ul style={{ paddingLeft: "1.2rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                            {report.missing_authority_signals.map((p: string, idx: number) => (
                              <li key={idx}>{p}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {report.missing_topics.length > 0 && (
                        <div style={{ padding: "0.8rem", background: "rgba(255,255,255,0.02)", borderLeft: "3px solid var(--border-color)", borderRadius: "6px" }}>
                          <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--text-light)", marginBottom: "0.3rem" }}>📂 Missing Topic &amp; Keywords Coverage:</strong>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                            {report.missing_topics.map((t: string, idx: number) => (
                              <span key={idx} className="badge" style={{ background: "rgba(255,255,255,0.08)", color: "#fff" }}>{t}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 4. Linking */}
        {subTab === "links" && (
          <div className="space-y-4">
            <h3 style={{ fontSize: "1.3rem", color: "var(--text-main)", marginBottom: "1rem" }}>🔗 Internal Linking Maps</h3>
            {links.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>No internal link configurations generated. Run pipeline to extract.</p>
            ) : (
              <div className="table-container" style={{ margin: 0 }}>
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th>Source Page (Parent)</th>
                      <th>Target Page (Child)</th>
                      <th>Suggested Anchor Text</th>
                      <th>Semantic Overlap Relevance</th>
                      <th>Suggested Link Strength</th>
                    </tr>
                  </thead>
                  <tbody>
                    {links.map((link, idx) => (
                      <tr key={idx}>
                        <td>
                          <div style={{ fontSize: "0.85rem", fontFamily: "monospace", color: "var(--secondary)" }}>{link.parent_page}</div>
                        </td>
                        <td>
                          <div style={{ fontSize: "0.85rem", fontFamily: "monospace", color: "var(--accent-green)" }}>{link.child_page}</div>
                        </td>
                        <td>
                          <strong style={{ color: "#fff" }}>&ldquo;{link.anchor_text}&rdquo;</strong>
                        </td>
                        <td>
                          <span className="badge badge-info" style={{ fontSize: "0.75rem" }}>{link.entity_relevance}% Relevance</span>
                        </td>
                        <td>
                          <strong style={{ color: getScoreColor(link.link_strength) }}>{link.link_strength}/100</strong>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* 5. FAQ */}
        {subTab === "faq" && (
          <div className="space-y-4">
            <h3 style={{ fontSize: "1.3rem", color: "var(--text-main)", marginBottom: "1rem" }}>❓ FAQ Outline &amp; Direct Answers</h3>
            {faqClusters.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>No FAQ outlines mapped. Run pipeline to extract.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                {faqClusters.map((faq, i) => (
                  <div key={i} className="card glow-border" style={{ borderLeft: faq.priority === "High" ? "4px solid var(--accent-green)" : "4px solid var(--accent-amber)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                      <span className="badge badge-info">{faq.intent}</span>
                      <span className={`badge ${faq.priority === "High" ? "badge-success" : "badge-warning"}`}>{faq.priority} Priority</span>
                    </div>

                    <h4 style={{ fontSize: "1.15rem", margin: "0.5rem 0", color: "#fff" }}>Q: {faq.question}</h4>
                    <div style={{ padding: "1rem", background: "rgba(255,255,255,0.02)", borderRadius: "6px", border: "1px solid var(--border-color)", marginTop: "0.5rem" }}>
                      <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--accent-green)", lineHeight: 1.4 }}>
                        <strong>Answer Script:</strong> {faq.answer_outline}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 6. Schema */}
        {subTab === "schema" && (
          <div className="space-y-4">
            <h3 style={{ fontSize: "1.3rem", color: "var(--text-main)", marginBottom: "1rem" }}>🏷️ schema.org JSON-LD Injectors</h3>
            {schemas.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>No schema bindings generated. Run pipeline to extract.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                {schemas.map((sch, i) => (
                  <div key={i} className="card glow-border">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                      <div>
                        <h4 style={{ fontSize: "1.1rem", margin: 0, color: "#fff" }}>{sch.page_title}</h4>
                        <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontFamily: "monospace" }}>{sch.page_url}</span>
                      </div>
                      <span className="badge badge-info" style={{ fontSize: "0.8rem", padding: "0.35rem 0.65rem" }}>{sch.recommended_schema} Schema</span>
                    </div>

                    <div style={{ marginTop: "1rem" }}>
                      <strong style={{ display: "block", fontSize: "0.85rem", color: "var(--text-light)", marginBottom: "0.5rem" }}>📋 JSON-LD Ready to Embed:</strong>
                      <pre style={{
                        background: "rgba(0,0,0,0.25)",
                        border: "1px solid var(--border-color)",
                        borderRadius: "8px",
                        padding: "1rem",
                        fontSize: "0.8rem",
                        fontFamily: "monospace",
                        color: "var(--accent-green)",
                        overflowX: "auto",
                        maxHeight: "250px"
                      }}>
                        {JSON.stringify(sch.schema_json, null, 2)}
                      </pre>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 7. Citations (Authority) */}
        {subTab === "authority" && (
          <div className="space-y-4">
            <h3 style={{ fontSize: "1.3rem", color: "var(--text-main)", marginBottom: "1rem" }}>🛡️ High-Authority External Reference Sources</h3>
            {authSources.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>No authority sources cataloged. Run pipeline to extract.</p>
            ) : (
              <div className="table-container" style={{ margin: 0 }}>
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th>Standard/Regulatory Title</th>
                      <th>Organization</th>
                      <th>Reference Type</th>
                      <th>Authority Score</th>
                      <th>Citation Placement Purpose</th>
                    </tr>
                  </thead>
                  <tbody>
                    {authSources.map((src, idx) => (
                      <tr key={idx}>
                        <td>
                          <strong style={{ color: "#fff" }}>{src.title}</strong>
                          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>Topic: {src.topic}</div>
                        </td>
                        <td>
                          <span style={{ fontSize: "0.85rem", color: "var(--text-light)" }}>{src.organization}</span>
                        </td>
                        <td>
                          <span className="badge badge-info">{src.source_type}</span>
                        </td>
                        <td>
                          <strong style={{ color: "var(--accent-green)" }}>{src.authority_score}%</strong>
                        </td>
                        <td>
                          <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)", maxWidth: "350px", lineHeight: 1.3 }}>{src.citation_purpose}</p>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* 8. Predictions */}
        {subTab === "citation_prob" && (
          <div className="space-y-4">
            <h3 style={{ fontSize: "1.3rem", color: "var(--text-main)", marginBottom: "1rem" }}>🔮 AI Citation Likelihood Predictions</h3>
            {citations.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>No likelihood predictions available. Run pipeline to extract.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                {citations.map((c, idx) => (
                  <div key={idx} className="card glow-border" style={{ borderLeft: `4px solid ${getScoreColor(c.citation_probability)}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
                      <div>
                        <h4 style={{ fontSize: "1.1rem", margin: 0, color: "#fff" }}>{c.page_title}</h4>
                        <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontFamily: "monospace" }}>{c.page_url}</span>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <span style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginRight: "1rem" }}>Citation Likelihood:</span>
                        <strong style={{ color: getScoreColor(c.citation_probability), fontSize: "1.6rem" }}>{c.citation_probability}%</strong>
                      </div>
                    </div>

                    <div className="grid-5" style={{ gap: "1rem", marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--border-color)", fontSize: "0.8rem" }}>
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: "0.5rem", borderRadius: "6px", textAlign: "center" }}>
                        <span style={{ color: "var(--text-muted)", display: "block" }}>Authority Strength</span>
                        <strong style={{ color: "var(--text-light)" }}>{c.authority_score}%</strong>
                      </div>
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: "0.5rem", borderRadius: "6px", textAlign: "center" }}>
                        <span style={{ color: "var(--text-muted)", display: "block" }}>Trust Signals</span>
                        <strong style={{ color: "var(--text-light)" }}>{c.trust_score}%</strong>
                      </div>
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: "0.5rem", borderRadius: "6px", textAlign: "center" }}>
                        <span style={{ color: "var(--text-muted)", display: "block" }}>Entity Occurrences</span>
                        <strong style={{ color: "var(--text-light)" }}>{c.entity_strength}%</strong>
                      </div>
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: "0.5rem", borderRadius: "6px", textAlign: "center" }}>
                        <span style={{ color: "var(--text-muted)", display: "block" }}>Content Depth</span>
                        <strong style={{ color: "var(--text-light)" }}>{c.content_depth}%</strong>
                      </div>
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: "0.5rem", borderRadius: "6px", textAlign: "center" }}>
                        <span style={{ color: "var(--text-muted)", display: "block" }}>Evidence Matches</span>
                        <strong style={{ color: "var(--text-light)" }}>{c.evidence_score}%</strong>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
