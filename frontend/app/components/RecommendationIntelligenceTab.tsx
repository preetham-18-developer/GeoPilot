"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "../lib/config";


interface RecommendationIntelligenceTabProps {
  projectId: string;
  userId: string;
}

export default function RecommendationIntelligenceTab({
  projectId,
  userId,
}: RecommendationIntelligenceTabProps) {
  const [recomData, setRecomData] = useState<any>(null);
  const [hallucData, setHallucData] = useState<any>(null);
  const [consisData, setConsisData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expandedQueryIdx, setExpandedQueryIdx] = useState<number | null>(null);

  useEffect(() => {
    if (projectId) {
      fetchReports();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const fetchReports = async () => {
    setLoading(true);
    setError("");
    try {
      const headers = { Authorization: `Bearer mock-${userId}` };
      const [recomRes, hallucRes, consisRes] = await Promise.all([
        fetch(`${API_BASE}/analysis/recommendation-intelligence/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/hallucination-report/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/consistency-report/${projectId}`, { headers }),
      ]);

      if (!recomRes.ok || !hallucRes.ok || !consisRes.ok) {
        throw new Error("One or more intelligence reports failed to generate.");
      }

      const recomJson = await recomRes.json();
      const hallucJson = await hallucRes.json();
      const consisJson = await consisRes.json();

      setRecomData(recomJson);
      setHallucData(hallucJson);
      setConsisData(consisJson);
    } catch (err: any) {
      setError(err.message || "Failed to connect to FastAPI services.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card flex-center" style={{ padding: "4rem" }}>
        <div className="spinner"></div>
        <p style={{ color: "var(--text-muted)", marginTop: "1rem" }}>
          Simulating search engine recommendations and running QA audits...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ borderLeft: "4px solid var(--accent-red)", padding: "1.5rem" }}>
        <p style={{ color: "var(--accent-red)", fontWeight: 600 }}>⚠️ {error}</p>
        <button className="btn btn-secondary" style={{ marginTop: "1rem" }} onClick={fetchReports}>
          Retry
        </button>
      </div>
    );
  }

  if (!recomData || !hallucData || !consisData) {
    return (
      <div className="card flex-center" style={{ padding: "4rem" }}>
        <p style={{ color: "var(--text-muted)" }}>
          No recommendation intelligence data available. Please trigger an analysis run first.
        </p>
      </div>
    );
  }

  // Helper colors
  const getScoreColor = (score: number) => {
    if (score >= 70) return "var(--accent-green)";
    if (score >= 45) return "var(--accent-amber)";
    return "var(--accent-red)";
  };

  const getStatusBadge = (status: string) => {
    if (status === "likely_recommended") return <span className="badge badge-success">Likely Recommended</span>;
    if (status === "partially_recommended") return <span className="badge badge-warning">Partially Recommended</span>;
    return <span className="badge badge-danger">Unlikely Recommended</span>;
  };

  const getFlagBadge = (level: string) => {
    switch (level) {
      case "VERIFIED":
        return <span className="badge badge-success" style={{ fontSize: "0.7rem" }}>Verified</span>;
      case "LOW_CONFIDENCE":
        return <span className="badge badge-warning" style={{ fontSize: "0.7rem" }}>Low Confidence</span>;
      case "UNSUPPORTED":
        return <span className="badge badge-danger" style={{ fontSize: "0.7rem" }}>Unsupported</span>;
      case "POSSIBLE_HALLUCINATION":
        return (
          <span
            className="badge"
            style={{
              fontSize: "0.7rem",
              background: "rgba(255, 75, 75, 0.25)",
              color: "#FF8A8A",
              border: "1px dashed var(--accent-red)",
            }}
          >
            Hallucination Alert
          </span>
        );
      default:
        return <span className="badge badge-info" style={{ fontSize: "0.7rem" }}>{level}</span>;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* 📋 Section 1: Overview Panel */}
      <div
        className="card glow-border"
        style={{
          background: "linear-gradient(135deg, rgba(98, 0, 234, 0.05) 0%, rgba(0, 229, 255, 0.02) 100%)",
          borderLeft: `4px solid ${getScoreColor(recomData.overall_recommendation_score)}`,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h2 style={{ fontSize: "1.75rem", margin: 0 }}>🧠 Explainable Recommendation Confidence</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.95rem", margin: "0.25rem 0 0 0" }}>
              How likely are AI search engines (ChatGPT, Gemini, Perplexity) to recommend this business?
            </p>
          </div>
          <div style={{ display: "flex", gap: "2rem", alignItems: "center" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: 600 }}>
                Confidence Score
              </div>
              <div style={{ fontSize: "2.5rem", fontWeight: 800, color: "var(--secondary)", lineHeight: 1.1 }}>
                {recomData.overall_confidence}%
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: 600 }}>
                Recommendation Score
              </div>
              <div
                style={{
                  fontSize: "3.25rem",
                  fontWeight: 800,
                  color: getScoreColor(recomData.overall_recommendation_score),
                  lineHeight: 1,
                }}
              >
                {recomData.overall_recommendation_score}/100
              </div>
              <div style={{ marginTop: "0.35rem" }}>
                {getStatusBadge(recomData.recommendation_status)}
              </div>
            </div>
          </div>
        </div>

        {/* Top Improvement Actions */}
        {recomData.top_improvement_actions && recomData.top_improvement_actions.length > 0 && (
          <div
            style={{
              marginTop: "2rem",
              paddingTop: "1.5rem",
              borderTop: "1px solid var(--border-color)",
            }}
          >
            <h3 style={{ fontSize: "1.1rem", marginBottom: "0.75rem", color: "var(--secondary)" }}>
              ⚡ Top Actionable Fixes to Increase AI Recommendations:
            </h3>
            <ul style={{ display: "flex", flexDirection: "column", gap: "0.5rem", paddingLeft: "1.2rem" }}>
              {recomData.top_improvement_actions.map((act: string, idx: number) => (
                <li key={idx} style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
                  {act}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div style={{ marginTop: "1.5rem", textAlign: "right" }}>
          <button className="btn btn-secondary" onClick={fetchReports} style={{ fontSize: "0.85rem" }}>
            ↻ Refresh Recommendation Audits
          </button>
        </div>
      </div>

      {/* 🚀 Section 2: Simulated User Query Comparisons */}
      <div>
        <h2 style={{ fontSize: "1.4rem", marginBottom: "1rem" }}>🔍 Simulated Search Queries</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {recomData.simulations.map((sim: any, idx: number) => {
            const isExpanded = expandedQueryIdx === idx;
            return (
              <div
                key={idx}
                className="card glow-border"
                style={{
                  padding: "1.25rem",
                  borderLeft: `4px solid ${getScoreColor(sim.recommendation_score)}`,
                  cursor: "pointer",
                }}
                onClick={() => setExpandedQueryIdx(isExpanded ? null : idx)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
                  <div>
                    <span className="badge badge-info" style={{ marginBottom: "0.5rem" }}>
                      {sim.query_type}
                    </span>
                    <h3 style={{ fontSize: "1.15rem", margin: 0, color: "var(--text-main)" }}>
                      &ldquo;{sim.query}&rdquo;
                    </h3>
                  </div>
                  <div style={{ display: "flex", gap: "1.5rem", alignItems: "center" }}>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Confidence</div>
                      <div style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--text-muted)" }}>
                        {sim.confidence}%
                      </div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Sim Score</div>
                      <div
                        style={{
                          fontSize: "1.75rem",
                          fontWeight: 800,
                          color: getScoreColor(sim.recommendation_score),
                        }}
                      >
                        {sim.recommendation_score}/100
                      </div>
                    </div>
                    <button className="btn btn-secondary" style={{ padding: "0.3rem 0.6rem", fontSize: "0.8rem" }}>
                      {isExpanded ? "Collapse Details" : "Expose Signals"}
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div
                    style={{
                      marginTop: "1.5rem",
                      paddingTop: "1.5rem",
                      borderTop: "1px solid var(--border-color)",
                      display: "flex",
                      flexDirection: "column",
                      gap: "1.5rem",
                    }}
                    onClick={(e) => e.stopPropagation()} // Prevent collapse on detail click
                  >
                    {/* Signal Breakdown */}
                    <div>
                      <h4 style={{ fontSize: "0.95rem", color: "var(--secondary)", marginBottom: "0.75rem" }}>
                        ⚖️ Multi-Signal Weighting Breakdown:
                      </h4>
                      <div className="grid-3" style={{ gap: "0.75rem" }}>
                        {Object.entries(sim.signal_breakdown).map(([key, item]: any) => (
                          <div
                            key={key}
                            style={{
                              background: "rgba(255, 255, 255, 0.02)",
                              border: "1px solid var(--border-color)",
                              borderRadius: "10px",
                              padding: "0.75rem",
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                            }}
                          >
                            <div>
                              <div style={{ fontSize: "0.8rem", fontWeight: 600 }}>{item.label}</div>
                              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                                Weight: {item.weight}
                              </div>
                            </div>
                            <div
                              style={{
                                fontSize: "1.1rem",
                                fontWeight: 700,
                                color: getScoreColor(item.score),
                              }}
                            >
                              {item.score}/100
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Evidence & Weaknesses */}
                    <div className="grid-2" style={{ gap: "1.5rem" }}>
                      <div>
                        <h4 style={{ fontSize: "0.95rem", color: "var(--accent-green)", marginBottom: "0.5rem" }}>
                          ✓ Supporting Evidence ({sim.evidence.length})
                        </h4>
                        {sim.evidence.length > 0 ? (
                          <ul style={{ display: "flex", flexDirection: "column", gap: "0.35rem", paddingLeft: "1.2rem" }}>
                            {sim.evidence.map((ev: string, i: number) => (
                              <li key={i} style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                                &ldquo;{ev}&rdquo;
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p style={{ fontSize: "0.85rem", color: "var(--text-dark)", fontStyle: "italic" }}>
                            No matching verified facts found.
                          </p>
                        )}
                      </div>

                      <div>
                        <h4 style={{ fontSize: "0.95rem", color: "var(--accent-red)", marginBottom: "0.5rem" }}>
                          ⚠️ Identified Weaknesses ({sim.weaknesses.length})
                        </h4>
                        {sim.weaknesses.length > 0 ? (
                          <ul style={{ display: "flex", flexDirection: "column", gap: "0.35rem", paddingLeft: "1.2rem" }}>
                            {sim.weaknesses.map((wk: string, i: number) => (
                              <li key={i} style={{ fontSize: "0.85rem", color: "var(--accent-amber)" }}>
                                {wk}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p style={{ fontSize: "0.85rem", color: "var(--accent-green)", fontStyle: "italic" }}>
                            No matching weaknesses.
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Competitor Threats */}
                    <div>
                      <h4 style={{ fontSize: "0.95rem", color: "var(--accent-amber)", marginBottom: "0.5rem" }}>
                        ⚔️ Competitor Strengths & Similarity Threats
                      </h4>
                      {sim.competitor_threats && sim.competitor_threats.length > 0 ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                          {sim.competitor_threats.map((threat: any, i: number) => (
                            <div
                              key={i}
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                background: "rgba(255, 75, 75, 0.03)",
                                borderLeft: "3px solid var(--accent-red)",
                                padding: "0.6rem 1rem",
                                borderRadius: "4px",
                                fontSize: "0.85rem",
                              }}
                            >
                              <div>
                                <strong>{threat.competitor}</strong> (Similarity: {threat.similarity})
                              </div>
                              <div style={{ color: "var(--text-muted)" }}>
                                Advantage: <em>{threat.advantage}</em>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p style={{ fontSize: "0.85rem", color: "var(--text-dark)", fontStyle: "italic" }}>
                          No direct competitors identified for comparison.
                        </p>
                      )}
                    </div>

                    {/* Improvement Actions */}
                    <div>
                      <h4 style={{ fontSize: "0.95rem", color: "var(--secondary)", marginBottom: "0.5rem" }}>
                        🛠️ Topic-Specific Optimization Actions:
                      </h4>
                      <ul style={{ display: "flex", flexDirection: "column", gap: "0.35rem", paddingLeft: "1.2rem" }}>
                        {sim.improvement_actions.map((act: string, i: number) => (
                          <li key={i} style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                            {act}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 🛡️ Section 3: Hallucination Quality Audit */}
      <div className="card glow-border">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h2 style={{ margin: 0 }}>🛡️ Hallucination Audit Report</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", margin: "0.25rem 0 0 0" }}>
              Verifies all AI-generated assertions, keywords, and questions against verbatim crawled facts.
            </p>
          </div>
          <div style={{ display: "flex", gap: "2rem" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Grounding Rate</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--accent-green)" }}>
                {hallucData.grounding_rate}%
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Hallucination Risk</div>
              <div
                style={{
                  fontSize: "1.5rem",
                  fontWeight: 800,
                  color: hallucData.hallucination_risk_score > 30 ? "var(--accent-red)" : "var(--accent-green)",
                }}
              >
                {hallucData.hallucination_risk_score}%
              </div>
            </div>
          </div>
        </div>

        {/* Audit recommendations */}
        {hallucData.recommendations && hallucData.recommendations.length > 0 && (
          <div
            style={{
              background: "rgba(255, 255, 255, 0.02)",
              border: "1px solid var(--border-color)",
              padding: "1rem",
              borderRadius: "10px",
              marginBottom: "1.5rem",
            }}
          >
            <ul style={{ display: "flex", flexDirection: "column", gap: "0.4rem", paddingLeft: "1.2rem" }}>
              {hallucData.recommendations.map((rec: string, idx: number) => (
                <li key={idx} style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  {rec}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Flag levels count */}
        <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
          {Object.entries(hallucData.by_level).map(([level, count]: any) => (
            <div
              key={level}
              style={{
                background: "rgba(255, 255, 255, 0.01)",
                border: "1px solid var(--border-color)",
                padding: "0.5rem 1rem",
                borderRadius: "8px",
                fontSize: "0.85rem",
              }}
            >
              <strong>{level}</strong>: {count}
            </div>
          ))}
        </div>

        {/* Flags Table */}
        <div className="table-container" style={{ margin: 0 }}>
          <table className="custom-table">
            <thead>
              <tr>
                <th>Element Type</th>
                <th>AI-Generated Claim / Item</th>
                <th>Status Flag</th>
                <th>Grounding Evidence</th>
              </tr>
            </thead>
            <tbody>
              {hallucData.flags && hallucData.flags.length > 0 ? (
                hallucData.flags.map((item: any, i: number) => (
                  <tr key={i}>
                    <td>
                      <span className="badge badge-info" style={{ fontSize: "0.7rem" }}>
                        {item.item_type}
                      </span>
                    </td>
                    <td>
                      <div
                        style={{
                          fontSize: "0.85rem",
                          maxWidth: "350px",
                          wordBreak: "break-word",
                          whiteSpace: "normal",
                        }}
                      >
                        {item.item_text}
                      </div>
                    </td>
                    <td>{getFlagBadge(item.flag_level)}</td>
                    <td>
                      {item.supporting_evidence ? (
                        <div
                          style={{
                            fontSize: "0.8rem",
                            color: "var(--accent-green)",
                            fontStyle: "italic",
                            maxWidth: "400px",
                            wordBreak: "break-word",
                            whiteSpace: "normal",
                          }}
                        >
                          &ldquo;{item.supporting_evidence}&rdquo;
                        </div>
                      ) : (
                        <span style={{ color: "var(--text-dark)", fontSize: "0.8rem", fontStyle: "italic" }}>
                          No citation found
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} style={{ textAlign: "center", color: "var(--text-dark)" }}>
                    No audit records checked yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ⚖️ Section 4: Agent Knowledge Consistency Audit */}
      <div className="card glow-border" style={{ borderLeft: `4px solid ${getScoreColor(consisData.consistency_score)}` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h2 style={{ margin: 0 }}>⚖️ Knowledge Graph & Agent Consistency</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", margin: "0.25rem 0 0 0" }}>
              Analyses conflicts, audience alignment contradictions, or orphan keywords between different platform agents.
            </p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>
              Consistency Score
            </div>
            <div
              style={{
                fontSize: "2.5rem",
                fontWeight: 800,
                color: getScoreColor(consisData.consistency_score),
              }}
            >
              {consisData.consistency_score}/100
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
              {consisData.overall_status.replace("_", " ")}
            </div>
          </div>
        </div>

        {/* Conflicts List */}
        {consisData.conflicts && consisData.conflicts.length > 0 ? (
          <div style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ fontSize: "1rem", color: "var(--accent-red)", marginBottom: "0.75rem" }}>
              🚨 Contradictions & Mismatches Detected ({consisData.total_conflicts}):
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {consisData.conflicts.map((conf: any, idx: number) => (
                <div
                  key={idx}
                  style={{
                    background: "rgba(255, 75, 75, 0.03)",
                    border: "1px solid rgba(255, 75, 75, 0.15)",
                    borderLeft: `4px solid ${conf.severity === "high" ? "var(--accent-red)" : "var(--accent-amber)"}`,
                    borderRadius: "8px",
                    padding: "0.85rem 1.25rem",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.35rem" }}>
                    <span
                      className="badge"
                      style={{
                        fontSize: "0.7rem",
                        background: conf.severity === "high" ? "rgba(255, 75, 75, 0.25)" : "rgba(255, 152, 0, 0.25)",
                        color: conf.severity === "high" ? "#FF8A8A" : "#FFD18A",
                      }}
                    >
                      {conf.severity} severity
                    </span>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      Involved: {conf.agents_involved.join(" &harr; ")}
                    </span>
                  </div>
                  <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-main)" }}>
                    {conf.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div
            style={{
              background: "rgba(0, 255, 136, 0.05)",
              border: "1px solid rgba(0, 255, 136, 0.2)",
              padding: "1rem",
              borderRadius: "10px",
              textAlign: "center",
              marginBottom: "1.5rem",
            }}
          >
            <span style={{ color: "var(--accent-green)", fontWeight: 600 }}>
              ✓ No active agent contradictions detected. Graph matches all metadata.
            </span>
          </div>
        )}

        {/* Warnings list */}
        {consisData.warnings && consisData.warnings.length > 0 && (
          <div style={{ marginBottom: "1.5rem" }}>
            <h4 style={{ fontSize: "0.95rem", color: "var(--accent-amber)", marginBottom: "0.5rem" }}>
              ⚠️ Warnings ({consisData.total_warnings})
            </h4>
            <ul style={{ display: "flex", flexDirection: "column", gap: "0.25rem", paddingLeft: "1.2rem" }}>
              {consisData.warnings.map((w: string, idx: number) => (
                <li key={idx} style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  {w}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Repair actions */}
        {consisData.repair_actions && consisData.repair_actions.length > 0 && (
          <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "1.25rem" }}>
            <h3 style={{ fontSize: "1rem", color: "var(--secondary)", marginBottom: "0.5rem" }}>
              🛠️ Recommended Repair Actions:
            </h3>
            <ul style={{ display: "flex", flexDirection: "column", gap: "0.4rem", paddingLeft: "1.2rem" }}>
              {consisData.repair_actions.map((act: string, idx: number) => (
                <li key={idx} style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  {act}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
