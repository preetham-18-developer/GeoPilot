"use client";

import { NoDataState } from "./ui/SkeletonLoader";
import { ProgressBar, getScoreColor } from "./ui/RadialGauge";

interface ContentOpportunitiesTabProps {
  contentOpportunities: any[];
  contentCoverage: any[];
  gapAnalysis: any[];
}

const PRIORITY_CONFIG: Record<string, { badge: string; label: string; accent: string }> = {
  high: { badge: "badge-danger", label: "HIGH", accent: "var(--accent-red)" },
  medium: { badge: "badge-warning", label: "MED", accent: "var(--accent-amber)" },
  low: { badge: "badge-info", label: "LOW", accent: "var(--accent-blue)" },
};

function OpportunityCard({ opp }: { opp: any }) {
  const prio = PRIORITY_CONFIG[opp.priority?.toLowerCase()] ?? PRIORITY_CONFIG.medium;
  const impact = opp.impact_score ?? 0;
  const effort = opp.effort_score ?? 0;
  const roi = impact - effort;

  return (
    <div className="card card-interactive" style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <span className={`badge ${prio.badge}`} style={{ fontSize: "0.7rem" }}>{prio.label} Priority</span>
        <span className="badge badge-success" style={{ textTransform: "capitalize" }}>{opp.content_type}</span>
      </div>

      {/* Title */}
      <h3 style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.45, margin: 0 }}>{opp.title}</h3>

      {/* Impact vs Effort */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.5rem" }}>
        {[
          { label: "Impact", value: impact, color: getScoreColor(impact) },
          { label: "Effort", value: effort, color: "var(--accent-amber)" },
          { label: "ROI", value: Math.max(0, roi), color: roi > 30 ? "var(--accent-green)" : "var(--text-muted)" },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ background: "rgba(255,255,255,0.03)", borderRadius: "var(--radius-sm)", padding: "0.5rem", border: "1px solid var(--border-color)", textAlign: "center" }}>
            <div style={{ fontSize: "0.65rem", color: "var(--text-dark)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.2rem" }}>{label}</div>
            <div style={{ fontSize: "1.125rem", fontWeight: 700, color }}>{value}/100</div>
          </div>
        ))}
      </div>

      {/* Bars */}
      <ProgressBar value={impact} label="Impact Score" showLabel color={getScoreColor(impact)} height={4} />
      <ProgressBar value={effort} label="Effort Required" showLabel color="var(--accent-amber)" height={4} />

      {/* Details */}
      <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {opp.reason && (
          <p style={{ margin: 0 }}>
            <span style={{ color: "var(--text-dark)" }}>GEO Rationale: </span>{opp.reason}
          </p>
        )}
        {opp.expected_benefit && (
          <p style={{ margin: 0 }}>
            <span style={{ color: "var(--text-dark)" }}>Expected Benefit: </span>{opp.expected_benefit}
          </p>
        )}
      </div>

      {/* Keyword/Question tags */}
      {(opp.related_keywords?.length > 0 || opp.related_questions?.length > 0) && (
        <div style={{ display: "flex", gap: "0.375rem", flexWrap: "wrap" }}>
          {opp.related_keywords?.slice(0, 3).map((kw: string, i: number) => (
            <span key={i} className="badge badge-purple" style={{ fontSize: "0.68rem" }}>{kw}</span>
          ))}
          {opp.related_questions?.slice(0, 2).map((q: string, i: number) => (
            <span key={i} className="badge badge-info" style={{ fontSize: "0.68rem" }}>{q.length > 40 ? q.slice(0, 40) + "…" : q}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function CoverageRow({ cov }: { cov: any }) {
  const score = cov.coverage_score ?? 0;
  const color = getScoreColor(score);

  return (
    <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-color)", borderRadius: "var(--radius-md)", padding: "1rem 1.25rem" }}>
      <div className="flex items-center justify-between mb-2">
        <h4 style={{ margin: 0, fontSize: "0.9375rem" }}>{cov.topic_name}</h4>
        <div className="flex items-center gap-3">
          <span className="badge badge-muted">{cov.content_depth}</span>
          <span style={{ fontSize: "1.25rem", fontWeight: 700, color }}>{score}%</span>
        </div>
      </div>
      <ProgressBar value={score} color={color} height={6} />
      {cov.missing_content_areas?.length > 0 && (
        <div style={{ marginTop: "0.75rem", fontSize: "0.8125rem", color: "var(--accent-red)" }}>
          Missing: {cov.missing_content_areas.join(", ")}
        </div>
      )}
    </div>
  );
}

export default function ContentOpportunitiesTab({ contentOpportunities, contentCoverage, gapAnalysis }: ContentOpportunitiesTabProps) {
  return (
    <div className="animate-fade-in">
      {/* Coverage Dashboard */}
      {contentCoverage?.length > 0 && (
        <div className="card mb-6">
          <h3 style={{ marginBottom: "1rem", fontSize: "1rem" }}>Content Coverage Dashboard</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {contentCoverage.map((cov, i) => <CoverageRow key={i} cov={cov} />)}
          </div>
        </div>
      )}

      {/* Gap Analysis — card grid (replaces table) */}
      {gapAnalysis?.length > 0 && (
        <div className="mb-6">
          <h3 style={{ marginBottom: "1rem", fontSize: "1rem" }}>GEO Gap Prioritization</h3>
          <div className="card-grid">
            {gapAnalysis.map((gap, i) => {
              const prio = PRIORITY_CONFIG[gap.priority?.toLowerCase()] ?? PRIORITY_CONFIG.medium;
              return (
                <div key={i} className="card" style={{ borderLeft: `3px solid ${prio.accent}` }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className={`badge ${prio.badge}`} style={{ fontSize: "0.7rem" }}>{prio.label}</span>
                  </div>
                  <h4 style={{ fontSize: "0.9rem", marginBottom: "0.625rem", color: "var(--text-main)" }}>{gap.gap_type}</h4>
                  <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", margin: 0, lineHeight: 1.6 }}>{gap.recommendation}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Content Opportunity Cards */}
      <h3 style={{ marginBottom: "1rem", fontSize: "1rem" }}>Scored Content Recommendations</h3>
      {!contentOpportunities?.length ? (
        <NoDataState
          title="No opportunities identified"
          description="Run an analysis to discover content gaps and page creation opportunities."
        />
      ) : (
        <div className="card-grid">
          {contentOpportunities.map((opp, i) => <OpportunityCard key={i} opp={opp} />)}
        </div>
      )}
    </div>
  );
}
