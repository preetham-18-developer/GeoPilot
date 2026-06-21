"use client";

import { useState, useEffect } from "react";

const API_BASE = "http://localhost:8000/api/v1";

interface ValidationTabProps {
  projectId: string;
  userId: string;
}

export default function ValidationTab({ projectId, userId }: ValidationTabProps) {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (projectId) {
      fetchReport();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const fetchReport = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/analysis/validation/${projectId}`, {
        headers: { Authorization: `Bearer mock-${userId}` },
      });
      const data = await res.json();
      if (res.ok) {
        setReport(data);
      } else {
        setError(data.detail || "Failed to load validation report.");
      }
    } catch {
      setError("Cannot connect to backend. Make sure the FastAPI server is running.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card flex-center" style={{ padding: "4rem" }}>
        <div className="spinner"></div>
        <p style={{ color: "var(--text-muted)", marginTop: "1rem" }}>
          Running quality auditors...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="card"
        style={{ borderLeft: "4px solid var(--accent-red)", padding: "1.5rem" }}
      >
        <p style={{ color: "var(--accent-red)", fontWeight: 600 }}>
          ⚠️ {error}
        </p>
        <button
          className="btn btn-secondary"
          style={{ marginTop: "1rem" }}
          onClick={fetchReport}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="card flex-center" style={{ padding: "4rem" }}>
        <p style={{ color: "var(--text-muted)" }}>
          No validation data available. Run an analysis first.
        </p>
      </div>
    );
  }

  const qa = report.question_audit;
  const kwa = report.keyword_audit;
  const statusColor =
    report.overall_status === "healthy"
      ? "var(--accent-green)"
      : report.overall_status === "warning"
      ? "var(--accent-amber)"
      : "var(--accent-red)";
  const statusIcon =
    report.overall_status === "healthy"
      ? "✅"
      : report.overall_status === "warning"
      ? "⚠️"
      : "🚨";

  return (
    <div>
      {/* Header / Overall Status */}
      <div
        className="card glow-border"
        style={{
          marginBottom: "2rem",
          background: "linear-gradient(135deg, rgba(110,0,255,0.05) 0%, rgba(0,255,136,0.02) 100%)",
          borderLeft: `4px solid ${statusColor}`,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: "1.6rem" }}>
              {statusIcon} Intelligence Quality Validation
            </h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", margin: "0.25rem 0 0 0" }}>
              Deterministic structural audit of all discovered questions and keywords.
              No LLM calls — pure heuristic analysis.
            </p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: 600 }}>
              Combined Quality Score
            </div>
            <div
              style={{
                fontSize: "3rem",
                fontWeight: 800,
                color: statusColor,
                lineHeight: 1,
              }}
            >
              {report.combined_quality_score}/100
            </div>
            <div
              style={{
                fontSize: "0.8rem",
                textTransform: "uppercase",
                color: statusColor,
                fontWeight: 700,
                marginTop: "0.25rem",
              }}
            >
              {report.overall_status}
            </div>
          </div>
        </div>

        <div
          className="grid-3"
          style={{ marginTop: "1.5rem", gap: "1rem" }}
        >
          {[
            { label: "Total Warnings", value: report.total_warnings, color: "var(--accent-amber)" },
            { label: "Total Suggestions", value: report.total_suggestions, color: "var(--secondary)" },
            { label: "Questions Audited", value: qa.total_questions, color: "var(--text-light)" },
          ].map(({ label, value, color }) => (
            <div
              key={label}
              style={{
                background: "rgba(255,255,255,0.03)",
                padding: "0.75rem 1rem",
                borderRadius: "10px",
                border: "1px solid var(--border-color)",
              }}
            >
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{label}</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 700, color }}>{value}</div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: "1rem", textAlign: "right" }}>
          <button className="btn btn-secondary" onClick={fetchReport} style={{ fontSize: "0.85rem" }}>
            ↻ Re-run Audit
          </button>
        </div>
      </div>

      {/* Question Quality Report */}
      <div className="card glow-border" style={{ marginBottom: "2rem" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "1.5rem",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          <div>
            <h2 style={{ margin: 0 }}>Question Quality Audit</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", margin: "0.25rem 0 0 0" }}>
              {qa.total_questions} questions audited for uniqueness, diversity, and completeness.
            </p>
          </div>
          <div style={{ textAlign: "right" }}>
            <span
              style={{
                fontSize: "2rem",
                fontWeight: 800,
                color:
                  qa.quality_score >= 80
                    ? "var(--accent-green)"
                    : qa.quality_score >= 60
                    ? "var(--accent-amber)"
                    : "var(--accent-red)",
              }}
            >
              {qa.quality_score}/100
            </span>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Quality Score</div>
          </div>
        </div>

        <div className="grid-3" style={{ gap: "1rem", marginBottom: "1.5rem" }}>
          {[
            {
              label: "Uniqueness Score",
              value: `${qa.uniqueness_score}/100`,
              good: qa.uniqueness_score >= 70,
            },
            {
              label: "Duplicate Pairs",
              value: qa.duplicate_count,
              good: qa.duplicate_count === 0,
            },
            {
              label: "Missing Answers",
              value: qa.missing_answers,
              good: qa.missing_answers === 0,
            },
            {
              label: "Category Diversity",
              value: qa.category_diversity.unique_categories,
              good: qa.category_diversity.ratio >= 0.6,
              suffix: " unique",
            },
            {
              label: "Template Violations",
              value: qa.template_violations.length,
              good: qa.template_violations.length === 0,
            },
            {
              label: "Low Confidence",
              value: qa.confidence_health.low_confidence_count,
              good: qa.confidence_health.low_confidence_count === 0,
            },
          ].map(({ label, value, good, suffix = "" }) => (
            <div
              key={label}
              style={{
                background: "rgba(255,255,255,0.03)",
                padding: "0.75rem 1rem",
                borderRadius: "10px",
                border: "1px solid var(--border-color)",
              }}
            >
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{label}</div>
              <div
                style={{
                  fontSize: "1.4rem",
                  fontWeight: 700,
                  marginTop: "0.25rem",
                  color: good ? "var(--accent-green)" : "var(--accent-red)",
                }}
              >
                {value}{suffix}
              </div>
            </div>
          ))}
        </div>

        {/* Category Distribution */}
        {qa.category_diversity.distribution &&
          Object.keys(qa.category_diversity.distribution).length > 0 && (
            <div style={{ marginBottom: "1.5rem" }}>
              <h4
                style={{
                  fontSize: "0.95rem",
                  marginBottom: "0.75rem",
                  color: "var(--text-light)",
                }}
              >
                Category Distribution
              </h4>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                {Object.entries(qa.category_diversity.distribution).map(
                  ([cat, count]: any) => (
                    <span
                      key={cat}
                      className="badge badge-info"
                      style={{ fontSize: "0.8rem" }}
                    >
                      {cat}: {count}
                    </span>
                  )
                )}
              </div>
            </div>
          )}

        {/* Warnings & Suggestions */}
        <AuditAlerts warnings={qa.warnings} suggestions={qa.suggestions} />
      </div>

      {/* Keyword Quality Report */}
      <div className="card glow-border" style={{ marginBottom: "2rem" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "1.5rem",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          <div>
            <h2 style={{ margin: 0 }}>Keyword Quality Audit</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", margin: "0.25rem 0 0 0" }}>
              {kwa.total_keywords} keywords audited for stem deduplication, intent coverage, and clustering.
            </p>
          </div>
          <div style={{ textAlign: "right" }}>
            <span
              style={{
                fontSize: "2rem",
                fontWeight: 800,
                color:
                  kwa.quality_score >= 80
                    ? "var(--accent-green)"
                    : kwa.quality_score >= 60
                    ? "var(--accent-amber)"
                    : "var(--accent-red)",
              }}
            >
              {kwa.quality_score}/100
            </span>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Quality Score</div>
          </div>
        </div>

        <div className="grid-3" style={{ gap: "1rem", marginBottom: "1.5rem" }}>
          {[
            {
              label: "Uniqueness Score",
              value: `${kwa.uniqueness_score}/100`,
              good: kwa.uniqueness_score >= 70,
            },
            {
              label: "Stem Duplication Rate",
              value: `${(kwa.stem_duplication.rate * 100).toFixed(0)}%`,
              good: kwa.stem_duplication.rate <= 0.25,
            },
            {
              label: "Category Saturated",
              value: kwa.category_saturation.saturated ? "YES" : "NO",
              good: !kwa.category_saturation.saturated,
            },
            {
              label: "Intent Coverage",
              value: `${kwa.intent_coverage.unique_count} / 4`,
              good: kwa.intent_coverage.unique_count >= 2,
            },
            {
              label: "Missing Clusters",
              value: kwa.missing_clusters,
              good: kwa.missing_clusters === 0,
            },
            {
              label: "High Priority %",
              value: `${kwa.total_keywords > 0 ? Math.round((kwa.priority_health.high_count / kwa.total_keywords) * 100) : 0}%`,
              good: kwa.priority_health.high_count > 0,
            },
          ].map(({ label, value, good }) => (
            <div
              key={label}
              style={{
                background: "rgba(255,255,255,0.03)",
                padding: "0.75rem 1rem",
                borderRadius: "10px",
                border: "1px solid var(--border-color)",
              }}
            >
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{label}</div>
              <div
                style={{
                  fontSize: "1.4rem",
                  fontWeight: 700,
                  marginTop: "0.25rem",
                  color: good ? "var(--accent-green)" : "var(--accent-red)",
                }}
              >
                {value}
              </div>
            </div>
          ))}
        </div>

        {/* Intent Coverage Pills */}
        <div style={{ marginBottom: "1.5rem" }}>
          <h4 style={{ fontSize: "0.95rem", marginBottom: "0.75rem", color: "var(--text-light)" }}>
            Search Intent Coverage
          </h4>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {["informational", "transactional", "navigational", "commercial"].map((intent) => {
              const present = kwa.intent_coverage.present.includes(intent);
              return (
                <span
                  key={intent}
                  className={`badge ${present ? "badge-success" : "badge-danger"}`}
                  style={{ textTransform: "capitalize", fontSize: "0.8rem" }}
                >
                  {present ? "✓" : "✗"} {intent}
                </span>
              );
            })}
          </div>
        </div>

        {/* Top Duplicate Stems */}
        {kwa.stem_duplication.top_stems.length > 0 && (
          <div style={{ marginBottom: "1.5rem" }}>
            <h4 style={{ fontSize: "0.95rem", marginBottom: "0.5rem", color: "var(--accent-amber)" }}>
              Top Duplicate Stems
            </h4>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              {kwa.stem_duplication.top_stems.map((stem: string) => (
                <span key={stem} className="badge badge-warning" style={{ fontSize: "0.8rem" }}>
                  {stem}
                </span>
              ))}
            </div>
          </div>
        )}

        <AuditAlerts warnings={kwa.warnings} suggestions={kwa.suggestions} />
      </div>
    </div>
  );
}

// ── Reusable Alerts Sub-component ─────────────────────────────────────────────

function AuditAlerts({
  warnings,
  suggestions,
}: {
  warnings: string[];
  suggestions: string[];
}) {
  if (!warnings.length && !suggestions.length) {
    return (
      <div
        style={{
          background: "rgba(0, 255, 136, 0.05)",
          border: "1px solid rgba(0, 255, 136, 0.2)",
          padding: "1rem",
          borderRadius: "10px",
          textAlign: "center",
        }}
      >
        <span style={{ color: "var(--accent-green)", fontWeight: 600 }}>
          ✓ No issues detected. Quality checks passed.
        </span>
      </div>
    );
  }

  return (
    <div
      style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
    >
      {warnings.length > 0 && (
        <div>
          <h4
            style={{
              fontSize: "0.95rem",
              color: "var(--accent-amber)",
              marginBottom: "0.5rem",
            }}
          >
            ⚠️ Warnings ({warnings.length})
          </h4>
          <ul
            style={{
              paddingLeft: "1.2rem",
              color: "var(--text-muted)",
              fontSize: "0.9rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.25rem",
            }}
          >
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {suggestions.length > 0 && (
        <div>
          <h4
            style={{
              fontSize: "0.95rem",
              color: "var(--secondary)",
              marginBottom: "0.5rem",
            }}
          >
            💡 Suggestions ({suggestions.length})
          </h4>
          <ul
            style={{
              paddingLeft: "1.2rem",
              color: "var(--text-muted)",
              fontSize: "0.9rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.25rem",
            }}
          >
            {suggestions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
