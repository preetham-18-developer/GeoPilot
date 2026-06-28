"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE, authHeader as buildAuthHeader } from "../lib/config";

interface ReliabilityDashboardProps {
  projectId: string;
  userId: string;
}

export default function ReliabilityDashboard({ projectId, userId }: ReliabilityDashboardProps) {
  const [report, setReport] = useState<any>(null);
  const [agentHealth, setAgentHealth] = useState<any[]>([]);
  const [recoveryHistory, setRecoveryHistory] = useState<any[]>([]);
  const [dependencies, setDependencies] = useState<any[]>([]);
  const [errors, setErrors] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [checkpoints, setCheckpoints] = useState<any[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [resuming, setResuming] = useState(false);
  const [refreshingDeps, setRefreshingDeps] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const authHeader = useCallback(() => buildAuthHeader(userId), [userId]);

  const fetchReliabilityData = useCallback(async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      // 1. Fetch overall report & latest run health
      const relRes = await fetch(`${API_BASE}/analysis/reliability/${projectId}`, {
        headers: authHeader(),
      });
      if (!relRes.ok) throw new Error("Failed to load reliability report");
      const relData = await relRes.ok ? await relRes.json() : {};
      
      setReport(relData.reliability_report || null);
      setAgentHealth(relData.agent_health_logs || []);
      setRecoveryHistory(relData.recovery_history || []);

      // Get latest run ID from logs if available
      const latestRunId = relData.agent_health_logs?.[0]?.run_id || relData.recovery_history?.[0]?.run_id;

      // 2. Fetch dependencies
      const depRes = await fetch(`${API_BASE}/analysis/dependencies`, {
        headers: authHeader(),
      });
      if (depRes.ok) {
        const depData = await depRes.json();
        setDependencies(depData);
      }

      // 3. Fetch error logs
      const errRes = await fetch(`${API_BASE}/analysis/errors/${projectId}`, {
        headers: authHeader(),
      });
      if (errRes.ok) {
        const errData = await errRes.json();
        setErrors(errData);
      }

      // 4. Fetch timeline & checkpoints if we have a run ID
      if (latestRunId) {
        const [timeRes, checkRes] = await Promise.all([
          fetch(`${API_BASE}/analysis/timeline/${latestRunId}`, { headers: authHeader() }),
          fetch(`${API_BASE}/analysis/checkpoints/${latestRunId}`, { headers: authHeader() })
        ]);
        if (timeRes.ok) setTimeline(await timeRes.json());
        if (checkRes.ok) setCheckpoints(await checkRes.json());
      } else {
        setTimeline([]);
        setCheckpoints([]);
      }

    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "Failed to retrieve reliability logs.");
    } finally {
      setLoading(false);
    }
  }, [projectId, authHeader]);

  useEffect(() => {
    if (projectId) {
      fetchReliabilityData();
    }
  }, [projectId, fetchReliabilityData]);

  const handleRefreshDependencies = async () => {
    setRefreshingDeps(true);
    try {
      const res = await fetch(`${API_BASE}/analysis/dependencies`, {
        headers: authHeader(),
      });
      if (res.ok) {
        setDependencies(await res.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setRefreshingDeps(false);
    }
  };

  const handleResumeRun = async () => {
    const latestRunId = agentHealth?.[0]?.run_id || checkpoints?.[0]?.run_id;
    if (!latestRunId) return;
    
    setResuming(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API_BASE}/analysis/resume/${latestRunId}`, {
        method: "POST",
        headers: authHeader(),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to trigger run resume");
      }
      // Wait a moment then refresh
      setTimeout(() => {
        fetchReliabilityData();
        setResuming(false);
      }, 2000);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to resume pipeline.");
      setResuming(false);
    }
  };

  // Node execution order for mapping timeline status
  const nodeSequence = [
    { key: "fact_extractor", label: "Fact Extractor" },
    { key: "verifier", label: "Verifier" },
    { key: "business_intelligence_agent", label: "BI Agent" },
    { key: "entity_graph", label: "Entity Graph" },
    { key: "question_discovery", label: "Question Discovery" },
    { key: "keyword_intelligence", label: "Keyword Agent" },
    { key: "competitor_discovery", label: "Competitor Agent" },
    { key: "content_coverage_eval", label: "Coverage Monitor" },
    { key: "visibility_scoring", label: "Visibility Scorer" },
    { key: "content_agent", label: "Content Optimization" },
    { key: "recommendation_sim", label: "Rec Simulator" },
    { key: "report_compiler", label: "Report Compiler" },
    { key: "qa_agent", label: "QA Evaluator" }
  ];

  const getScoreColor = (score: number) => {
    if (score >= 90) return "#10b981"; // Emerald
    if (score >= 75) return "#3b82f6"; // Blue
    if (score >= 60) return "#f59e0b"; // Amber
    return "#ef4444"; // Red
  };

  const getScoreRating = (score: number) => {
    if (score >= 90) return "EXCELLENT";
    if (score >= 75) return "HEALTHY";
    if (score >= 60) return "WARNING";
    return "CRITICAL";
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "4rem" }}>
        <div className="spinner"></div>
        <p style={{ marginTop: "1rem", color: "var(--text-muted)" }}>Analyzing platform reliability telemetry...</p>
      </div>
    );
  }

  const score = report?.reliability_score ?? 100.0;
  const rating = getScoreRating(score);
  const scoreColor = getScoreColor(score);

  // Check if latest run failed to offer resume button
  const isLastRunFailed = checkpoints.some(c => c.status === "failed") || 
                          agentHealth.some(h => !h.success);

  return (
    <div style={{ color: "var(--text-light)" }}>
      <h2>🛡️ Reliability & Self-Healing Center</h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "2rem" }}>
        Observe pipeline progress checkpoints, classification errors, service health dependencies, and automated recovery actions.
      </p>

      {errorMsg && (
        <div className="card" style={{ borderLeft: "4px solid var(--accent-red)", background: "rgba(239, 68, 68, 0.05)", marginBottom: "2rem" }}>
          <p style={{ color: "var(--accent-red)", margin: 0 }}>{errorMsg}</p>
        </div>
      )}

      {/* Grid: Score Widget + Summary Metrics */}
      <div className="grid-3" style={{ marginBottom: "2.5rem", gridTemplateColumns: "1fr 2fr" }}>
        {/* Score widget */}
        <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "2rem" }}>
          <h4 style={{ margin: "0 0 1rem 0", color: "var(--text-muted)" }}>RELIABILITY INDEX</h4>
          <div style={{ position: "relative", width: "130px", height: "130px" }}>
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
                strokeDasharray={`${score}, 100`}
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke={scoreColor}
                strokeWidth="3.5"
                strokeLinecap="round"
                style={{ transition: "stroke-dasharray 1s ease" }}
              />
            </svg>
            <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", textAlign: "center" }}>
              <span style={{ fontSize: "2rem", fontWeight: "bold", color: "#fff" }}>{score}%</span>
            </div>
          </div>
          <span className="badge" style={{ marginTop: "1rem", backgroundColor: scoreColor + "20", color: scoreColor, border: `1px solid ${scoreColor}30`, fontWeight: "bold", letterSpacing: "1px" }}>
            {rating}
          </span>
        </div>

        {/* Detailed Metrics Panel */}
        <div className="card" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", padding: "2rem" }}>
          <div>
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "0.25rem" }}>Agent Success Rate</div>
            <div style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#fff" }}>{report?.success_rate ?? 100}%</div>
            <div style={{ height: "6px", backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "3px", marginTop: "0.5rem", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${report?.success_rate ?? 100}%`, backgroundColor: "var(--accent-green)" }} />
            </div>
          </div>
          
          <div>
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "0.25rem" }}>Service Uptime Index</div>
            <div style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#fff" }}>{report?.dependency_score ?? 100}%</div>
            <div style={{ height: "6px", backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "3px", marginTop: "0.5rem", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${report?.dependency_score ?? 100}%`, backgroundColor: "var(--secondary)" }} />
            </div>
          </div>

          <div>
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "0.25rem" }}>Recovery Success Rate</div>
            <div style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#fff" }}>{report?.recovery_success_rate ?? 100}%</div>
            <div style={{ height: "6px", backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "3px", marginTop: "0.5rem", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${report?.recovery_success_rate ?? 100}%`, backgroundColor: "var(--primary)" }} />
            </div>
          </div>

          <div>
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "0.25rem" }}>Pipeline Completion stability</div>
            <div style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#fff" }}>{report?.pipeline_completion_score ?? 100}%</div>
            <div style={{ height: "6px", backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "3px", marginTop: "0.5rem", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${report?.pipeline_completion_score ?? 100}%`, backgroundColor: "var(--accent-amber)" }} />
            </div>
          </div>
        </div>
      </div>

      {/* Dependency Health Section */}
      <div style={{ marginBottom: "2.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.2rem" }}>
          <h3 style={{ margin: 0 }}>🔌 Service Dependency Health</h3>
          <button className="btn btn-secondary" style={{ padding: "0.35rem 0.75rem", fontSize: "0.85rem" }} onClick={handleRefreshDependencies} disabled={refreshingDeps}>
            {refreshingDeps ? "Testing Pings..." : "Trigger Health Check"}
          </button>
        </div>
        <div className="grid-3" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "1rem" }}>
          {dependencies.map((dep, index) => {
            const isHealthy = dep.status === "HEALTHY";
            const isDegraded = dep.status === "DEGRADED";
            const borderCol = isHealthy ? "rgba(16, 185, 129, 0.25)" : isDegraded ? "rgba(245, 158, 11, 0.25)" : "rgba(239, 68, 68, 0.25)";
            const glowCol = isHealthy ? "rgba(16, 185, 129, 0.05)" : isDegraded ? "rgba(245, 158, 11, 0.05)" : "rgba(239, 68, 68, 0.05)";
            const textCol = isHealthy ? "var(--accent-green)" : isDegraded ? "var(--accent-amber)" : "var(--accent-red)";
            return (
              <div key={index} className="card" style={{ padding: "1.2rem", border: `1px solid ${borderCol}`, background: glowCol, display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontWeight: "bold", color: "#fff" }}>{dep.service_name}</span>
                  <span style={{ fontSize: "0.75rem", padding: "0.1rem 0.4rem", borderRadius: "4px", background: borderCol, color: textCol, fontWeight: "bold" }}>
                    {dep.status}
                  </span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: "0.5rem" }}>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>Latency</span>
                  <span style={{ color: "#fff", fontSize: "0.85rem", fontWeight: "bold" }}>{dep.latency_ms} ms</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>Uptime</span>
                  <span style={{ color: "#fff", fontSize: "0.85rem", fontWeight: "bold" }}>{dep.uptime_percentage}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Pipeline Timelines / Checkpoints Tracker */}
      <div className="card" style={{ marginBottom: "2.5rem", padding: "1.8rem" }}>
        <h3 style={{ margin: "0 0 1.2rem 0" }}>📍 Checkpoints Execution Trace</h3>
        
        {/* Horizontal Timeline Track */}
        <div style={{ display: "flex", overflowX: "auto", padding: "1.5rem 0.5rem", gap: "1rem", whiteSpace: "nowrap", borderBottom: "1px solid rgba(255,255,255,0.06)", marginBottom: "1.5rem" }}>
          {nodeSequence.map((node, idx) => {
            const check = checkpoints.find(c => c.node_name === node.key);
            const status = check ? check.status : "pending"; // completed, failed, running
            
            let color = "rgba(255,255,255,0.15)";
            let glow = "none";
            let anim = "none";
            if (status === "completed") {
              color = "var(--accent-green)";
            } else if (status === "failed") {
              color = "var(--accent-red)";
              glow = "0 0 10px rgba(239, 68, 68, 0.4)";
            } else if (status === "running") {
              color = "var(--secondary)";
              glow = "0 0 12px rgba(59, 130, 246, 0.6)";
              anim = "pulse 1.5s infinite alternate";
            }
            
            return (
              <div key={idx} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <div style={{ width: "16px", height: "16px", borderRadius: "50%", backgroundColor: color, boxShadow: glow, animation: anim }} />
                  <span style={{ fontSize: "0.75rem", color: status !== "pending" ? "#fff" : "var(--text-muted)", marginTop: "0.4rem", fontWeight: status !== "pending" ? "bold" : "normal" }}>
                    {node.label}
                  </span>
                  <span style={{ fontSize: "0.65rem", color: "var(--text-muted)" }}>
                    {check && check.completed_at ? `${Math.round((new Date(check.completed_at).getTime() - new Date(check.started_at).getTime()) / 1000)}s` : check ? check.status : "pending"}
                  </span>
                </div>
                {idx < nodeSequence.length - 1 && (
                  <div style={{ width: "30px", height: "2px", backgroundColor: status === "completed" ? "var(--accent-green)" : "rgba(255,255,255,0.06)", marginTop: "-18px" }} />
                )}
              </div>
            );
          })}
        </div>

        {/* Resuming / Healing trigger Center */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h4 style={{ margin: "0 0 0.2rem 0" }}>Pipeline Recovery Center</h4>
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.85rem" }}>
              {isLastRunFailed 
                ? "The previous pipeline failed. Click Resume to run only remaining steps, avoiding Gemini/crawler API re-runs." 
                : "No recovery action required. Pipeline has run to completion."}
            </p>
          </div>
          {isLastRunFailed && (
            <button className="btn btn-primary" style={{ padding: "0.6rem 1.5rem", fontWeight: "bold", background: "linear-gradient(135deg, var(--secondary), var(--primary))", boxShadow: "0 4px 15px rgba(59, 130, 246, 0.3)" }} onClick={handleResumeRun} disabled={resuming}>
              {resuming ? "Healing & Resuming..." : "Resume Run Checkpoints"}
            </button>
          )}
        </div>
      </div>

      {/* Error Diagnostics Feed */}
      <div style={{ marginBottom: "2.5rem" }}>
        <h3>🚨 Error Diagnostics & Classifications</h3>
        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Agent Node</th>
                <th>Classification</th>
                <th>Severity</th>
                <th>Root Cause Analysis</th>
                <th>Automated Repair Action</th>
                <th>Traceback Preview</th>
                <th>Time Logged</th>
              </tr>
            </thead>
            <tbody>
              {errors.length > 0 ? (
                errors.map((err, i) => {
                  const isCritical = err.severity === "CRITICAL" || err.severity === "HIGH";
                  return (
                    <tr key={i}>
                      <td><strong>{err.agent_name}</strong></td>
                      <td><span className="badge badge-info">{err.error_type}</span></td>
                      <td>
                        <span className={`badge ${isCritical ? "badge-danger" : "badge-warning"}`}>
                          {err.severity}
                        </span>
                      </td>
                      <td style={{ color: "var(--text-light)", fontSize: "0.85rem" }}>{err.root_cause}</td>
                      <td style={{ color: "var(--accent-green)", fontSize: "0.85rem", fontWeight: "bold" }}>{err.recovery_action}</td>
                      <td>
                        <details>
                          <summary style={{ color: "var(--secondary)", cursor: "pointer", fontSize: "0.8rem" }}>View details</summary>
                          <pre style={{ margin: "0.5rem 0 0 0", padding: "0.5rem", fontSize: "0.7rem", backgroundColor: "rgba(0,0,0,0.2)", color: "var(--accent-red)", overflowX: "auto" }}>
                            {err.traceback}
                          </pre>
                        </details>
                      </td>
                      <td style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                        {new Date(err.timestamp).toLocaleString()}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", color: "var(--accent-green)", fontWeight: "bold", padding: "2rem" }}>
                    ✓ Clean Execution Diagnostics. No agent exceptions recorded.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recovery History Logs */}
      <div>
        <h3>📈 Self-Healing Recovery Logs</h3>
        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Recovery Session</th>
                <th>Interrupted node</th>
                <th>Resumed Target Node</th>
                <th>Recovery Status</th>
                <th>Attempts</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {recoveryHistory.length > 0 ? (
                recoveryHistory.map((rec, i) => (
                  <tr key={i}>
                    <td><span style={{ fontFamily: "monospace", fontSize: "0.8rem" }}>{rec.run_id}</span></td>
                    <td><span className="badge badge-danger">{rec.failed_node}</span></td>
                    <td><span className="badge badge-success">{rec.resumed_node}</span></td>
                    <td>
                      <span className={`badge ${rec.success ? "badge-success" : "badge-danger"}`}>
                        {rec.success ? "HEALED" : "FAILED"}
                      </span>
                    </td>
                    <td>{rec.retry_count}</td>
                    <td style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                      {new Date(rec.timestamp).toLocaleString()}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", color: "var(--text-dark)", padding: "2rem" }}>
                    No recovery operations have run yet. Run resumes are initiated on pipeline failures.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      
    </div>
  );
}
