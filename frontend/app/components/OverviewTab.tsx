"use client";

import React, { useState, useEffect } from "react";
import { RadialGauge, StatCard, ProgressBar, getScoreColor, getScoreLabel } from "./ui/RadialGauge";
import { EmptyState, SectionHeader } from "./ui/SkeletonLoader";

interface OverviewTabProps {
  projectId: string;
  userId: string;
  results: any;
  latestReport: any;
  triggerAnalysisRun: () => void;
  projectDetail?: any;
  onDownloadReport?: (format: "json" | "md") => void;
}

function AnimatedCounter({ target, duration = 1200 }: { target: number; duration?: number }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (target === 0) { setCount(0); return; }
    const start = Date.now();
    const update = () => {
      const elapsed = Date.now() - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      setCount(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(update);
    };
    requestAnimationFrame(update);
  }, [target, duration]);

  return <>{count}</>;
}

function SparklineBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div style={{ display: "flex", alignItems: "flex-end", height: "32px", width: "8px" }}>
      <div
         style={{
          width: "100%",
          background: "var(--primary)",
          borderRadius: "2px 2px 0 0",
          height: `${Math.max(4, pct)}%`,
          opacity: 0.7,
          transition: "height 0.5s ease",
        }}
      />
    </div>
  );
}

export default function OverviewTab({ projectId, userId, results, latestReport, triggerAnalysisRun, projectDetail, onDownloadReport }: OverviewTabProps) {
  const [localGeoScore, setLocalGeoScore] = useState<number>(0);
  const [localRecommendationProb, setLocalRecommendationProb] = useState<number>(0);
  const [localVerifiedFacts, setLocalVerifiedFacts] = useState<number>(0);
  const [localLlmQueries, setLocalLlmQueries] = useState<number>(0);
  const [localKeywordClusters, setLocalKeywordClusters] = useState<number>(0);
  const [localQaHealth, setLocalQaHealth] = useState<number | null>(null);
  const [localApprovalStatus, setLocalApprovalStatus] = useState<string | null>(null);
  const [hasLoadedOverview, setHasLoadedOverview] = useState<boolean>(false);

  useEffect(() => {
    const fetchOverview = async () => {
      if (!projectId) return;
      console.log('[AIVOP] Fetching overview for:', projectId);
      try {
        const response = await fetch(
          `http://localhost:8000/api/v1/projects/${projectId}/overview`,
          {
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer mock-${userId}`
            }
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log('[AIVOP] Overview response:', data);

        // Map response fields to state
        setLocalGeoScore(data.geo_score ?? 0);
        setLocalRecommendationProb(data.recommendation_probability ?? 0);
        setLocalVerifiedFacts(data.verified_facts_count ?? 0);
        setLocalLlmQueries(data.questions_count ?? 0);
        setLocalKeywordClusters(data.keyword_clusters_count ?? 0);
        setLocalQaHealth(data.qa_health ?? null);
        setLocalApprovalStatus(data.approval_status ?? null);
        setHasLoadedOverview(true);

      } catch (err) {
        console.error('Overview fetch failed:', err);
      }
    };

    fetchOverview();
  }, [projectId, userId]);

  const score = results.ai_visibility_score;
  const geoScore = hasLoadedOverview ? localGeoScore : (score?.overall_score ?? 0);
  const scoreColor = getScoreColor(geoScore);

  // Compute AI platform probabilities from simulations
  const simulations = results.recommendation_simulations ?? [];
  const avgProb = hasLoadedOverview ? localRecommendationProb : (
    simulations.length > 0
      ? Math.round(simulations.reduce((s: number, sim: any) => s + (sim.recommendation_probability ?? 0), 0) / simulations.length)
      : 0
  );

  const verifiedFactsCount = hasLoadedOverview ? localVerifiedFacts : (results.verified_facts?.length ?? 0);
  const llmQueriesCount = hasLoadedOverview ? localLlmQueries : (results.questions_count ?? 0);
  const keywordClustersCount = hasLoadedOverview ? localKeywordClusters : (
    results.keyword_clusters_count ?? (results.keywords_count ? Math.max(1, Math.floor(results.keywords_count / 10)) : 0)
  );

  // Sub-scores for progress bars
  const subScores: [string, number][] = Object.entries(score?.sub_scores ?? {}).slice(0, 6) as [string, number][];

  // Quick Wins from qa report recommendations
  const quickWins: string[] = (score?.recommendations ?? []).slice(0, 3);

  // Critical issues from qa report
  const criticalIssues: string[] = (results.qa_report?.checks?.unsupported_claims ?? []).slice(0, 3);
  const qaScore = hasLoadedOverview ? localQaHealth : (results.qa_report?.qa_score ?? null);
  const approvalStatus = hasLoadedOverview ? localApprovalStatus : (results.qa_report?.approval_status ?? "flagged");

  const hasData = geoScore > 0 || avgProb > 0 || verifiedFactsCount > 0 || llmQueriesCount > 0 || latestReport;

  return (
    <div className="animate-fade-in">
      <SectionHeader
        title="Executive Overview"
        subtitle="AI Visibility intelligence summary for this project"
        actions={
          <button className="btn btn-primary" onClick={triggerAnalysisRun}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            Run Analysis
          </button>
        }
      />

      {!hasData ? (
        <EmptyState
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="48" height="48">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          }
          title="No intelligence generated yet"
          description="Run your first analysis to populate the executive dashboard with GEO scores, recommendations, and competitor insights."
          action={
            <button className="btn btn-primary" onClick={triggerAnalysisRun}>
              Run Initial Analysis
            </button>
          }
        />
      ) : (
        <>
          {/* ── Row 1: GEO Score + AI Platform Probabilities ──────────── */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1.25rem", marginBottom: "1.25rem" }}>
            {/* GEO Score Dial */}
            <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "2rem", minWidth: 200 }}>
              <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-dark)", marginBottom: "1rem" }}>
                GEO Score
              </div>
              <RadialGauge
                value={geoScore}
                size={140}
                strokeWidth={4}
                color={scoreColor}
                label={
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "2rem", fontWeight: 800, color: "var(--text-primary)", lineHeight: 1 }}>
                      <AnimatedCounter target={geoScore} />
                    </div>
                    <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", marginTop: 4 }}>/ 100</div>
                  </div>
                }
              />
              <div style={{ marginTop: "1rem" }}>
                <span className={`badge ${geoScore >= 80 ? "badge-success" : geoScore >= 60 ? "badge-warning" : "badge-danger"}`} style={{ fontSize: "0.75rem" }}>
                  {getScoreLabel(geoScore)}
                </span>
              </div>
            </div>

            {/* AI Platform Probabilities + QA Score */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "1rem" }}>
              {/* Recommendation Probability */}
              <div className="stat-card" style={{ justifyContent: "space-between" }}>
                <span className="stat-label">Recommendation Prob.</span>
                <div className="stat-value" style={{ color: "var(--secondary)", fontSize: "2.25rem" }}>
                  <AnimatedCounter target={avgProb} />
                  <span style={{ fontSize: "1rem", fontWeight: 500 }}>%</span>
                </div>
                <ProgressBar value={avgProb} color="var(--secondary)" />
              </div>

              {/* Facts */}
              <div className="stat-card">
                <span className="stat-label">Verified Facts</span>
                <div className="stat-value" style={{ color: "var(--accent-green)" }}>
                  <AnimatedCounter target={verifiedFactsCount} />
                </div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-dark)" }}>extracted & verified</span>
              </div>

              {/* Questions */}
              <div className="stat-card">
                <span className="stat-label">LLM Queries</span>
                <div className="stat-value" style={{ color: "var(--primary)" }}>
                  <AnimatedCounter target={llmQueriesCount} />
                </div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-dark)" }}>discovered</span>
              </div>

              {/* Keywords */}
              <div className="stat-card">
                <span className="stat-label">Keyword Clusters</span>
                <div className="stat-value" style={{ color: "var(--accent-amber)" }}>
                  <AnimatedCounter target={keywordClustersCount} />
                </div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-dark)" }}>semantic groups</span>
              </div>

              {/* QA Score */}
              {qaScore !== null && (
                <div className="stat-card">
                  <span className="stat-label">QA Health</span>
                  <div className="stat-value" style={{ color: getScoreColor(qaScore), fontSize: "2.25rem" }}>
                    <AnimatedCounter target={Math.round(qaScore)} />
                    <span style={{ fontSize: "1rem", fontWeight: 500 }}>/100</span>
                  </div>
                  <span className={`badge ${approvalStatus === "approved" ? "badge-success" : "badge-danger"}`} style={{ fontSize: "0.65rem" }}>
                    {approvalStatus === "approved" ? "✓ Approved" : "⚠ Flagged"}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* ── Row 2: Sub-Scores + Quick Wins ────────────────────────── */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem", marginBottom: "1.25rem" }}>
            {/* Engine Sub-Scores */}
            {subScores.length > 0 && (
              <div className="card">
                <h3 style={{ marginBottom: "1.25rem", fontSize: "0.9375rem" }}>Engine Sub-Scores</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
                  {subScores.map(([key, val]) => (
                    <ProgressBar
                      key={key}
                      value={val}
                      label={key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      showLabel
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Quick Wins + Critical Issues */}
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {quickWins.length > 0 && (
                <div className="card" style={{ borderLeft: "3px solid var(--accent-green)" }}>
                  <h3 style={{ marginBottom: "0.875rem", fontSize: "0.9375rem", color: "var(--accent-green)" }}>
                    ⚡ Quick Wins
                  </h3>
                  <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.625rem" }}>
                    {quickWins.map((win, i) => (
                      <li key={i} style={{ fontSize: "0.8375rem", color: "var(--text-muted)", display: "flex", gap: "0.5rem" }}>
                        <span style={{ color: "var(--accent-green)", flexShrink: 0 }}>→</span>
                        {win}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {criticalIssues.length > 0 && (
                <div className="card" style={{ borderLeft: "3px solid var(--accent-red)" }}>
                  <h3 style={{ marginBottom: "0.875rem", fontSize: "0.9375rem", color: "var(--accent-red)" }}>
                    ⚠ Critical Issues
                  </h3>
                  <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.625rem" }}>
                    {criticalIssues.map((issue, i) => (
                      <li key={i} style={{ fontSize: "0.8375rem", color: "var(--text-muted)", display: "flex", gap: "0.5rem" }}>
                        <span style={{ color: "var(--accent-red)", flexShrink: 0 }}>!</span>
                        {issue}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* ── Row 3: Recommendation Simulations ─────────────────────── */}
          {simulations.length > 0 && (
            <div className="card" style={{ marginBottom: "1.25rem" }}>
              <h3 style={{ marginBottom: "1.25rem", fontSize: "0.9375rem" }}>
                AI Recommendation Simulations
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
                {simulations.slice(0, 3).map((sim: any, idx: number) => (
                  <div
                    key={idx}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "1.25rem",
                      padding: "0.875rem 1rem",
                      background: "var(--bg-card-hover)",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--border-color)",
                    }}
                  >
                    <RadialGauge
                      value={sim.recommendation_probability ?? 0}
                      size={52}
                      strokeWidth={4}
                      color={getScoreColor(sim.recommendation_probability)}
                      label={
                        <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--text-primary)" }}>
                          {sim.recommendation_probability}%
                        </span>
                      }
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: "0.875rem", color: "var(--text-main)", fontWeight: 500, marginBottom: "0.2rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        &ldquo;{sim.query}&rdquo;
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-dark)" }}>
                        {(sim.supporting_evidence ?? []).length} supporting signals · {(sim.missing_requirements ?? []).length} gaps
                      </div>
                    </div>
                    <span className={`badge ${sim.recommendation_probability >= 70 ? "badge-success" : sim.recommendation_probability >= 50 ? "badge-warning" : "badge-danger"}`}>
                      {sim.recommendation_probability >= 70 ? "Likely" : sim.recommendation_probability >= 50 ? "Possible" : "Unlikely"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Row 4: Executive Summary ───────────────────────────────── */}
          {latestReport && (
            <div className="card">
              <h3 style={{ marginBottom: "1rem", fontSize: "0.9375rem" }}>Executive Summary</h3>
              <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", lineHeight: 1.7, marginBottom: "1.5rem" }}>
                {latestReport.content?.executive_summary}
              </p>

              {latestReport.content?.swot && (
                <div className="grid-2">
                  <div style={{ background: "var(--accent-green-dim)", border: "1px solid color-mix(in srgb, var(--accent-green) 20%, transparent)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
                    <h4 style={{ color: "var(--accent-green)", marginBottom: "0.75rem", fontSize: "0.875rem" }}>Strengths</h4>
                    <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                      {(latestReport.content.swot.strengths ?? []).map((s: string, i: number) => (
                        <li key={i} style={{ fontSize: "0.8125rem", color: "var(--text-muted)", display: "flex", gap: "0.5rem" }}>
                          <span style={{ color: "var(--accent-green)" }}>✓</span> {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div style={{ background: "var(--accent-red-dim)", border: "1px solid color-mix(in srgb, var(--accent-red) 20%, transparent)", borderRadius: "var(--radius-md)", padding: "1rem" }}>
                    <h4 style={{ color: "var(--accent-red)", marginBottom: "0.75rem", fontSize: "0.875rem" }}>Weaknesses</h4>
                    <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                      {(latestReport.content.swot.weaknesses ?? []).map((w: string, i: number) => (
                        <li key={i} style={{ fontSize: "0.8125rem", color: "var(--text-muted)", display: "flex", gap: "0.5rem" }}>
                          <span style={{ color: "var(--accent-red)" }}>!</span> {w}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Row 5: Export Reports Collapsible Accordion ────────────── */}
          <CollapsibleAccordion title="Export Optimization Reports">
            <p style={{ color: "var(--text-muted)", margin: "0 0 1.5rem 0", fontSize: "0.875rem", lineHeight: 1.6 }}>
              Download your AI Visibility optimization package in Markdown format
              (perfect for copying straight to documentation) or JSON format (for custom pipeline integrations).
            </p>

            {latestReport ? (
              <div style={{ display: "flex", gap: "1rem" }}>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => onDownloadReport?.("md")}
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ marginRight: "4px" }}
                  >
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v4M7 10l5 5 5-5M12 15V3" />
                  </svg>
                  Download Markdown (.md)
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onDownloadReport?.("json")}
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ marginRight: "4px" }}
                  >
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v4M7 10l5 5 5-5M12 15V3" />
                  </svg>
                  Download JSON (.json)
                </button>
              </div>
            ) : (
              <p style={{ color: "var(--accent-red)", fontSize: "0.875rem", margin: 0 }}>
                No report available yet. Please execute an analysis run first.
              </p>
            )}
          </CollapsibleAccordion>
        </>
      )}
    </div>
  );
}

function CollapsibleAccordion({ title, children }: { title: string; children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "8px", overflow: "hidden", background: "var(--bg-card)", marginTop: "1.5rem" }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: "100%",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "16px 20px",
          fontFamily: "var(--font-title)",
          fontSize: "15px",
          fontWeight: 600,
          background: "none",
          border: "none",
          cursor: "pointer",
          color: "var(--text-primary)",
          textAlign: "left",
        }}
      >
        <span>{title}</span>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform var(--transition-fast)",
            opacity: 0.7,
            color: "var(--text-primary)",
          }}
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>
      {isOpen && (
        <div style={{ padding: "20px", borderTop: "1px solid var(--border)", background: "var(--bg-base)" }}>
          {children}
        </div>
      )}
    </div>
  );
}
