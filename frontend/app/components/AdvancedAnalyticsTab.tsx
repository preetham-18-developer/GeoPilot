"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE, authHeader } from "../lib/config";

interface AnalyticsData {
  trends: any;
  before_after_cards: any[];
  explainability: any;
}

const METRICS_LIST = [
  { key: "visibility_score", label: "Visibility", color: "#8b5cf6" },
  { key: "recommendation_score", label: "Recommendation", color: "#06b6d4" },
  { key: "grounding_score", label: "Grounding", color: "#10b981" },
  { key: "consistency_score", label: "Consistency", color: "#f59e0b" },
  { key: "coverage_score", label: "Content Coverage", color: "#ec4899" },
];

// Inline custom SVG sparkline chart
const ScoreSparkline = ({ runs, metricKey, color }: { runs: any[]; metricKey: string; color: string }) => {
  if (!runs || runs.length < 2) {
    return <div style={{ height: "120px", display: "flex", alignItems: "center", justifyContent: "center", color: "rgba(255,255,255,0.2)", fontSize: "0.85rem" }}>Not enough runs to plot trends</div>;
  }

  const vals = runs.map(r => r[metricKey] ?? 0);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  
  const width = 500;
  const height = 120;
  const padding = 15;
  
  const points = vals.map((v, i) => {
    const x = padding + (i / (vals.length - 1)) * (width - 2 * padding);
    const y = height - padding - ((v - min) / range) * (height - 2 * padding);
    return `${x},${y}`;
  }).join(" ");

  return (
    <div style={{ position: "relative", width: "100%", height: "140px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "12px", padding: "10px" }}>
      <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <polyline points={points} fill="none" stroke={color} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
        {vals.map((v, i) => {
          const x = padding + (i / (vals.length - 1)) * (width - 2 * padding);
          const y = height - padding - ((v - min) / range) * (height - 2 * padding);
          return (
            <g key={i}>
              <circle cx={x} cy={y} r={4} fill={color} stroke="#0B0E14" strokeWidth={1.5} />
              <text x={x} y={y - 8} fill="rgba(255,255,255,0.7)" fontSize="9" textAnchor="middle" fontWeight="bold">
                {v.toFixed(0)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

export default function AdvancedAnalyticsTab({ projectId, userId }: { projectId: string; userId: string }) {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [regressions, setRegressions] = useState<any[]>([]);
  const [rootCauses, setRootCauses] = useState<any[]>([]);
  const [heatmap, setHeatmap] = useState<any>(null);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [activeMetricTab, setActiveMetricTab] = useState("visibility_score");
  const [activeExplainTab, setActiveExplainTab] = useState("recommendation");

  const fetchData = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const headers = { "Content-Type": "application/json", ...authHeader(userId) };
      
      const [analyticsRes, regressionsRes, rootCausesRes, heatmapRes, opportunitiesRes] = await Promise.all([
        fetch(`${API_BASE}/analysis/analytics/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/regressions/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/root-causes/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/heatmap/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/opportunities/${projectId}`, { headers }),
      ]);

      if (!analyticsRes.ok) throw new Error("Failed to load analytics");

      setAnalytics(await analyticsRes.json());
      setRegressions(await regressionsRes.json());
      setRootCauses(await rootCausesRes.json());
      setHeatmap(await heatmapRes.json());
      setOpportunities(await opportunitiesRes.json());
    } catch (e: any) {
      console.error("Error loading Advanced Analytics", e);
      setError("Failed to retrieve diagnostics data. Make sure backend and Redis are running.");
    } finally {
      setLoading(false);
    }
  }, [projectId, userId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex-center" style={{ padding: "6rem 0" }}>
        <div className="spinner"></div>
        <p style={{ color: "var(--text-muted)", marginTop: "1rem" }}>Compiling diagnostics and explainability indices...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ borderLeft: "4px solid var(--accent-red)", padding: "2rem", textAlign: "center" }}>
        <p style={{ color: "HSL(0, 100%, 75%)", fontWeight: "bold", fontSize: "1.1rem" }}>⚠️ {error}</p>
        <button onClick={fetchData} className="btn btn-primary" style={{ marginTop: "1rem" }}>Retry Loading</button>
      </div>
    );
  }

  const runs = analytics?.trends?.runs || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2.5rem" }}>
      
      {/* HEADER SECTION */}
      <div>
        <h2 style={{ fontSize: "1.8rem", color: "var(--text-light)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span>📊</span> Explainable Diagnostics &amp; Analytics
        </h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.95rem" }}>
          Deconstruct recommendation changes, trace root cause regression maps, and explore semantic query coverages.
        </p>
      </div>

      {/* 1. HISTORICAL TRENDS SECTION */}
      <div className="card">
        <h3 style={{ marginBottom: "1rem", color: "var(--text-light)", fontSize: "1.2rem" }}>📈 Score Performance Trends</h3>
        <div className="grid-3" style={{ gap: "1rem", marginBottom: "1.5rem" }}>
          {METRICS_LIST.map((m) => {
            const currentVal = analytics?.trends?.trends?.[m.key]?.current ?? 0;
            const delta = analytics?.trends?.trends?.[m.key]?.weekly_delta ?? 0;
            const direction = analytics?.trends?.trends?.[m.key]?.weekly_direction || "stable";
            
            return (
              <div 
                key={m.key} 
                onClick={() => setActiveMetricTab(m.key)}
                style={{ 
                  background: "rgba(255,255,255,0.02)", 
                  border: `1px solid ${activeMetricTab === m.key ? m.color : "rgba(255,255,255,0.05)"}`, 
                  borderRadius: "16px", 
                  padding: "1.25rem", 
                  cursor: "pointer", 
                  transition: "all 0.2s ease" 
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: "bold" }}>{m.label}</span>
                  <span style={{ 
                    fontSize: "0.8rem", 
                    fontWeight: "bold",
                    color: direction === "improving" ? "var(--accent-green)" : direction === "declining" ? "var(--accent-red)" : "var(--text-muted)" 
                  }}>
                    {direction === "improving" ? "▲" : direction === "declining" ? "▼" : "•"} {delta > 0 ? "+" : ""}{delta}
                  </span>
                </div>
                <div style={{ fontSize: "2rem", fontWeight: "bold", color: "var(--text-light)", margin: "0.5rem 0" }}>
                  {currentVal.toFixed(0)}
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Metric Line Graph */}
        {runs.length > 0 && (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
              <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: METRICS_LIST.find(m => m.key === activeMetricTab)?.color }} />
              <span style={{ fontSize: "0.9rem", color: "var(--text-muted)", fontWeight: "bold" }}>
                {METRICS_LIST.find(m => m.key === activeMetricTab)?.label} Line Chart (Last {runs.length} runs)
              </span>
            </div>
            <ScoreSparkline runs={runs} metricKey={activeMetricTab} color={METRICS_LIST.find(m => m.key === activeMetricTab)?.color || "#fff"} />
          </div>
        )}
      </div>

      {/* 2. BEFORE VS AFTER CARDS */}
      {analytics?.before_after_cards && analytics.before_after_cards.length > 0 && (
        <div>
          <h3 style={{ marginBottom: "1rem", color: "var(--text-light)", fontSize: "1.2rem" }}>🔄 Before vs After Analysis Compare</h3>
          <div className="grid-3" style={{ gap: "1rem" }}>
            {analytics.before_after_cards.map((c, i) => (
              <div key={i} className="card" style={{ position: "relative", overflow: "hidden", padding: "1.25rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>{c.metric_name}</span>
                  <span className={`badge ${
                    c.status === "Improved" ? "badge-success" : c.status === "Regressed" ? "badge-danger" : "badge-info"
                  }`} style={{ fontSize: "0.75rem" }}>
                    {c.status}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem", margin: "0.75rem 0 0.25rem 0" }}>
                  <span style={{ fontSize: "1.8rem", fontWeight: "bold", color: "var(--text-light)" }}>{c.current_value}</span>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>from {c.previous_value}</span>
                </div>
                <div style={{ fontSize: "0.8rem", color: c.absolute_change >= 0 ? "var(--accent-green)" : "var(--accent-red)" }}>
                  {c.absolute_change >= 0 ? "+" : ""}{c.absolute_change} ({c.absolute_change >= 0 ? "+" : ""}{c.percentage_change}%)
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. REGRESSION ALERTS */}
      {regressions.length > 0 && (
        <div style={{ borderLeft: "4px solid var(--accent-red)", background: "rgba(255,59,48,0.03)", borderRadius: "0 16px 16px 0", padding: "1.5rem" }}>
          <h3 style={{ color: "var(--accent-red)", marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span>⚠️</span> Critical Regressions Detected
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {regressions.map((r, i) => (
              <div key={i} className="card" style={{ background: "rgba(11,14,20,0.6)", border: "1px solid rgba(255,59,48,0.15)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                  <h4 style={{ margin: 0, color: "var(--text-light)" }}>{r.metric_name} dropped by {r.drop_value} points</h4>
                  <span className="badge badge-danger" style={{ fontSize: "0.75rem" }}>{r.severity} Severity</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", fontSize: "0.85rem" }}>
                  <div>
                    <div style={{ color: "var(--text-muted)", fontWeight: "bold" }}>Reason</div>
                    <div style={{ color: "var(--text-light)", marginTop: "0.25rem" }}>{r.reason}</div>
                  </div>
                  <div>
                    <div style={{ color: "var(--text-muted)", fontWeight: "bold" }}>Recommended Fix</div>
                    <div style={{ color: "var(--accent-green)", marginTop: "0.25rem", fontWeight: "bold" }}>{r.recommended_fix}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. EXPLAINABILITY BREAKDOWNS */}
      {analytics?.explainability && (
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
            <h3 style={{ margin: 0, color: "var(--text-light)" }}>🔍 Score Explainability Breakdowns</h3>
            <div style={{ display: "flex", gap: "0.25rem", background: "rgba(255,255,255,0.05)", padding: "0.25rem", borderRadius: "10px" }}>
              {[
                { key: "recommendation", label: "Recommendation Breakdown" },
                { key: "visibility", label: "Visibility Breakdown" },
                { key: "coverage", label: "Coverage Breakdown" }
              ].map(t => (
                <button 
                  key={t.key}
                  onClick={() => setActiveExplainTab(t.key)}
                  className={`tab-btn ${activeExplainTab === t.key ? "active" : ""}`}
                  style={{ fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Breakdown cards grid */}
          {(() => {
            const exp = analytics.explainability;
            const dataObj = 
              activeExplainTab === "recommendation" ? exp.recommendation_breakdown :
              activeExplainTab === "visibility" ? exp.visibility_breakdown : exp.coverage_breakdown;
              
            if (!dataObj || !dataObj.components) return null;
            
            return (
              <div>
                <div style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", paddingBottom: "1rem", marginBottom: "1.5rem" }}>
                  <div style={{ display: "flex", alignItems: "baseline", gap: "1rem" }}>
                    <span style={{ fontSize: "2.4rem", fontWeight: "bold", color: "var(--text-light)" }}>{dataObj.overall.score}</span>
                    <span style={{ color: "var(--text-muted)" }}>/ {dataObj.overall.max} Overall</span>
                  </div>
                  <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "0.5rem" }}>
                    Reason: {dataObj.overall.reason} (Confidence Rating: {(dataObj.overall.confidence * 100).toFixed(0)}%)
                  </p>
                </div>
                
                <div className="grid-3" style={{ gap: "1rem" }}>
                  {dataObj.components.map((c: any, idx: number) => (
                    <div key={idx} style={{ padding: "1rem", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "14px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.5rem" }}>
                        <span style={{ fontWeight: "bold", fontSize: "0.9rem", color: "var(--text-light)" }}>{c.name}</span>
                        <span style={{ fontWeight: "bold", color: "var(--secondary)" }}>{c.value} / {c.max}</span>
                      </div>
                      <div style={{ width: "100%", height: "4px", background: "rgba(255,255,255,0.05)", borderRadius: "2px", overflow: "hidden", marginBottom: "0.75rem" }}>
                        <div style={{ width: `${(c.value / c.max) * 100}%`, height: "100%", background: "var(--secondary)" }} />
                      </div>
                      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{c.reason}</div>
                      {c.supporting_evidence && (
                        <div style={{ fontSize: "0.75rem", color: "var(--accent-green)", marginTop: "0.5rem", fontWeight: "500" }}>
                          ℹ️ {c.supporting_evidence}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* 5. ROOT CAUSE ENGINE REPORTS */}
      {rootCauses.length > 0 && (
        <div className="card">
          <h3 style={{ color: "var(--text-light)", marginBottom: "1.25rem", fontSize: "1.2rem" }}>🔍 Root Cause Diagnosis</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {rootCauses.map((rc, i) => (
              <div 
                key={i} 
                style={{ 
                  padding: "1.25rem", 
                  background: "rgba(255,255,255,0.02)", 
                  borderLeft: `4px solid ${
                    rc.severity === "HIGH" ? "var(--accent-red)" : rc.severity === "MEDIUM" ? "var(--accent-amber)" : "var(--primary)"
                  }`, 
                  borderRadius: "0 12px 12px 0" 
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                  <span style={{ fontSize: "0.9rem", fontWeight: "bold", color: "var(--text-light)" }}>
                    {rc.metric_name} Change: <span style={{ color: rc.score_change < 0 ? "var(--accent-red)" : "var(--accent-green)" }}>{rc.score_change} pts</span>
                  </span>
                  <span className="badge" style={{ 
                    fontSize: "0.75rem", 
                    background: rc.severity === "HIGH" ? "rgba(255,59,48,0.15)" : rc.severity === "MEDIUM" ? "rgba(245,158,11,0.15)" : "rgba(33,150,243,0.15)",
                    color: rc.severity === "HIGH" ? "var(--accent-red)" : rc.severity === "MEDIUM" ? "var(--accent-amber)" : "var(--primary)"
                  }}>
                    {rc.severity} Priority
                  </span>
                </div>
                
                <p style={{ color: "var(--text-light)", fontSize: "0.9rem", margin: "0.5rem 0" }}>
                  <strong>Cause:</strong> {rc.cause}
                </p>
                
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", fontSize: "0.8rem", marginTop: "0.75rem" }}>
                  <div>
                    <span style={{ color: "var(--text-muted)", fontWeight: "bold" }}>Affected Modules</span>
                    <ul style={{ paddingLeft: "1.25rem", margin: "0.25rem 0", color: "var(--text-muted)" }}>
                      {rc.affected_agents.map((a: string, idx: number) => <li key={idx}>{a}</li>)}
                    </ul>
                  </div>
                  <div>
                    <span style={{ color: "var(--text-muted)", fontWeight: "bold" }}>Repair Actions</span>
                    <ul style={{ paddingLeft: "1.25rem", margin: "0.25rem 0", color: "var(--accent-green)" }}>
                      {rc.repair_suggestions.map((s: string, idx: number) => <li key={idx} style={{ fontWeight: "500" }}>{s}</li>)}
                    </ul>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 6. COVERAGE HEATMAP GRID */}
      {heatmap && heatmap.category_scores && (
        <div className="card">
          <h3 style={{ color: "var(--text-light)", marginBottom: "0.5rem", fontSize: "1.2rem" }}>🎯 Query Intent Heatmap Matrix</h3>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
            Measures your content coverage rate across 20 distinct user intent categories. Weak coverage regions require priority content generation.
          </p>
          
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "0.75rem" }}>
            {Object.entries(heatmap.category_scores).map(([cat, score]: [string, any]) => {
              const scoreVal = float(score);
              const isWeak = scoreVal < 50.0;
              const isStrong = scoreVal >= 80.0;
              const priority = heatmap.priorities?.[cat] || "LOW";
              
              return (
                <div 
                  key={cat}
                  style={{ 
                    padding: "1rem", 
                    borderRadius: "12px", 
                    textAlign: "center", 
                    transition: "all 0.2s",
                    background: isWeak ? "rgba(255,59,48,0.04)" : isStrong ? "rgba(16,185,129,0.04)" : "rgba(255,255,255,0.02)",
                    border: `1px solid ${
                      isWeak ? "rgba(255,59,48,0.2)" : isStrong ? "rgba(16,185,129,0.2)" : "rgba(255,255,255,0.05)"
                    }`
                  }}
                >
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: "bold", marginBottom: "0.5rem" }}>{cat}</div>
                  <div style={{ fontSize: "1.6rem", fontWeight: "bold", color: isWeak ? "var(--accent-red)" : isStrong ? "var(--accent-green)" : "var(--text-light)" }}>
                    {scoreVal.toFixed(0)}%
                  </div>
                  {isWeak && (
                    <div style={{ fontSize: "0.7rem", color: "var(--accent-red)", fontWeight: "bold", marginTop: "0.25rem" }}>
                      ⚠️ {priority} Priority
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 7. OPPORTUNITIES V2 CARDS */}
      {opportunities.length > 0 && (
        <div>
          <h3 style={{ marginBottom: "1rem", color: "var(--text-light)", fontSize: "1.2rem" }}>💡 Dynamic V2 Opportunities Generator</h3>
          <div className="grid-3" style={{ gap: "1rem" }}>
            {opportunities.map((opp, i) => (
              <div 
                key={i} 
                className="card" 
                style={{ 
                  borderTop: `4px solid ${opp.priority === "HIGH" ? "var(--accent-red)" : "var(--accent-amber)"}`, 
                  display: "flex", 
                  flexDirection: "column", 
                  justifyContent: "space-between", 
                  padding: "1.25rem" 
                }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                    <span className="badge badge-info" style={{ fontSize: "0.7rem" }}>{opp.category} Category</span>
                    <span className={`badge ${opp.priority === "HIGH" ? "badge-danger" : "badge-warning"}`} style={{ fontSize: "0.7rem" }}>
                      {opp.priority} Priority
                    </span>
                  </div>
                  <h4 style={{ margin: "0 0 0.5rem 0", color: "var(--text-light)" }}>{opp.opportunity}</h4>
                  
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: "bold" }}>Recommended Actions:</span>
                  <ul style={{ margin: "0.25rem 0 1rem 0", paddingLeft: "1.25rem", fontSize: "0.8rem", color: "var(--text-light)" }}>
                    {opp.recommended_actions.map((act: string, idx: number) => <li key={idx}>{act}</li>)}
                  </ul>
                </div>
                
                <div style={{ display: "flex", justifyContent: "space-between", background: "rgba(255,255,255,0.02)", padding: "0.5rem", borderRadius: "8px", fontSize: "0.75rem" }}>
                  <span>Impact Score: <strong style={{ color: "var(--accent-green)" }}>{opp.impact_score}</strong></span>
                  <span>Effort Cost: <strong style={{ color: "var(--accent-amber)" }}>{opp.effort_score}</strong></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}

// Utility to parse floats safely
function float(val: any): number {
  const parsed = parseFloat(val);
  return isNaN(parsed) ? 0.0 : parsed;
}
