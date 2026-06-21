"use client";

import { useState } from "react";

interface BusinessIntelligenceTabProps {
  results: any;
}

export default function BusinessIntelligenceTab({
  results,
}: BusinessIntelligenceTabProps) {
  const [selectedGraphNode, setSelectedGraphNode] = useState<string | null>(null);

  if (!results.business_profile) {
    return (
      <div className="card flex-center" style={{ padding: "4rem" }}>
        <p style={{ color: "var(--text-muted)" }}>
          No business profile loaded. Run crawlers to evaluate SWOT.
        </p>
      </div>
    );
  }

  const bp = results.business_profile;

  return (
    <div>
      {/* Brand Details Card */}
      <div className="card glow-border" style={{ marginBottom: "2rem" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "1.5rem",
            marginBottom: "1.5rem",
          }}
        >
          <div>
            <h2 style={{ fontSize: "1.8rem", margin: 0 }}>{bp.company_name}</h2>
            <span
              className="badge badge-info"
              style={{ marginTop: "0.5rem", display: "inline-block" }}
            >
              {bp.industry}
            </span>
            <span
              className="badge badge-success"
              style={{ marginTop: "0.5rem", marginLeft: "0.5rem", display: "inline-block" }}
            >
              {bp.business_model}
            </span>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "1rem", fontSize: "0.95rem" }}>
          <p style={{ color: "var(--text-muted)", lineHeight: 1.6 }}>
            <strong>Description:</strong> {bp.description}
          </p>
          <p style={{ color: "var(--text-muted)" }}>
            <strong>Corporate Mission:</strong> {bp.mission}
          </p>
          <p style={{ color: "var(--text-muted)" }}>
            <strong>Corporate Vision:</strong> {bp.vision}
          </p>
          <p style={{ color: "var(--text-muted)" }}>
            <strong>Target Audience:</strong> {bp.target_audience}
          </p>
          <p style={{ color: "var(--text-muted)" }}>
            <strong>Unique Selling Proposition (USP):</strong>{" "}
            <strong style={{ color: "var(--secondary)" }}>{bp.usp}</strong>
          </p>
        </div>

        {/* Trust Signals */}
        <div
          style={{
            marginTop: "1.5rem",
            borderTop: "1px solid var(--border-color)",
            paddingTop: "1.5rem",
          }}
        >
          <h4
            style={{
              color: "var(--accent-green)",
              fontSize: "1rem",
              marginBottom: "0.5rem",
            }}
          >
            Verified Trust Signals &amp; Credentials
          </h4>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {bp.trust_signals && bp.trust_signals.length > 0 ? (
              bp.trust_signals.map((sig: string, idx: number) => (
                <span
                  key={idx}
                  className="badge badge-success"
                  style={{
                    background: "rgba(0, 255, 136, 0.1)",
                    color: "var(--accent-green)",
                  }}
                >
                  ✓ {sig}
                </span>
              ))
            ) : (
              <span style={{ color: "var(--text-muted)" }}>NOT FOUND</span>
            )}
          </div>
        </div>

        {/* AI Opportunities */}
        <div
          style={{
            marginTop: "1.5rem",
            borderTop: "1px solid var(--border-color)",
            paddingTop: "1.5rem",
          }}
        >
          <h4
            style={{
              color: "var(--secondary)",
              fontSize: "1rem",
              marginBottom: "0.5rem",
            }}
          >
            AI Visibility Opportunities
          </h4>
          <ul
            style={{
              paddingLeft: "1.2rem",
              fontSize: "0.9rem",
              color: "var(--text-muted)",
            }}
          >
            {bp.ai_visibility_opportunities && bp.ai_visibility_opportunities.length > 0 ? (
              bp.ai_visibility_opportunities.map((opp: string, idx: number) => (
                <li key={idx} style={{ marginBottom: "0.25rem" }}>
                  {opp}
                </li>
              ))
            ) : (
              <li style={{ color: "var(--text-muted)" }}>NOT FOUND</li>
            )}
          </ul>
        </div>
      </div>

      {/* SWOT Analysis */}
      <div className="grid-2" style={{ gap: "2rem", marginBottom: "2rem" }}>
        {[
          {
            label: "Strengths (S)",
            data: bp.strengths,
            color: "var(--accent-green)",
            border: "var(--accent-green)",
            bg: "rgba(0, 255, 136, 0.02)",
            icon: "✓",
          },
          {
            label: "Weaknesses (W)",
            data: bp.weaknesses,
            color: "var(--accent-red)",
            border: "var(--accent-red)",
            bg: "rgba(255, 70, 70, 0.02)",
            icon: "⚠️",
          },
          {
            label: "Opportunities (O)",
            data: bp.opportunities,
            color: "var(--accent-amber)",
            border: "var(--accent-amber)",
            bg: "rgba(255, 170, 0, 0.02)",
            icon: "↗",
          },
          {
            label: "Risks (T)",
            data: bp.risks,
            color: "var(--primary)",
            border: "var(--primary)",
            bg: "rgba(110, 0, 255, 0.02)",
            icon: "⚡",
          },
        ].map(({ label, data, color, border, bg, icon }) => (
          <div
            key={label}
            className="card"
            style={{ borderLeft: `4px solid ${border}`, background: bg }}
          >
            <h3 style={{ color, marginBottom: "0.75rem" }}>{label}</h3>
            <ul
              style={{
                paddingLeft: "1.2rem",
                color: "var(--text-muted)",
                fontSize: "0.9rem",
              }}
            >
              {data?.map((item: string, idx: number) => (
                <li key={idx} style={{ marginBottom: "0.25rem" }}>
                  {icon} {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Knowledge Graph Explorer */}
      {results.entity_nodes && results.entity_nodes.length > 0 && (
        <div className="card glow-border" style={{ marginBottom: "2rem" }}>
          <h2>Knowledge Graph Explorer</h2>
          <p
            style={{
              color: "var(--text-muted)",
              fontSize: "0.9rem",
              marginBottom: "1rem",
            }}
          >
            Discovered entities and predicate relationships extracted from
            crawling the target website. Click an entity to explorer its
            semantic relationships.
          </p>
          <div
            style={{
              display: "flex",
              gap: "1rem",
              flexWrap: "wrap",
              marginBottom: "1.5rem",
              borderBottom: "1px solid var(--border-color)",
              paddingBottom: "1rem",
            }}
          >
            {results.entity_nodes.map((node: any) => (
              <button
                key={node.id}
                onClick={() =>
                  setSelectedGraphNode(
                    selectedGraphNode === node.entity_name
                      ? null
                      : node.entity_name
                  )
                }
                className={`btn ${
                  selectedGraphNode === node.entity_name
                    ? "btn-primary"
                    : "btn-secondary"
                }`}
                style={{
                  padding: "0.4rem 0.8rem",
                  fontSize: "0.85rem",
                  borderRadius: "20px",
                }}
              >
                📁 {node.entity_name} ({node.entity_type})
              </button>
            ))}
          </div>

          {selectedGraphNode ? (
            <div
              className="card"
              style={{ background: "rgba(255,255,255,0.02)", padding: "1rem" }}
            >
              <h3 style={{ fontSize: "1.1rem", marginBottom: "0.5rem" }}>
                Semantic Links for{" "}
                <span style={{ color: "var(--secondary)" }}>
                  {selectedGraphNode}
                </span>
              </h3>
              <div className="table-container">
                <table className="custom-table" style={{ fontSize: "0.85rem" }}>
                  <thead>
                    <tr>
                      <th>Subject Node</th>
                      <th>Predicate Link</th>
                      <th>Object Node</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.entity_relationships
                      .filter(
                        (r: any) =>
                          r.source_node_id ===
                            results.entity_nodes.find(
                              (n: any) => n.entity_name === selectedGraphNode
                            )?.id ||
                          r.target_node_id ===
                            results.entity_nodes.find(
                              (n: any) => n.entity_name === selectedGraphNode
                            )?.id
                      )
                      .map((rel: any, idx: number) => {
                        const srcNode = results.entity_nodes.find(
                          (n: any) => n.id === rel.source_node_id
                        );
                        const tgtNode = results.entity_nodes.find(
                          (n: any) => n.id === rel.target_node_id
                        );
                        return (
                          <tr key={idx}>
                            <td
                              style={{
                                color:
                                  srcNode?.entity_name === selectedGraphNode
                                    ? "var(--secondary)"
                                    : "inherit",
                              }}
                            >
                              {srcNode?.entity_name} ({srcNode?.entity_type})
                            </td>
                            <td>
                              <span className="badge badge-info">
                                {rel.relationship_type}
                              </span>
                            </td>
                            <td
                              style={{
                                color:
                                  tgtNode?.entity_name === selectedGraphNode
                                    ? "var(--secondary)"
                                    : "inherit",
                              }}
                            >
                              {tgtNode?.entity_name} ({tgtNode?.entity_type})
                            </td>
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div
              style={{
                color: "var(--text-muted)",
                fontSize: "0.9rem",
                fontStyle: "italic",
                textAlign: "center",
                padding: "1rem",
              }}
            >
              Select an entity node above to visualize its knowledge graph
              relationships.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
