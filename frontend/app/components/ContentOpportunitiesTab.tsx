"use client";

interface ContentOpportunitiesTabProps {
  contentOpportunities: any[];
  contentCoverage: any[];
  gapAnalysis: any[];
}

export default function ContentOpportunitiesTab({
  contentOpportunities,
  contentCoverage,
  gapAnalysis,
}: ContentOpportunitiesTabProps) {
  return (
    <div>
      {/* Content Coverage Dashboard */}
      {contentCoverage && contentCoverage.length > 0 && (
        <div className="card glow-border" style={{ marginBottom: "2.5rem" }}>
          <h2>Content Coverage Dashboard</h2>
          <p
            style={{
              color: "var(--text-muted)",
              fontSize: "0.9rem",
              marginBottom: "1.5rem",
            }}
          >
            Assesses topical completeness of crawled website content compared to
            target business topics.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            {contentCoverage.map((cov: any, idx: number) => (
              <div
                key={idx}
                style={{
                  background: "rgba(255,255,255,0.01)",
                  border: "1px solid var(--border-color)",
                  padding: "1.25rem",
                  borderRadius: "10px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "0.5rem",
                  }}
                >
                  <h3 style={{ margin: 0 }}>{cov.topic_name}</h3>
                  <strong
                    style={{
                      fontSize: "1.4rem",
                      color:
                        cov.coverage_score >= 85
                          ? "var(--accent-green)"
                          : cov.coverage_score >= 70
                          ? "var(--accent-amber)"
                          : "var(--accent-red)",
                    }}
                  >
                    {cov.coverage_score}% Coverage
                  </strong>
                </div>
                <div
                  style={{
                    color: "var(--text-muted)",
                    fontSize: "0.85rem",
                    marginBottom: "1rem",
                  }}
                >
                  Content Depth:{" "}
                  <span className="badge badge-info">{cov.content_depth}</span>
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.5rem",
                    fontSize: "0.85rem",
                  }}
                >
                  <div>
                    <strong>Covered Questions:</strong>{" "}
                    {cov.question_coverage?.join(", ") || "None"}
                  </div>
                  <div>
                    <strong>Covered Keywords:</strong>{" "}
                    {cov.keyword_coverage?.join(", ") || "None"}
                  </div>
                  <div>
                    <strong>FAQ Points Covered:</strong>{" "}
                    {cov.faq_coverage?.join(", ") || "None"}
                  </div>
                  <div style={{ marginTop: "0.5rem", color: "var(--accent-red)" }}>
                    <strong>Missing Areas:</strong>{" "}
                    {cov.missing_content_areas?.join(", ") || "None"}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Gap Analysis */}
      {gapAnalysis && gapAnalysis.length > 0 && (
        <div className="card" style={{ marginBottom: "2.5rem" }}>
          <h2>GEO Gap Prioritization Matrix</h2>
          <p
            style={{
              color: "var(--text-muted)",
              fontSize: "0.9rem",
              marginBottom: "1.5rem",
            }}
          >
            Prioritized gaps in pages, schemas, and reviews that are preventing
            recommendations.
          </p>
          <div className="table-container">
            <table className="custom-table" style={{ fontSize: "0.9rem" }}>
              <thead>
                <tr>
                  <th>Actionable Gap</th>
                  <th>Priority</th>
                  <th>Improvement Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {gapAnalysis.map((gap: any, i: number) => (
                  <tr key={i}>
                    <td>
                      <strong>{gap.gap_type}</strong>
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          gap.priority === "high"
                            ? "badge-danger"
                            : gap.priority === "medium"
                            ? "badge-warning"
                            : "badge-info"
                        }`}
                      >
                        {gap.priority.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ color: "var(--text-muted)" }}>
                      {gap.recommendation}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Scored Content Recommendations */}
      <h2>Scored Content Recommendations</h2>
      <p
        style={{
          color: "var(--text-muted)",
          fontSize: "0.9rem",
          marginBottom: "1.5rem",
        }}
      >
        Actionable page creation recommendations scored on effort vs visibility
        impact.
      </p>
      <div className="grid-2">
        {contentOpportunities && contentOpportunities.length > 0 ? (
          contentOpportunities.map((opp: any, i: number) => (
            <div
              key={i}
              className="card glow-border"
              style={{ padding: "1.5rem" }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "1rem",
                }}
              >
                <span
                  className={`badge ${
                    opp.priority === "high"
                      ? "badge-danger"
                      : opp.priority === "medium"
                      ? "badge-warning"
                      : "badge-info"
                  }`}
                >
                  {opp.priority.toUpperCase()} Priority
                </span>
                <span className="badge badge-success">{opp.content_type}</span>
              </div>
              <h3 style={{ marginBottom: "0.75rem", fontSize: "1.2rem" }}>
                {opp.title}
              </h3>

              <div
                className="grid-2"
                style={{
                  gap: "0.75rem",
                  background: "rgba(255,255,255,0.02)",
                  padding: "0.5rem",
                  borderRadius: "6px",
                  fontSize: "0.85rem",
                  marginBottom: "1rem",
                }}
              >
                <div>
                  Impact score:{" "}
                  <strong style={{ color: "var(--accent-green)" }}>
                    {opp.impact_score}/100
                  </strong>
                </div>
                <div>
                  Complexity/Effort:{" "}
                  <strong style={{ color: "var(--accent-amber)" }}>
                    {opp.effort_score}/100
                  </strong>
                </div>
              </div>

              <div
                style={{
                  fontSize: "0.85rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.4rem",
                  color: "var(--text-muted)",
                }}
              >
                <p style={{ margin: 0 }}>
                  <strong>GEO Rationale:</strong> {opp.reason}
                </p>
                <p style={{ margin: 0 }}>
                  <strong>Expected Benefit:</strong> {opp.expected_benefit}
                </p>
                <p style={{ margin: 0, color: "var(--accent-green)" }}>
                  <strong>Supporting Evidence:</strong> &quot;
                  {opp.supporting_evidence}&quot;
                </p>
                <p style={{ margin: 0 }}>
                  <strong>Target Keywords:</strong>{" "}
                  {opp.related_keywords?.join(", ") || "None"}
                </p>
                <p style={{ margin: 0 }}>
                  <strong>Target Questions:</strong>{" "}
                  {opp.related_questions?.join(", ") || "None"}
                </p>
              </div>
            </div>
          ))
        ) : (
          <div
            className="card flex-center"
            style={{ gridColumn: "1 / -1", padding: "4rem" }}
          >
            <p style={{ color: "var(--text-muted)" }}>
              No content opportunities identified yet. Run agents to audit.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
