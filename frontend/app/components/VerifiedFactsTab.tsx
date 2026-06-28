"use client";

import React, { useState } from "react";
import { ChevronDown } from "./ui/Icons";

interface VerifiedFactsTabProps {
  facts: any[];
  expandedFactIds: Record<string, boolean>;
  onToggleExpand: (factId: string) => void;
}

function FactDetailCard({ content }: { content: any }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const keysList = Object.keys(content || {}).join(", ");
  const factTitle = keysList ? `Attributes: ${keysList}` : "Fact Details";

  return (
    <div
      className="fact-card"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "16px",
      }}
    >
      <div
        className="fact-header"
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          cursor: "pointer",
        }}
      >
        <span
          className="fact-key"
          style={{
            fontWeight: 600,
            fontSize: "14px",
            color: "var(--text-primary)",
            textTransform: "capitalize",
          }}
        >
          {factTitle}
        </span>
        <ChevronDown
          style={{
            transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform var(--transition-fast)",
            opacity: 0.7,
            color: "var(--text-primary)",
          }}
        />
      </div>
      {isExpanded && (
        <div
          className="fact-value"
          style={{
            fontSize: "13px",
            color: "var(--text-muted)",
            paddingTop: "8px",
            whiteSpace: "pre-wrap",
            fontFamily: "var(--font-mono)",
          }}
        >
          {JSON.stringify(content, null, 2)}
        </div>
      )}
    </div>
  );
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
              <React.Fragment key={fact.id || i}>
                <tr>
                  <td>
                    <span className="badge badge-info">{fact.fact_type}</span>
                  </td>
                  <td>
                    <FactDetailCard content={fact.content} />
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
                    key={`exp-${fact.id || i}`}
                    style={{ background: "color-mix(in srgb, var(--text-primary) 2%, transparent)" }}
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
              </React.Fragment>
            ))
          ) : (
            <tr>
              <td
                colSpan={4}
                style={{ textAlign: "center", color: "var(--text-dark)", padding: "2rem" }}
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
