"use client";

interface CompetitorAnalysisTabProps {
  competitors: any[];
  competitorFeatureMatrix: any;
}

export default function CompetitorAnalysisTab({
  competitors,
  competitorFeatureMatrix,
}: CompetitorAnalysisTabProps) {
  return (
    <div>
      {/* Competitors List */}
      <div className="grid-2" style={{ marginBottom: "2.5rem" }}>
        {competitors.length > 0 ? (
          competitors.map((comp: any, i: number) => (
            <div key={i} className="card glow-border" style={{ position: "relative" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "1rem",
                }}
              >
                <h2 style={{ margin: 0 }}>{comp.name}</h2>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <span
                    className={`badge ${
                      comp.competitor_type === "direct"
                        ? "badge-danger"
                        : "badge-warning"
                    }`}
                  >
                    {comp.competitor_type}
                  </span>
                  <span className="badge badge-info" style={{ fontWeight: 800 }}>
                    {comp.similarity_score}% Similar
                  </span>
                </div>
              </div>
              <p
                style={{
                  fontStyle: "italic",
                  fontSize: "0.85rem",
                  color: "var(--text-muted)",
                  marginBottom: "0.75rem",
                }}
              >
                Description: {comp.description}
              </p>
              <p
                style={{
                  color: "var(--text-muted)",
                  fontSize: "0.85rem",
                  marginBottom: "1rem",
                }}
              >
                URL:{" "}
                <a
                  href={comp.website_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: "var(--secondary)" }}
                >
                  {comp.website_url || "NOT FOUND"}
                </a>
              </p>

              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.4rem",
                  fontSize: "0.8rem",
                  background: "rgba(255,255,255,0.02)",
                  padding: "0.75rem",
                  borderRadius: "8px",
                  marginBottom: "1rem",
                }}
              >
                <div>
                  <strong style={{ color: "var(--secondary)" }}>
                    Reason Selected:
                  </strong>{" "}
                  {comp.reason_selected?.join(", ") || "NOT FOUND"}
                </div>
                <div>
                  <strong>Industry Alignment:</strong> {comp.industry_match}
                </div>
                <div>
                  <strong>Audience Alignment:</strong> {comp.audience_match}
                </div>
                <div>
                  <strong>Service Alignment:</strong> {comp.service_match}
                </div>
              </div>

              {[
                { label: "Strengths", data: comp.strengths, color: "var(--accent-green)" },
                { label: "Weaknesses", data: comp.weaknesses, color: "var(--accent-red)" },
                { label: "Unique Features", data: comp.unique_features, color: "var(--secondary)" },
                { label: "Content Opportunities & Gaps", data: comp.market_gaps, color: "var(--accent-amber)" },
              ].map(({ label, data, color }) => (
                <div key={label} style={{ marginBottom: "1rem" }}>
                  <h4
                    style={{
                      color,
                      fontSize: "0.9rem",
                      marginBottom: "0.25rem",
                    }}
                  >
                    {label}
                  </h4>
                  <ul
                    style={{
                      paddingLeft: "1.2rem",
                      fontSize: "0.85rem",
                      color: "var(--text-muted)",
                    }}
                  >
                    {data?.map((item: string, idx: number) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          ))
        ) : (
          <div
            className="card flex-center"
            style={{ gridColumn: "1 / -1", padding: "4rem" }}
          >
            <p style={{ color: "var(--text-muted)" }}>
              No competitors analyzed yet.
            </p>
          </div>
        )}
      </div>

      {/* Feature Comparison Matrix */}
      {competitorFeatureMatrix && (
        <div className="card glow-border">
          <h2>Competitor Feature Comparison Matrix</h2>
          <p
            style={{
              color: "var(--text-muted)",
              fontSize: "0.9rem",
              marginBottom: "1.5rem",
            }}
          >
            Cross-examination of core features between our Client and detected
            industry competitors.
          </p>
          <div className="table-container">
            <table className="custom-table" style={{ fontSize: "0.9rem" }}>
              <thead>
                <tr>
                  <th>Optimization Feature</th>
                  <th style={{ color: "var(--secondary)", fontWeight: "bold" }}>
                    Our Client
                  </th>
                  {competitors.slice(0, 5).map((comp: any) => (
                    <th key={comp.id}>{comp.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(competitorFeatureMatrix.features || []).map(
                  (feat: any, idx: number) => (
                    <tr key={idx}>
                      <td>
                        <strong>{feat.feature_name}</strong>
                      </td>
                      <td
                        style={{
                          color: "var(--secondary)",
                          fontWeight: "bold",
                        }}
                      >
                        {feat.client_value}
                      </td>
                      {competitors.slice(0, 5).map((comp: any) => (
                        <td key={comp.id}>
                          {feat.competitor_values[comp.name] || "NOT_FOUND"}
                        </td>
                      ))}
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>

          <div
            className="grid-2"
            style={{
              gap: "1.5rem",
              marginTop: "1.5rem",
              borderTop: "1px solid var(--border-color)",
              paddingTop: "1.5rem",
            }}
          >
            <div>
              <h4
                style={{ color: "var(--accent-amber)", marginBottom: "0.5rem" }}
              >
                Unique Competitor Offerings:
              </h4>
              <ul
                style={{
                  paddingLeft: "1.2rem",
                  color: "var(--text-muted)",
                  fontSize: "0.85rem",
                }}
              >
                {competitorFeatureMatrix.unique_competitor_features?.map(
                  (uf: string, idx: number) => <li key={idx}>{uf}</li>
                )}
              </ul>
            </div>
            <div>
              <h4
                style={{ color: "var(--accent-red)", marginBottom: "0.5rem" }}
              >
                Missing Client Features (Gaps):
              </h4>
              <ul
                style={{
                  paddingLeft: "1.2rem",
                  color: "var(--text-muted)",
                  fontSize: "0.85rem",
                }}
              >
                {competitorFeatureMatrix.missing_client_features?.map(
                  (mf: string, idx: number) => <li key={idx}>{mf}</li>
                )}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
