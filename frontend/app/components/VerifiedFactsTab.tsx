"use client";

interface VerifiedFactsTabProps {
  facts: any[];
  expandedFactIds: Record<string, boolean>;
  onToggleExpand: (factId: string) => void;
}

export default function VerifiedFactsTab({
  facts,
  expandedFactIds,
  onToggleExpand,
}: VerifiedFactsTabProps) {
  return (
    <div className="table-container">
      <table className="custom-table">
        <thead>
          <tr>
            <th>Fact Type</th>
            <th>Extracted Fact Details</th>
            <th>Confidence Score</th>
            <th>Audit Action</th>
          </tr>
        </thead>
        <tbody>
          {facts.length > 0 ? (
            facts.map((fact: any, i: number) => (
              <>
                <tr key={i}>
                  <td>
                    <span className="badge badge-info">{fact.fact_type}</span>
                  </td>
                  <td>
                    <pre
                      style={{
                        fontSize: "0.8rem",
                        color: "var(--text-muted)",
                        whiteSpace: "pre-wrap",
                        margin: 0,
                      }}
                    >
                      {JSON.stringify(fact.content, null, 2)}
                    </pre>
                  </td>
                  <td>
                    <strong
                      style={{
                        color:
                          fact.confidence_score > 0.9
                            ? "var(--accent-green)"
                            : "var(--accent-amber)",
                      }}
                    >
                      {(fact.confidence_score * 100).toFixed(0)}%
                    </strong>
                  </td>
                  <td>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: "0.3rem 0.6rem", fontSize: "0.8rem" }}
                      onClick={() => onToggleExpand(fact.id)}
                    >
                      {expandedFactIds[fact.id] ? "Hide Evidence" : "Expand Evidence"}
                    </button>
                  </td>
                </tr>
                {expandedFactIds[fact.id] && (
                  <tr
                    key={`exp-${i}`}
                    style={{ background: "rgba(255,255,255,0.02)" }}
                  >
                    <td
                      colSpan={4}
                      style={{
                        padding: "1.25rem",
                        borderLeft: "4px solid var(--accent-green)",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "0.5rem",
                          fontSize: "0.85rem",
                        }}
                      >
                        <p
                          style={{
                            color: "var(--accent-green)",
                            fontStyle: "italic",
                            margin: 0,
                          }}
                        >
                          <strong>Verbatim Evidence Snippet:</strong>{" "}
                          &quot;{fact.evidence}&quot;
                        </p>
                        <p style={{ margin: 0 }}>
                          <strong>Source Page URL:</strong>{" "}
                          <a
                            href={fact.source_url}
                            target="_blank"
                            rel="noreferrer"
                            style={{ color: "var(--secondary)" }}
                          >
                            {fact.source_url}
                          </a>
                        </p>
                        <p style={{ margin: 0 }}>
                          <strong>Verification Confidence:</strong>{" "}
                          {(fact.confidence_score * 100).toFixed(1)}% |{" "}
                          <strong>Status:</strong> Verified by Trust Engine
                        </p>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))
          ) : (
            <tr>
              <td
                colSpan={4}
                style={{ textAlign: "center", color: "var(--text-dark)" }}
              >
                No facts verified yet. Click &quot;Run AI Crawler &amp; Agents&quot; to
                start.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
