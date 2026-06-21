"use client";

interface OverviewTabProps {
  results: any;
  latestReport: any;
  triggerAnalysisRun: () => void;
}

export default function OverviewTab({
  results,
  latestReport,
  triggerAnalysisRun,
}: OverviewTabProps) {
  return (
    <div>
      {/* Quality Assurance Audit Card */}
      {results.qa_report && (
        <div
          className="card glow-border"
          style={{
            marginBottom: "2rem",
            borderLeft:
              results.qa_report.approval_status === "approved"
                ? "4px solid var(--accent-green)"
                : "4px solid var(--accent-red)",
            background: "rgba(255,255,255,0.02)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              flexWrap: "wrap",
              gap: "1rem",
              marginBottom: "1.5rem",
            }}
          >
            <div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                  marginBottom: "0.25rem",
                }}
              >
                <h2 style={{ fontSize: "1.5rem", margin: 0 }}>
                  Quality Assurance Audit
                </h2>
                <span
                  className={`badge ${
                    results.qa_report.approval_status === "approved"
                      ? "badge-success"
                      : "badge-danger"
                  }`}
                  style={{ fontSize: "0.85rem", padding: "0.35rem 0.85rem" }}
                >
                  {results.qa_report.approval_status === "approved"
                    ? "✓ Approved"
                    : "⚠️ Flagged"}
                </span>
              </div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                Programmatic and semantic checks to verify optimization
                intelligence reliability.
              </p>
            </div>
            <div style={{ textAlign: "right" }}>
              <div
                style={{
                  fontSize: "0.85rem",
                  color: "var(--text-muted)",
                  fontWeight: 600,
                }}
              >
                QA Health Score
              </div>
              <div
                style={{
                  fontSize: "2.2rem",
                  fontWeight: 800,
                  color:
                    results.qa_report.qa_score >= 80
                      ? "var(--accent-green)"
                      : results.qa_report.qa_score >= 70
                      ? "var(--accent-amber)"
                      : "var(--accent-red)",
                }}
              >
                {results.qa_report.qa_score.toFixed(0)}/100
              </div>
            </div>
          </div>

          <div
            className="grid-3"
            style={{ gap: "1rem", marginBottom: "1.5rem" }}
          >
            {[
              {
                label: "Duplicate Facts",
                value: results.qa_report.checks?.duplicate_facts_count ?? 0,
                goodWhen: 0,
                color: "amber",
              },
              {
                label: "Missing Evidence",
                value: results.qa_report.checks?.missing_evidence_count ?? 0,
                goodWhen: 0,
                color: "red",
              },
              {
                label: "Low Confidence Facts",
                value:
                  results.qa_report.checks?.low_confidence_facts_count ?? 0,
                goodWhen: 0,
                color: "amber",
              },
            ].map(({ label, value, goodWhen, color }) => (
              <div
                key={label}
                style={{
                  background: "rgba(255, 255, 255, 0.03)",
                  padding: "1rem",
                  borderRadius: "12px",
                  border: "1px solid var(--border-color)",
                }}
              >
                <div
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--text-muted)",
                    fontWeight: 600,
                  }}
                >
                  {label}
                </div>
                <div
                  style={{
                    fontSize: "1.6rem",
                    fontWeight: 700,
                    marginTop: "0.25rem",
                    color:
                      value === goodWhen
                        ? "var(--accent-green)"
                        : `var(--accent-${color})`,
                  }}
                >
                  {value}
                </div>
              </div>
            ))}
          </div>

          {results.qa_report.checks?.unsupported_claims &&
            results.qa_report.checks.unsupported_claims.length > 0 && (
              <div
                style={{
                  borderTop: "1px solid var(--border-color)",
                  paddingTop: "1.25rem",
                }}
              >
                <h4
                  style={{
                    color: "var(--accent-red)",
                    marginBottom: "0.5rem",
                    fontSize: "0.95rem",
                  }}
                >
                  ⚠️ Unsupported claims detected (potential hallucinations):
                </h4>
                <ul
                  style={{
                    paddingLeft: "1.25rem",
                    fontSize: "0.9rem",
                    color: "var(--text-muted)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.35rem",
                  }}
                >
                  {results.qa_report.checks.unsupported_claims.map(
                    (claim: string, idx: number) => (
                      <li key={idx}>{claim}</li>
                    )
                  )}
                </ul>
              </div>
            )}
        </div>
      )}

      {/* AI Visibility Scoring Engine */}
      {results.ai_visibility_score && (
        <div
          className="card glow-border"
          style={{
            marginBottom: "2rem",
            background:
              "linear-gradient(135deg, rgba(110,0,255,0.05) 0%, rgba(0,255,136,0.02) 100%)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1.5rem",
            }}
          >
            <div>
              <h2 style={{ fontSize: "1.6rem", margin: 0 }}>
                AI Visibility Readiness Index
              </h2>
              <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                Calculated based on search queries, content completeness,
                structured schema and trust metrics.
              </p>
            </div>
            <div style={{ textAlign: "right" }}>
              <span
                style={{ fontSize: "3rem", fontWeight: 800, color: "var(--secondary)" }}
              >
                {results.ai_visibility_score.overall_score}/100
              </span>
            </div>
          </div>

          <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>
            Engine Sub-Scores
          </h3>
          <div
            className="grid-3"
            style={{ gap: "1rem", marginBottom: "1.5rem" }}
          >
            {Object.entries(results.ai_visibility_score.sub_scores || {}).map(
              ([key, val]: any) => (
                <div
                  key={key}
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    padding: "0.75rem 1rem",
                    borderRadius: "10px",
                    border: "1px solid var(--border-color)",
                  }}
                >
                  <div
                    style={{
                      textTransform: "capitalize",
                      fontSize: "0.8rem",
                      color: "var(--text-muted)",
                    }}
                  >
                    {key.replace("_", " ")}
                  </div>
                  <div
                    style={{
                      fontSize: "1.3rem",
                      fontWeight: 700,
                      marginTop: "0.25rem",
                      color:
                        val >= 70
                          ? "var(--accent-green)"
                          : val >= 50
                          ? "var(--accent-amber)"
                          : "var(--accent-red)",
                    }}
                  >
                    {val}%
                  </div>
                </div>
              )
            )}
          </div>

          <div
            style={{
              borderTop: "1px solid var(--border-color)",
              paddingTop: "1rem",
            }}
          >
            <h4
              style={{
                color: "var(--secondary)",
                fontSize: "0.95rem",
                marginBottom: "0.5rem",
              }}
            >
              Key Recommendations:
            </h4>
            <ul
              style={{
                paddingLeft: "1.2rem",
                fontSize: "0.9rem",
                color: "var(--text-muted)",
              }}
            >
              {results.ai_visibility_score.recommendations?.map(
                (r: string, idx: number) => (
                  <li key={idx} style={{ marginBottom: "0.25rem" }}>
                    • {r}
                  </li>
                )
              )}
            </ul>
          </div>
        </div>
      )}

      {/* Recommendation Simulation Engine */}
      {results.recommendation_simulations &&
        results.recommendation_simulations.length > 0 && (
          <div className="card" style={{ marginBottom: "2rem" }}>
            <h2 style={{ marginBottom: "1rem" }}>
              AI Recommendation Simulation Engine
            </h2>
            <p
              style={{
                color: "var(--text-muted)",
                fontSize: "0.95rem",
                marginBottom: "1.5rem",
              }}
            >
              Simulates semantic user search queries inside LLMs (like ChatGPT,
              Gemini, Perplexity) to verify if the business is organically
              recommended.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
              {results.recommendation_simulations.map(
                (sim: any, idx: number) => (
                  <div
                    key={idx}
                    className="card glow-border"
                    style={{ padding: "1.25rem", background: "rgba(255,255,255,0.01)" }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "1rem",
                      }}
                    >
                      <h3 style={{ margin: 0, fontSize: "1.1rem" }}>
                        &quot;{sim.query}&quot;
                      </h3>
                      <div style={{ textAlign: "right" }}>
                        <span
                          style={{
                            fontSize: "0.8rem",
                            color: "var(--text-muted)",
                            display: "block",
                          }}
                        >
                          Recommendation Likelihood
                        </span>
                        <strong
                          style={{
                            fontSize: "1.3rem",
                            color:
                              sim.recommendation_probability >= 70
                                ? "var(--accent-green)"
                                : sim.recommendation_probability >= 50
                                ? "var(--accent-amber)"
                                : "var(--accent-red)",
                          }}
                        >
                          {sim.recommendation_probability}%
                        </strong>
                      </div>
                    </div>
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "0.5rem",
                        borderLeft: "2px solid var(--border-color)",
                        paddingLeft: "1rem",
                        fontSize: "0.9rem",
                      }}
                    >
                      <div>
                        <strong style={{ color: "var(--accent-green)" }}>
                          ✓ Supporting Evidence:
                        </strong>
                        <ul
                          style={{
                            paddingLeft: "1.2rem",
                            color: "var(--text-muted)",
                            marginTop: "0.25rem",
                          }}
                        >
                          {sim.supporting_evidence?.map(
                            (e: string, i: number) => <li key={i}>{e}</li>
                          )}
                        </ul>
                      </div>
                      <div style={{ marginTop: "0.5rem" }}>
                        <strong style={{ color: "var(--accent-red)" }}>
                          ⚠️ Missing Requirements:
                        </strong>
                        <ul
                          style={{
                            paddingLeft: "1.2rem",
                            color: "var(--text-muted)",
                            marginTop: "0.25rem",
                          }}
                        >
                          {sim.missing_requirements?.map(
                            (m: string, i: number) => <li key={i}>{m}</li>
                          )}
                        </ul>
                      </div>
                      <div style={{ marginTop: "0.5rem" }}>
                        <strong style={{ color: "var(--secondary)" }}>
                          💡 Improvement Actions:
                        </strong>
                        <ul
                          style={{
                            paddingLeft: "1.2rem",
                            color: "var(--text-muted)",
                            marginTop: "0.25rem",
                          }}
                        >
                          {sim.improvement_actions?.map(
                            (imp: string, i: number) => <li key={i}>{imp}</li>
                          )}
                        </ul>
                      </div>
                    </div>
                  </div>
                )
              )}
            </div>
          </div>
        )}

      {/* Executive Summary / Empty State */}
      {latestReport ? (
        <div className="card">
          <h2 style={{ marginBottom: "1rem" }}>Executive Summary</h2>
          <p
            style={{
              lineHeight: 1.6,
              color: "var(--text-muted)",
              marginBottom: "2rem",
            }}
          >
            {latestReport.content.executive_summary}
          </p>

          <h2 style={{ marginBottom: "1rem" }}>
            AI Recommendation System Gaps
          </h2>
          <p
            style={{
              lineHeight: 1.6,
              color: "var(--text-muted)",
              marginBottom: "2rem",
            }}
          >
            {latestReport.content.ai_visibility_analysis}
          </p>

          <div className="grid-2">
            <div className="card" style={{ padding: "1.5rem" }}>
              <h3
                style={{ color: "var(--accent-green)", marginBottom: "0.5rem" }}
              >
                SWOT Strengths
              </h3>
              <ul>
                {latestReport.content.swot?.strengths?.map(
                  (str: string, i: number) => (
                    <li
                      key={i}
                      style={{ color: "var(--text-muted)", marginBottom: "0.5rem" }}
                    >
                      ✓ {str}
                    </li>
                  )
                )}
              </ul>
            </div>
            <div className="card" style={{ padding: "1.5rem" }}>
              <h3
                style={{ color: "var(--accent-red)", marginBottom: "0.5rem" }}
              >
                SWOT Weaknesses
              </h3>
              <ul>
                {latestReport.content.swot?.weaknesses?.map(
                  (wk: string, i: number) => (
                    <li
                      key={i}
                      style={{ color: "var(--text-muted)", marginBottom: "0.5rem" }}
                    >
                      ⚠️ {wk}
                    </li>
                  )
                )}
              </ul>
            </div>
          </div>
        </div>
      ) : (
        <div
          className="card flex-center"
          style={{ flexDirection: "column", padding: "4rem" }}
        >
          <p style={{ color: "var(--text-muted)", marginBottom: "1.5rem" }}>
            No intelligence has been generated yet for this project.
          </p>
          <button className="btn btn-primary" onClick={triggerAnalysisRun}>
            Trigger Initial Analysis Run
          </button>
        </div>
      )}
    </div>
  );
}
