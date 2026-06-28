"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE, authHeader as buildAuthHeader } from "../lib/config";

interface OptimizationIntelligenceTabProps {
  projectId: string;
  userId: string;
}

export default function OptimizationIntelligenceTab({ projectId, userId }: OptimizationIntelligenceTabProps) {
  const [plans, setPlans] = useState<any[]>([]);
  const [projection, setProjection] = useState<any>(null);
  const [roiReports, setRoiReports] = useState<any[]>([]);
  const [roadmap, setRoadmap] = useState<any>(null);
  const [reasonings, setReasonings] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const authHeader = useCallback(() => buildAuthHeader(userId), [userId]);

  const fetchOptimizationData = useCallback(async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      const headers = authHeader();
      const [planRes, projRes, roiRes, roadRes, reasonRes] = await Promise.all([
        fetch(`${API_BASE}/analysis/optimization-plan/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/geo-projection/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/roi-report/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/strategy-roadmap/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/optimization-reasoning/${projectId}`, { headers })
      ]);

      if (!planRes.ok) throw new Error("Failed to load optimization roadmap data.");

      setPlans(await planRes.json());
      setProjection(await projRes.json());
      setRoiReports(await roiRes.json());
      const roadmapData = await roadRes.json();
      setRoadmap(roadmapData?.roadmap || null);
      setReasonings(await reasonRes.json());
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "Failed to load Strategy Roadmap.");
    } finally {
      setLoading(false);
    }
  }, [projectId, authHeader]);

  useEffect(() => {
    if (projectId) {
      fetchOptimizationData();
    }
  }, [projectId, fetchOptimizationData]);

  const handleAcceptOptimization = async (recommendation: string) => {
    setActionLoading(recommendation);
    try {
      const res = await fetch(`${API_BASE}/analysis/optimization-history/${projectId}`, {
        method: "POST",
        headers: {
          ...authHeader(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          recommendation,
          status: "executed"
        }),
      });

      if (!res.ok) throw new Error("Failed to execute optimization action.");
      
      const resData = await res.json();
      if (resData.status === "success" && resData.data) {
        setHistory(prev => [resData.data, ...prev]);
      }
      
      // Refresh strategic roadmap data after action
      await fetchOptimizationData();
    } catch (err: any) {
      alert(err.message || "Action failed");
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "4rem" }}>
        <div className="spinner"></div>
        <p style={{ marginTop: "1rem", color: "var(--text-muted)" }}>Running autonomous strategy and ROI simulations...</p>
      </div>
    );
  }

  const currentScore = projection?.current_geo_score ?? 50;
  const projectedScore = projection?.projected_geo_score ?? 50;
  const expectedGain = projection?.expected_gain ?? 0;
  const confidence = projection?.confidence ?? 80;

  // Filter Quick Wins: Low Effort (<= 45) and High/Medium Impact (>= 60)
  const quickWins = plans.filter(p => p.effort_score <= 45 && p.impact_score >= 60 && p.status === "pending");

  const getStatusColor = (st: string) => {
    if (st === "Excellent" || st === "Very High") return "#10b981"; // Emerald
    if (st === "Healthy" || st === "High") return "#3b82f6"; // Blue
    if (st === "Warning" || st === "Medium") return "#f59e0b"; // Amber
    return "#ef4444"; // Red
  };

  return (
    <div style={{ color: "var(--text-light)" }}>
      <h2>🤖 Autonomous Optimization & Strategy Roadmap</h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "2rem" }}>
        Simulate before-vs-after improvements, prioritize actions based on ROI, and execute Quick Wins to boost recommendation scores.
      </p>

      {errorMsg && (
        <div className="card" style={{ borderLeft: "4px solid var(--accent-red)", background: "rgba(239, 68, 68, 0.05)", marginBottom: "2rem" }}>
          <p style={{ color: "var(--accent-red)", margin: 0 }}>{errorMsg}</p>
        </div>
      )}

      {/* Grid: circular gain charts + expected stats */}
      <div className="grid-3" style={{ marginBottom: "2.5rem", gridTemplateColumns: "1.2fr 2fr", gap: "1.5rem" }}>
        {/* Before vs After Dial Comparison */}
        <div className="card" style={{ padding: "2rem", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center" }}>
          <h4 style={{ margin: "0 0 1rem 0", color: "var(--text-muted)", fontSize: "0.85rem" }}>SIMULATED GEO READINESS GAIN</h4>
          
          <div style={{ display: "flex", gap: "2rem", alignItems: "center", justifyContent: "center" }}>
            {/* Before circle */}
            <div style={{ position: "relative", width: "90px", height: "90px" }}>
              <svg width="100%" height="100%" viewBox="0 0 40 40" className="circular-chart">
                <path
                  className="circle-bg"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="rgba(255,255,255,0.06)"
                  strokeWidth="3.5"
                />
                <path
                  className="circle"
                  strokeDasharray={`${currentScore}, 100`}
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="var(--accent-amber)"
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  style={{ transition: "stroke-dasharray 1s ease" }}
                />
              </svg>
              <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", textAlign: "center" }}>
                <span style={{ fontSize: "1.2rem", fontWeight: "bold", color: "#fff" }}>{currentScore}%</span>
                <div style={{ fontSize: "0.55rem", color: "var(--text-muted)" }}>BEFORE</div>
              </div>
            </div>

            <div style={{ fontSize: "1.5rem", color: "var(--text-muted)" }}>➔</div>

            {/* After circle */}
            <div style={{ position: "relative", width: "90px", height: "90px" }}>
              <svg width="100%" height="100%" viewBox="0 0 40 40" className="circular-chart">
                <path
                  className="circle-bg"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="rgba(255,255,255,0.06)"
                  strokeWidth="3.5"
                />
                <path
                  className="circle"
                  strokeDasharray={`${projectedScore}, 100`}
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="var(--accent-green)"
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  style={{ transition: "stroke-dasharray 1s ease" }}
                />
              </svg>
              <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", textAlign: "center" }}>
                <span style={{ fontSize: "1.2rem", fontWeight: "bold", color: "#fff" }}>{projectedScore}%</span>
                <div style={{ fontSize: "0.55rem", color: "var(--text-muted)" }}>AFTER</div>
              </div>
            </div>
          </div>

          <div style={{ marginTop: "1rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
            Confidence Rating: <strong style={{ color: "var(--secondary)" }}>{confidence}%</strong>
          </div>
        </div>

        {/* Expected Gains and Stats card */}
        <div className="card" style={{ padding: "2rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", alignItems: "center" }}>
          <div>
            <h4 style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.85rem" }}>EXPECTED READINESS GAIN</h4>
            <div style={{ fontSize: "3rem", fontWeight: "bold", color: "var(--accent-green)", margin: "0.5rem 0" }}>
              +{expectedGain}%
            </div>
            <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", margin: 0 }}>
              Calculated simulation increase if all pending high-priority items are executed.
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div style={{ background: "rgba(255,255,255,0.02)", padding: "1rem", borderRadius: "6px" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>TOTAL ROADMAP STEPS</div>
              <strong style={{ fontSize: "1.2rem", color: "#fff" }}>{plans.length} Recommendations</strong>
            </div>
            <div style={{ background: "rgba(255,255,255,0.02)", padding: "1rem", borderRadius: "6px" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>COMPLETED / ACCEPTED</div>
              <strong style={{ fontSize: "1.2rem", color: "var(--secondary)" }}>
                {plans.filter(p => p.status !== "pending").length} Items
              </strong>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Wins Header Spotlight */}
      {quickWins.length > 0 && (
        <div className="card" style={{ marginBottom: "2.5rem", borderLeft: "4px solid var(--accent-green)", background: "rgba(16, 185, 129, 0.03)", padding: "1.5rem" }}>
          <h3 style={{ margin: "0 0 0.8rem 0", color: "#fff", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            ⚡ Recommended Quick Wins (Highest ROI)
          </h3>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.2rem" }}>
            High impact recommendations with minimal implementation effort. Accept them to capture immediate gains.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {quickWins.map((win, idx) => {
              const roi = roiReports.find(r => r.category === win.category);
              return (
                <div key={idx} style={{ background: "rgba(255,255,255,0.02)", padding: "1rem", borderRadius: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <span className="badge" style={{ backgroundColor: "rgba(16, 185, 129, 0.15)", color: "var(--accent-green)", fontWeight: "bold" }}>
                      {win.category.toUpperCase()}
                    </span>
                    <strong style={{ color: "#fff", marginLeft: "1rem" }}>{win.recommendation}</strong>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.3rem" }}>
                      Impact: {win.impact_score} | Effort: {win.effort_score} | ROI: <strong style={{ color: "var(--secondary)" }}>{roi ? roi.roi_score : 1.0}</strong>
                    </div>
                  </div>
                  <button
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: "0.8rem" }}
                    onClick={() => handleAcceptOptimization(win.recommendation)}
                    disabled={actionLoading === win.recommendation}
                  >
                    {actionLoading === win.recommendation ? "Executing..." : "Accept & Run"}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Chronological 30-60-90 Day Roadmap */}
      <div className="card" style={{ marginBottom: "2.5rem", padding: "1.8rem" }}>
        <h3 style={{ margin: "0 0 1.5rem 0" }}>📅 Strategic 30-60-90 Day Roadmap</h3>
        
        {roadmap ? (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1.5rem" }}>
            {/* 30 Days column */}
            <div style={{ background: "rgba(255,255,255,0.01)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: "8px", padding: "1.2rem" }}>
              <div style={{ borderBottom: "2px solid var(--accent-green)", paddingBottom: "0.5rem", marginBottom: "1rem" }}>
                <strong style={{ color: "#fff", fontSize: "0.95rem" }}>📅 30 Days (Quick Wins)</strong>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
                {roadmap["30_days"]?.milestones.length > 0 ? (
                  roadmap["30_days"].milestones.map((item: any, i: number) => (
                    <div key={i} style={{ padding: "0.8rem", background: "rgba(255,255,255,0.02)", borderRadius: "6px" }}>
                      <div style={{ fontSize: "0.75rem", color: "var(--accent-green)", fontWeight: "bold", textTransform: "uppercase" }}>
                        {item.category}
                      </div>
                      <div style={{ fontSize: "0.8rem", margin: "0.3rem 0", color: "var(--text-light)" }}>
                        {item.recommendation}
                      </div>
                      <span className="badge" style={{ fontSize: "0.65rem", background: item.status !== "pending" ? "rgba(16, 185, 129, 0.15)" : "rgba(255,255,255,0.04)" }}>
                        {item.status.toUpperCase()}
                      </span>
                    </div>
                  ))
                ) : (
                  <p style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>No milestones scheduled.</p>
                )}
              </div>
            </div>

            {/* 60 Days column */}
            <div style={{ background: "rgba(255,255,255,0.01)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: "8px", padding: "1.2rem" }}>
              <div style={{ borderBottom: "2px solid var(--secondary)", paddingBottom: "0.5rem", marginBottom: "1rem" }}>
                <strong style={{ color: "#fff", fontSize: "0.95rem" }}>📅 60 Days (Core Milestones)</strong>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
                {roadmap["60_days"]?.milestones.length > 0 ? (
                  roadmap["60_days"].milestones.map((item: any, i: number) => (
                    <div key={i} style={{ padding: "0.8rem", background: "rgba(255,255,255,0.02)", borderRadius: "6px" }}>
                      <div style={{ fontSize: "0.75rem", color: "var(--secondary)", fontWeight: "bold", textTransform: "uppercase" }}>
                        {item.category}
                      </div>
                      <div style={{ fontSize: "0.8rem", margin: "0.3rem 0", color: "var(--text-light)" }}>
                        {item.recommendation}
                      </div>
                      <span className="badge" style={{ fontSize: "0.65rem", background: item.status !== "pending" ? "rgba(16, 185, 129, 0.15)" : "rgba(255,255,255,0.04)" }}>
                        {item.status.toUpperCase()}
                      </span>
                    </div>
                  ))
                ) : (
                  <p style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>No milestones scheduled.</p>
                )}
              </div>
            </div>

            {/* 90 Days column */}
            <div style={{ background: "rgba(255,255,255,0.01)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: "8px", padding: "1.2rem" }}>
              <div style={{ borderBottom: "2px solid var(--accent-purple)", paddingBottom: "0.5rem", marginBottom: "1rem" }}>
                <strong style={{ color: "#fff", fontSize: "0.95rem" }}>📅 90 Days (Strategic Goals)</strong>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
                {roadmap["90_days"]?.milestones.length > 0 ? (
                  roadmap["90_days"].milestones.map((item: any, i: number) => (
                    <div key={i} style={{ padding: "0.8rem", background: "rgba(255,255,255,0.02)", borderRadius: "6px" }}>
                      <div style={{ fontSize: "0.75rem", color: "var(--accent-purple)", fontWeight: "bold", textTransform: "uppercase" }}>
                        {item.category}
                      </div>
                      <div style={{ fontSize: "0.8rem", margin: "0.3rem 0", color: "var(--text-light)" }}>
                        {item.recommendation}
                      </div>
                      <span className="badge" style={{ fontSize: "0.65rem", background: item.status !== "pending" ? "rgba(16, 185, 129, 0.15)" : "rgba(255,255,255,0.04)" }}>
                        {item.status.toUpperCase()}
                      </span>
                    </div>
                  ))
                ) : (
                  <p style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>No milestones scheduled.</p>
                )}
              </div>
            </div>
          </div>
        ) : (
          <p style={{ color: "var(--text-muted)" }}>Strategy roadmap not built.</p>
        )}
      </div>

      {/* Top Recommendations Table with ROI details */}
      <div className="card" style={{ marginBottom: "2.5rem", padding: "1.8rem" }}>
        <h3 style={{ margin: "0 0 1rem 0" }}>⚔️ Prioritized Strategy Recommendations</h3>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
          Interactive action plan mapping implementation priority weights and expected gains.
        </p>
        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Recommendation</th>
                <th>Priority</th>
                <th>Gain</th>
                <th>ROI</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {plans.length > 0 ? (
                plans.map((p, i) => {
                  const roi = roiReports.find(r => r.category === p.category);
                  const isPending = p.status === "pending";
                  return (
                    <tr key={i} style={{ opacity: isPending ? 1 : 0.6 }}>
                      <td><strong>{p.category}</strong></td>
                      <td style={{ fontSize: "0.85rem" }}>{p.recommendation}</td>
                      <td>
                        <span className="badge badge-info" style={{ fontWeight: "bold" }}>
                          {p.priority_score}
                        </span>
                      </td>
                      <td style={{ color: "var(--accent-green)", fontWeight: "bold" }}>
                        +{p.estimated_geo_gain}%
                      </td>
                      <td>
                        <span
                          className="badge"
                          style={{
                            backgroundColor: getStatusColor(roi?.roi_score >= 1.5 ? "High" : "Medium") + "20",
                            color: getStatusColor(roi?.roi_score >= 1.5 ? "High" : "Medium"),
                            border: `1px solid ${getStatusColor(roi?.roi_score >= 1.5 ? "High" : "Medium")}30`,
                            fontWeight: "bold",
                          }}
                        >
                          {roi ? roi.roi_score : 1.0} ROI
                        </span>
                      </td>
                      <td>
                        {isPending ? (
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ fontSize: "0.75rem" }}
                            onClick={() => handleAcceptOptimization(p.recommendation)}
                            disabled={actionLoading === p.recommendation}
                          >
                            {actionLoading === p.recommendation ? "..." : "Execute"}
                          </button>
                        ) : (
                          <span style={{ color: "var(--accent-green)", fontSize: "0.8rem", fontWeight: "bold" }}>✓ Accepted</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)" }}>No strategy recommendations cataloged.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recommendation Reasoning Cards */}
      <div style={{ marginBottom: "2.5rem" }}>
        <h3>💡 Strategic Optimization Reasoning</h3>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
          Explainability breakdown detailing targeted signals and simulated outcomes.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "1.2rem" }}>
          {reasonings.length > 0 ? (
            reasonings.map((rea, i) => (
              <div key={i} className="card" style={{ padding: "1.5rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.8rem" }}>
                  <strong style={{ color: "var(--secondary)", fontSize: "0.95rem" }}>
                    Category: {rea.category}
                  </strong>
                  <span className="badge badge-success" style={{ fontWeight: "bold" }}>
                    Priority Index: {rea.priority_score}
                  </span>
                </div>
                
                <p style={{ margin: "0.5rem 0", fontSize: "0.9rem", color: "#fff" }}>
                  <strong>Task:</strong> {rea.recommendation}
                </p>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginTop: "1rem" }}>
                  <div>
                    <h5 style={{ margin: "0 0 0.4rem 0", color: "var(--text-muted)", fontSize: "0.8rem" }}>WHY THIS MATTERS</h5>
                    <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)", lineHeight: "1.4" }}>
                      {rea.explanation}
                    </p>
                  </div>
                  <div>
                    <h5 style={{ margin: "0 0 0.4rem 0", color: "var(--text-muted)", fontSize: "0.8rem" }}>EXPECTED OUTCOME</h5>
                    <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--accent-green)", lineHeight: "1.4" }}>
                      ✓ {rea.expected_outcome}
                    </p>
                  </div>
                </div>

                <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", marginTop: "1rem", paddingTop: "0.8rem" }}>
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    Signals Influenced:{" "}
                    {rea.signals_involved.map((sig: string, idx: number) => (
                      <span key={idx} className="badge" style={{ marginLeft: "0.5rem", background: "rgba(255,255,255,0.05)" }}>
                        {sig}
                      </span>
                    ))}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <p style={{ color: "var(--text-muted)" }}>No strategic reasoning cards generated.</p>
          )}
        </div>
      </div>
    </div>
  );
}
