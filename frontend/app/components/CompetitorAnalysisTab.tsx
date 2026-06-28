"use client";

import { useState } from "react";
import { NoDataState } from "./ui/SkeletonLoader";
import { ProgressBar } from "./ui/RadialGauge";

interface CompetitorAnalysisTabProps {
  competitors: any[];
  competitorFeatureMatrix: any;
}

function CompetitorCard({ comp, index }: { comp: any; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const isDirect = comp.competitor_type === "direct";

  const sections = [
    { label: "Strengths", data: comp.strengths, color: "var(--accent-green)", icon: "↑" },
    { label: "Weaknesses", data: comp.weaknesses, color: "var(--accent-red)", icon: "↓" },
    { label: "Unique Features", data: comp.unique_features, color: "var(--secondary)", icon: "★" },
    { label: "Content Gaps", data: comp.market_gaps, color: "var(--accent-amber)", icon: "!" },
  ];

  return (
    <div className={`card ${isDirect ? "glow-border" : ""}`} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="flex items-center gap-2 mb-1">
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: "var(--radius-sm)",
                background: isDirect ? "var(--accent-red-dim)" : "var(--accent-amber-dim)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "0.875rem",
                fontWeight: 700,
                color: isDirect ? "#FCA5A5" : "#FCD34D",
                flexShrink: 0,
              }}
            >
              {comp.name?.charAt(0).toUpperCase()}
            </div>
            <h3 style={{ margin: 0, fontSize: "1rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{comp.name}</h3>
          </div>
          {comp.website_url && (
            <a
              href={comp.website_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: "0.75rem", color: "var(--secondary)", overflow: "hidden", textOverflow: "ellipsis", display: "block" }}
              onClick={(e) => e.stopPropagation()}
            >
              {comp.website_url}
            </a>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`badge ${isDirect ? "badge-danger" : "badge-warning"}`}>
            {comp.competitor_type ?? "indirect"}
          </span>
          <span className="badge badge-muted" style={{ fontSize: "0.7rem" }}>
            {comp.similarity_score ?? 0}% similar
          </span>
        </div>
      </div>

      {/* Similarity bar */}
      <ProgressBar value={comp.similarity_score ?? 0} color={isDirect ? "var(--accent-red)" : "var(--accent-amber)"} height={4} />

      {/* Alignment scores */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.5rem", fontSize: "0.75rem" }}>
        {[
          { label: "Industry", val: comp.industry_match },
          { label: "Audience", val: comp.audience_match },
          { label: "Service", val: comp.service_match },
        ].map(({ label, val }) => (
          <div key={label} style={{ background: "rgba(255,255,255,0.03)", borderRadius: "var(--radius-sm)", padding: "0.4rem 0.5rem", border: "1px solid var(--border-color)" }}>
            <div style={{ color: "var(--text-dark)", marginBottom: "0.15rem" }}>{label}</div>
            <div style={{ color: "var(--text-muted)", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {val ?? "N/A"}
            </div>
          </div>
        ))}
      </div>

      {/* Description */}
      {comp.description && (
        <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", margin: 0, lineHeight: 1.6 }}>
          {comp.description}
        </p>
      )}

      {/* Reason selected */}
      {comp.reason_selected?.length > 0 && (
        <div style={{ display: "flex", gap: "0.375rem", flexWrap: "wrap" }}>
          {comp.reason_selected.map((r: string, i: number) => (
            <span key={i} className="badge badge-purple" style={{ fontSize: "0.7rem" }}>{r}</span>
          ))}
        </div>
      )}

      {/* Expand: Strengths / Weaknesses / Features / Gaps */}
      <button
        className="btn btn-ghost btn-sm"
        style={{ justifyContent: "flex-start", gap: "0.5rem", paddingLeft: 0 }}
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          style={{ transition: "transform 0.2s", transform: expanded ? "rotate(90deg)" : "rotate(0deg)" }}>
          <path d="m9 18 6-6-6-6" />
        </svg>
        {expanded ? "Collapse" : "Show"} analysis
      </button>

      {expanded && (
        <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "0.875rem", borderTop: "1px solid var(--border-color)", paddingTop: "0.875rem" }}>
          {sections.map(({ label, data, color, icon }) =>
            data?.length > 0 ? (
              <div key={label}>
                <h4 style={{ fontSize: "0.8125rem", color, marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <span>{icon}</span> {label}
                </h4>
                <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                  {data.map((item: string, i: number) => (
                    <li key={i} style={{ fontSize: "0.8125rem", color: "var(--text-muted)", display: "flex", gap: "0.5rem", lineHeight: 1.5 }}>
                      <span style={{ color, flexShrink: 0 }}>—</span>{item}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null
          )}
        </div>
      )}
    </div>
  );
}

export default function CompetitorAnalysisTab({ competitors, competitorFeatureMatrix }: CompetitorAnalysisTabProps) {
  const [matrixExpanded, setMatrixExpanded] = useState(false);

  return (
    <div className="animate-fade-in">
      {/* Competitor cards */}
      {competitors.length === 0 ? (
        <NoDataState title="No competitors analyzed" description="Run an analysis to discover and benchmark industry competitors." />
      ) : (
        <>
          {/* Header stats */}
          <div className="grid-4 mb-6">
            {[
              { label: "Total Competitors", val: competitors.length, color: "var(--primary)" },
              { label: "Direct", val: competitors.filter((c) => c.competitor_type === "direct").length, color: "var(--accent-red)" },
              { label: "Indirect", val: competitors.filter((c) => c.competitor_type !== "direct").length, color: "var(--accent-amber)" },
              { label: "Avg Similarity", val: `${Math.round(competitors.reduce((s, c) => s + (c.similarity_score ?? 0), 0) / competitors.length)}%`, color: "var(--secondary)" },
            ].map(({ label, val, color }) => (
              <div key={label} className="stat-card">
                <span className="stat-label">{label}</span>
                <span className="stat-value" style={{ color }}>{val}</span>
              </div>
            ))}
          </div>

          <div className="card-grid mb-6">
            {competitors.map((comp, i) => (
              <CompetitorCard key={comp.id ?? i} comp={comp} index={i} />
            ))}
          </div>
        </>
      )}

      {/* Feature Matrix — keep as table (comparison matrix is appropriate) */}
      {competitorFeatureMatrix && (
        <div className="card">
          <button
            className="flex items-center justify-between w-full"
            style={{ background: "none", border: "none", cursor: "pointer", textAlign: "left", width: "100%" }}
            onClick={() => setMatrixExpanded((v) => !v)}
            aria-expanded={matrixExpanded}
          >
            <div>
              <h3 style={{ margin: 0, fontSize: "1rem" }}>Feature Comparison Matrix</h3>
              <p style={{ color: "var(--text-dark)", fontSize: "0.8125rem", marginTop: "0.2rem" }}>
                Cross-examine core features between client and competitors
              </p>
            </div>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-dark)" strokeWidth="2"
              style={{ transition: "transform 0.25s", transform: matrixExpanded ? "rotate(180deg)" : "rotate(0deg)", flexShrink: 0 }}>
              <path d="m6 9 6 6 6-6" />
            </svg>
          </button>

          {matrixExpanded && (
            <div className="animate-fade-in" style={{ marginTop: "1.25rem", borderTop: "1px solid var(--border-color)", paddingTop: "1.25rem" }}>
              <div className="table-container">
                <table className="custom-table" style={{ fontSize: "0.8375rem" }}>
                  <thead>
                    <tr>
                      <th>Feature</th>
                      <th style={{ color: "var(--secondary)" }}>Our Client</th>
                      {competitors.slice(0, 5).map((c) => <th key={c.id}>{c.name}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {(competitorFeatureMatrix.features ?? []).map((feat: any, i: number) => (
                      <tr key={i}>
                        <td><strong>{feat.feature_name}</strong></td>
                        <td style={{ color: "var(--secondary)", fontWeight: 600 }}>{feat.client_value}</td>
                        {competitors.slice(0, 5).map((c) => (
                          <td key={c.id} style={{ color: "var(--text-muted)" }}>{feat.competitor_values?.[c.name] ?? "—"}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="grid-2" style={{ marginTop: "1.25rem", gap: "1rem" }}>
                {[
                  { title: "Unique Competitor Offerings", items: competitorFeatureMatrix.unique_competitor_features, color: "var(--accent-amber)" },
                  { title: "Missing Client Features", items: competitorFeatureMatrix.missing_client_features, color: "var(--accent-red)" },
                ].map(({ title, items, color }) => (
                  <div key={title} style={{ background: "rgba(255,255,255,0.02)", borderRadius: "var(--radius-md)", padding: "1rem", border: "1px solid var(--border-color)" }}>
                    <h4 style={{ color, fontSize: "0.875rem", marginBottom: "0.75rem" }}>{title}</h4>
                    <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                      {items?.map((item: string, i: number) => (
                        <li key={i} style={{ fontSize: "0.8125rem", color: "var(--text-muted)", display: "flex", gap: "0.5rem" }}>
                          <span style={{ color }}>—</span>{item}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
