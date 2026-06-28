"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE, authHeader as buildAuthHeader } from "../lib/config";
import { motion } from "framer-motion";

interface GEOIntelligenceTabProps {
  projectId: string;
  userId: string;
}

export default function GEOIntelligenceTab({ projectId, userId }: GEOIntelligenceTabProps) {
  const [geoReadiness, setGeoReadiness] = useState<any>(null);
  const [citations, setCitations] = useState<any[]>([]);
  const [authorities, setAuthorities] = useState<any[]>([]);
  const [gaps, setGaps] = useState<any[]>([]);
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [reasonings, setReasonings] = useState<any[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  const authHeader = useCallback(() => buildAuthHeader(userId), [userId]);

  const fetchGEOData = useCallback(async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      const headers = authHeader();
      const [geoRes, citRes, autRes, gapRes, comRes, reaRes] = await Promise.all([
        fetch(`${API_BASE}/analysis/geo-readiness/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/citation-report/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/authority-sources-v2/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/recommendation-gaps/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/competitor-recommendations/${projectId}`, { headers }),
        fetch(`${API_BASE}/analysis/citation-reasoning/${projectId}`, { headers })
      ]);

      if (!geoRes.ok) throw new Error("Failed to load GEO Intelligence records.");

      setGeoReadiness(await geoRes.json());
      setCitations(await citRes.json());
      setAuthorities(await autRes.json());
      setGaps(await gapRes.json());
      setCompetitors(await comRes.json());
      setReasonings(await reaRes.json());
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "Failed to load GEO Intelligence.");
    } finally {
      setLoading(false);
    }
  }, [projectId, authHeader]);

  useEffect(() => {
    if (projectId) {
      fetchGEOData();
    }
  }, [projectId, fetchGEOData]);

  if (loading) {
    return (
      <div className="space-y-6" aria-busy="true">
        <div>
          <div className="skeleton skeleton-title" style={{ width: "300px" }} />
          <div className="skeleton skeleton-text mt-2" style={{ width: "500px" }} />
        </div>
        <div className="grid-3" style={{ gridTemplateColumns: "1fr 2fr", gap: "1.25rem" }}>
          <div className="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col items-center justify-center space-y-4">
            <div className="skeleton skeleton-text" style={{ width: "50%" }} />
            <div className="skeleton" style={{ width: "100px", height: "100px", borderRadius: "50%" }} />
            <div className="skeleton skeleton-text" style={{ width: "30%" }} />
          </div>
          <div className="bg-white/5 border border-white/10 rounded-2xl p-5 grid grid-cols-2 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="skeleton skeleton-text" style={{ width: "60%" }} />
                <div className="skeleton" style={{ height: "6px", width: "100%", borderRadius: "3px" }} />
              </div>
            ))}
          </div>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5 space-y-3">
          <div className="skeleton skeleton-title" style={{ width: "20%" }} />
          <div className="skeleton skeleton-text" style={{ width: "80%" }} />
          <div className="space-y-2 pt-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex gap-4 items-center">
                <div className="skeleton skeleton-text" style={{ flex: 1 }} />
                <div className="skeleton skeleton-text" style={{ width: "200px" }} />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const score = geoReadiness?.geo_readiness_score ?? 0;
  const status = geoReadiness?.status ?? "Warning";
  const breakdown = geoReadiness?.breakdown ?? {};

  const getStatusColor = (st: string) => {
    if (st === "Excellent") return "#10b981"; // Emerald
    if (st === "Healthy") return "#3b82f6"; // Blue
    if (st === "Warning") return "#f59e0b"; // Amber
    return "#ef4444"; // Red
  };

  const statusColor = getStatusColor(status);

  // Group recommendation gaps by severity
  const severityOrder = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
  const sortedGaps = [...gaps].sort((a, b) => {
    return severityOrder.indexOf(a.severity) - severityOrder.indexOf(b.severity);
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      style={{ color: "var(--text-light)" }}
      className="space-y-8"
    >
      <h2>🎯 Generative Engine Optimization (GEO) Intelligence</h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "2rem" }}>
        Optimize citation probability and recommendation likelihood across ChatGPT, Gemini, Perplexity, and Claude search agents.
      </p>

      {errorMsg && (
        <div className="card" style={{ borderLeft: "4px solid var(--accent-red)", background: "rgba(239, 68, 68, 0.05)", marginBottom: "2rem" }}>
          <p style={{ color: "var(--accent-red)", margin: 0 }}>{errorMsg}</p>
        </div>
      )}

      {/* Grid: circular score + compliance breakdown */}
      <div className="grid-3" style={{ marginBottom: "2.5rem", gridTemplateColumns: "1fr 2fr" }}>
        {/* Circle dial */}
        <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "2rem", textAlign: "center" }}>
          <h4 style={{ margin: "0 0 1rem 0", color: "var(--text-muted)", fontSize: "0.85rem" }}>GEO READINESS INDEX</h4>
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
                stroke={statusColor}
                strokeWidth="3.5"
                strokeLinecap="round"
                style={{ transition: "stroke-dasharray 1s ease" }}
              />
            </svg>
            <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", textAlign: "center" }}>
              <span style={{ fontSize: "2rem", fontWeight: "bold", color: "#fff" }}>{score}%</span>
            </div>
          </div>
          <span className="badge" style={{ marginTop: "1rem", backgroundColor: statusColor + "20", color: statusColor, border: `1px solid ${statusColor}30`, fontWeight: "bold" }}>
            {status.toUpperCase()}
          </span>
        </div>

        {/* Breakdown bar columns */}
        <div className="card" style={{ padding: "2rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", color: "var(--text-muted)" }}>
              <span>Evidence Density</span>
              <span style={{ color: "#fff", fontWeight: "bold" }}>{breakdown.evidence_density}%</span>
            </div>
            <div style={{ height: "6px", backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "3px", marginTop: "0.4rem", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${breakdown.evidence_density}%`, backgroundColor: "var(--accent-green)" }} />
            </div>
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", color: "var(--text-muted)" }}>
              <span>Authority Strength</span>
              <span style={{ color: "#fff", fontWeight: "bold" }}>{breakdown.authority_strength}%</span>
            </div>
            <div style={{ height: "6px", backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "3px", marginTop: "0.4rem", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${breakdown.authority_strength}%`, backgroundColor: "var(--secondary)" }} />
            </div>
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", color: "var(--text-muted)" }}>
              <span>Question Discovery</span>
              <span style={{ color: "#fff", fontWeight: "bold" }}>{breakdown.question_coverage}%</span>
            </div>
            <div style={{ height: "6px", backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "3px", marginTop: "0.4rem", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${breakdown.question_coverage}%`, backgroundColor: "var(--primary)" }} />
            </div>
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", color: "var(--text-muted)" }}>
              <span>Keyword Intelligence</span>
              <span style={{ color: "#fff", fontWeight: "bold" }}>{breakdown.keyword_intelligence}%</span>
            </div>
            <div style={{ height: "6px", backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "3px", marginTop: "0.4rem", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${breakdown.keyword_intelligence}%`, backgroundColor: "var(--accent-amber)" }} />
            </div>
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", color: "var(--text-muted)" }}>
              <span>Trust Compliance</span>
              <span style={{ color: "#fff", fontWeight: "bold" }}>{breakdown.trust_compliance}%</span>
            </div>
            <div style={{ height: "6px", backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "3px", marginTop: "0.4rem", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${breakdown.trust_compliance}%`, backgroundColor: "var(--accent-blue)" }} />
            </div>
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", color: "var(--text-muted)" }}>
              <span>Structured Data Markup</span>
              <span style={{ color: "#fff", fontWeight: "bold" }}>{breakdown.structured_data}%</span>
            </div>
            <div style={{ height: "6px", backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "3px", marginTop: "0.4rem", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${breakdown.structured_data}%`, backgroundColor: "var(--accent-purple)" }} />
            </div>
          </div>
        </div>
      </div>

      {/* Pages Citation Probability */}
      <div className="card" style={{ marginBottom: "2.5rem", padding: "1.8rem" }}>
        <h3 style={{ margin: "0 0 1rem 0" }}>🔗 Top Pages Citation Probability</h3>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
          Likelihood of search engines referencing and citing individual pages in AI answers.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {citations.length > 0 ? (
            citations.map((cit, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1.5rem" }}>
                <div style={{ flex: 1, textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
                  <a href={cit.page_url} target="_blank" rel="noreferrer" style={{ color: "var(--secondary)", fontSize: "0.9rem" }}>
                    {cit.page_url}
                  </a>
                </div>
                <div style={{ width: "200px", display: "flex", alignItems: "center", gap: "0.8rem" }}>
                  <div style={{ flex: 1, height: "8px", backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "4px", overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${cit.citation_probability}%`, backgroundColor: getStatusColor(cit.citation_probability >= 80 ? "Excellent" : cit.citation_probability >= 60 ? "Healthy" : "Warning") }} />
                  </div>
                  <span style={{ fontSize: "0.85rem", fontWeight: "bold", minWidth: "40px", textAlign: "right" }}>
                    {cit.citation_probability}%
                  </span>
                </div>
              </div>
            ))
          ) : (
            <p style={{ color: "var(--text-muted)" }}>No page citation predictions generated. Execute pipeline to update.</p>
          )}
        </div>
      </div>

      {/* Grid: Authority Entities & Gaps */}
      <div className="grid-3" style={{ marginBottom: "2.5rem", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
        {/* Discovered Authorities */}
        <div className="card" style={{ padding: "1.5rem" }}>
          <h3 style={{ margin: "0 0 1.2rem 0" }}>📚 Discovered Authority Entities</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {authorities.length > 0 ? (
              authorities.map((aut, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.6rem", background: "rgba(255,255,255,0.02)", borderRadius: "4px" }}>
                  <div>
                    <div style={{ fontWeight: "bold", fontSize: "0.9rem", color: "#fff" }}>{aut.entity_name}</div>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{aut.entity_type}</span>
                  </div>
                  <span className="badge badge-info" style={{ fontWeight: "bold" }}>
                    {aut.authority_strength} strength
                  </span>
                </div>
              ))
            ) : (
              <p style={{ color: "var(--text-muted)" }}>No standards or case studies cataloged.</p>
            )}
          </div>
        </div>

        {/* Gaps List */}
        <div className="card" style={{ padding: "1.5rem" }}>
          <h3 style={{ margin: "0 0 1.2rem 0" }}>⚠️ Recommendation Gaps & Fixes</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", maxHeight: "380px", overflowY: "auto" }}>
            {sortedGaps.length > 0 ? (
              sortedGaps.map((gap, i) => {
                const isCritical = gap.severity === "CRITICAL" || gap.severity === "HIGH";
                return (
                  <div key={i} style={{ borderLeft: `3px solid ${isCritical ? "var(--accent-red)" : "var(--accent-amber)"}`, paddingLeft: "0.8rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ fontSize: "0.9rem", color: "#fff" }}>{gap.missing_signal}</strong>
                      <span className="badge" style={{ backgroundColor: isCritical ? "rgba(239, 68, 68, 0.15)" : "rgba(245, 158, 11, 0.15)", color: isCritical ? "var(--accent-red)" : "var(--accent-amber)" }}>
                        {gap.severity}
                      </span>
                    </div>
                    <p style={{ margin: "0.3rem 0", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      {gap.explanation}
                    </p>
                    <div style={{ fontSize: "0.8rem", color: "var(--accent-green)" }}>
                      <strong>Fix:</strong> {gap.repair_action}
                    </div>
                  </div>
                );
              })
            ) : (
              <p style={{ color: "var(--text-muted)" }}>No gaps detected. Excellent compliance footprint.</p>
            )}
          </div>
        </div>
      </div>

      {/* Competitor Analysis Matrix */}
      <div style={{ marginBottom: "2.5rem" }}>
        <h3 style={{ margin: "0 0 0.5rem 0" }}>⚔️ Competitor Recommendation Matrix</h3>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
          Side-by-side gap audit detailing relative advantages, trust differences, and authority gaps.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {competitors.length > 0 ? (
            competitors.map((comp, i) => (
              <div key={i} className="card p-5 border border-white/10 rounded-2xl bg-white/5 space-y-4 hover:border-white/20 transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-white font-bold text-base">{comp.competitor}</span>
                  <div className="flex gap-3 text-xs">
                    <span className="flex items-center gap-1 text-white/50">
                      Trust: 
                      <span style={{ color: comp.trust_difference < 0 ? "var(--accent-red)" : "var(--accent-green)", fontWeight: "bold" }}>
                        {comp.trust_difference >= 0 ? "+" : ""}{comp.trust_difference}%
                      </span>
                    </span>
                    <span className="flex items-center gap-1 text-white/50">
                      Auth: 
                      <span style={{ color: comp.authority_difference < 0 ? "var(--accent-red)" : "var(--accent-green)", fontWeight: "bold" }}>
                        {comp.authority_difference >= 0 ? "+" : ""}{comp.authority_difference}%
                      </span>
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-xs pt-2 border-t border-white/5">
                  <div>
                    <span className="text-white/40 block mb-1">THEIR ADVANTAGE</span>
                    <span className="text-white/80 leading-relaxed">{comp.advantage || "—"}</span>
                  </div>
                  <div>
                    <span className="text-white/40 block mb-1">THEIR WEAKNESS</span>
                    <span className="text-white/80 leading-relaxed">{comp.weakness || "—"}</span>
                  </div>
                </div>

                <div className="text-xs pt-3 border-t border-white/5 flex flex-col gap-1 bg-amber-500/5 p-3 rounded-xl border border-amber-500/10">
                  <span className="text-amber-400 font-semibold">Missing Signals</span>
                  <span className="text-white/70 leading-relaxed">{comp.recommendation_gap || "—"}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-2 text-center py-8 text-white/30 card border-white/10 rounded-2xl bg-white/5">No competitor audit matrices generated yet.</div>
          )}
        </div>
      </div>

      {/* Citation Reasoning Explainability */}
      <div style={{ marginBottom: "2.5rem" }}>
        <h3>💡 Page Citation Reasoning & Verification</h3>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
          Explainability breakdown detailing backing evidence and citation trust ratings.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "1.2rem" }}>
          {reasonings.length > 0 ? (
            reasonings.map((rea, i) => (
              <div key={i} className="card" style={{ padding: "1.5rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.8rem" }}>
                  <a href={rea.page_url} target="_blank" rel="noreferrer" style={{ color: "var(--secondary)", fontWeight: "bold" }}>
                    {rea.page_title}
                  </a>
                  <span className="badge badge-success" style={{ fontWeight: "bold" }}>
                    {rea.confidence_score}% Confidence
                  </span>
                </div>
                
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
                  <div>
                    <h5 style={{ margin: "0 0 0.4rem 0", color: "var(--text-muted)", fontSize: "0.8rem" }}>SUPPORTING EVIDENCE</h5>
                    <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                      {rea.supporting_evidence.map((ev: string, idx: number) => (
                        <li key={idx} style={{ color: "var(--text-light)" }}>{ev}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h5 style={{ margin: "0 0 0.4rem 0", color: "var(--text-muted)", fontSize: "0.8rem" }}>WEAKNESSES / PENALTIES</h5>
                    <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                      {rea.weaknesses.map((we: string, idx: number) => (
                        <li key={idx} style={{ color: "var(--accent-red)" }}>{we}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", marginTop: "1rem", paddingTop: "0.8rem" }}>
                  <h5 style={{ margin: "0 0 0.3rem 0", color: "var(--text-muted)", fontSize: "0.8rem" }}>CITATION REASONING DETAILS</h5>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem" }}>
                    {rea.citation_reasons.map((cr: string, idx: number) => (
                      <div key={idx} style={{ fontSize: "0.85rem", color: "var(--accent-green)" }}>
                        ✓ {cr}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p style={{ color: "var(--text-muted)" }}>No reasoning logs available.</p>
          )}
        </div>
      </div>

      {/* Priority Recommendations */}
      <div>
        <h3>📋 Priority Recommendation Optimization Tasks</h3>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
          Ordered task list focused on maximizing AI search recommendation probability.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {sortedGaps.map((gap, i) => {
            const isCritical = gap.severity === "CRITICAL" || gap.severity === "HIGH";
            const indexValue = isCritical ? 90 : gap.severity === "MEDIUM" ? 65 : 40;
            const effortScore = isCritical ? 75 : gap.severity === "MEDIUM" ? 50 : 30;
            return (
              <div key={i} className="card" style={{ padding: "1.2rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.8rem" }}>
                    <span className="badge" style={{ backgroundColor: isCritical ? "var(--accent-red)20" : "var(--accent-amber)20", color: isCritical ? "var(--accent-red)" : "var(--accent-amber)" }}>
                      {gap.severity}
                    </span>
                    <strong style={{ color: "#fff" }}>{gap.repair_action}</strong>
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.3rem" }}>
                    Target Area: {gap.category} — {gap.missing_signal}
                  </div>
                </div>
                <div style={{ display: "flex", gap: "2rem", textAlign: "right" }}>
                  <div>
                    <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>EXPECTED IMPR.</div>
                    <strong style={{ color: "var(--accent-green)", fontSize: "1.1rem" }}>+{indexValue}%</strong>
                  </div>
                  <div>
                    <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>EFFORT</div>
                    <strong style={{ color: "var(--secondary)", fontSize: "1.1rem" }}>{effortScore}</strong>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
