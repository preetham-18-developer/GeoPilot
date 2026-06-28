"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE, authHeader as buildAuthHeader } from "../lib/config";

interface AutonomousExecutionTabProps {
  projectId: string;
  userId: string;
}


export default function AutonomousExecutionTab({ projectId, userId }: AutonomousExecutionTabProps) {
  const [tasks, setTasks] = useState<any[]>([]);
  const [assets, setAssets] = useState<any[]>([]);
  const [results, setResults] = useState<any[]>([]);
  const [learning, setLearning] = useState<any[]>([]);

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [activePreviewAsset, setActivePreviewAsset] = useState<any>(null);

  const authHeader = useCallback(() => buildAuthHeader(userId), [userId]);

  const fetchExecutionData = useCallback(async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      const headers = authHeader();
      const [taskRes, assetRes, resultRes, learnRes] = await Promise.all([
        fetch(`${API_BASE}/execution/tasks/${projectId}`, { headers }),
        fetch(`${API_BASE}/generated-assets/${projectId}`, { headers }),
        fetch(`${API_BASE}/execution/results/${projectId}`, { headers }),
        fetch(`${API_BASE}/learning-memory/${projectId}`, { headers })
      ]);

      if (!taskRes.ok) throw new Error("Failed to load autonomous execution datasets.");

      setTasks(await taskRes.json());
      setAssets(await assetRes.json());
      setResults(await resultRes.json());
      setLearning(await learnRes.json());
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "Failed to sync autonomous data.");
    } finally {
      setLoading(false);
    }
  }, [projectId, authHeader]);

  useEffect(() => {
    if (projectId) {
      fetchExecutionData();
    }
  }, [projectId, fetchExecutionData]);

  const handleRunTask = async (taskId: string) => {
    setActionLoading(taskId);
    try {
      const res = await fetch(`${API_BASE}/execution/accept/${taskId}`, {
        method: "POST",
        headers: authHeader(),
      });
      if (!res.ok) throw new Error("Failed to start executing target task.");
      await fetchExecutionData();
    } catch (err: any) {
      alert(err.message || "Action failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleCompleteTask = async (taskId: string) => {
    setActionLoading(taskId);
    try {
      const res = await fetch(`${API_BASE}/execution/complete/${taskId}`, {
        method: "POST",
        headers: authHeader(),
      });
      if (!res.ok) throw new Error("Failed to complete and compute gains.");
      await fetchExecutionData();
    } catch (err: any) {
      alert(err.message || "Action failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleCopyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert("Asset content copied successfully to clipboard!");
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "4rem" }}>
        <div className="spinner"></div>
        <p style={{ marginTop: "1rem", color: "var(--text-muted)" }}>Connecting to autonomous GEO agent copilot...</p>
      </div>
    );
  }

  // Stats calculation
  const totalCompletedGains = results.reduce((sum, r) => sum + r.gain, 0);

  const getStatusBadgeStyles = (status: string) => {
    if (status === "completed") return { background: "rgba(16, 185, 129, 0.15)", color: "var(--accent-green)" };
    if (status === "running") return { background: "rgba(59, 130, 246, 0.15)", color: "var(--accent-blue)" };
    if (status === "failed") return { background: "rgba(239, 68, 68, 0.15)", color: "var(--accent-red)" };
    return { background: "rgba(255,255,255,0.05)", color: "var(--text-muted)" };
  };

  const getPriorityColor = (pr: string) => {
    if (pr === "CRITICAL" || pr === "HIGH") return "var(--accent-red)";
    if (pr === "MEDIUM") return "var(--accent-amber)";
    return "var(--accent-blue)";
  };

  return (
    <div style={{ color: "var(--text-light)" }}>
      <h2>🛡️ Autonomous GEO Execution & Asset Generator</h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "2rem" }}>
        Autonomously deploy landing pages, FAQs, JSON-LD schemas, and anchor links. Measure readiness gains and train the platform&apos;s execution memory.
      </p>

      {errorMsg && (
        <div className="card" style={{ borderLeft: "4px solid var(--accent-red)", background: "rgba(239, 68, 68, 0.05)", marginBottom: "2rem" }}>
          <p style={{ color: "var(--accent-red)", margin: 0 }}>{errorMsg}</p>
        </div>
      )}

      {/* Grid: before/after stats + memory trends */}
      <div className="grid-3" style={{ marginBottom: "2.5rem", gridTemplateColumns: "1fr 2fr", gap: "1.5rem" }}>
        {/* Performance Gains stats */}
        <div className="card" style={{ padding: "2rem", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <h4 style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.85rem" }}>TOTAL REALIZED GAIN</h4>
          <div style={{ fontSize: "3.2rem", fontWeight: "bold", color: "var(--accent-green)", margin: "0.5rem 0" }}>
            +{totalCompletedGains.toFixed(1)}%
          </div>
          <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", margin: 0 }}>
            Readiness increase accumulated through completed task optimizations.
          </p>
        </div>

        {/* Learning Memory panel */}
        <div className="card" style={{ padding: "1.8rem" }}>
          <h3 style={{ margin: "0 0 1rem 0" }}>🧠 Local Strategy Learning Memory</h3>
          <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", marginBottom: "1rem" }}>
            Success trends audit showing categories and average optimization scores verified in search engines.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            {learning.length > 0 ? (
              learning.map((l, i) => (
                <div key={i} style={{ background: "rgba(255,255,255,0.02)", padding: "0.8rem", borderRadius: "6px" }}>
                  <div style={{ fontWeight: "bold", fontSize: "0.85rem", color: "#fff" }}>Category: {l.category}</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.3rem" }}>
                    Avg Gain: <strong style={{ color: "var(--accent-green)" }}>+{l.average_gain}%</strong> | Success Rate: <strong style={{ color: "var(--secondary)" }}>{l.success_rate}%</strong>
                  </div>
                </div>
              ))
            ) : (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Learning memory is initializing. Complete tasks to compile patterns.</p>
            )}
          </div>
        </div>
      </div>

      {/* Grid: Tasks Queue vs Generated Assets */}
      <div className="grid-3" style={{ marginBottom: "2.5rem", gridTemplateColumns: "1.8fr 1.2fr", gap: "2rem" }}>
        {/* Task Queue list */}
        <div className="card" style={{ padding: "1.5rem" }}>
          <h3 style={{ margin: "0 0 1rem 0" }}>📋 Autonomous Task Queue</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", maxHeight: "400px", overflowY: "auto" }}>
            {tasks.length > 0 ? (
              tasks.map((task, i) => {
                const styles = getStatusBadgeStyles(task.status);
                const isPending = task.status === "pending";
                const isRunning = task.status === "running";
                return (
                  <div key={i} style={{ borderLeft: `3px solid ${getPriorityColor(task.priority)}`, paddingLeft: "0.8rem", background: "rgba(255,255,255,0.01)", padding: "0.8rem", borderRadius: "0 6px 6px 0" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ fontSize: "0.9rem", color: "#fff" }}>{task.title}</strong>
                      <span className="badge" style={{ ...styles, fontSize: "0.7rem", fontWeight: "bold" }}>
                        {task.status.toUpperCase()}
                      </span>
                    </div>
                    <p style={{ margin: "0.4rem 0", fontSize: "0.8rem", color: "var(--text-muted)", lineHeight: "1.3" }}>
                      {task.description}
                    </p>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.5rem" }}>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        Priority: <strong style={{ color: getPriorityColor(task.priority) }}>{task.priority}</strong> | Effort: {task.effort_score}
                      </span>
                      
                      {isPending && (
                        <button
                          className="button"
                          style={{ padding: "0.3rem 0.7rem", fontSize: "0.75rem" }}
                          onClick={() => handleRunTask(task.id)}
                          disabled={actionLoading !== null}
                        >
                          {actionLoading === task.id ? "Deploying..." : "Accept & Run"}
                        </button>
                      )}
                      
                      {isRunning && (
                        <button
                          className="button"
                          style={{ padding: "0.3rem 0.7rem", fontSize: "0.75rem", backgroundColor: "var(--accent-green)", borderColor: "var(--accent-green)", color: "#fff" }}
                          onClick={() => handleCompleteTask(task.id)}
                          disabled={actionLoading !== null}
                        >
                          {actionLoading === task.id ? "Measuring..." : "Verify & Complete"}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            ) : (
              <p style={{ color: "var(--text-muted)" }}>No tasks in the execution queue.</p>
            )}
          </div>
        </div>

        {/* Generated Assets list */}
        <div className="card" style={{ padding: "1.5rem" }}>
          <h3 style={{ margin: "0 0 1rem 0" }}>📦 Generated Copy & Schema Assets</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem", maxHeight: "400px", overflowY: "auto" }}>
            {assets.length > 0 ? (
              assets.map((asset, i) => (
                <div
                  key={i}
                  style={{
                    padding: "0.8rem",
                    background: "rgba(255,255,255,0.02)",
                    border: "1px solid rgba(255,255,255,0.04)",
                    borderRadius: "6px",
                    cursor: "pointer",
                    transition: "all 0.2s"
                  }}
                  onClick={() => setActivePreviewAsset(asset)}
                  onMouseEnter={(e) => e.currentTarget.style.borderColor = "var(--secondary)"}
                  onMouseLeave={(e) => e.currentTarget.style.borderColor = "rgba(255,255,255,0.04)"}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ fontSize: "0.85rem", color: "#fff", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap", maxWidth: "160px" }}>
                      {asset.title}
                    </strong>
                    <span className="badge badge-info" style={{ fontSize: "0.65rem", fontWeight: "bold" }}>
                      {asset.asset_type.toUpperCase()}
                    </span>
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.3rem" }}>
                    Created at: {new Date(asset.created_at).toLocaleTimeString()}
                  </div>
                </div>
              ))
            ) : (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Accept and run queue tasks to generate optimization copy assets.</p>
            )}
          </div>
        </div>
      </div>

      {/* Asset Preview Dialog/Overlay panel */}
      {activePreviewAsset && (
        <div className="card" style={{ border: "1px solid var(--secondary)", background: "rgba(255,255,255,0.02)", padding: "2rem", marginBottom: "2.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "0.8rem", marginBottom: "1rem" }}>
            <div>
              <h3 style={{ margin: 0, color: "#fff" }}>🔍 Asset Preview: {activePreviewAsset.title}</h3>
              <span className="badge" style={{ marginTop: "0.3rem", background: "var(--secondary)" }}>
                {activePreviewAsset.asset_type.toUpperCase()}
              </span>
            </div>
            <div style={{ display: "flex", gap: "1rem" }}>
              <button
                className="button btn-secondary"
                style={{ padding: "0.4rem 0.8rem", fontSize: "0.8rem" }}
                onClick={() => handleCopyToClipboard(
                  activePreviewAsset.asset_type === "schema" 
                    ? activePreviewAsset.content?.script_snippet 
                    : activePreviewAsset.content?.body_content || JSON.stringify(activePreviewAsset.content, null, 2)
                )}
              >
                Copy Content
              </button>
              <button
                className="button btn-secondary"
                style={{ padding: "0.4rem 0.8rem", fontSize: "0.8rem", background: "rgba(239, 68, 68, 0.2)", borderColor: "var(--accent-red)", color: "var(--accent-red)" }}
                onClick={() => setActivePreviewAsset(null)}
              >
                Close Preview
              </button>
            </div>
          </div>

          {/* Render content depending on asset type */}
          {activePreviewAsset.asset_type === "schema" ? (
            <div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                Add the following JSON-LD snippet in your landing page&apos;s <code>&lt;head&gt;</code> tags:
              </p>
              <pre style={{ background: "rgba(0,0,0,0.3)", padding: "1.2rem", borderRadius: "6px", overflowX: "auto", fontSize: "0.85rem", color: "var(--secondary)", border: "1px solid rgba(255,255,255,0.05)" }}>
                {activePreviewAsset.content?.script_snippet}
              </pre>
            </div>
          ) : activePreviewAsset.asset_type === "internal_link" ? (
            <div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1rem" }}>
                {activePreviewAsset.content?.summary}
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
                {activePreviewAsset.content?.link_placements?.map((lp: any, idx: number) => (
                  <div key={idx} style={{ background: "rgba(0,0,0,0.15)", padding: "0.8rem", borderRadius: "6px" }}>
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      Source Page: <a href={lp.source_page} target="_blank" rel="noreferrer" style={{ color: "var(--secondary)" }}>{lp.source_page}</a> ➔ Target Page: <a href={lp.target_page} target="_blank" rel="noreferrer" style={{ color: "var(--secondary)" }}>{lp.target_page}</a>
                    </div>
                    <div style={{ fontSize: "0.85rem", color: "#fff", marginTop: "0.3rem" }}>
                      <strong>Anchor text:</strong> <code style={{ color: "var(--accent-amber)" }}>{lp.anchor_text}</code>
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontStyle: "italic", marginTop: "0.2rem" }}>
                      Context: {lp.placement_context}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ background: "rgba(0,0,0,0.15)", padding: "1.5rem", borderRadius: "6px", maxHeight: "300px", overflowY: "auto", fontSize: "0.9rem", lineHeight: "1.5", color: "var(--text-light)", whiteSpace: "pre-wrap" }}>
              {activePreviewAsset.content?.body_content}
            </div>
          )}
        </div>
      )}

      {/* Progress Timeline status */}
      <div className="card" style={{ padding: "1.8rem" }}>
        <h3 style={{ margin: "0 0 1.5rem 0" }}>📍 Autonomous Execution Progress Timeline</h3>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", position: "relative", padding: "0 1rem" }}>
          <div style={{ position: "absolute", left: "2.5%", right: "2.5%", height: "2px", backgroundColor: "rgba(255,255,255,0.06)", top: "50%", zIndex: 1 }} />
          
          {[
            { step: "Accepted", desc: "Select audit fix" },
            { step: "Running", desc: "Generate copies & tags" },
            { step: "Completed", desc: "Assets ready to export" },
            { step: "Measured", desc: "Track score gains" },
            { step: "Learned", desc: "Train memory trends" }
          ].map((s, idx) => {
            const isDone = (idx === 0 && tasks.some(t => t.status !== "pending")) || 
                           (idx === 1 && tasks.some(t => t.status === "running")) || 
                           (idx === 2 && assets.length > 0) || 
                           (idx === 3 && results.length > 0) || 
                           (idx === 4 && learning.length > 0);
            return (
              <div key={idx} style={{ display: "flex", flexDirection: "column", alignItems: "center", zIndex: 2, position: "relative" }}>
                <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: isDone ? "var(--accent-green)" : "rgba(255,255,255,0.1)", display: "flex", alignItems: "center", justifyContent: "center", border: `2px solid ${isDone ? "var(--accent-green)" : "rgba(255,255,255,0.2)"}`, transition: "all 0.3s" }}>
                  {isDone && <span style={{ color: "#fff", fontSize: "0.75rem", fontWeight: "bold" }}>✓</span>}
                </div>
                <strong style={{ fontSize: "0.85rem", marginTop: "0.5rem", color: isDone ? "#fff" : "var(--text-muted)" }}>{s.step}</strong>
                <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", textAlign: "center", width: "90px", marginTop: "0.2rem" }}>{s.desc}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
